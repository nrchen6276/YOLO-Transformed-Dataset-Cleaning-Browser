from __future__ import annotations

import sys
from pathlib import Path

from .version import SCRIPT_TIMECODE


def resolve_programme_dir() -> Path:
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        if exe_dir.name.casefold() == "executable":
            return exe_dir.parent
        return exe_dir
    return Path(__file__).resolve().parents[1]


PROGRAMME_DIR = resolve_programme_dir()
ASSET_DIR_NAME = f"V2.0_{SCRIPT_TIMECODE}"
ASSET_DIR = PROGRAMME_DIR / "UI_Assets" / ASSET_DIR_NAME
RUNTIME_LOGS_DIR = PROGRAMME_DIR / "Runtime_Logs"
RUNTIME_MANIFESTS_DIR = PROGRAMME_DIR / "Runtime_Manifests"
DIAGNOSTIC_BUNDLES_DIR = PROGRAMME_DIR / "Diagnostic_Bundles"
PERFORMANCE_REPORTS_DIR = PROGRAMME_DIR / "Performance_Reports"
STATE_SNAPSHOTS_DIR = PROGRAMME_DIR / "State_Snapshots"
BUILD_REPORTS_DIR = PROGRAMME_DIR / "Build_Reports"
AUDIT_REPORTS_DIR = PROGRAMME_DIR / "Audit_Reports"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
LABEL_EXTENSIONS = {".txt"}

DEFAULT_LOG_MAX_BYTES = 25 * 1024 * 1024
DEFAULT_LOG_KEEP = 8
DEFAULT_UNDO_STACK_LIMIT = 10
DEFAULT_VISUAL_QUALITY = "Balanced"
DEFAULT_THEME = "light"
