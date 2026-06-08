from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from .assets import AssetService
from .core import PickerCoreFacade
from .manual_objects import (
    ManualGroupSummary,
    ManualObjectGroup,
    ManualObjectItem,
    ManualObjectsFilter,
    ManualObjectsIndexResult,
    ManualObjectsIndexService,
    ManualObjectsService,
)
from .paths import PROGRAMME_DIR, RUNTIME_LOG_ROOT
from .version import PROGRAMME_VERSION, UI_VERSION

QT_IMPORT_ERROR: str | None = None
try:
    from PySide6.QtCore import QAbstractTableModel, QModelIndex, QObject, QRunnable, Qt, QThreadPool, QTimer, Signal, Slot
    from PySide6.QtGui import QImage, QKeySequence, QPixmap, QShortcut
    from PySide6.QtSvgWidgets import QSvgWidget
    from PySide6.QtWidgets import (
        QApplication,
        QCheckBox,
        QComboBox,
        QFileDialog,
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QScrollArea,
        QSizePolicy,
        QSplitter,
        QStackedWidget,
        QTableView,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )
except Exception as exc:  # pragma: no cover
    QT_IMPORT_ERROR = str(exc)


class TableModel(QAbstractTableModel):
    def __init__(self, headers: list[str], rows: list[list[Any]] | None = None) -> None:
        super().__init__()
        self.headers = headers
        self.rows = rows or []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self.headers)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid():
            return None
        if role in {Qt.DisplayRole, Qt.ToolTipRole}:
            try:
                return str(self.rows[index.row()][index.column()])
            except Exception:
                return ""
        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole) -> Any:  # noqa: N802
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.headers[section]
        return None

    def set_rows(self, rows: list[list[Any]]) -> None:
        self.beginResetModel()
        self.rows = rows
        self.endResetModel()


class V3Logger:
    def __init__(self, run_mode: str) -> None:
        self.run_mode = run_mode
        self.started_perf = time.perf_counter()
        self.run_id = datetime.now().strftime("%Y%m%d%H%M%S%f")[:-3]
        subdir = {"test": "Test", "debug": "Debug", "audit_only": "AuditOnly"}.get(run_mode, "Production")
        self.log_dir = RUNTIME_LOG_ROOT / subdir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.log_dir / f"picker_events_{PROGRAMME_VERSION}_{self.run_id}.jsonl"
        self._file = self.path.open("a", encoding="utf-8", buffering=1)

    def event(self, event: str, **payload: Any) -> None:
        row = {
            "timestamp": datetime.now().isoformat(timespec="milliseconds"),
            "elapsed_ms": round((time.perf_counter() - self.started_perf) * 1000, 3),
            "event": event,
            "programme_version": PROGRAMME_VERSION,
            "ui_version": UI_VERSION,
            "run_mode": self.run_mode,
        }
        row.update(payload)
        self._file.write(json.dumps(row, ensure_ascii=False) + "\n")


class ManualIndexSignals(QObject):
    done = Signal(int, object)
    error = Signal(int, str)


class ManualIndexWorker(QRunnable):
    def __init__(self, generation: int, root: Path) -> None:
        super().__init__()
        self.generation = generation
        self.root = root
        self.signals = ManualIndexSignals()

    @Slot()
    def run(self) -> None:
        try:
            result = ManualObjectsIndexService(self.root).load_group_summaries()
            self.signals.done.emit(self.generation, result)
        except Exception as exc:
            self.signals.error.emit(self.generation, str(exc))


class ManualGroupSignals(QObject):
    done = Signal(int, object, object)
    error = Signal(int, object, str)


class ManualGroupWorker(QRunnable):
    def __init__(self, generation: int, service: ManualObjectsIndexService, summary: ManualGroupSummary) -> None:
        super().__init__()
        self.generation = generation
        self.service = service
        self.summary = summary
        self.signals = ManualGroupSignals()

    @Slot()
    def run(self) -> None:
        try:
            group = self.service.load_group_from_summary(self.summary)
            self.signals.done.emit(self.generation, self.summary, group)
        except Exception as exc:
            self.signals.error.emit(self.generation, self.summary, str(exc))


class ThumbnailSignals(QObject):
    done = Signal(int, str, object)
    error = Signal(int, str, str)


class ThumbnailWorker(QRunnable):
    def __init__(self, generation: int, item_id: str, image_path: Path, max_size: tuple[int, int] = (430, 250)) -> None:
        super().__init__()
        self.generation = generation
        self.item_id = item_id
        self.image_path = image_path
        self.max_size = max_size
        self.signals = ThumbnailSignals()

    @Slot()
    def run(self) -> None:
        try:
            import io
            from PIL import Image

            with Image.open(self.image_path) as image:
                image = image.convert("RGB")
                image.thumbnail(self.max_size)
                buffer = io.BytesIO()
                image.save(buffer, format="PNG")
            self.signals.done.emit(self.generation, self.item_id, buffer.getvalue())
        except Exception as exc:
            self.signals.error.emit(self.generation, self.item_id, str(exc))


class ImageViewer(QFrame):
    def __init__(self, image_path: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent, Qt.Window)
        self.setWindowTitle(f"100% 原图查看 - {image_path.name}")
        self.resize(920, 720)
        layout = QVBoxLayout(self)
        label = QLabel()
        label.setAlignment(Qt.AlignCenter)
        label.setPixmap(QPixmap(str(image_path)))
        scroll = QScrollArea()
        scroll.setWidget(label)
        layout.addWidget(scroll)


