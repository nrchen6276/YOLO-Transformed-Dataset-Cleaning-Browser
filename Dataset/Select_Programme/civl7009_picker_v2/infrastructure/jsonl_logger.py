from __future__ import annotations

import hashlib
import json
import os
import sys
import threading
import time
import traceback
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from ..config import DEFAULT_LOG_KEEP, DEFAULT_LOG_MAX_BYTES, RUNTIME_LOGS_DIR
from ..version import LOG_SCHEMA_VERSION, LOGGER_VERSION, PROGRAMME_VERSION, UI_VERSION


def now_iso() -> str:
    return datetime.now().isoformat(timespec="milliseconds")


def runtime_subdir(run_mode: str) -> str:
    return {
        "gui_production": "Production",
        "production": "Production",
        "test": "Test",
        "audit_only": "AuditOnly",
        "debug": "Debug",
    }.get(run_mode, "Debug")


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


class V2Logger:
    def __init__(self, run_mode: str = "", log_root: Path = RUNTIME_LOGS_DIR, max_bytes: int = DEFAULT_LOG_MAX_BYTES) -> None:
        self.run_mode = detect_run_mode(run_mode)
        self.session_id = f"session_{uuid.uuid4().hex[:16]}"
        self.trace_id = f"trace_{uuid.uuid4().hex[:12]}"
        self.started = time.perf_counter()
        self.log_dir = log_root / runtime_subdir(self.run_mode)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d%H%M%S%f")[:-3]
        self.path = self.log_dir / f"picker_events_{PROGRAMME_VERSION}_{stamp}.jsonl"
        self.max_bytes = max_bytes
        self.keep = DEFAULT_LOG_KEEP
        self.lock = threading.Lock()
        self.index = 0
        self.handle = self.path.open("a", encoding="utf-8", buffering=1)
        self.core_meta: dict[str, Any] = {}
        self.review_dir = ""
        self.event("app_start", argv=sys.argv)

    def set_core_meta(self, **meta: Any) -> None:
        self.core_meta.update(meta)
        self.event("core_meta_updated", **meta)

    def set_review_dir(self, review_dir: str | Path | None) -> None:
        self.review_dir = str(review_dir or "")

    def _base(self, event: str, severity: str = "INFO") -> dict[str, Any]:
        return {
            "timestamp": now_iso(),
            "elapsed_ms": round((time.perf_counter() - self.started) * 1000, 3),
            "log_schema_version": LOG_SCHEMA_VERSION,
            "logger_version": LOGGER_VERSION,
            "session_id": self.session_id,
            "trace_id": self.trace_id,
            "event": event,
            "severity": severity,
            "programme_version": PROGRAMME_VERSION,
            "ui_version": UI_VERSION,
            "core_version": self.core_meta.get("core_version", ""),
            "run_mode": self.run_mode,
            "review_dir": self.review_dir,
            "operation_id": "",
            "transaction_id": "",
            "staging_run_id": "",
            "manifest_run_id": "",
            "group_id": "",
            "prefix": "",
            "duration_ms": None,
            "state_before": "",
            "state_after": "",
            "error_code": "",
            "exception_type": "",
            "stack_trace_hash": "",
            "thread": threading.current_thread().name,
        }

    def event(self, event: str, severity: str = "INFO", **fields: Any) -> None:
        payload = self._base(event, severity)
        payload.update(fields)
        with self.lock:
            self._rotate_if_needed()
            self.handle.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")

    def perf(self, event: str, started: float, **fields: Any) -> None:
        fields["duration_ms"] = round((time.perf_counter() - started) * 1000, 3)
        self.event(event, **fields)

    def exception(self, event: str, exc: BaseException, **fields: Any) -> None:
        stack = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        fields.update(
            exception_type=type(exc).__name__,
            stack_trace_hash=hashlib.sha256(stack.encode("utf-8", errors="replace")).hexdigest()[:16],
            error_message=str(exc),
        )
        self.event(event, severity="ERROR", **fields)

    def _rotate_if_needed(self) -> None:
        if self.handle.tell() < self.max_bytes:
            return
        self.handle.close()
        self.index += 1
        rotated = self.path.with_name(f"{self.path.stem}.{self.index}.jsonl")
        self.handle = rotated.open("a", encoding="utf-8", buffering=1)
        self._cleanup_old_logs()

    def _cleanup_old_logs(self) -> None:
        logs = sorted(self.log_dir.glob(f"{self.path.stem}*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
        for old in logs[self.keep :]:
            old.unlink(missing_ok=True)

    def close(self) -> None:
        self.event("app_closed")
        with self.lock:
            self.handle.close()
