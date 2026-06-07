from __future__ import annotations

import hashlib
import importlib.util
import inspect
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .paths import CORE_CANDIDATES, CORE_PATH


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass
class CoreLoadReport:
    ok: bool
    path: Path | None = None
    core_sha256: str = ""
    missing_symbols: list[str] = field(default_factory=list)
    signature_errors: list[str] = field(default_factory=list)
    error: str = ""
    candidate_paths: list[str] = field(default_factory=list)


class PickerCoreFacade:
    REQUIRED_SYMBOLS = [
        "review_dirs_for_id_root",
        "build_quick_preview_index",
        "build_fast_review_index",
        "audit_review_dir",
        "prepare_transaction_from_fast_index",
        "BackgroundMoveRunner",
        "QueuedMoveTask",
        "ReviewDirLock",
        "execute_transaction",
        "undo_transaction",
        "export_target_audit_report",
        "scan_unfinished_transactions",
        "keypad_slots_for_count",
        "keypad_grid_size",
    ]
    SIGNATURE_REQUIREMENTS = {
        "review_dirs_for_id_root": ["id_root"],
        "build_quick_preview_index": ["image_review_dir"],
        "build_fast_review_index": ["image_review_dir"],
        "audit_review_dir": ["image_review_dir"],
        "prepare_transaction_from_fast_index": ["index", "prefix", "selected_image"],
        "undo_transaction": ["transaction"],
        "export_target_audit_report": ["image_dir"],
    }

    def __init__(self, core_path: Path | None = None) -> None:
        if core_path is not None:
            self.candidate_paths = [Path(core_path).resolve()]
        else:
            self.candidate_paths = [path.resolve() for path in CORE_CANDIDATES]
        self.core_path = self.candidate_paths[0] if self.candidate_paths else CORE_PATH.resolve()
        self.core: Any | None = None
        self.report = self.load()

    def load(self) -> CoreLoadReport:
        candidate_text = [str(path) for path in self.candidate_paths]
        existing = [path for path in self.candidate_paths if path.exists()]
        if not existing:
            return CoreLoadReport(
                ok=False,
                path=self.core_path,
                error=f"core 文件不存在；已检查候选路径: {candidate_text}",
                candidate_paths=candidate_text,
            )

        self.core_path = existing[0]
        module_name = f"civl7009_v181_core_{self.core_path.stem}"
        try:
            before_tk = [name for name in sys.modules if name.startswith("tkinter")]
            spec = importlib.util.spec_from_file_location(module_name, self.core_path)
            if spec is None or spec.loader is None:
                raise RuntimeError("无法创建 core import spec")
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            after_tk = [name for name in sys.modules if name.startswith("tkinter")]

            missing = [symbol for symbol in self.REQUIRED_SYMBOLS if not hasattr(module, symbol)]
            signature_errors: list[str] = []
            for symbol, required_params in self.SIGNATURE_REQUIREMENTS.items():
                if not hasattr(module, symbol):
                    continue
                params = inspect.signature(getattr(module, symbol)).parameters
                for param in required_params:
                    if param not in params:
                        signature_errors.append(f"{symbol} 缺少参数 {param}")

            self.core = module
            side_effect_notes: list[str] = []
            if not before_tk and after_tk:
                side_effect_notes.append("core import loaded tkinter modules")

            ok = not missing and not signature_errors
            return CoreLoadReport(
                ok=ok,
                path=self.core_path,
                core_sha256=sha256_file(self.core_path),
                missing_symbols=missing,
                signature_errors=signature_errors + side_effect_notes,
                error="" if ok else "core 符号或签名检查失败",
                candidate_paths=candidate_text,
            )
        except Exception as exc:
            return CoreLoadReport(ok=False, path=self.core_path, error=str(exc), candidate_paths=candidate_text)

    def require_core(self) -> Any:
        if self.core is None or not self.report.ok:
            raise RuntimeError(self.report.error or "core 未加载")
        return self.core

    def review_dirs_for_id_root(self, id_root: Path) -> list[Path]:
        return list(self.require_core().review_dirs_for_id_root(id_root))

    def quick_index(self, review_dir: Path, preview_limit: int = 20) -> Any:
        return self.require_core().build_quick_preview_index(review_dir, preview_limit=preview_limit)

    def fast_index(self, review_dir: Path) -> Any:
        return self.require_core().build_fast_review_index(review_dir)

    def audit(self, review_dir: Path) -> tuple[Any, list[Any]]:
        return self.require_core().audit_review_dir(review_dir, create_missing=False)

    def export_audit(self, review_dir: Path) -> Path:
        return self.require_core().export_target_audit_report(review_dir)

    def keypad_slots(self, count: int) -> list[Any]:
        core = self.require_core()
        if count <= 9:
            return list(core.keypad_slots_for_count(count))
        base = list(core.keypad_slots_for_count(9))
        extras = [
            type(base[0])(index=idx, key=None, row=3 + ((idx - 9) // 3), col=(idx - 9) % 3)
            for idx in range(9, count)
        ]
        return base + extras

    def keypad_grid_size(self, slots: list[Any]) -> tuple[int, int]:
        if not slots:
            return (1, 1)
        return max(slot.row for slot in slots) + 1, max(slot.col for slot in slots) + 1
