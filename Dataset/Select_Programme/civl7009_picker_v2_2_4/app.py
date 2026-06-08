from __future__ import annotations

import argparse
import io
import json
import queue
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from PIL import Image
except Exception:  # pragma: no cover
    Image = None

try:
    from PySide6.QtCore import QAbstractTableModel, QModelIndex, QObject, QRunnable, Qt, QThreadPool, QTimer, Signal, Slot
    from PySide6.QtGui import QAction, QCloseEvent, QImage, QKeyEvent, QKeySequence, QPixmap, QShortcut
    from PySide6.QtSvgWidgets import QSvgWidget
    from PySide6.QtWidgets import (
        QApplication,
        QCheckBox,
        QComboBox,
        QDialog,
        QFileDialog,
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QScrollArea,
        QSizePolicy,
        QSplitter,
        QStackedWidget,
        QTableView,
        QTextEdit,
        QToolButton,
        QVBoxLayout,
        QWidget,
    )
except Exception as exc:  # pragma: no cover
    QT_IMPORT_ERROR = exc
else:
    QT_IMPORT_ERROR = None

from .assets import AssetService
from .core import PickerCoreFacade
from .paths import ASSET_DIR, PROGRAMME_DIR, RUNTIME_LOG_ROOT
from .version import PROGRAMME_VERSION, STATUS, UI_VERSION


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}


def now_iso() -> str:
    return datetime.now().isoformat(timespec="milliseconds")


def runtime_subdir(run_mode: str) -> str:
    return {
        "gui_production": "Production",
        "production": "Production",
        "test": "Test",
        "audit_only": "AuditOnly",
        "debug": "Debug",
    }.get(run_mode, "Debug")


class V223Logger:
    def __init__(self, run_mode: str) -> None:
        self.run_mode = run_mode or "gui_production"
        self.run_id = datetime.now().strftime("%Y%m%d%H%M%S%f")[:-3]
        self.started = time.perf_counter()
        self.review_dir = ""
        self.core_meta: dict[str, Any] = {}
        self.log_dir = RUNTIME_LOG_ROOT / runtime_subdir(self.run_mode)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.log_dir / f"picker_events_{PROGRAMME_VERSION}_{self.run_id}.jsonl"
        self.path.write_text("", encoding="utf-8")
        self.event("run_start", programme_dir=str(PROGRAMME_DIR))

    def set_review_dir(self, review_dir: str | Path | None) -> None:
        self.review_dir = str(review_dir or "")

    def set_core_meta(self, **fields: Any) -> None:
        self.core_meta.update(fields)
        self.event("core_meta", **fields)

    def payload(self, event: str, **fields: Any) -> dict[str, Any]:
        data = {
            "timestamp": now_iso(),
            "elapsed_ms": round((time.perf_counter() - self.started) * 1000, 3),
            "event": event,
            "programme_version": PROGRAMME_VERSION,
            "ui_version": UI_VERSION,
            "core_version": self.core_meta.get("core_version", ""),
            "core_timecode": self.core_meta.get("core_timecode", ""),
            "run_mode": self.run_mode,
            "review_dir": self.review_dir,
        }
        data.update(fields)
        return data

    def event(self, event: str, **fields: Any) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(self.payload(event, **fields), ensure_ascii=False, default=str) + "\n")

    def perf(self, event: str, started: float, **fields: Any) -> None:
        fields["duration_ms"] = round((time.perf_counter() - started) * 1000, 3)
        self.event(event, **fields)

    def can_write_transaction_log(self) -> bool:
        try:
            probe = self.log_dir / f".transaction_probe_{self.run_id}.tmp"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return True
        except OSError:
            return False


class TableModel(QAbstractTableModel):
    def __init__(self, headers: list[str], rows: list[list[Any]] | None = None) -> None:
        super().__init__()
        self.headers = headers
        self.rows = rows or []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return len(self.rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return len(self.headers)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if role in {Qt.DisplayRole, Qt.ToolTipRole} and index.isValid():
            return str(self.rows[index.row()][index.column()])
        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole) -> Any:  # noqa: N802
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.headers[section]
        return None

    def set_rows(self, rows: list[list[Any]]) -> None:
        self.beginResetModel()
        self.rows = rows
        self.endResetModel()


class OpenReviewSignals(QObject):
    progress = Signal(int, str, str)
    quick_ready = Signal(int, object)
    index_ready = Signal(int, object, object, object, object, list)
    error = Signal(int, str, str)


class OpenReviewWorker(QRunnable):
    def __init__(self, generation: int, facade: PickerCoreFacade, review_dir: Path) -> None:
        super().__init__()
        self.setAutoDelete(False)
        self.generation = generation
        self.facade = facade
        self.review_dir = review_dir
        self.signals = OpenReviewSignals()

    def run(self) -> None:
        try:
            core = self.facade.require_core()
            self.signals.progress.emit(self.generation, "正在获取筛选目录锁", str(self.review_dir))
            lock = core.ReviewDirLock(self.review_dir)
            try:
                lock.acquire(clear_stale=False)
            except Exception as exc:
                if "ERROR_STALE_REVIEW_LOCK" in str(exc):
                    lock.acquire(clear_stale=True)
                else:
                    raise
            self.signals.progress.emit(self.generation, "正在检查恢复状态", "扫描未完成事务")
            recovery = core.scan_unfinished_transactions(review_dir=self.review_dir)
            if recovery:
                raise RuntimeError(f"存在 {len(recovery)} 个未处理恢复问题")
            self.signals.progress.emit(self.generation, "正在准备快速预览", "扫描前 20 个完整图组")
            quick = core.build_quick_preview_index(self.review_dir, preview_limit=20)
            self.signals.quick_ready.emit(self.generation, quick)
            self.signals.progress.emit(self.generation, "正在构建快速索引（FastReviewIndex）", "提交启用前需要完成")
            index = core.build_fast_review_index(self.review_dir)
            self.signals.progress.emit(self.generation, "正在运行完整校核（Full Audit）", "校核 root/done/out 与标签同步")
            summary, rows = core.audit_review_dir(self.review_dir, create_missing=False)
            self.signals.index_ready.emit(self.generation, lock, index, summary, rows, recovery)
        except Exception as exc:
            self.signals.error.emit(self.generation, "OPEN_REVIEW_FAILED", str(exc))


class ThumbnailSignals(QObject):
    ready = Signal(int, str, bytes, int, int, str)


class ThumbnailWorker(QRunnable):
    def __init__(self, generation: int, image_path: Path, max_width: int, max_height: int) -> None:
        super().__init__()
        self.setAutoDelete(False)
        self.generation = generation
        self.image_path = image_path
        self.max_width = max_width
        self.max_height = max_height
        self.signals = ThumbnailSignals()

    def run(self) -> None:
        if Image is None:
            self.signals.ready.emit(self.generation, str(self.image_path), b"", 0, 0, "Pillow 不可用")
            return
        try:
            with Image.open(self.image_path) as img:
                img = img.convert("RGBA")
                img.thumbnail((self.max_width, self.max_height), Image.Resampling.LANCZOS)
                width, height = img.size
                self.signals.ready.emit(self.generation, str(self.image_path), img.tobytes("raw", "RGBA"), width, height, "")
        except Exception as exc:
            self.signals.ready.emit(self.generation, str(self.image_path), b"", 0, 0, str(exc))


