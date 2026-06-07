from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Capability:
    name: str
    display_name: str
    default_state: str
    risk: str
    raw_file_movement: bool
    gate: str
    storage: str = ""
    enabled: bool = False
    description: str = ""


@dataclass
class AuditIssue:
    severity: str
    error_code: str
    prefix: str = ""
    affected_paths: list[str] = field(default_factory=list)
    why_it_blocks: str = ""
    suggested_action: str = ""
    can_auto_fix: bool = False
    recovery_action_available: bool = False


@dataclass
class ManifestRun:
    run_id: str
    session_id: str
    manifest_path: Path
    review_dir: str = ""
    label_dir: str = ""
    status: str = "OPEN"
    schema_version: int = 1
    group_count: int = 0


@dataclass
class ManifestIntegrityReport:
    ok: bool
    schema_version: int
    action: str
    message: str = ""
    backup_path: str = ""
    issues: list[AuditIssue] = field(default_factory=list)


@dataclass
class GroupRecord:
    group_id: str
    prefix: str
    group_size: int
    state: str
    image_paths: list[str]
    label_paths: list[str]
    selected_stem: str = ""
    error_code: str = ""
    error_message: str = ""


@dataclass
class TransactionPlan:
    transaction_id: str
    group_id: str
    prefix: str
    selected_stem: str
    operations: list[dict[str, Any]]
    dry_run: bool = True
    target_conflict_ok: bool = True
    error_code: str = ""
    error_message: str = ""


@dataclass
class StagingDryRunReport:
    ok: bool
    run_id: str
    checked_groups: int
    same_volume: bool
    message: str
    issues: list[AuditIssue] = field(default_factory=list)


@dataclass
class RecoverySnapshot:
    clean: bool
    session_id: str
    issues: list[AuditIssue] = field(default_factory=list)


@dataclass
class DiagnosticBundleResult:
    path: Path
    mode: str
    raw_files_included: bool
    files: list[str]


@dataclass
class ProductivitySnapshot:
    groups_completed: int = 0
    groups_per_min: float = 0.0
    median_click_to_next_ms: float = 0.0
    p95_move_ms: float = 0.0
    undo_count: int = 0
    recovery_count: int = 0
    rough_remaining_time: str = "rough estimate, not a data quality metric"


def to_jsonable(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return {k: to_jsonable(v) for k, v in asdict(value).items()}
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, list):
        return [to_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {k: to_jsonable(v) for k, v in value.items()}
    return value
