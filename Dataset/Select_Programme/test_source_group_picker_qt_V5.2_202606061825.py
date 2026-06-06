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

from civl7009_picker_v5_2.app import MainWindow, ManualObjectCard, ThumbnailWorker
from civl7009_picker_v5_2.assets import AssetService
from civl7009_picker_v5_2.conflict_resolution import ConflictAwarenessService
from civl7009_picker_v5_2.manual_objects import ManualObjectsClassService, ManualObjectsIndexService, ManualObjectsService, UNREVIEWED_STATUS, sha256_file
from civl7009_picker_v5_2.paths import ASSET_DIR
from civl7009_picker_v5_2.tier_governance import TierPrefixGovernanceService, canonical_stem_for_tier, normalise_tier


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


def make_tier_dataset(root: Path) -> Path:
    image_dir_1 = root / "ID01" / "images" / "train"
    label_dir_1 = root / "ID01" / "labels" / "train"
    image_dir_2 = root / "ID09" / "images" / "train"
    label_dir_2 = root / "ID09" / "labels" / "train"
    write_image(image_dir_1 / "ID01_shared_scene.jpg")
    write_label(label_dir_1 / "ID01_shared_scene.txt")
    write_image(image_dir_2 / "ID09_shared_scene.jpg")
    write_label(label_dir_2 / "ID09_shared_scene.txt")
    write_image(image_dir_1 / "Tier02_ID01_marked_scene.jpg")
    write_label(label_dir_1 / "Tier02_ID01_marked_scene.txt")
    return root


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


