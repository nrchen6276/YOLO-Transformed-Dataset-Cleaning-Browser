from __future__ import annotations

import json
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("CIVL7009_PICKER_RUN_MODE", "test")

from PIL import Image
from PySide6.QtWidgets import QApplication

from civl7009_picker_v3_0.app import MainWindow
from civl7009_picker_v3_0.assets import AssetService
from civl7009_picker_v3_0.manual_objects import ManualObjectsService, sha256_file
from civl7009_picker_v3_0.paths import ASSET_DIR


def app() -> QApplication:
    existing = QApplication.instance()
    if existing is not None:
        return existing
    return QApplication(["test"])


def write_image(path: Path, colour: tuple[int, int, int] = (20, 80, 70)) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (42, 36), colour).save(path)


def write_label(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("0 0.5 0.5 0.2 0.2\n", encoding="utf-8")


def make_special_source_group(root: Path) -> Path:
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
    return image_dir


def make_manual_group(root: Path, reason: str, bucket: str, group_name: str, count: int = 2) -> Path:
    group_dir = root / reason / bucket / group_name
    group_dir.mkdir(parents=True, exist_ok=True)
    items = []
    for idx in range(count):
        dataset_id = f"ID{idx + 1:02d}"
        stem = f"{dataset_id}_case_{idx + 1}"
        image = group_dir / f"{stem}.jpg"
        label = group_dir / f"{stem}.txt"
        write_image(image, (20 + idx * 10, 80, 70))
        write_label(label)
        items.append(
            {
                "item_id": f"item_{idx + 1}",
                "dataset_id": dataset_id,
                "image_filename": image.name,
                "label_filename": label.name,
                "image_path_relative_to_group": image.name,
                "label_path_relative_to_group": label.name,
                "source_image_project_path": f"Dataset/Source_Archive/{dataset_id}/images/demo/{image.name}",
                "source_label_project_path": f"Dataset/Source_Archive/{dataset_id}/labels/demo/{label.name}",
                "image_sha256": sha256_file(image),
                "label_sha256": sha256_file(label),
                "source_size": image.stat().st_size,
                "source_mtime": image.stat().st_mtime,
                "width": 42,
                "height": 36,
                "label_line_count": 1,
                "label_class_set": [0],
                "metrics": {"reason_score": 0, "phash_distance": idx},
            }
        )
    manifest = {
        "schema_version": "CIVL7009_MANUAL_OBJECTS_GROUP_V1",
        "group_key": f"{reason}:{bucket}:{group_name}",
        "reason": reason,
        "group_size": count,
        "dataset_ids": [item["dataset_id"] for item in items],
        "claim_status": "PENDING_AUDIT",
        "items": items,
    }
    (group_dir / "group_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return group_dir


class V30Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.qt = app()

    def test_assets_manifest_and_no_raster(self) -> None:
        AssetService().ensure_assets()
        self.assertTrue((ASSET_DIR / "asset_manifest.json").exists())
        self.assertTrue((ASSET_DIR / "asset_prompt_log.json").exists())
        raster = [path for path in ASSET_DIR.rglob("*") if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}]
        self.assertEqual(raster, [])

    def test_workflow_tabs_exist(self) -> None:
        window = MainWindow(run_mode="test")
        try:
            self.assertEqual(len(window.workflow_buttons), 3)
            self.assertIn("图源组筛选", window.workflow_buttons[0].text())
            self.assertIn("Manual Objects", window.workflow_buttons[1].text())
            window.set_workflow(1)
            self.assertEqual(window.stack.currentIndex(), 1)
        finally:
            window.close()

    def test_manual_objects_service_loads_and_writes_selection_with_history(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "Manual_Objects"
            group_dir = make_manual_group(root, "SHA256_EXACT_IMAGE", "N02", "G000001", 2)
            service = ManualObjectsService(root)
            groups = service.list_groups()
            self.assertEqual(len(groups), 1)
            group = groups[0]
            self.assertTrue(group.can_write_selection, group.issues)
            self.assertEqual(len(group.items), 2)
            first = service.save_selection(group, "APPROVED", ["item_1"], ["item_2"], notes="ok")
            self.assertTrue(first.exists())
            group = service.load_group(group_dir)
            second = service.save_selection(group, "AMBIGUOUS", ["item_1"], [], notes="near hash remains ambiguous")
            self.assertTrue(second.exists())
            history = list((group_dir / "_selection_history").glob("manual_selection_*.json"))
            self.assertEqual(len(history), 1)
            payload = json.loads(second.read_text(encoding="utf-8"))
            self.assertEqual(payload["review_status"], "AMBIGUOUS")

    def test_manual_objects_invalid_manifest_blocks_write(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "Manual_Objects"
            group_dir = make_manual_group(root, "PHASH_NEAR_STRONG", "N03", "G000002", 3)
            (group_dir / "ID02_case_2.jpg").write_bytes(b"changed")
            group = ManualObjectsService(root).list_groups()[0]
            codes = {issue.code for issue in group.issues}
            self.assertIn("IMAGE_SHA256_MISMATCH", codes)
            self.assertFalse(group.can_write_selection)
            with self.assertRaises(RuntimeError):
                ManualObjectsService(root).save_selection(group, "APPROVED", ["item_1"], ["item_2", "item_3"])

    def test_manual_objects_page_renders_and_saves(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "Manual_Objects"
            group_dir = make_manual_group(root, "COMPOSITE_NEAR_HASH", "N02", "G000003", 2)
            window = MainWindow(run_mode="test")
            try:
                window.set_workflow(1)
                window.load_manual_root(root)
                self.assertEqual(window.manual_group_model.rowCount(), 1)
                self.assertEqual(len(window.manual_cards), 2)
                window.select_manual_item("item_1")
                self.assertEqual(window.manual_cards[0].item.selection_state, "KEEP")
                self.assertEqual(window.manual_cards[1].item.selection_state, "REMOVE")
                window.save_manual_selection("APPROVED")
                selection = json.loads((group_dir / "manual_selection.json").read_text(encoding="utf-8"))
                self.assertEqual(selection["selected_keep_item_ids"], ["item_1"])
                self.assertEqual(selection["selected_remove_item_ids"], ["item_2"])
            finally:
                window.close()

    def test_source_group_special_directory_still_works(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            review_dir = make_special_source_group(root)
            window = MainWindow(run_mode="test")
            try:
                window.open_review_dir(review_dir)
                self.assertTrue(window.fast_index.ready_for_commit)
                self.assertEqual(len(window.current_groups), 2)
                self.assertGreaterEqual(len(window.source_cards), 2)
            finally:
                window.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
