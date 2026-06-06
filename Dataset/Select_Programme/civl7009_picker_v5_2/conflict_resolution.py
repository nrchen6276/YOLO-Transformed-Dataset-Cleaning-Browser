from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from .manual_objects import INDEX_NAME, SELECTION_NAME
from .version import CONFLICT_RESOLUTION_SCHEMA, STATUS, UI_VERSION

KEEP_LIKE = {"KEEP", "DONE", "ALL_DONE"}
REMOVE_LIKE = {"REMOVE", "OUT", "ALL_OUT"}
UNRESOLVED_LIKE = {"SKIP", "AMBIGUOUS", "NEEDS_AGENT_CHECK", "UNDECIDED", "PARTIAL", "UNREADABLE", "UNKNOWN"}
EXACT_REASONS = {"SHA256_EXACT_IMAGE", "PIXEL_SHA256_EXACT_IMAGE"}
NEAR_REASONS = {"PHASH_NEAR_STRONG", "DHASH_NEAR_STRONG", "ROTATION_AWARE_PHASH", "COMPOSITE_NEAR_HASH"}


@dataclass
class SourceItemRecord:
    reason: str
    bucket: str
    group_key: str
    group_folder: str
    item_id: str
    dataset_id: str
    source_image_project_path: str
    source_label_project_path: str
    image_sha256: str
    label_sha256: str
    target_group_project_path: str
    target_image_project_path: str
    target_label_project_path: str
    image_filename: str
    label_filename: str
    width: int = 0
    height: int = 0
    label_line_count: int = 0
    label_class_set: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    weak_identity: bool = False

    @property
    def source_object_key(self) -> str:
        if self.source_image_project_path:
            return f"{self.source_image_project_path}|{self.image_sha256}"
        return f"WEAK_IMAGE_SHA256|{self.image_sha256}"

    @property
    def group_identity(self) -> str:
        return f"{self.reason}/{self.bucket}/{self.group_folder}"


@dataclass
class ReasonEventDecision:
    reason: str
    bucket: str
    group_key: str
    group_folder: str
    group_dir: Path
    selection_path: Path
    review_status: str
    schema_version: str
    local_decision_for_source_object: str
    selected_item: SourceItemRecord
    peer_items: list[SourceItemRecord]
    keep_item_ids: list[str]
    remove_item_ids: list[str]
    unresolved_reason: str = ""

    @property
    def group_identity(self) -> str:
        return f"{self.reason}/{self.bucket}/{self.group_folder}"


@dataclass
class SourceObjectConflict:
    source_object_key: str
    source_image_project_path: str
    image_sha256: str
    source_label_project_path: str = ""
    label_sha256: str = ""
    dataset_id: str = ""
    image_filename: str = ""
    events: list[ReasonEventDecision] = field(default_factory=list)
    conflict_state: str = "UNRESOLVED_OR_PARTIAL"
    keep_event_count: int = 0
    remove_event_count: int = 0
    unresolved_event_count: int = 0
    weak_identity: bool = False
    group_signature_conflict: bool = False
    exact_near_conflict: bool = False
    resolution: dict[str, Any] | None = None

    @property
    def related_event_count(self) -> int:
        return len(self.events)

    @property
    def reason_set(self) -> list[str]:
        return sorted({event.reason for event in self.events})

    @property
    def group_key_set(self) -> list[str]:
        return sorted({event.group_key for event in self.events})


@dataclass
class ConflictIndex:
    root: Path
    objects: list[SourceObjectConflict]
    source_map: dict[str, SourceObjectConflict]
    row_count: int
    selection_count: int
    duration_ms: float
    issues: list[str] = field(default_factory=list)


@dataclass
class ConflictResolutionResult:
    path: Path
    index_path: Path
    verified: bool


def _split_classes(value: str) -> list[str]:
    text = str(value or "").strip()
    if not text:
        return []
    if "|" in text:
        return [part for part in text.split("|") if part]
    if "," in text:
        return [part.strip() for part in text.split(",") if part.strip()]
    return [text]


def _json_metrics(value: str) -> dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _safe_id(source_object_key: str) -> str:
    return hashlib.sha256(source_object_key.encode("utf-8")).hexdigest()[:24]