def write_conflict_index(root: Path, rows: list[dict[str, str]]) -> None:
    index_dir = root / "_indexes"
    index_dir.mkdir(parents=True, exist_ok=True)
    headers = [
        "reason",
        "group_key",
        "group_folder",
        "duplicate_count_bucket",
        "group_size",
        "item_id",
        "dataset_id",
        "image_filename",
        "label_filename",
        "label_class_set",
        "source_image_project_path",
        "source_label_project_path",
        "image_sha256",
        "label_sha256",
        "target_group_project_path",
        "target_image_project_path",
        "target_label_project_path",
        "width",
        "height",
        "label_line_count",
        "metrics_json",
        "copy_status",
    ]
    with (index_dir / "manual_objects_index.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            payload = {key: row.get(key, "") for key in headers}
            writer.writerow(payload)


def write_selection(group_dir: Path, group_key: str, status: str, keep: list[str], remove: list[str]) -> None:
    group_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "CIVL7009_MANUAL_OBJECTS_SELECTION_V1",
        "group_key": group_key,
        "review_status": status,
        "selected_keep_item_ids": keep,
        "selected_remove_item_ids": remove,
        "reviewer": "test",
        "reviewed_at": "2026-06-06T00:00:00",
        "software_version": "test",
        "notes": "",
    }
    (group_dir / "manual_selection.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def conflict_rows_from_manifest(group_dir: Path) -> list[dict[str, str]]:
    manifest = json.loads((group_dir / "group_manifest.json").read_text(encoding="utf-8"))
    rows: list[dict[str, str]] = []
    for raw in manifest["items"]:
        rows.append(
            {
                "reason": manifest["reason"],
                "duplicate_count_bucket": group_dir.parent.name,
                "group_folder": group_dir.name,
                "group_key": manifest["group_key"],
                "group_size": str(manifest["group_size"]),
                "item_id": str(raw["item_id"]),
                "dataset_id": str(raw["dataset_id"]),
                "image_filename": str(raw["image_filename"]),
                "label_filename": str(raw["label_filename"]),
                "label_class_set": "0",
                "source_image_project_path": str(raw["source_image_project_path"]),
                "source_label_project_path": str(raw["source_label_project_path"]),
                "image_sha256": str(raw["image_sha256"]),
                "label_sha256": str(raw["label_sha256"]),
                "target_group_project_path": str(group_dir),
                "target_image_project_path": str(group_dir / raw["image_filename"]),
                "target_label_project_path": str(group_dir / raw["label_filename"]),
                "width": str(raw.get("width", 0)),
                "height": str(raw.get("height", 0)),
                "label_line_count": str(raw.get("label_line_count", 0)),
                "metrics_json": json.dumps(raw.get("metrics", {}) or {}),
                "copy_status": "COPIED_AND_VERIFIED",
            }
        )
    return rows


def make_two_reason_source_conflict(root: Path) -> tuple[Path, Path, str]:
    group1 = make_manual_group(root, "SHA256_EXACT_IMAGE", "N02", "G000001", 2)
    group2 = make_manual_group(root, "PHASH_NEAR_STRONG", "N02", "G000002", 2)
    rows1 = conflict_rows_from_manifest(group1)
    rows2 = conflict_rows_from_manifest(group2)
    shared_source = rows1[0]["source_image_project_path"]
    rows2[0]["source_image_project_path"] = rows1[0]["source_image_project_path"]
    rows2[0]["source_label_project_path"] = rows1[0]["source_label_project_path"]
    rows2[0]["image_sha256"] = rows1[0]["image_sha256"]
    rows2[0]["label_sha256"] = rows1[0]["label_sha256"]
    write_conflict_index(root, rows1 + rows2)
    service = ManualObjectsService(root)
    service.save_selection(service.load_group(group1), "APPROVED", ["item_1"], ["item_2"])
    service.save_selection(service.load_group(group2), "APPROVED", ["item_2"], ["item_1"])
    return group1, group2, shared_source


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
            self.assertEqual(len(window.workflow_buttons), 6)
            self.assertIn("Source Group", window.workflow_buttons[0].text())
            self.assertIn("Manual Objects", window.workflow_buttons[1].text())
            self.assertIn("Conflict", window.workflow_buttons[2].text())
            self.assertIn("Tier", window.workflow_buttons[3].text())
            self.assertIn("Review History", window.workflow_buttons[4].text())
            window.set_workflow(1)
            self.assertEqual(window.stack.currentIndex(), 1)
        finally:
            window.close()

    def test_tier_prefix_canonical_stem_and_normalisation(self) -> None:
        self.assertEqual(normalise_tier("1"), "Tier01")
        self.assertEqual(normalise_tier("Tier09"), "Tier09")
        canonical, dataset_id, tier, marked = canonical_stem_for_tier("Tier02_ID09_shared_scene")
        self.assertEqual(canonical, "shared_scene")
        self.assertEqual(dataset_id, "ID09")
        self.assertEqual(tier, "Tier02")
        self.assertTrue(marked)
        canonical, dataset_id, tier, marked = canonical_stem_for_tier("ID01_shared_scene")
        self.assertEqual(canonical, "shared_scene")
        self.assertEqual(dataset_id, "ID01")
        self.assertEqual(tier, "")
        self.assertFalse(marked)

    def test_tier_prefix_scan_plan_and_apply(self) -> None:
        with TemporaryDirectory() as tmp:
            root = make_tier_dataset(Path(tmp) / "Source_Archive")
            service = TierPrefixGovernanceService(root)
            result = service.scan()
            group = next(item for item in result.groups if item.canonical_stem == "shared_scene")
            self.assertEqual(group.image_count, 2)
            self.assertEqual(group.label_count, 2)
            self.assertEqual(group.status, "UNMARKED")
            marked_group = next(item for item in result.groups if item.canonical_stem == "marked_scene")
            self.assertEqual(marked_group.status, "MARKED")
            plan = service.build_plan("Tier03")
            self.assertEqual(len(plan.blocked_reasons), 0)
            self.assertEqual(len(plan.operations), 4)
            journal = service.apply_plan(plan)
            self.assertTrue(journal.exists())
            self.assertTrue((root / "ID01" / "images" / "train" / "Tier03_ID01_shared_scene.jpg").exists())
            self.assertTrue((root / "ID09" / "labels" / "train" / "Tier03_ID09_shared_scene.txt").exists())
            after = service.scan()
            self.assertEqual(after.unmarked_count, 0)

    def test_tier_prefix_page_scans_and_builds_plan(self) -> None:
        with TemporaryDirectory() as tmp:
            root = make_tier_dataset(Path(tmp) / "Source_Archive")
            window = MainWindow(run_mode="test")
            try:
                window.set_workflow(3)
                window.tier_root = root
                window.scan_tier_root()
                wait_until(lambda: window.tier_scan_result is not None)
                self.assertGreaterEqual(window.tier_group_model.rowCount(), 2)
                window.tier_input.setText("Tier04")
                window.build_tier_plan()
                self.assertEqual(window.tier_plan.tier, "Tier04")
                self.assertGreater(window.tier_plan_model.rowCount(), 0)
                self.assertTrue(window.apply_tier_btn.isEnabled())
            finally:
                window.close()

    def test_conflict_awareness_classifies_keep_remove_and_writes_resolution(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "Manual_Objects"
            shared_source = "Dataset/Source_Archive/ID01/images/demo/shared.jpg"
            shared_sha = "a" * 64
            rows = [
                {
                    "reason": "SHA256_EXACT_IMAGE",
                    "duplicate_count_bucket": "N02",
                    "group_folder": "G000001",
                    "group_key": "SHA256_EXACT_IMAGE_G000001",
                    "group_size": "2",
                    "item_id": "item_shared_a",
                    "dataset_id": "ID01",
                    "image_filename": "ID01_a.jpg",
                    "label_filename": "ID01_a.txt",
                    "source_image_project_path": shared_source,
                    "source_label_project_path": "Dataset/Source_Archive/ID01/labels/demo/shared.txt",
                    "image_sha256": shared_sha,
                    "label_sha256": "b" * 64,
                    "target_group_project_path": "Dataset/Source_Archive/Manual_Objects/SHA256_EXACT_IMAGE/N02/G000001",
                    "target_image_project_path": "Dataset/Source_Archive/Manual_Objects/SHA256_EXACT_IMAGE/N02/G000001/ID01_a.jpg",
                    "target_label_project_path": "Dataset/Source_Archive/Manual_Objects/SHA256_EXACT_IMAGE/N02/G000001/ID01_a.txt",
                },
                {
                    "reason": "SHA256_EXACT_IMAGE",
                    "duplicate_count_bucket": "N02",
                    "group_folder": "G000001",
                    "group_key": "SHA256_EXACT_IMAGE_G000001",
                    "group_size": "2",
                    "item_id": "item_peer_a",
                    "dataset_id": "ID02",
                    "image_filename": "ID02_a.jpg",
                    "label_filename": "ID02_a.txt",
                    "source_image_project_path": "Dataset/Source_Archive/ID02/images/demo/peer.jpg",
                    "image_sha256": "c" * 64,
                    "target_group_project_path": "Dataset/Source_Archive/Manual_Objects/SHA256_EXACT_IMAGE/N02/G000001",
                    "target_image_project_path": "Dataset/Source_Archive/Manual_Objects/SHA256_EXACT_IMAGE/N02/G000001/ID02_a.jpg",
                    "target_label_project_path": "Dataset/Source_Archive/Manual_Objects/SHA256_EXACT_IMAGE/N02/G000001/ID02_a.txt",
                },
                {
                    "reason": "PHASH_NEAR_STRONG",
                    "duplicate_count_bucket": "N02",
                    "group_folder": "G000002",
                    "group_key": "PHASH_NEAR_STRONG_G000002",
                    "group_size": "2",
                    "item_id": "item_shared_b",
                    "dataset_id": "ID01",
                    "image_filename": "ID01_b.jpg",
                    "label_filename": "ID01_b.txt",
                    "source_image_project_path": shared_source,
                    "source_label_project_path": "Dataset/Source_Archive/ID01/labels/demo/shared.txt",
                    "image_sha256": shared_sha,
                    "label_sha256": "b" * 64,
                    "target_group_project_path": "Dataset/Source_Archive/Manual_Objects/PHASH_NEAR_STRONG/N02/G000002",
                    "target_image_project_path": "Dataset/Source_Archive/Manual_Objects/PHASH_NEAR_STRONG/N02/G000002/ID01_b.jpg",
                    "target_label_project_path": "Dataset/Source_Archive/Manual_Objects/PHASH_NEAR_STRONG/N02/G000002/ID01_b.txt",
                },
                {
                    "reason": "PHASH_NEAR_STRONG",
                    "duplicate_count_bucket": "N02",
                    "group_folder": "G000002",
                    "group_key": "PHASH_NEAR_STRONG_G000002",
                    "group_size": "2",
                    "item_id": "item_peer_b",
                    "dataset_id": "ID03",
                    "image_filename": "ID03_b.jpg",
                    "label_filename": "ID03_b.txt",
                    "source_image_project_path": "Dataset/Source_Archive/ID03/images/demo/peer.jpg",
                    "image_sha256": "d" * 64,
                    "target_group_project_path": "Dataset/Source_Archive/Manual_Objects/PHASH_NEAR_STRONG/N02/G000002",
                    "target_image_project_path": "Dataset/Source_Archive/Manual_Objects/PHASH_NEAR_STRONG/N02/G000002/ID03_b.jpg",
                    "target_label_project_path": "Dataset/Source_Archive/Manual_Objects/PHASH_NEAR_STRONG/N02/G000002/ID03_b.txt",
                },
            ]
            write_conflict_index(root, rows)
            write_selection(root / "SHA256_EXACT_IMAGE" / "N02" / "G000001", "SHA256_EXACT_IMAGE_G000001", "APPROVED", ["item_shared_a"], ["item_peer_a"])
            write_selection(root / "PHASH_NEAR_STRONG" / "N02" / "G000002", "PHASH_NEAR_STRONG_G000002", "APPROVED", ["item_peer_b"], ["item_shared_b"])
            service = ConflictAwarenessService(root)
            index = service.build_index()
            conflicts = [obj for obj in index.objects if obj.source_image_project_path == shared_source]
            self.assertEqual(len(conflicts), 1)
            self.assertEqual(conflicts[0].conflict_state, "CONFLICT_KEEP_REMOVE")
            result = service.write_resolution(conflicts[0], "DEFER_REVIEW", reviewer="tester", decision_rationale="unit test")
            self.assertTrue(result.verified)
            self.assertTrue(result.path.exists())
            self.assertTrue(result.index_path.exists())

    def test_refresh_source_object_rereads_only_related_selection_state(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "Manual_Objects"
            _group1, group2, shared_source = make_two_reason_source_conflict(root)
            service = ConflictAwarenessService(root)
            index = service.build_index()
            conflict = next(obj for obj in index.objects if obj.source_image_project_path == shared_source)
            self.assertEqual(conflict.conflict_state, "CONFLICT_KEEP_REMOVE")
            ManualObjectsService(root).save_selection(ManualObjectsService(root).load_group(group2), "APPROVED", ["item_1"], ["item_2"])
            refreshed = service.refresh_source_object(conflict.source_object_key)
            self.assertIsNotNone(refreshed)
            self.assertEqual(refreshed.conflict_state, "CONSISTENT_KEEP")
            self.assertEqual(service.latest_index.source_map[conflict.source_object_key].conflict_state, "CONSISTENT_KEEP")

    def test_ui_refresh_current_conflict_object_button_updates_current_object(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "Manual_Objects"
            _group1, group2, shared_source = make_two_reason_source_conflict(root)
            window = MainWindow(run_mode="test")
            try:
                window.set_workflow(1)
                window.load_manual_root(root)
                wait_until(lambda: window.conflict_index is not None)
                conflict = next(obj for obj in window.conflict_index.objects if obj.source_image_project_path == shared_source)
                self.assertTrue(hasattr(window, "refresh_current_conflict_btn"))
                self.assertEqual(conflict.conflict_state, "CONFLICT_KEEP_REMOVE")
                window.current_conflict_object = conflict
                window.render_conflict_object(conflict)
                ManualObjectsService(root).save_selection(ManualObjectsService(root).load_group(group2), "APPROVED", ["item_1"], ["item_2"])
                window.refresh_current_conflict_object()
                self.assertEqual(window.current_conflict_object.conflict_state, "CONSISTENT_KEEP")
                self.assertIn("CONSISTENT_KEEP", window.conflict_status_label.text())
            finally:
                window.close()

    def test_manual_cards_receive_conflict_chip_after_index(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "Manual_Objects"
            group_dir = make_manual_group(root, "SHA256_EXACT_IMAGE", "N02", "G000001", 2)
            write_manual_index(root, [("SHA256_EXACT_IMAGE", "N02", "G000001", 2)])
            group = ManualObjectsService(root).load_group(group_dir)
            ManualObjectsService(root).save_selection(group, "APPROVED", ["item_1"], ["item_2"])
            window = MainWindow(run_mode="test")
            try:
                window.set_workflow(1)
                window.load_manual_root(root)
                wait_until(lambda: window.manual_group_model.rowCount() == 1)
                wait_until(lambda: window.conflict_index is not None)
                window.open_manual_group_from_summary(window.manual_row_summary_map[0])
                wait_until(lambda: len(window.manual_cards) == 2)
                self.assertTrue(window.manual_cards[0].conflict_chip.text())
                window.set_workflow(2)
                self.assertGreaterEqual(window.conflict_queue_model.rowCount(), 1)
            finally:
                window.close()

    def test_conflict_event_click_jumps_back_to_manual_group_and_item(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "Manual_Objects"
            group1 = make_manual_group(root, "SHA256_EXACT_IMAGE", "N02", "G000001", 2)
            group2 = make_manual_group(root, "PHASH_NEAR_STRONG", "N02", "G000002", 2)
            write_manual_index(root, [("SHA256_EXACT_IMAGE", "N02", "G000001", 2), ("PHASH_NEAR_STRONG", "N02", "G000002", 2)])
            service = ManualObjectsService(root)
            service.save_selection(service.load_group(group1), "APPROVED", ["item_1"], ["item_2"])
            service.save_selection(service.load_group(group2), "APPROVED", ["item_2"], ["item_1"])
            window = MainWindow(run_mode="test")
            try:
                window.set_workflow(1)
                window.load_manual_root(root)
                wait_until(lambda: window.conflict_index is not None)
                window.set_workflow(2)
                self.assertGreaterEqual(window.conflict_queue_model.rowCount(), 1)
                window.open_conflict_object_from_table(window.conflict_queue_model.index(0, 0))
                wait_until(lambda: window.current_conflict_object is not None)
                window.open_conflict_event_from_table(window.conflict_event_model.index(0, 0))
                wait_until(lambda: window.stack.currentIndex() == 1 and window.current_manual_group is not None)
                self.assertIn(window.current_manual_group.group_dir, {group1, group2})
                self.assertGreaterEqual(window.manual_preview_index, 0)
            finally:
                window.close()

    def test_ad_shortcuts_step_manual_groups_and_conflict_objects(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "Manual_Objects"
            group1 = make_manual_group(root, "SHA256_EXACT_IMAGE", "N02", "G000001", 2)
            group2 = make_manual_group(root, "SHA256_EXACT_IMAGE", "N02", "G000002", 2)
            write_conflict_index(root, conflict_rows_from_manifest(group1) + conflict_rows_from_manifest(group2))
            service = ManualObjectsService(root)
            service.save_selection(service.load_group(group1), "ALL_DONE", [], [])
            service.save_selection(service.load_group(group2), "ALL_OUT", [], [])
            window = MainWindow(run_mode="test")
            try:
                window.set_workflow(1)
                window.load_manual_root(root)
                wait_until(lambda: window.manual_group_model.rowCount() == 2)
                window.open_manual_group_from_summary(window.manual_row_summary_map[0])
                wait_until(lambda: window.current_manual_group is not None)
                first_key = window.current_manual_group.group_key
                window.step_workflow_record(1)
                wait_until(lambda: window.current_manual_group is not None and window.current_manual_group.group_key != first_key)
                self.assertEqual(window.current_manual_group.group_key, window.manual_filtered_summaries[1].group_key)
                wait_until(lambda: window.conflict_index is not None)
                window.set_workflow(2)
                self.assertGreaterEqual(window.conflict_queue_model.rowCount(), 2)
                window.open_conflict_object_from_table(window.conflict_queue_model.index(0, 0))
                first_object = window.current_conflict_object.source_object_key
                window.step_workflow_record(1)
                self.assertNotEqual(window.current_conflict_object.source_object_key, first_object)
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
            self.assertTrue(result.warning)

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

    def test_unreviewed_filter_refreshes_selection_state_before_filtering(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "Manual_Objects"
            group_dirs = []
            groups = []
            for idx in range(8):
                folder = f"G{idx + 1:06d}"
                group_dirs.append(make_manual_group(root, "SHA256_EXACT_IMAGE", "N02", folder, 2))
                groups.append(("SHA256_EXACT_IMAGE", "N02", folder, 2))
            write_manual_index(root, groups)
            service = ManualObjectsService(root)
            for folder, status in [("G000001", "APPROVED"), ("G000003", "SKIP"), ("G000005", "NEEDS_AGENT_CHECK")]:
                group = service.load_group(root / "SHA256_EXACT_IMAGE" / "N02" / folder)
                service.save_selection(group, status, ["item_1"], ["item_2"])
            window = MainWindow(run_mode="test")
            try:
                window.set_workflow(1)
                window.load_manual_root(root)
                wait_until(lambda: window.manual_group_model.rowCount() == 8)
                window.status_filter.setCurrentIndex(window.status_filter.findData(UNREVIEWED_STATUS))
                app().processEvents()
                self.assertEqual({summary.selection_status for summary in window.manual_filtered_summaries}, {UNREVIEWED_STATUS})
                self.assertEqual(len(window.manual_filtered_summaries), 5)
                window.dataset_filter.setText("ID02")
                app().processEvents()
                self.assertEqual({summary.selection_status for summary in window.manual_filtered_summaries}, {UNREVIEWED_STATUS})
                window.selection_filter.setCurrentIndex(window.selection_filter.findData("missing"))
                app().processEvents()
                self.assertEqual({summary.selection_status for summary in window.manual_filtered_summaries}, {UNREVIEWED_STATUS})
                window.refresh_manual_status_dashboard()
                self.assertTrue(window.global_status.text())
            finally:
                window.close()

    def test_manual_ad_shortcuts_move_preview_without_saving_status(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "Manual_Objects"
            group_dir = make_manual_group(root, "SHA256_EXACT_IMAGE", "N03", "G000001", 3)
            write_manual_index(root, [("SHA256_EXACT_IMAGE", "N03", "G000001", 3)])
            window = MainWindow(run_mode="test")
            try:
                window.set_workflow(1)
                window.load_manual_root(root)
                wait_until(lambda: window.manual_group_model.rowCount() == 1)
                window.open_manual_group_from_summary(window.manual_row_summary_map[0])
                wait_until(lambda: len(window.manual_cards) == 3)
                self.assertEqual(window.manual_preview_index, 0)
                window.step_manual_preview_item(1)
                self.assertEqual(window.manual_preview_index, 1)
                window.step_manual_preview_item(-1)
                self.assertEqual(window.manual_preview_index, 0)
                self.assertFalse((group_dir / "manual_selection.json").exists())
                self.assertEqual([item.selection_state for item in window.current_manual_group.items], ["UNDECIDED", "UNDECIDED", "UNDECIDED"])
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
                wait_until(lambda: window.manual_thumbnail_expected == 2 and window.manual_thumbnail_done == 2)
                self.assertTrue(window.bbox_overlay_box.isChecked())
                window.refresh_current_manual_preview()
                wait_until(lambda: window.manual_thumbnail_expected == 2 and window.manual_thumbnail_done == 2)
                window.select_manual_item("item_1")
                wait_until(lambda: (group1 / "manual_selection.json").exists())
                wait_until(lambda: window.current_manual_group is not None and window.current_manual_group.group_dir == group2)
                window.multi_keep_box.setChecked(True)
                self.assertTrue(window.manual_multi_keep)
                self.assertFalse(window.auto_next_same_bucket_box.isEnabled())
            finally:
                window.close()

    def test_save_keeps_current_filtered_row_until_manual_refilter_or_refresh(self) -> None:
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
                window.status_filter.setCurrentIndex(window.status_filter.findData(UNREVIEWED_STATUS))
                window.auto_next_same_bucket_box.setChecked(False)
                window.open_manual_group_from_summary(window.manual_row_summary_map[0])
                wait_until(lambda: len(window.manual_cards) == 2)
                window.select_manual_item("item_1")
                window.save_manual_selection("APPROVED")
                self.assertTrue((group1 / "manual_selection.json").exists())
                self.assertEqual(window.manual_group_model.rowCount(), 2)
                visible_statuses = [window.manual_group_model.rows[row][3] for row in range(window.manual_group_model.rowCount())]
                self.assertIn("APPROVED", visible_statuses)
                window.apply_manual_filters()
                self.assertEqual(window.manual_group_model.rowCount(), 1)
                self.assertEqual(window.manual_filtered_summaries[0].group_dir, group2)
            finally:
                window.close()

    def test_same_group_folder_under_different_reasons_writes_correct_path(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "Manual_Objects"
            phash_group = make_manual_group(root, "PHASH_NEAR_STRONG", "N03", "G006229", 3)
            rotation_group = make_manual_group(root, "ROTATION_AWARE_PHASH", "N03", "G006229", 3)
            write_manual_index(root, [("PHASH_NEAR_STRONG", "N03", "G006229", 3), ("ROTATION_AWARE_PHASH", "N03", "G006229", 3)])
            window = MainWindow(run_mode="test")
            try:
                window.set_workflow(1)
                window.load_manual_root(root)
                wait_until(lambda: window.manual_group_model.rowCount() == 2)
                window.reason_filter.setCurrentIndex(window.reason_filter.findData("PHASH_NEAR_STRONG"))
                app().processEvents()
                self.assertEqual(window.manual_group_model.rowCount(), 1)
                window.auto_next_same_bucket_box.setChecked(False)
                window.open_manual_group_from_summary(window.manual_row_summary_map[0])
                wait_until(lambda: len(window.manual_cards) == 3)
                window.select_manual_item("item_1")
                window.save_manual_selection("APPROVED")
                phash_selection = phash_group / "manual_selection.json"
                rotation_selection = rotation_group / "manual_selection.json"
                self.assertTrue(phash_selection.exists())
                self.assertFalse(rotation_selection.exists())
                payload = json.loads(phash_selection.read_text(encoding="utf-8"))
                self.assertEqual(payload["group_key"], "PHASH_NEAR_STRONG_G006229")
                self.assertEqual(payload["review_status"], "APPROVED")
                self.assertIn("PHASH_NEAR_STRONG/N03/G006229", window.global_status.text())
            finally:
                window.close()

    def test_all_out_status_writes_empty_keep_and_all_remove(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "Manual_Objects"
            group_dir = make_manual_group(root, "PHASH_NEAR_STRONG", "N03", "G000777", 3)
            group = ManualObjectsService(root).load_group(group_dir)
            path = ManualObjectsService(root).save_selection(group, "ALL_OUT", ["item_1"], [])
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["review_status"], "ALL_OUT")
            self.assertEqual(payload["selected_keep_item_ids"], [])
            self.assertEqual(payload["selected_remove_item_ids"], ["item_1", "item_2", "item_3"])

    def test_all_done_status_writes_all_keep_and_empty_remove(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "Manual_Objects"
            group_dir = make_manual_group(root, "PHASH_NEAR_STRONG", "N03", "G000778", 3)
            group = ManualObjectsService(root).load_group(group_dir)
            path = ManualObjectsService(root).save_selection(group, "ALL_DONE", [], ["item_1"])
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["review_status"], "ALL_DONE")
            self.assertEqual(payload["selected_keep_item_ids"], ["item_1", "item_2", "item_3"])
            self.assertEqual(payload["selected_remove_item_ids"], [])

    def test_all_done_button_saves_all_keep(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "Manual_Objects"
            group_dir = make_manual_group(root, "SHA256_EXACT_IMAGE", "N02", "G000779", 2)
            write_manual_index(root, [("SHA256_EXACT_IMAGE", "N02", "G000779", 2)])
            window = MainWindow(run_mode="test")
            try:
                window.set_workflow(1)
                window.load_manual_root(root)
                wait_until(lambda: window.manual_group_model.rowCount() == 1)
                window.open_manual_group_from_summary(window.manual_row_summary_map[0])
                wait_until(lambda: len(window.manual_cards) == 2)
                self.assertTrue(hasattr(window, "save_all_done_btn"))
                window.save_manual_selection("ALL_DONE")
                payload = json.loads((group_dir / "manual_selection.json").read_text(encoding="utf-8"))
                self.assertEqual(payload["review_status"], "ALL_DONE")
                self.assertEqual(payload["selected_keep_item_ids"], ["item_1", "item_2"])
                self.assertEqual(payload["selected_remove_item_ids"], [])
            finally:
                window.close()

    def test_manual_history_records_open_group_for_reselection(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "Manual_Objects"
            group1 = make_manual_group(root, "SHA256_EXACT_IMAGE", "N02", "G000001", 2)
            write_manual_index(root, [("SHA256_EXACT_IMAGE", "N02", "G000001", 2)])
            window = MainWindow(run_mode="test")
            try:
                window.manual_history_path = Path(tmp) / "history" / "manual_history.jsonl"
                window.set_workflow(1)
                window.load_manual_root(root)
                wait_until(lambda: window.manual_group_model.rowCount() == 1)
                window.open_manual_group_from_summary(window.manual_row_summary_map[0])
                wait_until(lambda: len(window.manual_cards) == 2)
                window.select_manual_item("item_1")
                window.save_manual_selection("APPROVED")
                self.assertTrue(window.manual_history_path.exists())
                window.load_manual_history()
                self.assertGreaterEqual(window.history_model.rowCount(), 1)
                window.set_workflow(3)
                window.open_history_record_from_table(window.history_model.index(0, 0))
                wait_until(lambda: window.current_manual_group is not None and window.current_manual_group.group_dir == group1)
                self.assertEqual(window.stack.currentIndex(), 1)
                self.assertEqual([item.selection_state for item in window.current_manual_group.items], ["KEEP", "REMOVE"])
                window.multi_keep_box.setChecked(True)
                window.select_manual_item("item_2")
                window.select_manual_item("item_2")
                window.save_manual_selection("APPROVED")
                selection = json.loads((group1 / "manual_selection.json").read_text(encoding="utf-8"))
                self.assertIn("item_2", selection["selected_keep_item_ids"])
            finally:
                window.close()

    def test_manual_undo_last_review_removes_new_selection(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "Manual_Objects"
            group1 = make_manual_group(root, "SHA256_EXACT_IMAGE", "N02", "G000001", 2)
            write_manual_index(root, [("SHA256_EXACT_IMAGE", "N02", "G000001", 2)])
            window = MainWindow(run_mode="test")
            try:
                window.set_workflow(1)
                window.load_manual_root(root)
                wait_until(lambda: window.manual_group_model.rowCount() == 1)
                window.open_manual_group_from_summary(window.manual_row_summary_map[0])
                wait_until(lambda: len(window.manual_cards) == 2)
                window.auto_next_same_bucket_box.setChecked(False)
                window.select_manual_item("item_1")
                window.save_manual_selection("APPROVED")
                self.assertTrue((group1 / "manual_selection.json").exists())
                self.assertTrue(window.undo_manual_btn.isEnabled())
                window.undo_last_manual_review_operation()
                self.assertFalse((group1 / "manual_selection.json").exists())
                self.assertFalse(window.undo_manual_btn.isEnabled())
                self.assertEqual(window.current_manual_summary.selection_status, UNREVIEWED_STATUS)
            finally:
                window.close()

    def test_manual_undo_last_review_restores_previous_selection(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "Manual_Objects"
            group1 = make_manual_group(root, "SHA256_EXACT_IMAGE", "N02", "G000001", 2)
            write_manual_index(root, [("SHA256_EXACT_IMAGE", "N02", "G000001", 2)])
            service = ManualObjectsService(root)
            service.save_selection(service.load_group(group1), "APPROVED", ["item_1"], ["item_2"])
            window = MainWindow(run_mode="test")
            try:
                window.set_workflow(1)
                window.load_manual_root(root)
                wait_until(lambda: window.manual_group_model.rowCount() == 1)
                window.open_manual_group_from_summary(window.manual_row_summary_map[0])
                wait_until(lambda: len(window.manual_cards) == 2)
                window.multi_keep_box.setChecked(True)
                window.select_manual_item("item_2")
                window.select_manual_item("item_2")
                window.save_manual_selection("APPROVED")
                changed = json.loads((group1 / "manual_selection.json").read_text(encoding="utf-8"))
                self.assertIn("item_2", changed["selected_keep_item_ids"])
                window.undo_last_manual_review_operation()
                restored = json.loads((group1 / "manual_selection.json").read_text(encoding="utf-8"))
                self.assertEqual(restored["selected_keep_item_ids"], ["item_1"])
                self.assertEqual(restored["selected_remove_item_ids"], ["item_2"])
                self.assertEqual(window.current_manual_summary.selection_status, "APPROVED")
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
                worker = ThumbnailWorker(1, f"item_{draw}", image_path, label_path, draw_bboxes=draw, class_map={"0": "person"}, max_size=(420, 260))
                worker.signals.done.connect(lambda _gen, _item, payload, key=str(draw): payloads.setdefault(key, payload))
                worker.run()
            self.assertIn("False", payloads)
            self.assertIn("True", payloads)
            self.assertNotEqual(payloads["False"], payloads["True"])
            image = Image.open(io.BytesIO(payloads["True"])).convert("RGB")
            red_pixels = sum(1 for pixel in image.getdata() if pixel[0] > 180 and pixel[1] < 100 and pixel[2] < 80)
            self.assertGreater(red_pixels, 0)

    def test_id_classes_dirs_and_any_txt_filename_detection(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "Manual_Objects"
            service = ManualObjectsClassService(root)
            statuses = service.ensure_id_class_dirs(["ID01", "ID09"])
            self.assertTrue((root / "ID_Classes" / "ID01").is_dir())
            self.assertTrue((root / "ID_Classes" / "ID09").is_dir())
            self.assertEqual({status.status for status in statuses}, {"MISSING"})
            (root / "ID_Classes" / "ID01" / "whatever_name_is_ok.txt").write_text("person\nknife\n", encoding="utf-8")
            (root / "ID_Classes" / "ID09" / "custom_categories.txt").write_text("background\nvehicle\n", encoding="utf-8")
            statuses = service.ensure_id_class_dirs(["ID01", "ID09"])
            self.assertEqual({status.status for status in statuses}, {"OK"})
            maps = service.load_class_maps()
            self.assertEqual(maps["ID01"]["0"], "person")
            self.assertEqual(maps["ID01"]["1"], "knife")
            self.assertEqual(maps["ID09"]["1"], "vehicle")

    def test_window_load_manual_root_reports_missing_id_classes(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "Manual_Objects"
            write_manual_index(root, [("SHA256_EXACT_IMAGE", "N02", "G000001", 2)])
            window = MainWindow(run_mode="test")
            try:
                window.set_workflow(1)
                window.load_manual_root(root)
                wait_until(lambda: window.manual_group_model.rowCount() == 1)
                self.assertTrue((root / "ID_Classes" / "ID01").is_dir())
                self.assertTrue((root / "ID_Classes" / "ID02").is_dir())
                self.assertEqual({status.status for status in window.manual_class_statuses}, {"MISSING"})
                (root / "ID_Classes" / "ID01" / "labels_id01.txt").write_text("person\n", encoding="utf-8")
                (root / "ID_Classes" / "ID02" / "not_classes_name.txt").write_text("person\n", encoding="utf-8")
                window.refresh_manual_class_statuses()
                self.assertEqual({status.status for status in window.manual_class_statuses}, {"OK"})
            finally:
                window.close()

    def test_manual_object_card_preview_scales_to_available_space_and_shows_class_names(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "Manual_Objects"
            group_dir = make_manual_group(root, "SHA256_EXACT_IMAGE", "N02", "G000001", 2)
            group = ManualObjectsService(root).load_group(group_dir)
            item = group.items[0]
            payload = item.image_path.read_bytes()
            card = ManualObjectCard(item, 0, {"0": "person"})
            try:
                card.preview.resize(620, 620)
                card.set_thumbnail_bytes(payload)
                app().processEvents()
                pixmap = card.preview.pixmap()
                self.assertIsNotNone(pixmap)
                self.assertGreater(pixmap.width(), 430)
                self.assertIn("person (0)", card.class_names_label.text())
            finally:
                card.deleteLater()

    def test_n20_plus_group_renders_all_items_with_batched_thumbnails(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "Manual_Objects"
            make_manual_group(root, "PHASH_NEAR_STRONG", "N20_PLUS", "G000999", 35)
            write_manual_index(root, [("PHASH_NEAR_STRONG", "N20_PLUS", "G000999", 35)])
            window = MainWindow(run_mode="test")
            try:
                window.set_workflow(1)
                window.load_manual_root(root)
                wait_until(lambda: window.manual_group_model.rowCount() == 1)
                window.open_manual_group_from_summary(window.manual_row_summary_map[0])
                wait_until(lambda: len(window.manual_cards) == 35)
                self.assertEqual(window.manual_thumbnail_expected, 35)
                self.assertIn("item_35", window.manual_cards_by_item)
                wait_until(lambda: window.manual_thumbnail_done == 35, timeout_ms=12000)
                self.assertEqual(window.manual_thumbnail_failed, {})
            finally:
                window.close()

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
