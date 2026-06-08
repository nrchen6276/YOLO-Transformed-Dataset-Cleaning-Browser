from __future__ import annotations

import csv
import io
import json
import os
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("CIVL7009_PICKER_RUN_MODE", "test")

from PIL import Image
from PySide6.QtWidgets import QApplication

from civl7009_picker_v3_0_3.app import MainWindow, ThumbnailWorker
from civl7009_picker_v3_0_3.assets import AssetService
from civl7009_picker_v3_0_3.manual_objects import ManualObjectsIndexService, ManualObjectsService, sha256_file
from civl7009_picker_v3_0_3.paths import ASSET_DIR


def app() -> QApplication:
    existing = QApplication.instance()
    if existing is not None:
        return existing
    return QApplication(["test"])


def wait_until(condition, timeout_ms: int = 5000) -> None:
    deadline = time.perf_counter() + timeout_ms / 1000
    while time.perf_counter() < deadline:
        app().processEvents()
        if condition():
            return
        time.sleep(0.01)
    raise AssertionError("Timed out waiting for Qt condition.")


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
                "source_mtime": int(image.stat().st_mtime_ns),
                "width": 42,
                "height": 36,
                "image_decode_status": "STRICT_OK",
                "label_line_count": 1,
                "label_format_set": "DETECTION_BBOX",
                "label_class_set": "0",
                "metrics": {"reason_score": 0, "phash_distance": idx},
            }
        )
    manifest = {
        "schema_version": "CIVL7009_MANUAL_OBJECTS_V1",
        "group_key": f"{reason}_{group_name}",
        "reason": reason,
        "group_size": count,
        "dataset_ids": [item["dataset_id"] for item in items],
        "claim_status": "PENDING_AUDIT",
        "items": items,
    }
    (group_dir / "group_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return group_dir


def write_manual_index(root: Path, groups: list[tuple[str, str, str, int]]) -> None:
    index_dir = root / "_indexes"
    index_dir.mkdir(parents=True, exist_ok=True)
    headers = [
        "reason",
        "group_key",
        "group_folder",
        "group_size",
        "duplicate_count_bucket",
        "item_id",
        "dataset_id",
        "image_filename",
        "label_filename",
        "label_class_set",
        "copy_status",
    ]
    with (index_dir / "manual_objects_index.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        item_counter = 1
        for reason, bucket, folder, count in groups:
            for idx in range(count):
                writer.writerow(
                    {
                        "reason": reason,
                        "group_key": f"{reason}_{folder}",
                        "group_folder": folder,
                        "group_size": count,
                        "duplicate_count_bucket": bucket,
                        "item_id": f"I{item_counter:06d}",
                        "dataset_id": f"ID{idx + 1:02d}",
                        "image_filename": f"ID{idx + 1:02d}_{folder}.jpg",
                        "label_filename": f"ID{idx + 1:02d}_{folder}.txt",
                        "label_class_set": str(idx % 3),
                        "copy_status": "COPIED_AND_VERIFIED",
                    }
                )
                item_counter += 1


class V301Tests(unittest.TestCase):
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

    def test_index_service_reads_csv_without_manifest_sha_work(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "Manual_Objects"
            write_manual_index(root, [("SHA256_EXACT_IMAGE", "N02", "G000001", 2)])
            result = ManualObjectsIndexService(root).load_group_summaries()
            self.assertEqual(result.mode, "index")
            self.assertEqual(result.group_count, 1)
            self.assertEqual(result.row_count, 2)
            group = ManualObjectsIndexService(root).load_group_from_summary(result.summaries[0])
            self.assertIn("MANIFEST_MISSING", {issue.code for issue in group.issues})

    def test_index_missing_fallback_manifest_mode(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "Manual_Objects"
            make_manual_group(root, "PHASH_NEAR_STRONG", "N03", "G000002", 3)
            result = ManualObjectsIndexService(root).load_group_summaries()
            self.assertEqual(result.mode, "manifest_fallback")
            self.assertEqual(result.group_count, 1)
            self.assertIn("慢速", result.warning)

    def test_manual_objects_page_paginates_and_filters(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "Manual_Objects"
            groups = []
            for idx in range(1200):
                reason = "SHA256_EXACT_IMAGE" if idx < 700 else "COMPOSITE_NEAR_HASH"
                groups.append((reason, "N02", f"G{idx + 1:06d}", 2))
            write_manual_index(root, groups)
            window = MainWindow(run_mode="test")
            try:
                window.set_workflow(1)
                window.load_manual_root(root)
                wait_until(lambda: window.manual_group_model.rowCount() == 500)
                self.assertEqual(len(window.manual_filtered_summaries), 1200)
                window.change_manual_page(1)
                self.assertEqual(window.manual_group_model.rowCount(), 500)
                index = window.reason_filter.findData("COMPOSITE_NEAR_HASH")
                window.reason_filter.setCurrentIndex(index)
                self.assertEqual(len(window.manual_filtered_summaries), 500)
            finally:
                window.close()

    def test_manual_group_click_saves_and_advances_with_bbox_preview(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "Manual_Objects"
            group1 = make_manual_group(root, "SHA256_EXACT_IMAGE", "N02", "G000001", 2)
            group2 = make_manual_group(root, "SHA256_EXACT_IMAGE", "N02", "G000002", 2)
            write_manual_index(root, [("SHA256_EXACT_IMAGE", "N02", "G000001", 2), ("SHA256_EXACT_IMAGE", "N02", "G000002", 2)])
            window = MainWindow(run_mode="test")
            try:
                window.set_workflow(1)
                window.load_manual_root(root)
                wait_until(lambda: window.manual_group_model.rowCount() == 2)
                self.assertEqual(len(window.manual_cards), 0)
                window.open_manual_group_from_summary(window.manual_row_summary_map[0])
                wait_until(lambda: len(window.manual_cards) == 2)
                wait_until(lambda: "已完成 2/2" in window.manual_load_status.toPlainText())
                self.assertTrue(window.bbox_overlay_box.isChecked())
                window.refresh_current_manual_preview()
                wait_until(lambda: "已完成 2/2" in window.manual_load_status.toPlainText())
                window.select_manual_item("item_1")
                wait_until(lambda: (group1 / "manual_selection.json").exists())
                wait_until(lambda: window.current_manual_group is not None and window.current_manual_group.group_dir == group2)
                window.multi_keep_box.setChecked(True)
                self.assertTrue(window.manual_multi_keep)
                self.assertFalse(window.auto_next_same_bucket_box.isEnabled())
            finally:
                window.close()

    def test_manual_click_auto_next_can_be_disabled(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "Manual_Objects"
            group1 = make_manual_group(root, "SHA256_EXACT_IMAGE", "N02", "G000001", 2)
            group2 = make_manual_group(root, "SHA256_EXACT_IMAGE", "N02", "G000002", 2)
            write_manual_index(root, [("SHA256_EXACT_IMAGE", "N02", "G000001", 2), ("SHA256_EXACT_IMAGE", "N02", "G000002", 2)])
            window = MainWindow(run_mode="test")
            try:
                window.set_workflow(1)
                window.load_manual_root(root)
                wait_until(lambda: window.manual_group_model.rowCount() == 2)
                window.auto_next_same_bucket_box.setChecked(False)
                window.open_manual_group_from_summary(window.manual_row_summary_map[0])
                wait_until(lambda: len(window.manual_cards) == 2)
                window.select_manual_item("item_1")
                app().processEvents()
                self.assertFalse((group1 / "manual_selection.json").exists())
                self.assertEqual(window.current_manual_group.group_dir, group1)
                self.assertNotEqual(window.current_manual_group.group_dir, group2)
            finally:
                window.close()

    def test_yolo_bbox_overlay_changes_thumbnail_pixels(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "Manual_Objects"
            group_dir = make_manual_group(root, "SHA256_EXACT_IMAGE", "N02", "G000001", 2)
            image_path = group_dir / "ID01_case_1.jpg"
            label_path = group_dir / "ID01_case_1.txt"
            label_path.write_text("0 0.5 0.5 0.6 0.6\n", encoding="utf-8")
            payloads: dict[str, bytes] = {}
            for draw in [False, True]:
                worker = ThumbnailWorker(1, f"item_{draw}", image_path, label_path, draw_bboxes=draw, max_size=(420, 260))
                worker.signals.done.connect(lambda _gen, _item, payload, key=str(draw): payloads.setdefault(key, payload))
                worker.run()
            self.assertIn("False", payloads)
            self.assertIn("True", payloads)
            self.assertNotEqual(payloads["False"], payloads["True"])
            image = Image.open(io.BytesIO(payloads["True"])).convert("RGB")
            red_pixels = sum(1 for pixel in image.getdata() if pixel[0] > 180 and pixel[1] < 100 and pixel[2] < 80)
            self.assertGreater(red_pixels, 0)

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

    def test_real_manual_objects_index_read_only_counts_if_available(self) -> None:
        root = Path("D:/P/CIVL7009/Dataset/Source_Archive/Manual_Objects")
        if not (root / "_indexes" / "manual_objects_index.csv").exists():
            self.skipTest("real Manual_Objects index not available")
        result = ManualObjectsIndexService(root).load_group_summaries()
        self.assertEqual(result.mode, "index")
        self.assertEqual(result.group_count, 43563)
        self.assertEqual(result.row_count, 135349)
        self.assertLess(result.duration_ms, 3000)

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
