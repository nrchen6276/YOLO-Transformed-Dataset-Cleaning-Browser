from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("CIVL7009_PICKER_RUN_MODE", "test")
os.environ.setdefault("CIVL7009_PICKER_TEST_MODE", "1")

from PIL import Image
from PySide6.QtWidgets import QApplication


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    PROJECT_ROOT
    / "Dataset"
    / "Select_Programme"
    / "CIVL7009_source_group_picker_qt_V1.9_202606041626.py"
)

spec = importlib.util.spec_from_file_location("source_group_picker_qt_v19", SCRIPT_PATH)
source_group_picker_qt_v19 = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules["source_group_picker_qt_v19"] = source_group_picker_qt_v19
spec.loader.exec_module(source_group_picker_qt_v19)


def write_image(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (32, 24), (9, 68, 56)).save(path)


def write_label(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("0 0.5 0.5 0.5 0.5\n", encoding="utf-8")


def make_review(tmp: str, group_size: int = 3) -> tuple[Path, Path, Path]:
    root = Path(tmp) / "Dataset" / "Source_Archive" / "01"
    img = root / "images" / f"ManualReview_GroupSize_{group_size}"
    lab = root / "labels" / f"ManualReview_GroupSize_{group_size}"
    (img / "done").mkdir(parents=True)
    (img / "out").mkdir(parents=True)
    (lab / "done").mkdir(parents=True)
    (lab / "out").mkdir(parents=True)
    return root, img, lab


def process_events(app: QApplication, duration_ms: int = 20) -> None:
    deadline = time.time() + duration_ms / 1000.0
    while time.time() < deadline:
        app.processEvents()
        time.sleep(0.002)


class SourceGroupPickerQtV19Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = source_group_picker_qt_v19.create_app([])

    def make_facade(self) -> tuple[object, object]:
        logger = source_group_picker_qt_v19.V19Logger("test")
        facade = source_group_picker_qt_v19.PickerCoreFacade(logger, developer_mode=True)
        report = facade.load()
        self.assertTrue(report.ok, report)
        return logger, facade

    def test_asset_manifest_declares_no_dataset_images(self) -> None:
        manifest_path = (
            PROJECT_ROOT
            / "Dataset"
            / "Select_Programme"
            / "UI_Assets"
            / "V1.9_202606041626"
            / "asset_manifest.json"
        )
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertFalse(data["policy"]["contains_dataset_image"])
        self.assertFalse(data["policy"]["internet_assets_used"])
        for asset in data["assets"]:
            self.assertFalse(asset["contains_dataset_image"])
            path = manifest_path.parent / asset["asset_name"]
            self.assertTrue(path.exists())
            self.assertEqual(source_group_picker_qt_v19.sha256_file(path), asset["sha256"])

    def test_core_facade_loads_v181_without_version_spoofing(self) -> None:
        logger, facade = self.make_facade()
        try:
            self.assertEqual(facade.core.SCRIPT_VERSION, "V1.8.1")
            self.assertEqual(logger.core_meta["core_version"], "V1.8.1")
            self.assertEqual(logger.core_meta["core_timecode"], "202606041443")
            self.assertIsNone(facade.core.RUNTIME_LOGGER)
            self.assertIn("core_sha256", logger.core_meta)
            self.assertFalse(facade.report.missing_symbols)
        finally:
            logger.close()

    def test_core_facade_fails_closed_for_missing_symbols(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bad_core = Path(tmp) / "bad_core.py"
            bad_core.write_text("SCRIPT_VERSION='bad'\nSCRIPT_TIMECODE='bad'\n", encoding="utf-8")
            logger = source_group_picker_qt_v19.V19Logger("test")
            facade = source_group_picker_qt_v19.PickerCoreFacade(logger, explicit_core_path=bad_core)
            try:
                report = facade.load()
                self.assertFalse(report.ok)
                self.assertIn("build_quick_preview_index", report.missing_symbols)
                self.assertIsNone(facade.core)
            finally:
                logger.close()

    def test_safe_gate_off_preview_does_not_move_or_create_transaction_journal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _root, img, lab = make_review(tmp, 3)
            for suffix in ["a", "b", "c"]:
                image = img / f"case.rf.{suffix}.jpg"
                write_image(image)
                write_label(lab / f"{image.stem}.txt")
            before = source_group_picker_qt_v19.file_tree_fingerprint(Path(tmp))
            logger, facade = self.make_facade()
            window = source_group_picker_qt_v19.MainWindow(facade, logger)
            window.show()
            try:
                index = facade.core.build_fast_review_index(img)
                summary, rows = facade.core.audit_review_dir(img, create_missing=False)
                lock = facade.core.ReviewDirLock(img)
                lock.acquire()
                window.current_review_dir = img
                window.current_lock = lock
                window.fast_index = index
                window.audit_summary = summary
                window.audit_rows = rows
                window.current_groups = index.selectable_groups()
                window.render_current_group()
                process_events(self.app, 80)
                window.select_card(0)
                after = source_group_picker_qt_v19.file_tree_fingerprint(Path(tmp))
                self.assertEqual(before, after)
                self.assertFalse(logger.transaction_path.exists())
                self.assertFalse(window.safe_gate_enabled)
            finally:
                window.close()
                process_events(self.app, 80)

    def test_safe_gate_on_moves_and_undo_restores_temp_dataset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _root, img, lab = make_review(tmp, 3)
            for suffix in ["a", "b", "c"]:
                image = img / f"case.rf.{suffix}.jpg"
                write_image(image)
                write_label(lab / f"{image.stem}.txt")
            before = source_group_picker_qt_v19.file_tree_fingerprint(Path(tmp))
            logger, facade = self.make_facade()
            window = source_group_picker_qt_v19.MainWindow(facade, logger)
            window.show()
            try:
                index = facade.core.build_fast_review_index(img)
                summary, rows = facade.core.audit_review_dir(img, create_missing=False)
                lock = facade.core.ReviewDirLock(img)
                lock.acquire()
                window.current_review_dir = img
                window.current_lock = lock
                window.fast_index = index
                window.audit_summary = summary
                window.audit_rows = rows
                window.current_groups = index.selectable_groups()
                window.render_current_group()
                process_events(self.app, 80)
                self.assertTrue(window.enable_safe_gate_for_tests("MOVE"))
                window.select_card(0)
                window.commit_selected()
                for _ in range(100):
                    process_events(self.app, 30)
                    window.poll_move_events()
                    if window.last_committed_transaction is not None:
                        break
                self.assertIsNotNone(window.last_committed_transaction)
                self.assertTrue(logger.transaction_path.exists())
                self.assertEqual(len(list((img / "done").glob("*.jpg"))), 1)
                self.assertEqual(len(list((img / "out").glob("*.jpg"))), 2)
                self.assertTrue(window.can_undo())
                window.undo_last_transaction()
                for _ in range(20):
                    process_events(self.app, 20)
                after = source_group_picker_qt_v19.file_tree_fingerprint(Path(tmp))
                self.assertEqual(before, after)
            finally:
                window.close()
                process_events(self.app, 80)

    def test_open_review_progress_and_ready_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _root, img, lab = make_review(tmp, 2)
            for suffix in ["a", "b"]:
                image = img / f"case.rf.{suffix}.jpg"
                write_image(image)
                write_label(lab / f"{image.stem}.txt")
            logger, facade = self.make_facade()
            window = source_group_picker_qt_v19.MainWindow(facade, logger)
            window.show()
            try:
                window.open_review_dir(img)
                self.assertTrue(window.overlay.isVisible())
                for _ in range(160):
                    process_events(self.app, 25)
                    if window.fast_index is not None:
                        break
                self.assertIsNotNone(window.quick_index)
                self.assertIsNotNone(window.fast_index)
                self.assertFalse(window.safe_gate_enabled)
                self.assertIn("READ-ONLY", window.banner.text())
                self.assertIn("Ready", window.progress_chip.text())
            finally:
                window.close()
                process_events(self.app, 120)


if __name__ == "__main__":
    unittest.main(verbosity=2)