class ImageCard(QFrame):
    selected = Signal(int)
    activated = Signal(int)

    def __init__(self, index: int, key_text: str, image_path: Path) -> None:
        super().__init__()
        self.index = index
        self.key_text = key_text
        self.image_path = image_path
        self.setObjectName("imageCard")
        self.setProperty("selected", False)
        self.setProperty("selectedState", "false")
        self.setMinimumSize(220, 260)
        layout = QVBoxLayout(self)
        top = QHBoxLayout()
        self.key_label = QLabel(key_text or "·")
        self.key_label.setObjectName("cardNumber")
        top.addWidget(self.key_label)
        self.target_label = QLabel("预览")
        self.target_label.setObjectName("statusChip")
        self.target_label.setProperty("selectedState", "false")
        top.addStretch(1)
        top.addWidget(self.target_label)
        layout.addLayout(top)
        self.preview = QLabel("加载缩略图")
        self.preview.setObjectName("imagePreview")
        self.preview.setProperty("selectedState", "false")
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setMinimumHeight(170)
        layout.addWidget(self.preview, 1)
        self.file_label = QLabel(image_path.name)
        self.file_label.setObjectName("cardFilename")
        self.file_label.setToolTip(str(image_path))
        layout.addWidget(self.file_label)
        self.status_label = QLabel("Label: 待检查 | Target: done/out")
        self.status_label.setObjectName("cardStatus")
        layout.addWidget(self.status_label)

    def set_selected(self, selected: bool) -> None:
        state = "true" if selected else "false"
        self.setProperty("selected", selected)
        self.setProperty("selectedState", state)
        self.preview.setProperty("selected", selected)
        self.preview.setProperty("selectedState", state)
        self.target_label.setProperty("selected", selected)
        self.target_label.setProperty("selectedState", state)
        self.target_label.setText("已选图源预览" if selected else "预览")
        for widget in [self, self.preview, self.target_label]:
            widget.style().unpolish(widget)
            widget.style().polish(widget)
            widget.update()
            widget.repaint()

    def set_thumbnail(self, image: QImage) -> None:
        pixmap = QPixmap.fromImage(image)
        self.preview.setPixmap(pixmap)
        self.preview.setText("")
        self.status_label.setText(f"{image.width()}×{image.height()} | Label OK | Target: done/out")

    def mousePressEvent(self, event: Any) -> None:
        if event.button() == Qt.LeftButton:
            self.selected.emit(self.index)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: Any) -> None:
        self.activated.emit(self.index)
        super().mouseDoubleClickEvent(event)


class ImageViewer(QDialog):
    def __init__(self, image_path: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"100% 原图查看器 - {image_path.name}")
        self.resize(980, 720)
        layout = QVBoxLayout(self)
        label = QLabel()
        label.setAlignment(Qt.AlignCenter)
        pixmap = QPixmap(str(image_path))
        label.setPixmap(pixmap)
        scroll = QScrollArea()
        scroll.setWidget(label)
        layout.addWidget(scroll)


