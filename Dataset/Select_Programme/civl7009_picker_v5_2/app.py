from __future__ import annotations

import json
import os
import queue
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from .assets import AssetService
from .conflict_resolution import ConflictAwarenessService, ConflictIndex, ReasonEventDecision, SourceItemRecord, SourceObjectConflict
from .core import PickerCoreFacade
from .manual_objects import (
    IdClassStatus,
    ManualGroupSummary,
    ManualObjectGroup,
    ManualObjectItem,
    ManualObjectsClassService,
    ManualObjectsFilter,
    ManualObjectsIndexResult,
    ManualObjectsIndexService,
    ManualObjectsService,
    UNREVIEWED_STATUS,
)
from .paths import PROGRAMME_DIR, RUNTIME_LOG_ROOT
from .tier_governance import TierPrefixGovernanceService, TierRenamePlan, TierScanResult
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
        QDialog,
        QFileDialog,
        QFrame,
        QGridLayout,
        QHeaderView,
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


class ConflictIndexSignals(QObject):
    done = Signal(int, object, object)
    error = Signal(int, str)


class ConflictIndexWorker(QRunnable):
    def __init__(self, generation: int, root: Path) -> None:
        super().__init__()
        self.generation = generation
        self.root = root
        self.signals = ConflictIndexSignals()

    @Slot()
    def run(self) -> None:
        try:
            service = ConflictAwarenessService(self.root)
            result = service.build_index()
            self.signals.done.emit(self.generation, service, result)
        except Exception as exc:
            self.signals.error.emit(self.generation, str(exc))


class TierScanSignals(QObject):
    done = Signal(int, object)
    error = Signal(int, str)


class TierScanWorker(QRunnable):
    def __init__(self, generation: int, root: Path) -> None:
        super().__init__()
        self.generation = generation
        self.root = root
        self.signals = TierScanSignals()

    @Slot()
    def run(self) -> None:
        try:
            result = TierPrefixGovernanceService(self.root).scan()
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
    def __init__(
        self,
        generation: int,
        item_id: str,
        image_path: Path,
        label_path: Path | None = None,
        draw_bboxes: bool = True,
        class_map: dict[str, str] | None = None,
        max_size: tuple[int, int] = (1280, 960),
    ) -> None:
        super().__init__()
        self.generation = generation
        self.item_id = item_id
        self.image_path = image_path
        self.label_path = label_path
        self.draw_bboxes = draw_bboxes
        self.class_map = class_map or {}
        self.max_size = max_size
        self.signals = ThumbnailSignals()

    @Slot()
    def run(self) -> None:
        try:
            import io
            from PIL import Image, ImageDraw, ImageFont

            with Image.open(self.image_path) as image:
                image = image.convert("RGB")
                if self.draw_bboxes and self.label_path:
                    self.draw_yolo_bboxes(image, self.label_path, ImageDraw, ImageFont, self.class_map)
                image.thumbnail(self.max_size)
                buffer = io.BytesIO()
                image.save(buffer, format="PNG")
            self.signals.done.emit(self.generation, self.item_id, buffer.getvalue())
        except Exception as exc:
            self.signals.error.emit(self.generation, self.item_id, str(exc))

    @staticmethod
    def parse_yolo_label(label_path: Path) -> tuple[list[tuple[str, float, float, float, float]], list[str]]:
        boxes: list[tuple[str, float, float, float, float]] = []
        issues: list[str] = []
        if not label_path.exists():
            return boxes, [f"标签不存在: {label_path.name}"]
        try:
            lines = label_path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            lines = label_path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
        for line_no, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            parts = stripped.split()
            if len(parts) < 5:
                issues.append(f"第 {line_no} 行字段不足")
                continue
            try:
                cls = parts[0]
                cx, cy, bw, bh = [float(value) for value in parts[1:5]]
            except ValueError:
                issues.append(f"第 {line_no} 行无法解析为 YOLO bbox")
                continue
            if bw <= 0 or bh <= 0:
                issues.append(f"第 {line_no} 行 bbox 宽高非正")
                continue
            boxes.append((cls, cx, cy, bw, bh))
        return boxes, issues

    @staticmethod
    def draw_yolo_bboxes(image: Any, label_path: Path, image_draw: Any, image_font: Any, class_map: dict[str, str] | None = None) -> None:
        boxes, _issues = ThumbnailWorker.parse_yolo_label(label_path)
        if not boxes:
            return
        class_map = class_map or {}
        width, height = image.size
        draw = image_draw.Draw(image)
        colours = ["#EF4022", "#009CD5", "#094438", "#D1C18D", "#FED40D"]
        try:
            font = image_font.load_default()
        except Exception:
            font = None
        for idx, (cls, cx, cy, bw, bh) in enumerate(boxes):
            x1 = max(0, min(width - 1, int((cx - bw / 2) * width)))
            y1 = max(0, min(height - 1, int((cy - bh / 2) * height)))
            x2 = max(0, min(width - 1, int((cx + bw / 2) * width)))
            y2 = max(0, min(height - 1, int((cy + bh / 2) * height)))
            colour = colours[idx % len(colours)]
            font_size = max(18, min(34, int(min(width, height) / 22)))
            font = ThumbnailWorker.load_bbox_font(image_font, font_size)
            line_width = max(3, int(min(width, height) / 120))
            for offset in range(line_width):
                draw.rectangle([x1 - offset, y1 - offset, x2 + offset, y2 + offset], outline=colour)
            mapped_name = class_map.get(str(cls))
            label = f"{mapped_name} ({cls})" if mapped_name else f"class {cls}"
            safe_label = label
            try:
                text_bbox = draw.textbbox((x1, y1), safe_label, font=font) if hasattr(draw, "textbbox") else (x1, y1, x1 + 54, y1 + 12)
            except Exception:
                safe_label = f"class {cls}"
                text_bbox = draw.textbbox((x1, y1), safe_label, font=font) if hasattr(draw, "textbbox") else (x1, y1, x1 + 54, y1 + 12)
            tx1, ty1, tx2, ty2 = text_bbox
            pad = max(5, int(font_size / 4))
            bg_y1 = max(0, y1 - (ty2 - ty1) - pad * 2)
            draw.rectangle([x1, bg_y1, x1 + (tx2 - tx1) + pad * 2, bg_y1 + (ty2 - ty1) + pad * 2], fill=colour)
            try:
                draw.text((x1 + pad, bg_y1 + pad), safe_label, fill="white", font=font)
            except Exception:
                draw.text((x1 + pad, bg_y1 + pad), f"class {cls}", fill="white", font=font)

    @staticmethod
    def load_bbox_font(image_font: Any, font_size: int) -> Any:
        candidates = [
            Path("C:/Windows/Fonts/msyh.ttc"),
            Path("C:/Windows/Fonts/msyhbd.ttc"),
            Path("C:/Windows/Fonts/seguisym.ttf"),
            Path("C:/Windows/Fonts/segoeui.ttf"),
            Path("C:/Windows/Fonts/arial.ttf"),
        ]
        for path in candidates:
            try:
                if path.exists():
                    return image_font.truetype(str(path), font_size)
            except Exception:
                continue
        try:
            return image_font.load_default(font_size)
        except Exception:
            return image_font.load_default()


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

    def set_conflict_status(self, status: str, explanation: str = "") -> None:
        display = {
            "CONSISTENT_KEEP": "冲突状态：一致保留",
            "CONSISTENT_REMOVE": "冲突状态：一致移除",
            "CONFLICT_KEEP_REMOVE": "冲突状态：保留/移除冲突",
            "GROUP_SIGNATURE_CONFLICT": "冲突状态：组签名冲突",
            "UNRESOLVED_OR_PARTIAL": "冲突状态：未解决/部分选择",
            "WEAK_IDENTITY": "冲突状态：弱身份",
            "PENDING_INDEX": "冲突状态：待索引",
            "NO_KNOWN_CONFLICT": "冲突状态：无已知冲突",
        }.get(status, f"冲突状态：{status}")
        self.conflict_chip.setText(display)
        self.conflict_chip.setToolTip(explanation)
        self.conflict_chip.setProperty("conflictState", status)
        self.setProperty("conflictState", status)
        for widget in (self, self.conflict_chip):
            widget.style().unpolish(widget)
            widget.style().polish(widget)
            widget.update()

    def mousePressEvent(self, event: Any) -> None:
        self.selected.emit(self.index)

    def mouseDoubleClickEvent(self, event: Any) -> None:
        self.activated.emit(self.index)


class ScalableImageLabel(QLabel):
    def __init__(self) -> None:
        super().__init__()
        self._source_image: QImage | None = None
        self.setAlignment(Qt.AlignCenter)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumHeight(320)

    def set_image_bytes(self, payload: bytes) -> None:
        image = QImage.fromData(payload)
        if image.isNull():
            self._source_image = None
            self.setPixmap(QPixmap())
            self.setText("图片无法加载")
            return
        self._source_image = image
        self.setText("")
        self.update_scaled_pixmap()

    def resizeEvent(self, event: Any) -> None:
        super().resizeEvent(event)
        self.update_scaled_pixmap()

    def update_scaled_pixmap(self) -> None:
        if self._source_image is None or self.width() <= 8 or self.height() <= 8:
            return
        side = max(24, min(self.width() - 8, self.height() - 8))
        pixmap = QPixmap.fromImage(self._source_image)
        self.setPixmap(pixmap.scaled(side, side, Qt.KeepAspectRatio, Qt.SmoothTransformation))


