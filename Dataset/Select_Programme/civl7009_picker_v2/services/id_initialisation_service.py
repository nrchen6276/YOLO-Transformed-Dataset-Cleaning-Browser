from __future__ import annotations

from pathlib import Path

from ..core_bridge.v181_facade import V181CoreFacade


class IdInitialisationService:
    def __init__(self, core: V181CoreFacade | None = None) -> None:
        self.core = core or V181CoreFacade()

    def audit(self, id_root: Path):
        return self.core.require().audit_yolo_dataset(id_root)

    def initialise(self, audit, confirmation: str = ""):
        if confirmation != "INIT":
            return {"result": "blocked", "error_code": "ID_INIT_TARGET_CONFLICT", "message": "需要输入 INIT。"}
        return self.core.require().initialise_manualreview_from_yolo(audit)
