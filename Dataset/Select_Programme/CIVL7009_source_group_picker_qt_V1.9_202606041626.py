from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import inspect
import json
import os
import queue
import shutil
import sys
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

try:
    from PIL import Image
except Exception:  # pragma: no cover - handled at runtime.
    Image = None

try:
    from PySide6.QtCore import (
        QAbstractTableModel,
        QModelIndex,
        QObject,
        QRunnable,
        QSize,
        Qt,
        QThreadPool,
        QTimer,
        Signal,
        Slot,
    )
    from PySide6.QtGui import QAction, QCloseEvent, QIcon, QImage, QKeyEvent, QPixmap
    from PySide6.QtSvgWidgets import QSvgWidget
    from PySide6.QtWidgets import (
        QApplication,
        QCheckBox,
        QComboBox,
        QDialog,
        QFileDialog,
        QFrame,
        QGraphicsScene,
        QGraphicsView,
        QGridLayout,
        QHBoxLayout,
        QInputDialog,
        QLabel,
        QLineEdit,
        QListWidget,
        QListWidgetItem,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QProgressBar,
        QScrollArea,
        QSplitter,
        QStackedWidget,
        QTableView,
        QTabWidget,
        QTextEdit,
        QToolButton,
        QVBoxLayout,
        QWidget,
    )
except Exception as exc:  # pragma: no cover - CLI can report this cleanly.
    QT_IMPORT_ERROR = exc
else:
    QT_IMPORT_ERROR = None


PROGRAMME_VERSION = "V1.9"
SCRIPT_VERSION = PROGRAMME_VERSION
SCRIPT_TIMECODE = "202606041626"
UI_VERSION = f"{PROGRAMME_VERSION}_{SCRIPT_TIMECODE}"
CORE_FILENAME = "CIVL7009_source_group_picker_gui_V1.8.1_202606041443.py"
ASSET_DIR_NAME = f"V1.9_{SCRIPT_TIMECODE}"
STATUS = "PENDING_AUDIT"


def resolve_programme_dir() -> Path:
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        if exe_dir.name.casefold() == "executable":
            return exe_dir.parent
        return exe_dir
    return Path(__file__).resolve().parent


PROGRAMME_DIR = resolve_programme_dir()
ASSET_DIR = PROGRAMME_DIR / "UI_Assets" / ASSET_DIR_NAME


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def now_iso() -> str:
    return datetime.now().isoformat(timespec="milliseconds")


def runtime_subdir(run_mode: str) -> str:
    mapping = {
        "gui_production": "Production",
        "production": "Production",
        "test": "Test",
        "audit_only": "AuditOnly",
        "debug": "Debug",
    }
    return mapping.get(run_mode, "Debug")


def detect_run_mode(explicit: str = "") -> str:
    if explicit:
        return explicit
    env_mode = os.environ.get("CIVL7009_PICKER_RUN_MODE", "").strip()
    if env_mode:
        return env_mode
    argv = " ".join(sys.argv).casefold()
    if "--audit-only" in argv:
        return "audit_only"
    if "pytest" in argv or "unittest" in argv or Path(sys.argv[0]).name.startswith("test_"):
        return "test"
    return "gui_production"


class V19Logger:
    def __init__(self, run_mode: str, programme_dir: Path = PROGRAMME_DIR) -> None:
        self.run_mode = detect_run_mode(run_mode)
        self.programme_dir = programme_dir
        self.run_id = datetime.now().strftime("%Y%m%d%H%M%S%f")[:-3]
        self.started_perf = time.perf_counter()
        self.lock = threading.Lock()
        self.log_dir = programme_dir / "Runtime_Logs" / runtime_subdir(self.run_mode)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.log_dir / f"picker_events_{PROGRAMME_VERSION}_{self.run_id}.jsonl"
        self.transaction_path = self.log_dir / f"file_transactions_{PROGRAMME_VERSION}_{self.run_id}.jsonl"
        self._event_file = self.path.open("a", encoding="utf-8", buffering=1)
        self._transaction_file = None
        self.core_meta: dict[str, Any] = {}
        self.review_dir = ""
        self.event("run_start", argv=sys.argv, programme_dir=str(programme_dir))

    def set_core_meta(self, **meta: Any) -> None:
        self.core_meta.update(meta)
        self.event("core_meta_updated", **meta)

    def set_review_dir(self, review_dir: str | Path | None) -> None:
        self.review_dir = str(review_dir or "")

    def base_payload(self, event: str) -> dict[str, Any]:
        return {
            "timestamp": now_iso(),
            "elapsed_ms": round((time.perf_counter() - self.started_perf) * 1000.0, 3),
            "event": event,
            "programme_version": PROGRAMME_VERSION,
            "ui_version": UI_VERSION,
            "core_version": self.core_meta.get("core_version", ""),
            "core_timecode": self.core_meta.get("core_timecode", ""),
            "run_mode": self.run_mode,
            "review_dir": self.review_dir,
            "thread": threading.current_thread().name,
        }

    def event(self, event: str, **fields: Any) -> None:
        payload = self.base_payload(event)
        payload.update(fields)
        with self.lock:
            self._event_file.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")

    def perf(self, event: str, started: float, **fields: Any) -> None:
        fields["duration_ms"] = round((time.perf_counter() - started) * 1000.0, 3)
        self.event(event, **fields)

    def transaction_event(self, record: dict[str, Any]) -> None:
        payload = self.base_payload("transaction_journal")
        payload.update(record)
        created = False
        with self.lock:
            if self._transaction_file is None:
                self._transaction_file = self.transaction_path.open("a", encoding="utf-8", buffering=1)
                created = True
            self._transaction_file.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
        if created:
            self.event("transaction_journal_created", path=str(self.transaction_path))

    def can_write_transaction_log(self) -> bool:
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            probe = self.log_dir / f".write_probe_{self.run_id}.tmp"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return True
        except OSError:
            return False

    def close(self) -> None:
        self.event("run_end")
        with self.lock:
            self._event_file.close()
            if self._transaction_file is not None:
                self._transaction_file.close()


@dataclass
class CoreLoadReport:
    ok: bool
    path: Path | None = None
    core_sha256: str = ""
    bundled_core_sha256: str = ""
    developer_override: bool = False
    missing_symbols: list[str] = field(default_factory=list)
    signature_errors: list[str] = field(default_factory=list)
    import_side_effects: list[str] = field(default_factory=list)
    error: str = ""


