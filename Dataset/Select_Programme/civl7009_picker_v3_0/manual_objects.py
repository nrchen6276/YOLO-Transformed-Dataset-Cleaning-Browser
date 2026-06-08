from __future__ import annotations

import json
import os
import shutil
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from .version import MANUAL_SELECTION_SCHEMA, UI_VERSION

MANIFEST_NAME = "group_manifest.json"
SELECTION_NAME = "manual_selection.json"
CLAIM_STATUS = "PENDING_AUDIT"
REVIEW_STATUSES = {"APPROVED", "SKIP", "AMBIGUOUS", "NEEDS_AGENT_CHECK"}
REQUIRED_MANIFEST_FIELDS = {"schema_version", "group_key", "reason", "group_size", "dataset_ids", "claim_status", "items"}
REQUIRED_ITEM_FIELDS = {
    "item_id",
    "dataset_id",
    "image_filename",
    "label_filename",
    "image_path_relative_to_group",
    "label_path_relative_to_group",
    "source_image_project_path",
    "source_label_project_path",
    "image_sha256",
    "label_sha256",
    "width",
    "height",
    "label_line_count",
    "label_class_set",
    "metrics",
}


def sha256_file(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass
class ManualObjectsIssue:
    severity: str
    code: str
    message: str
    group_dir: Path
    item_id: str = ""


@dataclass
class ManualObjectItem:
    item_id: str
    dataset_id: str
    image_filename: str
    label_filename: str
    image_path: Path
    label_path: Path
    source_image_project_path: str
    source_label_project_path: str
    image_sha256: str
    label_sha256: str
    width: int
    height: int
    label_line_count: int
    label_class_set: list[Any]
    metrics: dict[str, Any]
    selection_state: str = "UNDECIDED"


@dataclass
class ManualObjectGroup:
    group_dir: Path
    reason: str
    size_bucket: str
    group_name: str
    schema_version: str = ""
    group_key: str = ""
    group_size: int = 0
    dataset_ids: list[str] = field(default_factory=list)
    claim_status: str = CLAIM_STATUS
    items: list[ManualObjectItem] = field(default_factory=list)
    issues: list[ManualObjectsIssue] = field(default_factory=list)
    selection: dict[str, Any] | None = None

    @property
    def can_write_selection(self) -> bool:
        return not any(issue.severity == "ERROR" for issue in self.issues)

    @property
    def review_status(self) -> str:
        if self.selection:
            return str(self.selection.get("review_status", ""))
        return "未复核"


class ManualObjectsService:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def list_groups(self) -> list[ManualObjectGroup]:
        groups: list[ManualObjectGroup] = []
        if not self.root.exists() or not self.root.is_dir():
            return groups
        for reason_dir in sorted([p for p in self.root.iterdir() if p.is_dir() and not p.name.startswith("_")], key=lambda p: p.name.lower()):
            for bucket_dir in sorted([p for p in reason_dir.iterdir() if p.is_dir()], key=lambda p: p.name.lower()):
                for group_dir in sorted([p for p in bucket_dir.iterdir() if p.is_dir()], key=lambda p: p.name.lower()):
                    groups.append(self.load_group(group_dir))
        return groups

    def load_group(self, group_dir: Path) -> ManualObjectGroup:
        group_dir = group_dir.resolve()
        reason = group_dir.parent.parent.name if len(group_dir.parents) >= 2 else ""
        size_bucket = group_dir.parent.name if group_dir.parent else ""
        group = ManualObjectGroup(group_dir=group_dir, reason=reason, size_bucket=size_bucket, group_name=group_dir.name)
        manifest_path = group_dir / MANIFEST_NAME
        if not manifest_path.exists():
            group.issues.append(ManualObjectsIssue("ERROR", "MANIFEST_MISSING", "缺少 group_manifest.json。", group_dir))
            group.selection = self.load_selection_if_any(group_dir, group.issues)
            return group
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception as exc:
            group.issues.append(ManualObjectsIssue("ERROR", "MANIFEST_JSON_INVALID", f"group_manifest.json 无法解析: {exc}", group_dir))
            group.selection = self.load_selection_if_any(group_dir, group.issues)
            return group

        missing_fields = sorted(REQUIRED_MANIFEST_FIELDS - set(manifest))
        for field_name in missing_fields:
            group.issues.append(ManualObjectsIssue("ERROR", "MANIFEST_FIELD_MISSING", f"manifest 缺少字段: {field_name}", group_dir))
        group.schema_version = str(manifest.get("schema_version", ""))
        group.group_key = str(manifest.get("group_key", group_dir.name))
        group.group_size = int(manifest.get("group_size", 0) or 0)
        group.dataset_ids = list(manifest.get("dataset_ids", []) or [])
        group.claim_status = str(manifest.get("claim_status", CLAIM_STATUS))
        if group.claim_status != CLAIM_STATUS:
            group.issues.append(ManualObjectsIssue("WARN", "CLAIM_STATUS_NOT_PENDING_AUDIT", f"claim_status 应保持 {CLAIM_STATUS}: {group.claim_status}", group_dir))

        raw_items = manifest.get("items", [])
        if not isinstance(raw_items, list):
            group.issues.append(ManualObjectsIssue("ERROR", "ITEMS_NOT_LIST", "manifest.items 必须是 list。", group_dir))
            raw_items = []
        seen_item_ids: set[str] = set()
        for raw in raw_items:
            if not isinstance(raw, dict):
                group.issues.append(ManualObjectsIssue("ERROR", "ITEM_NOT_OBJECT", "items[] 中存在非 object 项。", group_dir))
                continue
            item_id = str(raw.get("item_id", ""))
            if not item_id:
                group.issues.append(ManualObjectsIssue("ERROR", "ITEM_ID_MISSING", "item 缺少 item_id。", group_dir))
                continue
            if item_id in seen_item_ids:
                group.issues.append(ManualObjectsIssue("ERROR", "ITEM_ID_DUPLICATE", f"item_id 重复: {item_id}", group_dir, item_id))
                continue
            seen_item_ids.add(item_id)
            for field_name in sorted(REQUIRED_ITEM_FIELDS - set(raw)):
                group.issues.append(ManualObjectsIssue("ERROR", "ITEM_FIELD_MISSING", f"{item_id} 缺少字段: {field_name}", group_dir, item_id))
            image_path = group_dir / str(raw.get("image_path_relative_to_group", raw.get("image_filename", "")))
            label_path = group_dir / str(raw.get("label_path_relative_to_group", raw.get("label_filename", "")))
            if not image_path.exists():
                group.issues.append(ManualObjectsIssue("ERROR", "IMAGE_MISSING", f"{item_id} 图片不存在: {image_path.name}", group_dir, item_id))
            elif raw.get("image_sha256"):
                actual = sha256_file(image_path)
                if actual.casefold() != str(raw.get("image_sha256")).casefold():
                    group.issues.append(ManualObjectsIssue("ERROR", "IMAGE_SHA256_MISMATCH", f"{item_id} 图片 SHA256 与 manifest 不一致。", group_dir, item_id))
            if not label_path.exists():
                group.issues.append(ManualObjectsIssue("ERROR", "LABEL_MISSING", f"{item_id} 标签不存在: {label_path.name}", group_dir, item_id))
            elif raw.get("label_sha256"):
                actual = sha256_file(label_path)
                if actual.casefold() != str(raw.get("label_sha256")).casefold():
                    group.issues.append(ManualObjectsIssue("ERROR", "LABEL_SHA256_MISMATCH", f"{item_id} 标签 SHA256 与 manifest 不一致。", group_dir, item_id))
            group.items.append(
                ManualObjectItem(
                    item_id=item_id,
                    dataset_id=str(raw.get("dataset_id", "")),
                    image_filename=str(raw.get("image_filename", image_path.name)),
                    label_filename=str(raw.get("label_filename", label_path.name)),
                    image_path=image_path,
                    label_path=label_path,
                    source_image_project_path=str(raw.get("source_image_project_path", "")),
                    source_label_project_path=str(raw.get("source_label_project_path", "")),
                    image_sha256=str(raw.get("image_sha256", "")),
                    label_sha256=str(raw.get("label_sha256", "")),
                    width=int(raw.get("width", 0) or 0),
                    height=int(raw.get("height", 0) or 0),
                    label_line_count=int(raw.get("label_line_count", 0) or 0),
                    label_class_set=list(raw.get("label_class_set", []) or []),
                    metrics=dict(raw.get("metrics", {}) or {}),
                )
            )
        if group.group_size and len(group.items) != group.group_size:
            group.issues.append(ManualObjectsIssue("WARN", "GROUP_SIZE_MISMATCH", f"group_size={group.group_size}，items={len(group.items)}。", group_dir))
        group.selection = self.load_selection_if_any(group_dir, group.issues)
        self.apply_selection_to_items(group)
        return group

    def load_selection_if_any(self, group_dir: Path, issues: list[ManualObjectsIssue]) -> dict[str, Any] | None:
        path = group_dir / SELECTION_NAME
        if not path.exists():
            return None
        try:
            selection = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            issues.append(ManualObjectsIssue("ERROR", "SELECTION_JSON_INVALID", f"manual_selection.json 无法解析: {exc}", group_dir))
            return None
        if selection.get("schema_version") != MANUAL_SELECTION_SCHEMA:
            issues.append(ManualObjectsIssue("WARN", "SELECTION_SCHEMA_UNKNOWN", f"selection schema 不匹配: {selection.get('schema_version')}", group_dir))
        return selection

    @staticmethod
    def apply_selection_to_items(group: ManualObjectGroup) -> None:
        if not group.selection:
            return
        keep = set(group.selection.get("selected_keep_item_ids", []) or [])
        remove = set(group.selection.get("selected_remove_item_ids", []) or [])
        for item in group.items:
            if item.item_id in keep:
                item.selection_state = "KEEP"
            elif item.item_id in remove:
                item.selection_state = "REMOVE"
            else:
                item.selection_state = "UNDECIDED"

    def save_selection(
        self,
        group: ManualObjectGroup,
        review_status: str,
        keep_item_ids: list[str],
        remove_item_ids: list[str],
        reviewer: str = "",
        notes: str = "",
    ) -> Path:
        if review_status not in REVIEW_STATUSES:
            raise ValueError(f"未知 review_status: {review_status}")
        if not group.can_write_selection:
            raise RuntimeError("当前组存在阻断异常，禁止写入 manual_selection.json。")
        known_ids = {item.item_id for item in group.items}
        keep_set = set(keep_item_ids)
        remove_set = set(remove_item_ids)
        unknown = sorted((keep_set | remove_set) - known_ids)
        if unknown:
            raise ValueError(f"selection 包含未知 item_id: {unknown}")
        if keep_set & remove_set:
            raise ValueError("同一 item_id 不能同时位于 keep/remove。")
        if review_status == "APPROVED":
            undecided = sorted(known_ids - keep_set - remove_set)
            if not keep_set:
                raise ValueError("APPROVED 至少需要一个 keep item。")
            if undecided:
                raise ValueError(f"APPROVED 不允许存在未决 item: {undecided}")
        if review_status == "SKIP" and not notes:
            notes = "Reviewer skipped this candidate group."
        payload = {
            "schema_version": MANUAL_SELECTION_SCHEMA,
            "group_key": group.group_key,
            "review_status": review_status,
            "selected_keep_item_ids": sorted(keep_set),
            "selected_remove_item_ids": sorted(remove_set),
            "reviewer": reviewer,
            "reviewed_at": datetime.now().isoformat(timespec="seconds"),
            "software_version": UI_VERSION,
            "notes": notes,
        }
        target = group.group_dir / SELECTION_NAME
        if target.exists():
            history_dir = group.group_dir / "_selection_history"
            history_dir.mkdir(exist_ok=True)
            history_name = f"manual_selection_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
            shutil.copy2(target, history_dir / history_name)
        fd, tmp_name = tempfile.mkstemp(prefix="manual_selection_", suffix=".json.tmp", dir=str(group.group_dir))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
            os.replace(tmp_name, target)
        finally:
            tmp_path = Path(tmp_name)
            if tmp_path.exists():
                tmp_path.unlink()
        group.selection = payload
        self.apply_selection_to_items(group)
        return target

    def export_selection_summary(self, destination: Path) -> Path:
        rows: list[dict[str, Any]] = []
        for group in self.list_groups():
            rows.append(
                {
                    "reason": group.reason,
                    "size_bucket": group.size_bucket,
                    "group_name": group.group_name,
                    "group_key": group.group_key,
                    "review_status": group.review_status,
                    "issue_count": len(group.issues),
                    "can_write_selection": group.can_write_selection,
                    "selection_path": str(group.group_dir / SELECTION_NAME) if group.selection else "",
                }
            )
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps({"manual_objects_root": str(self.root), "groups": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
        return destination
