from __future__ import annotations

import sys
from pathlib import Path

from .version import CORE_FILENAME, UI_VERSION


def resolve_programme_dir() -> Path:
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        if exe_dir.name.casefold() == "executable":
            return exe_dir.parent
        return exe_dir
    return Path(__file__).resolve().parents[1]


def resolve_bundle_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(getattr(sys, "_MEIPASS")).resolve()
    return Path(__file__).resolve().parents[1]


PROGRAMME_DIR = resolve_programme_dir()
BUNDLE_DIR = resolve_bundle_dir()
ASSET_DIR = PROGRAMME_DIR / "UI_Assets" / UI_VERSION
CORE_CANDIDATES = [
    BUNDLE_DIR / CORE_FILENAME,
    PROGRAMME_DIR / CORE_FILENAME,
    Path(__file__).resolve().parents[1] / CORE_FILENAME,
]
CORE_PATH = CORE_CANDIDATES[0]
RUNTIME_LOG_ROOT = PROGRAMME_DIR / "Runtime_Logs"
BUILD_REPORT_ROOT = PROGRAMME_DIR / "Build_Reports"
