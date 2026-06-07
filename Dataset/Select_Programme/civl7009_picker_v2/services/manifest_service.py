from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from ..config import RUNTIME_MANIFESTS_DIR
from ..domain.models import GroupRecord, ManifestIntegrityReport, ManifestRun
from ..infrastructure.ids import new_id
from ..infrastructure.sqlite_manifest import connect_manifest, initialise_schema, open_manifest


class ManifestService:
    def __init__(self, manifests_root: Path = RUNTIME_MANIFESTS_DIR) -> None:
        self.manifests_root = manifests_root

    def manifest_path_for_session(self, session_id: str) -> Path:
        return self.manifests_root / session_id / "review_manifest.sqlite"

    def open_or_create(self, session_id: str, review_dir: Path, label_dir: Path | None = None) -> ManifestRun:
        path = self.manifest_path_for_session(session_id)
        result = open_manifest(path)
        if not result.ok:
            raise RuntimeError(f"RECOVERY_REQUIRED: {result.message}")
        run_id = new_id("manifest")
        conn = connect_manifest(path)
        try:
            initialise_schema(conn)
            conn.execute(
                "INSERT OR REPLACE INTO runs(run_id, session_id, image_review_dir, label_review_dir, review_name, programme_version, ui_version, started_at, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    run_id,
                    session_id,
                    str(review_dir),
                    str(label_dir or ""),
                    review_dir.name,
                    "V2.0",
                    "V2.0_202606041822",
                    datetime.now().isoformat(timespec="seconds"),
                    "OPEN",
                ),
            )
            conn.commit()
            count = conn.execute("SELECT COUNT(*) FROM groups WHERE run_id=?", (run_id,)).fetchone()[0]
            return ManifestRun(run_id, session_id, path, str(review_dir), str(label_dir or ""), "OPEN", 1, count)
        finally:
            conn.close()

    def check_integrity(self, manifest_path: Path) -> ManifestIntegrityReport:
        result = open_manifest(manifest_path)
        return ManifestIntegrityReport(result.ok, result.schema_version, result.action, result.message, str(result.backup_path or ""))

    def migrate_if_needed(self, manifest_path: Path) -> ManifestIntegrityReport:
        return self.check_integrity(manifest_path)

    def add_group(self, manifest: ManifestRun, group: GroupRecord) -> None:
        conn = connect_manifest(manifest.manifest_path)
        try:
            conn.execute(
                "INSERT OR REPLACE INTO groups(group_id, run_id, prefix, group_size, state, source_image_paths_json, source_label_paths_json, selected_stem, created_at, updated_at, error_code, error_message) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    group.group_id,
                    manifest.run_id,
                    group.prefix,
                    group.group_size,
                    group.state,
                    json.dumps(group.image_paths, ensure_ascii=False),
                    json.dumps(group.label_paths, ensure_ascii=False),
                    group.selected_stem,
                    datetime.now().isoformat(timespec="seconds"),
                    datetime.now().isoformat(timespec="seconds"),
                    group.error_code,
                    group.error_message,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def update_group_state(self, manifest: ManifestRun, group_id: str, state: str) -> None:
        conn = connect_manifest(manifest.manifest_path)
        try:
            conn.execute(
                "UPDATE groups SET state=?, updated_at=? WHERE group_id=? AND run_id=?",
                (state, datetime.now().isoformat(timespec="seconds"), group_id, manifest.run_id),
            )
            conn.commit()
        finally:
            conn.close()

    def counts_by_state(self, manifest: ManifestRun) -> dict[str, int]:
        conn = connect_manifest(manifest.manifest_path)
        try:
            rows = conn.execute("SELECT state, COUNT(*) FROM groups WHERE run_id=? GROUP BY state", (manifest.run_id,)).fetchall()
            return {state: count for state, count in rows}
        finally:
            conn.close()