class PickerCoreFacade:
    REQUIRED_SYMBOLS = [
        "build_quick_preview_index",
        "build_fast_review_index",
        "audit_review_dir",
        "prepare_transaction_from_fast_index",
        "BackgroundMoveRunner",
        "ReviewDirLock",
        "execute_transaction",
        "undo_transaction",
        "export_audit_report",
        "scan_unfinished_transactions",
        "QueuedMoveTask",
        "keypad_slots_for_count",
    ]
    SIGNATURE_REQUIREMENTS = {
        "build_quick_preview_index": ["image_review_dir"],
        "build_fast_review_index": ["image_review_dir"],
        "audit_review_dir": ["image_review_dir"],
        "prepare_transaction_from_fast_index": ["index", "prefix", "selected_image"],
        "execute_transaction": ["transaction"],
        "undo_transaction": ["transaction"],
        "export_audit_report": ["id_root"],
    }

    def __init__(
        self,
        logger: V19Logger,
        explicit_core_path: Path | None = None,
        developer_mode: bool = False,
    ) -> None:
        self.logger = logger
        self.explicit_core_path = explicit_core_path
        self.developer_mode = developer_mode or not getattr(sys, "frozen", False)
        self.core = None
        self.report = CoreLoadReport(ok=False)

    def bundled_core_path(self) -> Path | None:
        mei = getattr(sys, "_MEIPASS", "")
        if mei:
            candidate = Path(mei) / CORE_FILENAME
            if candidate.exists():
                return candidate
        candidate = PROGRAMME_DIR / CORE_FILENAME
        if getattr(sys, "frozen", False) and candidate.exists():
            return candidate
        return None

    def sibling_core_path(self) -> Path:
        return PROGRAMME_DIR / CORE_FILENAME

    def resolve_core_path(self) -> tuple[Path | None, bool, str]:
        if self.explicit_core_path:
            return self.explicit_core_path.resolve(), False, "explicit"
        bundled = self.bundled_core_path()
        sibling = self.sibling_core_path()
        if getattr(sys, "frozen", False):
            if bundled is not None and not self.developer_mode:
                return bundled.resolve(), False, "bundled"
            if self.developer_mode and sibling.exists():
                return sibling.resolve(), bundled is not None and sibling.resolve() != bundled.resolve(), "developer_sibling"
            if bundled is not None:
                return bundled.resolve(), False, "bundled_fallback"
        if self.developer_mode and sibling.exists():
            return sibling.resolve(), False, "source_sibling"
        return None, False, "missing"

    def load(self) -> CoreLoadReport:
        started = time.perf_counter()
        path, developer_override, source_kind = self.resolve_core_path()
        bundled = self.bundled_core_path()
        bundled_hash = sha256_file(bundled) if bundled and bundled.exists() else ""
        if path is None or not path.exists():
            self.report = CoreLoadReport(ok=False, path=path, bundled_core_sha256=bundled_hash, error="Core file not found")
            self.logger.event("core_load_failed", error=self.report.error, source_kind=source_kind)
            return self.report

        core_hash = sha256_file(path)
        try:
            spec = importlib.util.spec_from_file_location(f"civl7009_picker_core_{core_hash[:12]}", path)
            if spec is None or spec.loader is None:
                raise RuntimeError("importlib could not create a loader")
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
        except Exception as exc:
            self.report = CoreLoadReport(
                ok=False,
                path=path,
                core_sha256=core_hash,
                bundled_core_sha256=bundled_hash,
                developer_override=developer_override,
                error=f"Core import failed: {exc}",
            )
            self.logger.event("core_load_failed", error=self.report.error, core_file=str(path))
            return self.report

        missing = [name for name in self.REQUIRED_SYMBOLS if not hasattr(module, name)]
        sig_errors: list[str] = []
        for name, required_params in self.SIGNATURE_REQUIREMENTS.items():
            if not hasattr(module, name):
                continue
            try:
                params = list(inspect.signature(getattr(module, name)).parameters)
            except (TypeError, ValueError) as exc:
                sig_errors.append(f"{name}: signature unreadable ({exc})")
                continue
            for param in required_params:
                if param not in params:
                    sig_errors.append(f"{name}: missing parameter {param}")

        side_effects: list[str] = []
        if getattr(module, "RUNTIME_LOGGER", None) is not None:
            side_effects.append("core import created RUNTIME_LOGGER")

        ok = not missing and not sig_errors and not side_effects
        self.core = module if ok else None
        self.report = CoreLoadReport(
            ok=ok,
            path=path,
            core_sha256=core_hash,
            bundled_core_sha256=bundled_hash,
            developer_override=developer_override,
            missing_symbols=missing,
            signature_errors=sig_errors,
            import_side_effects=side_effects,
            error="" if ok else "Core validation failed",
        )

        if ok:
            self.patch_logging(module)
            self.logger.set_core_meta(
                core_version=getattr(module, "SCRIPT_VERSION", ""),
                core_timecode=getattr(module, "SCRIPT_TIMECODE", ""),
                core_file=str(path),
                core_sha256=core_hash,
                bundled_core_sha256=bundled_hash,
                developer_override=developer_override,
            )
            self.logger.perf("core_load_ok", started, core_file=str(path), core_sha256=core_hash, source_kind=source_kind)
        else:
            self.logger.perf(
                "core_load_failed",
                started,
                core_file=str(path),
                core_sha256=core_hash,
                missing_symbols=missing,
                signature_errors=sig_errors,
                import_side_effects=side_effects,
            )
        return self.report

    def patch_logging(self, module: Any) -> None:
        def log_event(event: str, **fields: Any) -> None:
            self.logger.event(event, **fields)

        def log_perf(event: str, started: float, **fields: Any) -> None:
            self.logger.perf(event, started, **fields)

        def write_transaction_journal(transaction: Any, state: str | None = None, error: str = "") -> None:
            record = module.transaction_record(transaction, state=state, error=error)
            self.logger.transaction_event(record)

        module.log_event = log_event
        module.log_perf = log_perf
        module.write_transaction_journal = write_transaction_journal


class TableModel(QAbstractTableModel):
    def __init__(self, headers: list[str], rows: list[list[Any]] | None = None) -> None:
        super().__init__()
        self.headers = headers
        self.rows = rows or []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.headers)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid() or role not in (Qt.DisplayRole, Qt.ToolTipRole):
            return None
        value = self.rows[index.row()][index.column()]
        return "" if value is None else str(value)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole) -> Any:
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.headers[section]
        return None

    def set_rows(self, rows: list[list[Any]]) -> None:
        self.beginResetModel()
        self.rows = rows
        self.endResetModel()


