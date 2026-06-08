from __future__ import annotations

import os
import shutil
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("CIVL7009_PICKER_RUN_MODE", "test")

from PIL import Image
from PySide6.QtWidgets import QApplication

from civl7009_picker_v2_2_4.app import MainWindow
from civl7009_picker_v2_2_4.assets import AssetService
from civl7009_picker_v2_2_4.core import PickerCoreFacade
from civl7009_picker_v2_2_4.paths import ASSET_DIR, PROGRAMME_DIR
from civl7009_picker_v2_2_4.version import CORE_FILENAME
import civl7009_picker_v2_2_4.core as core_module


def app() -> QApplication:
    existing = QApplication.instance()
    if existing is not None:
        return existing
    return QApplication(["test"])


def write_image(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (40, 32), (20, 80, 70)).save(path)


def write_label(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("0 0.5 0.5 0.2 0.2\n", encoding="utf-8")


def make_review_dataset(root: Path, group_size: int = 2) -> Path:
    image_dir = root / "images" / f"ManualReview_GroupSize_{group_size}"
    label_dir = root / "labels" / f"ManualReview_GroupSize_{group_size}"
    for suffix in [chr(ord("a") + idx) for idx in range(group_size)]:
        write_image(image_dir / f"case.rf.{suffix}.jpg")
        write_label(label_dir / f"case.rf.{suffix}.txt")
    return image_dir


def make_mixed_special_dataset(root: Path) -> Path:
    image_dir = root / "images" / "special"
    label_dir = root / "labels" / "special"
    for folder in [image_dir / "done", image_dir / "out", label_dir / "done", label_dir / "out"]:
        folder.mkdir(parents=True, exist_ok=True)
    for stem in ["case-a_jpg.rf.aaa", "case-a_jpg.rf.bbb"]:
        write_image(image_dir / f"{stem}.jpg")
        write_label(label_dir / f"{stem}.txt")
    for stem in ["case-b_jpg.rf.111", "case-b_jpg.rf.222", "case-b_jpg.rf.333"]:
        write_image(image_dir / f"{stem}.jpg")
        write_label(label_dir / f"{stem}.txt")
    write_image(image_dir / "single_jpg.rf.only.jpg")
    write_label(label_dir / "single_jpg.rf.only.txt")
    write_image(image_dir / "broken_jpg.rfdeadbeef.jpg")
    write_label(label_dir / "broken_jpg.rfdeadbeef.txt")
    return image_dir


def wait_until(condition, qt_app: QApplication, timeout: float = 5.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        qt_app.processEvents()
        if condition():
            return True
        time.sleep(0.03)
    qt_app.processEvents()
    return condition()


class V223PickerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.qt = app()

    def test_image2_assets_manifest_and_no_raster_extension(self) -> None:
        AssetService().ensure_assets()
        self.assertTrue((ASSET_DIR / "asset_manifest.json").exists())
        self.assertTrue((ASSET_DIR / "asset_prompt_log.json").exists())
        self.assertTrue((ASSET_DIR / "image2_glass_cockpit.svg").exists())
        raster_assets = [path for path in ASSET_DIR.rglob("*") if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}]
        self.assertEqual(raster_assets, [])

    def test_keypad_layouts_follow_numeric_keypad(self) -> None:
        facade = PickerCoreFacade()
        self.assertTrue(facade.report.ok)
        slots2 = {slot.key: (slot.row, slot.col) for slot in facade.keypad_slots(2)}
        self.assertEqual(slots2, {"1": (0, 0), "2": (0, 1)})
        slots4 = {slot.key: (slot.row, slot.col) for slot in facade.keypad_slots(4)}
        self.assertEqual(slots4["4"], (0, 0))
        self.assertEqual(slots4["1"], (1, 0))
        self.assertEqual(slots4["2"], (1, 1))
        self.assertEqual(slots4["3"], (1, 2))
        slots9 = {slot.key: (slot.row, slot.col) for slot in facade.keypad_slots(9)}
        self.assertEqual(slots9["7"], (0, 0))
        self.assertEqual(slots9["8"], (0, 1))
        self.assertEqual(slots9["9"], (0, 2))
        self.assertEqual(slots9["1"], (2, 0))
        slots10 = facade.keypad_slots(10)
        self.assertEqual(slots10[8].key, "9")
        self.assertIsNone(slots10[9].key)
        self.assertEqual((slots10[9].row, slots10[9].col), (3, 0))

    def test_empty_state_has_directory_entry_points(self) -> None:
        window = MainWindow(run_mode="test")
        try:
            self.assertIn("ID", window.choose_id_btn.text())
            self.assertIn("筛选", window.choose_review_btn.text())
            self.assertEqual(window.stack.currentIndex(), 0)
            self.assertTrue(hasattr(window, "nav_buttons"))
            self.assertEqual(len(window.nav_buttons), 7)
            self.assertFalse(hasattr(window, "sidebar"))
            self.assertTrue(hasattr(window, "review_vertical_splitter"))
            self.assertTrue(hasattr(window, "bottom_splitter"))
            self.assertTrue(hasattr(window, "nav_status_chip"))
            self.assertIn("就绪", window.nav_status_chip.text())
            self.assertTrue(window.context_label.toolTip())
            self.assertEqual(window.bottom_splitter.count(), 2)
            self.assertGreaterEqual(min(window.review_vertical_splitter.sizes()), 0)
        finally:
            window.close()

    def test_startup_notice_confirmation_arms_auto_move(self) -> None:
        window = MainWindow(run_mode="test")
        try:
            self.assertFalse(window.auto_move_armed)
            window.acknowledge_startup_notice_for_tests()
            self.assertTrue(window.auto_move_armed)
            self.assertTrue(window.startup_notice_shown)
        finally:
            window.close()

    def test_core_loader_uses_bundled_candidate_when_exe_sibling_missing(self) -> None:
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            missing_sibling = tmp_path / "moved_exe_dir" / CORE_FILENAME
            bundled_core = tmp_path / "_MEIPASS" / CORE_FILENAME
            bundled_core.parent.mkdir(parents=True)
            shutil.copy2(PROGRAMME_DIR / CORE_FILENAME, bundled_core)

            old_candidates = core_module.CORE_CANDIDATES
            try:
                core_module.CORE_CANDIDATES = [missing_sibling, bundled_core]
                facade = PickerCoreFacade()
            finally:
                core_module.CORE_CANDIDATES = old_candidates

            self.assertTrue(facade.report.ok, facade.report.error)
            self.assertEqual(facade.report.path, bundled_core.resolve())
            self.assertIn(str(missing_sibling.resolve()), facade.report.candidate_paths)

    def test_id_root_scan_populates_review_board(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_review_dataset(root, group_size=2)
            window = MainWindow(run_mode="test")
            try:
                window.load_id_root(root)
                self.assertGreaterEqual(window.review_model.rowCount(), 1)
                self.assertIn("ManualReview_GroupSize_2", window.review_model.rows[0][0])
            finally:
                window.close()

    def test_auto_move_enables_after_review_ready_without_move_text(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            review_dir = make_review_dataset(root, group_size=2)
            window = MainWindow(run_mode="test")
            try:
                window.acknowledge_startup_notice_for_tests()
                window.open_review_dir(review_dir)
                self.assertTrue(wait_until(lambda: window.fast_index is not None, self.qt, timeout=8.0))
                self.assertTrue(wait_until(lambda: window.safe_gate_enabled, self.qt, timeout=3.0))
                self.assertIn("暂停", window.safe_gate_btn.text())
            finally:
                window.close()

    def test_safe_gate_off_preview_does_not_move_then_on_moves_and_undoes(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            review_dir = make_review_dataset(root, group_size=2)
            before_transactions = {
                path: path.stat().st_size
                for path in (PROGRAMME_DIR / "Runtime_Logs").rglob("file_transactions_V1.8.*_*.jsonl")
            }
            window = MainWindow(run_mode="test")
            try:
                window.open_review_dir(review_dir)
                self.assertTrue(wait_until(lambda: window.fast_index is not None, self.qt, timeout=8.0))
                self.assertTrue(window.current_groups)
                window.select_card(0)
                self.qt.processEvents()
                self.assertTrue(window.cards[0].property("selected"))
                self.assertEqual(window.cards[0].property("selectedState"), "true")
                self.assertEqual(window.cards[0].target_label.property("selectedState"), "true")
                self.assertEqual(window.cards[0].target_label.text(), "已选图源预览")
                self.assertTrue(window.cards[0].preview.property("selected"))
                self.assertEqual(window.cards[0].preview.property("selectedState"), "true")
                self.assertEqual(window.cards[1].property("selectedState"), "false")
                self.assertTrue((review_dir / "case.rf.a.jpg").exists())
                self.assertFalse((review_dir / "done" / "case.rf.a.jpg").exists())
                after_preview_transactions = {
                    path: path.stat().st_size
                    for path in (PROGRAMME_DIR / "Runtime_Logs").rglob("file_transactions_V1.8.*_*.jsonl")
                }
                new_or_changed = {
                    path: size
                    for path, size in after_preview_transactions.items()
                    if before_transactions.get(path, 0) != size
                }
                self.assertEqual(new_or_changed, {})

                self.assertTrue(window.enable_safe_gate_for_tests())
                window.select_card(0)
                self.assertTrue(
                    wait_until(
                        lambda: (review_dir / "done" / "case.rf.a.jpg").exists() or (review_dir / "done" / "case.rf.b.jpg").exists(),
                        self.qt,
                        timeout=8.0,
                    )
                )
                self.assertTrue(
                    wait_until(
                        lambda: (window.poll_move_events() or True) and window.last_committed_transaction is not None,
                        self.qt,
                        timeout=5.0,
                    )
                )
                self.assertIsNotNone(window.last_committed_transaction)
                self.assertTrue(window.can_undo())
                window.undo_last_transaction()
                self.assertTrue(wait_until(lambda: (review_dir / "case.rf.a.jpg").exists() and (review_dir / "case.rf.b.jpg").exists(), self.qt, timeout=5.0))
                self.assertEqual(window.current_review_dir, review_dir.resolve())
                self.assertIsNotNone(window.fast_index)
                self.assertTrue(window.current_groups)
                self.assertEqual(window.current_groups[window.current_group_index][0], "case.rf.")
                self.assertFalse(window.last_committed_transaction)
                self.assertEqual(window.stack.currentIndex(), 0)
                self.assertFalse(window.overlay.isVisible())
                self.assertIn("撤销完成", window.nav_status_chip.toolTip())
                self.assertIn("撤销完成", window.nav_status_full_text)
            finally:
                window.close()

    def test_safe_gate_badge_is_single_line_and_nav_status_persists(self) -> None:
        window = MainWindow(run_mode="test")
        try:
            window.safe_gate_enabled = True
            window.update_safe_gate()
            self.assertNotIn("\n", window.status_badge.text())
            self.assertGreaterEqual(window.status_badge.minimumWidth(), 156)
            window.set_nav_status("撤销完成：当前目录已刷新")
            window.set_page(3)
            self.assertIn("撤销完成", window.nav_status_chip.toolTip())
            self.assertIn("撤销完成", window.nav_status_full_text)
        finally:
            window.close()

    def test_nonstandard_special_mixed_group_dir_can_prepare_transactions(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            review_dir = make_mixed_special_dataset(root)
            facade = PickerCoreFacade()
            self.assertTrue(facade.report.ok, facade.report.error)
            summary, _rows = facade.audit(review_dir)
            index = facade.fast_index(review_dir)
            self.assertEqual(summary.group_size, 0)
            self.assertTrue(summary.can_select)
            self.assertEqual(summary.selectable_group_count, 2)
            self.assertEqual(summary.root_group_size_distribution, {1: 2, 2: 1, 3: 1})
            self.assertEqual(len(summary.blocking_errors), 0)
            self.assertGreaterEqual(len(summary.info), 1)
            self.assertTrue(index.ready_for_commit)
            self.assertEqual(len(index.root_prefix_queue), 2)

            prefix = "case-a_jpg.rf."
            selected = index.root_groups_by_prefix[prefix][0]
            transaction = facade.require_core().prepare_transaction_from_fast_index(index, prefix, selected)
            self.assertEqual(transaction.group_size, 2)
            self.assertEqual(len(transaction.operations), 4)
            roles = [operation.role for operation in transaction.operations]
            self.assertEqual(roles.count("done"), 2)
            self.assertEqual(roles.count("out"), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
