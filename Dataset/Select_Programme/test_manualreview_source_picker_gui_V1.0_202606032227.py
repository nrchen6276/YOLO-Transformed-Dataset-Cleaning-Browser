from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    PROJECT_ROOT
    / "Dataset"
    / "Select_Programme"
    / "CIVL7009_manualreview_source_picker_gui_V1.0_202606032227.py"
)

spec = importlib.util.spec_from_file_location("manualreview_gui_v1", SCRIPT_PATH)
manualreview_gui_v1 = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules["manualreview_gui_v1"] = manualreview_gui_v1
spec.loader.exec_module(manualreview_gui_v1)


def write_image(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"fake-image")


def write_label(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("0 0.5 0.5 0.5 0.5\n", encoding="utf-8")


def make_id_root(tmp: str) -> Path:
    root = Path(tmp) / "Dataset" / "Source_Archive" / "01"
    (root / "images").mkdir(parents=True)
    (root / "labels").mkdir(parents=True)
    return root


def make_review(root: Path, group_size: int) -> tuple[Path, Path]:
    img = root / "images" / f"ManualReview_GroupSize_{group_size}"
    lab = root / "labels" / f"ManualReview_GroupSize_{group_size}"
    img.mkdir(parents=True)
    lab.mkdir(parents=True)
    return img, lab


class ManualReviewSourcePickerTests(unittest.TestCase):
    def test_prefix_includes_rf_marker(self) -> None:
        prefix, mode = manualreview_gui_v1.get_prefix(
            Path("1DamG17_jpg.rf.01ce34c3c9dfbc7a115bc3a5c5f6c68a.jpg")
        )
        self.assertEqual(prefix, "1DamG17_jpg.rf.")
        self.assertEqual(mode, "rf_prefix")

    def test_id_root_scans_only_manualreview_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_id_root(tmp)
            make_review(root, 2)
            (root / "images" / "transformations").mkdir()
            (root / "images" / "Done").mkdir()
            dirs = manualreview_gui_v1.review_dirs_for_id_root(root)
            self.assertEqual([path.name for path in dirs], ["ManualReview_GroupSize_2"])

    def test_group_size_1_missing_label_dir_is_readonly_stat_not_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_id_root(tmp)
            img = root / "images" / "ManualReview_GroupSize_1"
            img.mkdir(parents=True)
            write_image(img / "single.rf.a.jpg")
            summary, _rows = manualreview_gui_v1.audit_review_dir(img)
            self.assertEqual(summary.root_image_count, 1)
            self.assertEqual(summary.root_prefix_count, 1)
            self.assertEqual(summary.selectable_group_count, 0)
            self.assertEqual(summary.errors, [])
            self.assertGreaterEqual(len(summary.warnings), 1)
            self.assertEqual(manualreview_gui_v1.selectable_groups(img), [])

    def test_illegal_image_child_dir_blocks_audit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_id_root(tmp)
            img, _lab = make_review(root, 2)
            (img / "Done_auto").mkdir()
            with self.assertRaises(manualreview_gui_v1.ManualReviewError):
                manualreview_gui_v1.audit_review_dir(img)

    def test_root_group_size_mismatch_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_id_root(tmp)
            img, lab = make_review(root, 3)
            write_image(img / "case.rf.a.jpg")
            write_image(img / "case.rf.b.jpg")
            write_label(lab / "case.rf.a.txt")
            write_label(lab / "case.rf.b.txt")
            summary, _rows = manualreview_gui_v1.audit_review_dir(img, create_missing=True)
            self.assertEqual(summary.root_invalid_group_count, 1)
            self.assertGreater(len(summary.errors), 0)

    def test_completed_group_size_4_formula_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_id_root(tmp)
            img, lab = make_review(root, 4)
            for idx in range(2):
                prefix = f"g{idx}.rf."
                done = img / "done" / f"{prefix}src.jpg"
                write_image(done)
                write_label(lab / "done" / f"{done.stem}.txt")
                for out_idx in range(3):
                    out = img / "out" / f"{prefix}out{out_idx}.jpg"
                    write_image(out)
                    write_label(lab / "out" / f"{out.stem}.txt")
            summary, _rows = manualreview_gui_v1.audit_review_dir(img, create_missing=True)
            self.assertTrue(summary.image_rule_pass)
            self.assertEqual(summary.done_image_count, 2)
            self.assertEqual(summary.out_image_count, 6)
            self.assertTrue(summary.out_image_count_equals_done_times_expected)
            self.assertEqual(summary.out_group_size_distribution, {3: 2})
            self.assertTrue(summary.label_position_sync_pass)

    def test_completed_group_size_5_formula_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_id_root(tmp)
            img, lab = make_review(root, 5)
            done = img / "done" / "g.rf.src.jpg"
            write_image(done)
            write_label(lab / "done" / f"{done.stem}.txt")
            for out_idx in range(4):
                out = img / "out" / f"g.rf.out{out_idx}.jpg"
                write_image(out)
                write_label(lab / "out" / f"{out.stem}.txt")
            summary, _rows = manualreview_gui_v1.audit_review_dir(img, create_missing=True)
            self.assertTrue(summary.image_rule_pass)
            self.assertEqual(summary.out_image_count, summary.done_prefix_count * 4)
            self.assertEqual(summary.out_group_size_distribution, {4: 1})

    def test_out_prefix_missing_fails_image_rule(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_id_root(tmp)
            img, lab = make_review(root, 3)
            done = img / "done" / "g.rf.src.jpg"
            write_image(done)
            write_label(lab / "done" / f"{done.stem}.txt")
            summary, rows = manualreview_gui_v1.audit_review_dir(img, create_missing=True)
            self.assertFalse(summary.image_rule_pass)
            self.assertTrue(any("done_prefix_missing_out" in row.audit_status for row in rows))

    def test_click_transaction_moves_images_and_labels_from_auto_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_id_root(tmp)
            img, lab = make_review(root, 2)
            a = img / "case.rf.a.jpg"
            b = img / "case.rf.b.jpg"
            write_image(a)
            write_image(b)
            write_label(lab / "Done_auto" / "case.rf.a.txt")
            write_label(lab / "Out_auto" / "case.rf.b.txt")

            transaction = manualreview_gui_v1.prepare_transaction(img, "case.rf.", b)
            manualreview_gui_v1.execute_transaction(transaction)

            self.assertTrue((img / "done" / b.name).exists())
            self.assertTrue((img / "out" / a.name).exists())
            self.assertTrue((lab / "done" / "case.rf.b.txt").exists())
            self.assertTrue((lab / "out" / "case.rf.a.txt").exists())
            self.assertFalse((lab / "Done_auto" / "case.rf.a.txt").exists())
            self.assertFalse((lab / "Out_auto" / "case.rf.b.txt").exists())

    def test_duplicate_label_blocks_transaction(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_id_root(tmp)
            img, lab = make_review(root, 2)
            write_image(img / "case.rf.a.jpg")
            write_image(img / "case.rf.b.jpg")
            write_label(lab / "case.rf.a.txt")
            write_label(lab / "Done_auto" / "case.rf.a.txt")
            write_label(lab / "case.rf.b.txt")
            with self.assertRaises(manualreview_gui_v1.ManualReviewError):
                manualreview_gui_v1.prepare_transaction(img, "case.rf.", img / "case.rf.a.jpg")

    def test_undo_transaction_restores_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_id_root(tmp)
            img, lab = make_review(root, 2)
            a = img / "case.rf.a.jpg"
            b = img / "case.rf.b.jpg"
            write_image(a)
            write_image(b)
            write_label(lab / "case.rf.a.txt")
            write_label(lab / "case.rf.b.txt")
            transaction = manualreview_gui_v1.execute_transaction(
                manualreview_gui_v1.prepare_transaction(img, "case.rf.", a)
            )
            manualreview_gui_v1.undo_transaction(transaction)
            self.assertTrue(a.exists())
            self.assertTrue(b.exists())
            self.assertTrue((lab / "case.rf.a.txt").exists())
            self.assertTrue((lab / "case.rf.b.txt").exists())
            self.assertFalse((img / "done" / a.name).exists())

    def test_export_audit_defaults_to_select_programme_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_id_root(tmp)
            img, lab = make_review(root, 3)
            for suffix in ["a", "b", "c"]:
                path = img / f"case.rf.{suffix}.jpg"
                write_image(path)
                write_label(lab / f"{path.stem}.txt")
            run_dir = manualreview_gui_v1.export_audit_report(root)
            self.assertIn("Dataset\\Select_Programme\\Audit_Reports", str(run_dir))
            self.assertNotIn("Data_Governance", str(run_dir))
            self.assertTrue(any(path.name.endswith(".md") for path in run_dir.iterdir()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
