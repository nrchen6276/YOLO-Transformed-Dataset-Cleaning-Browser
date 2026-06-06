from __future__ import annotations

import json
import os
import re
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from .paths import PROGRAMME_DIR
from .version import UI_VERSION

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
LABEL_EXT = ".txt"
TIER_RE = re.compile(r"^Tier(?P<tier>\d{2})_", re.IGNORECASE)
ID_RE = re.compile(r"^ID\d{2,}[_-]", re.IGNORECASE)


@dataclass
class TierFileRecord:
    path: Path
    kind: str
    stem: str
    suffix: str
    relative_path: str
    canonical_stem: str
    dataset_id: str
    tier: str
    marked: bool
    paired_exists: bool = False


@dataclass
class TierStemGroup:
    canonical_stem: str
    image_count: int = 0
    label_count: int = 0
    marked_count: int = 0
    unmarked_count: int = 0
    dataset_ids: set[str] = field(default_factory=set)
    tiers: set[str] = field(default_factory=set)
    records: list[TierFileRecord] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)

    @property
    def status(self) -> str:
        if self.issues:
            return "ERROR"
        if self.unmarked_count == 0 and self.marked_count:
            return "MARKED"
        if self.marked_count and self.unmarked_count:
            return "PARTIAL"
        return "UNMARKED"


@dataclass
class TierScanResult:
    root: Path
    groups: list[TierStemGroup]
    file_count: int
    image_count: int
    label_count: int
    marked_count: int
    unmarked_count: int
    issue_count: int
    duration_ms: float


@dataclass
class TierRenameOperation:
    source: Path
    target: Path
    kind: str
    canonical_stem: str


@dataclass
class TierRenamePlan:
    root: Path
    tier: str
    operations: list[TierRenameOperation]
    blocked_reasons: list[str]

    @property
    def can_apply(self) -> bool:
        return bool(self.operations) and not self.blocked_reasons


def normalise_tier(text: str) -> str:
    match = re.search(r"(\d{1,2})", text or "")
    if not match:
        raise ValueError("Tier 必须包含 1-2 位数字，例如 Tier01。")
    return f"Tier{int(match.group(1)):02d}"


def strip_tier_prefix(stem: str) -> tuple[str, str, bool]:
    match = TIER_RE.match(stem)
    if not match:
        return stem, "", False
    return stem[match.end():], f"Tier{int(match.group('tier')):02d}", True


def strip_id_prefix(stem: str) -> tuple[str, str]:
    match = ID_RE.match(stem)
    if not match:
        return stem, ""
    raw = stem[: match.end()]
    dataset_id = raw.rstrip("_-")
    return stem[match.end():], dataset_id


def canonical_stem_for_tier(stem: str) -> tuple[str, str, str, bool]:
    without_tier, tier, marked = strip_tier_prefix(stem)
    without_id, dataset_id = strip_id_prefix(without_tier)
    return without_id, dataset_id, tier, marked