class SourceImageCard(QFrame):
    selected = Signal(int)
    activated = Signal(int)

    def __init__(self, index: int, key_text: str, image_path: Path) -> None:
        super().__init__()
        self.index = index
        self.image_path = image_path
        self.setObjectName("imageCard")
        self.setProperty("selectedState", "false")
        self.setMinimumWidth(230)
        self.setMinimumHeight(300)
        layout = QVBoxLayout(self)
        header = QHBoxLayout()
        number = QLabel(key_text)
        number.setObjectName("cardNumber")
        self.target_label = QLabel("预览")
        self.target_label.setObjectName("statusChip")
        self.target_label.setProperty("selectedState", "false")
        header.addWidget(number)
        header.addStretch(1)
        header.addWidget(self.target_label)
        layout.addLayout(header)
        self.preview = QLabel()
        self.preview.setObjectName("imagePreview")
        self.preview.setProperty("selectedState", "false")
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setMinimumHeight(210)
        layout.addWidget(self.preview, 1)
        self.name_label = QLabel(image_path.name)
        self.name_label.setObjectName("cardFilename")
        self.name_label.setWordWrap(True)
        self.status_label = QLabel("Label OK | Target: done/out")
        self.status_label.setObjectName("cardStatus")
        layout.addWidget(self.name_label)
        layout.addWidget(self.status_label)
        self.load_thumbnail()

    def load_thumbnail(self) -> None:
        pixmap = QPixmap(str(self.image_path))
        if pixmap.isNull():
            self.preview.setText("图片无法加载")
            return
        scaled = pixmap.scaled(420, 260, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.preview.setPixmap(scaled)
        self.status_label.setText(f"{pixmap.width()}×{pixmap.height()} | Label OK | Target: done/out")

    def set_selected(self, selected: bool) -> None:
        self.setProperty("selectedState", "true" if selected else "false")
        self.preview.setProperty("selectedState", "true" if selected else "false")
        self.target_label.setProperty("selectedState", "true" if selected else "false")
        self.target_label.setText("已选图源预览" if selected else "预览")
        for widget in (self, self.preview, self.target_label):
            widget.style().unpolish(widget)
            widget.style().polish(widget)
            widget.update()

    def mousePressEvent(self, event: Any) -> None:
        self.selected.emit(self.index)

    def mouseDoubleClickEvent(self, event: Any) -> None:
        self.activated.emit(self.index)


class ManualObjectCard(QFrame):
    selected = Signal(str)
    activated = Signal(str)

    def __init__(self, item: ManualObjectItem, index: int) -> None:
        super().__init__()
        self.item = item
        self.index = index
        self.setObjectName("manualObjectCard")
        self.setProperty("state", item.selection_state)
        self.setMinimumWidth(250)
        self.setMinimumHeight(330)
        layout = QVBoxLayout(self)
        header = QHBoxLayout()
        self.number_label = QLabel(str(index + 1) if index < 9 else "•")
        self.number_label.setObjectName("cardNumber")
        self.state_chip = QLabel(item.selection_state)
        self.state_chip.setObjectName("stateChip")
        header.addWidget(self.number_label)
        header.addWidget(QLabel(f"{item.dataset_id} | {item.item_id}"))
        header.addStretch(1)
        header.addWidget(self.state_chip)
        layout.addLayout(header)
        self.preview = QLabel()
        self.preview.setObjectName("imagePreview")
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setMinimumHeight(210)
        layout.addWidget(self.preview, 1)
        self.name_label = QLabel(item.image_filename)
        self.name_label.setWordWrap(True)
        self.meta_label = QLabel(f"{item.width}×{item.height} | label {item.label_line_count} 行 | class {','.join(map(str, item.label_class_set))}")
        self.meta_label.setObjectName("cardStatus")
        self.metrics_label = QLabel(self.metrics_text(item.metrics))
        self.metrics_label.setObjectName("cardStatus")
        self.metrics_label.setWordWrap(True)
        layout.addWidget(self.name_label)
        layout.addWidget(self.meta_label)
        layout.addWidget(self.metrics_label)
        self.preview.setText("缩略图加载中...")
        self.refresh_state(item.selection_state)

    @staticmethod
    def metrics_text(metrics: dict[str, Any]) -> str:
        if not metrics:
            return "metrics: none"
        parts = [f"{key}={value}" for key, value in list(metrics.items())[:4]]
        return "metrics: " + "; ".join(parts)

    def load_thumbnail(self) -> None:
        pixmap = QPixmap(str(self.item.image_path))
        if pixmap.isNull():
            self.preview.setText("图片无法加载")
            return
        self.preview.setPixmap(pixmap.scaled(430, 250, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def set_thumbnail_bytes(self, payload: bytes) -> None:
        image = QImage.fromData(payload)
        if image.isNull():
            self.preview.setText("图片无法加载")
            return
        self.preview.setPixmap(QPixmap.fromImage(image))

    def refresh_state(self, state: str) -> None:
        self.item.selection_state = state
        self.setProperty("state", state)
        self.state_chip.setText({"KEEP": "保留 KEEP", "REMOVE": "移除 REMOVE", "UNDECIDED": "未决"}.get(state, state))
        self.state_chip.setProperty("state", state)
        for widget in (self, self.state_chip):
            widget.style().unpolish(widget)
            widget.style().polish(widget)
            widget.update()

    def mousePressEvent(self, event: Any) -> None:
        self.selected.emit(self.item.item_id)

    def mouseDoubleClickEvent(self, event: Any) -> None:
        self.activated.emit(self.item.item_id)


class MainWindow(QMainWindow):
    def __init__(self, run_mode: str = "gui_production") -> None:
        super().__init__()
        if QT_IMPORT_ERROR:
            raise RuntimeError(QT_IMPORT_ERROR)
        self.run_mode = run_mode
        self.assets = AssetService()
        self.assets.ensure_assets()
        self.logger = V3Logger(run_mode)
        self.facade = PickerCoreFacade()
        self.core = self.facade.core if self.facade.report.ok else None
        self.source_move_queue: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.source_runner = self.core.BackgroundMoveRunner(self.source_move_queue) if self.core else None
        self.current_review_dir: Path | None = None
        self.current_lock: Any | None = None
        self.fast_index: Any | None = None
        self.audit_summary: Any | None = None
        self.current_groups: list[tuple[str, list[Path]]] = []
        self.current_group_index = 0
        self.source_selected_index: int | None = None
        self.source_cards: list[SourceImageCard] = []
        self.key_to_source_card: dict[str, int] = {}
        self.safe_gate_enabled = False
        self.last_committed_transaction: Any | None = None

        self.thread_pool = QThreadPool.globalInstance()
        self.manual_root: Path | None = None
        self.manual_service: ManualObjectsService | None = None
        self.manual_index_service: ManualObjectsIndexService | None = None
        self.manual_index_result: ManualObjectsIndexResult | None = None
        self.manual_all_summaries: list[ManualGroupSummary] = []
        self.manual_filtered_summaries: list[ManualGroupSummary] = []
        self.manual_row_summary_map: list[ManualGroupSummary] = []
        self.manual_page = 0
        self.manual_page_size = 500
        self.manual_generation = 0
        self.manual_group_cache: dict[str, ManualObjectGroup] = {}
        self.manual_prefetch_after = 5
        self.current_manual_group: ManualObjectGroup | None = None
        self.current_manual_summary: ManualGroupSummary | None = None
        self.manual_cards: list[ManualObjectCard] = []
        self.manual_cards_by_item: dict[str, ManualObjectCard] = {}
        self.manual_thumbnail_cache: dict[tuple[str, int, int], bytes] = {}
        self.manual_thumbnail_pending: set[str] = set()
        self.manual_thumbnail_expected = 0
        self.manual_thumbnail_done = 0
        self.manual_thumbnail_failed: dict[str, str] = {}
        self.manual_thumbnail_workers: dict[str, ThumbnailWorker] = {}
        self.manual_multi_keep = False

        self.source_review_model = TableModel(["目录", "Root", "Done", "异常", "标签同步"])
        self.source_issue_model = TableModel(["等级", "Prefix", "代码", "说明", "建议"])
        self.source_queue_model = TableModel(["任务", "Prefix", "选中", "状态", "错误"])
        self.manual_group_model = TableModel(["Reason", "N", "Group", "状态", "行数", "数据集", "类别", "异常"])
        self.manual_issue_model = TableModel(["等级", "代码", "Item", "说明"])

        self.setWindowTitle(f"CIVL7009 Source Group Picker {UI_VERSION}")
        self.resize(1660, 950)
        self.setMinimumSize(1366, 768)
        self.build_ui()
        self.apply_style()
        self.install_shortcuts()
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self.poll_source_moves)
        self.poll_timer.start(150)
        self.logger.event("app_started")

    def build_ui(self) -> None:
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)
        layout.addWidget(self.build_workflow_tabs())
        self.stack = QStackedWidget()
        self.stack.addWidget(self.build_source_page())
        self.stack.addWidget(self.build_manual_objects_page())
        self.stack.addWidget(self.build_diagnostics_page())
        layout.addWidget(self.stack, 1)
        self.setCentralWidget(root)

    def build_workflow_tabs(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("workflowBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(10, 8, 10, 8)
        title = QLabel("CIVL7009 V3.0.2")
        title.setObjectName("appTitle")
        layout.addWidget(title)
        self.workflow_buttons: list[QPushButton] = []
        labels = ["图源组筛选（Source Group Review）", "跨库候选复核（Manual Objects Review）", "诊断与设置（Diagnostics & Settings）"]
        for index, label in enumerate(labels):
            button = QPushButton(label)
            button.setObjectName("workflowButton")
            button.setCheckable(True)
            button.clicked.connect(lambda _=False, i=index: self.set_workflow(i))
            layout.addWidget(button)
            self.workflow_buttons.append(button)
        layout.addStretch(1)
        self.global_status = QLabel("就绪")
        self.global_status.setObjectName("statusChip")
        layout.addWidget(self.global_status)
        self.set_workflow(0)
        return bar

    def set_workflow(self, index: int) -> None:
        if hasattr(self, "stack"):
            self.stack.setCurrentIndex(index)
        for i, button in enumerate(getattr(self, "workflow_buttons", [])):
            button.setChecked(i == index)
        self.global_status.setText(["图源组筛选模式", "Manual Objects 复核模式", "诊断与设置"][index])

    def build_source_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        command = QFrame()
        command.setObjectName("commandBar")
        cmd = QHBoxLayout(command)
        self.choose_id_btn = QPushButton("选择 ID 根目录")
        self.choose_review_btn = QPushButton("直接选择筛选目录")
        self.export_btn = QPushButton("导出校核")
        self.undo_btn = QPushButton("撤销上一组")
        self.undo_btn.setEnabled(False)
        self.safe_btn = QPushButton("自动移动：开启")
        self.source_status = QLabel("只读预览")
        self.source_status.setObjectName("statusChip")
        for widget in [self.choose_id_btn, self.choose_review_btn, self.export_btn, self.undo_btn, self.safe_btn]:
            cmd.addWidget(widget)
        cmd.addStretch(1)
        cmd.addWidget(self.source_status)
        layout.addWidget(command)
        self.choose_id_btn.clicked.connect(self.choose_id_root)
        self.choose_review_btn.clicked.connect(self.choose_review_dir)
        self.export_btn.clicked.connect(self.export_current_audit)
        self.undo_btn.clicked.connect(self.undo_last_transaction)
        self.safe_btn.clicked.connect(self.toggle_safe_gate)

        splitter = QSplitter(Qt.Horizontal)
        left = QFrame()
        left.setObjectName("glassPanel")
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("目录大盘（Review Board）"))
        self.source_review_table = QTableView()
        self.source_review_table.setModel(self.source_review_model)
        self.source_review_table.doubleClicked.connect(self.open_review_from_board)
        left_layout.addWidget(self.source_review_table)
        splitter.addWidget(left)

        center = QFrame()
        center.setObjectName("stagePanel")
        center_layout = QVBoxLayout(center)
        self.source_empty = self.empty_widget("选择 ID 根目录，或直接选择 images/<review-folder> 筛选目录。", "empty_manual_objects.svg")
        center_layout.addWidget(self.source_empty)
        self.source_scroll = QScrollArea()
        self.source_scroll.setWidgetResizable(True)
        self.source_host = QWidget()
        self.source_grid = QGridLayout(self.source_host)
        self.source_grid.setSpacing(12)
        self.source_scroll.setWidget(self.source_host)
        center_layout.addWidget(self.source_scroll, 1)
        nav = QHBoxLayout()
        self.prev_btn = QPushButton("上一组")
        self.next_btn = QPushButton("下一组")
        self.commit_btn = QPushButton("提交当前选中")
        nav.addWidget(self.prev_btn)
        nav.addWidget(self.next_btn)
        nav.addStretch(1)
        nav.addWidget(self.commit_btn)
        center_layout.addLayout(nav)
        self.prev_btn.clicked.connect(lambda: self.step_source_group(-1))
        self.next_btn.clicked.connect(lambda: self.step_source_group(1))
        self.commit_btn.clicked.connect(self.commit_source_selected)
        splitter.addWidget(center)

        right = QFrame()
        right.setObjectName("glassPanel")
        right_layout = QVBoxLayout(right)
        right_layout.addWidget(QLabel("当前组检查器"))
        self.source_group_text = QTextEdit()
        self.source_group_text.setReadOnly(True)
        self.source_group_text.setMaximumHeight(150)
        right_layout.addWidget(self.source_group_text)
        right_layout.addWidget(QLabel("异常表"))
        self.source_issue_table = QTableView()
        self.source_issue_table.setModel(self.source_issue_model)
        right_layout.addWidget(self.source_issue_table)
        right_layout.addWidget(QLabel("后台队列"))
        self.source_queue_table = QTableView()
        self.source_queue_table.setModel(self.source_queue_model)
        right_layout.addWidget(self.source_queue_table)
        splitter.addWidget(right)
        splitter.setSizes([320, 920, 380])
        layout.addWidget(splitter, 1)
        return page

    def build_manual_objects_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        command = QFrame()
        command.setObjectName("commandBar")
        cmd = QHBoxLayout(command)
        self.choose_manual_btn = QPushButton("选择 Manual_Objects 根目录")
        self.export_manual_btn = QPushButton("导出选择汇总")
        self.open_group_btn = QPushButton("打开当前组文件夹")
        self.manual_root_label = QLabel("Manual_Objects: 未选择")
        self.manual_root_label.setObjectName("context")
        cmd.addWidget(self.choose_manual_btn)
        cmd.addWidget(self.export_manual_btn)
        cmd.addWidget(self.open_group_btn)
        cmd.addStretch(1)
        cmd.addWidget(self.manual_root_label)
        layout.addWidget(command)
        self.choose_manual_btn.clicked.connect(self.choose_manual_root)
        self.export_manual_btn.clicked.connect(self.export_manual_summary)
        self.open_group_btn.clicked.connect(self.open_current_manual_folder)

        filter_bar = QFrame()
        filter_bar.setObjectName("commandBar")
        filters = QHBoxLayout(filter_bar)
        filters.setContentsMargins(8, 6, 8, 6)
        self.reason_filter = QComboBox()
        self.reason_filter.addItem("全部 reason", "")
        for reason in [
            "SHA256_EXACT_IMAGE",
            "PIXEL_SHA256_EXACT_IMAGE",
            "PHASH_NEAR_STRONG",
            "DHASH_NEAR_STRONG",
            "ROTATION_AWARE_PHASH",
            "COMPOSITE_NEAR_HASH",
        ]:
            self.reason_filter.addItem(reason, reason)
        self.bucket_filter = QComboBox()
        self.bucket_filter.addItem("全部 N", "")
        self.status_filter = QComboBox()
        self.status_filter.addItem("全部状态", "")
        for status in ["未复核", "APPROVED", "SKIP", "AMBIGUOUS", "NEEDS_AGENT_CHECK"]:
            self.status_filter.addItem(status, status)
        self.dataset_filter = QLineEdit()
        self.dataset_filter.setPlaceholderText("dataset_id")
        self.class_filter = QLineEdit()
        self.class_filter.setPlaceholderText("class")
        self.copy_status_filter = QComboBox()
        self.copy_status_filter.addItem("全部 copy_status", "")
        self.copy_status_filter.addItem("COPIED_AND_VERIFIED", "COPIED_AND_VERIFIED")
        self.selection_filter = QComboBox()
        self.selection_filter.addItem("全部选择记录", "")
        self.selection_filter.addItem("未写入 selection", "missing")
        self.selection_filter.addItem("已有 selection", "has")
        self.prev_page_btn = QPushButton("上一页")
        self.next_page_btn = QPushButton("下一页")
        self.page_label = QLabel("0 / 0")
        self.auto_next_same_bucket_box = QCheckBox("保存后同 N 自动下一组")
        self.auto_next_same_bucket_box.setChecked(True)
        self.stay_after_save_box = QCheckBox("保存后停留当前组")
        for widget in [
            self.reason_filter,
            self.bucket_filter,
            self.status_filter,
            self.dataset_filter,
            self.class_filter,
            self.copy_status_filter,
            self.selection_filter,
            self.prev_page_btn,
            self.next_page_btn,
            self.page_label,
            self.auto_next_same_bucket_box,
            self.stay_after_save_box,
        ]:
            filters.addWidget(widget)
        filters.addStretch(1)
        layout.addWidget(filter_bar)
        for widget in [self.reason_filter, self.bucket_filter, self.status_filter, self.copy_status_filter, self.selection_filter]:
            widget.currentIndexChanged.connect(self.apply_manual_filters)
        self.dataset_filter.textChanged.connect(self.apply_manual_filters)
        self.class_filter.textChanged.connect(self.apply_manual_filters)
        self.prev_page_btn.clicked.connect(lambda: self.change_manual_page(-1))
        self.next_page_btn.clicked.connect(lambda: self.change_manual_page(1))

        splitter = QSplitter(Qt.Horizontal)
        left = QFrame()
        left.setObjectName("glassPanel")
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("Reason / Nxx / Group"))
        self.manual_group_table = QTableView()
        self.manual_group_table.setModel(self.manual_group_model)
        self.manual_group_table.clicked.connect(self.open_manual_group_from_table)
        left_layout.addWidget(self.manual_group_table)
        splitter.addWidget(left)

        center = QFrame()
        center.setObjectName("stagePanel")
        center_layout = QVBoxLayout(center)
        self.manual_empty = self.empty_widget("请选择 Manual_Objects 根目录。V3.0 只写 manual_selection.json，不治理主库。", "empty_manual_objects.svg")
        center_layout.addWidget(self.manual_empty)
        self.manual_scroll = QScrollArea()
        self.manual_scroll.setWidgetResizable(True)
        self.manual_host = QWidget()
        self.manual_grid = QGridLayout(self.manual_host)
        self.manual_grid.setSpacing(12)
        self.manual_scroll.setWidget(self.manual_host)
        center_layout.addWidget(self.manual_scroll, 1)
        actions = QHBoxLayout()
        self.multi_keep_box = QCheckBox("多保留模式")
        self.save_approved_btn = QPushButton("写入 APPROVED")
        self.save_skip_btn = QPushButton("标记 SKIP")
        self.save_ambiguous_btn = QPushButton("标记 AMBIGUOUS")
        self.save_needs_check_btn = QPushButton("标记 NEEDS_AGENT_CHECK")
        self.save_next_btn = QPushButton("+ 保存并下一组")
        self.clear_manual_btn = QPushButton("撤销本组未保存选择")
        for widget in [self.multi_keep_box, self.save_approved_btn, self.save_skip_btn, self.save_ambiguous_btn, self.save_needs_check_btn, self.save_next_btn, self.clear_manual_btn]:
            actions.addWidget(widget)
        center_layout.addLayout(actions)
        self.multi_keep_box.stateChanged.connect(self.on_manual_multi_keep_changed)
        self.save_approved_btn.clicked.connect(lambda: self.save_manual_selection("APPROVED"))
        self.save_skip_btn.clicked.connect(lambda: self.save_manual_selection("SKIP"))
        self.save_ambiguous_btn.clicked.connect(lambda: self.save_manual_selection("AMBIGUOUS"))
        self.save_needs_check_btn.clicked.connect(lambda: self.save_manual_selection("NEEDS_AGENT_CHECK"))
        self.save_next_btn.clicked.connect(lambda: self.save_manual_selection("APPROVED", force_next=True))
        self.clear_manual_btn.clicked.connect(self.clear_manual_selection)
        splitter.addWidget(center)

        right = QFrame()
        right.setObjectName("glassPanel")
        right_layout = QVBoxLayout(right)
        right_layout.addWidget(QLabel("Manifest Inspector"))
        self.manual_inspector = QTextEdit()
        self.manual_inspector.setReadOnly(True)
        self.manual_inspector.setMaximumHeight(220)
        right_layout.addWidget(self.manual_inspector)
        right_layout.addWidget(QLabel("Manual Objects Issue Table"))
        self.manual_issue_table = QTableView()
        self.manual_issue_table.setModel(self.manual_issue_model)
        right_layout.addWidget(self.manual_issue_table, 1)
        right_layout.addWidget(QLabel("Selection Summary"))
        self.selection_summary = QTextEdit()
        self.selection_summary.setReadOnly(True)
        self.selection_summary.setMaximumHeight(150)
        right_layout.addWidget(self.selection_summary)
        load_header = QHBoxLayout()
        load_header.addWidget(QLabel("预览加载状态"))
        self.refresh_preview_btn = QPushButton("刷新当前组预览")
        self.refresh_preview_btn.clicked.connect(self.refresh_current_manual_preview)
        load_header.addWidget(self.refresh_preview_btn)
        right_layout.addLayout(load_header)
        self.manual_load_status = QTextEdit()
        self.manual_load_status.setReadOnly(True)
        self.manual_load_status.setMaximumHeight(150)
        right_layout.addWidget(self.manual_load_status)
        splitter.addWidget(right)
        splitter.setSizes([340, 900, 420])
        layout.addWidget(splitter, 1)
        return page

    def build_diagnostics_page(self) -> QWidget:
        page = QFrame()
        page.setObjectName("glassPanel")
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("诊断与设置（Diagnostics & Settings）"))
        text = QTextEdit()
        text.setReadOnly(True)
        text.setText(
            f"UI version: {UI_VERSION}\n"
            f"Core ok: {self.facade.report.ok}\n"
            f"Core path: {self.facade.report.path}\n"
            f"Core SHA256: {self.facade.report.core_sha256}\n"
            f"Runtime log: {self.logger.path}\n"
            "Manual Objects 模式只写 manual_selection.json 与 _selection_history，不移动主库文件。"
        )
        layout.addWidget(text)
        art = QSvgWidget(str(self.assets.asset("manual_objects_pipeline.svg")))
        art.setMinimumHeight(360)
        layout.addWidget(art)
        return page

    def empty_widget(self, message: str, asset_name: str) -> QWidget:
        frame = QFrame()
        frame.setObjectName("emptyState")
        layout = QHBoxLayout(frame)
        art = QSvgWidget(str(self.assets.asset(asset_name)))
        art.setFixedSize(190, 116)
        label = QLabel(message)
        label.setWordWrap(True)
        layout.addWidget(art)
        layout.addWidget(label, 1)
        return frame

    def install_shortcuts(self) -> None:
        for key in list("123456789"):
            QShortcut(QKeySequence(key), self).activated.connect(lambda k=key: self.handle_number_key(k))
        QShortcut(QKeySequence("Return"), self).activated.connect(self.handle_enter)
        QShortcut(QKeySequence("Enter"), self).activated.connect(self.handle_enter)
        QShortcut(QKeySequence("Esc"), self).activated.connect(self.handle_escape)
        QShortcut(QKeySequence("Space"), self).activated.connect(self.handle_space)
        QShortcut(QKeySequence("Ctrl+Z"), self).activated.connect(self.undo_last_transaction)
        QShortcut(QKeySequence("?"), self).activated.connect(self.show_shortcuts)
        QShortcut(QKeySequence("A"), self).activated.connect(lambda: self.save_manual_selection("AMBIGUOUS"))
        QShortcut(QKeySequence("S"), self).activated.connect(lambda: self.save_manual_selection("SKIP"))
        QShortcut(QKeySequence("N"), self).activated.connect(lambda: self.save_manual_selection("NEEDS_AGENT_CHECK"))
        QShortcut(QKeySequence("+"), self).activated.connect(lambda: self.save_manual_selection("APPROVED", force_next=True))

    def choose_id_root(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "选择 YOLO 数据集 ID 根目录")
        if path:
            self.load_id_root(Path(path))

    def load_id_root(self, id_root: Path) -> None:
        if self.core is None:
            self.show_message("core 未加载，无法扫描 ID 根目录。")
            return
        try:
            dirs = self.facade.review_dirs_for_id_root(id_root)
            rows = []
            for review_dir in dirs:
                summary, _issues = self.facade.audit(review_dir)
                rows.append([
                    review_dir.name,
                    getattr(summary, "root_prefix_count", 0),
                    getattr(summary, "done_prefix_count", 0),
                    len(getattr(summary, "errors", [])),
                    getattr(summary, "label_sync_status", ""),
                ])
            self.source_review_model.set_rows(rows)
            self.source_review_dirs = dirs
            self.source_status.setText(f"已扫描 {len(dirs)} 个筛选目录")
            self.logger.event("id_root_loaded", id_root=str(id_root), review_dir_count=len(dirs))
        except Exception as exc:
            self.show_message(str(exc))

    def choose_review_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "选择 images/<review-folder> 筛选目录")
        if path:
            self.open_review_dir(Path(path))

    def open_review_from_board(self, index: QModelIndex) -> None:
        dirs = getattr(self, "source_review_dirs", [])
        if 0 <= index.row() < len(dirs):
            self.open_review_dir(dirs[index.row()])

    def open_review_dir(self, review_dir: Path) -> None:
        if self.core is None:
            self.show_message("core 未加载，无法打开筛选目录。")
            return
        try:
            self.current_review_dir = review_dir.resolve()
            if self.current_lock is not None:
                try:
                    self.current_lock.release()
                except Exception:
                    pass
            self.current_lock = self.core.ReviewDirLock(self.current_review_dir)
            self.current_lock.acquire()
            self.fast_index = self.facade.fast_index(self.current_review_dir)
            self.audit_summary, rows = self.facade.audit(self.current_review_dir)
            self.current_groups = self.fast_index.selectable_groups()
            self.current_group_index = 0
            self.safe_gate_enabled = bool(self.current_groups) and not getattr(self.audit_summary, "blocking_errors", [])
            self.update_source_issues()
            self.render_source_group()
            self.update_safe_state()
            self.logger.event("review_dir_opened", review_dir=str(self.current_review_dir), group_count=len(self.current_groups))
        except Exception as exc:
            self.show_message(str(exc))

    def render_source_group(self) -> None:
        self.clear_layout(self.source_grid)
        self.source_cards = []
        self.key_to_source_card = {}
        self.source_selected_index = None
        self.source_empty.setVisible(not self.current_groups)
        if not self.current_groups:
            self.source_group_text.setText("暂无可筛选组。")
            return
        prefix, members = self.current_groups[self.current_group_index]
        slots = self.facade.keypad_slots(len(members))
        for slot in slots:
            if slot.index >= len(members):
                continue
            key_text = slot.key or str(slot.index + 1)
            card = SourceImageCard(slot.index, key_text, Path(members[slot.index]))
            card.selected.connect(self.select_source_card)
            card.activated.connect(lambda idx: self.open_image_viewer(Path(self.current_groups[self.current_group_index][1][idx])))
            self.source_cards.append(card)
            self.source_grid.addWidget(card, slot.row, slot.col)
            if slot.key:
                self.key_to_source_card[slot.key] = slot.index
        self.source_group_text.setText(
            f"Prefix: {prefix}\n"
            f"组内图片: {len(members)}\n"
            f"当前组: {self.current_group_index + 1}/{len(self.current_groups)}\n"
            f"Safe Gate: {'ON 文件移动已启用' if self.safe_gate_enabled else 'OFF 只读预览'}"
        )

    def select_source_card(self, index: int) -> None:
        self.source_selected_index = index
        for card in self.source_cards:
            card.set_selected(card.index == index)
        if self.safe_gate_enabled:
            QTimer.singleShot(70, self.commit_source_selected)

    def commit_source_selected(self) -> None:
        if self.core is None or self.fast_index is None or self.source_selected_index is None or not self.current_groups:
            return
        if not self.safe_gate_enabled:
            self.show_message("当前为只读预览；目录未就绪或存在阻断问题。")
            return
        prefix, members = self.current_groups[self.current_group_index]
        try:
            selected = Path(members[self.source_selected_index])
            transaction = self.core.prepare_transaction_from_fast_index(self.fast_index, prefix, selected)
            task_id = len(self.source_runner.tasks) + 1
            task = self.core.QueuedMoveTask(task_id, self.current_review_dir, prefix, transaction.selected_stem, transaction)
            self.source_runner.enqueue(task)
            self.fast_index.apply_queued_transaction(transaction)
            self.current_groups = self.fast_index.selectable_groups()
            self.current_group_index = min(self.current_group_index, max(0, len(self.current_groups) - 1))
            self.source_queue_model.set_rows(self.source_queue_model.rows + [[task_id, prefix, transaction.selected_stem, "QUEUED", ""]])
            self.render_source_group()
        except Exception as exc:
            self.show_message(str(exc))

    def poll_source_moves(self) -> None:
        if self.source_runner is None:
            return
        changed = False
        while True:
            try:
                event_name, task = self.source_move_queue.get_nowait()
            except queue.Empty:
                break
            changed = True
            if event_name == "moved":
                self.last_committed_transaction = task.transaction
            elif event_name == "failed":
                self.source_issue_model.set_rows(self.source_issue_model.rows + [["错误", task.prefix, "MOVE_FAILED", task.error, "进入恢复流程排查"]])
            self.source_move_queue.task_done()
        if changed:
            self.undo_btn.setEnabled(self.can_undo())

    def can_undo(self) -> bool:
        return bool(self.last_committed_transaction and self.source_runner and self.source_runner.work_queue.empty() and not self.source_runner.blocked_error)

    def undo_last_transaction(self) -> None:
        if not self.can_undo():
            return
        try:
            transaction = self.last_committed_transaction
            self.core.undo_transaction(transaction)
            self.last_committed_transaction = None
            if self.current_review_dir:
                self.open_review_dir(self.current_review_dir)
            self.source_status.setText("撤销完成：当前目录已刷新")
        except Exception as exc:
            self.show_message(str(exc))

    def step_source_group(self, delta: int) -> None:
        if not self.current_groups:
            return
        self.current_group_index = max(0, min(len(self.current_groups) - 1, self.current_group_index + delta))
        self.render_source_group()

    def toggle_safe_gate(self) -> None:
        self.safe_gate_enabled = not self.safe_gate_enabled
        self.update_safe_state()

    def update_safe_state(self) -> None:
        self.safe_btn.setText("自动移动：暂停" if self.safe_gate_enabled else "自动移动：开启")
        self.source_status.setText("文件移动已启用" if self.safe_gate_enabled else "只读预览")

    def update_source_issues(self) -> None:
        rows = []
        summary = self.audit_summary
        if summary is not None:
            for err in getattr(summary, "errors", []):
                rows.append(["错误", "", "AUDIT_ERROR", err, "检查 prefix 与标签同步"])
            for warn in getattr(summary, "warnings", []):
                rows.append(["警告", "", "AUDIT_WARNING", warn, "可继续但建议复核"])
        self.source_issue_model.set_rows(rows)

    def export_current_audit(self) -> None:
        if self.current_review_dir is None:
            self.show_message("尚未打开筛选目录。")
            return
        try:
            path = self.facade.export_audit(self.current_review_dir)
            self.show_message(f"校核报告已导出：{path}")
        except Exception as exc:
            self.show_message(str(exc))

    def choose_manual_root(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "选择 Manual_Objects 根目录")
        if path:
            self.load_manual_root(Path(path))

    def load_manual_root(self, root: Path) -> None:
        self.manual_root = root.resolve()
        self.manual_generation += 1
        generation = self.manual_generation
        self.manual_service = ManualObjectsService(self.manual_root)
        self.manual_index_service = ManualObjectsIndexService(self.manual_root)
        self.manual_index_result = None
        self.manual_all_summaries = []
        self.manual_filtered_summaries = []
        self.manual_row_summary_map = []
        self.manual_group_cache = {}
        self.current_manual_group = None
        self.current_manual_summary = None
        self.manual_group_model.set_rows([])
        self.clear_layout(self.manual_grid)
        self.manual_empty.setVisible(True)
        self.manual_load_status.setText("正在读取 Manual Objects 全局 index；尚未加载任何图片预览。")
        self.manual_root_label.setText(f"Manual_Objects: {self.manual_root} | 正在读取全局 index...")
        self.logger.event("manual_objects_index_start", manual_root=str(self.manual_root))
        worker = ManualIndexWorker(generation, self.manual_root)
        worker.signals.done.connect(self.on_manual_index_done)
        worker.signals.error.connect(self.on_manual_index_error)
        self.thread_pool.start(worker)

    def on_manual_index_done(self, generation: int, result: ManualObjectsIndexResult) -> None:
        if generation != self.manual_generation:
            return
        self.manual_index_result = result
        self.manual_index_service = ManualObjectsIndexService(result.root)
        self.manual_service = ManualObjectsService(result.root)
        self.manual_all_summaries = result.summaries
        for summary in self.manual_all_summaries[: self.manual_page_size]:
            self.manual_index_service.refresh_summary_selection_status(summary)
        self.populate_manual_filter_options()
        self.apply_manual_filters()
        mode_text = "index 快速模式" if result.mode == "index" else "慢速兼容模式"
        warning = f" | {result.warning}" if result.warning else ""
        self.manual_root_label.setText(
            f"Manual_Objects: {result.root} | {mode_text} | groups={result.group_count:,} | rows={result.row_count:,} | {result.duration_ms:.1f} ms{warning}"
        )
        self.logger.event(
            "manual_objects_index_done",
            manual_root=str(result.root),
            mode=result.mode,
            group_count=result.group_count,
            row_count=result.row_count,
            duration_ms=round(result.duration_ms, 3),
        )
        if self.manual_row_summary_map:
            self.manual_inspector.setText("全局 index 已加载。请在左侧选择具体 Nxx/Gxxxxx 组后再加载该组图片预览。")
            self.manual_load_status.setText("等待选择具体候选组；未启动图片预览加载。")

    def on_manual_index_error(self, generation: int, error: str) -> None:
        if generation != self.manual_generation:
            return
        self.manual_root_label.setText(f"Manual_Objects: {self.manual_root} | index 读取失败")
        self.logger.event("manual_objects_index_failed", manual_root=str(self.manual_root), error=error)
        self.show_message(error)

    def populate_manual_filter_options(self) -> None:
        blocker = self.bucket_filter.blockSignals(True)
        current = self.bucket_filter.currentData()
        self.bucket_filter.clear()
        self.bucket_filter.addItem("全部 N", "")
        buckets = sorted({summary.size_bucket for summary in self.manual_all_summaries if summary.size_bucket}, key=lambda text: (len(text), text))
        for bucket in buckets:
            self.bucket_filter.addItem(bucket, bucket)
        if current:
            index = self.bucket_filter.findData(current)
            if index >= 0:
                self.bucket_filter.setCurrentIndex(index)
        self.bucket_filter.blockSignals(blocker)

    def current_manual_filters(self) -> ManualObjectsFilter:
        return ManualObjectsFilter(
            reason=str(self.reason_filter.currentData() or ""),
            bucket=str(self.bucket_filter.currentData() or ""),
            review_status=str(self.status_filter.currentData() or ""),
            dataset_id=self.dataset_filter.text().strip(),
            label_class=self.class_filter.text().strip(),
            copy_status=str(self.copy_status_filter.currentData() or ""),
            selection_presence=str(self.selection_filter.currentData() or ""),
        )

    def apply_manual_filters(self) -> None:
        if self.manual_index_service is None:
            return
        self.manual_page = 0
        self.manual_filtered_summaries = self.manual_index_service.filter_summaries(self.manual_all_summaries, self.current_manual_filters())
        self.render_manual_group_page()

    def change_manual_page(self, delta: int) -> None:
        if not self.manual_filtered_summaries:
            return
        max_page = max(0, (len(self.manual_filtered_summaries) - 1) // self.manual_page_size)
        self.manual_page = max(0, min(max_page, self.manual_page + delta))
        self.render_manual_group_page()

    def render_manual_group_page(self) -> None:
        if self.manual_index_service is None:
            return
        visible = self.manual_index_service.page_summaries(self.manual_filtered_summaries, self.manual_page, self.manual_page_size)
        for summary in visible:
            self.manual_index_service.refresh_summary_selection_status(summary)
        self.manual_row_summary_map = visible
        rows = [
            [
                summary.reason,
                summary.size_bucket,
                summary.group_folder,
                summary.selection_status,
                summary.copied_row_count,
                ",".join(summary.dataset_ids[:3]) + ("..." if len(summary.dataset_ids) > 3 else ""),
                "|".join(summary.label_class_set[:6]),
                summary.issue_count,
            ]
            for summary in visible
        ]
        self.manual_group_model.set_rows(rows)
        total = len(self.manual_filtered_summaries)
        max_page = max(1, (total + self.manual_page_size - 1) // self.manual_page_size)
        self.page_label.setText(f"{self.manual_page + 1} / {max_page} | {total:,} 组")
        self.manual_empty.setVisible(not bool(visible))

    def open_manual_group_from_table(self, index: QModelIndex) -> None:
        if 0 <= index.row() < len(self.manual_row_summary_map):
            self.open_manual_group_from_summary(self.manual_row_summary_map[index.row()])

    def open_manual_group(self, row: int) -> None:
        if 0 <= row < len(self.manual_row_summary_map):
            self.open_manual_group_from_summary(self.manual_row_summary_map[row])

    def open_manual_group_from_summary(self, summary: ManualGroupSummary) -> None:
        self.current_manual_summary = summary
        cached = self.manual_group_cache.get(summary.group_key)
        if cached is not None:
            self.current_manual_group = cached
            self.render_manual_group()
            self.prefetch_manual_after(summary)
            return
        if self.manual_index_service is None:
            return
        generation = self.manual_generation
        self.manual_inspector.setText(f"正在懒加载组 manifest...\n{summary.group_key}\n{summary.group_dir}")
        worker = ManualGroupWorker(generation, self.manual_index_service, summary)
        worker.signals.done.connect(self.on_manual_group_loaded)
        worker.signals.error.connect(self.on_manual_group_error)
        self.thread_pool.start(worker)

    def on_manual_group_loaded(self, generation: int, summary: ManualGroupSummary, group: ManualObjectGroup) -> None:
        if generation != self.manual_generation:
            return
        self.manual_group_cache[summary.group_key] = group
        self.current_manual_summary = summary
        self.current_manual_group = group
        self.render_manual_group()
        self.prefetch_manual_after(summary)
        self.logger.event("manual_objects_group_loaded", group_key=summary.group_key, item_count=len(group.items), issue_count=len(group.issues))

    def on_manual_group_error(self, generation: int, summary: ManualGroupSummary, error: str) -> None:
        if generation != self.manual_generation:
            return
        self.manual_issue_model.set_rows([["ERROR", "GROUP_LOAD_FAILED", "", error]])
        self.manual_inspector.setText(f"组加载失败:\n{summary.group_key}\n{error}")
        self.logger.event("manual_objects_group_load_failed", group_key=summary.group_key, error=error)

    def prefetch_manual_after(self, summary: ManualGroupSummary) -> None:
        if self.manual_index_service is None:
            return
        try:
            current_index = self.manual_filtered_summaries.index(summary)
        except ValueError:
            return
        generation = self.manual_generation
        for next_summary in self.manual_filtered_summaries[current_index + 1 : current_index + 1 + self.manual_prefetch_after]:
            if next_summary.group_key in self.manual_group_cache:
                continue
            worker = ManualGroupWorker(generation, self.manual_index_service, next_summary)
            worker.signals.done.connect(self.on_manual_prefetch_loaded)
            worker.signals.error.connect(lambda *_args: None)
            self.thread_pool.start(worker)

    def on_manual_prefetch_loaded(self, generation: int, summary: ManualGroupSummary, group: ManualObjectGroup) -> None:
        if generation != self.manual_generation:
            return
        self.manual_group_cache.setdefault(summary.group_key, group)

    def render_manual_group(self) -> None:
        self.clear_layout(self.manual_grid)
        self.manual_cards = []
        self.manual_cards_by_item = {}
        group = self.current_manual_group
        if group is None:
            self.manual_empty.setVisible(True)
            return
        self.manual_empty.setVisible(False)
        visible_items = group.items[:30]
        self.manual_thumbnail_expected = len(visible_items)
        self.manual_thumbnail_done = 0
        self.manual_thumbnail_failed = {}
        self.manual_thumbnail_pending = set()
        self.update_manual_load_status("准备加载当前组预览图。")
        for index, item in enumerate(visible_items):
            card = ManualObjectCard(item, index)
            card.selected.connect(self.select_manual_item)
            card.activated.connect(lambda item_id: self.open_manual_item_viewer(item_id))
            self.manual_cards.append(card)
            self.manual_cards_by_item[item.item_id] = card
            row, col = divmod(index, 3)
            self.manual_grid.addWidget(card, row, col)
            self.request_manual_thumbnail(item)
        if len(group.items) > len(visible_items):
            notice = QLabel(f"N20_PLUS 大组：先显示前 {len(visible_items)} 张，其余候选保持在 manifest 中，后续可继续展开。")
            notice.setObjectName("statusChip")
            self.manual_grid.addWidget(notice, (len(visible_items) + 2) // 3, 0, 1, 3)
        issue_rows = [[issue.severity, issue.code, issue.item_id, issue.message] for issue in group.issues]
        self.manual_issue_model.set_rows(issue_rows)
        self.manual_inspector.setText(
            f"group_key: {group.group_key}\n"
            f"reason: {group.reason}\n"
            f"bucket: {group.size_bucket}\n"
            f"dataset_ids: {', '.join(group.dataset_ids)}\n"
            f"claim_status: {group.claim_status}\n"
            f"items: {len(group.items)}\n"
            f"can_write_selection: {group.can_write_selection}\n"
            f"group_dir: {group.group_dir}"
        )
        self.update_selection_summary()

    def manual_thumbnail_key(self, item: ManualObjectItem) -> tuple[str, int, int]:
        try:
            stat = item.image_path.stat()
            return (str(item.image_path), stat.st_size, getattr(stat, "st_mtime_ns", int(stat.st_mtime * 1_000_000_000)))
        except Exception:
            return (str(item.image_path), 0, 0)

    def request_manual_thumbnail(self, item: ManualObjectItem) -> None:
        key = self.manual_thumbnail_key(item)
        cached = self.manual_thumbnail_cache.get(key)
        card = self.manual_cards_by_item.get(item.item_id)
        if cached is not None and card is not None:
            card.set_thumbnail_bytes(cached)
            self.manual_thumbnail_done += 1
            self.update_manual_load_status(f"使用缓存预览：{item.item_id}")
            return
        generation = self.manual_generation
        self.manual_thumbnail_pending.add(item.item_id)
        self.update_manual_load_status(f"正在后台加载预览：{item.item_id}")
        self.logger.event("manual_thumbnail_start", group_key=self.current_manual_group.group_key if self.current_manual_group else "", item_id=item.item_id, image_path=str(item.image_path))
        worker = ThumbnailWorker(generation, item.item_id, item.image_path)
        worker.signals.done.connect(lambda gen, item_id, payload, cache_key=key: self.on_manual_thumbnail_done(gen, item_id, payload, cache_key))
        worker.signals.error.connect(self.on_manual_thumbnail_error)
        self.manual_thumbnail_workers[item.item_id] = worker
        self.thread_pool.start(worker)

    def on_manual_thumbnail_done(self, generation: int, item_id: str, payload: bytes, cache_key: tuple[str, int, int]) -> None:
        if generation != self.manual_generation:
            return
        self.manual_thumbnail_cache[cache_key] = payload
        self.manual_thumbnail_pending.discard(item_id)
        self.manual_thumbnail_done += 1
        self.manual_thumbnail_workers.pop(item_id, None)
        card = self.manual_cards_by_item.get(item_id)
        if card is not None:
            card.set_thumbnail_bytes(payload)
        self.update_manual_load_status(f"预览已加载：{item_id}")
        self.logger.event("manual_thumbnail_done", group_key=self.current_manual_group.group_key if self.current_manual_group else "", item_id=item_id, bytes=len(payload))

    def on_manual_thumbnail_error(self, generation: int, item_id: str, error: str) -> None:
        if generation != self.manual_generation:
            return
        self.manual_thumbnail_pending.discard(item_id)
        self.manual_thumbnail_failed[item_id] = error
        self.manual_thumbnail_workers.pop(item_id, None)
        card = self.manual_cards_by_item.get(item_id)
        if card is not None:
            card.preview.setText(f"缩略图加载失败\n{error}")
        self.update_manual_load_status(f"预览加载失败：{item_id}")
        self.logger.event("manual_thumbnail_error", group_key=self.current_manual_group.group_key if self.current_manual_group else "", item_id=item_id, error=error)

    def update_manual_load_status(self, message: str = "") -> None:
        expected = self.manual_thumbnail_expected
        pending = len(self.manual_thumbnail_pending)
        failed = len(self.manual_thumbnail_failed)
        done = self.manual_thumbnail_done
        lines = [
            f"当前组预览：已完成 {done}/{expected}，待加载 {pending}，失败 {failed}",
        ]
        if message:
            lines.append(message)
        if self.current_manual_group:
            lines.append(f"group_key: {self.current_manual_group.group_key}")
        if self.manual_thumbnail_failed:
            lines.append("问题：")
            for item_id, error in list(self.manual_thumbnail_failed.items())[:6]:
                lines.append(f"- {item_id}: {error}")
        self.manual_load_status.setText("\n".join(lines))

    def refresh_current_manual_preview(self) -> None:
        group = self.current_manual_group
        if group is None:
            self.manual_load_status.setText("尚未打开候选组，无法刷新预览。")
            return
        for item in group.items[:30]:
            self.manual_thumbnail_cache.pop(self.manual_thumbnail_key(item), None)
        self.logger.event("manual_thumbnail_refresh_requested", group_key=group.group_key, visible_count=min(30, len(group.items)))
        self.render_manual_group()

    def select_manual_item(self, item_id: str) -> None:
        group = self.current_manual_group
        if group is None:
            return
        if self.manual_multi_keep:
            for item in group.items:
                if item.item_id == item_id:
                    item.selection_state = {"UNDECIDED": "KEEP", "KEEP": "REMOVE", "REMOVE": "UNDECIDED"}[item.selection_state]
                    break
        else:
            for item in group.items:
                item.selection_state = "KEEP" if item.item_id == item_id else "REMOVE"
        for card in self.manual_cards:
            card.refresh_state(card.item.selection_state)
        self.update_selection_summary()

    def on_manual_multi_keep_changed(self, state: int) -> None:
        self.manual_multi_keep = bool(state)
        if self.manual_multi_keep:
            self.auto_next_same_bucket_box.setChecked(False)
            self.auto_next_same_bucket_box.setEnabled(False)
            self.global_status.setText("多保留模式：自动下一组已禁用，请手动下一组或使用 + 保存并下一组")
        else:
            self.auto_next_same_bucket_box.setEnabled(True)
            self.auto_next_same_bucket_box.setChecked(True)
            self.global_status.setText("单保留模式：保存后可自动跳到同 N 下一组")

    def clear_manual_selection(self) -> None:
        if self.current_manual_group is None:
            return
        for item in self.current_manual_group.items:
            item.selection_state = "UNDECIDED"
        for card in self.manual_cards:
            card.refresh_state("UNDECIDED")
        self.update_selection_summary()

    def save_manual_selection(self, review_status: str, force_next: bool = False) -> None:
        group = self.current_manual_group
        if group is None or self.manual_service is None:
            return
        keep = [item.item_id for item in group.items if item.selection_state == "KEEP"]
        remove = [item.item_id for item in group.items if item.selection_state == "REMOVE"]
        try:
            path = self.manual_service.save_selection(group, review_status, keep, remove)
            self.global_status.setText(f"已写入选择结果：{path.name}")
            self.logger.event("manual_objects_selection_saved", group_key=group.group_key, review_status=review_status, path=str(path))
            self.refresh_manual_group_row()
            should_auto_next = (
                force_next
                or (
                    self.auto_next_same_bucket_box.isChecked()
                    and not self.manual_multi_keep
                    and not self.stay_after_save_box.isChecked()
                )
            )
            if should_auto_next:
                self.open_next_unreviewed_manual_group(group.group_key, same_bucket=True)
        except Exception as exc:
            self.show_message(str(exc))

    def refresh_manual_group_row(self) -> None:
        if self.manual_index_service is None or self.current_manual_summary is None:
            return
        self.manual_index_service.refresh_summary_selection_status(self.current_manual_summary)
        if self.current_manual_group:
            self.manual_group_cache[self.current_manual_group.group_key] = self.current_manual_group
        self.render_manual_group_page()

    def open_next_unreviewed_manual_group(self, current_group_key: str, same_bucket: bool = True) -> None:
        if not self.manual_filtered_summaries:
            return
        start = 0
        current_summary = self.current_manual_summary
        for index, summary in enumerate(self.manual_filtered_summaries):
            if summary.group_key == current_group_key:
                start = index + 1
                break
        candidates = self.manual_filtered_summaries[start:] + self.manual_filtered_summaries[:start]
        for summary in candidates:
            if same_bucket and current_summary is not None:
                if summary.reason != current_summary.reason or summary.size_bucket != current_summary.size_bucket:
                    continue
            if summary.selection_status == "未复核":
                page = self.manual_filtered_summaries.index(summary) // self.manual_page_size
                if page != self.manual_page:
                    self.manual_page = page
                    self.render_manual_group_page()
                self.open_manual_group_from_summary(summary)
                return
        if current_summary is not None:
            self.global_status.setText(f"{current_summary.reason}/{current_summary.size_bucket} 当前筛选范围内暂无下一条未复核组")

    def update_selection_summary(self) -> None:
        group = self.current_manual_group
        if group is None:
            self.selection_summary.setText("")
            return
        keep = [item.item_id for item in group.items if item.selection_state == "KEEP"]
        remove = [item.item_id for item in group.items if item.selection_state == "REMOVE"]
        undecided = [item.item_id for item in group.items if item.selection_state == "UNDECIDED"]
        self.selection_summary.setText(
            f"保留 KEEP: {', '.join(keep) or '-'}\n"
            f"移除 REMOVE: {', '.join(remove) or '-'}\n"
            f"未决 UNDECIDED: {', '.join(undecided) or '-'}"
        )

    def export_manual_summary(self) -> None:
        if self.manual_service is None:
            self.show_message("尚未选择 Manual_Objects 根目录。")
            return
        out = PROGRAMME_DIR / "Audit_Reports" / f"manual_objects_selection_summary_{UI_VERSION}_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
        path = self.manual_service.export_selection_summary(out)
        self.show_message(f"选择汇总已导出：{path}")

    def open_current_manual_folder(self) -> None:
        if self.current_manual_group is None:
            return
        subprocess.Popen(["explorer", str(self.current_manual_group.group_dir)])

    def open_manual_item_viewer(self, item_id: str) -> None:
        group = self.current_manual_group
        if group is None:
            return
        for item in group.items:
            if item.item_id == item_id:
                self.open_image_viewer(item.image_path)
                return

    def open_image_viewer(self, image_path: Path) -> None:
        viewer = ImageViewer(image_path, self)
        viewer.show()

    def handle_number_key(self, key: str) -> None:
        if self.stack.currentIndex() == 0:
            if key in self.key_to_source_card:
                self.select_source_card(self.key_to_source_card[key])
        elif self.stack.currentIndex() == 1:
            idx = int(key) - 1
            if 0 <= idx < len(self.manual_cards):
                self.select_manual_item(self.manual_cards[idx].item.item_id)

    def handle_enter(self) -> None:
        if self.stack.currentIndex() == 0:
            self.commit_source_selected()
        elif self.stack.currentIndex() == 1:
            self.save_manual_selection("APPROVED")

    def handle_escape(self) -> None:
        if self.stack.currentIndex() == 0:
            self.source_selected_index = None
            for card in self.source_cards:
                card.set_selected(False)
        elif self.stack.currentIndex() == 1:
            self.clear_manual_selection()

    def handle_space(self) -> None:
        if self.stack.currentIndex() == 0 and self.source_selected_index is not None and self.current_groups:
            self.open_image_viewer(Path(self.current_groups[self.current_group_index][1][self.source_selected_index]))
        elif self.stack.currentIndex() == 1 and self.current_manual_group:
            keep = [item for item in self.current_manual_group.items if item.selection_state == "KEEP"]
            if keep:
                self.open_image_viewer(keep[0].image_path)

    def show_shortcuts(self) -> None:
        self.show_message("快捷键：1-9 选择；Enter 写入/提交；+ 保存并下一组；Esc 清除；Space 查看原图；Ctrl+Z 撤销图源组；A/S/N 标记 Manual Objects 状态。")

    def show_message(self, text: str) -> None:
        if self.run_mode == "test":
            self.global_status.setText(text[:80])
            return
        QMessageBox.information(self, "提示", text)

    @staticmethod
    def clear_layout(layout: QGridLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

    def apply_style(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow, QWidget { background: #EEF2F6; color: #17201C; font-size: 12px; font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif; }
            #workflowBar, #commandBar, #glassPanel, #stagePanel, #emptyState { background: rgba(255,255,255,0.78); border: 1px solid rgba(255,255,255,0.92); border-radius: 12px; }
            #appTitle { font-size: 20px; font-weight: 900; color: #094438; }
            #workflowButton { padding: 7px 12px; border-radius: 8px; border: 1px solid rgba(9,68,56,0.25); background: rgba(255,255,255,0.86); }
            #workflowButton:checked { background: rgba(9,68,56,0.16); color: #094438; font-weight: 800; }
            QPushButton { background: rgba(255,255,255,0.88); border: 1px solid rgba(9,68,56,0.25); border-radius: 8px; padding: 6px 10px; }
            QPushButton:hover { border-color: #009CD5; }
            #statusChip { padding: 7px 12px; border-radius: 8px; background: rgba(209,193,141,0.22); color: #094438; font-weight: 800; }
            #context { color: #667085; }
            #imageCard, #manualObjectCard { background: rgba(255,255,255,0.86); border: 2px solid rgba(209,193,141,0.42); border-radius: 12px; }
            #imageCard[selectedState="true"] { border: 3px solid #EF4022; }
            #manualObjectCard[state="KEEP"] { border: 3px solid #094438; background: rgba(9,68,56,0.06); }
            #manualObjectCard[state="REMOVE"] { border: 3px solid #667085; background: rgba(102,112,133,0.05); }
            #manualObjectCard[state="UNDECIDED"] { border: 2px solid rgba(209,193,141,0.42); }
            #imagePreview { background: rgba(232,237,242,0.88); border: 2px solid transparent; border-radius: 10px; }
            #imagePreview[selectedState="true"] { border: 2px solid #EF4022; background: rgba(239,64,34,0.05); }
            #cardNumber { color: #EF4022; font-size: 24px; font-weight: 900; }
            #cardFilename { color: #17201C; font-weight: 700; }
            #cardStatus { color: #667085; }
            #stateChip[state="KEEP"] { background: rgba(9,68,56,0.14); color: #094438; padding: 5px 8px; border-radius: 8px; }
            #stateChip[state="REMOVE"] { background: rgba(102,112,133,0.14); color: #344054; padding: 5px 8px; border-radius: 8px; }
            #stateChip[state="UNDECIDED"], #stateChip { background: rgba(209,193,141,0.18); color: #094438; padding: 5px 8px; border-radius: 8px; }
            QTableView, QTextEdit { background: rgba(255,255,255,0.74); border: 1px solid rgba(9,68,56,0.10); border-radius: 8px; }
            """
        )


def main(argv: list[str] | None = None) -> int:
    args = list(argv or sys.argv)
    if "--help" in args:
        print(f"CIVL7009 Source Group Picker {UI_VERSION}")
        print("  --help        Show this help.")
        print("  --smoke-open  Open the Qt shell briefly and exit.")
        return 0
    if QT_IMPORT_ERROR is not None:
        print(QT_IMPORT_ERROR, file=sys.stderr)
        return 2
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    app = QApplication.instance() or QApplication(args)
    app.setApplicationName("CIVL7009 Source Group Picker V3.0.1")
    window = MainWindow(run_mode=os.environ.get("CIVL7009_PICKER_RUN_MODE", "gui_production"))
    window.show()
    if "--smoke-open" in args:
        QTimer.singleShot(350, app.quit)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