class WorkerSignals(QObject):
    progress = Signal(int, str, str)
    quick_ready = Signal(int, object)
    index_ready = Signal(int, object, object, object, object, list)
    error = Signal(int, str, str)
    thumbnail_ready = Signal(int, str, str, bytes, int, int, str)


class OpenReviewWorker(QRunnable):
    def __init__(self, generation: int, facade: PickerCoreFacade, review_dir: Path) -> None:
        super().__init__()
        self.generation = generation
        self.facade = facade
        self.review_dir = review_dir
        self.signals = WorkerSignals()
        self.cancelled = False

    def cancel(self) -> None:
        self.cancelled = True

    @Slot()
    def run(self) -> None:
        core = self.facade.core
        if core is None:
            self.signals.error.emit(self.generation, "CORE_NOT_LOADED", "Core is not loaded.")
            return
        lock = None
        try:
            self.signals.progress.emit(self.generation, "Acquiring review lock", "Checking single-instance lock")
            lock = core.ReviewDirLock(self.review_dir)
            lock.acquire(clear_stale=False)
            if self.cancelled:
                lock.release()
                return

            self.signals.progress.emit(self.generation, "Running recovery scan", "Checking unfinished transactions")
            recovery = core.scan_unfinished_transactions(review_dir=self.review_dir)
            if self.cancelled:
                lock.release()
                return

            self.signals.progress.emit(self.generation, "Preparing quick preview", "Scanning first complete groups")
            quick = core.build_quick_preview_index(self.review_dir, preview_limit=20)
            self.signals.quick_ready.emit(self.generation, quick)
            self.signals.progress.emit(self.generation, "First group ready", "Preview available; commit remains disabled")
            if self.cancelled:
                lock.release()
                return

            self.signals.progress.emit(self.generation, "Building FastReviewIndex", "Building commit-safe index")
            index = core.build_fast_review_index(self.review_dir)
            if self.cancelled:
                lock.release()
                return

            self.signals.progress.emit(self.generation, "Running full audit", "Validating root/done/out/labels")
            summary, rows = core.audit_review_dir(self.review_dir, create_missing=False)
            self.signals.progress.emit(self.generation, "Ready for commit", "Audit complete; Safe Gate remains OFF")
            self.signals.index_ready.emit(self.generation, lock, index, summary, rows, recovery)
        except Exception as exc:
            if lock is not None:
                try:
                    lock.release()
                except Exception:
                    pass
            self.signals.error.emit(self.generation, "OPEN_REVIEW_FAILED", str(exc))


class ThumbnailWorker(QRunnable):
    def __init__(self, generation: int, image_path: Path, max_width: int, max_height: int) -> None:
        super().__init__()
        self.generation = generation
        self.image_path = image_path
        self.max_width = max_width
        self.max_height = max_height
        self.signals = WorkerSignals()

    @Slot()
    def run(self) -> None:
        if Image is None:
            self.signals.thumbnail_ready.emit(self.generation, str(self.image_path), "", b"", 0, 0, "Pillow is unavailable")
            return
        try:
            with Image.open(self.image_path) as img:
                preview = img.convert("RGBA")
                preview.thumbnail((self.max_width, self.max_height), Image.Resampling.LANCZOS)
                width, height = preview.size
                payload = preview.tobytes("raw", "RGBA")
            key = thumbnail_cache_key(self.image_path, self.max_width, self.max_height)
            self.signals.thumbnail_ready.emit(self.generation, str(self.image_path), key, payload, width, height, "")
        except Exception as exc:
            self.signals.thumbnail_ready.emit(self.generation, str(self.image_path), "", b"", 0, 0, str(exc))


def thumbnail_cache_key(image_path: Path, max_width: int, max_height: int) -> str:
    stat = image_path.stat()
    return "|".join(
        [
            str(image_path.resolve(strict=False)),
            str(max_width),
            str(max_height),
            str(stat.st_mtime_ns),
            str(stat.st_size),
        ]
    )


