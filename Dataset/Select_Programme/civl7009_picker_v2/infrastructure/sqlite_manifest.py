from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from ..version import PROGRAMME_VERSION, UI_VERSION

SCHEMA_VERSION = 1
APP_MIN_SCHEMA_VERSION = 1
APP_MAX_SCHEMA_VERSION = 1


@dataclass
class ManifestOpenResult:
    ok: bool
    action: str
    schema_version: int
    message: str = ""
    backup_path: Path | None = None


def connect_manifest(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialise_schema(conn: sqlite3.Connection) -> None:
    conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS migrations (id INTEGER PRIMARY KEY AUTOINCREMENT, from_version INTEGER, to_version INTEGER, applied_at TEXT, result TEXT)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS manifest_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS runs (run_id TEXT PRIMARY KEY, session_id TEXT, id_root TEXT, image_review_dir TEXT, label_review_dir TEXT, review_name TEXT, group_size INTEGER, programme_version TEXT, ui_version TEXT, started_at TEXT, finished_at TEXT, status TEXT)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS groups (group_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, prefix TEXT, group_size INTEGER, state TEXT, source_image_paths_json TEXT, source_label_paths_json TEXT, selected_stem TEXT, created_at TEXT, updated_at TEXT, error_code TEXT, error_message TEXT, FOREIGN KEY(run_id) REFERENCES runs(run_id))"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS operations (operation_id TEXT PRIMARY KEY, run_id TEXT, group_id TEXT, kind TEXT, source TEXT, target TEXT, role TEXT, state TEXT, started_at TEXT, finished_at TEXT, error_code TEXT, error_message TEXT, FOREIGN KEY(run_id) REFERENCES runs(run_id), FOREIGN KEY(group_id) REFERENCES groups(group_id))"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS audit_snapshots (snapshot_id TEXT PRIMARY KEY, run_id TEXT, created_at TEXT, root_image_count INTEGER, root_prefix_count INTEGER, done_image_count INTEGER, done_prefix_count INTEGER, out_image_count INTEGER, out_prefix_count INTEGER, missing_label_count INTEGER, orphan_label_count INTEGER, duplicate_label_count INTEGER, blocking_error_count INTEGER, snapshot_json TEXT, FOREIGN KEY(run_id) REFERENCES runs(run_id))"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS events (event_id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, timestamp TEXT, event_type TEXT, severity TEXT, payload_json TEXT, FOREIGN KEY(run_id) REFERENCES runs(run_id))"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS undo_stack (undo_id TEXT PRIMARY KEY, run_id TEXT, transaction_id TEXT, prefix TEXT, selected_stem TEXT, operation_json TEXT, created_at TEXT, state TEXT, FOREIGN KEY(run_id) REFERENCES runs(run_id))"
    )
    now = datetime.now().isoformat(timespec="seconds")
    conn.execute("INSERT OR IGNORE INTO schema_version(version, applied_at) VALUES (?, ?)", (SCHEMA_VERSION, now))
    metadata = {
        "app_min_schema_version": str(APP_MIN_SCHEMA_VERSION),
        "app_max_schema_version": str(APP_MAX_SCHEMA_VERSION),
        "created_by_programme_version": PROGRAMME_VERSION,
        "created_by_ui_version": UI_VERSION,
        "stores_raw_image_label_bytes": "false",
    }
    for key, value in metadata.items():
        conn.execute("INSERT OR REPLACE INTO manifest_metadata(key, value) VALUES (?, ?)", (key, value))
    conn.commit()


def get_user_version(conn: sqlite3.Connection) -> int:
    return int(conn.execute("PRAGMA user_version").fetchone()[0])


def table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def verify_schema(conn: sqlite3.Connection) -> tuple[bool, str]:
    required = {
        "schema_version": {"version", "applied_at"},
        "migrations": {"id", "from_version", "to_version", "applied_at", "result"},
        "manifest_metadata": {"key", "value"},
        "runs": {"run_id", "session_id", "status"},
        "groups": {"group_id", "run_id", "prefix", "state", "source_image_paths_json"},
        "operations": {"operation_id", "run_id", "group_id", "state"},
        "audit_snapshots": {"snapshot_id", "run_id", "snapshot_json"},
        "events": {"event_id", "run_id", "event_type", "payload_json"},
        "undo_stack": {"undo_id", "run_id", "transaction_id", "state"},
    }
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    for table, columns in required.items():
        if table not in tables:
            return False, f"missing table {table}"
        missing = columns - table_columns(conn, table)
        if missing:
            return False, f"missing columns {table}: {sorted(missing)}"
    return True, "ok"


def backup_manifest(path: Path) -> Path:
    backup_dir = path.parent / "Backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup = backup_dir / f"{path.stem}_{datetime.now().strftime('%Y%m%d%H%M%S')}.sqlite"
    shutil.copy2(path, backup)
    return backup


def open_manifest(path: Path) -> ManifestOpenResult:
    existed = path.exists()
    conn = connect_manifest(path)
    try:
        if existed:
            integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
            if integrity != "ok":
                return ManifestOpenResult(False, "RECOVERY_REQUIRED", get_user_version(conn), f"integrity_check failed: {integrity}")
        version = get_user_version(conn)
        if not existed or version == 0:
            initialise_schema(conn)
            return ManifestOpenResult(True, "created", SCHEMA_VERSION)
        if version > APP_MAX_SCHEMA_VERSION:
            return ManifestOpenResult(False, "RECOVERY_REQUIRED", version, "manifest schema newer than app")
        backup = None
        if version < APP_MIN_SCHEMA_VERSION:
            backup = backup_manifest(path)
            return ManifestOpenResult(False, "RECOVERY_REQUIRED", version, "migration path unavailable", backup)
        ok, message = verify_schema(conn)
        return ManifestOpenResult(ok, "opened" if ok else "RECOVERY_REQUIRED", version, message)
    finally:
        conn.close()


def manifest_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def insert_event(conn: sqlite3.Connection, run_id: str, event_type: str, severity: str, payload: dict[str, Any]) -> None:
    conn.execute(
        "INSERT INTO events(run_id, timestamp, event_type, severity, payload_json) VALUES (?, ?, ?, ?, ?)",
        (run_id, datetime.now().isoformat(timespec="milliseconds"), event_type, severity, json.dumps(payload, ensure_ascii=False)),
    )
    conn.commit()
