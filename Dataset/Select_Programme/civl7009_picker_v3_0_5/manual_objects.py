from __future__ import annotations

import csv
import json
import os
import shutil
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from .version import MANUAL_SELECTION_SCHEMA, UI_VERSION

MANIFEST_NAME = "group_manifest.json"
SELECTION_NAME = "manual_selection.json"
INDEX_NAME = "manual_objects_index.csv"
CLAIM_STATUS = "PENDING_AUDIT"
REVIEW_STATUSES = {"APPROVED", "SKIP", "AMBIGUOUS", "NEEDS_AGENT_CHECK"}
UNREVIEWED_STATUS = "未复核"

REASON_PRIORITY = [
    "SHA256_EXACT_IMAGE",
    "PIXEL_SHA256_EXACT_IMAGE",
    "PHASH_NEAR_STRONG",
    "DHASH_NEAR_STRONG",
    "ROTATION_AWARE_PHASH",
    "COMPOSITE_NEAR_HASH",
]

REQUIRED_MANIFEST_FIELDS = {
    "schema_version",
    "group_key",
    "reason",
    "group_size",
    "dataset_ids",
    "claim_status",
    "items",
}
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


def normalise_label_class_set(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    text = str(value).strip()
    if not text:
        return []
    if "|" in text:
        return [part for part in text.split("|") if part]
    if "," in text:
        return [part.strip() for part in text.split(",") if part.strip()]
    return [text]


def reason_sort_key(reason: str) -> tuple[int, str]:
    try:
        return (REASON_PRIORITY.index(reason), reason)
    except ValueError:
        return (len(REASON_PRIORITY), reason)


def bucket_sort_key(bucket: str) -> tuple[int, int, str]:
    text = str(bucket or "")
    if text.upper().startswith("N") and text[1:].isdigit():
        return (0, int(text[1:]), text)
    if text.upper() == "N20_PLUS":
        return (1, 20, text)
    return (2, 9999, text)


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
    label_class_set: list[str]
    metrics: dict[str, Any]
    image_decode_status: str = ""
    label_format_set: str = ""
    source_size: int = 0
    source_mtime: int | float | str = ""
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
        return UNREVIEWED_STATUS


@dataclass
class ManualGroupSummary:
    reason: str
    size_bucket: str
    group_key: str
    group_folder: str
    group_dir: Path
    group_size: int
    dataset_ids: list[str] = field(default_factory=list)
    copied_row_count: int = 0
    label_class_set: list[str] = field(default_factory=list)
    copy_status_set: list[str] = field(default_factory=list)
    has_selection: bool = False
    selection_status: str = UNREVIEWED_STATUS
    issue_count: int = 0

    @property
    def group_name(self) -> str:
        return self.group_folder


@dataclass
class ManualObjectsIndexResult:
    root: Path
    mode: str
    summaries: list[ManualGroupSummary]
    row_count: int
    duration_ms: float
    warning: str = ""

    @property
    def group_count(self) -> int:
        return len(self.summaries)


@dataclass
class ManualObjectsFilter:
    reason: str = ""
    bucket: str = ""
    review_status: str = ""
    dataset_id: str = ""
    label_class: str = ""
    copy_status: str = ""
    selection_presence: str = ""


@dataclass
class IdClassStatus:
    dataset_id: str
    class_dir: Path
    class_file: Path | None = None
    class_count: int = 0
    status: str = "MISSING"
    message: str = ""


class ManualObjectsClassService:
    """Manage per-ID class-name files for Manual Objects bbox display."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.classes_root = self.root / "ID_Classes"

    def ensure_id_class_dirs(self, dataset_ids: list[str] | set[str]) -> list[IdClassStatus]:
        self.classes_root.mkdir(parents=True, exist_ok=True)
        statuses: list[IdClassStatus] = []
        for dataset_id in sorted({str(item).strip() for item in dataset_ids if str(item).strip()}):
            class_dir = self.classes_root / dataset_id
            class_dir.mkdir(parents=True, exist_ok=True)
            statuses.append(self.inspect_dataset_id(dataset_id))
        return statuses

    def inspect_dataset_id(self, dataset_id: str) -> IdClassStatus:
        dataset_id = str(dataset_id).strip()
        class_dir = self.classes_root / dataset_id
        class_dir.mkdir(parents=True, exist_ok=True)
        candidates = [
            path
            for path in sorted(class_dir.glob("*.txt"), key=lambda p: p.name.casefold())
            if path.is_file() and not path.name.startswith("_")
        ]
        if not candidates:
            return IdClassStatus(dataset_id, class_dir, None, 0, "MISSING", "未发现类别 txt 文件。")
        valid_files: list[tuple[Path, list[str]]] = []
        for path in candidates:
            names = self.read_class_file(path)
            if names:
                valid_files.append((path, names))
        if not valid_files:
            return IdClassStatus(dataset_id, class_dir, candidates[0], 0, "EMPTY", "类别 txt 存在但没有有效类别行。")
        if len(valid_files) > 1:
            path, names = valid_files[0]
            return IdClassStatus(dataset_id, class_dir, path, len(names), "MULTIPLE", f"发现 {len(valid_files)} 个有效 txt，已使用按文件名排序的第一个。")
        path, names = valid_files[0]
        return IdClassStatus(dataset_id, class_dir, path, len(names), "OK", "类别文件可用。")

    @staticmethod
    def read_class_file(path: Path) -> list[str]:
        try:
            text = path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            text = path.read_text(encoding="utf-8", errors="replace")
        names: list[str] = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            names.append(stripped)
        return names

    def load_class_maps(self) -> dict[str, dict[str, str]]:
        maps: dict[str, dict[str, str]] = {}
        if not self.classes_root.exists():
            return maps
        for class_dir in sorted([path for path in self.classes_root.iterdir() if path.is_dir()], key=lambda p: p.name.casefold()):
            status = self.inspect_dataset_id(class_dir.name)
            if status.class_file and status.class_count > 0:
                names = self.read_class_file(status.class_file)
                maps[class_dir.name] = {str(index): name for index, name in enumerate(names)}
        return maps

    @staticmethod
    def dataset_ids_from_summaries(summaries: list[ManualGroupSummary]) -> list[str]:
        dataset_ids: set[str] = set()
        for summary in summaries:
            dataset_ids.update(str(item).strip() for item in summary.dataset_ids if str(item).strip())
        return sorted(dataset_ids)


class ManualObjectsService:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def list_groups(self) -> list[ManualObjectGroup]:
        groups: list[ManualObjectGroup] = []
        if not self.root.exists() or not self.root.is_dir():
            return groups
        for reason_dir in sorted(
            [p for p in self.root.iterdir() if p.is_dir() and not p.name.startswith("_") and p.name != "ID_Classes"],
            key=lambda p: reason_sort_key(p.name),
        ):
            for bucket_dir in sorted([p for p in reason_dir.iterdir() if p.is_dir()], key=lambda p: bucket_sort_key(p.name)):
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

        for field_name in sorted(REQUIRED_MANIFEST_FIELDS - set(manifest)):
            group.issues.append(ManualObjectsIssue("ERROR", "MANIFEST_FIELD_MISSING", f"manifest 缺少字段: {field_name}", group_dir))
        group.schema_version = str(manifest.get("schema_version", ""))
        group.group_key = str(manifest.get("group_key", group_dir.name))
        group.group_size = int(manifest.get("group_size", 0) or 0)
        group.dataset_ids = [str(item) for item in (manifest.get("dataset_ids", []) or [])]
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
                    label_class_set=normalise_label_class_set(raw.get("label_class_set", [])),
                    metrics=dict(raw.get("metrics", {}) or {}),
                    image_decode_status=str(raw.get("image_decode_status", "")),
                    label_format_set=str(raw.get("label_format_set", "")),
                    source_size=int(raw.get("source_size", 0) or 0),
                    source_mtime=raw.get("source_mtime", raw.get("source_mtime_ns", "")),
                )
            )
        if group.group_size and len(group.items) != group.group_size:
            group.issues.append(ManualObjectsIssue("WARN", "GROUP_SIZE_MISMATCH", f"group_size={group.group_size}, items={len(group.items)}。", group_dir))
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
        index = ManualObjectsIndexService(self.root).load_group_summaries()
        rows = []
        for summary in index.summaries:
            summary = ManualObjectsIndexService(self.root).refresh_summary_selection_status(summary)
            rows.append(
                {
                    "reason": summary.reason,
                    "size_bucket": summary.size_bucket,
                    "group_name": summary.group_name,
                    "group_key": summary.group_key,
                    "review_status": summary.selection_status,
                    "issue_count": summary.issue_count,
                    "selection_path": str(summary.group_dir / SELECTION_NAME) if summary.has_selection else "",
                }
            )
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps({"manual_objects_root": str(self.root), "groups": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
        return destination


class ManualObjectsIndexService:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.index_path = self.root / "_indexes" / INDEX_NAME
        self.group_service = ManualObjectsService(self.root)

    def load_group_summaries(self) -> ManualObjectsIndexResult:
        started = time.perf_counter()
        if self.index_path.exists():
            result = self._load_from_csv(started)
        else:
            result = self._load_from_manifests(started)
        result.summaries.sort(key=lambda s: (reason_sort_key(s.reason), bucket_sort_key(s.size_bucket), s.group_folder, s.group_key))
        return result

    def _load_from_csv(self, started: float) -> ManualObjectsIndexResult:
        grouped: dict[tuple[str, str], dict[str, Any]] = {}
        row_count = 0
        with self.index_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle)
            try:
                header = next(reader)
            except StopIteration:
                header = []
            columns = {name: index for index, name in enumerate(header)}
            reason_index = columns.get("reason", -1)
            group_key_index = columns.get("group_key", -1)
            group_folder_index = columns.get("group_folder", -1)
            bucket_index = columns.get("duplicate_count_bucket", -1)
            group_size_index = columns.get("group_size", -1)
            dataset_id_index = columns.get("dataset_id", -1)
            label_class_index = columns.get("label_class_set", -1)
            copy_status_index = columns.get("copy_status", -1)

            def cell(row: list[str], index: int) -> str:
                return row[index] if 0 <= index < len(row) else ""

            for row in reader:
                row_count += 1
                reason = cell(row, reason_index)
                group_key = cell(row, group_key_index)
                group_folder = cell(row, group_folder_index)
                bucket = cell(row, bucket_index)
                key = (reason, group_key)
                data = grouped.get(key)
                if data is None:
                    try:
                        group_size = int(cell(row, group_size_index) or 0)
                    except ValueError:
                        group_size = 0
                    data = {
                        "reason": reason,
                        "group_key": group_key,
                        "group_folder": group_folder,
                        "bucket": bucket,
                        "group_size": group_size,
                        "dataset_ids": set(),
                        "label_classes": set(),
                        "copy_statuses": set(),
                        "rows": 0,
                    }
                    grouped[key] = data
                data["rows"] += 1
                dataset_id = cell(row, dataset_id_index)
                if dataset_id:
                    data["dataset_ids"].add(dataset_id)
                label_class_value = cell(row, label_class_index)
                if label_class_value:
                    for label_class in normalise_label_class_set(label_class_value):
                        data["label_classes"].add(label_class)
                copy_status = cell(row, copy_status_index)
                if copy_status:
                    data["copy_statuses"].add(copy_status)
        summaries = []
        for data in grouped.values():
            reason = data["reason"]
            bucket = data["bucket"]
            folder = data["group_folder"]
            group_dir = self.root / reason / bucket / folder
            summaries.append(
                ManualGroupSummary(
                    reason=reason,
                    size_bucket=bucket,
                    group_key=data["group_key"],
                    group_folder=folder,
                    group_dir=group_dir,
                    group_size=int(data["group_size"]),
                    dataset_ids=sorted(data["dataset_ids"]),
                    copied_row_count=int(data["rows"]),
                    label_class_set=sorted(data["label_classes"]),
                    copy_status_set=sorted(data["copy_statuses"]),
                )
            )
        return ManualObjectsIndexResult(
            root=self.root,
            mode="index",
            summaries=summaries,
            row_count=row_count,
            duration_ms=(time.perf_counter() - started) * 1000,
        )

    def _load_from_manifests(self, started: float) -> ManualObjectsIndexResult:
        groups = self.group_service.list_groups()
        summaries = [
            ManualGroupSummary(
                reason=group.reason,
                size_bucket=group.size_bucket,
                group_key=group.group_key,
                group_folder=group.group_name,
                group_dir=group.group_dir,
                group_size=group.group_size,
                dataset_ids=group.dataset_ids,
                copied_row_count=len(group.items),
                label_class_set=sorted({klass for item in group.items for klass in item.label_class_set}),
                copy_status_set=[],
                has_selection=bool(group.selection),
                selection_status=group.review_status,
                issue_count=len(group.issues),
            )
            for group in groups
        ]
        return ManualObjectsIndexResult(
            root=self.root,
            mode="manifest_fallback",
            summaries=summaries,
            row_count=sum(summary.copied_row_count for summary in summaries),
            duration_ms=(time.perf_counter() - started) * 1000,
            warning="未找到 _indexes/manual_objects_index.csv，已降级为慢速 manifest 递归模式。",
        )

    def load_group_from_summary(self, summary: ManualGroupSummary) -> ManualObjectGroup:
        return self.group_service.load_group(summary.group_dir)

    def refresh_summary_selection_status(self, summary: ManualGroupSummary) -> ManualGroupSummary:
        selection_path = summary.group_dir / SELECTION_NAME
        summary.has_selection = selection_path.exists()
        summary.selection_status = UNREVIEWED_STATUS
        summary.issue_count = 0
        if not selection_path.exists():
            return summary
        try:
            selection = json.loads(selection_path.read_text(encoding="utf-8"))
            summary.selection_status = str(selection.get("review_status", "UNKNOWN"))
        except Exception:
            summary.selection_status = "SELECTION_JSON_INVALID"
            summary.issue_count += 1
        return summary

    def filter_summaries(self, summaries: list[ManualGroupSummary], filters: ManualObjectsFilter) -> list[ManualGroupSummary]:
        rows = summaries
        if filters.reason:
            rows = [s for s in rows if s.reason == filters.reason]
        if filters.bucket:
            rows = [s for s in rows if s.size_bucket == filters.bucket]
        if filters.review_status:
            rows = [s for s in rows if s.selection_status == filters.review_status]
        if filters.dataset_id:
            needle = filters.dataset_id.casefold()
            rows = [s for s in rows if any(needle in dataset.casefold() for dataset in s.dataset_ids)]
        if filters.label_class:
            needle = filters.label_class.casefold()
            rows = [s for s in rows if any(needle == klass.casefold() for klass in s.label_class_set)]
        if filters.copy_status:
            rows = [s for s in rows if filters.copy_status in s.copy_status_set]
        if filters.selection_presence == "has":
            rows = [s for s in rows if s.has_selection]
        elif filters.selection_presence == "missing":
            rows = [s for s in rows if not s.has_selection]
        return rows

    @staticmethod
    def page_summaries(summaries: list[ManualGroupSummary], page: int, page_size: int = 500) -> list[ManualGroupSummary]:
        start = max(0, page) * page_size
        return summaries[start : start + page_size]
