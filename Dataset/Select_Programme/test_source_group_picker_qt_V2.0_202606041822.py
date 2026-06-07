from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("CIVL7009_PICKER_RUN_MODE", "test")

import civl7009_picker_v2
from civl7009_picker_v2.config import ASSET_DIR, DIAGNOSTIC_BUNDLES_DIR, RUNTIME_MANIFESTS_DIR
from civl7009_picker_v2.core_bridge.v181_facade import V181CoreFacade
from civl7009_picker_v2.domain.models import GroupRecord
from civl7009_picker_v2.gui.app import create_app
from civl7009_picker_v2.gui.main_window import MainWindow
from civl7009_picker_v2.infrastructure.path_policy import validate_for_staging, validate_inside
from civl7009_picker_v2.infrastructure.sqlite_manifest import connect_manifest, open_manifest
from civl7009_picker_v2.services.asset_service import AssetService, sha256_file
from civl7009_picker_v2.services.capability_service import CapabilityMatrixService
from civl7009_picker_v2.services.diagnostic_service import DiagnosticService
from civl7009_picker_v2.services.id_initialisation_service import IdInitialisationService
from civl7009_picker_v2.services.manifest_service import ManifestService
from civl7009_picker_v2.services.recovery_service import RecoveryService
from civl7009_picker_v2.services.staging_service import StagingService
from civl7009_picker_v2.services.transaction_service import TransactionService


class SourceGroupPickerV20Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = create_app([])

    def test_capability_matrix_defaults_and_chinese_labels(self) -> None:
        matrix = CapabilityMatrixService().get_matrix()
        by_name = {cap.name: cap for cap in matrix}
        self.assertTrue(by_name["manifest_only_queue"].enabled)
        self.assertFalse(by_name["manifest_only_queue"].raw_file_movement)
        self.assertFalse(by_name["physical_staging"].enabled)
        self.assertTrue(by_name["physical_staging"].raw_file_movement)
        self.assertIn("清单队列", by_name["manifest_only_queue"].display_name)
        self.assertIn("STAGE", by_name["physical_staging"].gate)

    def test_asset_manifest_design_tokens_and_image2_policy(self) -> None:
        asset_dir = AssetService().ensure_assets()
        manifest_path = asset_dir / "asset_manifest.json"
        prompt_log = asset_dir / "asset_prompt_log.json"
        tokens = asset_dir / "design_tokens.json"
        self.assertTrue(manifest_path.exists())
        self.assertTrue(tokens.exists())
        data = __import__("json").loads(manifest_path.read_text(encoding="utf-8"))
        self.assertFalse(data["policy"]["contains_dataset_image"])
        for asset in data["assets"]:
            self.assertFalse(asset["contains_dataset_image"])
            path = asset_dir / asset["asset_name"]
            self.assertTrue(path.exists())
            self.assertEqual(sha256_file(path), asset["sha256"])
        if (asset_dir / "splash_hero_image2.svg").exists():
            self.assertTrue(prompt_log.exists())
            log = __import__("json").loads(prompt_log.read_text(encoding="utf-8"))
            self.assertFalse(log["assets"][0]["contains_dataset_image"])

    def test_manifest_schema_integrity_and_newer_schema_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            service = ManifestService(tmp_path / "Runtime_Manifests")
            manifest = service.open_or_create("session_test", tmp_path / "images" / "ManualReview_GroupSize_2")
            report = service.check_integrity(manifest.manifest_path)
            self.assertTrue(report.ok)
            conn = connect_manifest(manifest.manifest_path)
            try:
                version = conn.execute("PRAGMA user_version").fetchone()[0]
                self.assertEqual(version, 1)
                tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                self.assertIn("manifest_metadata", tables)
                self.assertIn("migrations", tables)
            finally:
                conn.close()
            newer = tmp_path / "newer.sqlite"
            conn = sqlite3.connect(newer)
            conn.execute("PRAGMA user_version = 999")
            conn.commit()
            conn.close()
            newer_result = open_manifest(newer)
            self.assertFalse(newer_result.ok)
            self.assertEqual(newer_result.action, "RECOVERY_REQUIRED")

    def test_manifest_group_state_and_transaction_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = ManifestService(root / "manifests").open_or_create("session_test", root / "review")
            group = GroupRecord("group_1", "abc.rf", 2, "READY_FOR_PREVIEW", [str(root / "a.jpg"), str(root / "b.jpg")], [str(root / "a.txt"), str(root / "b.txt")])
            service = ManifestService(root / "manifests")
            service.add_group(manifest, group)
            service.update_group_state(manifest, "group_1", "DISPLAYED")
            self.assertEqual(service.counts_by_state(manifest)["DISPLAYED"], 1)
            plan = TransactionService().prepare_from_group(group, "a", dry_run=True)
            self.assertTrue(plan.dry_run)
            self.assertEqual(len(plan.operations), 4)

    def test_staging_default_disabled_and_path_escape_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            review = root / "review"
            review.mkdir()
            manifest = ManifestService(root / "manifests").open_or_create("session_test", review)
            result = StagingService().enable(manifest, confirmation="", review_dir=review)
            self.assertEqual(result["state"], "disabled")
            self.assertFalse(validate_inside(review, root / "outside").ok)
            dry = StagingService().dry_run(manifest, review)
            self.assertTrue(dry.ok)
            self.assertIn("未移动文件", dry.message)

    def test_recovery_detects_staging_dir_and_diagnostic_excludes_raw_images(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            review = Path(tmp) / "review"
            (review / "_ManualReview_Staging").mkdir(parents=True)
            snapshot = RecoveryService().scan("session_test", review_dir=review)
            self.assertTrue(snapshot.issues)
            raw = Path(tmp) / "raw.jpg"
            raw.write_bytes(b"not a real image")
            txt = Path(tmp) / "note.txt"
            txt.write_text("diagnostic text", encoding="utf-8")
            bundle = DiagnosticService().export_bundle("session_test", mode="redacted_share", sources=[raw, txt])
            self.assertFalse(bundle.raw_files_included)
            self.assertIn("note.txt", bundle.files)
            self.assertNotIn("raw.jpg", bundle.files)

    def test_id_initialisation_requires_init_confirmation_before_core_write(self) -> None:
        result = IdInitialisationService(core=V181CoreFacade()).initialise(object(), confirmation="")
        self.assertEqual(result["result"], "blocked")
        self.assertIn("INIT", result["message"])

    def test_core_facade_loads_v181_without_version_spoofing(self) -> None:
        facade = V181CoreFacade()
        report = facade.load()
        self.assertTrue(report.ok, report)
        self.assertEqual(report.core_version, "V1.8.1")
        self.assertNotEqual(report.core_version, civl7009_picker_v2.PROGRAMME_VERSION)

    def test_qt_shell_is_chinese_and_has_required_pages(self) -> None:
        window = MainWindow(run_mode="test")
        try:
            self.assertEqual(window.stack.count(), 7)
            self.assertIn("图源筛选", window.nav_buttons["Review"].text())
            self.assertIn("恢复中心", window.nav_buttons["Recovery"].text())
            self.assertIn("ID 初始化", window.nav_buttons["Initialise"].text())
            self.assertIn("安全门", window.context_label.text())
            window.set_page(4)
            self.assertEqual(window.stack.currentIndex(), 4)
            path = window.export_diagnostic_for_tests("redacted_share")
            self.assertTrue(path.exists())
        finally:
            window.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