class ManualObjectCard(QFrame):
    selected = Signal(str)
    activated = Signal(str)

    def __init__(self, item: ManualObjectItem, index: int, class_map: dict[str, str] | None = None) -> None:
        super().__init__()
        self.item = item
        self.index = index
        self.class_map = class_map or {}
        self.setObjectName("manualObjectCard")
        self.setProperty("state", item.selection_state)
        self.setProperty("previewSelected", "false")
        self.setMinimumWidth(300)
        self.setMinimumHeight(460)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 9, 10, 9)
        layout.setSpacing(6)
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
        self.preview = ScalableImageLabel()
        self.preview.setObjectName("imagePreview")
        self.preview.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.preview, 1)
        self.name_label = QLabel(item.image_filename)
        self.name_label.setWordWrap(True)
        self.name_label.setMaximumHeight(34)
        self.class_names_label = QLabel(f"标签：{self.label_names_text(item, self.class_map)}")
        self.class_names_label.setObjectName("classLabel")
        self.class_names_label.setWordWrap(True)
        self.class_names_label.setMaximumHeight(42)
        self.conflict_chip = QLabel("冲突状态：待索引")
        self.conflict_chip.setObjectName("conflictChip")
        self.conflict_chip.setWordWrap(True)
        self.conflict_chip.setMaximumHeight(42)
        self.meta_label = QLabel(f"{item.width}×{item.height} | label {item.label_line_count} 行 | class {','.join(map(str, item.label_class_set))}")
        self.meta_label.setObjectName("cardStatus")
        self.metrics_label = QLabel(self.metrics_text(item.metrics))
        self.metrics_label.setObjectName("cardStatus")
        self.metrics_label.setWordWrap(True)
        self.metrics_label.setMaximumHeight(38)
        layout.addWidget(self.name_label)
        layout.addWidget(self.class_names_label)
        layout.addWidget(self.conflict_chip)
        layout.addWidget(self.meta_label)
        layout.addWidget(self.metrics_label)
        self.preview.setText("缩略图加载中...")
        self.refresh_state(item.selection_state)

    def set_preview_selected(self, selected: bool) -> None:
        self.setProperty("previewSelected", "true" if selected else "false")
        self.preview.setProperty("previewSelected", "true" if selected else "false")
        for widget in (self, self.preview):
            widget.style().unpolish(widget)
            widget.style().polish(widget)
            widget.update()

    @staticmethod
    def label_names_text(item: ManualObjectItem, class_map: dict[str, str]) -> str:
        raw_classes = [str(value) for value in item.label_class_set if str(value).strip()]
        if not raw_classes:
            return "无 bbox 类别"
        labels = []
        for raw in raw_classes:
            mapped = class_map.get(raw)
            labels.append(f"{mapped} ({raw})" if mapped else f"class {raw}")
        return "、".join(labels)

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
        self.preview.set_image_bytes(payload)

    def refresh_state(self, state: str) -> None:
        self.item.selection_state = state
        self.setProperty("state", state)
        self.state_chip.setText({"KEEP": "保留 KEEP", "REMOVE": "移除 REMOVE", "UNDECIDED": "未决"}.get(state, state))
        self.state_chip.setProperty("state", state)
        for widget in (self, self.state_chip):
            widget.style().unpolish(widget)
            widget.style().polish(widget)
            widget.update()

    def set_conflict_status(self, status: str, explanation: str = "") -> None:
        display = {
            "CONSISTENT_KEEP": "冲突状态：一致保留",
            "CONSISTENT_REMOVE": "冲突状态：一致移除",
            "CONFLICT_KEEP_REMOVE": "冲突状态：保留/移除冲突",
            "GROUP_SIGNATURE_CONFLICT": "冲突状态：组签名冲突",
            "UNRESOLVED_OR_PARTIAL": "冲突状态：未解决/部分选择",
            "WEAK_IDENTITY": "冲突状态：弱身份",
            "PENDING_INDEX": "冲突状态：待索引",
            "NO_KNOWN_CONFLICT": "冲突状态：无已知冲突",
        }.get(status, f"冲突状态：{status}")
        self.conflict_chip.setText(display)
        self.conflict_chip.setToolTip(explanation)
        self.conflict_chip.setProperty("conflictState", status)
        self.setProperty("conflictState", status)
        for widget in (self, self.conflict_chip):
            widget.style().unpolish(widget)
            widget.style().polish(widget)
            widget.update()

    def mousePressEvent(self, event: Any) -> None:
        self.selected.emit(self.item.item_id)

    def mouseDoubleClickEvent(self, event: Any) -> None:
        self.activated.emit(self.item.item_id)


