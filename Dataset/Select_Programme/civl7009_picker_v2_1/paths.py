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


PROGRAMME_DIR = resolve_programme_dir()
ASSET_DIR = PROGRAMME_DIR / "UI_Assets" / UI_VERSION
CORE_PATH = PROGRAMME_DIR / CORE_FILENAME
RUNTIME_LOG_ROOT = PROGRAMME_DIR / "Runtime_Logs"
BUILD_REPORT_ROOT = PROGRAMME_DIR / "Build_Reports"
