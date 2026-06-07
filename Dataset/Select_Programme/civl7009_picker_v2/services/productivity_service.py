from __future__ import annotations

import statistics
from dataclasses import dataclass, field

from ..domain.models import ProductivitySnapshot


@dataclass
class ProductivityService:
    click_to_next_ms: list[float] = field(default_factory=list)
    move_ms: list[float] = field(default_factory=list)
    groups_completed: int = 0
    undo_count: int = 0
    recovery_count: int = 0

    def record_commit(self, click_to_next_ms: float, move_ms: float = 0.0) -> None:
        self.groups_completed += 1
        self.click_to_next_ms.append(click_to_next_ms)
        self.move_ms.append(move_ms)

    def snapshot(self) -> ProductivitySnapshot:
        median = statistics.median(self.click_to_next_ms) if self.click_to_next_ms else 0.0
        sorted_moves = sorted(self.move_ms)
        p95 = sorted_moves[int((len(sorted_moves) - 1) * 0.95)] if sorted_moves else 0.0
        return ProductivitySnapshot(
            groups_completed=self.groups_completed,
            groups_per_min=0.0,
            median_click_to_next_ms=round(median, 3),
            p95_move_ms=round(p95, 3),
            undo_count=self.undo_count,
            recovery_count=self.recovery_count,
        )