class ClassFilesDialog(QDialog):
    def __init__(self, parent: QWidget, service: ManualObjectsClassService, dataset_ids: list[str]) -> None:
        super().__init__(parent)
        self.service = service
        self.dataset_ids = dataset_ids
        self.statuses: list[IdClassStatus] = []
        self.setWindowTitle("Manual Objects ID 类别文件检测")
        self.resize(920, 420)
        layout = QVBoxLayout(self)
        intro = QLabel(
            "程序会在 Manual_Objects/ID_Classes/IDxx 内读取任意非空 .txt 作为类别文件；"
            "文件名不限，不必叫 classes.txt。缺失时请打开对应 ID 目录后放入类别 txt，再刷新检测。"
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)
        self.model = TableModel(["ID", "状态", "类别数", "类别文件", "目录", "说明"])
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        layout.addWidget(self.table, 1)
        actions = QHBoxLayout()
        self.open_dir_btn = QPushButton("打开选中 ID 目录")
        self.refresh_btn = QPushButton("刷新检测")
        self.close_btn = QPushButton("关闭")
        actions.addWidget(self.open_dir_btn)
        actions.addWidget(self.refresh_btn)
        actions.addStretch(1)
        actions.addWidget(self.close_btn)
        layout.addLayout(actions)
        self.open_dir_btn.clicked.connect(self.open_selected_dir)
        self.refresh_btn.clicked.connect(self.refresh)
        self.close_btn.clicked.connect(self.accept)
        self.refresh()

    def refresh(self) -> None:
        self.statuses = self.service.ensure_id_class_dirs(self.dataset_ids)
        rows = []
        for status in self.statuses:
            rows.append(
                [
                    status.dataset_id,
                    status.status,
                    status.class_count,
                    str(status.class_file) if status.class_file else "",
                    str(status.class_dir),
                    status.message,
                ]
            )
        self.model.set_rows(rows)

    def open_selected_dir(self) -> None:
        index = self.table.currentIndex()
        if not index.isValid() or not (0 <= index.row() < len(self.statuses)):
            return
        subprocess.Popen(["explorer", str(self.statuses[index.row()].class_dir)])


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
        self.manual_class_service: ManualObjectsClassService | None = None
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
        self.manual_thumbnail_cache: dict[tuple[str, int, int, str, int, int, bool, str], bytes] = {}
        self.manual_thumbnail_pending: set[str] = set()
        self.manual_thumbnail_expected = 0
        self.manual_thumbnail_done = 0
        self.manual_thumbnail_failed: dict[str, str] = {}
        self.manual_thumbnail_workers: dict[str, ThumbnailWorker] = {}
        self.manual_thumbnail_queue: list[str] = []
        self.manual_thumbnail_batch_size = 12
        self.manual_draw_bboxes = True
        self.manual_click_save_in_progress = False
        self.manual_multi_keep = False
        self.manual_dataset_ids: list[str] = []
        self.manual_class_statuses: list[IdClassStatus] = []
        self.manual_class_maps: dict[str, dict[str, str]] = {}
        self.manual_missing_class_notice_shown = False
        self.manual_preview_index = -1
        self.pending_history_group_key: str | None = None
        self.pending_history_manual_root: Path | None = None
        self.pending_conflict_item_id: str = ""
        self.manual_history_path = RUNTIME_LOG_ROOT / "Manual_Object_History" / f"manual_object_selection_history_{UI_VERSION}.jsonl"
        self.manual_history_rows: list[dict[str, Any]] = []
        self.history_row_records: list[dict[str, Any]] = []
        self.last_manual_save_record: dict[str, Any] | None = None
        self.conflict_service: ConflictAwarenessService | None = None
        self.conflict_index: ConflictIndex | None = None
        self.conflict_row_objects: list[SourceObjectConflict] = []
        self.current_conflict_object: SourceObjectConflict | None = None
        self.conflict_index_quiet = False
        self.pending_conflict_refresh_source_key: str = ""
        self.tier_root: Path | None = None
        self.tier_generation = 0
        self.tier_scan_result: TierScanResult | None = None
        self.tier_plan: TierRenamePlan | None = None

        self.source_review_model = TableModel(["目录", "Root", "Done", "异常", "标签同步"])
        self.source_issue_model = TableModel(["等级", "Prefix", "代码", "说明", "建议"])
        self.source_queue_model = TableModel(["任务", "Prefix", "选中", "状态", "错误"])
        self.manual_group_model = TableModel(["Reason", "N", "Group", "状态", "行数", "数据集", "类别", "异常"])
        self.manual_issue_model = TableModel(["等级", "代码", "Item", "说明"])
        self.history_model = TableModel(["操作时间", "状态", "Reason", "N", "Group", "KEEP", "REMOVE", "组目录"])

        self.conflict_queue_model = TableModel(["状态", "数据集", "文件", "SHA256", "事件", "KEEP", "REMOVE", "Resolution"])
        self.conflict_event_model = TableModel(["事件", "本地决策", "Review", "Selection Path"])
        self.tier_group_model = TableModel(["规范 stem", "状态", "图片", "标签", "已标记", "未标记", "ID", "Tier", "异常"])
        self.tier_plan_model = TableModel(["类型", "规范 stem", "源文件", "目标文件"])

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
        self.stack.addWidget(self.build_conflict_resolution_page())
        self.stack.addWidget(self.build_tier_prefix_page())
        self.stack.addWidget(self.build_history_page())
        self.stack.addWidget(self.build_diagnostics_page())
        layout.addWidget(self.stack, 1)
        self.setCentralWidget(root)

    def build_workflow_tabs(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("workflowBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(10, 8, 10, 8)
        self.workflow_buttons: list[QPushButton] = []
        labels = [
            "图源组筛选（Source Group Review）",
            "跨库候选复核（Manual Objects Review）",
            "冲突复核（Conflict Resolution）",
            "Tier 前缀治理（Tier Prefix）",
            "操作记录（Review History）",
            "诊断与设置（Diagnostics Settings）",
        ]
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
        statuses = ["图源组筛选模式", "Manual Objects 复核模式", "冲突复核模式", "Tier 前缀治理模式", "操作记录", "诊断与设置"]
        self.global_status.setText(statuses[index] if 0 <= index < len(statuses) else "就绪")
        return
        self.global_status.setText(["图源组筛选模式", "Manual Objects 复核模式", "操作记录", "诊断与设置"][index])

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
        self.undo_manual_btn = QPushButton("撤销上一次复核")
        self.undo_manual_btn.setEnabled(False)
        self.check_classes_btn = QPushButton("类别文件检测")
        self.refresh_manual_status_btn = QPushButton("刷新全目录状态")
        self.manual_root_label = QLabel("Manual_Objects: 未选择")
        self.manual_root_label.setObjectName("context")
        cmd.addWidget(self.choose_manual_btn)
        cmd.addWidget(self.export_manual_btn)
        cmd.addWidget(self.open_group_btn)
        cmd.addWidget(self.undo_manual_btn)
        cmd.addWidget(self.check_classes_btn)
        cmd.addWidget(self.refresh_manual_status_btn)
        cmd.addStretch(1)
        cmd.addWidget(self.manual_root_label)
        layout.addWidget(command)
        self.choose_manual_btn.clicked.connect(self.choose_manual_root)
        self.export_manual_btn.clicked.connect(self.export_manual_summary)
        self.open_group_btn.clicked.connect(self.open_current_manual_folder)
        self.undo_manual_btn.clicked.connect(self.undo_last_manual_review_operation)
        self.check_classes_btn.clicked.connect(self.show_class_files_dialog)
        self.refresh_manual_status_btn.clicked.connect(self.refresh_manual_status_dashboard)

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
        for status in [UNREVIEWED_STATUS, "APPROVED", "ALL_DONE", "ALL_OUT", "SKIP", "AMBIGUOUS", "NEEDS_AGENT_CHECK", "SELECTION_JSON_INVALID", "UNKNOWN"]:
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
        self.auto_next_same_bucket_box = QCheckBox("单击保存并进入同 N 下一组")
        self.auto_next_same_bucket_box.setChecked(True)
        self.bbox_overlay_box = QCheckBox("显示 txt BBox")
        self.bbox_overlay_box.setChecked(True)
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
            self.bbox_overlay_box,
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
        self.bbox_overlay_box.stateChanged.connect(self.on_bbox_overlay_changed)

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
        self.manual_conflict_explanation = QTextEdit()
        self.manual_conflict_explanation.setObjectName("conflictExplanation")
        self.manual_conflict_explanation.setReadOnly(True)
        self.manual_conflict_explanation.setMaximumHeight(120)
        self.manual_conflict_explanation.setText("当前对象冲突说明：等待选择候选图片。")
        center_layout.addWidget(self.manual_conflict_explanation)
        actions = QHBoxLayout()
        self.multi_keep_box = QCheckBox("多保留模式")
        self.save_approved_btn = QPushButton("写入 APPROVED")
        self.save_skip_btn = QPushButton("标记 SKIP")
        self.save_ambiguous_btn = QPushButton("标记 AMBIGUOUS")
        self.save_needs_check_btn = QPushButton("标记 NEEDS_AGENT_CHECK")
        self.save_all_done_btn = QPushButton("标记 ALL_DONE")
        self.save_all_out_btn = QPushButton("标记 ALL_OUT")
        self.save_next_btn = QPushButton("+ 保存并下一组")
        self.clear_manual_btn = QPushButton("撤销本组未保存选择")
        for widget in [self.multi_keep_box, self.save_approved_btn, self.save_skip_btn, self.save_ambiguous_btn, self.save_needs_check_btn, self.save_all_done_btn, self.save_all_out_btn, self.save_next_btn, self.clear_manual_btn]:
            actions.addWidget(widget)
        center_layout.addLayout(actions)
        self.multi_keep_box.stateChanged.connect(self.on_manual_multi_keep_changed)
        self.save_approved_btn.clicked.connect(lambda: self.save_manual_selection("APPROVED"))
        self.save_skip_btn.clicked.connect(lambda: self.save_manual_selection("SKIP"))
        self.save_ambiguous_btn.clicked.connect(lambda: self.save_manual_selection("AMBIGUOUS"))
        self.save_needs_check_btn.clicked.connect(lambda: self.save_manual_selection("NEEDS_AGENT_CHECK"))
        self.save_all_done_btn.clicked.connect(lambda: self.save_manual_selection("ALL_DONE"))
        self.save_all_out_btn.clicked.connect(lambda: self.save_manual_selection("ALL_OUT"))
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

    def build_conflict_resolution_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        command = QFrame()
        command.setObjectName("commandBar")
        cmd = QHBoxLayout(command)
        self.refresh_conflict_btn = QPushButton("刷新冲突索引")
        self.refresh_current_conflict_btn = QPushButton("重读当前对象状态")
        self.export_conflict_gate_btn = QPushButton("导出治理门摘要")
        self.open_conflict_folder_btn = QPushButton("打开 resolution 文件夹")
        self.conflict_state_filter = QComboBox()
        self.conflict_state_filter.addItem("全部冲突状态", "")
        for state in [
            "CONFLICT_KEEP_REMOVE",
            "GROUP_SIGNATURE_CONFLICT",
            "UNRESOLVED_OR_PARTIAL",
            "CONSISTENT_KEEP",
            "CONSISTENT_REMOVE",
        ]:
            self.conflict_state_filter.addItem(state, state)
        self.conflict_status_label = QLabel("冲突索引：尚未构建")
        self.conflict_status_label.setObjectName("context")
        for widget in [self.refresh_conflict_btn, self.refresh_current_conflict_btn, self.export_conflict_gate_btn, self.open_conflict_folder_btn, self.conflict_state_filter]:
            cmd.addWidget(widget)
        cmd.addStretch(1)
        cmd.addWidget(self.conflict_status_label)
        layout.addWidget(command)
        self.refresh_conflict_btn.clicked.connect(self.start_conflict_index_build)
        self.refresh_current_conflict_btn.clicked.connect(self.refresh_current_conflict_object)
        self.export_conflict_gate_btn.clicked.connect(self.export_conflict_gate_summary)
        self.open_conflict_folder_btn.clicked.connect(self.open_conflict_resolution_folder)
        self.conflict_state_filter.currentIndexChanged.connect(self.render_conflict_queue)

        splitter = QSplitter(Qt.Horizontal)
        left = QFrame()
        left.setObjectName("glassPanel")
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("Source object 冲突队列"))
        self.conflict_queue_table = QTableView()
        self.conflict_queue_table.setModel(self.conflict_queue_model)
        self.conflict_queue_table.clicked.connect(self.open_conflict_object_from_table)
        self.conflict_queue_table.doubleClicked.connect(self.open_conflict_object_from_table)
        left_layout.addWidget(self.conflict_queue_table, 1)
        splitter.addWidget(left)

        center = QFrame()
        center.setObjectName("stagePanel")
        center_layout = QVBoxLayout(center)
        center_layout.addWidget(QLabel("Reason 证据事件（Evidence Events）"))
        self.conflict_event_table = QTableView()
        self.conflict_event_table.setModel(self.conflict_event_model)
        self.conflict_event_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.conflict_event_table.clicked.connect(self.open_conflict_event_from_table)
        self.conflict_event_table.doubleClicked.connect(self.open_conflict_event_from_table)
        center_layout.addWidget(self.conflict_event_table, 0)
        self.conflict_evidence_scroll = QScrollArea()
        self.conflict_evidence_scroll.setWidgetResizable(True)
        self.conflict_evidence_host = QWidget()
        self.conflict_evidence_layout = QVBoxLayout(self.conflict_evidence_host)
        self.conflict_evidence_layout.setSpacing(10)
        self.conflict_evidence_scroll.setWidget(self.conflict_evidence_host)
        center_layout.addWidget(self.conflict_evidence_scroll, 1)
        splitter.addWidget(center)

        right = QFrame()
        right.setObjectName("glassPanel")
        right_layout = QVBoxLayout(right)
        right_layout.addWidget(QLabel("对象级决策（Object-level Resolution）"))
        self.conflict_summary_text = QTextEdit()
        self.conflict_summary_text.setReadOnly(True)
        self.conflict_summary_text.setMaximumHeight(210)
        right_layout.addWidget(self.conflict_summary_text)
        self.final_decision_combo = QComboBox()
        for decision in [
            "KEEP_SOURCE_OBJECT",
            "REMOVE_SOURCE_OBJECT",
            "ALL_OUT_SOURCE_OBJECT",
            "DEFER_REVIEW",
            "NEEDS_AGENT_CHECK",
            "SPLIT_CONTEXT_REQUIRED",
        ]:
            self.final_decision_combo.addItem(decision, decision)
        self.conflict_confidence_combo = QComboBox()
        for confidence in ["HIGH", "MEDIUM", "LOW"]:
            self.conflict_confidence_combo.addItem(confidence, confidence)
        self.conflict_reviewer_edit = QLineEdit()
        self.conflict_reviewer_edit.setPlaceholderText("reviewer")
        self.conflict_rationale_edit = QTextEdit()
        self.conflict_rationale_edit.setPlaceholderText("决策依据 / decision rationale")
        self.conflict_rationale_edit.setMaximumHeight(120)
        self.conflict_notes_edit = QTextEdit()
        self.conflict_notes_edit.setPlaceholderText("notes")
        self.conflict_notes_edit.setMaximumHeight(100)
        self.save_conflict_resolution_btn = QPushButton("写入对象级 resolution")
        for widget in [
            QLabel("Final decision"),
            self.final_decision_combo,
            QLabel("Confidence"),
            self.conflict_confidence_combo,
            QLabel("Reviewer"),
            self.conflict_reviewer_edit,
            self.conflict_rationale_edit,
            self.conflict_notes_edit,
            self.save_conflict_resolution_btn,
        ]:
            right_layout.addWidget(widget)
        right_layout.addStretch(1)
        self.save_conflict_resolution_btn.clicked.connect(self.save_conflict_resolution)
        splitter.addWidget(right)
        splitter.setSizes([420, 760, 420])
        layout.addWidget(splitter, 1)
        return page

    def build_tier_prefix_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        command = QFrame()
        command.setObjectName("commandBar")
        cmd = QHBoxLayout(command)
        self.choose_tier_root_btn = QPushButton("选择主库根目录")
        self.scan_tier_btn = QPushButton("扫描 Tier 状态")
        self.export_tier_btn = QPushButton("导出扫描报告")
        self.tier_input = QLineEdit("Tier01")
        self.tier_input.setMaximumWidth(90)
        self.plan_tier_btn = QPushButton("生成 dry-run 计划")
        self.apply_tier_btn = QPushButton("执行加前缀")
        self.apply_tier_btn.setEnabled(False)
        self.tier_status_label = QLabel("尚未扫描。聚合键 = 去掉 TierXX_ 与开头 IDXX_ 后的 stem。")
        self.tier_status_label.setObjectName("context")
        for widget in [self.choose_tier_root_btn, self.scan_tier_btn, self.export_tier_btn, QLabel("目标 Tier:"), self.tier_input, self.plan_tier_btn, self.apply_tier_btn]:
            cmd.addWidget(widget)
        cmd.addStretch(1)
        cmd.addWidget(self.tier_status_label)
        layout.addWidget(command)
        self.choose_tier_root_btn.clicked.connect(self.choose_tier_root)
        self.scan_tier_btn.clicked.connect(self.scan_tier_root)
        self.export_tier_btn.clicked.connect(self.export_tier_scan)
        self.plan_tier_btn.clicked.connect(self.build_tier_plan)
        self.apply_tier_btn.clicked.connect(self.apply_tier_plan)

        splitter = QSplitter(Qt.Horizontal)
        left = QFrame()
        left.setObjectName("glassPanel")
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("Tier 聚合大盘（同 stem 组）"))
        self.tier_group_table = QTableView()
        self.tier_group_table.setModel(self.tier_group_model)
        self.tier_group_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        left_layout.addWidget(self.tier_group_table, 1)
        splitter.addWidget(left)

        right = QFrame()
        right.setObjectName("glassPanel")
        right_layout = QVBoxLayout(right)
        right_layout.addWidget(QLabel("Dry-run 重命名计划"))
        self.tier_plan_table = QTableView()
        self.tier_plan_table.setModel(self.tier_plan_model)
        self.tier_plan_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        right_layout.addWidget(self.tier_plan_table, 1)
        self.tier_detail_text = QTextEdit()
        self.tier_detail_text.setReadOnly(True)
        self.tier_detail_text.setMaximumHeight(190)
        self.tier_detail_text.setText(
            "功能说明：\n"
            "1. 已带 TierXX_ 的图片或标签视为已标记。\n"
            "2. 聚合键 = 文件 stem 去掉 TierXX_，再去掉开头 IDXX_。\n"
            "3. 执行加前缀会把未标记文件重命名为 TierXX_<原文件名>。\n"
            "4. 图片与标签都纳入计划；目标冲突会阻断执行。\n"
            "5. 所有结论保持 PENDING_AUDIT。"
        )
        right_layout.addWidget(self.tier_detail_text)
        splitter.addWidget(right)
        splitter.setSizes([820, 760])
        layout.addWidget(splitter, 1)
        return page

    def choose_tier_root(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "选择主库根目录", str(PROGRAMME_DIR.parent / "Source_Archive"))
        if folder:
            self.tier_root = Path(folder)
            self.scan_tier_root()

    def scan_tier_root(self) -> None:
        if self.tier_root is None:
            self.show_message("请先选择主库根目录。")
            return
        self.tier_generation += 1
        self.tier_status_label.setText(f"正在扫描：{self.tier_root}")
        self.tier_plan = None
        self.apply_tier_btn.setEnabled(False)
        self.tier_plan_model.set_rows([])
        worker = TierScanWorker(self.tier_generation, self.tier_root)
        worker.signals.done.connect(self.on_tier_scan_done)
        worker.signals.error.connect(self.on_tier_scan_error)
        self.thread_pool.start(worker)
        self.logger.event("tier_prefix_scan_start", root=str(self.tier_root))

    def on_tier_scan_done(self, generation: int, result: TierScanResult) -> None:
        if generation != self.tier_generation:
            return
        self.tier_scan_result = result
        rows = [
            [
                group.canonical_stem,
                group.status,
                group.image_count,
                group.label_count,
                group.marked_count,
                group.unmarked_count,
                ", ".join(sorted(group.dataset_ids)[:8]),
                ", ".join(sorted(group.tiers)),
                len(group.issues),
            ]
            for group in result.groups[:10000]
        ]
        self.tier_group_model.set_rows(rows)
        self.tier_status_label.setText(
            f"扫描完成：files={result.file_count:,} | images={result.image_count:,} | labels={result.label_count:,} | "
            f"marked={result.marked_count:,} | unmarked={result.unmarked_count:,} | issues={result.issue_count:,} | {result.duration_ms:.1f} ms"
        )
        self.tier_detail_text.setText(
            f"扫描根目录：{result.root}\n"
            f"聚合组数：{len(result.groups):,}\n"
            f"已标记文件：{result.marked_count:,}\n"
            f"未标记文件：{result.unmarked_count:,}\n"
            f"异常数：{result.issue_count:,}\n\n"
            "下一步：输入目标 Tier，例如 Tier01，然后点击“生成 dry-run 计划”。"
        )
        self.logger.event(
            "tier_prefix_scan_done",
            root=str(result.root),
            file_count=result.file_count,
            image_count=result.image_count,
            label_count=result.label_count,
            marked_count=result.marked_count,
            unmarked_count=result.unmarked_count,
            issue_count=result.issue_count,
            duration_ms=round(result.duration_ms, 3),
        )

    def on_tier_scan_error(self, generation: int, error: str) -> None:
        if generation != self.tier_generation:
            return
        self.tier_status_label.setText(f"扫描失败：{error}")
        self.logger.event("tier_prefix_scan_failed", root=str(self.tier_root or ""), error=error)

    def build_tier_plan(self) -> None:
        if self.tier_root is None:
            self.show_message("请先选择主库根目录。")
            return
        try:
            plan = TierPrefixGovernanceService(self.tier_root).build_plan(self.tier_input.text(), only_unmarked=True)
        except Exception as exc:
            self.show_message(str(exc))
            return
        self.tier_plan = plan
        rows = [[operation.kind, operation.canonical_stem, str(operation.source), str(operation.target)] for operation in plan.operations[:20000]]
        self.tier_plan_model.set_rows(rows)
        self.apply_tier_btn.setEnabled(plan.can_apply)
        blocked_text = "\n".join(plan.blocked_reasons[:30])
        self.tier_detail_text.setText(
            f"Dry-run 计划：{plan.tier}\n"
            f"待重命名文件：{len(plan.operations):,}\n"
            f"阻断项：{len(plan.blocked_reasons):,}\n"
            f"可执行：{'YES' if plan.can_apply else 'NO'}\n\n"
            f"{blocked_text}"
        )
        self.logger.event(
            "tier_prefix_plan_built",
            root=str(plan.root),
            tier=plan.tier,
            operation_count=len(plan.operations),
            blocked_count=len(plan.blocked_reasons),
        )

    def apply_tier_plan(self) -> None:
        if self.tier_plan is None:
            self.show_message("请先生成 dry-run 计划。")
            return
        if not self.tier_plan.can_apply:
            self.show_message("当前计划为空或存在目标冲突，不能执行。")
            return
        if self.run_mode != "test":
            ok = QMessageBox.question(
                self,
                "确认执行 Tier 前缀治理",
                f"将重命名 {len(self.tier_plan.operations):,} 个图片/标签文件。\n"
                f"目标前缀：{self.tier_plan.tier}_\n\n此操作会改文件名，但不删除文件。是否继续？",
            )
            if ok != QMessageBox.Yes:
                return
        try:
            journal = TierPrefixGovernanceService(self.tier_plan.root).apply_plan(self.tier_plan)
            self.tier_status_label.setText(f"执行完成：{journal.name}")
            self.tier_detail_text.setText(f"Tier 前缀治理已执行。\nJournal: {journal}\n建议重新扫描确认状态。")
            self.logger.event("tier_prefix_plan_applied", root=str(self.tier_plan.root), journal=str(journal), operation_count=len(self.tier_plan.operations))
            self.scan_tier_root()
        except Exception as exc:
            self.show_message(str(exc))
            self.logger.event("tier_prefix_plan_failed", root=str(self.tier_plan.root), error=str(exc))

    def export_tier_scan(self) -> None:
        if self.tier_scan_result is None:
            self.show_message("请先扫描 Tier 状态。")
            return
        path = TierPrefixGovernanceService(self.tier_scan_result.root).export_scan_report(self.tier_scan_result)
        self.show_message(f"Tier 扫描报告已导出：{path}")

    def build_history_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        command = QFrame()
        command.setObjectName("commandBar")
        cmd = QHBoxLayout(command)
        self.refresh_history_btn = QPushButton("刷新操作记录")
        self.open_history_log_btn = QPushButton("打开记录日志文件夹")
        self.history_path_label = QLabel(f"记录文件：{self.manual_history_path}")
        self.history_path_label.setObjectName("context")
        cmd.addWidget(self.refresh_history_btn)
        cmd.addWidget(self.open_history_log_btn)
        cmd.addStretch(1)
        cmd.addWidget(self.history_path_label)
        layout.addWidget(command)
        self.refresh_history_btn.clicked.connect(self.load_manual_history)
        self.open_history_log_btn.clicked.connect(self.open_manual_history_folder)

        info = QLabel("双击一条历史记录可回到对应 Manual Objects 组。打开后会读取当前 manual_selection.json，允许重新复选并保存更改。")
        info.setWordWrap(True)
        info.setObjectName("statusChip")
        layout.addWidget(info)

        self.history_table = QTableView()
        self.history_table.setModel(self.history_model)
        self.history_table.doubleClicked.connect(self.open_history_record_from_table)
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.history_table, 1)
        self.load_manual_history()
        return page

    def load_manual_history(self) -> None:
        records: list[dict[str, Any]] = []
        if self.manual_history_path.exists():
            try:
                for line in self.manual_history_path.read_text(encoding="utf-8").splitlines():
                    if not line.strip():
                        continue
                    try:
                        records.append(json.loads(line))
                    except Exception:
                        continue
            except Exception as exc:
                self.global_status.setText(f"操作记录读取失败：{exc}")
        records = records[-1000:]
        records.reverse()
        self.manual_history_rows = records
        self.history_row_records = records
        rows = [
            [
                record.get("saved_at", ""),
                record.get("review_status", ""),
                record.get("reason", ""),
                record.get("size_bucket", ""),
                record.get("group_identity") or record.get("group_folder", ""),
                ", ".join(record.get("keep_item_ids", []) or []),
                ", ".join(record.get("remove_item_ids", []) or []),
                record.get("group_dir", ""),
            ]
            for record in records
        ]
        self.history_model.set_rows(rows)
        if hasattr(self, "history_path_label"):
            self.history_path_label.setText(f"记录文件：{self.manual_history_path} | 最近 {len(rows)} 条")

    def open_manual_history_folder(self) -> None:
        self.manual_history_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.Popen(["explorer", str(self.manual_history_path.parent)])

    def append_manual_history_record(
        self,
        group: ManualObjectGroup,
        review_status: str,
        keep: list[str],
        remove: list[str],
        path: Path,
        previous_selection_path: Path | None = None,
        had_previous_selection: bool = False,
    ) -> None:
        record = {
            "schema_version": "CIVL7009_MANUAL_OBJECT_HISTORY_V1",
            "event_type": "SAVE_SELECTION",
            "saved_at": datetime.now().isoformat(timespec="seconds"),
            "software_version": UI_VERSION,
            "manual_root": str(self.manual_root or ""),
            "group_key": group.group_key,
            "reason": group.reason,
            "size_bucket": group.size_bucket,
            "group_folder": group.group_name,
            "group_identity": f"{group.reason}/{group.size_bucket}/{group.group_name}",
            "group_dir": str(group.group_dir),
            "review_status": review_status,
            "keep_item_ids": keep,
            "remove_item_ids": remove,
            "selection_path": str(path),
            "had_previous_selection": had_previous_selection,
            "previous_selection_path": str(previous_selection_path or ""),
        }
        self.manual_history_path.parent.mkdir(parents=True, exist_ok=True)
        with self.manual_history_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        self.last_manual_save_record = record
        if hasattr(self, "undo_manual_btn"):
            self.undo_manual_btn.setEnabled(True)
        self.manual_history_rows.insert(0, record)
        self.load_manual_history()

    @staticmethod
    def latest_selection_history_file(group_dir: Path) -> Path | None:
        history_dir = group_dir / "_selection_history"
        if not history_dir.exists():
            return None
        candidates = [
            path for path in history_dir.glob("manual_selection_*.json")
            if len(path.stem.removeprefix("manual_selection_")) == 14 and path.stem.removeprefix("manual_selection_").isdigit()
        ]
        candidates = sorted(
            candidates,
            key=lambda path: (path.stat().st_mtime_ns, path.name),
            reverse=True,
        )
        return candidates[0] if candidates else None

    def undo_last_manual_review_operation(self) -> None:
        record = self.last_manual_save_record
        if not record:
            self.show_message("当前会话还没有可撤销的复核保存操作。")
            return
        group_dir = Path(str(record.get("group_dir", "")))
        selection_path = Path(str(record.get("selection_path", group_dir / "manual_selection.json")))
        if not group_dir.exists():
            self.show_message(f"撤销失败：组目录不存在。\n{group_dir}")
            return
        if self.run_mode != "test":
            ok = QMessageBox.question(
                self,
                "确认撤销上一次复核",
                f"将撤销最近一次保存：\n{record.get('group_identity', record.get('group_key', ''))}\n\n"
                "若保存前已有 selection，将恢复旧文件；否则会删除本次新写入的 manual_selection.json。",
            )
            if ok != QMessageBox.Yes:
                return
        try:
            undo_dir = group_dir / "_selection_history"
            undo_dir.mkdir(exist_ok=True)
            current_backup = undo_dir / f"manual_selection_undo_current_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
            if selection_path.exists():
                shutil.copy2(selection_path, current_backup)
            previous_path_text = str(record.get("previous_selection_path", ""))
            previous_path = Path(previous_path_text) if previous_path_text else None
            had_previous = bool(record.get("had_previous_selection"))
            if had_previous and previous_path and previous_path.exists():
                shutil.copy2(previous_path, selection_path)
                action = "UNDO_RESTORED_PREVIOUS"
            else:
                if selection_path.exists():
                    selection_path.unlink()
                action = "UNDO_REMOVED_NEW_SELECTION"
            undo_record = {
                "schema_version": "CIVL7009_MANUAL_OBJECT_HISTORY_V1",
                "event_type": "UNDO_SELECTION",
                "saved_at": datetime.now().isoformat(timespec="seconds"),
                "software_version": UI_VERSION,
                "manual_root": str(self.manual_root or ""),
                "group_key": str(record.get("group_key", "")),
                "reason": str(record.get("reason", "")),
                "size_bucket": str(record.get("size_bucket", "")),
                "group_folder": str(record.get("group_folder", "")),
                "group_identity": str(record.get("group_identity", "")),
                "group_dir": str(group_dir),
                "review_status": action,
                "keep_item_ids": [],
                "remove_item_ids": [],
                "selection_path": str(selection_path),
                "restored_from": str(previous_path or ""),
                "current_backup_path": str(current_backup if current_backup.exists() else ""),
            }
            self.manual_history_path.parent.mkdir(parents=True, exist_ok=True)
            with self.manual_history_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(undo_record, ensure_ascii=False) + "\n")
            self.last_manual_save_record = None
            self.undo_manual_btn.setEnabled(False)
            self.logger.event("manual_objects_selection_undone", group_key=undo_record["group_key"], action=action, selection_path=str(selection_path))
            self.load_manual_history()
            group_key = str(record.get("group_key", ""))
            if self.manual_index_service and self.current_manual_summary and self.current_manual_summary.group_key == group_key:
                self.manual_index_service.refresh_summary_selection_status(self.current_manual_summary)
                self.current_manual_group = self.manual_index_service.load_group_from_summary(self.current_manual_summary)
                self.manual_group_cache[group_key] = self.current_manual_group
                self.render_manual_group()
                self.refresh_manual_group_row()
                self.refresh_conflicts_for_manual_group(self.current_manual_group)
            elif group_key:
                self.open_manual_group_by_key(group_key)
            self.global_status.setText(f"已撤销上一次复核操作：{action}")
        except Exception as exc:
            self.show_message(f"撤销失败：{exc}")

    def open_history_record_from_table(self, index: QModelIndex) -> None:
        if not index.isValid() or not (0 <= index.row() < len(self.history_row_records)):
            return
        record = self.history_row_records[index.row()]
        group_key = str(record.get("group_key", ""))
        manual_root = Path(str(record.get("manual_root", ""))) if record.get("manual_root") else None
        if not group_key:
            return
        self.set_workflow(1)
        if manual_root and manual_root.exists() and (self.manual_root is None or self.manual_root.resolve() != manual_root.resolve()):
            self.pending_history_group_key = group_key
            self.pending_history_manual_root = manual_root
            self.load_manual_root(manual_root)
            return
        self.open_manual_group_by_key(group_key)

    def open_manual_group_by_key(self, group_key: str) -> bool:
        for summary in self.manual_all_summaries:
            if summary.group_key == group_key:
                if summary not in self.manual_filtered_summaries:
                    self.reason_filter.setCurrentIndex(0)
                    self.bucket_filter.setCurrentIndex(0)
                    self.status_filter.setCurrentIndex(0)
                    self.selection_filter.setCurrentIndex(0)
                    self.dataset_filter.clear()
                    self.class_filter.clear()
                    self.apply_manual_filters()
                if summary in self.manual_filtered_summaries:
                    index = self.manual_filtered_summaries.index(summary)
                    target_page = index // self.manual_page_size
                    if target_page != self.manual_page:
                        self.manual_page = target_page
                        self.render_manual_group_page()
                    visible_index = index % self.manual_page_size
                    if 0 <= visible_index < self.manual_group_model.rowCount():
                        self.manual_group_table.selectRow(visible_index)
                self.current_manual_summary = summary
                self.open_manual_group_from_summary(summary)
                return True
        self.global_status.setText(f"未找到历史记录对应 group：{group_key}")
        return False

    def build_diagnostics_page(self) -> QWidget:
        page = QFrame()
        page.setObjectName("glassPanel")
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("诊断与设置（Diagnostics & Settings）"))
        text = QTextEdit()
        text.setReadOnly(True)
        text.setText(
            f"UI version: {UI_VERSION}\n"
            f"Programme version: {PROGRAMME_VERSION}\n"
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
        QShortcut(QKeySequence("A"), self).activated.connect(lambda: self.step_workflow_record(-1))
        QShortcut(QKeySequence("D"), self).activated.connect(lambda: self.step_workflow_record(1))
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
        self.manual_class_service = ManualObjectsClassService(self.manual_root)
        self.manual_index_result = None
        self.manual_all_summaries = []
        self.manual_filtered_summaries = []
        self.manual_row_summary_map = []
        self.manual_group_cache = {}
        self.current_manual_group = None
        self.current_manual_summary = None
        self.manual_dataset_ids = []
        self.manual_class_statuses = []
        self.manual_class_maps = {}
        self.manual_missing_class_notice_shown = False
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
        self.manual_class_service = ManualObjectsClassService(result.root)
        self.manual_all_summaries = result.summaries
        self.refresh_manual_class_statuses(show_dialog_if_missing=True)
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
        self.start_conflict_index_build()
        if self.pending_history_group_key:
            group_key = self.pending_history_group_key
            self.pending_history_group_key = None
            self.open_manual_group_by_key(group_key)

    def on_manual_index_error(self, generation: int, error: str) -> None:
        if generation != self.manual_generation:
            return
        self.manual_root_label.setText(f"Manual_Objects: {self.manual_root} | index 读取失败")
        self.logger.event("manual_objects_index_failed", manual_root=str(self.manual_root), error=error)
        self.show_message(error)

    def start_conflict_index_build(self, quiet: bool = False) -> None:
        if self.manual_root is None:
            self.global_status.setText("尚未选择 Manual_Objects 根目录，无法构建冲突索引。")
            return
        self.conflict_index_quiet = quiet
        generation = self.manual_generation
        if hasattr(self, "conflict_status_label"):
            self.conflict_status_label.setText("冲突索引：后台构建中...")
        if not quiet:
            self.global_status.setText("正在后台构建冲突索引（只读 index + selection JSON）。")
        self.logger.event("manual_objects_conflict_index_start", manual_root=str(self.manual_root))
        worker = ConflictIndexWorker(generation, self.manual_root)
        worker.signals.done.connect(self.on_conflict_index_done)
        worker.signals.error.connect(self.on_conflict_index_error)
        self.thread_pool.start(worker)

    def on_conflict_index_done(self, generation: int, service: ConflictAwarenessService, result: ConflictIndex) -> None:
        if generation != self.manual_generation:
            return
        self.conflict_service = service
        self.conflict_index = result
        if hasattr(self, "conflict_status_label"):
            self.conflict_status_label.setText(
                f"冲突索引：objects={len(result.objects):,} | selections={result.selection_count:,} | {result.duration_ms:.1f} ms"
            )
        if not self.conflict_index_quiet:
            self.global_status.setText(f"冲突索引已完成：{len(result.objects):,} 个 source object。")
        self.conflict_index_quiet = False
        self.logger.event(
            "manual_objects_conflict_index_done",
            manual_root=str(result.root),
            object_count=len(result.objects),
            row_count=result.row_count,
            selection_count=result.selection_count,
            duration_ms=round(result.duration_ms, 3),
            issue_count=len(result.issues),
        )
        previous_key = self.pending_conflict_refresh_source_key or (self.current_conflict_object.source_object_key if self.current_conflict_object else "")
        self.render_conflict_queue()
        if previous_key and result.source_map.get(previous_key):
            self.current_conflict_object = result.source_map[previous_key]
            if hasattr(self, "conflict_evidence_layout"):
                self.render_conflict_object(self.current_conflict_object)
        self.pending_conflict_refresh_source_key = ""
        self.update_current_manual_conflict_chips()

    def on_conflict_index_error(self, generation: int, error: str) -> None:
        if generation != self.manual_generation:
            return
        if hasattr(self, "conflict_status_label"):
            self.conflict_status_label.setText("冲突索引：构建失败")
        if not self.conflict_index_quiet:
            self.global_status.setText(f"冲突索引构建失败：{error}")
        self.conflict_index_quiet = False
        self.logger.event("manual_objects_conflict_index_failed", manual_root=str(self.manual_root or ""), error=error)

    def refresh_current_conflict_object(self) -> None:
        if self.current_conflict_object is None:
            self.show_message("尚未选择 source object，无法重读当前对象状态。")
            return
        self.refresh_conflict_object_by_key(self.current_conflict_object.source_object_key, show_message=True)

    def refresh_conflict_object_by_key(self, source_object_key: str, show_message: bool = False) -> SourceObjectConflict | None:
        if not source_object_key:
            return None
        if self.conflict_service is None:
            if show_message:
                self.show_message("冲突服务尚未就绪，请先构建一次冲突索引。")
            return None
        try:
            refreshed = self.conflict_service.refresh_source_object(source_object_key)
        except Exception as exc:
            self.logger.event("manual_objects_conflict_object_refresh_failed", source_object_key=source_object_key, error=str(exc))
            if show_message:
                self.show_message(f"重读当前对象状态失败：{exc}")
            return None
        if refreshed is None:
            if self.conflict_index is not None:
                self.conflict_index = self.conflict_service.latest_index
                self.render_conflict_queue()
            if show_message:
                self.show_message("当前 source object 已不在冲突索引中。")
            return None
        self.conflict_index = self.conflict_service.latest_index
        previous_row_key = refreshed.source_object_key
        self.current_conflict_object = refreshed
        if hasattr(self, "conflict_queue_model"):
            self.render_conflict_queue()
            for row, obj in enumerate(self.conflict_row_objects):
                if obj.source_object_key == previous_row_key:
                    self.conflict_queue_table.selectRow(row)
                    break
        if hasattr(self, "conflict_evidence_layout"):
            self.render_conflict_object(refreshed)
        self.update_current_manual_conflict_chips()
        if hasattr(self, "conflict_status_label"):
            self.conflict_status_label.setText(
                f"当前对象已重读：{refreshed.conflict_state} | events={refreshed.related_event_count}"
            )
        self.global_status.setText(f"当前对象状态已重读：{refreshed.conflict_state}")
        self.logger.event(
            "manual_objects_conflict_object_refreshed",
            source_object_key=source_object_key,
            conflict_state=refreshed.conflict_state,
            related_event_count=refreshed.related_event_count,
        )
        return refreshed

    def refresh_conflicts_for_manual_group(self, group: ManualObjectGroup | None) -> None:
        if group is None or self.conflict_service is None:
            return
        refreshed_current = False
        for item in group.items:
            record = self.conflict_service.item_records.get((group.group_key, item.item_id))
            if record is None:
                continue
            refreshed = self.conflict_service.refresh_source_object(record.source_object_key)
            if self.current_conflict_object and self.current_conflict_object.source_object_key == record.source_object_key and refreshed:
                self.current_conflict_object = refreshed
                refreshed_current = True
        self.conflict_index = self.conflict_service.latest_index
        if hasattr(self, "conflict_queue_model"):
            self.render_conflict_queue()
        if refreshed_current and hasattr(self, "conflict_evidence_layout"):
            self.render_conflict_object(self.current_conflict_object)
        self.update_current_manual_conflict_chips()

    def refresh_manual_class_statuses(self, show_dialog_if_missing: bool = False) -> None:
        if self.manual_class_service is None:
            self.manual_class_statuses = []
            self.manual_class_maps = {}
            return
        self.manual_dataset_ids = ManualObjectsClassService.dataset_ids_from_summaries(self.manual_all_summaries)
        self.manual_class_statuses = self.manual_class_service.ensure_id_class_dirs(self.manual_dataset_ids)
        self.manual_class_maps = self.manual_class_service.load_class_maps()
        missing = [status for status in self.manual_class_statuses if status.status in {"MISSING", "EMPTY"}]
        warning = [status for status in self.manual_class_statuses if status.status == "MULTIPLE"]
        self.logger.event(
            "manual_objects_class_status_refreshed",
            manual_root=str(self.manual_root or ""),
            dataset_id_count=len(self.manual_dataset_ids),
            missing_count=len(missing),
            warning_count=len(warning),
        )
        if missing:
            self.global_status.setText(f"类别文件缺失：{len(missing)} 个 ID，请点击“类别文件检测”。")
            self.manual_load_status.setText(
                f"类别文件缺失：{len(missing)}/{len(self.manual_class_statuses)} 个 ID 尚无可用类别 txt。"
                "可点击“类别文件检测”打开对应 ID_Classes 目录。"
            )
        elif warning:
            self.global_status.setText(f"类别文件警告：{len(warning)} 个 ID 有多个有效 txt。")
            self.manual_load_status.setText(f"类别文件可用，但 {len(warning)} 个 ID 有多个 txt；已按文件名排序使用第一个。")
        elif self.manual_class_statuses:
            self.global_status.setText(f"类别文件检测通过：{len(self.manual_class_statuses)} 个 ID。")
            self.manual_load_status.setText(f"类别文件检测通过：{len(self.manual_class_statuses)} 个 ID 均有可用类别 txt。")
        if show_dialog_if_missing and missing and not self.manual_missing_class_notice_shown and self.run_mode != "test":
            self.manual_missing_class_notice_shown = True
            self.show_class_files_dialog()

    def show_class_files_dialog(self) -> None:
        if self.manual_class_service is None:
            self.show_message("尚未选择 Manual_Objects 根目录。")
            return
        dataset_ids = self.manual_dataset_ids or ManualObjectsClassService.dataset_ids_from_summaries(self.manual_all_summaries)
        dialog = ClassFilesDialog(self, self.manual_class_service, dataset_ids)
        dialog.exec()
        self.manual_class_statuses = dialog.statuses
        self.manual_class_maps = self.manual_class_service.load_class_maps()
        if self.current_manual_group is not None and self.manual_draw_bboxes:
            self.render_manual_group()

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
        filters = self.current_manual_filters()
        base_filters = ManualObjectsFilter(
            reason=filters.reason,
            bucket=filters.bucket,
            dataset_id=filters.dataset_id,
            label_class=filters.label_class,
            copy_status=filters.copy_status,
        )
        rows = self.manual_index_service.filter_summaries(self.manual_all_summaries, base_filters)
        if filters.review_status or filters.selection_presence:
            self.refresh_manual_selection_statuses(rows)
            rows = self.manual_index_service.filter_summaries(
                rows,
                ManualObjectsFilter(review_status=filters.review_status, selection_presence=filters.selection_presence),
            )
        self.manual_filtered_summaries = rows
        self.render_manual_group_page()

    def refresh_manual_selection_statuses(self, summaries: list[ManualGroupSummary]) -> None:
        if self.manual_index_service is None:
            return
        for summary in summaries:
            self.manual_index_service.refresh_summary_selection_status(summary)

    def refresh_manual_status_dashboard(self) -> None:
        if self.manual_index_service is None or not self.manual_all_summaries:
            self.global_status.setText("尚未加载 Manual_Objects 全局大盘。")
            return
        started = time.perf_counter()
        self.refresh_manual_selection_statuses(self.manual_all_summaries)
        elapsed_ms = (time.perf_counter() - started) * 1000
        status_counts: dict[str, int] = {}
        for summary in self.manual_all_summaries:
            status_counts[summary.selection_status] = status_counts.get(summary.selection_status, 0) + 1
        self.apply_manual_filters()
        counts_text = " | ".join(f"{key}: {value:,}" for key, value in sorted(status_counts.items()))
        self.global_status.setText(f"全目录状态已刷新：{counts_text}")
        self.manual_load_status.setText(f"全目录 selection 状态刷新完成，用时 {elapsed_ms:.1f} ms。\n{counts_text}")
        self.logger.event(
            "manual_objects_status_dashboard_refreshed",
            manual_root=str(self.manual_root or ""),
            group_count=len(self.manual_all_summaries),
            duration_ms=round(elapsed_ms, 3),
            status_counts=status_counts,
        )

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
        filters = self.current_manual_filters()
        if not filters.review_status and not filters.selection_presence:
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
        self.select_pending_conflict_item()
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
        self.manual_preview_index = -1
        group = self.current_manual_group
        if group is None:
            self.manual_empty.setVisible(True)
            return
        self.manual_empty.setVisible(False)
        visible_items = group.items
        self.manual_thumbnail_expected = len(visible_items)
        self.manual_thumbnail_done = 0
        self.manual_thumbnail_failed = {}
        self.manual_thumbnail_pending = set()
        self.manual_thumbnail_workers = {}
        self.manual_thumbnail_queue = []
        self.update_manual_load_status("准备加载当前组全部候选预览图。")
        for index, item in enumerate(visible_items):
            card = ManualObjectCard(item, index, self.manual_class_maps.get(item.dataset_id, {}))
            card.selected.connect(self.select_manual_item)
            card.activated.connect(lambda item_id: self.open_manual_item_viewer(item_id))
            self.manual_cards.append(card)
            self.manual_cards_by_item[item.item_id] = card
            row, col = divmod(index, 3)
            self.manual_grid.addWidget(card, row, col)
            self.manual_thumbnail_queue.append(item.item_id)
        if self.manual_cards:
            self.set_manual_preview_index(0)
        if len(group.items) > 30:
            notice = QLabel(f"N20_PLUS 大组：已创建全部 {len(group.items)} 张候选卡片，可滚动查看；缩略图正在分批异步加载。")
            notice.setObjectName("statusChip")
            self.manual_grid.addWidget(notice, (len(visible_items) + 2) // 3, 0, 1, 3)
        self.request_next_manual_thumbnail_batch(self.manual_generation)
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
        self.update_current_manual_conflict_chips()

    def update_current_manual_conflict_chips(self) -> None:
        group = self.current_manual_group
        if group is None:
            if hasattr(self, "manual_conflict_explanation"):
                self.manual_conflict_explanation.setText("当前对象冲突说明：尚未打开候选组。")
            return
        service = self.conflict_service
        for card in self.manual_cards:
            conflict = service.conflict_for_item(group.group_key, card.item.item_id) if service is not None else None
            if conflict is None:
                card.set_conflict_status("PENDING_INDEX" if service is None else "NO_KNOWN_CONFLICT", "冲突索引尚未覆盖该对象。")
                continue
            state = "WEAK_IDENTITY" if conflict.weak_identity and conflict.conflict_state == "UNRESOLVED_OR_PARTIAL" else conflict.conflict_state
            card.set_conflict_status(state, service.explanation_for(conflict))
        self.update_manual_conflict_explanation_for_current_preview()

    def update_manual_conflict_explanation_for_current_preview(self) -> None:
        if not hasattr(self, "manual_conflict_explanation"):
            return
        if self.current_manual_group is None or not self.manual_cards or self.manual_preview_index < 0:
            self.manual_conflict_explanation.setText("当前对象冲突说明：等待选择候选图片。")
            return
        item = self.manual_cards[self.manual_preview_index].item
        if self.conflict_service is None:
            self.manual_conflict_explanation.setText("当前对象冲突说明：冲突索引仍在后台构建。保存前仍会执行本组选择校验。")
            return
        conflict = self.conflict_service.conflict_for_item(self.current_manual_group.group_key, item.item_id)
        self.manual_conflict_explanation.setText(self.conflict_service.explanation_for(conflict))

    def class_map_signature(self, item: ManualObjectItem) -> str:
        class_map = self.manual_class_maps.get(item.dataset_id, {})
        if not class_map:
            return ""
        return "|".join(f"{key}:{value}" for key, value in sorted(class_map.items(), key=lambda pair: int(pair[0]) if pair[0].isdigit() else 999999))

    def manual_thumbnail_key(self, item: ManualObjectItem) -> tuple[str, int, int, str, int, int, bool, str]:
        try:
            stat = item.image_path.stat()
            image_size = stat.st_size
            image_mtime = getattr(stat, "st_mtime_ns", int(stat.st_mtime * 1_000_000_000))
        except Exception:
            image_size = 0
            image_mtime = 0
        try:
            label_stat = item.label_path.stat()
            label_size = label_stat.st_size
            label_mtime = getattr(label_stat, "st_mtime_ns", int(label_stat.st_mtime * 1_000_000_000))
        except Exception:
            label_size = 0
            label_mtime = 0
        return (
            str(item.image_path),
            image_size,
            image_mtime,
            str(item.label_path),
            label_size,
            label_mtime,
            self.manual_draw_bboxes,
            self.class_map_signature(item),
        )

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
        class_map = self.manual_class_maps.get(item.dataset_id, {})
        worker = ThumbnailWorker(generation, item.item_id, item.image_path, item.label_path, self.manual_draw_bboxes, class_map)
        worker.signals.done.connect(lambda gen, item_id, payload, cache_key=key: self.on_manual_thumbnail_done(gen, item_id, payload, cache_key))
        worker.signals.error.connect(self.on_manual_thumbnail_error)
        self.manual_thumbnail_workers[item.item_id] = worker
        self.thread_pool.start(worker)

    def request_next_manual_thumbnail_batch(self, generation: int | None = None) -> None:
        if generation is not None and generation != self.manual_generation:
            return
        if self.current_manual_group is None:
            return
        batch: list[str] = []
        while self.manual_thumbnail_queue and len(batch) < self.manual_thumbnail_batch_size:
            item_id = self.manual_thumbnail_queue.pop(0)
            if item_id in self.manual_thumbnail_pending:
                continue
            if item_id not in self.manual_cards_by_item:
                continue
            batch.append(item_id)
        for item_id in batch:
            card = self.manual_cards_by_item.get(item_id)
            if card is not None:
                self.request_manual_thumbnail(card.item)
        if self.manual_thumbnail_queue:
            QTimer.singleShot(35, lambda gen=self.manual_generation: self.request_next_manual_thumbnail_batch(gen))

    def on_manual_thumbnail_done(self, generation: int, item_id: str, payload: bytes, cache_key: tuple[Any, ...]) -> None:
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
        queued = len(self.manual_thumbnail_queue)
        failed = len(self.manual_thumbnail_failed)
        done = self.manual_thumbnail_done
        lines = [
            f"当前组预览：已完成 {done}/{expected}，进行中 {pending}，排队 {queued}，失败 {failed}",
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
        for item in group.items:
            self.manual_thumbnail_cache.pop(self.manual_thumbnail_key(item), None)
        self.logger.event("manual_thumbnail_refresh_requested", group_key=group.group_key, visible_count=len(group.items))
        self.render_manual_group()

    def select_manual_item(self, item_id: str) -> None:
        group = self.current_manual_group
        if group is None:
            return
        for index, item in enumerate(group.items[: len(self.manual_cards)]):
            if item.item_id == item_id:
                self.set_manual_preview_index(index)
                break
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
        if not self.manual_multi_keep and self.auto_next_same_bucket_box.isChecked():
            if not self.manual_click_save_in_progress:
                self.manual_click_save_in_progress = True
                self.global_status.setText("已选择保留项，准备保存并进入同 N 下一组...")
                QTimer.singleShot(80, lambda: self.save_manual_selection("APPROVED", force_next=True))

    def set_manual_preview_index(self, index: int) -> None:
        if not self.manual_cards:
            self.manual_preview_index = -1
            return
        self.manual_preview_index = max(0, min(index, len(self.manual_cards) - 1))
        for card_index, card in enumerate(self.manual_cards):
            card.set_preview_selected(card_index == self.manual_preview_index)
        item = self.manual_cards[self.manual_preview_index].item
        self.global_status.setText(f"预览焦点：{item.dataset_id} / {item.item_id}（A/D 可切换上一张/下一张）")

        self.update_manual_conflict_explanation_for_current_preview()

    def step_manual_preview_item(self, delta: int) -> None:
        if self.stack.currentIndex() != 1 or not self.manual_cards:
            return
        current = self.manual_preview_index if self.manual_preview_index >= 0 else 0
        self.set_manual_preview_index((current + delta) % len(self.manual_cards))

    def step_workflow_record(self, delta: int) -> None:
        page = self.stack.currentIndex()
        if page == 0:
            self.step_source_group(delta)
        elif page == 1:
            self.step_manual_group_record(delta)
        elif page == 2:
            self.step_conflict_object_record(delta)

    def step_manual_group_record(self, delta: int) -> None:
        if not self.manual_filtered_summaries:
            return
        current_key = self.current_manual_summary.group_key if self.current_manual_summary else ""
        try:
            current = next(index for index, summary in enumerate(self.manual_filtered_summaries) if summary.group_key == current_key)
        except StopIteration:
            current = self.manual_page * self.manual_page_size
        target = max(0, min(len(self.manual_filtered_summaries) - 1, current + delta))
        target_page = target // self.manual_page_size
        if target_page != self.manual_page:
            self.manual_page = target_page
            self.render_manual_group_page()
        summary = self.manual_filtered_summaries[target]
        self.open_manual_group_from_summary(summary)
        self.global_status.setText(f"已切换到候选组：{summary.reason}/{summary.size_bucket}/{summary.group_folder}")

    def step_conflict_object_record(self, delta: int) -> None:
        if not self.conflict_row_objects:
            return
        current_key = self.current_conflict_object.source_object_key if self.current_conflict_object else ""
        try:
            current = next(index for index, obj in enumerate(self.conflict_row_objects) if obj.source_object_key == current_key)
        except StopIteration:
            current = 0
        target = max(0, min(len(self.conflict_row_objects) - 1, current + delta))
        self.current_conflict_object = self.conflict_row_objects[target]
        self.render_conflict_object(self.current_conflict_object)
        self.conflict_queue_table.selectRow(target)
        self.global_status.setText(f"已切换到冲突对象：{target + 1}/{len(self.conflict_row_objects)}")

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

    def on_bbox_overlay_changed(self, state: int) -> None:
        self.manual_draw_bboxes = bool(state)
        if self.current_manual_group is not None:
            self.refresh_current_manual_preview()

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
        group_identity = f"{group.reason}/{group.size_bucket}/{group.group_name}"
        selection_path = group.group_dir / "manual_selection.json"
        had_previous_selection = selection_path.exists()
        previous_history_before = self.latest_selection_history_file(group.group_dir)
        if review_status == "ALL_DONE":
            for item in group.items:
                item.selection_state = "KEEP"
            for card in self.manual_cards:
                card.refresh_state("KEEP")
        if review_status == "ALL_OUT":
            for item in group.items:
                item.selection_state = "REMOVE"
            for card in self.manual_cards:
                card.refresh_state("REMOVE")
        keep = [item.item_id for item in group.items if item.selection_state == "KEEP"]
        remove = [item.item_id for item in group.items if item.selection_state == "REMOVE"]
        proposed_decisions = {item_id: "KEEP" for item_id in keep}
        proposed_decisions.update({item_id: "REMOVE" for item_id in remove})
        if review_status == "ALL_OUT":
            proposed_decisions = {item.item_id: "REMOVE" for item in group.items}
        conflict_warnings = self.conflict_service.proposed_conflict_warnings(group.group_key, proposed_decisions) if self.conflict_service else []
        if conflict_warnings:
            warning_text = "本次选择可能制造新的 source-object 冲突：\n" + "\n".join(conflict_warnings[:12])
            self.logger.event(
                "manual_objects_conflict_warning_acknowledged",
                group_key=group.group_key,
                review_status=review_status,
                warning_count=len(conflict_warnings),
                warnings=conflict_warnings[:20],
            )
            if self.run_mode == "test":
                self.global_status.setText("冲突预警已记录；测试模式不弹窗。")
            else:
                QMessageBox.warning(self, "冲突预警", warning_text)
        if self.conflict_service and group.items:
            focus_id = ""
            if 0 <= self.manual_preview_index < len(self.manual_cards):
                focus_id = self.manual_cards[self.manual_preview_index].item.item_id
            focus_id = focus_id or group.items[0].item_id
            record = self.conflict_service.item_records.get((group.group_key, focus_id))
            if record:
                self.pending_conflict_refresh_source_key = record.source_object_key
        try:
            path = self.manual_service.save_selection(group, review_status, keep, remove)
            previous_selection_path = self.latest_selection_history_file(group.group_dir)
            if previous_selection_path == previous_history_before and not had_previous_selection:
                previous_selection_path = None
            self.verify_manual_selection_readback(group, path, review_status, keep, remove)
            self.global_status.setText(f"已写入并校验：{group_identity} -> {path.name}")
            self.logger.event(
                "manual_objects_selection_saved",
                group_key=group.group_key,
                reason=group.reason,
                size_bucket=group.size_bucket,
                group_folder=group.group_name,
                group_identity=group_identity,
                review_status=review_status,
                path=str(path),
            )
            self.logger.event(
                "manual_objects_selection_verified",
                group_key=group.group_key,
                reason=group.reason,
                size_bucket=group.size_bucket,
                group_folder=group.group_name,
                group_identity=group_identity,
                review_status=review_status,
                path=str(path),
                verified=True,
            )
            self.append_manual_history_record(
                group,
                review_status,
                keep,
                remove,
                path,
                previous_selection_path=previous_selection_path if had_previous_selection else None,
                had_previous_selection=had_previous_selection,
            )
            self.refresh_manual_group_row()
            if self.pending_conflict_refresh_source_key:
                self.refresh_conflict_object_by_key(self.pending_conflict_refresh_source_key)
                self.pending_conflict_refresh_source_key = ""
            else:
                self.update_current_manual_conflict_chips()
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
        finally:
            self.manual_click_save_in_progress = False

    def verify_manual_selection_readback(self, group: ManualObjectGroup, path: Path, review_status: str, keep: list[str], remove: list[str]) -> None:
        try:
            saved = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise RuntimeError(f"manual_selection.json 写入后读回失败：{path}\n{exc}") from exc
        expected_keep = sorted(str(item) for item in keep)
        expected_remove = sorted(str(item) for item in remove)
        actual_keep = sorted(str(item) for item in (saved.get("selected_keep_item_ids", []) or []))
        actual_remove = sorted(str(item) for item in (saved.get("selected_remove_item_ids", []) or []))
        problems: list[str] = []
        if str(saved.get("group_key", "")) != str(group.group_key):
            problems.append(f"group_key={saved.get('group_key')!r} != {group.group_key!r}")
        if str(saved.get("review_status", "")) != str(review_status):
            problems.append(f"review_status={saved.get('review_status')!r} != {review_status!r}")
        if actual_keep != expected_keep:
            problems.append(f"KEEP={actual_keep!r} != {expected_keep!r}")
        if actual_remove != expected_remove:
            problems.append(f"REMOVE={actual_remove!r} != {expected_remove!r}")
        if problems:
            raise RuntimeError(f"manual_selection.json 写入后校验失败：{path}\n" + "\n".join(problems))

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
        found_current = False
        for index, summary in enumerate(self.manual_filtered_summaries):
            if summary.group_key == current_group_key:
                start = index + 1
                found_current = True
                break
        if not found_current and current_summary is not None:
            for index, summary in enumerate(self.manual_filtered_summaries):
                if same_bucket and (summary.reason != current_summary.reason or summary.size_bucket != current_summary.size_bucket):
                    continue
                if (summary.group_folder, summary.group_key) > (current_summary.group_folder, current_summary.group_key):
                    start = index
                    break
        candidates = self.manual_filtered_summaries[start:] + self.manual_filtered_summaries[:start]
        for summary in candidates:
            if same_bucket and current_summary is not None:
                if summary.reason != current_summary.reason or summary.size_bucket != current_summary.size_bucket:
                    continue
            if summary.selection_status == UNREVIEWED_STATUS:
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

    def render_conflict_queue(self) -> None:
        if self.conflict_index is None:
            self.conflict_row_objects = []
            self.conflict_queue_model.set_rows([])
            return
        state_filter = str(self.conflict_state_filter.currentData() or "") if hasattr(self, "conflict_state_filter") else ""
        objects = [obj for obj in self.conflict_index.objects if not state_filter or obj.conflict_state == state_filter]
        self.conflict_row_objects = objects
        rows = [
            [
                obj.conflict_state,
                obj.dataset_id,
                obj.image_filename or Path(obj.source_image_project_path).name,
                obj.image_sha256[:12],
                obj.related_event_count,
                obj.keep_event_count,
                obj.remove_event_count,
                (obj.resolution or {}).get("final_object_decision", ""),
            ]
            for obj in objects[:5000]
        ]
        self.conflict_queue_model.set_rows(rows)
        if hasattr(self, "conflict_status_label") and self.conflict_index:
            self.conflict_status_label.setText(f"冲突队列：显示 {len(rows):,}/{len(objects):,}，索引对象 {len(self.conflict_index.objects):,}")

    def open_conflict_object_from_table(self, index: QModelIndex) -> None:
        if not index.isValid() or not (0 <= index.row() < len(self.conflict_row_objects)):
            return
        self.current_conflict_object = self.conflict_row_objects[index.row()]
        self.render_conflict_object(self.current_conflict_object)

    def open_conflict_event_from_table(self, index: QModelIndex) -> None:
        if not index.isValid() or self.current_conflict_object is None:
            return
        row = index.row()
        if 0 <= row < len(self.current_conflict_object.events):
            event = self.current_conflict_object.events[row]
            self.open_manual_group_from_conflict_event(event, event.selected_item.item_id)

    def open_manual_group_from_conflict_event(self, event: ReasonEventDecision, item_id: str = "") -> None:
        self.set_workflow(1)
        self.pending_conflict_item_id = item_id
        if self.open_manual_group_by_key(event.group_key):
            self.select_pending_conflict_item()
        else:
            self.global_status.setText(f"未能从当前 Manual Objects 大盘定位事件：{event.group_identity}")

    def select_pending_conflict_item(self) -> None:
        item_id = getattr(self, "pending_conflict_item_id", "")
        if not item_id or not self.current_manual_group:
            return
        if item_id not in {item.item_id for item in self.current_manual_group.items}:
            return
        for index, item in enumerate(self.current_manual_group.items[: len(self.manual_cards)]):
            if item.item_id == item_id:
                self.set_manual_preview_index(index)
                break
        self.pending_conflict_item_id = ""
        self.global_status.setText(f"已从冲突复核跳转到候选组并定位 item：{item_id}")

    def render_conflict_object(self, conflict: SourceObjectConflict) -> None:
        rows = [
            [event.group_identity, event.local_decision_for_source_object, event.review_status, str(event.selection_path)]
            for event in conflict.events
        ]
        self.conflict_event_model.set_rows(rows)
        explanation = self.conflict_service.explanation_for(conflict) if self.conflict_service else ""
        self.conflict_summary_text.setText(explanation + "\n\n" + f"Resolution: {(conflict.resolution or {}).get('final_object_decision', '-')}")
        while self.conflict_evidence_layout.count():
            item = self.conflict_evidence_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        for event in conflict.events:
            frame = QFrame()
            frame.setObjectName("glassPanel")
            layout = QVBoxLayout(frame)
            header = QLabel(f"{event.group_identity} | 当前对象：{event.selected_item.item_id} | 本地决策：{event.local_decision_for_source_object}")
            header.setObjectName("statusChip")
            layout.addWidget(header)
            row = QHBoxLayout()
            for card_index, record in enumerate(([event.selected_item] + event.peer_items)[:12]):
                item = self.source_record_to_manual_item(record)
                card = ManualObjectCard(item, card_index, self.manual_class_maps.get(item.dataset_id, {}))
                card.selected.connect(lambda _item_id, event_obj=event, record_obj=record: self.open_manual_group_from_conflict_event(event_obj, record_obj.item_id))
                card.set_conflict_status(conflict.conflict_state, explanation)
                if record.item_id == event.selected_item.item_id:
                    card.set_preview_selected(True)
                if record.item_id in event.keep_item_ids:
                    card.refresh_state("KEEP")
                elif record.item_id in event.remove_item_ids:
                    card.refresh_state("REMOVE")
                else:
                    card.refresh_state("UNDECIDED")
                if item.image_path.exists():
                    card.load_thumbnail()
                else:
                    card.preview.setText("staged copy 缺失")
                row.addWidget(card)
            layout.addLayout(row)
            self.conflict_evidence_layout.addWidget(frame)
        self.conflict_evidence_layout.addStretch(1)

    def source_record_to_manual_item(self, record: SourceItemRecord) -> ManualObjectItem:
        image_path = self.resolve_manual_project_path(record.target_image_project_path)
        label_path = self.resolve_manual_project_path(record.target_label_project_path)
        if (not record.target_image_project_path or not record.target_label_project_path) and record.target_group_project_path:
            group_dir = self.resolve_manual_project_path(record.target_group_project_path)
            image_path = group_dir / record.image_filename
            label_path = group_dir / record.label_filename
        return ManualObjectItem(
            item_id=record.item_id,
            dataset_id=record.dataset_id,
            image_filename=record.image_filename,
            label_filename=record.label_filename,
            image_path=image_path,
            label_path=label_path,
            source_image_project_path=record.source_image_project_path,
            source_label_project_path=record.source_label_project_path,
            image_sha256=record.image_sha256,
            label_sha256=record.label_sha256,
            width=record.width,
            height=record.height,
            label_line_count=record.label_line_count,
            label_class_set=record.label_class_set,
            metrics=record.metrics,
        )

    @staticmethod
    def resolve_manual_project_path(path_text: str) -> Path:
        if not path_text:
            return Path()
        path = Path(path_text)
        if path.is_absolute():
            return path
        return PROGRAMME_DIR.parent.parent / path

    def save_conflict_resolution(self) -> None:
        if self.current_conflict_object is None or self.conflict_service is None:
            self.show_message("尚未选择 source object。")
            return
        decision = str(self.final_decision_combo.currentData() or self.final_decision_combo.currentText())
        if decision in {"REMOVE_SOURCE_OBJECT", "ALL_OUT_SOURCE_OBJECT"} and self.run_mode != "test":
            ok = QMessageBox.question(self, "高风险确认", f"将写入对象级决策：{decision}\n此操作不移动主库文件，但会影响后续治理 agent 的优先读取。")
            if ok != QMessageBox.Yes:
                return
        try:
            result = self.conflict_service.write_resolution(
                self.current_conflict_object,
                final_decision=decision,
                reviewer=self.conflict_reviewer_edit.text().strip(),
                confidence=str(self.conflict_confidence_combo.currentData() or self.conflict_confidence_combo.currentText()),
                notes=self.conflict_notes_edit.toPlainText().strip(),
                decision_rationale=self.conflict_rationale_edit.toPlainText().strip(),
                canonical_group_key=self.current_conflict_object.group_key_set[0] if self.current_conflict_object.group_key_set else "",
            )
            self.logger.event("conflict_resolution_written", path=str(result.path), decision=decision)
            self.logger.event("conflict_resolution_verified", path=str(result.path), verified=result.verified)
            self.global_status.setText(f"对象级 resolution 已写入并校验：{result.path.name}")
            self.refresh_conflict_object_by_key(self.current_conflict_object.source_object_key)
        except Exception as exc:
            self.show_message(str(exc))

    def export_conflict_gate_summary(self) -> None:
        if self.conflict_service is None:
            self.show_message("冲突索引尚未构建。")
            return
        out = PROGRAMME_DIR / "Audit_Reports" / f"manual_objects_source_governance_gate_summary_{UI_VERSION}_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
        path = self.conflict_service.export_gate_summary(out)
        self.show_message(f"治理门摘要已导出：{path}")

    def open_conflict_resolution_folder(self) -> None:
        if self.manual_root is None:
            return
        folder = self.manual_root / "_conflict_resolutions"
        folder.mkdir(parents=True, exist_ok=True)
        subprocess.Popen(["explorer", str(folder)])

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
        self.show_message("快捷键：1-9 选择候选；A/D 切换当前组上一张/下一张预览；Enter 写入 APPROVED/提交；+ 保存并下一组；Esc 清除；Space 查看原图；Ctrl+Z 撤销图源组。")

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
            #manualObjectCard[previewSelected="true"] { border: 3px solid #009CD5; }
            #manualObjectCard[state="KEEP"][previewSelected="true"] { border: 3px solid #EF4022; }
            #manualObjectCard[state="REMOVE"][previewSelected="true"] { border: 3px solid #009CD5; }
            #imagePreview { background: rgba(232,237,242,0.88); border: 2px solid transparent; border-radius: 10px; }
            #imagePreview[selectedState="true"] { border: 2px solid #EF4022; background: rgba(239,64,34,0.05); }
            #imagePreview[previewSelected="true"] { border: 2px solid #009CD5; background: rgba(0,156,213,0.05); }
            #cardNumber { color: #EF4022; font-size: 24px; font-weight: 900; }
            #cardFilename { color: #17201C; font-weight: 700; }
            #classLabel { color: #094438; font-size: 13px; font-weight: 800; background: rgba(9,68,56,0.08); padding: 4px 7px; border-radius: 7px; }
            #cardStatus { color: #667085; font-size: 12px; }
            #stateChip[state="KEEP"] { background: rgba(9,68,56,0.14); color: #094438; padding: 7px 11px; border-radius: 8px; font-size: 13px; font-weight: 800; }
            #stateChip[state="REMOVE"] { background: rgba(102,112,133,0.14); color: #344054; padding: 7px 11px; border-radius: 8px; font-size: 13px; font-weight: 800; }
            #stateChip[state="UNDECIDED"], #stateChip { background: rgba(209,193,141,0.18); color: #094438; padding: 7px 11px; border-radius: 8px; font-size: 13px; font-weight: 800; }
            #conflictChip { background: rgba(209,193,141,0.18); color: #094438; padding: 5px 8px; border-radius: 8px; font-size: 12px; font-weight: 800; }
            #conflictChip[conflictState="CONFLICT_KEEP_REMOVE"], #conflictChip[conflictState="GROUP_SIGNATURE_CONFLICT"] { background: rgba(239,64,34,0.14); color: #EF4022; }
            #conflictChip[conflictState="CONSISTENT_KEEP"] { background: rgba(9,68,56,0.14); color: #094438; }
            #conflictChip[conflictState="CONSISTENT_REMOVE"] { background: rgba(102,112,133,0.14); color: #344054; }
            #conflictExplanation { background: rgba(255,255,255,0.82); border: 1px solid rgba(239,64,34,0.18); border-radius: 8px; color: #17201C; }
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
    app.setApplicationName(f"CIVL7009 Source Group Picker {UI_VERSION}")
    window = MainWindow(run_mode=os.environ.get("CIVL7009_PICKER_RUN_MODE", "gui_production"))
    window.show()
    if "--smoke-open" in args:
        QTimer.singleShot(350, app.quit)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
