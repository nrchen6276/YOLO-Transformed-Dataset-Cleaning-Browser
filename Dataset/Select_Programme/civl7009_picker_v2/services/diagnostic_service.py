from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

from ..config import DIAGNOSTIC_BUNDLES_DIR
from ..domain.models import DiagnosticBundleResult


class DiagnosticService:
    def export_bundle(self, session_id: str, mode: str = "redacted_share", sources: list[Path] | None = None) -> DiagnosticBundleResult:
        if mode not in {"full_local", "redacted_share"}:
            raise ValueError("mode must be full_local or redacted_share")
        bundle = DIAGNOSTIC_BUNDLES_DIR / f"diagnostic_bundle_{session_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        bundle.mkdir(parents=True, exist_ok=True)
        manifest = {
            "session_id": session_id,
            "mode": mode,
            "raw_files_included": False,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "note": "redacted mode hashes parent paths; raw images/labels are never copied.",
        }
        (bundle / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        copied: list[str] = ["manifest.json"]
        for source in sources or []:
            if source.exists() and source.is_file() and source.suffix.casefold() not in {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}:
                target = bundle / source.name
                shutil.copy2(source, target)
                copied.append(target.name)
        return DiagnosticBundleResult(bundle, mode, False, copied)
