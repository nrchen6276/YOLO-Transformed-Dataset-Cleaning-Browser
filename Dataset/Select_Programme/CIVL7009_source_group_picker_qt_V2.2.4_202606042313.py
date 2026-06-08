from __future__ import annotations

import sys
from pathlib import Path

PROGRAMME_DIR = Path(__file__).resolve().parent
if str(PROGRAMME_DIR) not in sys.path:
    sys.path.insert(0, str(PROGRAMME_DIR))

from civl7009_picker_v2_2_4.app import main
from civl7009_picker_v2_2_4.version import PROGRAMME_VERSION, SCRIPT_TIMECODE, SCRIPT_VERSION, UI_VERSION


if __name__ == "__main__":
    raise SystemExit(main())