class ConflictAwarenessService:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.index_path = self.root / "_indexes" / INDEX_NAME
        self.resolution_root = self.root / "_conflict_resolutions"
        self.resolution_index_path = self.root / "_indexes" / "manual_objects_conflict_resolution_index.csv"
        self.item_records: dict[tuple[str, str], SourceItemRecord] = {}
        self.group_items: dict[str, list[SourceItemRecord]] = {}
        self.latest_index: ConflictIndex | None = None

    def build_index(self) -> ConflictIndex:
        started = time.perf_counter()
        issues: list[str] = []
        self.item_records, self.group_items, row_count = self._load_source_records()
        object_events: dict[str, list[ReasonEventDecision]] = {}
        selection_count = 0
        for selection_path in self.root.rglob(SELECTION_NAME):
            if "_selection_history" in selection_path.parts:
                continue
            selection_count += 1
            try:
                selection = json.loads(selection_path.read_text(encoding="utf-8"))
            except Exception as exc:
                issues.append(f"SELECTION_JSON_INVALID: {selection_path}: {exc}")
                continue
            group_key = str(selection.get("group_key", ""))
            review_status = str(selection.get("review_status", "UNKNOWN"))
            keep_ids = [str(item) for item in (selection.get("selected_keep_item_ids", []) or [])]
            remove_ids = [str(item) for item in (selection.get("selected_remove_item_ids", []) or [])]
            group_records = self.group_items.get(group_key, [])
            if not group_records:
                issues.append(f"GROUP_NOT_IN_INDEX: {group_key}: {selection_path}")
                continue
            if review_status == "ALL_OUT":
                keep_ids = []
                remove_ids = [record.item_id for record in group_records]
            if review_status == "ALL_DONE":
                keep_ids = [record.item_id for record in group_records]
                remove_ids = []
            known_ids = {record.item_id for record in group_records}
            local_by_item: dict[str, str] = {}
            for item_id in keep_ids:
                local_by_item[item_id] = "KEEP"
            for item_id in remove_ids:
                local_by_item[item_id] = "REMOVE"
            if review_status in {"SKIP", "AMBIGUOUS", "NEEDS_AGENT_CHECK"}:
                for record in group_records:
                    local_by_item.setdefault(record.item_id, review_status)
            for item_id in sorted(known_ids - set(local_by_item)):
                local_by_item[item_id] = "PARTIAL"
            if not local_by_item:
                issues.append(f"SELECTION_EMPTY: {group_key}: {selection_path}")
                continue
            group_dir = selection_path.parent
            for record in group_records:
                local_decision = local_by_item.get(record.item_id, "UNKNOWN")
                peer_items = [peer for peer in group_records if peer.item_id != record.item_id]
                event = ReasonEventDecision(
                    reason=record.reason,
                    bucket=record.bucket,
                    group_key=record.group_key,
                    group_folder=record.group_folder,
                    group_dir=group_dir,
                    selection_path=selection_path,
                    review_status=review_status,
                    schema_version=str(selection.get("schema_version", "")),
                    local_decision_for_source_object=local_decision,
                    selected_item=record,
                    peer_items=peer_items,
                    keep_item_ids=sorted(set(keep_ids) & known_ids),
                    remove_item_ids=sorted(set(remove_ids) & known_ids),
                    unresolved_reason="" if local_decision in KEEP_LIKE | REMOVE_LIKE else local_decision,
                )
                object_events.setdefault(record.source_object_key, []).append(event)
        objects = [self._build_conflict_object(source_key, events) for source_key, events in object_events.items()]
        resolution_map = self._load_existing_resolutions()
        for conflict in objects:
            conflict.resolution = resolution_map.get(conflict.source_object_key)
        objects.sort(key=self._object_sort_key)
        source_map = {obj.source_object_key: obj for obj in objects}
        result = ConflictIndex(
            root=self.root,
            objects=objects,
            source_map=source_map,
            row_count=row_count,
            selection_count=selection_count,
            duration_ms=(time.perf_counter() - started) * 1000,
            issues=issues,
        )
        self.latest_index = result
        return result

    def _load_source_records(self) -> tuple[dict[tuple[str, str], SourceItemRecord], dict[str, list[SourceItemRecord]], int]:
        records: dict[tuple[str, str], SourceItemRecord] = {}
        group_items: dict[str, list[SourceItemRecord]] = {}
        row_count = 0
        if not self.index_path.exists():
            return records, group_items, row_count
        with self.index_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                row_count += 1
                group_key = str(row.get("group_key", ""))
                item_id = str(row.get("item_id", ""))
                if not group_key or not item_id:
                    continue
                record = SourceItemRecord(
                    reason=str(row.get("reason", "")),
                    bucket=str(row.get("duplicate_count_bucket", "")),
                    group_key=group_key,
                    group_folder=str(row.get("group_folder", "")),
                    item_id=item_id,
                    dataset_id=str(row.get("dataset_id", "")),
                    source_image_project_path=str(row.get("source_image_project_path", "")),
                    source_label_project_path=str(row.get("source_label_project_path", "")),
                    image_sha256=str(row.get("image_sha256", "")),
                    label_sha256=str(row.get("label_sha256", "")),
                    target_group_project_path=str(row.get("target_group_project_path", "")),
                    target_image_project_path=str(row.get("target_image_project_path", "")),
                    target_label_project_path=str(row.get("target_label_project_path", "")),
                    image_filename=str(row.get("image_filename", "")),
                    label_filename=str(row.get("label_filename", "")),
                    width=int(row.get("width") or 0),
                    height=int(row.get("height") or 0),
                    label_line_count=int(row.get("label_line_count") or 0),
                    label_class_set=_split_classes(str(row.get("label_class_set", ""))),
                    metrics=_json_metrics(str(row.get("metrics_json", ""))),
                    weak_identity=not bool(str(row.get("source_image_project_path", ""))),
                )
                records[(group_key, item_id)] = record
                group_items.setdefault(group_key, []).append(record)
        return records, group_items, row_count

    def refresh_source_object(self, source_object_key: str) -> SourceObjectConflict | None:
        """Reread only one source object's related selection files.

        This is intentionally narrower than build_index(): it avoids a global
        Manual_Objects scan when the user has just re-reviewed one evidence
        event and wants the current object-level state to catch up.
        """
        if not source_object_key:
            return None
        if not self.group_items or not self.item_records:
            self.item_records, self.group_items, row_count = self._load_source_records()
        else:
            row_count = sum(len(items) for items in self.group_items.values())
        related_records = [record for record in self.item_records.values() if record.source_object_key == source_object_key]
        if not related_records:
            if self.latest_index is not None:
                self.latest_index.source_map.pop(source_object_key, None)
                self.latest_index.objects = [obj for obj in self.latest_index.objects if obj.source_object_key != source_object_key]
            return None
        events: list[ReasonEventDecision] = []
        seen_groups = sorted({record.group_key for record in related_records})
        for group_key in seen_groups:
            group_records = self.group_items.get(group_key, [])
            if not group_records:
                continue
            selection_path = self._selection_path_for_group(group_records)
            selection: dict[str, Any] | None = None
            unreadable_reason = ""
            if selection_path.exists():
                try:
                    selection = json.loads(selection_path.read_text(encoding="utf-8"))
                except Exception as exc:
                    unreadable_reason = f"UNREADABLE: {exc}"
            else:
                unreadable_reason = "MISSING_SELECTION"
            events.extend(
                self._events_for_group_selection(
                    group_key=group_key,
                    group_records=group_records,
                    selection_path=selection_path,
                    selection=selection,
                    source_key_filter=source_object_key,
                    unreadable_reason=unreadable_reason,
                )
            )
        if not events:
            return None
        conflict = self._build_conflict_object(source_object_key, events)
        conflict.resolution = self._load_existing_resolutions().get(source_object_key)
        self._replace_latest_object(conflict, row_count=row_count)
        return conflict

    def _selection_path_for_group(self, group_records: list[SourceItemRecord]) -> Path:
        first = group_records[0]
        return self.root / first.reason / first.bucket / first.group_folder / SELECTION_NAME

    def _events_for_group_selection(
        self,
        group_key: str,
        group_records: list[SourceItemRecord],
        selection_path: Path,
        selection: dict[str, Any] | None,
        source_key_filter: str = "",
        unreadable_reason: str = "",
    ) -> list[ReasonEventDecision]:
        review_status = str((selection or {}).get("review_status", "UNKNOWN"))
        schema_version = str((selection or {}).get("schema_version", ""))
        keep_ids = [str(item) for item in ((selection or {}).get("selected_keep_item_ids", []) or [])]
        remove_ids = [str(item) for item in ((selection or {}).get("selected_remove_item_ids", []) or [])]
        if unreadable_reason:
            review_status = unreadable_reason
            keep_ids = []
            remove_ids = []
        if review_status == "ALL_OUT":
            keep_ids = []
            remove_ids = [record.item_id for record in group_records]
        if review_status == "ALL_DONE":
            keep_ids = [record.item_id for record in group_records]
            remove_ids = []
        known_ids = {record.item_id for record in group_records}
        local_by_item: dict[str, str] = {}
        for item_id in keep_ids:
            local_by_item[item_id] = "KEEP"
        for item_id in remove_ids:
            local_by_item[item_id] = "REMOVE"
        if review_status in {"SKIP", "AMBIGUOUS", "NEEDS_AGENT_CHECK"}:
            for record in group_records:
                local_by_item.setdefault(record.item_id, review_status)
        if unreadable_reason:
            for record in group_records:
                local_by_item.setdefault(record.item_id, unreadable_reason)
        for item_id in sorted(known_ids - set(local_by_item)):
            local_by_item[item_id] = "PARTIAL"
        target_records = [
            record for record in group_records
            if not source_key_filter or record.source_object_key == source_key_filter
        ]
        events: list[ReasonEventDecision] = []
        for record in target_records:
            local_decision = local_by_item.get(record.item_id, "UNKNOWN")
            peer_items = [peer for peer in group_records if peer.item_id != record.item_id]
            events.append(
                ReasonEventDecision(
                    reason=record.reason,
                    bucket=record.bucket,
                    group_key=record.group_key,
                    group_folder=record.group_folder,
                    group_dir=selection_path.parent,
                    selection_path=selection_path,
                    review_status=review_status,
                    schema_version=schema_version,
                    local_decision_for_source_object=local_decision,
                    selected_item=record,
                    peer_items=peer_items,
                    keep_item_ids=sorted(set(keep_ids) & known_ids),
                    remove_item_ids=sorted(set(remove_ids) & known_ids),
                    unresolved_reason="" if local_decision in KEEP_LIKE | REMOVE_LIKE else local_decision,
                )
            )
        return events

    def _replace_latest_object(self, conflict: SourceObjectConflict, row_count: int = 0) -> None:
        if self.latest_index is None:
            self.latest_index = ConflictIndex(
                root=self.root,
                objects=[],
                source_map={},
                row_count=row_count,
                selection_count=0,
                duration_ms=0.0,
                issues=[],
            )
        self.latest_index.source_map[conflict.source_object_key] = conflict
        replaced = False
        objects: list[SourceObjectConflict] = []
        for obj in self.latest_index.objects:
            if obj.source_object_key == conflict.source_object_key:
                if not replaced:
                    objects.append(conflict)
                    replaced = True
            else:
                objects.append(obj)
        if not replaced:
            objects.append(conflict)
        objects.sort(key=self._object_sort_key)
        self.latest_index.objects = objects

    def _build_conflict_object(self, source_key: str, events: list[ReasonEventDecision]) -> SourceObjectConflict:
        first = events[0].selected_item
        keep = sum(1 for event in events if event.local_decision_for_source_object in KEEP_LIKE)
        remove = sum(1 for event in events if event.local_decision_for_source_object in REMOVE_LIKE)
        unresolved = len(events) - keep - remove
        group_signature_conflict = self._has_group_signature_conflict(events)
        exact_near_conflict = self._has_exact_near_conflict(events)
        if keep and remove:
            state = "CONFLICT_KEEP_REMOVE"
        elif group_signature_conflict:
            state = "GROUP_SIGNATURE_CONFLICT"
        elif unresolved:
            state = "UNRESOLVED_OR_PARTIAL"
        elif remove:
            state = "CONSISTENT_REMOVE"
        elif keep:
            state = "CONSISTENT_KEEP"
        else:
            state = "UNRESOLVED_OR_PARTIAL"
        if first.weak_identity and state not in {"CONFLICT_KEEP_REMOVE", "GROUP_SIGNATURE_CONFLICT"}:
            state = "UNRESOLVED_OR_PARTIAL"
        return SourceObjectConflict(
            source_object_key=source_key,
            source_image_project_path=first.source_image_project_path,
            image_sha256=first.image_sha256,
            source_label_project_path=first.source_label_project_path,
            label_sha256=first.label_sha256,
            dataset_id=first.dataset_id,
            image_filename=first.image_filename,
            events=events,
            conflict_state=state,
            keep_event_count=keep,
            remove_event_count=remove,
            unresolved_event_count=unresolved,
            weak_identity=first.weak_identity,
            group_signature_conflict=group_signature_conflict,
            exact_near_conflict=exact_near_conflict,
        )

    @staticmethod
    def _has_group_signature_conflict(events: list[ReasonEventDecision]) -> bool:
        signatures_by_set: dict[tuple[str, ...], set[tuple[tuple[str, ...], tuple[str, ...]]]] = {}
        for event in events:
            records = [event.selected_item] + event.peer_items
            by_item_id = {record.item_id: record for record in records}
            source_set = tuple(sorted(record.source_object_key for record in records))
            keep_sources = tuple(sorted(by_item_id[item_id].source_object_key for item_id in event.keep_item_ids if item_id in by_item_id))
            remove_sources = tuple(sorted(by_item_id[item_id].source_object_key for item_id in event.remove_item_ids if item_id in by_item_id))
            signature = (keep_sources, remove_sources)
            signatures_by_set.setdefault(source_set, set()).add(signature)
        return any(len(signatures) > 1 for signatures in signatures_by_set.values())

    @staticmethod
    def _has_exact_near_conflict(events: list[ReasonEventDecision]) -> bool:
        exact_decisions = {event.local_decision_for_source_object for event in events if event.reason in EXACT_REASONS}
        near_decisions = {event.local_decision_for_source_object for event in events if event.reason in NEAR_REASONS}
        return bool((exact_decisions & KEEP_LIKE and near_decisions & REMOVE_LIKE) or (exact_decisions & REMOVE_LIKE and near_decisions & KEEP_LIKE))

    @staticmethod
    def _object_sort_key(obj: SourceObjectConflict) -> tuple[int, int, str, str]:
        priority = {
            "CONFLICT_KEEP_REMOVE": 0,
            "GROUP_SIGNATURE_CONFLICT": 1,
            "UNRESOLVED_OR_PARTIAL": 2,
            "CONSISTENT_REMOVE": 3,
            "CONSISTENT_KEEP": 4,
        }
        return (priority.get(obj.conflict_state, 9), -obj.related_event_count, obj.dataset_id, obj.image_filename)

    def _load_existing_resolutions(self) -> dict[str, dict[str, Any]]:
        results: dict[str, dict[str, Any]] = {}
        if not self.resolution_root.exists():
            return results
        for path in self.resolution_root.rglob("conflict_resolution.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            source_key = str(data.get("source_object_key", ""))
            if source_key:
                results[source_key] = data
        return results

    def conflict_for_item(self, group_key: str, item_id: str) -> SourceObjectConflict | None:
        if self.latest_index is None:
            return None
        record = self.item_records.get((group_key, item_id))
        if record is None:
            return None
        return self.latest_index.source_map.get(record.source_object_key)

    def proposed_conflict_warnings(self, group_key: str, decisions: dict[str, str]) -> list[str]:
        warnings: list[str] = []
        for item_id, decision in decisions.items():
            current = self.conflict_for_item(group_key, item_id)
            if current is None:
                continue
            existing_keep = current.keep_event_count
            existing_remove = current.remove_event_count
            if decision in KEEP_LIKE and existing_remove:
                warnings.append(f"{item_id}: 当前 KEEP 会与已有 {existing_remove} 个 remove-like reason 冲突。")
            if decision in REMOVE_LIKE and existing_keep:
                warnings.append(f"{item_id}: 当前 REMOVE/ALL_OUT 会与已有 {existing_keep} 个 keep-like reason 冲突。")
        return warnings

    def explanation_for(self, conflict: SourceObjectConflict | None) -> str:
        if conflict is None:
            return "冲突状态：待索引。当前对象尚未进入冲突索引，保存前仍会按本组选择执行校验。"
        lines = [
            f"冲突状态：{conflict.conflict_state}",
            f"相关 reason 事件：{conflict.related_event_count}；keep-like={conflict.keep_event_count}；remove-like={conflict.remove_event_count}；unresolved={conflict.unresolved_event_count}",
            f"Source object: {conflict.source_image_project_path or conflict.image_sha256}",
        ]
        if conflict.conflict_state == "CONSISTENT_KEEP":
            lines.append("说明：所有已知 reason 级选择均倾向保留；后续治理仍应保留 provenance。")
        elif conflict.conflict_state == "CONSISTENT_REMOVE":
            lines.append("说明：所有已知 reason 级选择均倾向移除或 ALL_OUT。")
        elif conflict.conflict_state == "CONFLICT_KEEP_REMOVE":
            lines.append("说明：该对象同时出现 keep-like 与 remove-like 决策，后续必须进入对象级冲突复核。")
        elif conflict.conflict_state == "GROUP_SIGNATURE_CONFLICT":
            lines.append("说明：同一候选集合跨 reason 的 keep/remove 签名不一致，应在冲突复核页确认。")
        elif conflict.conflict_state == "UNRESOLVED_OR_PARTIAL":
            lines.append("说明：相关选择缺失、部分覆盖或处于 SKIP/AMBIGUOUS/NEEDS_AGENT_CHECK 等未解决状态。")
        if conflict.weak_identity:
            lines.append("弱身份提醒：缺少 source_image_project_path，仅能用 image SHA256 回退身份。")
        if conflict.exact_near_conflict:
            lines.append("Exact-vs-near 提醒：exact-hash reason 与 near-hash reason 存在相反倾向。")
        if conflict.resolution:
            lines.append(f"已有对象级 resolution：{conflict.resolution.get('final_object_decision', '')} @ {conflict.resolution.get('reviewed_at', '')}")
        return "\n".join(lines)

    def write_resolution(
        self,
        conflict: SourceObjectConflict,
        final_decision: str,
        reviewer: str = "",
        confidence: str = "MEDIUM",
        notes: str = "",
        decision_rationale: str = "",
        canonical_group_key: str = "",
    ) -> ConflictResolutionResult:
        if final_decision not in {
            "KEEP_SOURCE_OBJECT",
            "REMOVE_SOURCE_OBJECT",
            "ALL_OUT_SOURCE_OBJECT",
            "DEFER_REVIEW",
            "NEEDS_AGENT_CHECK",
            "SPLIT_CONTEXT_REQUIRED",
        }:
            raise ValueError(f"Unknown final object decision: {final_decision}")
        safe_id = _safe_id(conflict.source_object_key)
        resolution_dir = self.resolution_root / safe_id
        resolution_dir.mkdir(parents=True, exist_ok=True)
        target = resolution_dir / "conflict_resolution.json"
        if target.exists():
            history_dir = resolution_dir / "_history"
            history_dir.mkdir(exist_ok=True)
            shutil.copy2(target, history_dir / f"conflict_resolution_{datetime.now().strftime('%Y%m%d%H%M%S')}.json")
        payload = {
            "schema_version": CONFLICT_RESOLUTION_SCHEMA,
            "claim_status": STATUS,
            "source_object_key": conflict.source_object_key,
            "source_image_project_path": conflict.source_image_project_path,
            "image_sha256": conflict.image_sha256,
            "source_label_project_path": conflict.source_label_project_path,
            "label_sha256": conflict.label_sha256,
            "conflict_state": conflict.conflict_state,
            "final_object_decision": final_decision,
            "reviewer": reviewer,
            "reviewed_at": datetime.now().isoformat(timespec="seconds"),
            "software_version": UI_VERSION,
            "confidence": confidence,
            "notes": notes,
            "decision_rationale": decision_rationale,
            "canonical_group_key": canonical_group_key,
            "related_events": [self._event_payload(event) for event in conflict.events],
            "audit": {
                "created_by": "source_group_picker",
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "readback_verified": False,
            },
        }
        fd, tmp_name = tempfile.mkstemp(prefix="conflict_resolution_", suffix=".json.tmp", dir=str(resolution_dir))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
            os.replace(tmp_name, target)
        finally:
            tmp_path = Path(tmp_name)
            if tmp_path.exists():
                tmp_path.unlink()
        self._verify_resolution(target, payload)
        payload["audit"]["readback_verified"] = True
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self._verify_resolution(target, payload)
        self.update_resolution_index(conflict, payload, target)
        return ConflictResolutionResult(target, self.resolution_index_path, True)

    @staticmethod
    def _event_payload(event: ReasonEventDecision) -> dict[str, Any]:
        return {
            "reason": event.reason,
            "bucket": event.bucket,
            "group_key": event.group_key,
            "group_folder": event.group_folder,
            "selection_project_path": str(event.selection_path),
            "local_decision_for_source_object": event.local_decision_for_source_object,
            "local_review_status": event.review_status,
            "peer_items": [
                {
                    "item_id": peer.item_id,
                    "dataset_id": peer.dataset_id,
                    "source_image_project_path": peer.source_image_project_path,
                    "local_decision": "KEEP" if peer.item_id in event.keep_item_ids else "REMOVE" if peer.item_id in event.remove_item_ids else "UNRESOLVED",
                }
                for peer in event.peer_items
            ],
        }

    @staticmethod
    def _verify_resolution(path: Path, expected: dict[str, Any]) -> None:
        data = json.loads(path.read_text(encoding="utf-8"))
        checks = ["source_object_key", "source_image_project_path", "image_sha256", "final_object_decision", "reviewer", "reviewed_at"]
        problems = [field for field in checks if str(data.get(field, "")) != str(expected.get(field, ""))]
        if len(data.get("related_events", []) or []) != len(expected.get("related_events", []) or []):
            problems.append("related_events")
        if problems:
            raise RuntimeError("conflict_resolution.json readback verification failed: " + ", ".join(problems))

    def update_resolution_index(self, conflict: SourceObjectConflict, payload: dict[str, Any], path: Path) -> None:
        self.resolution_index_path.parent.mkdir(parents=True, exist_ok=True)
        rows: list[dict[str, str]] = []
        headers = [
            "source_object_key",
            "source_image_project_path",
            "image_sha256",
            "conflict_state",
            "final_object_decision",
            "reviewer",
            "reviewed_at",
            "resolution_json_project_path",
            "related_event_count",
            "keep_event_count",
            "remove_event_count",
            "reason_set",
            "group_key_set",
            "software_version",
            "claim_status",
        ]
        if self.resolution_index_path.exists():
            with self.resolution_index_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    if row.get("source_object_key") != conflict.source_object_key:
                        rows.append({key: row.get(key, "") for key in headers})
        rows.append(
            {
                "source_object_key": conflict.source_object_key,
                "source_image_project_path": conflict.source_image_project_path,
                "image_sha256": conflict.image_sha256,
                "conflict_state": conflict.conflict_state,
                "final_object_decision": str(payload.get("final_object_decision", "")),
                "reviewer": str(payload.get("reviewer", "")),
                "reviewed_at": str(payload.get("reviewed_at", "")),
                "resolution_json_project_path": str(path),
                "related_event_count": str(conflict.related_event_count),
                "keep_event_count": str(conflict.keep_event_count),
                "remove_event_count": str(conflict.remove_event_count),
                "reason_set": "|".join(conflict.reason_set),
                "group_key_set": "|".join(conflict.group_key_set),
                "software_version": UI_VERSION,
                "claim_status": STATUS,
            }
        )
        with self.resolution_index_path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)

    def export_gate_summary(self, destination: Path) -> Path:
        index = self.latest_index or self.build_index()
        counts: dict[str, int] = {}
        resolved = 0
        for obj in index.objects:
            counts[obj.conflict_state] = counts.get(obj.conflict_state, 0) + 1
            if obj.resolution:
                resolved += 1
        blocked = [
            {
                "source_object_key": obj.source_object_key,
                "source_image_project_path": obj.source_image_project_path,
                "conflict_state": obj.conflict_state,
                "related_event_count": obj.related_event_count,
            }
            for obj in index.objects
            if obj.conflict_state in {"CONFLICT_KEEP_REMOVE", "GROUP_SIGNATURE_CONFLICT", "UNRESOLVED_OR_PARTIAL"} and not obj.resolution
        ]
        payload = {
            "schema_version": "CIVL7009_MANUAL_OBJECTS_SOURCE_GOVERNANCE_GATE_SUMMARY_V1",
            "claim_status": STATUS,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "software_version": UI_VERSION,
            "manual_objects_root": str(self.root),
            "counts": counts,
            "resolved_count": resolved,
            "blocked_count": len(blocked),
            "blocked_objects": blocked,
        }
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return destination