class MainWindow(QMainWindow):
    NAV = [
        ("Review", "筛选"),
        ("Staging", "暂存"),
        ("Recovery", "恢复"),
        ("Initialise", "初始化"),
        ("Diagnostics", "诊断"),
        ("Dashboard", "仪表盘"),
        ("Settings", "设置"),
    ]

    def __init__(self, run_mode: str = "gui_production") -> None:
        super().__init__()
        if QT_IMPORT_ERROR is not None:
            raise RuntimeError(QT_IMPORT_ERROR)
        self.run_mode = run_mode
        self.assets = AssetService()
        self.assets.ensure_assets()
        self.logger = V223Logger(run_mode)
        self.facade = PickerCoreFacade()
        self.core = self.facade.core if self.facade.report.ok else None
        if self.core is not None:
            self.logger.set_core_meta(
                core_version=getattr(self.core, "SCRIPT_VERSION", ""),
                core_timecode=getattr(self.core, "SCRIPT_TIMECODE", ""),
                core_file=str(self.facade.report.path),
                core_sha256=self.facade.report.core_sha256,
            )
        else:
            self.logger.event(
                "core_load_failed",
                core_file=str(self.facade.report.path) if self.facade.report.path else "",
                candidate_paths=self.facade.report.candidate_paths,
                missing_symbols=self.facade.report.missing_symbols,
                signature_errors=self.facade.report.signature_errors,
                error=self.facade.report.error,
            )
        self.thread_pool = QThreadPool.globalInstance()
        self.generation = 0
        self.id_root: Path | None = None
        self.current_review_dir: Path | None = None
        self.current_lock: Any | None = None
        self.quick_index: Any | None = None
        self.fast_index: Any | None = None
        self.audit_summary: Any | None = None
        self.audit_rows: list[Any] = []
        self.recovery_rows: list[Any] = []
        self.current_groups: list[tuple[str, list[Path]]] = []
        self.current_group_index = 0
        self.selected_card_index: int | None = None
        self.cards: list[ImageCard] = []
        self.key_to_card: dict[str, int] = {}
        self.safe_gate_enabled = False
        self.auto_move_armed = False
        self.startup_notice_shown = False
        self.click_mode_commit = True
        self.last_committed_transaction: Any | None = None
        self.optimistic_transaction_ids: set[str] = set()
        self.move_event_queue: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.move_runner = self.core.BackgroundMoveRunner(self.move_event_queue) if self.core else None
        self.open_worker: OpenReviewWorker | None = None
        self.thumbnail_workers: list[ThumbnailWorker] = []

        self.review_model = TableModel(["目录", "Root", "Done", "异常", "标签同步"])
        self.issue_model = TableModel(["等级", "Prefix", "代码", "说明", "建议"])
        self.queue_model = TableModel(["任务", "Prefix", "选中", "状态", "错误"])
        self.recent_model = TableModel(["时间", "事件"])

        self.setWindowTitle(f"CIVL7009 图源筛选器 {UI_VERSION}")
        self.resize(1600, 940)
        self.setMinimumSize(1366, 768)
        self.build_ui()
        self.apply_style()
        self.install_shortcuts()
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self.poll_move_events)
        self.poll_timer.start(120)
        self.update_safe_gate()
        self.show_empty_state()
        if self.run_mode not in {"test", "debug"}:
            QTimer.singleShot(350, self.show_startup_notice)

    def build_ui(self) -> None:
        root = QWidget()
        main = QVBoxLayout(root)
        main.setContentsMargins(14, 14, 14, 14)
        main.setSpacing(12)
        main.addWidget(self.build_command_bar())
        main.addWidget(self.build_nav_bar())
        self.stack = QStackedWidget()
        self.stack.addWidget(self.build_review_page())
        self.stack.addWidget(self.simple_page("暂存队列（Staging）", "Manifest-only 队列默认启用；Physical Staging 默认关闭。本页保留 V2 框架，不移动真实文件。"))
        self.stack.addWidget(self.simple_page("恢复中心（Recovery Center）", "恢复问题会阻断新移动；高风险动作需要人工确认。"))
        self.stack.addWidget(self.simple_page("ID 初始化（Initialise）", "V2.2.4 保留初始化向导入口；写入动作仍须 dry-run 与 INIT 确认，原 YOLO 数据不移动、不删除。"))
        self.stack.addWidget(self.simple_page("诊断中心（Diagnostics）", "显示事件摘要、性能、状态快照与诊断包导出入口；Raw JSON 仅高级模式查看。"))
        self.stack.addWidget(self.simple_page("Session Operations Dashboard", "PENDING_AUDIT — operational metrics only。吞吐和剩余时间仅为粗略操作指标。"))
        self.stack.addWidget(self.simple_page("设置（Settings）", "默认 light + Balanced。Safe Gate 每次启动默认 OFF；image2 资产仅为抽象 UI 装饰。"))
        main.addWidget(self.stack, 1)
        self.setCentralWidget(root)

    def build_command_bar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("commandBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(6)
        self.choose_id_btn = QPushButton("选择 ID 根目录")
        self.choose_review_btn = QPushButton("直接选择筛选目录")
        self.export_btn = QPushButton("导出校核")
        self.undo_btn = QPushButton("撤销上一组")
        self.undo_btn.setEnabled(False)
        self.safe_gate_btn = QPushButton("启用文件移动")
        self.safe_gate_btn.setObjectName("dangerButton")
        self.mode_box = QComboBox()
        self.mode_box.addItems(["Safe Gate 开启后单击/数字键直接提交", "单击只预览，Enter 提交"])
        self.mode_box.currentIndexChanged.connect(lambda idx: setattr(self, "click_mode_commit", idx == 0))
        self.progress_chip = QLabel("请选择目录")
        self.progress_chip.setObjectName("progressChip")
        self.progress_chip.setMinimumWidth(230)
        self.progress_chip.setMaximumWidth(360)
        self.progress_chip.setWordWrap(False)
        self.context_label = QLabel("ID: 未选择 | 筛选目录: 未选择")
        self.context_label.setObjectName("context")
        self.context_full_text = self.context_label.text()
        self.context_label.setToolTip(self.context_full_text)
        self.context_label.setWordWrap(False)
        self.context_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.status_badge = QLabel("自动移动准备中")
        self.status_badge.setObjectName("safeBadge")
        self.status_badge.setMinimumWidth(156)
        self.status_badge.setMaximumWidth(190)
        self.status_badge.setWordWrap(False)
        self.status_badge.setAlignment(Qt.AlignCenter)
        for widget in [self.choose_id_btn, self.choose_review_btn, self.export_btn, self.undo_btn, self.safe_gate_btn, self.mode_box]:
            layout.addWidget(widget)
        layout.addStretch(1)
        layout.addWidget(self.progress_chip)
        layout.addWidget(self.status_badge)
        layout.addWidget(self.context_label, 1)
        self.choose_id_btn.clicked.connect(self.choose_id_root)
        self.choose_review_btn.clicked.connect(self.choose_review_dir)
        self.export_btn.clicked.connect(self.export_current_audit)
        self.undo_btn.clicked.connect(self.undo_last_transaction)
        self.safe_gate_btn.clicked.connect(self.toggle_safe_gate)
        return bar

    def build_nav_bar(self) -> QWidget:
        nav = QFrame()
        nav.setObjectName("navBar")
        layout = QHBoxLayout(nav)
        layout.setContentsMargins(10, 8, 10, 8)
        title = QLabel("CIVL7009 V2.2.4")
        title.setObjectName("appTitle")
        layout.addWidget(title)
        self.nav_buttons: list[QPushButton] = []
        for index, (_key, label) in enumerate(self.NAV):
            button = QPushButton(label)
            button.setObjectName("navButton")
            button.setCheckable(True)
            button.clicked.connect(lambda _=False, i=index: self.set_page(i))
            layout.addWidget(button)
            self.nav_buttons.append(button)
        layout.addStretch(1)
        self.nav_status_full_text = "就绪"
        self.nav_status_chip = QLabel("就绪")
        self.nav_status_chip.setObjectName("navStatusChip")
        self.nav_status_chip.setMinimumWidth(260)
        self.nav_status_chip.setMaximumWidth(520)
        self.nav_status_chip.setWordWrap(False)
        self.nav_status_chip.setAlignment(Qt.AlignCenter)
        self.nav_status_chip.setToolTip(self.nav_status_full_text)
        layout.addWidget(self.nav_status_chip)
        self.set_page(0)
        return nav

    def build_review_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        kpis = QHBoxLayout()
        self.kpi_labels: dict[str, QLabel] = {}
        for key, title in [
            ("root", "Root 剩余"),
            ("current", "当前组"),
            ("done", "Done 组"),
            ("out", "Out 图"),
            ("queue", "后台队列"),
            ("sync", "标签同步"),
        ]:
            card = QFrame()
            card.setObjectName("kpiCard")
            card_layout = QVBoxLayout(card)
            card_layout.addWidget(QLabel(title))
            value = QLabel("0")
            value.setObjectName("kpiValue")
            card_layout.addWidget(value)
            self.kpi_labels[key] = value
            kpis.addWidget(card)
        layout.addLayout(kpis)

        self.review_vertical_splitter = QSplitter(Qt.Vertical)
        splitter = QSplitter(Qt.Horizontal)
        left = QFrame()
        left.setObjectName("glassPanel")
        left_layout = QVBoxLayout(left)
        board_header = QHBoxLayout()
        board_header.addWidget(QLabel("目录大盘（Review Board）"))
        self.board_toggle = QToolButton()
        self.board_toggle.setText("收起")
        self.board_toggle.clicked.connect(lambda: left.setVisible(False))
        board_header.addWidget(self.board_toggle)
        left_layout.addLayout(board_header)
        self.review_table = QTableView()
        self.review_table.setModel(self.review_model)
        self.review_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.review_table.horizontalHeader().setStretchLastSection(False)
        self.review_table.doubleClicked.connect(self.open_review_from_board)
        left_layout.addWidget(self.review_table, 1)
        splitter.addWidget(left)

        center = QFrame()
        center.setObjectName("stagePanel")
        center_layout = QVBoxLayout(center)
        self.overlay = QFrame()
        self.overlay.setObjectName("overlay")
        overlay_layout = QHBoxLayout(self.overlay)
        self.overlay_badge = QSvgWidget(str(self.assets.asset("loading_overlay.svg")))
        self.overlay_badge.setFixedSize(120, 80)
        self.overlay_text = QLabel("请选择一个人工筛选目录。")
        self.overlay_text.setWordWrap(True)
        overlay_layout.addWidget(self.overlay_badge)
        overlay_layout.addWidget(self.overlay_text, 1)
        center_layout.addWidget(self.overlay)
        self.image_scroll = QScrollArea()
        self.image_scroll.setWidgetResizable(True)
        self.image_host = QWidget()
        self.image_grid = QGridLayout(self.image_host)
        self.image_grid.setSpacing(14)
        self.image_scroll.setWidget(self.image_host)
        center_layout.addWidget(self.image_scroll, 1)
        nav = QHBoxLayout()
        self.prev_btn = QPushButton("上一组")
        self.next_btn = QPushButton("下一组")
        self.commit_btn = QPushButton("提交当前选中")
        self.commit_btn.setEnabled(False)
        nav.addWidget(self.prev_btn)
        nav.addWidget(self.next_btn)
        nav.addStretch(1)
        nav.addWidget(self.commit_btn)
        center_layout.addLayout(nav)
        self.prev_btn.clicked.connect(lambda: self.step_group(-1))
        self.next_btn.clicked.connect(lambda: self.step_group(1))
        self.commit_btn.clicked.connect(self.commit_selected)
        splitter.addWidget(center)

        right = QFrame()
        right.setObjectName("glassPanel")
        right_layout = QVBoxLayout(right)
        right_layout.addWidget(QLabel("当前组检查器（Current Group Inspector）"))
        self.group_text = QTextEdit()
        self.group_text.setReadOnly(True)
        self.group_text.setMaximumHeight(116)
        right_layout.addWidget(self.group_text)
        right_layout.addWidget(QLabel("异常表（Issue Table）"))
        self.issue_table = QTableView()
        self.issue_table.setModel(self.issue_model)
        self.issue_table.horizontalHeader().setStretchLastSection(True)
        right_layout.addWidget(self.issue_table, 1)
        right_layout.addWidget(QLabel("校核公式（Formula Inspector）"))
        self.formula_text = QTextEdit()
        self.formula_text.setReadOnly(True)
        self.formula_text.setMaximumHeight(132)
        right_layout.addWidget(self.formula_text)
        splitter.addWidget(right)
        splitter.setSizes([300, 900, 360])
        self.review_horizontal_splitter = splitter
        self.review_vertical_splitter.addWidget(splitter)

        bottom = QFrame()
        bottom.setObjectName("glassPanel")
        bottom_layout = QHBoxLayout(bottom)
        bottom.setMinimumHeight(110)
        self.bottom_splitter = QSplitter(Qt.Horizontal)
        self.queue_table = QTableView()
        self.queue_table.setModel(self.queue_model)
        self.queue_table.horizontalHeader().setStretchLastSection(True)
        self.recent_table = QTableView()
        self.recent_table.setModel(self.recent_model)
        self.recent_table.horizontalHeader().setStretchLastSection(True)
        self.bottom_splitter.addWidget(self.queue_table)
        self.bottom_splitter.addWidget(self.recent_table)
        self.bottom_splitter.setSizes([520, 520])
        bottom_layout.addWidget(self.bottom_splitter)
        self.review_vertical_splitter.addWidget(bottom)
        self.review_vertical_splitter.setSizes([760, 190])
        layout.addWidget(self.review_vertical_splitter, 1)
        return page

    def simple_page(self, title: str, message: str) -> QWidget:
        page = QFrame()
        page.setObjectName("glassPanel")
        layout = QVBoxLayout(page)
        title_label = QLabel(title)
        title_label.setObjectName("sectionTitle")
        layout.addWidget(title_label)
        body = QLabel(message)
        body.setWordWrap(True)
        layout.addWidget(body)
        art = QSvgWidget(str(self.assets.asset("image2_glass_cockpit.svg")))
        art.setMinimumHeight(360)
        layout.addWidget(art, 1)
        return page

    def set_page(self, index: int) -> None:
        if hasattr(self, "stack"):
            self.stack.setCurrentIndex(index)
        for i, button in enumerate(getattr(self, "nav_buttons", [])):
            button.setChecked(i == index)

    def resize_review_columns(self) -> None:
        if not hasattr(self, "review_table"):
            return
        width = max(520, self.review_table.viewport().width())
        weights = [0.46, 0.13, 0.13, 0.12, 0.16]
        for column, weight in enumerate(weights):
            self.review_table.setColumnWidth(column, int(width * weight))

    def resizeEvent(self, event: Any) -> None:
        super().resizeEvent(event)
        self.resize_review_columns()
        if hasattr(self, "context_full_text"):
            self.set_elided_label(self.context_label, self.context_full_text)
        if hasattr(self, "nav_status_full_text"):
            self.set_nav_status(self.nav_status_full_text)

    def apply_style(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow, QWidget { background: #EEF2F6; color: #17201C; font-size: 12px; font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif; }
            #commandBar, #navBar, #glassPanel, #stagePanel { background: rgba(255,255,255,0.76); border: 1px solid rgba(255,255,255,0.92); border-radius: 12px; }
            #navBar { background: rgba(9,68,56,0.08); }
            #appTitle { font-size: 20px; font-weight: 800; color: #094438; }
            #sectionTitle { font-size: 22px; font-weight: 800; color: #094438; }
            #progressChip, #safeBadge, #statusChip { padding: 8px 12px; border-radius: 8px; background: rgba(209,193,141,0.24); color: #094438; font-weight: 700; }
            #safeBadge { padding: 7px 12px; min-width: 156px; }
            #navStatusChip { padding: 7px 12px; border-radius: 8px; background: rgba(209,193,141,0.22); color: #094438; font-weight: 800; }
            #statusChip[selectedState="true"] { background: rgba(239,64,34,0.14); color: #EF4022; border: 1px solid rgba(239,64,34,0.36); }
            #safeBadge[enabledMoves="true"] { background: rgba(239,64,34,0.18); color: #EF4022; }
            #context { color: #667085; }
            #kpiCard { background: rgba(255,255,255,0.82); border: 1px solid rgba(209,193,141,0.55); border-radius: 12px; }
            #kpiValue { font-size: 22px; font-weight: 800; color: #094438; }
            #overlay { background: rgba(253,253,253,0.88); border: 1px solid rgba(255,255,255,0.95); border-radius: 12px; }
            #imageCard { background: rgba(255,255,255,0.82); border: 2px solid rgba(209,193,141,0.42); border-radius: 12px; }
            #imageCard[selectedState="true"] { border: 3px solid #EF4022; background: rgba(255,255,255,0.98); }
            #imagePreview { background: rgba(232,237,242,0.88); border: 2px solid transparent; border-radius: 10px; }
            #imagePreview[selectedState="true"] { border: 2px solid #EF4022; background: rgba(239,64,34,0.05); }
            #cardNumber { color: #EF4022; font-size: 24px; font-weight: 900; }
            #cardFilename { color: #17201C; font-weight: 700; }
            #cardStatus { color: #667085; }
            QPushButton { background: rgba(255,255,255,0.88); border: 1px solid rgba(9,68,56,0.25); border-radius: 8px; padding: 6px 10px; }
            QPushButton:hover { border-color: #009CD5; }
            QPushButton:disabled { color: #98A2B3; background: rgba(232,237,242,0.72); }
            #dangerButton { color: #EF4022; font-weight: 800; }
            #navButton { padding: 6px 12px; min-width: 72px; }
            #navButton:checked { background: rgba(9,68,56,0.16); color: #094438; font-weight: 800; }
            QTableView, QTextEdit { background: rgba(255,255,255,0.70); border: 1px solid rgba(9,68,56,0.10); border-radius: 8px; }
            """
        )

    def install_shortcuts(self) -> None:
        for key in [str(i) for i in range(1, 10)]:
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.activated.connect(lambda k=key: self.select_by_key(k))
        QShortcut(QKeySequence("Return"), self).activated.connect(self.commit_selected)
        QShortcut(QKeySequence("Enter"), self).activated.connect(self.commit_selected)
        QShortcut(QKeySequence("Esc"), self).activated.connect(self.clear_selection)
        QShortcut(QKeySequence("Ctrl+Z"), self).activated.connect(self.undo_last_transaction)
        QShortcut(QKeySequence("Space"), self).activated.connect(self.open_selected_viewer)
        QShortcut(QKeySequence("?"), self).activated.connect(self.show_shortcuts)

    def choose_id_root(self) -> None:
        root = QFileDialog.getExistingDirectory(self, "选择 Dataset/Source_Archive/<ID> 根目录")
        if root:
            self.load_id_root(Path(root))

    def choose_review_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "选择 images/ManualReview_GroupSize_N 筛选目录")
        if path:
            self.open_review_dir(Path(path))

    def load_id_root(self, id_root: Path) -> None:
        if self.core is None:
            self.show_reason("Core Load Failed，无法扫描目录。")
            return
        started = time.perf_counter()
        try:
            dirs = self.facade.review_dirs_for_id_root(id_root)
            self.id_root = id_root.resolve()
            rows = []
            for directory in dirs:
                try:
                    summary, _ = self.facade.audit(directory)
                    rows.append([directory.name, summary.root_prefix_count, summary.done_prefix_count, len(summary.errors), self.label_sync_state(summary)])
                except Exception as exc:
                    rows.append([directory.name, "--", "--", "ERROR", str(exc)])
            self.review_model.set_rows(rows)
            self.review_dirs = dirs
            self.resize_review_columns()
            self.add_recent(f"已读取 ID 根目录：{self.id_root}")
            self.logger.perf("load_id_root_done", started, id_root=str(id_root), review_dir_count=len(dirs))
            self.update_context()
        except Exception as exc:
            self.add_issue("错误", "", "ID_ROOT_FAILED", str(exc), "检查 images/labels 与 ManualReview_GroupSize_N 结构。")

    def open_review_from_board(self, index: QModelIndex) -> None:
        dirs = getattr(self, "review_dirs", [])
        if 0 <= index.row() < len(dirs):
            self.open_review_dir(dirs[index.row()])

    def open_review_dir(self, review_dir: Path) -> None:
        if self.core is None:
            self.show_reason("Core Load Failed，无法打开筛选目录。")
            return
        self.release_lock()
        self.generation += 1
        self.current_review_dir = review_dir.resolve()
        self.logger.set_review_dir(self.current_review_dir)
        self.safe_gate_enabled = False
        self.quick_index = None
        self.fast_index = None
        self.audit_summary = None
        self.audit_rows = []
        self.recovery_rows = []
        self.current_groups = []
        self.current_group_index = 0
        self.selected_card_index = None
        self.cards = []
        self.key_to_card = {}
        self.update_safe_gate()
        self.update_context()
        self.clear_image_grid()
        self.set_progress("正在获取筛选目录锁", str(self.current_review_dir))
        worker = OpenReviewWorker(self.generation, self.facade, self.current_review_dir)
        worker.signals.progress.connect(self.on_open_progress)
        worker.signals.quick_ready.connect(self.on_quick_ready)
        worker.signals.index_ready.connect(self.on_index_ready)
        worker.signals.error.connect(self.on_worker_error)
        self.open_worker = worker
        self.thread_pool.start(worker)

    @Slot(int, str, str)
    def on_open_progress(self, generation: int, phase: str, detail: str) -> None:
        if generation == self.generation:
            self.set_progress(phase, detail)

    @Slot(int, object)
    def on_quick_ready(self, generation: int, index: Any) -> None:
        if generation != self.generation:
            return
        self.quick_index = index
        self.current_groups = index.selectable_groups()
        self.current_group_index = 0
        self.render_current_group()
        self.overlay.hide()
        self.set_nav_status("已可预览；完整索引完成前禁止提交")
        self.update_kpis()

    @Slot(int, object, object, object, object, list)
    def on_index_ready(self, generation: int, lock: Any, index: Any, summary: Any, rows: Any, recovery: list[Any]) -> None:
        if generation != self.generation:
            try:
                lock.release()
            except Exception:
                pass
            return
        self.current_lock = lock
        self.fast_index = index
        self.audit_summary = summary
        self.audit_rows = list(rows)
        self.recovery_rows = recovery
        self.current_groups = index.selectable_groups()
        self.current_group_index = min(self.current_group_index, max(0, len(self.current_groups) - 1))
        self.overlay.hide()
        self.update_issues_from_audit()
        self.update_formula()
        self.render_current_group()
        self.set_nav_status("FastReviewIndex 已完成；等待自动移动安全门")
        self.add_recent("快速索引（FastReviewIndex）与完整校核已完成")
        self.update_kpis()
        self.update_commit_enabled()
        self.auto_enable_safe_gate_if_ready()

    @Slot(int, str, str)
    def on_worker_error(self, generation: int, code: str, message: str) -> None:
        if generation != self.generation:
            return
        self.add_issue("错误", "", code, message, "修复该问题后重新打开目录。")
        self.set_nav_status(f"{code}: {message}")

    def set_elided_label(self, label: QLabel, full_text: str, reserve: int = 18) -> None:
        label.setToolTip(full_text)
        width = max(80, label.width() - reserve)
        label.setText(label.fontMetrics().elidedText(full_text, Qt.ElideRight, width))

    def set_nav_status(self, text: str) -> None:
        self.nav_status_full_text = text
        if hasattr(self, "nav_status_chip"):
            self.set_elided_label(self.nav_status_chip, text)

    def set_command_status(self, text: str) -> None:
        self.set_elided_label(self.progress_chip, text)

    def set_progress(self, phase: str, detail: str = "", target: str = "overlay") -> None:
        message = phase if not detail else f"{phase}: {detail}"
        if target == "overlay":
            self.overlay.show()
            self.overlay_text.setText(f"{phase}\n{detail}")
            self.set_command_status(phase)
            self.set_nav_status(message)
        elif target == "nav_chip":
            if hasattr(self, "overlay"):
                self.overlay.hide()
            self.set_nav_status(message)
        else:
            self.set_command_status(message)
        self.logger.event("progress_phase", phase=phase, detail=detail)

    def show_empty_state(self) -> None:
        self.clear_image_grid()
        holder = QFrame()
        holder.setObjectName("glassPanel")
        layout = QVBoxLayout(holder)
        art = QSvgWidget(str(self.assets.asset("image2_glass_cockpit.svg")))
        art.setMinimumHeight(360)
        layout.addWidget(art)
        title = QLabel("请选择要处理的目录")
        title.setObjectName("sectionTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        hint = QLabel("先选择 ID 根目录扫描大盘，或直接选择 images/ManualReview_GroupSize_N 筛选目录。")
        hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint)
        buttons = QHBoxLayout()
        b1 = QPushButton("选择 ID 根目录")
        b2 = QPushButton("直接选择筛选目录")
        b1.clicked.connect(self.choose_id_root)
        b2.clicked.connect(self.choose_review_dir)
        buttons.addStretch(1)
        buttons.addWidget(b1)
        buttons.addWidget(b2)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        self.image_grid.addWidget(holder, 0, 0)

    def clear_image_grid(self) -> None:
        while self.image_grid.count():
            item = self.image_grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def render_current_group(self) -> None:
        started = time.perf_counter()
        self.clear_image_grid()
        self.cards = []
        self.key_to_card = {}
        self.selected_card_index = None
        if not self.current_groups:
            self.show_empty_state()
            self.logger.perf("render_next_group_done", started, group_size=0)
            return
        prefix, members = self.current_groups[self.current_group_index]
        slots = self.facade.keypad_slots(len(members))
        for slot in slots:
            if slot.index >= len(members):
                continue
            image_path = Path(members[slot.index])
            key_text = slot.key or f"{slot.index + 1}"
            card = ImageCard(slot.index, key_text, image_path)
            card.selected.connect(self.select_card)
            card.activated.connect(self.open_viewer)
            self.cards.append(card)
            self.image_grid.addWidget(card, slot.row, slot.col)
            if slot.key:
                self.key_to_card[slot.key] = slot.index
            worker = ThumbnailWorker(self.generation, image_path, 420, 320)
            worker.signals.ready.connect(self.on_thumbnail_ready)
            self.thumbnail_workers.append(worker)
            self.thumbnail_workers = self.thumbnail_workers[-80:]
            self.thread_pool.start(worker)
        self.group_text.setText(
            f"Prefix: {prefix}\n"
            f"组内图片: {len(members)}\n"
            f"小键盘布局: {' / '.join([slot.key or str(slot.index + 1) for slot in slots])}\n"
            f"Safe Gate: {'ON 文件移动已启用' if self.safe_gate_enabled else 'OFF 只读预览'}"
        )
        self.progress_chip.setText(f"当前 Prefix: {prefix}")
        self.logger.perf("render_next_group_done", started, prefix=prefix, group_size=len(members))
        self.update_kpis()
        self.update_commit_enabled()

    @Slot(int, str, bytes, int, int, str)
    def on_thumbnail_ready(self, generation: int, path_text: str, payload: bytes, width: int, height: int, error: str) -> None:
        if generation != self.generation:
            return
        if error:
            self.add_issue("警告", "", "THUMBNAIL_FAILED", f"{Path(path_text).name}: {error}", "双击可尝试打开 100% 原图查看器。")
            return
        image = QImage(payload, width, height, QImage.Format_RGBA8888).copy()
        for card in self.cards:
            if str(card.image_path) == path_text:
                card.set_thumbnail(image)
                break

    @Slot(int)
    def select_card(self, index: int) -> None:
        if not self.current_groups:
            return
        self.selected_card_index = index
        for card in self.cards:
            card.set_selected(card.index == index)
        prefix = self.current_groups[self.current_group_index][0]
        selected_path = self.current_groups[self.current_group_index][1][index]
        self.logger.event("preview_select", prefix=prefix, selected=str(selected_path))
        self.add_recent(f"已选中 [{index + 1}] {Path(selected_path).name}")
        if self.safe_gate_enabled and self.click_mode_commit:
            QTimer.singleShot(70, self.commit_selected)
        else:
            self.update_commit_enabled()

    def select_by_key(self, key: str) -> None:
        if key in self.key_to_card:
            self.select_card(self.key_to_card[key])

    def clear_selection(self) -> None:
        self.selected_card_index = None
        for card in self.cards:
            card.set_selected(False)
        self.update_commit_enabled()

    def open_viewer(self, index: int) -> None:
        if 0 <= index < len(self.cards):
            viewer = ImageViewer(self.cards[index].image_path, self)
            viewer.exec()

    def open_selected_viewer(self) -> None:
        if self.selected_card_index is not None:
            self.open_viewer(self.selected_card_index)

    def step_group(self, delta: int) -> None:
        if not self.current_groups:
            return
        self.current_group_index = max(0, min(len(self.current_groups) - 1, self.current_group_index + delta))
        self.render_current_group()

    def disabled_reason(self) -> str:
        if not self.safe_gate_enabled:
            return "Safe Gate 未开启：当前为只读预览。"
        if self.current_lock is None:
            return "尚未持有筛选目录锁。"
        if self.recovery_rows:
            return "存在恢复问题。"
        if self.fast_index is None or not getattr(self.fast_index, "ready_for_commit", False):
            return "快速索引（FastReviewIndex）仍在构建。"
        if self.audit_summary is None:
            return "完整校核（Full Audit）尚未完成。"
        if getattr(self.audit_summary, "blocking_errors", []):
            return "存在阻断性校核错误。"
        if self.selected_card_index is None:
            return "尚未选择图片。"
        return ""

    def update_commit_enabled(self) -> None:
        reason = self.disabled_reason()
        self.commit_btn.setEnabled(reason == "")
        self.commit_btn.setToolTip(reason or "提交当前选中图片为图源。")

    def show_reason(self, reason: str) -> None:
        QMessageBox.information(self, "当前操作不可用", reason)
        self.add_recent(f"操作被阻断：{reason}")

    def show_startup_notice(self) -> None:
        if self.startup_notice_shown:
            return
        self.startup_notice_shown = True
        QMessageBox.information(
            self,
            "自动移动模式说明",
            "本工具用于人工选择同源组内的图源。\n\n"
            "目录就绪并通过安全校核后，程序会自动进入文件移动模式：\n"
            "1. 单击图片或按数字键会直接提交当前组。\n"
            "2. 选中的图片和标签进入 done。\n"
            "3. 同组其他图片和标签进入 out。\n"
            "4. 后台队列会继续移动文件，必要时可以撤销上一组。\n\n"
            "如果目录锁、恢复扫描、快速索引或完整校核未通过，程序会保持只读预览并显示原因。",
        )
        self.auto_move_armed = True
        self.logger.event("auto_move_armed", source="startup_notice")
        self.add_recent("自动移动说明已确认；等待目录就绪后自动启用文件移动。")
        self.auto_enable_safe_gate_if_ready()

    def acknowledge_startup_notice_for_tests(self) -> None:
        self.startup_notice_shown = True
        self.auto_move_armed = True
        self.logger.event("auto_move_armed", source="test")
        self.auto_enable_safe_gate_if_ready()

    def can_enable_safe_gate(self) -> tuple[bool, str]:
        if self.current_review_dir is None:
            return False, "尚未打开筛选目录。"
        if self.current_lock is None:
            return False, "尚未持有筛选目录锁。"
        if self.recovery_rows:
            return False, "恢复扫描发现未处理问题。"
        if self.fast_index is None or not getattr(self.fast_index, "ready_for_commit", False):
            return False, "快速索引（FastReviewIndex）尚未就绪。"
        if self.audit_summary is None:
            return False, "完整校核尚未完成。"
        if getattr(self.audit_summary, "blocking_errors", []):
            return False, "完整校核存在阻断错误。"
        if not self.logger.can_write_transaction_log():
            return False, "日志目录不可写。"
        return True, ""

    def auto_enable_safe_gate_if_ready(self) -> None:
        if self.safe_gate_enabled:
            return
        if not self.auto_move_armed:
            self.set_nav_status("已就绪；请确认启动说明后启用自动移动")
            return
        ok, reason = self.can_enable_safe_gate()
        if ok:
            self.set_safe_gate_enabled("auto_ready")
            self.set_nav_status("自动移动已开启；单击/数字键直接提交")
            return
        self.safe_gate_enabled = False
        self.update_safe_gate()
        self.set_nav_status(f"只读预览：{reason}")
        self.add_recent(f"自动移动暂未启用：{reason}")

    def toggle_safe_gate(self) -> None:
        if self.safe_gate_enabled:
            self.safe_gate_enabled = False
            self.auto_move_armed = False
            self.logger.event("safe_gate_disabled", note="existing move queue will finish")
            self.add_recent("文件移动已关闭；已入队任务会继续完成。")
            self.update_safe_gate()
            return
        self.auto_move_armed = True
        ok, reason = self.can_enable_safe_gate()
        if ok:
            self.set_safe_gate_enabled("manual")
        else:
            self.update_safe_gate()
            self.show_reason(f"自动移动已准备，但当前还不能提交：{reason}")

    def enable_safe_gate_for_tests(self) -> bool:
        self.auto_move_armed = True
        ok, reason = self.can_enable_safe_gate()
        if ok:
            self.set_safe_gate_enabled("test")
            return True
        self.logger.event("safe_gate_enable_blocked", reason=reason)
        return False

    def set_safe_gate_enabled(self, source: str) -> None:
        self.safe_gate_enabled = True
        self.logger.event("safe_gate_enabled", source=source, review_dir=str(self.current_review_dir))
        self.add_recent("Safe Gate 已开启：单击或数字键将直接提交当前组。")
        self.update_safe_gate()

    def update_safe_gate(self) -> None:
        if self.safe_gate_enabled:
            self.status_badge.setText("文件移动已启用")
            self.status_badge.setProperty("enabledMoves", True)
            self.safe_gate_btn.setText("自动移动：暂停")
        else:
            self.status_badge.setText("自动移动准备中" if self.auto_move_armed else "只读预览")
            self.status_badge.setProperty("enabledMoves", False)
            self.safe_gate_btn.setText("自动移动：开启")
        self.status_badge.setToolTip(self.status_badge.text())
        self.status_badge.style().unpolish(self.status_badge)
        self.status_badge.style().polish(self.status_badge)
        self.update_commit_enabled()

    def dry_run_transaction(self) -> tuple[Any | None, str]:
        if self.fast_index is None or self.selected_card_index is None or not self.current_groups:
            return None, "尚未选择图片。"
        prefix, members = self.current_groups[self.current_group_index]
        selected = Path(members[self.selected_card_index])
        try:
            transaction = self.core.prepare_transaction_from_fast_index(self.fast_index, prefix, selected)
        except Exception as exc:
            return None, str(exc)
        done_count = len([op for op in transaction.operations if op.role == "done"])
        out_count = len([op for op in transaction.operations if op.role == "out"])
        return transaction, f"selected image/label -> done: {done_count}; variant images/labels -> out: {out_count}; target conflict check: PASS"

    def commit_selected(self) -> None:
        started = time.perf_counter()
        reason = self.disabled_reason()
        if reason:
            self.show_reason(reason)
            return
        transaction, summary = self.dry_run_transaction()
        if transaction is None:
            self.add_issue("错误", "", "DRY_RUN_FAILED", summary, "检查标签唯一性和目标冲突。")
            return
        self.logger.event("dry_run_transaction_passed", prefix=transaction.prefix, selected_stem=transaction.selected_stem, summary=summary)
        task_id = len(self.move_runner.tasks) + 1
        task = self.core.QueuedMoveTask(
            task_id=task_id,
            review_dir=self.current_review_dir,
            prefix=transaction.prefix,
            selected_stem=transaction.selected_stem,
            transaction=transaction,
        )
        self.move_runner.enqueue(task)
        self.optimistic_transaction_ids.add(transaction.transaction_id)
        self.add_recent(f"已入队并切到下一组：{transaction.prefix}")
        self.update_queue_model()
        try:
            self.fast_index.apply_queued_transaction(transaction)
            self.current_groups = self.fast_index.selectable_groups()
            self.current_group_index = min(self.current_group_index, max(0, len(self.current_groups) - 1))
            self.render_current_group()
            self.update_formula()
        except Exception as exc:
            self.add_issue("错误", transaction.prefix, "OPTIMISTIC_UPDATE_FAILED", str(exc), "等待后台任务完成后重新打开目录。")
        self.logger.perf("commit_selected_enqueued", started, prefix=transaction.prefix)

    def poll_move_events(self) -> None:
        if self.move_runner is None:
            return
        changed = False
        while True:
            try:
                event_name, task = self.move_event_queue.get_nowait()
            except queue.Empty:
                break
            changed = True
            self.add_recent(f"队列 {event_name}: {task.prefix} ({task.status})")
            if event_name == "moved":
                self.last_committed_transaction = task.transaction
                self.optimistic_transaction_ids.discard(getattr(task.transaction, "transaction_id", ""))
            elif event_name == "failed":
                self.optimistic_transaction_ids.discard(getattr(task.transaction, "transaction_id", ""))
                self.add_issue("错误", task.prefix, "MOVE_FAILED", task.error, "打开恢复中心并检查文件系统。")
            self.move_event_queue.task_done()
        if changed:
            self.update_queue_model()
            self.update_kpis()
            self.undo_btn.setEnabled(self.can_undo())

    def can_undo(self) -> bool:
        if self.last_committed_transaction is None or self.move_runner is None:
            return False
        if self.move_runner.blocked_error:
            return False
        return self.move_runner.work_queue.empty()

    def undo_last_transaction(self) -> None:
        if not self.can_undo():
            self.show_reason("撤销需要后台队列空闲，且存在上一组成功事务。")
            return
        transaction = self.last_committed_transaction
        undo_prefix = getattr(transaction, "prefix", "")
        self.undo_btn.setEnabled(False)
        self.commit_btn.setEnabled(False)
        try:
            self.core.undo_transaction(transaction)
            self.last_committed_transaction = None
            self.refresh_current_review_after_undo(undo_prefix)
            self.add_recent("上一组已撤销；当前筛选目录已原地刷新。")
            self.set_nav_status("撤销完成：当前目录已刷新")
            self.logger.event("undo_completed_in_place", prefix=undo_prefix, review_dir=str(self.current_review_dir))
        except Exception as exc:
            self.add_issue("错误", "", "UNDO_FAILED", str(exc), "进入恢复中心排查。")
        finally:
            self.update_queue_model()
            self.update_kpis()
            self.undo_btn.setEnabled(self.can_undo())
            self.update_commit_enabled()

    def refresh_current_review_after_undo(self, preferred_prefix: str = "") -> None:
        if self.core is None or self.current_review_dir is None:
            return
        self.set_progress("撤销完成，正在刷新当前目录", preferred_prefix or str(self.current_review_dir), target="nav_chip")
        index = self.core.build_fast_review_index(self.current_review_dir)
        summary, rows = self.core.audit_review_dir(self.current_review_dir, create_missing=False)
        self.fast_index = index
        self.audit_summary = summary
        self.audit_rows = list(rows)
        self.recovery_rows = []
        self.current_groups = index.selectable_groups()
        self.current_group_index = 0
        if preferred_prefix:
            for idx, (prefix, _members) in enumerate(self.current_groups):
                if prefix == preferred_prefix:
                    self.current_group_index = idx
                    break
        self.selected_card_index = None
        self.update_issues_from_audit()
        self.update_formula()
        self.render_current_group()
        self.overlay.hide()
        self.update_safe_gate()
        self.auto_enable_safe_gate_if_ready()

    def export_current_audit(self) -> None:
        if self.current_review_dir is None:
            self.show_reason("尚未打开筛选目录。")
            return
        try:
            path = self.facade.export_audit(self.current_review_dir)
            self.add_recent(f"校核报告已导出：{path}")
            QMessageBox.information(self, "导出完成", str(path))
        except Exception as exc:
            self.add_issue("错误", "", "EXPORT_FAILED", str(exc), "检查 Audit_Reports 目录权限。")

    def update_issues_from_audit(self) -> None:
        rows: list[list[Any]] = []
        summary = self.audit_summary
        if summary is not None:
            for err in getattr(summary, "errors", []):
                rows.append(["错误", "", "AUDIT_ERROR", err, "检查异常 prefix 与文件。"])
            for warn in getattr(summary, "warnings", []):
                rows.append(["警告", "", "AUDIT_WARNING", warn, "可继续筛选，但建议后续校核。"])
        self.issue_model.set_rows(rows)

    def add_issue(self, severity: str, prefix: str, code: str, message: str, suggestion: str) -> None:
        rows = self.issue_model.rows + [[severity, prefix, code, message, suggestion]]
        self.issue_model.set_rows(rows)

    def add_recent(self, text: str) -> None:
        rows = self.recent_model.rows[-80:] + [[datetime.now().strftime("%H:%M:%S"), text]]
        self.recent_model.set_rows(rows)

    def update_formula(self) -> None:
        s = self.audit_summary
        if s is None:
            self.formula_text.setText("完整校核尚未完成。")
            return
        raw_n = getattr(s, "group_size", getattr(s, "group_size_n", 0))
        if raw_n == 0:
            self.formula_text.setText(
                "Auto/Mixed: 非标准目录名，按每个 .rf. prefix 的实际成员数提交。\n"
                f"Root: {s.root_image_count} images / {s.root_prefix_count} prefixes\n"
                f"Selectable: {getattr(s, 'selectable_group_count', 0)} groups\n"
                f"Done: {s.done_image_count} images / {s.done_prefix_count} prefixes\n"
                f"Out actual: {s.out_image_count}\n"
                f"Label Sync: {self.label_sync_state(s)}"
            )
            return
        n = raw_n or getattr(s, "expected_out_per_done_group", 0) + 1
        self.formula_text.setText(
            f"Root: {s.root_image_count} images = {s.root_prefix_count} groups × {n}\n"
            f"Done: {s.done_image_count} images / {s.done_prefix_count} prefixes\n"
            f"Out expected: {s.done_prefix_count} × ({n} - 1) = {s.done_prefix_count * max(0, n - 1)}\n"
            f"Out actual: {s.out_image_count}\n"
            f"Label Sync: {self.label_sync_state(s)}"
        )

    @staticmethod
    def label_sync_state(summary: Any) -> str:
        if getattr(summary, "blocking_errors", []) or getattr(summary, "missing_label_stem_count", 0) or getattr(summary, "orphan_label_stem_count", 0):
            return "ERROR"
        if getattr(summary, "root_image_count", 0) > 0:
            return "IN_PROGRESS_SYNCED"
        return "PASS"

    def update_kpis(self) -> None:
        s = self.audit_summary or getattr(self.fast_index, "audit_counts", None) or getattr(self.quick_index, "audit_counts", None)
        if s is not None:
            self.kpi_labels["root"].setText(str(getattr(s, "root_prefix_count", 0)))
            self.kpi_labels["done"].setText(str(getattr(s, "done_prefix_count", 0)))
            self.kpi_labels["out"].setText(str(getattr(s, "out_image_count", 0)))
            self.kpi_labels["sync"].setText(self.label_sync_state(s))
        self.kpi_labels["current"].setText(f"{self.current_group_index + 1}/{len(self.current_groups)}" if self.current_groups else "0")
        self.kpi_labels["queue"].setText(str(len(self.move_runner.tasks) if self.move_runner else 0))

    def update_queue_model(self) -> None:
        if self.move_runner is None:
            return
        rows = [[task.task_id, task.prefix, task.selected_stem, task.status, task.error] for task in self.move_runner.tasks.values()]
        self.queue_model.set_rows(rows)

    def update_context(self) -> None:
        self.context_full_text = f"ID: {self.id_root or '未选择'} | 筛选目录: {self.current_review_dir or '未选择'}"
        self.set_elided_label(self.context_label, self.context_full_text)

    def show_shortcuts(self) -> None:
        QMessageBox.information(
            self,
            "快捷键",
            "1-9：按小键盘映射选择/提交\nEnter：提交当前选中\nEsc：清除选择\nCtrl+Z：撤销上一组\nSpace：打开 100% 原图查看器\n?：显示本说明",
        )

    def closeEvent(self, event: QCloseEvent) -> None:
        self.release_lock()
        if self.move_runner is not None:
            self.move_runner.stop()
        super().closeEvent(event)

    def release_lock(self) -> None:
        if self.current_lock is not None:
            try:
                self.current_lock.release()
            except Exception:
                pass
            self.current_lock = None

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if Qt.Key_1 <= event.key() <= Qt.Key_9:
            self.select_by_key(str(event.key() - Qt.Key_0))
            return
        super().keyPressEvent(event)


def create_app(argv: list[str] | None = None) -> QApplication:
    if QT_IMPORT_ERROR is not None:
        raise RuntimeError(QT_IMPORT_ERROR)
    app = QApplication.instance()
    if app is None:
        app = QApplication(argv or [sys.argv[0]])
    app.setApplicationName("CIVL7009 Source Group Picker V2.2.4")
    return app


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CIVL7009 图源筛选器 V2.2.4")
    parser.add_argument("--run-mode", default="")
    parser.add_argument("--smoke-open", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    app = create_app([sys.argv[0]])
    window = MainWindow(run_mode=args.run_mode or "gui_production")
    window.show()
    if args.smoke_open:
        app.processEvents()
        window.close()
        app.processEvents()
        return 0
    return app.exec()