class TierPrefixGovernanceService:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def scan(self) -> TierScanResult:
        started = time.perf_counter()
        records: list[TierFileRecord] = []
        for path in self._iter_candidate_files():
            canonical, dataset_id, tier, marked = canonical_stem_for_tier(path.stem)
            kind = "image" if path.suffix.lower() in IMAGE_EXTS else "label"
            paired = self._paired_path(path, kind).exists()
            records.append(
                TierFileRecord(
                    path=path,
                    kind=kind,
                    stem=path.stem,
                    suffix=path.suffix,
                    relative_path=str(path.relative_to(self.root)),
                    canonical_stem=canonical,
                    dataset_id=dataset_id,
                    tier=tier,
                    marked=marked,
                    paired_exists=paired,
                )
            )
        groups_by_key: dict[str, TierStemGroup] = {}
        for record in records:
            group = groups_by_key.setdefault(record.canonical_stem, TierStemGroup(record.canonical_stem))
            group.records.append(record)
            if record.kind == "image":
                group.image_count += 1
            else:
                group.label_count += 1
            if record.marked:
                group.marked_count += 1
                if record.tier:
                    group.tiers.add(record.tier)
            else:
                group.unmarked_count += 1
            if record.dataset_id:
                group.dataset_ids.add(record.dataset_id)
            if not record.paired_exists:
                group.issues.append(f"{record.kind.upper()}_PAIR_MISSING: {record.relative_path}")
        groups = sorted(groups_by_key.values(), key=lambda item: (-item.unmarked_count, item.canonical_stem.lower()))
        issue_count = sum(len(group.issues) for group in groups)
        marked_count = sum(record.marked for record in records)
        return TierScanResult(
            root=self.root,
            groups=groups,
            file_count=len(records),
            image_count=sum(record.kind == "image" for record in records),
            label_count=sum(record.kind == "label" for record in records),
            marked_count=marked_count,
            unmarked_count=len(records) - marked_count,
            issue_count=issue_count,
            duration_ms=(time.perf_counter() - started) * 1000,
        )

    def build_plan(self, tier_text: str, only_unmarked: bool = True) -> TierRenamePlan:
        tier = normalise_tier(tier_text)
        result = self.scan()
        operations: list[TierRenameOperation] = []
        blocked: list[str] = []
        for group in result.groups:
            for record in group.records:
                if only_unmarked and record.marked:
                    continue
                if record.marked:
                    target_stem = TIER_RE.sub(f"{tier}_", record.stem, count=1)
                else:
                    target_stem = f"{tier}_{record.stem}"
                target = record.path.with_name(target_stem + record.suffix)
                if target == record.path:
                    continue
                if target.exists():
                    blocked.append(f"TARGET_EXISTS: {target}")
                    continue
                operations.append(TierRenameOperation(record.path, target, record.kind, record.canonical_stem))
        return TierRenamePlan(self.root, tier, operations, blocked)

    def apply_plan(self, plan: TierRenamePlan) -> Path:
        if not plan.can_apply:
            raise RuntimeError("Tier rename plan is blocked or empty.")
        journal_dir = PROGRAMME_DIR / "Runtime_Logs" / "Tier_Governance"
        journal_dir.mkdir(parents=True, exist_ok=True)
        journal_path = journal_dir / f"tier_prefix_rename_{UI_VERSION}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jsonl"
        completed: list[TierRenameOperation] = []
        try:
            with journal_path.open("w", encoding="utf-8", buffering=1) as handle:
                for operation in plan.operations:
                    row = {
                        "event": "PLANNED",
                        "source": str(operation.source),
                        "target": str(operation.target),
                        "kind": operation.kind,
                        "canonical_stem": operation.canonical_stem,
                        "programme_version": UI_VERSION,
                    }
                    handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                for operation in plan.operations:
                    operation.source.rename(operation.target)
                    completed.append(operation)
                    row = {
                        "event": "RENAMED",
                        "source": str(operation.source),
                        "target": str(operation.target),
                        "kind": operation.kind,
                        "canonical_stem": operation.canonical_stem,
                        "programme_version": UI_VERSION,
                    }
                    handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            return journal_path
        except Exception:
            for operation in reversed(completed):
                if operation.target.exists() and not operation.source.exists():
                    operation.target.rename(operation.source)
            raise

    def export_scan_report(self, result: TierScanResult) -> Path:
        out_dir = PROGRAMME_DIR / "Audit_Reports"
        out_dir.mkdir(parents=True, exist_ok=True)
        target = out_dir / f"tier_prefix_scan_{UI_VERSION}_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
        payload = {
            "schema_version": "CIVL7009_TIER_PREFIX_SCAN_V1",
            "claim_status": "PENDING_AUDIT",
            "root": str(result.root),
            "file_count": result.file_count,
            "image_count": result.image_count,
            "label_count": result.label_count,
            "marked_count": result.marked_count,
            "unmarked_count": result.unmarked_count,
            "issue_count": result.issue_count,
            "duration_ms": result.duration_ms,
            "groups": [
                {
                    "canonical_stem": group.canonical_stem,
                    "status": group.status,
                    "image_count": group.image_count,
                    "label_count": group.label_count,
                    "marked_count": group.marked_count,
                    "unmarked_count": group.unmarked_count,
                    "dataset_ids": sorted(group.dataset_ids),
                    "tiers": sorted(group.tiers),
                    "issues": group.issues[:50],
                }
                for group in result.groups
            ],
        }
        fd, tmp_name = tempfile.mkstemp(prefix="tier_prefix_scan_", suffix=".json.tmp", dir=str(out_dir))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
            os.replace(tmp_name, target)
        finally:
            tmp_path = Path(tmp_name)
            if tmp_path.exists():
                tmp_path.unlink()
        return target

    def _iter_candidate_files(self) -> list[Path]:
        blocked_parts = {"Manual_Objects", "Removed", "Removed_By_Dedup", "_ManualReview_Staging", "__pycache__"}
        results: list[Path] = []
        for path in self.root.rglob("*"):
            if not path.is_file():
                continue
            if any(part in blocked_parts for part in path.parts):
                continue
            suffix = path.suffix.lower()
            if suffix in IMAGE_EXTS or suffix == LABEL_EXT:
                results.append(path)
        return results

    def _paired_path(self, path: Path, kind: str) -> Path:
        parts = list(path.parts)
        try:
            if kind == "image":
                idx = next(i for i, part in enumerate(parts) if part.lower() == "images")
                parts[idx] = "labels"
                return Path(*parts).with_suffix(LABEL_EXT)
            idx = next(i for i, part in enumerate(parts) if part.lower() == "labels")
            parts[idx] = "images"
            for ext in IMAGE_EXTS:
                candidate = Path(*parts).with_suffix(ext)
                if candidate.exists():
                    return candidate
            return Path(*parts).with_suffix(".jpg")
        except StopIteration:
            return path.with_suffix(LABEL_EXT if kind == "image" else ".jpg")
