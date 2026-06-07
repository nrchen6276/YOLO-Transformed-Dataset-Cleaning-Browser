from __future__ import annotations

import hashlib
import importlib.util
import inspect
import sys
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any

from ..config import PROGRAMME_DIR
from ..version import CORE_FILENAME

REQUIRED_SYMBOLS = [
    "build_quick_preview_index",
    "build_fast_review_index",
    "audit_review_dir",
    "prepare_transaction_from_fast_index",
    "BackgroundMoveRunner",
    "ReviewDirLock",
    "execute_transaction",
    "undo_transaction",
    "export_audit_report",
    "audit_yolo_dataset",
    "initialise_manualreview_from_yolo",
]


@dataclass
class CoreLoadReport:
    ok: bool
    core_file: str
    core_sha256: str = ""
    core_version: str = ""
    core_timecode: str = ""
    missing_symbols: list[str] = field(default_factory=list)
    signature_mismatch: list[str] = field(default_factory=list)
    error: str = ""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class V181CoreFacade:
    def __init__(self, core_path: Path | None = None) -> None:
        self.core_path = core_path or (PROGRAMME_DIR / CORE_FILENAME)
        self.module: ModuleType | None = None
        self.report = CoreLoadReport(False, str(self.core_path))

    def load(self) -> CoreLoadReport:
        try:
            if not self.core_path.exists():
                self.report.error = "core file missing"
                return self.report
            before_modules = set(sys.modules)
            spec = importlib.util.spec_from_file_location("civl7009_v181_core_for_v2", self.core_path)
            if spec is None or spec.loader is None:
                self.report.error = "cannot create import spec"
                return self.report
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            after_modules = set(sys.modules)
            missing = [name for name in REQUIRED_SYMBOLS if not hasattr(module, name)]
            mismatch = self._signature_check(module)
            self.report = CoreLoadReport(
                ok=not missing and not mismatch,
                core_file=str(self.core_path),
                core_sha256=sha256_file(self.core_path),
                core_version=getattr(module, "SCRIPT_VERSION", ""),
                core_timecode=getattr(module, "SCRIPT_TIMECODE", ""),
                missing_symbols=missing,
                signature_mismatch=mismatch,
            )
            self.module = module if self.report.ok else None
            return self.report
        except Exception as exc:
            self.report.error = str(exc)
            return self.report

    def _signature_check(self, module: ModuleType) -> list[str]:
        checks: dict[str, list[str]] = {
            "prepare_transaction_from_fast_index": ["index", "prefix", "selected_image"],
            "audit_review_dir": ["image_review_dir"],
            "build_fast_review_index": ["image_review_dir"],
        }
        errors: list[str] = []
        for name, required in checks.items():
            if not hasattr(module, name):
                continue
            params = list(inspect.signature(getattr(module, name)).parameters)
            for item in required:
                if item not in params:
                    errors.append(f"{name} missing parameter {item}")
        return errors

    def require(self) -> ModuleType:
        if self.module is None:
            report = self.load()
            if not report.ok or self.module is None:
                raise RuntimeError(f"V1.8.1 core load failed: {report}")
        return self.module

    def audit_review_dir(self, image_base: Path) -> Any:
        return self.require().audit_review_dir(image_base)

    def build_fast_review_index(self, image_base: Path) -> Any:
        return self.require().build_fast_review_index(image_base)

    def build_quick_preview_index(self, image_base: Path, max_prefixes: int = 20) -> Any:
        return self.require().build_quick_preview_index(image_base, max_prefixes=max_prefixes)