class ImageCard(QFrame):
    selected = Signal(int)
    activated = Signal(int)

    def __init__(self, index: int, image_path: Path, key_hint: str) -> None:
        super().__init__()
        self.index = index
        self.image_path = image_path
        self.key_hint = key_hint
        self.setObjectName("imageCard")
        self.setFrameShape(QFrame.NoFrame)
        self.setMinimumSize(260, 240)
        self.setProperty("selected", False)
        layout = QVBoxLayout(self)
        self.number = QLabel(f"[{index + 1}]")
        self.number.setObjectName("cardNumber")
        self.preview = QLabel("Loading")
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setMinimumSize(220, 160)
        self.preview.setObjectName("imagePreview")
        self.name = QLabel(image_path.name)
        self.name.setObjectName("cardFilename")
        self.name.setWordWrap(True)
        self.status = QLabel("Label pending")
        self.status.setObjectName("cardStatus")
        layout.addWidget(self.number)
        layout.addWidget(self.preview, 1)
        layout.addWidget(self.name)
        layout.addWidget(self.status)

    def set_selected(self, selected: bool) -> None:
        self.setProperty("selected", selected)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def set_thumbnail(self, image: QImage) -> None:
        pixmap = QPixmap.fromImage(image)
        self.preview.setPixmap(pixmap.scaled(self.preview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.status.setText("Label OK")

    def mousePressEvent(self, event: Any) -> None:
        if event.button() == Qt.LeftButton:
            self.selected.emit(self.index)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: Any) -> None:
        if event.button() == Qt.LeftButton:
            self.activated.emit(self.index)
        super().mouseDoubleClickEvent(event)


class ImageViewer(QDialog):
    def __init__(self, image_path: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(image_path.name)
        self.resize(1100, 760)
        layout = QVBoxLayout(self)
        label = QLabel(str(image_path))
        self.scene = QGraphicsScene(self)
        self.view = QGraphicsView(self.scene)
        self.view.setDragMode(QGraphicsView.ScrollHandDrag)
        pixmap = QPixmap(str(image_path))
        self.scene.addPixmap(pixmap)
        self.scene.setSceneRect(pixmap.rect())
        layout.addWidget(label)
        layout.addWidget(self.view, 1)


class MainWindow(QMainWindow):
    def __init__(self, facade: PickerCoreFacade, logger: V19Logger) -> None:
        super().__init__()
        if QT_IMPORT_ERROR is not None:
            raise RuntimeError(QT_IMPORT_ERROR)
        self.facade = facade
        self.logger = logger
        self.core = facade.core
        self.thread_pool = QThreadPool.globalInstance()
        self.generation = 0
        self.current_review_dir: Path | None = None
        self.current_lock = None
        self.quick_index = None
        self.fast_index = None
        self.audit_summary = None
        self.audit_rows: list[Any] = []
        self.recovery_rows: list[Any] = []
        self.current_groups: list[tuple[str, list[Path]]] = []
        self.current_group_index = 0
        self.selected_card_index: int | None = None
        self.safe_gate_enabled = False
        self.click_mode_commit = False
        self.last_committed_transaction = None
        self.move_event_queue: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.move_runner = self.core.BackgroundMoveRunner(self.move_event_queue) if self.core else None
        self.issue_model = TableModel(["Severity", "Prefix", "Code", "Message", "Suggested Action"])
        self.queue_model = TableModel(["Task", "Prefix", "Selected", "Status", "Error"])
        self.review_model = TableModel(["Review Dir", "Root", "Done", "Errors", "Label Sync"])
        self.cards: list[ImageCard] = []
        self.thumbnail_cache: dict[str, QImage] = {}
        self.open_worker: OpenReviewWorker | None = None

        self.setWindowTitle(f"CIVL7009 Source Group Picker {UI_VERSION}")
        self.resize(1540, 940)
        self.setWindowIcon(QIcon(str(ASSET_DIR / "app_icon.svg")))
        self.build_ui()
        self.apply_style()

        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self.poll_move_events)
        self.poll_timer.start(120)
        self.update_safe_gate_banner()
        self.show_core_status()

    def build_ui(self) -> None:
        root = QWidget()
        main = QVBoxLayout(root)
        main.setContentsMargins(16, 16, 16, 16)
        main.setSpacing(12)

        self.banner = QLabel("READ-ONLY PREVIEW")
        self.banner.setObjectName("safeBanner")
        main.addWidget(self.banner)

        toolbar = QHBoxLayout()
        self.open_id_btn = QPushButton("Open ID Root")
        self.open_review_btn = QPushButton("Open Review Dir")
        self.safe_gate_btn = QPushButton("Enable Safe Gate")
        self.safe_gate_btn.setObjectName("dangerButton")
        self.export_btn = QPushButton("Export Audit")
        self.undo_btn = QPushButton("Undo Last")
        self.undo_btn.setEnabled(False)
        self.mode_box = QComboBox()
        self.mode_box.addItems(["Single click previews, Enter commits", "Single click commits when Safe Gate ON"])
        self.mode_box.currentIndexChanged.connect(lambda idx: setattr(self, "click_mode_commit", idx == 1))
        for widget in [self.open_id_btn, self.open_review_btn, self.safe_gate_btn, self.export_btn, self.undo_btn, self.mode_box]:
            toolbar.addWidget(widget)
        toolbar.addStretch(1)
        main.addLayout(toolbar)

        self.kpi_layout = QHBoxLayout()
        self.kpi_labels: dict[str, QLabel] = {}
        for key in ["Root remaining", "Current group", "Done groups", "Out images", "Move queue", "Failed tasks", "Label Sync", "Audit state"]:
            card = QFrame()
            card.setObjectName("kpiCard")
            card_layout = QVBoxLayout(card)
            title = QLabel(key)
            value = QLabel("0")
            value.setObjectName("kpiValue")
            card_layout.addWidget(title)
            card_layout.addWidget(value)
            self.kpi_layout.addWidget(card)
            self.kpi_labels[key] = value
        main.addLayout(self.kpi_layout)

        self.progress_chip = QLabel("Idle")
        self.progress_chip.setObjectName("progressChip")
        main.addWidget(self.progress_chip)

        tabs = QTabWidget()
        tabs.addTab(self.build_manual_tab(), "Manual Selection")
        tabs.addTab(self.build_initialisation_tab(), "ID Initialisation")
        main.addWidget(tabs, 1)
        self.setCentralWidget(root)

        self.open_id_btn.clicked.connect(self.choose_id_root)
        self.open_review_btn.clicked.connect(self.choose_review_dir)
        self.safe_gate_btn.clicked.connect(self.toggle_safe_gate)
        self.undo_btn.clicked.connect(self.undo_last_transaction)
        self.export_btn.clicked.connect(self.export_current_audit)

    def build_manual_tab(self) -> QWidget:
        outer = QWidget()
        layout = QHBoxLayout(outer)
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        sidebar = QFrame()
        sidebar.setObjectName("glassPanel")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.addWidget(QLabel("Review Board"))
        self.review_list = QTableView()
        self.review_list.setModel(self.review_model)
        sidebar_layout.addWidget(self.review_list, 1)
        self.core_status = QLabel("")
        self.core_status.setWordWrap(True)
        sidebar_layout.addWidget(self.core_status)
        splitter.addWidget(sidebar)

        center = QFrame()
        center.setObjectName("stagePanel")
        center_layout = QVBoxLayout(center)
        self.overlay = QFrame()
        self.overlay.setObjectName("overlay")
        overlay_layout = QHBoxLayout(self.overlay)
        self.overlay_badge = QSvgWidget(str(ASSET_DIR / "loading_badge.svg"))
        self.overlay_badge.setFixedSize(96, 48)
        self.overlay_text = QLabel("Open a review directory")
        self.overlay_progress = QProgressBar()
        self.overlay_progress.setRange(0, 0)
        overlay_layout.addWidget(self.overlay_badge)
        overlay_layout.addWidget(self.overlay_text, 1)
        overlay_layout.addWidget(self.overlay_progress)
        center_layout.addWidget(self.overlay)
        self.image_scroll = QScrollArea()
        self.image_scroll.setWidgetResizable(True)
        self.image_host = QWidget()
        self.image_grid = QGridLayout(self.image_host)
        self.image_grid.setSpacing(14)
        self.image_scroll.setWidget(self.image_host)
        center_layout.addWidget(self.image_scroll, 1)
        button_row = QHBoxLayout()
        self.prev_btn = QPushButton("Previous")
        self.next_btn = QPushButton("Next")
        self.commit_btn = QPushButton("Commit Selected")
        self.commit_btn.setEnabled(False)
        button_row.addWidget(self.prev_btn)
        button_row.addWidget(self.next_btn)
        button_row.addStretch(1)
        button_row.addWidget(self.commit_btn)
        center_layout.addLayout(button_row)
        splitter.addWidget(center)

        inspector = QFrame()
        inspector.setObjectName("glassPanel")
        inspector_layout = QVBoxLayout(inspector)
        inspector_layout.addWidget(QLabel("Issue Table"))
        self.issue_table = QTableView()
        self.issue_table.setModel(self.issue_model)
        inspector_layout.addWidget(self.issue_table, 2)
        inspector_layout.addWidget(QLabel("Formula Inspector"))
        self.formula_text = QTextEdit()
        self.formula_text.setReadOnly(True)
        self.formula_text.setMaximumHeight(150)
        inspector_layout.addWidget(self.formula_text)
        inspector_layout.addWidget(QLabel("Move Queue"))
        self.queue_table = QTableView()
        self.queue_table.setModel(self.queue_model)
        inspector_layout.addWidget(self.queue_table, 1)
        inspector_layout.addWidget(QLabel("Recent Events"))
        self.recent_events = QTextEdit()
        self.recent_events.setReadOnly(True)
        self.recent_events.setMaximumHeight(145)
        inspector_layout.addWidget(self.recent_events)
        splitter.addWidget(inspector)
        splitter.setSizes([300, 780, 440])

        self.prev_btn.clicked.connect(lambda: self.step_group(-1))
        self.next_btn.clicked.connect(lambda: self.step_group(1))
        self.commit_btn.clicked.connect(self.commit_selected)
        return outer

    def build_initialisation_tab(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("glassPanel")
        layout = QVBoxLayout(panel)
        msg = QLabel(
            "ID Initialisation write actions are handled by V1.8.1 fallback in this release. "
            "V1.9.1 will migrate this page."
        )
        msg.setWordWrap(True)
        layout.addWidget(msg)
        fallback = QTextEdit()
        fallback.setReadOnly(True)
        fallback.setText(
            "Fallback policy:\n"
            "- This V1.9.0 page is read-only.\n"
            "- No YOLO initialisation write/copy/move action is performed here.\n"
            f"- V1.8.1 fallback source: {PROGRAMME_DIR / CORE_FILENAME}\n"
            "- Launching fallback must show id_root and write-risk confirmation first."
        )
        layout.addWidget(fallback, 1)
        return panel

    def apply_style(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow, QWidget { background: #EEF2F6; color: #17201C; font-size: 13px; }
            #safeBanner { padding: 10px 14px; border-radius: 14px; background: rgba(9,68,56,0.12); color: #094438; font-weight: 700; }
            #safeBanner[enabledMoves="true"] { background: rgba(239,64,34,0.16); color: #EF4022; }
            #glassPanel, #stagePanel { background: rgba(255,255,255,0.72); border: 1px solid rgba(255,255,255,0.92); border-radius: 22px; }
            #kpiCard { background: rgba(255,255,255,0.78); border: 1px solid rgba(209,193,141,0.55); border-radius: 16px; }
            #kpiValue { font-size: 20px; font-weight: 700; color: #094438; }
            #progressChip { padding: 8px 12px; border-radius: 12px; background: rgba(209,193,141,0.24); color: #094438; }
            #overlay { background: rgba(253,253,253,0.86); border: 1px solid rgba(255,255,255,0.95); border-radius: 18px; }
            #imageCard { background: rgba(255,255,255,0.82); border: 2px solid rgba(209,193,141,0.45); border-radius: 18px; }
            #imageCard[selected="true"] { border: 3px solid #009CD5; background: rgba(255,255,255,0.96); }
            #imagePreview { background: rgba(232,237,242,0.8); border-radius: 14px; }
            #cardNumber { color: #EF4022; font-weight: 800; }
            #cardFilename { color: #17201C; }
            #cardStatus { color: #667085; }
            QPushButton { background: rgba(255,255,255,0.86); border: 1px solid rgba(9,68,56,0.25); border-radius: 12px; padding: 8px 12px; }
            QPushButton:hover { border-color: #009CD5; }
            QPushButton:disabled { color: #98A2B3; background: rgba(232,237,242,0.7); }
            #dangerButton { color: #EF4022; font-weight: 700; }
            QTableView { background: rgba(255,255,255,0.7); border-radius: 12px; gridline-color: #E8EDF2; }
            QTextEdit { background: rgba(255,255,255,0.68); border: 1px solid rgba(9,68,56,0.12); border-radius: 12px; }
            """
        )

    def show_core_status(self) -> None:
        report = self.facade.report
        if report.ok:
            status = f"Core: {self.logger.core_meta.get('core_version')} {self.logger.core_meta.get('core_timecode')}"
            if report.developer_override:
                status += "\nDev Core Override"
            status += f"\nSHA256: {report.core_sha256[:16]}..."
        else:
            status = f"Core Load Failed\n{report.error}\nMissing: {', '.join(report.missing_symbols)}"
        self.core_status.setText(status)

    def add_recent(self, text: str) -> None:
        self.recent_events.append(f"{datetime.now().strftime('%H:%M:%S')}  {text}")

    def set_progress(self, phase: str, detail: str = "", indeterminate: bool = True) -> None:
        self.overlay.show()
        self.overlay_text.setText(f"{phase}\n{detail}")
        self.progress_chip.setText(f"{phase}: {detail}")
        self.overlay_progress.setRange(0, 0 if indeterminate else 100)
        self.logger.event("progress_phase", phase=phase, detail=detail)

    def choose_id_root(self) -> None:
        root = QFileDialog.getExistingDirectory(self, "Choose Source_Archive/<ID> root")
        if not root or self.core is None:
            return
        try:
            review_dirs = self.core.review_dirs_for_id_root(Path(root))
            rows = [[path.name, "", "", "", ""] for path in review_dirs]
            self.review_model.set_rows(rows)
            self.add_recent(f"Loaded ID root: {root}")
        except Exception as exc:
            self.add_issue("ERROR", "", "ID_ROOT_FAILED", str(exc), "Check images/labels folders.")

    def choose_review_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Choose images/ManualReview_GroupSize_N")
        if path:
            self.open_review_dir(Path(path))

    def open_review_dir(self, review_dir: Path) -> None:
        if self.core is None:
            self.show_disabled_reason("Core load failed")
            return
        self.release_lock()
        self.generation += 1
        self.current_review_dir = review_dir.resolve()
        self.logger.set_review_dir(self.current_review_dir)
        self.safe_gate_enabled = False
        self.update_safe_gate_banner()
        self.fast_index = None
        self.audit_summary = None
        self.recovery_rows = []
        self.current_groups = []
        self.current_group_index = 0
        self.selected_card_index = None
        self.cards = []
        self.clear_image_grid()
        self.set_progress("Acquiring review lock", str(self.current_review_dir))
        worker = OpenReviewWorker(self.generation, self.facade, self.current_review_dir)
        self.open_worker = worker
        worker.signals.progress.connect(self.on_open_progress)
        worker.signals.quick_ready.connect(self.on_quick_ready)
        worker.signals.index_ready.connect(self.on_index_ready)
        worker.signals.error.connect(self.on_worker_error)
        self.thread_pool.start(worker)

    @Slot(int, str, str)
    def on_open_progress(self, generation: int, phase: str, detail: str) -> None:
        if generation != self.generation:
            return
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
        self.progress_chip.setText("Preview available / Commit disabled until index ready")
        self.update_kpis()
        self.add_recent("Quick preview ready")

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
        self.update_kpis()
        self.update_commit_enabled()
        self.render_current_group()
        self.progress_chip.setText("Ready / READ-ONLY PREVIEW")
        self.add_recent("FastReviewIndex and full audit ready")

    @Slot(int, str, str)
    def on_worker_error(self, generation: int, code: str, message: str) -> None:
        if generation != self.generation:
            return
        self.add_issue("ERROR", "", code, message, "Resolve before continuing.")
        self.progress_chip.setText(f"{code}: {message}")
        self.add_recent(f"{code}: {message}")

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
        self.selected_card_index = None
        if not self.current_groups:
            empty = QSvgWidget(str(ASSET_DIR / "empty_state.svg"))
            empty.setFixedSize(420, 260)
            self.image_grid.addWidget(empty, 0, 0)
            self.logger.perf("render_next_group_done", started, group_size=0)
            return
        prefix, members = self.current_groups[self.current_group_index]
        rows = max(1, (len(members) + 2) // 3)
        for idx, image_path in enumerate(members):
            key = thumbnail_cache_key(image_path, 360, 260)
            card = ImageCard(idx, image_path, key)
            card.selected.connect(self.select_card)
            card.activated.connect(self.open_viewer)
            self.cards.append(card)
            self.image_grid.addWidget(card, idx // 3, idx % 3)
            if key in self.thumbnail_cache:
                card.set_thumbnail(self.thumbnail_cache[key])
            else:
                worker = ThumbnailWorker(self.generation, image_path, 360, 260)
                worker.signals.thumbnail_ready.connect(self.on_thumbnail_ready)
                self.thread_pool.start(worker)
        self.progress_chip.setText(f"Current prefix: {prefix}")
        self.update_kpis()
        self.logger.perf("render_next_group_done", started, prefix=prefix, group_size=len(members), grid_rows=rows)

    @Slot(int, str, str, bytes, int, int, str)
    def on_thumbnail_ready(self, generation: int, path_text: str, key: str, payload: bytes, width: int, height: int, error: str) -> None:
        if generation != self.generation:
            return
        if error:
            self.add_issue("WARN", "", "THUMBNAIL_FAILED", f"{path_text}: {error}", "Open 100% viewer if needed.")
            return
        image = QImage(payload, width, height, QImage.Format_RGBA8888).copy()
        self.thumbnail_cache[key] = image
        for card in self.cards:
            if str(card.image_path) == path_text:
                card.set_thumbnail(image)

    @Slot(int)
    def select_card(self, index: int) -> None:
        if index < 0 or index >= len(self.cards):
            return
        self.selected_card_index = index
        for idx, card in enumerate(self.cards):
            card.set_selected(idx == index)
        prefix = self.current_groups[self.current_group_index][0] if self.current_groups else ""
        self.logger.event("preview_select", prefix=prefix, selected=str(self.cards[index].image_path))
        self.add_recent(f"Preview selected [{index + 1}] {self.cards[index].image_path.name}")
        if self.safe_gate_enabled and self.click_mode_commit:
            self.commit_selected()
        else:
            self.update_commit_enabled()

    @Slot(int)
    def open_viewer(self, index: int) -> None:
        if index < 0 or index >= len(self.cards):
            return
        viewer = ImageViewer(self.cards[index].image_path, self)
        viewer.exec()

    def step_group(self, delta: int) -> None:
        if not self.current_groups:
            return
        self.current_group_index = max(0, min(len(self.current_groups) - 1, self.current_group_index + delta))
        self.render_current_group()

    def disabled_reason(self) -> str:
        if not self.safe_gate_enabled:
            return "Safe Gate is OFF"
        if self.current_lock is None:
            return "Review lock not acquired"
        if self.recovery_rows:
            return "Recovery scan has unfinished transactions"
        if self.fast_index is None or not getattr(self.fast_index, "ready_for_commit", False):
            return "FastReviewIndex is still building"
        if self.audit_summary is None:
            return "Full audit not finished"
        if getattr(self.audit_summary, "blocking_errors", []):
            return "Blocking audit errors exist"
        if self.selected_card_index is None:
            return "No image selected"
        return ""

    def update_commit_enabled(self) -> None:
        reason = self.disabled_reason()
        self.commit_btn.setEnabled(reason == "")
        self.commit_btn.setToolTip(reason)

    def show_disabled_reason(self, reason: str | None = None) -> None:
        reason = reason or self.disabled_reason() or "Action is disabled"
        QMessageBox.information(self, "Action disabled", reason)
        self.add_recent(f"Disabled: {reason}")

    def can_enable_safe_gate(self) -> tuple[bool, str]:
        if self.current_review_dir is None:
            return False, "No review dir is open"
        if self.current_lock is None:
            return False, "ReviewDirLock is not held"
        if self.recovery_rows:
            return False, "Recovery scan has unfinished transactions"
        if self.fast_index is None or not getattr(self.fast_index, "ready_for_commit", False):
            return False, "FastReviewIndex ready_for_commit is false"
        if self.audit_summary is None:
            return False, "Full audit has not finished"
        if getattr(self.audit_summary, "blocking_errors", []):
            return False, "Full audit has blocking_errors"
        if not self.logger.can_write_transaction_log():
            return False, "Transaction log path is not writable"
        return True, ""

    def toggle_safe_gate(self) -> None:
        if self.safe_gate_enabled:
            self.safe_gate_enabled = False
            self.logger.event("safe_gate_disabled", note="existing move queue will finish")
            self.add_recent("Safe Gate OFF; existing move queue will finish.")
            self.update_safe_gate_banner()
            self.update_commit_enabled()
            return
        ok, reason = self.can_enable_safe_gate()
        if not ok:
            self.show_disabled_reason(reason)
            return
        text, accepted = QInputDialog.getText(
            self,
            "Enable File Moves",
            f"Review dir:\n{self.current_review_dir}\n\nType MOVE to enable real file moves.",
            QLineEdit.Normal,
            "",
        )
        if not accepted or text.strip() != "MOVE":
            self.add_recent("Safe Gate enable cancelled.")
            return
        self.enable_safe_gate_for_tests("MOVE")

    def enable_safe_gate_for_tests(self, confirmation: str) -> bool:
        ok, reason = self.can_enable_safe_gate()
        if not ok or confirmation.strip() != "MOVE":
            self.logger.event("safe_gate_enable_blocked", reason=reason or "MOVE confirmation missing")
            return False
        self.safe_gate_enabled = True
        self.logger.event("safe_gate_enabled", review_dir=str(self.current_review_dir))
        self.add_recent("Safe Gate ON: FILE MOVES ENABLED")
        self.update_safe_gate_banner()
        self.update_commit_enabled()
        return True

    def update_safe_gate_banner(self) -> None:
        if self.safe_gate_enabled:
            self.banner.setText("FILE MOVES ENABLED")
            self.banner.setProperty("enabledMoves", True)
            self.safe_gate_btn.setText("Disable Safe Gate")
        else:
            override = "  |  Dev Core Override" if self.facade.report.developer_override else ""
            self.banner.setText(f"READ-ONLY PREVIEW{override}")
            self.banner.setProperty("enabledMoves", False)
            self.safe_gate_btn.setText("Enable Safe Gate")
        self.banner.style().unpolish(self.banner)
        self.banner.style().polish(self.banner)

    def dry_run_transaction(self) -> tuple[Any | None, str]:
        if self.fast_index is None or self.selected_card_index is None or not self.current_groups:
            return None, "No selected image."
        prefix, members = self.current_groups[self.current_group_index]
        selected = members[self.selected_card_index]
        try:
            transaction = self.core.prepare_transaction_from_fast_index(self.fast_index, prefix, selected)
        except Exception as exc:
            return None, str(exc)
        done_items = [op for op in transaction.operations if op.role == "done"]
        out_items = [op for op in transaction.operations if op.role == "out"]
        summary = [
            "Dry-run transaction summary:",
            f"Prefix: {prefix}",
            f"Selected image/label -> done: {len(done_items)} operations",
            f"Variant images/labels -> out: {len(out_items)} operations",
            "Target conflict check result: PASS",
        ]
        return transaction, "\n".join(summary)

    def commit_selected(self) -> None:
        reason = self.disabled_reason()
        if reason:
            self.show_disabled_reason(reason)
            return
        transaction, summary = self.dry_run_transaction()
        if transaction is None:
            self.add_issue("ERROR", "", "DRY_RUN_FAILED", summary, "Resolve before moving files.")
            self.show_disabled_reason(summary)
            return
        if not os.environ.get("CIVL7009_PICKER_TEST_MODE"):
            response = QMessageBox.question(self, "Confirm move", summary)
            if response != QMessageBox.Yes:
                self.add_recent("Commit cancelled after dry-run.")
                return
        task_id = len(self.move_runner.tasks) + 1
        task = self.core.QueuedMoveTask(
            task_id=task_id,
            review_dir=self.current_review_dir,
            prefix=transaction.prefix,
            selected_stem=transaction.selected_stem,
            transaction=transaction,
        )
        self.move_runner.enqueue(task)
        self.update_queue_model()
        self.add_recent(f"Move queued: {transaction.prefix}")
        self.update_commit_enabled()

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
            self.add_recent(f"Queue {event_name}: {task.prefix} ({task.status})")
            if event_name == "moved":
                self.last_committed_transaction = task.transaction
                if self.fast_index is not None:
                    self.fast_index.apply_queued_transaction(task.transaction)
                    self.current_groups = self.fast_index.selectable_groups()
                    self.current_group_index = min(self.current_group_index, max(0, len(self.current_groups) - 1))
                    self.render_current_group()
            elif event_name == "failed":
                self.add_issue("ERROR", task.prefix, "MOVE_FAILED", task.error, "Inspect recovery panel and filesystem.")
            self.move_event_queue.task_done()
        if changed:
            self.update_queue_model()
            self.update_kpis()
            self.update_commit_enabled()
            self.undo_btn.setEnabled(self.can_undo())

    def can_undo(self) -> bool:
        if self.last_committed_transaction is None or self.move_runner is None:
            return False
        if self.move_runner.blocked_error:
            return False
        return self.move_runner.work_queue.empty()

    def undo_last_transaction(self) -> None:
        if not self.can_undo():
            self.show_disabled_reason("Undo requires an idle queue and a successful transaction.")
            return
        try:
            self.core.undo_transaction(self.last_committed_transaction)
            self.add_recent("Undo completed.")
            self.last_committed_transaction = None
            if self.current_review_dir is not None:
                self.open_review_dir(self.current_review_dir)
        except Exception as exc:
            self.add_issue("ERROR", "", "UNDO_FAILED", str(exc), "Manual recovery may be required.")

    def update_queue_model(self) -> None:
        if self.move_runner is None:
            self.queue_model.set_rows([])
            return
        rows = [
            [task.task_id, task.prefix, task.selected_stem, task.status, task.error]
            for task in self.move_runner.tasks.values()
        ]
        self.queue_model.set_rows(rows)

    def update_issues_from_audit(self) -> None:
        rows: list[list[Any]] = []
        for issue in getattr(self.audit_summary, "blocking_errors", []) or []:
            rows.append(["ERROR", getattr(issue, "prefix", ""), getattr(issue, "error_code", ""), getattr(issue, "message", ""), getattr(issue, "suggested_action", "")])
        for issue in getattr(self.audit_summary, "warnings", []) or []:
            rows.append(["WARN", "", "WARNING", issue, "Review when convenient."])
        if self.recovery_rows:
            rows.append(["ERROR", "", "RECOVERY_PENDING", f"{len(self.recovery_rows)} unfinished transactions", "Resolve recovery before enabling Safe Gate."])
        self.issue_model.set_rows(rows)

    def add_issue(self, severity: str, prefix: str, code: str, message: str, action: str) -> None:
        rows = list(self.issue_model.rows)
        rows.append([severity, prefix, code, message, action])
        self.issue_model.set_rows(rows)

    def update_formula(self) -> None:
        summary = self.audit_summary
        if summary is None:
            self.formula_text.setText("No audit loaded.")
            return
        n = getattr(summary, "group_size", 0)
        done = getattr(summary, "done_prefix_count", 0)
        out = getattr(summary, "out_image_count", 0)
        root_groups = getattr(summary, "root_prefix_count", 0)
        root_images = getattr(summary, "root_image_count", 0)
        label_sync = getattr(summary, "label_sync_status", "")
        self.formula_text.setText(
            f"Review: {getattr(summary, 'review_name', '')}\n"
            f"Root: {root_images} images = {root_groups} groups x {n}\n"
            f"Done/Out: out images {out} = done groups {done} x {max(n - 1, 0)}\n"
            f"Label Sync: {label_sync}\n"
            f"Status: {STATUS}"
        )

    def update_kpis(self) -> None:
        summary = self.audit_summary or (getattr(self.fast_index, "audit_counts", None) if self.fast_index else None)
        self.kpi_labels["Root remaining"].setText(str(getattr(summary, "root_prefix_count", len(self.current_groups))))
        current = f"{self.current_group_index + 1}/{len(self.current_groups)}" if self.current_groups else "0/0"
        self.kpi_labels["Current group"].setText(current)
        self.kpi_labels["Done groups"].setText(str(getattr(summary, "done_prefix_count", 0)))
        self.kpi_labels["Out images"].setText(str(getattr(summary, "out_image_count", 0)))
        queue_count = len(self.move_runner.tasks) if self.move_runner is not None else 0
        failed = sum(1 for task in self.move_runner.tasks.values() if task.status == "FAILED") if self.move_runner is not None else 0
        self.kpi_labels["Move queue"].setText(str(queue_count))
        self.kpi_labels["Failed tasks"].setText(str(failed))
        self.kpi_labels["Label Sync"].setText(str(getattr(summary, "label_sync_status", "PENDING")))
        self.kpi_labels["Audit state"].setText("READY" if self.audit_summary is not None else "BUILDING")

    def export_current_audit(self) -> None:
        if self.current_review_dir is None or self.core is None:
            self.show_disabled_reason("No review dir is open")
            return
        worker = GenericWorker(self.generation, lambda: self.core.export_target_audit_report(self.current_review_dir))
        worker.signals.progress.connect(self.on_open_progress)
        worker.signals.error.connect(self.on_worker_error)
        worker.signals.quick_ready.connect(lambda _gen, result: self.add_recent(f"Audit exported: {result}"))
        self.thread_pool.start(worker)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = event.key()
        if Qt.Key_1 <= key <= Qt.Key_9:
            self.select_card(key - Qt.Key_1)
            return
        if key in (Qt.Key_Return, Qt.Key_Enter):
            self.commit_selected()
            return
        if key == Qt.Key_Escape:
            self.selected_card_index = None
            for card in self.cards:
                card.set_selected(False)
            self.update_commit_enabled()
            return
        super().keyPressEvent(event)

    def release_lock(self) -> None:
        if self.current_lock is not None:
            try:
                self.current_lock.release()
            except Exception:
                pass
            self.current_lock = None

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.open_worker is not None:
            self.open_worker.cancel()
        if self.move_runner is not None:
            self.move_runner.stop()
        self.release_lock()
        self.logger.close()
        super().closeEvent(event)


class GenericWorker(QRunnable):
    def __init__(self, generation: int, fn: Callable[[], Any]) -> None:
        super().__init__()
        self.generation = generation
        self.fn = fn
        self.signals = WorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            self.signals.progress.emit(self.generation, "Exporting report", "Running report service")
            result = self.fn()
            self.signals.quick_ready.emit(self.generation, result)
        except Exception as exc:
            self.signals.error.emit(self.generation, "REPORT_EXPORT_FAILED", str(exc))


def file_tree_fingerprint(root: Path) -> dict[str, Any]:
    image_exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}
    label_exts = {".txt"}
    counts = {"images": 0, "labels": 0, "manualreview_staging": 0, "done": 0, "out": 0, "root": 0}
    for item in root.rglob("*"):
        if item.is_dir() and item.name == "_ManualReview_Staging":
            counts["manualreview_staging"] += 1
        if not item.is_file():
            continue
        suffix = item.suffix.lower()
        if suffix in image_exts:
            counts["images"] += 1
        if suffix in label_exts:
            counts["labels"] += 1
        if suffix not in image_exts and suffix not in label_exts:
            continue
        parent_name = item.parent.name.casefold()
        if parent_name == "done":
            counts["done"] += 1
        elif parent_name == "out":
            counts["out"] += 1
        elif "manualreview_groupsize_" in item.parent.name.casefold():
            counts["root"] += 1
    return counts


def create_app(argv: list[str] | None = None) -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication(argv or sys.argv)
    app.setApplicationName("CIVL7009 Source Group Picker")
    return app


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CIVL7009 Source Group Picker V1.9 PySide6 Review Cockpit.")
    parser.add_argument("--core-path", default="", help="Explicit V1.8.1 core path.")
    parser.add_argument("--developer-mode", action="store_true", help="Allow sibling core override.")
    parser.add_argument("--audit-only", action="store_true", help="Export audit and exit.")
    parser.add_argument("--id-root", default="", help="ID root for --audit-only.")
    parser.add_argument("--image-dir", default="", help="Single review image dir for --audit-only.")
    parser.add_argument("--run-mode", default="", help="gui_production, audit_only, test, debug.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if QT_IMPORT_ERROR is not None and not args.audit_only:
        print(f"PySide6 import failed: {QT_IMPORT_ERROR}", file=sys.stderr)
        return 2
    run_mode = args.run_mode or ("audit_only" if args.audit_only else detect_run_mode())
    logger = V19Logger(run_mode)
    facade = PickerCoreFacade(
        logger,
        explicit_core_path=Path(args.core_path) if args.core_path else None,
        developer_mode=args.developer_mode or not getattr(sys, "frozen", False),
    )
    report = facade.load()
    if args.audit_only:
        if not report.ok or facade.core is None:
            print(json.dumps({"status": "CORE_LOAD_FAILED", "error": asdict(report)}, ensure_ascii=False, default=str))
            logger.close()
            return 1
        try:
            if args.id_root:
                run_dir = facade.core.export_audit_report(Path(args.id_root))
            elif args.image_dir:
                run_dir = facade.core.export_target_audit_report(Path(args.image_dir))
            else:
                raise RuntimeError("--audit-only requires --id-root or --image-dir")
            print(json.dumps({"status": STATUS, "run_dir": str(run_dir)}, ensure_ascii=False))
            logger.close()
            return 0
        except Exception as exc:
            logger.event("audit_only_failed", error=str(exc))
            logger.close()
            raise
    app = create_app(argv)
    window = MainWindow(facade, logger)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
