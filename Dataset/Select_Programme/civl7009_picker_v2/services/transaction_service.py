from __future__ import annotations

from pathlib import Path

from ..domain.models import GroupRecord, TransactionPlan
from ..infrastructure.ids import new_id


class TransactionService:
    def prepare_from_group(self, group: GroupRecord, selected_stem: str, dry_run: bool = True) -> TransactionPlan:
        operations = []
        for image in group.image_paths:
            stem = Path(image).stem
            role = "source" if stem == selected_stem else "variant"
            operations.append({"kind": "image", "source": image, "target_role": "done" if role == "source" else "out", "role": role})
        for label in group.label_paths:
            stem = Path(label).stem
            role = "source" if stem == selected_stem else "variant"
            operations.append({"kind": "label", "source": label, "target_role": "done" if role == "source" else "out", "role": role})
        return TransactionPlan(new_id("txn"), group.group_id, group.prefix, selected_stem, operations, dry_run=dry_run)

    def enqueue(self, plan: TransactionPlan, trace_id: str = "") -> dict[str, str]:
        if plan.dry_run:
            return {"state": "dry_run_only", "transaction_id": plan.transaction_id}
        return {"state": "queued", "transaction_id": plan.transaction_id, "trace_id": trace_id}
