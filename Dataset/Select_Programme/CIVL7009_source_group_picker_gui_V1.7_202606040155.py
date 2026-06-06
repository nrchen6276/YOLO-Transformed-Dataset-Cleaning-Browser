from __future__ import annotations

import argparse
import atexit
import csv
import json
import queue
import re
import shutil
import sys
import threading
import time
from collections import Counter, OrderedDict, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
except Exception:  # pragma: no cover - GUI imports are environment dependent.
    tk = None
    filedialog = None
    messagebox = None
    ttk = None

try:
    from PIL import Image, ImageTk
except Exception:  # pragma: no cover - handled at GUI startup.
    Image = None
    ImageTk = None


SCRIPT_VERSION = "V1.7"
SCRIPT_TIMECODE = "202606040155"
STATUS = "PENDING_AUDIT"
REVIEW_DIR_RE = re.compile(r"^ManualReview_GroupSize_(\d+)$")
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
LABEL_EXT = ".txt"
RF_MARKER = ".rf."
ALLOWED_IMAGE_SUBDIRS = {"done", "out"}
ALLOWED_LABEL_SUBDIRS = {"done", "out", "done_auto", "out_auto"}
YOLO_SPLIT_NAMES = {"train", "valid", "val", "test"}
HKU_DEEP_GREEN = "#094438"
HKU_OFFICIAL_GREEN = "#024638"
HKU_LIGHT_GOLD = "#D1C18D"
HKU_BLUE = "#009CD5"
HKU_RED = "#EF4022"
HKU_SOFT_GREY = "#E8EDF2"
HKU_WHITE = "#FDFDFD"
HKU_BLACK = "#1C1C1C"


class ManualReviewError(RuntimeError):
    """Raised when a ManualReview directory is unsafe for GUI processing."""


class RuntimeLogger:
    def __init__(self, script_version: str, script_timecode: str) -> None:
        self.script_version = script_version
        self.script_timecode = script_timecode
        self.run_id = datetime.now().strftime("%Y%m%d%H%M%S%f")[:-3]
        self.started_perf = time.perf_counter()
        self.lock = threading.Lock()
        self.programme_dir = self.resolve_programme_dir()
        self.log_dir = self.programme_dir / "Runtime_Logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.log_dir / f"CIVL7009_Source_Group_Picker_Plog_{script_version}_{self.run_id}.jsonl"
        self._file = self.path.open("a", encoding="utf-8", buffering=1)
        self.event(
            "run_start",
            script_version=script_version,
            script_timecode=script_timecode,
            programme_dir=str(self.programme_dir),
            log_path=str(self.path),
            python=sys.version,
            argv=sys.argv,
        )

    @staticmethod
    def resolve_programme_dir() -> Path:
        if getattr(sys, "frozen", False):
            exe_dir = Path(sys.executable).resolve().parent
            if exe_dir.name.casefold() == "executable":
                return exe_dir.parent
            return exe_dir
        return Path(__file__).resolve().parent

    def event(self, event: str, **fields: Any) -> None:
        record = {
            "timestamp": datetime.now().isoformat(timespec="milliseconds"),
            "elapsed_ms": round((time.perf_counter() - self.started_perf) * 1000.0, 3),
            "thread": threading.current_thread().name,
            "event": event,
            **fields,
        }
        with self.lock:
            self._file.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")

    def close(self) -> None:
        self.event("run_end")
        with self.lock:
            self._file.close()


RUNTIME_LOGGER: RuntimeLogger | None = None
RUNTIME_LOGGER_LOCK = threading.Lock()


def ensure_runtime_logger() -> RuntimeLogger:
    global RUNTIME_LOGGER
    if RUNTIME_LOGGER is None:
        with RUNTIME_LOGGER_LOCK:
            if RUNTIME_LOGGER is None:
                RUNTIME_LOGGER = RuntimeLogger(SCRIPT_VERSION, SCRIPT_TIMECODE)
    return RUNTIME_LOGGER


def log_event(event: str, **fields: Any) -> None:
    logger = ensure_runtime_logger()
    logger.event(event, **fields)


def close_runtime_logger() -> None:
    global RUNTIME_LOGGER
    with RUNTIME_LOGGER_LOCK:
        if RUNTIME_LOGGER is not None:
            RUNTIME_LOGGER.close()
            RUNTIME_LOGGER = None


atexit.register(close_runtime_logger)


@dataclass
class AuditSummary:
    review_name: str
    group_size: int
    image_base: str
    label_base: str
    status: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    root_image_count: int = 0
    root_prefix_count: int = 0
    root_group_size_distribution: dict[int, int] = field(default_factory=dict)
    root_invalid_group_count: int = 0
    root_completed_conflict_count: int = 0
    done_image_count: int = 0
    done_prefix_count: int = 0
    done_group_size_distribution: dict[int, int] = field(default_factory=dict)
    done_duplicate_prefix_count: int = 0
    out_image_count: int = 0
    out_prefix_count: int = 0
    out_group_size_distribution: dict[int, int] = field(default_factory=dict)
    out_prefixes_not_expected_size_count: int = 0
    expected_out_per_done_group: int = 0
    expected_out_image_count: int = 0
    out_image_count_equals_done_times_expected: bool = False
    out_prefix_set_equals_done_prefix_set: bool = False
    image_rule_pass: bool = False
    label_root_count: int = 0
    label_done_count: int = 0
    label_out_count: int = 0
    label_done_auto_count: int = 0
    label_out_auto_count: int = 0
    label_recursive_total_count: int = 0
    label_position_sync_pass: bool = False
    all_image_stems_have_label_somewhere: bool = False
    missing_label_stem_count: int = 0
    orphan_label_stem_count: int = 0
    unfinished_group_count: int = 0
    completed_group_count: int = 0
    selectable_group_count: int = 0


@dataclass
class PrefixAuditRow:
    prefix: str
    root_image_count: int
    done_image_count: int
    out_image_count: int
    label_root_count: int
    label_done_count: int
    label_out_count: int
    label_auto_count: int
    root_filenames: str
    done_filenames: str
    out_filenames: str
    audit_status: str


@dataclass
class YoloSourceBranch:
    split: str
    image_base: Path
    label_base: Path
    layout: str


@dataclass
class YoloPairRow:
    split: str
    image_path: Path | None
    label_path: Path | None
    relative_stem: str
    filename: str
    prefix: str
    status: str


@dataclass
class YoloDatasetAudit:
    dataset_root: Path
    layout: str
    branches: list[YoloSourceBranch]
    paired_rows: list[YoloPairRow]
    missing_label_rows: list[YoloPairRow]
    orphan_label_rows: list[YoloPairRow]
    invalid_prefix_rows: list[YoloPairRow]
    duplicate_image_name_count: int
    duplicate_label_name_count: int
    target_name_conflict_count: int
    group_size_distribution: dict[int, int]
    prefix_count: int
    image_count: int
    label_count: int
    paired_count: int
    status: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class ManualReviewInitResult:
    dataset_root: Path
    target_id_root: Path
    copied_image_count: int
    copied_label_count: int
    skipped_count: int
    group_size_distribution: dict[int, int]
    target_review_summaries: list[AuditSummary]
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class MoveOperation:
    kind: str
    prefix: str
    source: Path
    target: Path
    role: str
    no_op: bool = False


@dataclass
class MoveTransaction:
    review_name: str
    group_size: int
    prefix: str
    selected_stem: str
    operations: list[MoveOperation]
    moved: list[MoveOperation] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))


@dataclass
class ReviewFastState:
    image_review_dir: Path
    label_review_dir: Path
    label_index: dict[str, list[Path]]
    image_done_names: set[str]
    image_out_names: set[str]
    label_done_names: set[str]
    label_out_names: set[str]


@dataclass
class QueuedMoveTask:
    task_id: int
    review_dir: Path
    prefix: str
    selected_stem: str
    transaction: MoveTransaction
    status: str = "QUEUED"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    started_at: str = ""
    finished_at: str = ""
    error: str = ""


@dataclass
class AuditRefreshResult:
    review_dir: Path
    summary: AuditSummary | None = None
    rows: list[PrefixAuditRow] = field(default_factory=list)
    groups: list[tuple[str, list[Path]]] = field(default_factory=list)
    label_index: dict[str, list[Path]] = field(default_factory=dict)
    fast_state: ReviewFastState | None = None
    error: str = ""


@dataclass
class ThumbnailJob:
    key: tuple[str, int, int, int, int]
    image_path: Path
    max_width: int
    max_height: int


@dataclass
class ThumbnailResult:
    key: tuple[str, int, int, int, int]
    image_path: Path
    pil_image: Any | None = None
    error: str = ""


@dataclass(frozen=True)
class KeypadSlot:
    index: int
    key: str | None
    row: int
    col: int


def get_prefix(path: Path) -> tuple[str | None, str]:
    stem = path.stem
    idx = stem.rfind(RF_MARKER)
    if idx < 0:
        return None, "missing_rf_marker"
    return stem[: idx + len(RF_MARKER)], "rf_prefix"


def sorted_top_files(path: Path, exts: set[str]) -> list[Path]:
    if not path.exists():
        return []
    return sorted(
        [item for item in path.iterdir() if item.is_file() and item.suffix.lower() in exts],
        key=lambda item: item.name.lower(),
    )


def sorted_child_dirs(path: Path) -> list[Path]:
    if not path.exists():
        return []
    return sorted([item for item in path.iterdir() if item.is_dir()], key=lambda item: item.name.lower())


def group_by_prefix(paths: list[Path]) -> dict[str, list[Path]]:
    groups: dict[str, list[Path]] = defaultdict(list)
    for path in paths:
        prefix, mode = get_prefix(path)
        if prefix is None:
            groups[f"__NO_RF__::{path.stem}"].append(path)
        else:
            groups[prefix].append(path)
    return dict(sorted(groups.items(), key=lambda item: item[0].lower()))


def stem_set(paths: list[Path]) -> set[str]:
    return {path.stem for path in paths}


def relative_stem(path: Path, base: Path) -> str:
    rel = path.relative_to(base).with_suffix("")
    return rel.as_posix()


def split_name_for_relative(relative_stem_value: str, fallback: str) -> str:
    first = relative_stem_value.split("/", 1)[0].casefold()
    if first in YOLO_SPLIT_NAMES:
        return first
    return fallback


def discover_yolo_source_branches(dataset_root: Path) -> tuple[str, list[YoloSourceBranch]]:
    dataset_root = dataset_root.resolve()
    if not dataset_root.exists() or not dataset_root.is_dir():
        raise ManualReviewError(f"YOLO 数据集目录不存在: {dataset_root}")
    image_root = dataset_root / "images"
    label_root = dataset_root / "labels"
    if image_root.exists() and image_root.is_dir() and label_root.exists() and label_root.is_dir():
        return "images_labels_root", [YoloSourceBranch("all", image_root, label_root, "images_labels_root")]

    branches: list[YoloSourceBranch] = []
    for child in sorted_child_dirs(dataset_root):
        child_image = child / "images"
        child_label = child / "labels"
        has_image = child_image.exists() and child_image.is_dir()
        has_label = child_label.exists() and child_label.is_dir()
        if has_image or has_label:
            branches.append(YoloSourceBranch(child.name, child_image, child_label, "split_images_labels"))
    if branches:
        return "split_images_labels", branches
    raise ManualReviewError(
        "未识别到常见 YOLO 结构。支持 root/images + root/labels，或 root/train|valid|val|test/images + labels。"
    )


def recursive_files(path: Path, exts: set[str]) -> list[Path]:
    if not path.exists():
        return []
    return sorted(
        [item for item in path.rglob("*") if item.is_file() and item.suffix.lower() in exts],
        key=lambda item: str(item).lower(),
    )


def audit_yolo_dataset(dataset_root: Path) -> YoloDatasetAudit:
    dataset_root = dataset_root.resolve()
    layout, branches = discover_yolo_source_branches(dataset_root)
    paired_rows: list[YoloPairRow] = []
    missing_label_rows: list[YoloPairRow] = []
    orphan_label_rows: list[YoloPairRow] = []
    invalid_prefix_rows: list[YoloPairRow] = []
    image_names: list[str] = []
    label_names: list[str] = []
    target_names: list[tuple[int, str]] = []
    grouped_images: dict[str, list[Path]] = defaultdict(list)
    matched_label_paths: set[Path] = set()
    total_images = 0
    total_labels = 0

    for branch in branches:
        images = recursive_files(branch.image_base, IMAGE_EXTS)
        labels = recursive_files(branch.label_base, {LABEL_EXT})
        total_images += len(images)
        total_labels += len(labels)
        label_by_relative = {relative_stem(label, branch.label_base): label for label in labels}
        image_relative_stems = {relative_stem(image, branch.image_base) for image in images}
        for image in images:
            rel_stem = relative_stem(image, branch.image_base)
            split = branch.split if branch.layout == "split_images_labels" else split_name_for_relative(rel_stem, "all")
            label = label_by_relative.get(rel_stem)
            prefix, _mode = get_prefix(image)
            prefix_value = prefix or ""
            image_names.append(image.name)
            if label is None:
                row = YoloPairRow(split, image, None, rel_stem, image.name, prefix_value, "missing_label")
                missing_label_rows.append(row)
                if prefix is None:
                    invalid_prefix_rows.append(row)
                continue
            label_names.append(label.name)
            matched_label_paths.add(label.resolve())
            row_status = "paired" if prefix is not None else "paired_missing_rf_marker"
            row = YoloPairRow(split, image, label, rel_stem, image.name, prefix_value, row_status)
            paired_rows.append(row)
            if prefix is None:
                invalid_prefix_rows.append(row)
            else:
                grouped_images[prefix].append(image)

        for label in labels:
            rel_stem = relative_stem(label, branch.label_base)
            if rel_stem not in image_relative_stems:
                split = branch.split if branch.layout == "split_images_labels" else split_name_for_relative(rel_stem, "all")
                label_names.append(label.name)
                orphan_label_rows.append(YoloPairRow(split, None, label, rel_stem, label.name, "", "orphan_label"))

    group_size_distribution = dict(sorted(Counter(len(members) for members in grouped_images.values()).items()))
    group_size_by_prefix = {prefix: len(members) for prefix, members in grouped_images.items()}
    for row in paired_rows:
        if row.prefix:
            target_names.append((group_size_by_prefix.get(row.prefix, 0), row.image_path.name if row.image_path else row.filename))
    duplicate_image_name_count = sum(count - 1 for count in Counter(image_names).values() if count > 1)
    duplicate_label_name_count = sum(count - 1 for count in Counter(label_names).values() if count > 1)
    target_name_conflict_count = sum(count - 1 for count in Counter(target_names).values() if count > 1)

    errors: list[str] = []
    warnings: list[str] = []
    if missing_label_rows:
        errors.append(f"存在图片缺少同相对路径标签: {len(missing_label_rows)}")
    if orphan_label_rows:
        warnings.append(f"存在标签找不到同相对路径图片: {len(orphan_label_rows)}")
    if invalid_prefix_rows:
        warnings.append(f"存在缺少 .rf. prefix 的图片，初始化时会跳过: {len(invalid_prefix_rows)}")
    if duplicate_image_name_count:
        warnings.append(f"存在重复图片文件名，扁平化 ManualReview 目标可能冲突: {duplicate_image_name_count}")
    if duplicate_label_name_count:
        warnings.append(f"存在重复标签文件名: {duplicate_label_name_count}")
    if target_name_conflict_count:
        errors.append(f"ManualReview 扁平化目标文件名冲突: {target_name_conflict_count}")

    status = "READY_WITH_WARNINGS"
    if errors:
        status = "READY_WITH_ERRORS"
    elif not warnings:
        status = "READY"
    return YoloDatasetAudit(
        dataset_root=dataset_root,
        layout=layout,
        branches=branches,
        paired_rows=paired_rows,
        missing_label_rows=missing_label_rows,
        orphan_label_rows=orphan_label_rows,
        invalid_prefix_rows=invalid_prefix_rows,
        duplicate_image_name_count=duplicate_image_name_count,
        duplicate_label_name_count=duplicate_label_name_count,
        target_name_conflict_count=target_name_conflict_count,
        group_size_distribution=group_size_distribution,
        prefix_count=len(grouped_images),
        image_count=total_images,
        label_count=total_labels,
        paired_count=len(paired_rows),
        status=status,
        errors=errors,
        warnings=warnings,
    )


def yolo_audit_to_markdown(audit: YoloDatasetAudit) -> str:
    lines = [
        "# CIVL7009 YOLO Dataset Initialisation Audit",
        "",
        f"- Status: `{STATUS}`",
        f"- Dataset root: `{audit.dataset_root}`",
        f"- Detected layout: `{audit.layout}`",
        f"- Images: {audit.image_count}",
        f"- Labels: {audit.label_count}",
        f"- Paired image-label rows: {audit.paired_count}",
        f"- Prefix groups: {audit.prefix_count}",
        f"- Group-size distribution: `{audit.group_size_distribution}`",
        f"- Missing labels: {len(audit.missing_label_rows)}",
        f"- Orphan labels: {len(audit.orphan_label_rows)}",
        f"- Missing `.rf.` prefix rows: {len(audit.invalid_prefix_rows)}",
        "",
        "## Errors",
        *(audit.errors or ["- None"]),
        "",
        "## Warnings",
        *(audit.warnings or ["- None"]),
        "",
        "## Branches",
    ]
    for branch in audit.branches:
        lines.append(f"- `{branch.split}`: images=`{branch.image_base}`, labels=`{branch.label_base}`")
    def append_rows(title: str, rows: list[YoloPairRow], limit: int = 80) -> None:
        lines.extend(["", f"## {title}", ""])
        if not rows:
            lines.append("None")
            return
        for row in rows[:limit]:
            image = str(row.image_path) if row.image_path else ""
            label = str(row.label_path) if row.label_path else ""
            lines.append(f"- `{row.status}` split=`{row.split}` stem=`{row.relative_stem}` image=`{image}` label=`{label}`")
        if len(rows) > limit:
            lines.append(f"- ... {len(rows) - limit} additional rows omitted from Markdown preview.")
    append_rows("Missing Labels", audit.missing_label_rows)
    append_rows("Orphan Labels", audit.orphan_label_rows)
    append_rows("Missing RF Prefix", audit.invalid_prefix_rows)
    lines.extend(["", "## Evidence Status", "All conclusions remain `PENDING_AUDIT`."])
    return "\n".join(lines) + "\n"


def export_yolo_audit_markdown(audit: YoloDatasetAudit, output_root: Path | None = None) -> Path:
    output_root = output_root.resolve() if output_root else RuntimeLogger.resolve_programme_dir() / "Audit_Reports"
    output_root.mkdir(parents=True, exist_ok=True)
    timecode = datetime.now().strftime("%Y%m%d%H%M")
    path = output_root / f"yolo_initialisation_audit_{timecode}.md"
    path.write_text(yolo_audit_to_markdown(audit), encoding="utf-8")
    return path


def initialise_manualreview_from_yolo(audit: YoloDatasetAudit, target_id_root: Path | None = None) -> ManualReviewInitResult:
    target_id_root = target_id_root.resolve() if target_id_root else audit.dataset_root.resolve()
    target_image_root = target_id_root / "images"
    target_label_root = target_id_root / "labels"
    target_image_root.mkdir(parents=True, exist_ok=True)
    target_label_root.mkdir(parents=True, exist_ok=True)
    grouped_rows: dict[str, list[YoloPairRow]] = defaultdict(list)
    skipped = len(audit.missing_label_rows) + len(audit.orphan_label_rows)
    for row in audit.paired_rows:
        if row.status != "paired" or not row.prefix or row.image_path is None or row.label_path is None:
            skipped += 1
            continue
        grouped_rows[row.prefix].append(row)

    target_pairs: list[tuple[Path, Path]] = []
    target_seen: set[Path] = set()
    for prefix, rows in grouped_rows.items():
        group_size = len(rows)
        image_dir = target_image_root / f"ManualReview_GroupSize_{group_size}"
        label_dir = target_label_root / f"ManualReview_GroupSize_{group_size}"
        for row in rows:
            target_image = image_dir / row.image_path.name
            target_label = label_dir / f"{row.image_path.stem}{LABEL_EXT}"
            for target in (target_image, target_label):
                resolved = target.resolve(strict=False)
                if resolved in target_seen:
                    raise ManualReviewError(f"初始化目标文件名冲突: {target}")
                if target.exists():
                    raise ManualReviewError(f"初始化目标已存在，已阻断以避免覆盖: {target}")
                target_seen.add(resolved)
            target_pairs.append((row.image_path, target_image))
            target_pairs.append((row.label_path, target_label))

    copied: list[tuple[Path, Path]] = []
    try:
        for source, target in target_pairs:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            copied.append((source, target))
    except Exception:
        for _source, target in reversed(copied):
            if target.exists():
                target.unlink()
        raise

    summaries: list[AuditSummary] = []
    for review_dir in review_dirs_for_id_root(target_id_root):
        summary, _rows = audit_review_dir(review_dir, create_missing=True)
        summaries.append(summary)
    dist = dict(sorted(Counter(len(rows) for rows in grouped_rows.values()).items()))
    warnings = []
    if skipped:
        warnings.append(f"跳过未配对或缺少 .rf. prefix 的行: {skipped}")
    return ManualReviewInitResult(
        dataset_root=audit.dataset_root,
        target_id_root=target_id_root,
        copied_image_count=len([target for _source, target in copied if target.suffix.lower() in IMAGE_EXTS]),
        copied_label_count=len([target for _source, target in copied if target.suffix.lower() == LABEL_EXT]),
        skipped_count=skipped,
        group_size_distribution=dist,
        target_review_summaries=summaries,
        warnings=warnings,
    )


def infer_label_dir(image_work_dir: Path) -> tuple[Path, Path]:
    parts = image_work_dir.resolve().parts
    image_indexes = [idx for idx, part in enumerate(parts) if part.casefold() == "images"]
    if not image_indexes:
        raise ManualReviewError(
            "无法从目标图片文件夹推断 labels 目录；请确保目标位于 <ID>/images/... 下，"
            "或通过 --label-dir 显式指定。"
        )
    idx = image_indexes[-1]
    id_root = Path(*parts[:idx])
    label_parts = list(parts)
    label_parts[idx] = "labels"
    return id_root, Path(*label_parts)


def parse_review_dir(image_review_dir: Path, label_review_dir: Path | None = None) -> tuple[int, Path, Path]:
    image_review_dir = image_review_dir.resolve()
    match = REVIEW_DIR_RE.match(image_review_dir.name)
    group_size_hint = int(match.group(1)) if match else 0
    if label_review_dir is not None:
        try:
            id_root, _inferred = infer_label_dir(image_review_dir)
        except ManualReviewError:
            id_root = image_review_dir.parent
        return group_size_hint, id_root, label_review_dir.resolve()
    id_root, inferred_label_dir = infer_label_dir(image_review_dir)
    return group_size_hint, id_root, inferred_label_dir


def review_dirs_for_id_root(id_root: Path) -> list[Path]:
    id_root = id_root.resolve()
    image_root = id_root / "images"
    label_root = id_root / "labels"
    if not image_root.exists() or not image_root.is_dir():
        raise ManualReviewError(f"<ID> 根目录缺少 images: {image_root}")
    if not label_root.exists() or not label_root.is_dir():
        raise ManualReviewError(f"<ID> 根目录缺少 labels: {label_root}")
    return [
        path
        for path in sorted_child_dirs(image_root)
        if REVIEW_DIR_RE.match(path.name)
    ]


def canonical_child_dir(parent: Path, desired: str) -> Path:
    matches = [child for child in sorted_child_dirs(parent) if child.name.casefold() == desired.casefold()]
    if len(matches) > 1:
        raise ManualReviewError(f"大小写等价目录重复，无法安全处理: {parent} -> {desired}")
    return matches[0] if matches else parent / desired


def validate_child_dirs(
    image_review_dir: Path,
    label_review_dir: Path,
    create_missing: bool = False,
    allow_missing_label_dir: bool = False,
) -> None:
    image_children = sorted_child_dirs(image_review_dir)
    bad_image_dirs = [
        child.name
        for child in image_children
        if child.name.casefold() not in ALLOWED_IMAGE_SUBDIRS
    ]
    if bad_image_dirs:
        raise ManualReviewError(
            "图片 ManualReview 目录只允许 done/out 子目录；非法子目录: "
            + ", ".join(bad_image_dirs)
        )

    if not label_review_dir.exists() and allow_missing_label_dir:
        return
    if not label_review_dir.exists():
        raise ManualReviewError(f"对应标签目录不存在: {label_review_dir}")
    label_children = sorted_child_dirs(label_review_dir)
    bad_label_dirs = [
        child.name
        for child in label_children
        if child.name.casefold() not in ALLOWED_LABEL_SUBDIRS
    ]
    if bad_label_dirs:
        raise ManualReviewError(
            "标签 ManualReview 目录只允许 done/out/Done_auto/Out_auto；非法子目录: "
            + ", ".join(bad_label_dirs)
        )

    if create_missing:
        canonical_child_dir(image_review_dir, "done").mkdir(parents=True, exist_ok=True)
        canonical_child_dir(image_review_dir, "out").mkdir(parents=True, exist_ok=True)
        canonical_child_dir(label_review_dir, "done").mkdir(parents=True, exist_ok=True)
        canonical_child_dir(label_review_dir, "out").mkdir(parents=True, exist_ok=True)


def label_lookup_dirs(label_review_dir: Path) -> list[Path]:
    dirs = [label_review_dir]
    for name in ("done", "out", "Done_auto", "Out_auto"):
        path = canonical_child_dir(label_review_dir, name)
        if path.exists():
            dirs.append(path)
    unique: list[Path] = []
    seen: set[Path] = set()
    for path in dirs:
        resolved = path.resolve(strict=False)
        if resolved not in seen:
            seen.add(resolved)
            unique.append(path)
    return unique


def locate_label(label_review_dir: Path, stem: str) -> list[Path]:
    matches: list[Path] = []
    for directory in label_lookup_dirs(label_review_dir):
        candidate = directory / f"{stem}{LABEL_EXT}"
        if candidate.exists() and candidate.is_file():
            matches.append(candidate)
    return matches


def build_label_index(label_review_dir: Path) -> dict[str, list[Path]]:
    label_index: dict[str, list[Path]] = defaultdict(list)
    for directory in label_lookup_dirs(label_review_dir):
        for label_path in sorted_top_files(directory, {LABEL_EXT}):
            label_index[label_path.stem].append(label_path)
    return dict(label_index)


def build_review_fast_state(image_review_dir: Path) -> ReviewFastState:
    _group_size, _id_root, label_review_dir = parse_review_dir(image_review_dir)
    validate_child_dirs(image_review_dir, label_review_dir, create_missing=True)
    img_done_dir = canonical_child_dir(image_review_dir, "done")
    img_out_dir = canonical_child_dir(image_review_dir, "out")
    lab_done_dir = canonical_child_dir(label_review_dir, "done")
    lab_out_dir = canonical_child_dir(label_review_dir, "out")
    return ReviewFastState(
        image_review_dir=image_review_dir,
        label_review_dir=label_review_dir,
        label_index=build_label_index(label_review_dir),
        image_done_names={path.name for path in sorted_top_files(img_done_dir, IMAGE_EXTS)},
        image_out_names={path.name for path in sorted_top_files(img_out_dir, IMAGE_EXTS)},
        label_done_names={path.name for path in sorted_top_files(lab_done_dir, {LABEL_EXT})},
        label_out_names={path.name for path in sorted_top_files(lab_out_dir, {LABEL_EXT})},
    )


def prepare_transaction_from_cached_state(
    image_review_dir: Path,
    prefix: str,
    selected_image: Path,
    members: list[Path],
    state: ReviewFastState,
) -> MoveTransaction:
    members = sorted(members, key=lambda item: item.name.lower())
    actual_group_size = len(members)
    if actual_group_size <= 1:
        raise ManualReviewError("当前 prefix 只有一张图片，不进入人工择一队列。")
    selected_image = selected_image.resolve()
    member_resolved = {path.resolve(): path for path in members}
    if selected_image not in member_resolved:
        raise ManualReviewError(f"选中图片不属于当前 prefix: {selected_image}")

    img_done_dir = canonical_child_dir(image_review_dir, "done")
    img_out_dir = canonical_child_dir(image_review_dir, "out")
    lab_done_dir = canonical_child_dir(state.label_review_dir, "done")
    lab_out_dir = canonical_child_dir(state.label_review_dir, "out")
    operations: list[MoveOperation] = []

    for image in members:
        role = "done" if image.resolve() == selected_image else "out"
        target_image_dir = img_done_dir if role == "done" else img_out_dir
        target_label_dir = lab_done_dir if role == "done" else lab_out_dir
        target_image = target_image_dir / image.name
        target_label = target_label_dir / f"{image.stem}{LABEL_EXT}"
        target_image_names = state.image_done_names if role == "done" else state.image_out_names
        target_label_names = state.label_done_names if role == "done" else state.label_out_names
        if target_image.name in target_image_names:
            raise ManualReviewError(f"目标图片已存在，整组阻断: {target_image}")
        label_matches = state.label_index.get(image.stem, [])
        if len(label_matches) != 1:
            raise ManualReviewError(f"标签必须唯一定位，整组阻断: {image.stem} -> {len(label_matches)} 个候选")
        source_label = label_matches[0]
        label_no_op = source_label.resolve(strict=False) == target_label.resolve(strict=False)
        if target_label.name in target_label_names and not label_no_op:
            raise ManualReviewError(f"目标标签已存在，整组阻断: {target_label}")
        operations.append(MoveOperation("image", prefix, image, target_image, role))
        operations.append(MoveOperation("label", prefix, source_label, target_label, role, no_op=label_no_op))

    return MoveTransaction(
        review_name=image_review_dir.name,
        group_size=actual_group_size,
        prefix=prefix,
        selected_stem=selected_image.stem,
        operations=operations,
    )


def prepare_transaction_from_members(
    image_review_dir: Path,
    prefix: str,
    selected_image: Path,
    members: list[Path],
    label_index: dict[str, list[Path]] | None = None,
) -> MoveTransaction:
    _group_size, _id_root, label_review_dir = parse_review_dir(image_review_dir)
    validate_child_dirs(image_review_dir, label_review_dir, create_missing=True)
    members = sorted(members, key=lambda item: item.name.lower())
    actual_group_size = len(members)
    if actual_group_size <= 1:
        raise ManualReviewError("当前 prefix 只有一张图片，不进入人工择一队列。")
    selected_image = selected_image.resolve()
    member_resolved = {path.resolve(): path for path in members}
    if selected_image not in member_resolved:
        raise ManualReviewError(f"选中图片不属于当前 prefix: {selected_image}")

    img_done_dir = canonical_child_dir(image_review_dir, "done")
    img_out_dir = canonical_child_dir(image_review_dir, "out")
    lab_done_dir = canonical_child_dir(label_review_dir, "done")
    lab_out_dir = canonical_child_dir(label_review_dir, "out")
    operations: list[MoveOperation] = []

    for image in members:
        role = "done" if image.resolve() == selected_image else "out"
        target_image_dir = img_done_dir if role == "done" else img_out_dir
        target_label_dir = lab_done_dir if role == "done" else lab_out_dir
        target_image = target_image_dir / image.name
        target_label = target_label_dir / f"{image.stem}{LABEL_EXT}"
        if target_image.exists():
            raise ManualReviewError(f"目标图片已存在，整组阻断: {target_image}")
        if label_index is None:
            label_matches = locate_label(label_review_dir, image.stem)
        else:
            label_matches = [path for path in label_index.get(image.stem, []) if path.exists()]
        if len(label_matches) != 1:
            raise ManualReviewError(f"标签必须唯一定位，整组阻断: {image.stem} -> {len(label_matches)} 个候选")
        source_label = label_matches[0]
        label_no_op = source_label.resolve(strict=False) == target_label.resolve(strict=False)
        if target_label.exists() and not label_no_op:
            raise ManualReviewError(f"目标标签已存在，整组阻断: {target_label}")
        operations.append(MoveOperation("image", prefix, image, target_image, role))
        operations.append(MoveOperation("label", prefix, source_label, target_label, role, no_op=label_no_op))

    return MoveTransaction(
        review_name=image_review_dir.name,
        group_size=actual_group_size,
        prefix=prefix,
        selected_stem=selected_image.stem,
        operations=operations,
    )


def folder_status(image_dir: Path, label_dir: Path) -> dict[str, Any]:
    images = sorted_top_files(image_dir, IMAGE_EXTS)
    labels = sorted_top_files(label_dir, {LABEL_EXT})
    groups = group_by_prefix(images)
    image_stems = stem_set(images)
    label_stems = stem_set(labels)
    return {
        "images": len(images),
        "labels": len(labels),
        "groups": len(groups),
        "group_size_distribution": dict(sorted(Counter(len(v) for v in groups.values()).items())),
        "missing_labels": len(image_stems - label_stems),
        "orphan_labels": len(label_stems - image_stems),
        "prefix_count": len(groups),
    }


def audit_review_dir(
    image_review_dir: Path,
    create_missing: bool = False,
    label_review_dir: Path | None = None,
) -> tuple[AuditSummary, list[PrefixAuditRow]]:
    group_size, _id_root, label_review_dir = parse_review_dir(image_review_dir, label_review_dir)
    validate_child_dirs(
        image_review_dir,
        label_review_dir,
        create_missing=create_missing and group_size > 1,
        allow_missing_label_dir=group_size == 1,
    )

    img_done_dir = canonical_child_dir(image_review_dir, "done")
    img_out_dir = canonical_child_dir(image_review_dir, "out")
    lab_done_dir = canonical_child_dir(label_review_dir, "done")
    lab_out_dir = canonical_child_dir(label_review_dir, "out")
    lab_done_auto_dir = canonical_child_dir(label_review_dir, "Done_auto")
    lab_out_auto_dir = canonical_child_dir(label_review_dir, "Out_auto")

    img_root = sorted_top_files(image_review_dir, IMAGE_EXTS)
    img_done = sorted_top_files(img_done_dir, IMAGE_EXTS)
    img_out = sorted_top_files(img_out_dir, IMAGE_EXTS)
    lab_root = sorted_top_files(label_review_dir, {LABEL_EXT})
    lab_done = sorted_top_files(lab_done_dir, {LABEL_EXT})
    lab_out = sorted_top_files(lab_out_dir, {LABEL_EXT})
    lab_done_auto = sorted_top_files(lab_done_auto_dir, {LABEL_EXT})
    lab_out_auto = sorted_top_files(lab_out_auto_dir, {LABEL_EXT})

    root_by = group_by_prefix(img_root)
    done_by = group_by_prefix(img_done)
    out_by = group_by_prefix(img_out)
    lab_root_by = group_by_prefix(lab_root)
    lab_done_by = group_by_prefix(lab_done)
    lab_out_by = group_by_prefix(lab_out)
    lab_auto_by = group_by_prefix(lab_done_auto + lab_out_auto)

    errors: list[str] = []
    warnings: list[str] = []
    expected_out = max(group_size - 1, 0)

    invalid_root = {
        prefix: members
        for prefix, members in root_by.items()
        if prefix.startswith("__NO_RF__::")
    }
    hint_mismatch_root = {
        prefix: members
        for prefix, members in root_by.items()
        if group_size > 1 and not prefix.startswith("__NO_RF__::") and len(members) != group_size
    }
    root_completed_conflicts = {
        prefix
        for prefix in root_by
        if prefix in done_by or prefix in out_by
    }
    if invalid_root:
        errors.append(f"root 未完成区存在缺少 .rf. prefix 的文件组: {len(invalid_root)}")
    if hint_mismatch_root:
        warnings.append(f"root 组规模与目录名提示 GroupSize_{group_size} 不一致: {len(hint_mismatch_root)}")
    if root_completed_conflicts:
        errors.append(f"root 与 done/out 存在同 prefix 恢复冲突: {len(root_completed_conflicts)}")

    done_duplicates = {prefix: members for prefix, members in done_by.items() if len(members) != 1}
    out_bad = {prefix: members for prefix, members in out_by.items() if group_size > 1 and len(members) != expected_out}
    if done_duplicates:
        errors.append(f"done 中存在非单张代表 prefix: {len(done_duplicates)}")
    if out_bad:
        errors.append(f"out 中存在非 {expected_out} 张 prefix: {len(out_bad)}")
    if set(done_by) != set(out_by):
        warnings.append("done/out prefix 集合不一致；可能仍在处理中或存在历史未同步。")

    all_images = img_root + img_done + img_out
    all_labels = lab_root + lab_done + lab_out + lab_done_auto + lab_out_auto
    missing_labels = stem_set(all_images) - stem_set(all_labels)
    orphan_labels = stem_set(all_labels) - stem_set(all_images)
    if missing_labels:
        if group_size == 1 and not label_review_dir.exists():
            warnings.append("GroupSize_1 为原始单图组（previous SINGLE）只读统计目录，缺少对应标签目录时不进入人工筛选。")
        else:
            errors.append(f"存在图片 stem 找不到唯一标签候选: {len(missing_labels)}")
    if orphan_labels:
        warnings.append(f"标签目录分支存在当前图片侧未覆盖的 orphan label: {len(orphan_labels)}")

    label_position_sync = (
        len(lab_done) == len(img_done)
        and len(lab_out) == len(img_out)
        and len(lab_root) == 0
        and stem_set(lab_done) == stem_set(img_done)
        and stem_set(lab_out) == stem_set(img_out)
    )
    has_completed = bool(done_by or out_by)
    image_rule_pass = (
        len(done_duplicates) == 0
        and len(out_bad) == 0
        and (not has_completed or set(done_by) == set(out_by))
        and len(img_done) == len(done_by)
        and len(root_completed_conflicts) == 0
    )

    selectable_prefixes = [
        prefix
        for prefix, members in root_by.items()
        if not prefix.startswith("__NO_RF__::")
        and len(members) > 1
        and prefix not in done_by
        and prefix not in out_by
    ]

    summary = AuditSummary(
        review_name=image_review_dir.name,
        group_size=group_size,
        image_base=str(image_review_dir),
        label_base=str(label_review_dir),
        status=STATUS,
        errors=errors,
        warnings=warnings,
        root_image_count=len(img_root),
        root_prefix_count=len(root_by),
        root_group_size_distribution=dict(sorted(Counter(len(v) for v in root_by.values()).items())),
        root_invalid_group_count=len(invalid_root),
        root_completed_conflict_count=len(root_completed_conflicts),
        done_image_count=len(img_done),
        done_prefix_count=len(done_by),
        done_group_size_distribution=dict(sorted(Counter(len(v) for v in done_by.values()).items())),
        done_duplicate_prefix_count=len(done_duplicates),
        out_image_count=len(img_out),
        out_prefix_count=len(out_by),
        out_group_size_distribution=dict(sorted(Counter(len(v) for v in out_by.values()).items())),
        out_prefixes_not_expected_size_count=len(out_bad),
        expected_out_per_done_group=expected_out,
        expected_out_image_count=len(done_by) * expected_out if group_size > 1 else 0,
        out_image_count_equals_done_times_expected=(len(img_out) == len(done_by) * expected_out) if group_size > 1 else False,
        out_prefix_set_equals_done_prefix_set=set(out_by) == set(done_by),
        image_rule_pass=image_rule_pass,
        label_root_count=len(lab_root),
        label_done_count=len(lab_done),
        label_out_count=len(lab_out),
        label_done_auto_count=len(lab_done_auto),
        label_out_auto_count=len(lab_out_auto),
        label_recursive_total_count=len(all_labels),
        label_position_sync_pass=label_position_sync,
        all_image_stems_have_label_somewhere=stem_set(all_images).issubset(stem_set(all_labels)),
        missing_label_stem_count=len(missing_labels),
        orphan_label_stem_count=len(orphan_labels),
        unfinished_group_count=len(root_by),
        completed_group_count=len(done_by),
        selectable_group_count=len(selectable_prefixes),
    )

    prefixes = sorted(
        set(root_by) | set(done_by) | set(out_by) | set(lab_root_by) | set(lab_done_by) | set(lab_out_by) | set(lab_auto_by),
        key=str.lower,
    )
    rows: list[PrefixAuditRow] = []
    for prefix in prefixes:
        root_members = root_by.get(prefix, [])
        done_members = done_by.get(prefix, [])
        out_members = out_by.get(prefix, [])
        label_root_members = lab_root_by.get(prefix, [])
        label_done_members = lab_done_by.get(prefix, [])
        label_out_members = lab_out_by.get(prefix, [])
        label_auto_members = lab_auto_by.get(prefix, [])

        status_bits: list[str] = []
        if root_members and prefix.startswith("__NO_RF__::"):
            status_bits.append("missing_rf_marker")
        if root_members and group_size > 1 and len(root_members) != group_size:
            status_bits.append(f"root_image_count_{len(root_members)}_vs_hint_{group_size}")
        if done_members and len(done_members) != 1:
            status_bits.append(f"done_image_count_{len(done_members)}")
        if out_members and group_size > 1 and len(out_members) != expected_out:
            status_bits.append(f"out_image_count_{len(out_members)}")
        if root_members and (done_members or out_members):
            status_bits.append("root_done_out_prefix_conflict")
        if done_members and not out_members:
            status_bits.append("done_prefix_missing_out")
        if out_members and not done_members:
            status_bits.append("out_prefix_missing_done")
        rows.append(
            PrefixAuditRow(
                prefix=prefix,
                root_image_count=len(root_members),
                done_image_count=len(done_members),
                out_image_count=len(out_members),
                label_root_count=len(label_root_members),
                label_done_count=len(label_done_members),
                label_out_count=len(label_out_members),
                label_auto_count=len(label_auto_members),
                root_filenames=";".join(path.name for path in root_members),
                done_filenames=";".join(path.name for path in done_members),
                out_filenames=";".join(path.name for path in out_members),
                audit_status="PASS_OR_IN_PROGRESS" if not status_bits else ";".join(status_bits),
            )
        )
    return summary, rows


def filenames_from_row_field(value: str) -> list[str]:
    return [item for item in value.split(";") if item]


def build_gui_issue_detail_lines(rows: list[PrefixAuditRow], limit: int = 24) -> list[str]:
    issue_rows = [row for row in rows if row.audit_status != "PASS_OR_IN_PROGRESS"]
    if not issue_rows:
        return ["无"]
    lines: list[str] = []
    for idx, row in enumerate(issue_rows[:limit], start=1):
        lines.append(f"{idx}. prefix: {row.prefix}")
        lines.append(f"   status: {row.audit_status}")
        root_names = filenames_from_row_field(row.root_filenames)
        done_names = filenames_from_row_field(row.done_filenames)
        out_names = filenames_from_row_field(row.out_filenames)
        if root_names:
            lines.append(f"   root({row.root_image_count}): " + "; ".join(root_names))
        if done_names:
            lines.append(f"   done({row.done_image_count}): " + "; ".join(done_names))
        if out_names:
            lines.append(f"   out({row.out_image_count}): " + "; ".join(out_names))
        label_bits = (
            f"labels root/done/out/auto = "
            f"{row.label_root_count}/{row.label_done_count}/{row.label_out_count}/{row.label_auto_count}"
        )
        lines.append(f"   {label_bits}")
    remaining = len(issue_rows) - limit
    if remaining > 0:
        lines.append(f"... 另有 {remaining} 个异常 prefix，请导出 CSV 查看完整清单。")
    return lines


def selectable_groups(image_review_dir: Path) -> list[tuple[str, list[Path]]]:
    group_size, _id_root, label_review_dir = parse_review_dir(image_review_dir)
    if group_size == 1:
        return []
    validate_child_dirs(image_review_dir, label_review_dir, create_missing=True)
    img_root = sorted_top_files(image_review_dir, IMAGE_EXTS)
    img_done = sorted_top_files(canonical_child_dir(image_review_dir, "done"), IMAGE_EXTS)
    img_out = sorted_top_files(canonical_child_dir(image_review_dir, "out"), IMAGE_EXTS)
    root_by = group_by_prefix(img_root)
    done_prefixes = set(group_by_prefix(img_done))
    out_prefixes = set(group_by_prefix(img_out))
    groups: list[tuple[str, list[Path]]] = []
    for prefix, members in root_by.items():
        if prefix.startswith("__NO_RF__::"):
            continue
        if len(members) <= 1:
            continue
        if prefix in done_prefixes or prefix in out_prefixes:
            continue
        groups.append((prefix, members))
    return groups


def prepare_transaction(image_review_dir: Path, prefix: str, selected_image: Path) -> MoveTransaction:
    group_size, _id_root, label_review_dir = parse_review_dir(image_review_dir)
    validate_child_dirs(image_review_dir, label_review_dir, create_missing=True)
    root_by = group_by_prefix(sorted_top_files(image_review_dir, IMAGE_EXTS))
    members = root_by.get(prefix, [])
    actual_group_size = len(members)
    if actual_group_size <= 1:
        raise ManualReviewError("当前 prefix 只有一张图片，不进入人工择一队列。")
    selected_image = selected_image.resolve()
    member_resolved = {path.resolve(): path for path in members}
    if selected_image not in member_resolved:
        raise ManualReviewError(f"选中图片不属于当前 prefix: {selected_image}")

    img_done_dir = canonical_child_dir(image_review_dir, "done")
    img_out_dir = canonical_child_dir(image_review_dir, "out")
    lab_done_dir = canonical_child_dir(label_review_dir, "done")
    lab_out_dir = canonical_child_dir(label_review_dir, "out")
    operations: list[MoveOperation] = []

    for image in members:
        role = "done" if image.resolve() == selected_image else "out"
        target_image_dir = img_done_dir if role == "done" else img_out_dir
        target_label_dir = lab_done_dir if role == "done" else lab_out_dir
        target_image = target_image_dir / image.name
        target_label = target_label_dir / f"{image.stem}{LABEL_EXT}"
        if target_image.exists():
            raise ManualReviewError(f"目标图片已存在，整组阻断: {target_image}")
        label_matches = locate_label(label_review_dir, image.stem)
        if len(label_matches) != 1:
            raise ManualReviewError(
                f"标签必须唯一定位，整组阻断: {image.stem} -> {len(label_matches)} 个候选"
            )
        source_label = label_matches[0]
        label_no_op = source_label.resolve(strict=False) == target_label.resolve(strict=False)
        if target_label.exists() and not label_no_op:
            raise ManualReviewError(f"目标标签已存在，整组阻断: {target_label}")
        operations.append(MoveOperation("image", prefix, image, target_image, role))
        operations.append(MoveOperation("label", prefix, source_label, target_label, role, no_op=label_no_op))

    return MoveTransaction(
        review_name=image_review_dir.name,
        group_size=actual_group_size,
        prefix=prefix,
        selected_stem=selected_image.stem,
        operations=operations,
    )


def execute_transaction(transaction: MoveTransaction) -> MoveTransaction:
    moved: list[MoveOperation] = []
    try:
        for op in transaction.operations:
            if op.no_op:
                continue
            if not op.source.exists():
                raise ManualReviewError(f"源文件不存在: {op.source}")
            if op.target.exists():
                raise ManualReviewError(f"目标文件已存在: {op.target}")
            op.target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(op.source), str(op.target))
            moved.append(op)
        transaction.moved = moved
        return transaction
    except Exception:
        for op in reversed(moved):
            if op.target.exists() and not op.source.exists():
                op.source.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(op.target), str(op.source))
        raise


def undo_transaction(transaction: MoveTransaction) -> None:
    for op in reversed(transaction.moved):
        if op.target.exists() and not op.source.exists():
            op.source.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(op.target), str(op.source))
        elif op.source.exists():
            continue
        else:
            raise ManualReviewError(f"无法撤销，源和目标都不存在: {op.source} / {op.target}")
    transaction.moved = []


def execute_queued_move_task(task: QueuedMoveTask) -> QueuedMoveTask:
    started = time.perf_counter()
    task.status = "RUNNING"
    task.started_at = datetime.now().isoformat(timespec="seconds")
    log_event(
        "move_task_execute_start",
        task_id=task.task_id,
        prefix=task.prefix,
        selected_stem=task.selected_stem,
        operation_count=len(task.transaction.operations),
    )
    try:
        task.transaction = execute_transaction(task.transaction)
        task.status = "MOVED"
    except Exception as exc:
        task.status = "FAILED"
        task.error = str(exc)
    task.finished_at = datetime.now().isoformat(timespec="seconds")
    log_event(
        "move_task_execute_end",
        task_id=task.task_id,
        prefix=task.prefix,
        status=task.status,
        moved_count=len(task.transaction.moved),
        error=task.error,
        duration_ms=round((time.perf_counter() - started) * 1000.0, 3),
    )
    return task


class BackgroundMoveRunner:
    def __init__(self, event_queue: queue.Queue[tuple[str, QueuedMoveTask]] | None = None) -> None:
        self.event_queue = event_queue
        self.work_queue: queue.Queue[QueuedMoveTask | None] = queue.Queue()
        self.tasks: dict[int, QueuedMoveTask] = {}
        self.blocked_error = ""
        self._thread: threading.Thread | None = None
        self._stop_requested = threading.Event()
        self._lock = threading.Lock()

    def start(self) -> None:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop_requested.clear()
            self._thread = threading.Thread(target=self._worker, name="manualreview-move-worker", daemon=True)
            self._thread.start()

    def enqueue(self, task: QueuedMoveTask) -> None:
        if self.blocked_error:
            raise ManualReviewError(f"后台移动队列已暂停，请先排查失败任务: {self.blocked_error}")
        self.tasks[task.task_id] = task
        self.start()
        self.work_queue.put(task)
        log_event("move_task_enqueued", task_id=task.task_id, prefix=task.prefix, selected_stem=task.selected_stem)
        self._emit("queued", task)

    def stop(self) -> None:
        self._stop_requested.set()
        self.work_queue.put(None)

    def _worker(self) -> None:
        while True:
            task = self.work_queue.get()
            try:
                if task is None or self._stop_requested.is_set():
                    return
                task.status = "RUNNING"
                task.started_at = datetime.now().isoformat(timespec="seconds")
                self._emit("running", task)
                execute_queued_move_task(task)
                if task.status == "FAILED":
                    self.blocked_error = task.error
                    self._emit("failed", task)
                    return
                self._emit("moved", task)
            finally:
                self.work_queue.task_done()

    def _emit(self, event_name: str, task: QueuedMoveTask) -> None:
        if self.event_queue is not None:
            self.event_queue.put((event_name, task))


class PreviewCache:
    def __init__(self, max_entries: int = 240) -> None:
        self.max_entries = max_entries
        self._photos: OrderedDict[tuple[str, int, int, int, int], Any] = OrderedDict()

    def clear(self) -> None:
        self._photos.clear()

    def get_photo(self, image_path: Path, max_width: int, max_height: int) -> Any:
        max_width = max(80, max_width)
        max_height = max(80, max_height)
        stat = image_path.stat()
        key = (
            str(image_path.resolve(strict=False)),
            max_width,
            max_height,
            stat.st_mtime_ns,
            stat.st_size,
        )
        if key in self._photos:
            self._photos.move_to_end(key)
            return self._photos[key]
        with Image.open(image_path) as img:
            preview = img.copy()
            preview.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(preview)
        self._photos[key] = photo
        while len(self._photos) > self.max_entries:
            self._photos.popitem(last=False)
        return photo


def thumbnail_key(image_path: Path, max_width: int, max_height: int) -> tuple[str, int, int, int, int]:
    max_width = max(80, max_width)
    max_height = max(80, max_height)
    stat = image_path.stat()
    return (
        str(image_path.resolve(strict=False)),
        max_width,
        max_height,
        stat.st_mtime_ns,
        stat.st_size,
    )


def keypad_slots_for_count(count: int) -> list[KeypadSlot]:
    if count <= 0:
        return []
    if count <= 3:
        return [KeypadSlot(index=idx, key=str(idx + 1), row=0, col=idx) for idx in range(count)]
    if count <= 6:
        return [
            KeypadSlot(index=key - 1, key=str(key), row=1 if key <= 3 else 0, col=(key - 1) % 3)
            for key in range(1, count + 1)
        ]
    if count <= 9:
        return [
            KeypadSlot(index=key - 1, key=str(key), row=2 - ((key - 1) // 3), col=(key - 1) % 3)
            for key in range(1, count + 1)
        ]
    return [
        KeypadSlot(index=idx, key=str(idx + 1) if idx < 9 else None, row=idx // 3, col=idx % 3)
        for idx in range(count)
    ]


def keypad_grid_size(slots: list[KeypadSlot]) -> tuple[int, int]:
    if not slots:
        return 1, 1
    rows = max(slot.row for slot in slots) + 1
    cols = max(slot.col for slot in slots) + 1
    return rows, cols


class AsyncThumbnailLoader:
    def __init__(self, result_queue: queue.Queue[ThumbnailResult], worker_count: int = 2) -> None:
        self.result_queue = result_queue
        self.work_queue: queue.PriorityQueue[tuple[int, int, ThumbnailJob | None]] = queue.PriorityQueue()
        self._counter = 0
        self._pending: set[tuple[str, int, int, int, int]] = set()
        self._lock = threading.Lock()
        self._stop_requested = threading.Event()
        self._threads: list[threading.Thread] = []
        self.worker_count = max(1, worker_count)

    def start(self) -> None:
        with self._lock:
            live_threads = [thread for thread in self._threads if thread.is_alive()]
            self._threads = live_threads
            needed = self.worker_count - len(self._threads)
            for _idx in range(needed):
                thread = threading.Thread(target=self._worker, name="manualreview-thumbnail-worker", daemon=True)
                self._threads.append(thread)
                thread.start()

    def request(self, image_path: Path, max_width: int, max_height: int, priority: int = 20) -> tuple[str, int, int, int, int]:
        key = thumbnail_key(image_path, max_width, max_height)
        with self._lock:
            if key in self._pending:
                return key
            self._pending.add(key)
            self._counter += 1
            counter = self._counter
        self.start()
        self.work_queue.put((priority, counter, ThumbnailJob(key, image_path, max_width, max_height)))
        log_event(
            "thumbnail_requested",
            image=str(image_path),
            width=max_width,
            height=max_height,
            priority=priority,
        )
        return key

    def stop(self) -> None:
        self._stop_requested.set()
        for _idx in range(max(1, len(self._threads))):
            with self._lock:
                self._counter += 1
                counter = self._counter
            self.work_queue.put((999999, counter, None))

    def _worker(self) -> None:
        while True:
            _priority, _counter, job = self.work_queue.get()
            try:
                if job is None or self._stop_requested.is_set():
                    return
                started = time.perf_counter()
                try:
                    with Image.open(job.image_path) as img:
                        preview = img.copy()
                        preview.thumbnail((job.max_width, job.max_height), Image.Resampling.LANCZOS)
                    self.result_queue.put(ThumbnailResult(job.key, job.image_path, preview))
                    log_event(
                        "thumbnail_worker_done",
                        image=str(job.image_path),
                        width=job.max_width,
                        height=job.max_height,
                        duration_ms=round((time.perf_counter() - started) * 1000.0, 3),
                    )
                except Exception as exc:
                    self.result_queue.put(ThumbnailResult(job.key, job.image_path, None, str(exc)))
                    log_event(
                        "thumbnail_worker_failed",
                        image=str(job.image_path),
                        width=job.max_width,
                        height=job.max_height,
                        error=str(exc),
                        duration_ms=round((time.perf_counter() - started) * 1000.0, 3),
                    )
            finally:
                if job is not None:
                    with self._lock:
                        self._pending.discard(job.key)
                self.work_queue.task_done()


def output_root_for_id_root(id_root: Path) -> Path:
    project = id_root.resolve().parents[2] if len(id_root.resolve().parents) >= 3 else Path.cwd()
    return project / "Dataset" / "Select_Programme" / "Audit_Reports"


def export_audit_report(id_root: Path, output_root: Path | None = None) -> Path:
    id_root = id_root.resolve()
    output_root = output_root.resolve() if output_root else output_root_for_id_root(id_root)
    timecode = datetime.now().strftime("%Y%m%d%H%M")
    run_dir = output_root / f"Step08A_数据集治理05_Phase2E_GUI_{timecode}"
    run_dir.mkdir(parents=True, exist_ok=False)
    summaries: list[dict[str, Any]] = []
    prefix_rows: list[dict[str, Any]] = []
    for review_dir in review_dirs_for_id_root(id_root):
        try:
            summary, rows = audit_review_dir(review_dir, create_missing=False)
        except Exception as exc:
            group_match = REVIEW_DIR_RE.match(review_dir.name)
            group_size = int(group_match.group(1)) if group_match else -1
            summary = AuditSummary(
                review_name=review_dir.name,
                group_size=group_size,
                image_base=str(review_dir),
                label_base=str(id_root / "labels" / review_dir.name),
                status=STATUS,
                errors=[str(exc)],
            )
            rows = []
        summaries.append(asdict(summary))
        for row in rows:
            row_dict = asdict(row)
            row_dict["review_name"] = review_dir.name
            prefix_rows.append(row_dict)

    summary_json = run_dir / f"manualreview_gui_audit_summary_{timecode}.json"
    summary_json.write_text(json.dumps({"status": STATUS, "summaries": summaries}, ensure_ascii=False, indent=2), encoding="utf-8")

    summary_csv = run_dir / f"manualreview_gui_audit_summary_{timecode}.csv"
    if summaries:
        with summary_csv.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(summaries[0].keys()))
            writer.writeheader()
            writer.writerows(summaries)

    prefix_csv = run_dir / f"manualreview_gui_prefix_audit_{timecode}.csv"
    prefix_fields = [
        "review_name",
        "prefix",
        "root_image_count",
        "done_image_count",
        "out_image_count",
        "label_root_count",
        "label_done_count",
        "label_out_count",
        "label_auto_count",
        "root_filenames",
        "done_filenames",
        "out_filenames",
        "audit_status",
    ]
    with prefix_csv.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=prefix_fields)
        writer.writeheader()
        writer.writerows(prefix_rows)

    md = run_dir / f"manualreview_gui_audit_summary_{timecode}.md"
    md.write_text(build_markdown_summary(id_root, summaries, timecode), encoding="utf-8")
    return run_dir


def export_target_audit_report(
    image_dir: Path,
    output_root: Path | None = None,
    label_dir: Path | None = None,
) -> Path:
    image_dir = image_dir.resolve()
    _hint, id_root, label_dir = parse_review_dir(image_dir, label_dir)
    output_root = output_root.resolve() if output_root else output_root_for_id_root(id_root)
    timecode = datetime.now().strftime("%Y%m%d%H%M")
    run_dir = output_root / f"Source_Group_Picker_Target_Audit_{timecode}"
    run_dir.mkdir(parents=True, exist_ok=False)
    summary, rows = audit_review_dir(image_dir, create_missing=False, label_review_dir=label_dir)
    summary_dict = asdict(summary)
    (run_dir / f"source_group_picker_target_summary_{timecode}.json").write_text(
        json.dumps({"status": STATUS, "summary": summary_dict}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    with (run_dir / f"source_group_picker_target_prefix_audit_{timecode}.csv").open(
        "w", newline="", encoding="utf-8-sig"
    ) as handle:
        fields = list(asdict(rows[0]).keys()) if rows else list(PrefixAuditRow("", 0, 0, 0, 0, 0, 0, 0, "", "", "", "").__dict__.keys())
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(asdict(row) for row in rows)
    (run_dir / f"source_group_picker_target_summary_{timecode}.md").write_text(
        build_markdown_summary(id_root, [summary_dict], timecode),
        encoding="utf-8",
    )
    return run_dir


def build_markdown_summary(id_root: Path, summaries: list[dict[str, Any]], timecode: str) -> str:
    rows = []
    for item in summaries:
        n = item["group_size"]
        if n == 0:
            formula = "dynamic"
        elif n == 1:
            formula = "original singleton"
        else:
            formula = f"done x {max(n - 1, 0)}"
        label_sync = "N/A" if n == 1 else ("PASS" if item.get("label_position_sync_pass") else "PENDING/FAIL")
        rows.append(
            "| {name} | {n} | {root_groups} | {done_groups} | {out_images} | {expected} | {errors} | {sync} |".format(
                name=item["review_name"],
                n=n,
                root_groups=item["root_prefix_count"],
                done_groups=item["done_prefix_count"],
                out_images=item["out_image_count"],
                expected=formula,
                errors=len(item.get("errors", [])),
                sync=label_sync,
            )
        )
    table = "\n".join(rows) if rows else "| none | | | | | | | |"
    return (
        "# Source Group Picker Audit Summary\n\n"
        "## English\n"
        f"- Status: {STATUS}.\n"
        f"- Audit target: `{id_root}`.\n"
        "- This audit checks selected source-group working folders only. Global `Done` and `transformations` folders are outside scope.\n"
        "- Image rule: `done` has one representative per prefix; `out` contains the remaining same-prefix images. "
        "If a folder name provides a GroupSize_N hint, the report also checks `out = done x (N - 1)` as a hint-level formula.\n"
        "- No images or labels were deleted, overwritten, or edited by this report export.\n\n"
        "## 中文\n"
        f"- 状态：{STATUS}。\n"
        f"- 审计对象：`{id_root}`。\n"
        "- 本审计只检查已选择的图源分组工作文件夹，全局 `Done` 和 `transformations` 不属于本工具范围。\n"
        "- 图片规则：`done` 每个前缀一张代表图；`out` 存放同前缀剩余图片。"
        "若目录名提供 GroupSize_N 提示，报告同时按提示检查 `out = done x (N - 1)`。\n"
        "- 本报告导出不删除、不覆盖、不编辑图片或标签。\n\n"
        "| Review Dir | N | Root Groups | Done Groups | Out Images | Formula | Errors | Label Sync |\n"
        "|---|---:|---:|---:|---:|---|---:|---|\n"
        f"{table}\n\n"
        "```json\n"
        + json.dumps({"timecode": timecode, "summaries": summaries}, ensure_ascii=False, indent=2)
        + "\n```\n"
    )


class ManualReviewPickerApp:
    def __init__(self, id_root: Path | None = None, review_dir: Path | None = None) -> None:
        if tk is None or ttk is None or filedialog is None or messagebox is None:
            raise ManualReviewError("Tkinter 不可用，无法启动 GUI。")
        if Image is None or ImageTk is None:
            raise ManualReviewError("Pillow/ImageTk 不可用，请使用 uv run --extra annotation 启动。")
        self.root = tk.Tk()
        self.root.title("CIVL7009 ManualReview Source Picker")
        self.root.geometry("1280x820")
        self.id_root: Path | None = None
        self.current_review_dir: Path | None = None
        self.current_groups: list[tuple[str, list[Path]]] = []
        self.current_group_members_by_prefix: dict[str, list[Path]] = {}
        self.current_index = 0
        self.photo_refs: list[Any] = []
        self.last_transaction: MoveTransaction | None = None
        self.pending_click_after: str | None = None
        self.pending_prefixes_by_review: dict[Path, set[str]] = defaultdict(set)
        self.label_index_by_review: dict[Path, dict[str, list[Path]]] = {}
        self.fast_state_by_review: dict[Path, ReviewFastState] = {}
        self.move_event_queue: queue.Queue[tuple[str, QueuedMoveTask]] = queue.Queue()
        self.audit_event_queue: queue.Queue[AuditRefreshResult] = queue.Queue()
        self.thumbnail_event_queue: queue.Queue[ThumbnailResult] = queue.Queue()
        self.move_runner = BackgroundMoveRunner(self.move_event_queue)
        self.thumbnail_loader = AsyncThumbnailLoader(self.thumbnail_event_queue, worker_count=2)
        self.move_task_counter = 0
        self.move_tasks: dict[int, QueuedMoveTask] = {}
        self.move_task_order: list[int] = []
        self.queue_rows: dict[int, str] = {}
        self.selection_blocked = False
        self.manual_continue_pending = False
        self.preview_cache = PreviewCache(max_entries=260)
        self.thumbnail_photo_cache: OrderedDict[tuple[str, int, int, int, int], Any] = OrderedDict()
        self.thumbnail_pil_cache: OrderedDict[tuple[str, int, int, int, int], Any] = OrderedDict()
        self.thumbnail_placeholders: dict[tuple[str, int, int, int, int], list[dict[str, Any]]] = defaultdict(list)
        self.thumbnail_cache_limit = 420
        self.render_token = 0
        self.render_cache_hits = 0
        self.render_cache_misses = 0
        self.last_render_ms = 0.0
        self.last_click_ms = 0.0
        self.shortcut_image_by_key: dict[str, Path] = {}
        self.card_bg_by_image: dict[str, int] = {}
        self.selection_highlight_ids: list[int] = []
        self.preload_after: str | None = None
        self.preload_offsets: list[int] = []
        self.preload_group_count = 10
        self.is_closing = False
        self.audit_dirty = False
        self.audit_refresh_running = False
        self.auto_next = tk.BooleanVar(value=True)
        self.init_dataset_root: Path | None = None
        self.init_audit: YoloDatasetAudit | None = None
        self.init_result: ManualReviewInitResult | None = None

        self._build_ui()
        self.root.bind("<KeyPress>", self.handle_shortcut_key)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.after(120, self.poll_move_events)
        self.root.after(180, self.poll_audit_events)
        self.root.after(80, self.poll_thumbnail_events)
        if review_dir:
            _n, id_root_from_review, _lab = parse_review_dir(review_dir)
            self.load_id_root(id_root_from_review)
            self.select_review_dir(review_dir)
        elif id_root:
            self.load_id_root(id_root)

    def configure_visual_style(self) -> None:
        self.root.configure(background=HKU_SOFT_GREY)
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure(".", font=("Segoe UI", 10), background=HKU_SOFT_GREY, foreground=HKU_BLACK)
        style.configure("TNotebook", background=HKU_SOFT_GREY, borderwidth=0)
        style.configure("TNotebook.Tab", padding=(18, 8), background="#F7F8F9", foreground=HKU_DEEP_GREEN)
        style.map("TNotebook.Tab", background=[("selected", HKU_WHITE)], foreground=[("selected", HKU_DEEP_GREEN)])
        style.configure("TFrame", background=HKU_SOFT_GREY)
        style.configure("Card.TFrame", background=HKU_WHITE, relief="solid", borderwidth=1)
        style.configure("TLabel", background=HKU_SOFT_GREY, foreground=HKU_BLACK)
        style.configure("Card.TLabel", background=HKU_WHITE, foreground=HKU_BLACK)
        style.configure("Title.TLabel", background=HKU_SOFT_GREY, foreground=HKU_DEEP_GREEN, font=("Segoe UI", 15, "bold"))
        style.configure("Subtle.TLabel", background=HKU_SOFT_GREY, foreground="#52616B")
        style.configure("Accent.TButton", padding=(10, 6))
        style.configure("Gold.TButton", padding=(10, 6))

    def _build_ui(self) -> None:
        self.configure_visual_style()
        header = ttk.Frame(self.root)
        header.pack(fill="x", padx=14, pady=(10, 4))
        ttk.Label(header, text="CIVL7009 ManualReview Source Picker", style="Title.TLabel").pack(side="left")
        ttk.Label(header, text="HKU palette | source grouping | PENDING_AUDIT", style="Subtle.TLabel").pack(side="left", padx=16)

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=12, pady=(4, 10))
        self.picker_tab = ttk.Frame(self.notebook)
        self.initialise_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.picker_tab, text="人工筛选")
        self.notebook.add(self.initialise_tab, text="ID 初始化")
        self.build_picker_page(self.picker_tab)
        self.build_initialise_page(self.initialise_tab)

    def build_picker_page(self, parent: Any) -> None:
        top = ttk.Frame(parent, style="Card.TFrame")
        top.pack(fill="x", padx=8, pady=8)
        ttk.Button(top, text="选择目标图片文件夹", command=self.choose_target_image_dir, style="Accent.TButton").pack(side="left", padx=8, pady=8)
        ttk.Button(top, text="扫描 ID 根目录", command=self.choose_id_root).pack(side="left", padx=6)
        ttk.Button(top, text="导出校核报告", command=self.export_report).pack(side="left", padx=6)
        ttk.Button(top, text="撤销上一组", command=self.undo_last).pack(side="left", padx=6)
        ttk.Checkbutton(top, text="自动进入下一组", variable=self.auto_next).pack(side="left", padx=12)
        self.path_var = tk.StringVar(value="未选择目录")
        ttk.Button(top, text="刷新校核", command=self.request_audit_refresh).pack(side="left", padx=6)
        ttk.Label(top, textvariable=self.path_var, style="Card.TLabel").pack(side="left", padx=12)

        body = ttk.PanedWindow(parent, orient="horizontal")
        body.pack(fill="both", expand=True, padx=8, pady=6)

        left = ttk.Frame(body, width=380)
        body.add(left, weight=0)
        ttk.Label(left, text="ManualReview 目录").pack(anchor="w")
        self.dir_list = tk.Listbox(left, height=14, exportselection=False, borderwidth=1, relief="solid")
        self.dir_list.pack(fill="both", expand=False, pady=4)
        self.dir_list.bind("<<ListboxSelect>>", self.on_dir_select)
        self.dir_items: list[Path] = []

        self.audit_text = tk.Text(left, height=25, wrap="word", background=HKU_WHITE, relief="solid", borderwidth=1)
        self.audit_text.pack(fill="both", expand=True, pady=4)

        right = ttk.Frame(body)
        body.add(right, weight=1)
        self.formula_var = tk.StringVar(value="等待扫描")
        ttk.Label(right, textvariable=self.formula_var, font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=4)
        controls = ttk.Frame(right, style="Card.TFrame")
        controls.pack(fill="x")
        ttk.Button(controls, text="上一组", command=self.prev_group).pack(side="left", padx=8, pady=6)
        ttk.Button(controls, text="下一组", command=self.next_group).pack(side="left", padx=6)
        self.group_var = tk.StringVar(value="")
        ttk.Label(controls, textvariable=self.group_var, style="Card.TLabel").pack(side="left", padx=12)

        self.canvas = tk.Canvas(right, background="#F7F8F9", highlightthickness=1, highlightbackground="#B9C4CC")
        self.canvas.pack(fill="both", expand=True, pady=6)
        self.canvas.bind("<Configure>", lambda _event: self.render_current_group())

        queue_frame = ttk.LabelFrame(right, text="后台移动队列")
        queue_frame.pack(fill="x", pady=(0, 4))
        self.queue_status_var = tk.StringVar(value="队列空闲")
        ttk.Label(queue_frame, textvariable=self.queue_status_var).pack(anchor="w", padx=6, pady=(4, 0))
        self.queue_tree = ttk.Treeview(
            queue_frame,
            columns=("status", "prefix", "selected", "created", "error"),
            show="headings",
            height=5,
        )
        for column, label, width in [
            ("status", "状态", 86),
            ("prefix", "prefix", 260),
            ("selected", "保留图源", 190),
            ("created", "排队时间", 130),
            ("error", "错误/说明", 360),
        ]:
            self.queue_tree.heading(column, text=label)
            self.queue_tree.column(column, width=width, minwidth=60, stretch=(column in {"prefix", "error"}))
        self.queue_tree.pack(fill="x", padx=6, pady=4)

    def build_initialise_page(self, parent: Any) -> None:
        toolbar = ttk.Frame(parent, style="Card.TFrame")
        toolbar.pack(fill="x", padx=8, pady=8)
        self.init_path_var = tk.StringVar(value="未选择 YOLO 数据集根目录")
        self.init_status_var = tk.StringVar(value="先选择一个包含 images/labels 或 train|valid|test/images/labels 的 ID 目录")
        ttk.Button(toolbar, text="选择 YOLO ID 目录", command=self.choose_yolo_dataset_root, style="Accent.TButton").pack(side="left", padx=8, pady=8)
        ttk.Button(toolbar, text="校核图片-标签匹配", command=self.run_yolo_audit).pack(side="left", padx=6)
        ttk.Button(toolbar, text="导出 Markdown 报告", command=self.export_yolo_audit_report_gui).pack(side="left", padx=6)
        ttk.Button(toolbar, text="初始化 ManualReview 大盘", command=self.run_yolo_initialise, style="Gold.TButton").pack(side="left", padx=6)
        ttk.Button(toolbar, text="新用户说明", command=self.show_initializer_help).pack(side="left", padx=6)
        ttk.Label(toolbar, textvariable=self.init_path_var, style="Card.TLabel").pack(side="left", padx=14)

        ttk.Label(parent, textvariable=self.init_status_var, style="Subtle.TLabel").pack(anchor="w", padx=14, pady=(0, 4))
        body = ttk.PanedWindow(parent, orient="horizontal")
        body.pack(fill="both", expand=True, padx=8, pady=6)

        left = ttk.Frame(body, width=560)
        body.add(left, weight=1)
        ttk.Label(left, text="初始化校核与说明").pack(anchor="w")
        self.init_audit_text = tk.Text(left, height=28, wrap="word", background=HKU_WHITE, relief="solid", borderwidth=1)
        self.init_audit_text.pack(fill="both", expand=True, pady=4)

        right = ttk.Frame(body)
        body.add(right, weight=1)
        ttk.Label(right, text="ManualReview 大盘状态").pack(anchor="w")
        self.init_board_tree = ttk.Treeview(
            right,
            columns=("review", "n", "root", "done", "out", "labels", "errors"),
            show="headings",
            height=18,
        )
        for column, label, width in [
            ("review", "目录", 220),
            ("n", "N", 50),
            ("root", "root组/图", 110),
            ("done", "done", 90),
            ("out", "out", 90),
            ("labels", "标签同步", 100),
            ("errors", "异常", 80),
        ]:
            self.init_board_tree.heading(column, text=label)
            self.init_board_tree.column(column, width=width, minwidth=50, stretch=(column == "review"))
        self.init_board_tree.pack(fill="both", expand=True, pady=4)

    def choose_yolo_dataset_root(self) -> None:
        selected = filedialog.askdirectory(title="选择 YOLO 数据集 ID 根目录")
        if not selected:
            return
        self.init_dataset_root = Path(selected).resolve()
        self.init_audit = None
        self.init_result = None
        self.init_path_var.set(str(self.init_dataset_root))
        self.init_status_var.set("已选择目录，请先执行图片-标签匹配校核。")
        self.init_audit_text.delete("1.0", "end")
        self.init_audit_text.insert("end", "等待校核。支持 root/images + root/labels，或 root/train|valid|val|test/images + labels。")
        self.refresh_init_board(self.init_dataset_root)

    def run_yolo_audit(self) -> None:
        if self.init_dataset_root is None:
            messagebox.showerror("未选择目录", "请先选择 YOLO 数据集 ID 根目录。")
            return
        try:
            self.init_audit = audit_yolo_dataset(self.init_dataset_root)
            self.write_yolo_audit(self.init_audit)
            self.init_status_var.set(
                f"校核完成: {self.init_audit.status}; paired={self.init_audit.paired_count}, "
                f"missing={len(self.init_audit.missing_label_rows)}, orphan={len(self.init_audit.orphan_label_rows)}"
            )
            self.refresh_init_board(self.init_dataset_root)
        except Exception as exc:
            self.init_audit = None
            self.init_status_var.set("校核失败")
            self.init_audit_text.delete("1.0", "end")
            self.init_audit_text.insert("end", str(exc))
            messagebox.showerror("校核失败", str(exc))

    def write_yolo_audit(self, audit: YoloDatasetAudit) -> None:
        self.init_audit_text.delete("1.0", "end")
        lines = [
            f"目录: {audit.dataset_root}",
            f"识别结构: {audit.layout}",
            f"图片: {audit.image_count}",
            f"标签: {audit.label_count}",
            f"一一匹配: {audit.paired_count}",
            f"prefix 组数: {audit.prefix_count}",
            f"组规模分布: {audit.group_size_distribution}",
            f"缺失标签: {len(audit.missing_label_rows)}",
            f"孤立标签: {len(audit.orphan_label_rows)}",
            f"缺少 .rf. prefix: {len(audit.invalid_prefix_rows)}",
            f"目标扁平化文件名冲突: {audit.target_name_conflict_count}",
            "",
            "错误:",
            *(audit.errors or ["无"]),
            "",
            "警告:",
            *(audit.warnings or ["无"]),
            "",
            "结构分支:",
        ]
        for branch in audit.branches:
            lines.append(f"- {branch.split}: images={branch.image_base} | labels={branch.label_base}")
        def append_issue_rows(title: str, rows: list[YoloPairRow], limit: int = 40) -> None:
            lines.extend(["", title + ":"])
            if not rows:
                lines.append("无")
                return
            for row in rows[:limit]:
                image = row.image_path.name if row.image_path else ""
                label = row.label_path.name if row.label_path else ""
                lines.append(f"- {row.status} | split={row.split} | stem={row.relative_stem} | image={image} | label={label}")
            if len(rows) > limit:
                lines.append(f"... 另有 {len(rows) - limit} 行，导出 Markdown 可查看路径级清单。")
        append_issue_rows("缺失标签明细", audit.missing_label_rows)
        append_issue_rows("孤立标签明细", audit.orphan_label_rows)
        append_issue_rows("缺少 .rf. prefix 明细", audit.invalid_prefix_rows)
        self.init_audit_text.insert("end", "\n".join(lines))

    def export_yolo_audit_report_gui(self) -> None:
        if self.init_audit is None:
            self.run_yolo_audit()
        if self.init_audit is None:
            return
        try:
            path = export_yolo_audit_markdown(self.init_audit)
            messagebox.showinfo("导出完成", f"Markdown 校核报告已导出:\n{path}")
        except Exception as exc:
            messagebox.showerror("导出失败", str(exc))

    def run_yolo_initialise(self) -> None:
        if self.init_audit is None:
            self.run_yolo_audit()
        if self.init_audit is None:
            return
        confirm_text = (
            "将把可一一匹配且包含 .rf. prefix 的图片/标签复制到当前 ID 根目录下的 "
            "images/ManualReview_GroupSize_N 与 labels/ManualReview_GroupSize_N。\n\n"
            "不会删除或移动原始 train/valid/test 数据。若目标文件已存在，将阻断以避免覆盖。\n\n"
            f"当前校核状态: {self.init_audit.status}\n"
            f"错误数: {len(self.init_audit.errors)}；警告数: {len(self.init_audit.warnings)}\n\n"
            "确认初始化？"
        )
        if not messagebox.askyesno("确认初始化 ManualReview 大盘", confirm_text):
            return
        try:
            started = time.perf_counter()
            self.init_result = initialise_manualreview_from_yolo(self.init_audit)
            self.write_init_result(self.init_result)
            self.refresh_init_board(self.init_result.target_id_root)
            self.load_id_root(self.init_result.target_id_root)
            self.init_status_var.set(
                f"初始化完成: copied images={self.init_result.copied_image_count}, "
                f"labels={self.init_result.copied_label_count}, skipped={self.init_result.skipped_count}"
            )
            log_event(
                "yolo_initialise_done",
                dataset_root=str(self.init_result.dataset_root),
                target_id_root=str(self.init_result.target_id_root),
                copied_image_count=self.init_result.copied_image_count,
                copied_label_count=self.init_result.copied_label_count,
                duration_ms=round((time.perf_counter() - started) * 1000.0, 3),
            )
        except Exception as exc:
            log_event("yolo_initialise_failed", error=str(exc))
            messagebox.showerror("初始化失败", str(exc))

    def write_init_result(self, result: ManualReviewInitResult) -> None:
        lines = [
            "",
            "初始化结果:",
            f"- target_id_root: {result.target_id_root}",
            f"- copied images: {result.copied_image_count}",
            f"- copied labels: {result.copied_label_count}",
            f"- skipped: {result.skipped_count}",
            f"- group distribution: {result.group_size_distribution}",
            "",
            "初始化警告:",
            *(result.warnings or ["无"]),
        ]
        self.init_audit_text.insert("end", "\n" + "\n".join(lines))

    def refresh_init_board(self, id_root: Path) -> None:
        if not hasattr(self, "init_board_tree"):
            return
        self.init_board_tree.delete(*self.init_board_tree.get_children())
        try:
            review_dirs = review_dirs_for_id_root(id_root)
        except Exception:
            return
        for review_dir in review_dirs:
            try:
                summary, _rows = audit_review_dir(review_dir, create_missing=True)
                values = (
                    summary.review_name,
                    summary.group_size,
                    f"{summary.root_prefix_count}/{summary.root_image_count}",
                    f"{summary.done_prefix_count}/{summary.done_image_count}",
                    f"{summary.out_prefix_count}/{summary.out_image_count}",
                    "PASS" if summary.label_position_sync_pass else "PENDING",
                    len(summary.errors),
                )
            except Exception as exc:
                values = (review_dir.name, "?", "?", "?", "?", "ERROR", str(exc))
            self.init_board_tree.insert("", "end", values=values)

    def show_initializer_help(self) -> None:
        top = tk.Toplevel(self.root)
        top.title("ManualReview 初始化说明")
        top.configure(background=HKU_SOFT_GREY)
        try:
            top.attributes("-alpha", 0.0)
        except Exception:
            pass
        top.geometry("760x520")
        text = tk.Text(top, wrap="word", background=HKU_WHITE, relief="solid", borderwidth=1)
        text.pack(fill="both", expand=True, padx=16, pady=16)
        text.insert(
            "end",
            "本页用于把一个普通 YOLO 数据集初始化成 ManualReview 图源筛选大盘。\n\n"
            "支持两类常见结构：\n"
            "1. ID/images/train 与 ID/labels/train 这种 images/labels 在上层的结构。\n"
            "2. ID/train/images 与 ID/train/labels 这种 train/valid/test 在上层的结构。\n\n"
            "工作顺序：\n"
            "1. 先选择 YOLO ID 根目录。\n"
            "2. 执行图片-标签一一匹配校核。校核会检查图片是否有同相对路径 txt 标签、是否存在孤立标签、是否缺少 .rf. prefix、扁平化目标文件名是否冲突。\n"
            "3. 无论校核完美还是存在异常，都可以导出 Markdown 报告作为过程记录。\n"
            "4. 点击初始化后，程序只复制可一一匹配且具有 .rf. prefix 的图片/标签，按 prefix 组大小放入 ManualReview_GroupSize_N。原始 YOLO 数据不会被删除或移动。\n"
            "5. 初始化后的大盘状态会显示每个 GroupSize_N 的 root、done、out、标签同步和异常数量。\n\n"
            "证据状态：本工具输出保持 PENDING_AUDIT，只用于人工数据治理，不直接升级任何模型或论文实证结论。",
        )
        text.configure(state="disabled")
        def fade(alpha: float = 0.0) -> None:
            try:
                top.attributes("-alpha", min(alpha, 0.96))
            except Exception:
                return
            if alpha < 0.96:
                top.after(18, lambda: fade(alpha + 0.08))
        fade()

    def choose_id_root(self) -> None:
        selected = filedialog.askdirectory(title="选择 Dataset/Source_Archive/<ID> 根目录")
        if selected:
            self.load_id_root(Path(selected))

    def choose_target_image_dir(self) -> None:
        selected = filedialog.askdirectory(title="选择目标图片文件夹，例如 <ID>/images/某个待筛选目录")
        if selected:
            try:
                _hint, id_root, _label = parse_review_dir(Path(selected))
            except Exception as exc:
                messagebox.showerror("目标目录不可用", str(exc))
                return
            self.id_root = id_root
            self.path_var.set(str(Path(selected).resolve()))
            self.dir_items = [Path(selected).resolve()]
            self.dir_list.delete(0, "end")
            self.dir_list.insert("end", Path(selected).name)
            self.dir_list.selection_clear(0, "end")
            self.dir_list.selection_set(0)
            self.select_review_dir(Path(selected).resolve())

    def load_id_root(self, id_root: Path) -> None:
        try:
            dirs = review_dirs_for_id_root(id_root)
        except Exception as exc:
            messagebox.showerror("初始化失败", str(exc))
            return
        self.id_root = id_root.resolve()
        self.path_var.set(str(self.id_root))
        self.dir_items = dirs
        self.dir_list.delete(0, "end")
        for directory in dirs:
            try:
                summary, _rows = audit_review_dir(directory, create_missing=True)
                label = (
                    f"{directory.name} | root组 {summary.root_prefix_count} | "
                    f"done {summary.done_prefix_count} | 异常 {len(summary.errors)}"
                )
            except Exception as exc:
                label = f"{directory.name} | ERROR: {exc}"
            self.dir_list.insert("end", label)
        if dirs:
            self.dir_list.selection_clear(0, "end")
            self.dir_list.selection_set(0)
            self.select_review_dir(dirs[0])

    def on_dir_select(self, _event: Any) -> None:
        selection = self.dir_list.curselection()
        if selection:
            self.select_review_dir(self.dir_items[selection[0]])

    def select_review_dir(self, review_dir: Path) -> None:
        self.current_review_dir = review_dir
        self.current_index = 0
        self.manual_continue_pending = False
        self.refresh_current_review()

    @staticmethod
    def review_key(review_dir: Path) -> Path:
        return review_dir.resolve()

    def pending_prefixes_for(self, review_dir: Path) -> set[str]:
        return self.pending_prefixes_by_review[self.review_key(review_dir)]

    def filter_pending_groups(self, groups: list[tuple[str, list[Path]]], review_dir: Path) -> list[tuple[str, list[Path]]]:
        pending = self.pending_prefixes_for(review_dir)
        return [(prefix, members) for prefix, members in groups if prefix not in pending]

    def label_index_for_review(self, review_dir: Path) -> dict[str, list[Path]]:
        key = self.review_key(review_dir)
        if key not in self.label_index_by_review:
            state = build_review_fast_state(review_dir)
            self.fast_state_by_review[key] = state
            self.label_index_by_review[key] = state.label_index
        return self.label_index_by_review[key]

    def fast_state_for_review(self, review_dir: Path) -> ReviewFastState:
        key = self.review_key(review_dir)
        if key not in self.fast_state_by_review:
            state = build_review_fast_state(review_dir)
            self.fast_state_by_review[key] = state
            self.label_index_by_review[key] = state.label_index
        return self.fast_state_by_review[key]

    def prepare_fast_transaction(self, prefix: str, image_path: Path) -> MoveTransaction:
        if self.current_review_dir is None:
            raise ManualReviewError("未选择当前处理目录。")
        members = self.current_group_members_by_prefix.get(prefix)
        if not members:
            for group_prefix, group_members in self.current_groups:
                if group_prefix == prefix:
                    members = group_members
                    break
        if not members:
            raise ManualReviewError(f"当前前台队列中找不到 prefix: {prefix}")
        return prepare_transaction_from_cached_state(
            self.current_review_dir,
            prefix,
            image_path,
            members,
            self.fast_state_for_review(self.current_review_dir),
        )

    def next_task_id(self) -> int:
        self.move_task_counter += 1
        return self.move_task_counter

    def apply_transaction_to_fast_state(self, transaction: MoveTransaction) -> None:
        if self.current_review_dir is None:
            return
        key = self.review_key(self.current_review_dir)
        state = self.fast_state_by_review.get(key)
        if state is None:
            return
        for op in transaction.operations:
            if op.kind == "image":
                if op.role == "done":
                    state.image_done_names.add(op.target.name)
                elif op.role == "out":
                    state.image_out_names.add(op.target.name)
            elif op.kind == "label":
                if op.role == "done":
                    state.label_done_names.add(op.target.name)
                elif op.role == "out":
                    state.label_out_names.add(op.target.name)

    def enqueue_move_task(self, transaction: MoveTransaction) -> QueuedMoveTask:
        if self.current_review_dir is None:
            raise ManualReviewError("未选择当前处理目录。")
        task = QueuedMoveTask(
            task_id=self.next_task_id(),
            review_dir=self.review_key(self.current_review_dir),
            prefix=transaction.prefix,
            selected_stem=transaction.selected_stem,
            transaction=transaction,
        )
        self.move_tasks[task.task_id] = task
        self.move_task_order.append(task.task_id)
        self.pending_prefixes_for(self.current_review_dir).add(task.prefix)
        self.apply_transaction_to_fast_state(transaction)
        self.update_queue_row(task)
        self.move_runner.enqueue(task)
        self.update_queue_status()
        return task

    def update_queue_row(self, task: QueuedMoveTask) -> None:
        if not hasattr(self, "queue_tree"):
            return
        values = (
            task.status,
            task.prefix,
            task.selected_stem,
            task.created_at,
            task.error,
        )
        item_id = self.queue_rows.get(task.task_id)
        if item_id and self.queue_tree.exists(item_id):
            self.queue_tree.item(item_id, values=values)
            return
        item_id = f"task_{task.task_id}"
        self.queue_rows[task.task_id] = item_id
        self.queue_tree.insert("", "end", iid=item_id, values=values)

    def update_queue_status(self) -> None:
        counts = Counter(task.status for task in self.move_tasks.values())
        queued = counts.get("QUEUED", 0)
        running = counts.get("RUNNING", 0)
        failed = counts.get("FAILED", 0)
        moved = counts.get("MOVED", 0)
        if failed:
            self.queue_status_var.set(f"后台队列已暂停：FAILED {failed}，MOVED {moved}，RUNNING {running}，QUEUED {queued}")
        else:
            self.queue_status_var.set(f"后台队列：QUEUED {queued}，RUNNING {running}，MOVED {moved}")

        dirty = " | 校核待刷新" if self.audit_dirty else ""
        perf = (
            f" | click {self.last_click_ms:.0f}ms"
            f" | render {self.last_render_ms:.0f}ms"
            f" | thumb hit/miss {self.render_cache_hits}/{self.render_cache_misses}"
        )
        if failed:
            self.queue_status_var.set(f"后台队列已暂停: FAILED {failed}, MOVED {moved}, RUNNING {running}, QUEUED {queued}{dirty}{perf}")
        else:
            self.queue_status_var.set(f"后台队列: QUEUED {queued}, RUNNING {running}, MOVED {moved}{dirty}{perf}")

    def poll_move_events(self) -> None:
        if self.is_closing:
            return
        failure: QueuedMoveTask | None = None
        affected_current_dir = False
        while True:
            try:
                _event_name, task = self.move_event_queue.get_nowait()
            except queue.Empty:
                break
            self.move_tasks[task.task_id] = task
            self.update_queue_row(task)
            if task.status == "MOVED":
                self.pending_prefixes_by_review[task.review_dir].discard(task.prefix)
                self.last_transaction = task.transaction
                affected_current_dir = affected_current_dir or (
                    self.current_review_dir is not None and task.review_dir == self.review_key(self.current_review_dir)
                )
            elif task.status == "FAILED":
                self.selection_blocked = True
                failure = task
                affected_current_dir = affected_current_dir or (
                    self.current_review_dir is not None and task.review_dir == self.review_key(self.current_review_dir)
                )
            self.update_queue_status()
        if affected_current_dir and self.current_review_dir is not None:
            self.audit_dirty = True
            self.update_queue_status()
            if failure is not None:
                self.render_current_group()
        if failure is not None:
            self.show_background_failure(failure)
        self.root.after(120, self.poll_move_events)

    def show_background_failure(self, task: QueuedMoveTask) -> None:
        message = (
            "后台移动任务失败，程序已暂停新的人工筛选。\n\n"
            f"任务: #{task.task_id}\n"
            f"prefix: {task.prefix}\n"
            f"保留图源: {task.selected_stem}\n"
            f"错误原因: {task.error}\n\n"
            "请先人工排查该目录和下方队列状态，再重启程序继续。"
        )
        messagebox.showerror("后台移动失败，已暂停", message)

    def active_background_task_count(self) -> int:
        return sum(1 for task in self.move_tasks.values() if task.status in {"QUEUED", "RUNNING"})

    def request_audit_refresh(self) -> None:
        if self.current_review_dir is None or self.audit_refresh_running:
            return
        review_dir = self.review_key(self.current_review_dir)
        self.audit_refresh_running = True
        self.queue_status_var.set("后台校核刷新中；筛选可继续")
        threading.Thread(target=self.run_audit_refresh_worker, args=(review_dir,), daemon=True).start()

    def run_audit_refresh_worker(self, review_dir: Path) -> None:
        result = AuditRefreshResult(review_dir=review_dir)
        try:
            summary, rows = audit_review_dir(review_dir, create_missing=True)
            groups = selectable_groups(review_dir)
            _hint, _id_root, label_review_dir = parse_review_dir(review_dir)
            fast_state = build_review_fast_state(review_dir)
            result.summary = summary
            result.rows = rows
            result.groups = groups
            result.label_index = fast_state.label_index
            result.fast_state = fast_state
        except Exception as exc:
            result.error = str(exc)
        self.audit_event_queue.put(result)

    def poll_audit_events(self) -> None:
        if self.is_closing:
            return
        while True:
            try:
                result = self.audit_event_queue.get_nowait()
            except queue.Empty:
                break
            self.audit_refresh_running = False
            if self.current_review_dir is None or result.review_dir != self.review_key(self.current_review_dir):
                continue
            if result.error:
                self.audit_text.delete("1.0", "end")
                self.audit_text.insert("end", result.error)
                self.formula_var.set("目录校核失败")
                self.update_queue_status()
                continue
            self.current_groups = self.filter_pending_groups(result.groups, self.current_review_dir)
            self.current_group_members_by_prefix = {prefix: members for prefix, members in self.current_groups}
            self.label_index_by_review[result.review_dir] = result.label_index
            if result.fast_state is not None:
                self.fast_state_by_review[result.review_dir] = result.fast_state
            self.audit_dirty = False
            if result.summary is not None:
                self.write_audit(result.summary, result.rows)
                self.formula_var.set(self.formula_text(result.summary))
            self.update_queue_status()
            self.render_current_group()
        self.root.after(180, self.poll_audit_events)

    def remember_thumbnail_photo(self, key: tuple[str, int, int, int, int], photo: Any) -> None:
        self.thumbnail_photo_cache[key] = photo
        self.thumbnail_photo_cache.move_to_end(key)
        while len(self.thumbnail_photo_cache) > self.thumbnail_cache_limit:
            self.thumbnail_photo_cache.popitem(last=False)

    def remember_thumbnail_pil(self, key: tuple[str, int, int, int, int], pil_image: Any) -> None:
        self.thumbnail_pil_cache[key] = pil_image
        self.thumbnail_pil_cache.move_to_end(key)
        while len(self.thumbnail_pil_cache) > self.thumbnail_cache_limit:
            self.thumbnail_pil_cache.popitem(last=False)

    def photo_for_thumbnail_key(self, key: tuple[str, int, int, int, int]) -> Any | None:
        photo = self.thumbnail_photo_cache.get(key)
        if photo is not None:
            self.thumbnail_photo_cache.move_to_end(key)
            return photo
        pil_image = self.thumbnail_pil_cache.get(key)
        if pil_image is None:
            return None
        self.thumbnail_pil_cache.move_to_end(key)
        photo = ImageTk.PhotoImage(pil_image)
        self.remember_thumbnail_photo(key, photo)
        return photo

    def bind_card_items(self, item_ids: list[int], image_path: Path) -> None:
        for item_id in item_ids:
            if self.canvas.find_withtag(item_id):
                self.canvas.tag_bind(item_id, "<Button-1>", lambda _event, p=image_path: self.schedule_choose_source(p))
                self.canvas.tag_bind(item_id, "<Double-Button-1>", lambda _event, p=image_path: self.handle_double_open(p))

    def clear_selection_highlight(self) -> None:
        for item_id in self.selection_highlight_ids:
            if self.canvas.find_withtag(item_id):
                self.canvas.delete(item_id)
        self.selection_highlight_ids = []

    def highlight_selected_card(self, image_path: Path) -> None:
        self.clear_selection_highlight()
        key = str(image_path.resolve(strict=False))
        bg_id = self.card_bg_by_image.get(key)
        if bg_id is None or not self.canvas.find_withtag(bg_id):
            return
        coords = self.canvas.coords(bg_id)
        if len(coords) != 4:
            return
        x1, y1, x2, y2 = coords
        highlight_id = self.canvas.create_rectangle(
            x1 + 3,
            y1 + 3,
            x2 - 3,
            y2 - 3,
            outline="#2563eb",
            width=5,
        )
        self.selection_highlight_ids = [highlight_id]
        self.canvas.tag_raise(highlight_id)
        self.root.update_idletasks()

    def handle_shortcut_key(self, event: Any) -> str | None:
        key = ""
        char = getattr(event, "char", "")
        keysym = getattr(event, "keysym", "")
        if char in self.shortcut_image_by_key:
            key = char
        elif keysym.startswith("KP_") and keysym[3:] in self.shortcut_image_by_key:
            key = keysym[3:]
        elif keysym in self.shortcut_image_by_key:
            key = keysym
        if not key:
            return None
        image_path = self.shortcut_image_by_key.get(key)
        if image_path is None:
            return None
        if self.pending_click_after is not None:
            self.root.after_cancel(self.pending_click_after)
            self.pending_click_after = None
        log_event("shortcut_choose", key=key, image=str(image_path))
        self.schedule_choose_source(image_path, delay_ms=45, selection_source="shortcut", shortcut_key=key)
        return "break"

    def poll_thumbnail_events(self) -> None:
        if self.is_closing:
            return
        updated = False
        while True:
            try:
                result = self.thumbnail_event_queue.get_nowait()
            except queue.Empty:
                break
            placeholders = self.thumbnail_placeholders.pop(result.key, [])
            if result.pil_image is None:
                for placeholder in placeholders:
                    label_id = placeholder.get("placeholder_id")
                    if label_id and self.canvas.find_withtag(label_id):
                        self.canvas.itemconfigure(label_id, text=f"缩略图失败: {result.error}")
                continue
            self.remember_thumbnail_pil(result.key, result.pil_image)
            photo = self.photo_for_thumbnail_key(result.key)
            if photo is None:
                continue
            self.photo_refs.append(photo)
            for placeholder in placeholders:
                if placeholder.get("token") != self.render_token:
                    continue
                bg_id = placeholder["bg_id"]
                if not self.canvas.find_withtag(bg_id):
                    continue
                placeholder_id = placeholder.get("placeholder_id")
                if placeholder_id and self.canvas.find_withtag(placeholder_id):
                    self.canvas.delete(placeholder_id)
                image_item_id = self.canvas.create_image(
                    placeholder["center_x"],
                    placeholder["top_y"],
                    anchor="n",
                    image=photo,
                )
                raise_ids = placeholder.get("raise_ids", [])
                for raise_id in raise_ids:
                    if self.canvas.find_withtag(raise_id):
                        self.canvas.tag_raise(raise_id)
                self.bind_card_items(
                    [bg_id, placeholder["text_id"], image_item_id, *raise_ids],
                    placeholder["image_path"],
                )
                updated = True
        if updated:
            self.update_queue_status()
        self.root.after(80, self.poll_thumbnail_events)

    def refresh_current_review(self) -> None:
        if self.current_review_dir is None:
            return
        try:
            summary, rows = audit_review_dir(self.current_review_dir, create_missing=True)
            self.current_groups = self.filter_pending_groups(selectable_groups(self.current_review_dir), self.current_review_dir)
            self.current_group_members_by_prefix = {prefix: members for prefix, members in self.current_groups}
            key = self.review_key(self.current_review_dir)
            _hint, _id_root, label_review_dir = parse_review_dir(self.current_review_dir)
            fast_state = build_review_fast_state(self.current_review_dir)
            self.label_index_by_review[key] = fast_state.label_index
            self.fast_state_by_review[key] = fast_state
            self.audit_dirty = False
            self.write_audit(summary, rows)
            self.formula_var.set(self.formula_text(summary))
        except Exception as exc:
            self.current_groups = []
            self.current_group_members_by_prefix = {}
            self.audit_text.delete("1.0", "end")
            self.audit_text.insert("end", str(exc))
            self.formula_var.set("目录校核失败")
        self.render_current_group()

    def write_audit(self, summary: AuditSummary, rows: list[PrefixAuditRow] | None = None) -> None:
        self.audit_text.delete("1.0", "end")
        data = asdict(summary)
        issue_detail_lines = build_gui_issue_detail_lines(rows or [])
        lines = [
            f"目录: {summary.review_name}",
            f"N: {summary.group_size}",
            f"未完成 root: {summary.root_image_count} 张 / {summary.root_prefix_count} 组",
            f"完成 done: {summary.done_image_count} 张 / {summary.done_prefix_count} 组",
            f"out: {summary.out_image_count} 张 / {summary.out_prefix_count} 组",
            f"标签同步: {'通过' if summary.label_position_sync_pass else '未通过/进行中'}",
            f"可筛选组: {summary.selectable_group_count}",
            "",
            "错误:",
            *(summary.errors or ["无"]),
            "",
            "警告:",
            *(summary.warnings or ["无"]),
            "",
            "异常 prefix 明细:",
            *issue_detail_lines,
            "",
            json.dumps(data, ensure_ascii=False, indent=2),
        ]
        self.audit_text.insert("end", "\n".join(lines))

    @staticmethod
    def formula_text(summary: AuditSummary) -> str:
        if summary.group_size == 0:
            return (
                f"{summary.review_name}: dynamic grouping; "
                f"root {summary.root_image_count} images / {summary.root_prefix_count} groups; "
                f"root distribution {summary.root_group_size_distribution}."
            )
        if summary.group_size == 1:
            return (
                f"{summary.review_name}: single-only statistics; "
                f"root {summary.root_image_count} = {summary.root_prefix_count} original singleton groups; "
                "not selectable."
            )
        return (
            f"{summary.review_name}: out = done x {summary.expected_out_per_done_group}; "
            f"{summary.out_image_count} = {summary.done_prefix_count} x {summary.expected_out_per_done_group}; "
            f"root {summary.root_image_count} = {summary.root_prefix_count} groups x {summary.group_size}"
        )

    def finish_render_diagnostics(self, started: float) -> None:
        self.last_render_ms = (time.perf_counter() - started) * 1000.0
        prefix = ""
        members_count = 0
        if self.current_groups:
            safe_index = max(0, min(self.current_index, len(self.current_groups) - 1))
            prefix, members = self.current_groups[safe_index]
            members_count = len(members)
        log_event(
            "render_current_group_done",
            prefix=prefix,
            members_count=members_count,
            group_index=self.current_index,
            group_count=len(self.current_groups),
            cache_hits=self.render_cache_hits,
            cache_misses=self.render_cache_misses,
            duration_ms=round(self.last_render_ms, 3),
        )
        if hasattr(self, "queue_status_var"):
            self.update_queue_status()

    def render_current_group(self) -> None:
        started = time.perf_counter()
        self.canvas.delete("all")
        self.photo_refs = []
        self.thumbnail_placeholders.clear()
        self.shortcut_image_by_key = {}
        self.card_bg_by_image = {}
        self.selection_highlight_ids = []
        self.render_token += 1
        self.render_cache_hits = 0
        self.render_cache_misses = 0
        if self.selection_blocked:
            self.canvas.create_text(
                30,
                30,
                anchor="nw",
                text="后台移动失败，新的筛选已暂停。请查看下方队列错误并人工排查后重启程序。",
                fill="#b00020",
                width=760,
            )
            return
        if self.manual_continue_pending:
            self.canvas.create_text(
                30,
                30,
                anchor="nw",
                text="当前组已加入后台移动队列。请点击“下一组”继续。",
                fill="#333",
                width=760,
            )
            return
        if not self.current_groups:
            self.canvas.create_text(30, 30, anchor="nw", text="没有可筛选组或目录存在阻断项。", fill="#333")
            self.group_var.set("0 / 0")
            return
        self.current_index = max(0, min(self.current_index, len(self.current_groups) - 1))
        prefix, members = self.current_groups[self.current_index]
        self.group_var.set(f"{self.current_index + 1} / {len(self.current_groups)} | {prefix}")
        width = max(self.canvas.winfo_width(), 800)
        height = max(self.canvas.winfo_height(), 500)
        slots = keypad_slots_for_count(len(members))
        rows, cols = keypad_grid_size(slots)
        card_w = max(260, (width - 40) // max(cols, 1))
        card_h = max(220, (height - 60) // max(rows, 1))
        for slot in slots:
            if slot.index >= len(members):
                continue
            image_path = members[slot.index]
            x = 18 + slot.col * card_w
            y = 18 + slot.row * card_h
            self.draw_card(image_path, x, y, card_w - 16, card_h - 16, slot.key)
        self.schedule_preload()
        self.finish_render_diagnostics(started)

    def draw_card(self, image_path: Path, x: int, y: int, w: int, h: int, shortcut_key: str | None = None) -> None:
        if shortcut_key is not None:
            self.shortcut_image_by_key[shortcut_key] = image_path
        bg_id = self.canvas.create_rectangle(x, y, x + w, y + h, outline="#999", width=1, fill="#ffffff")
        self.card_bg_by_image[str(image_path.resolve(strict=False))] = bg_id
        preview_h = h - 58
        image_item_id: int | None = None
        placeholder_id: int | None = None
        try:
            max_width = w - 16
            max_height = preview_h - 10
            key = thumbnail_key(image_path, max_width, max_height)
            photo = self.photo_for_thumbnail_key(key)
            if photo is not None:
                self.render_cache_hits += 1
                self.photo_refs.append(photo)
                image_item_id = self.canvas.create_image(x + w // 2, y + 8, anchor="n", image=photo)
            else:
                self.render_cache_misses += 1
                placeholder_id = self.canvas.create_text(
                    x + w // 2,
                    y + max(30, preview_h // 2),
                    anchor="center",
                    text="缩略图加载中",
                    fill="#666",
                )
                self.thumbnail_placeholders[key].append(
                    {
                        "token": self.render_token,
                        "bg_id": bg_id,
                        "text_id": 0,
                        "placeholder_id": placeholder_id,
                        "raise_ids": [],
                        "center_x": x + w // 2,
                        "top_y": y + 8,
                        "image_path": image_path,
                    }
                )
                self.thumbnail_loader.request(image_path, max_width, max_height, priority=0)
        except Exception as exc:
            self.canvas.create_text(x + 10, y + 20, anchor="nw", text=f"读取失败: {exc}", fill="#b00020")
        label = image_path.name if len(image_path.name) <= 62 else image_path.name[:58] + "..."
        text_id = self.canvas.create_text(x + 8, y + h - 44, anchor="nw", text=label, fill="#222", width=w - 16)
        badge_ids: list[int] = []
        if shortcut_key is not None:
            badge_bg_id = self.canvas.create_rectangle(
                x + 10,
                y + 10,
                x + 42,
                y + 36,
                outline="#111827",
                fill="#111827",
            )
            badge_text_id = self.canvas.create_text(
                x + 26,
                y + 23,
                anchor="center",
                text=shortcut_key,
                fill="#ffffff",
                font=("Segoe UI", 11, "bold"),
            )
            badge_ids = [badge_bg_id, badge_text_id]
        if placeholder_id is not None:
            for placeholders in self.thumbnail_placeholders.values():
                for placeholder in placeholders:
                    if placeholder.get("placeholder_id") == placeholder_id:
                        placeholder["text_id"] = text_id
                        placeholder["raise_ids"] = badge_ids
        bind_ids = [bg_id, text_id] + badge_ids
        if image_item_id is not None:
            bind_ids.append(image_item_id)
        if placeholder_id is not None:
            bind_ids.append(placeholder_id)
        for item_id in bind_ids:
            self.canvas.tag_bind(item_id, "<Button-1>", lambda _event, p=image_path: self.schedule_choose_source(p))
            self.canvas.tag_bind(item_id, "<Double-Button-1>", lambda _event, p=image_path: self.handle_double_open(p))

    def schedule_preload(self) -> None:
        if self.preload_after is not None:
            self.root.after_cancel(self.preload_after)
        self.preload_offsets = list(range(1, self.preload_group_count + 1))
        self.preload_after = self.root.after(40, self.preload_next_group)

    def preload_next_group(self) -> None:
        self.preload_after = None
        if self.selection_blocked or self.manual_continue_pending or not self.current_groups:
            return
        if not self.preload_offsets:
            return
        offset = self.preload_offsets.pop(0)
        target_index = self.current_index + offset
        if target_index < len(self.current_groups):
            _prefix, members = self.current_groups[target_index]
            width = max(self.canvas.winfo_width(), 800)
            height = max(self.canvas.winfo_height(), 500)
            slots = keypad_slots_for_count(len(members))
            rows, cols = keypad_grid_size(slots)
            card_w = max(260, (width - 40) // max(cols, 1)) - 16
            card_h = max(220, (height - 60) // max(rows, 1)) - 16
            preview_h = card_h - 58
            for image_path in members:
                try:
                    key = thumbnail_key(image_path, card_w - 16, preview_h - 10)
                    if key not in self.thumbnail_photo_cache and key not in self.thumbnail_pil_cache:
                        self.thumbnail_loader.request(image_path, card_w - 16, preview_h - 10, priority=20 + offset)
                except Exception:
                    continue
        if self.preload_offsets:
            self.preload_after = self.root.after(25, self.preload_next_group)

    def schedule_choose_source(
        self,
        image_path: Path,
        delay_ms: int = 70,
        selection_source: str = "mouse",
        shortcut_key: str = "",
    ) -> None:
        if self.pending_click_after is not None:
            self.root.after_cancel(self.pending_click_after)
        self.highlight_selected_card(image_path)
        log_event(
            "selection_highlight",
            source=selection_source,
            shortcut_key=shortcut_key,
            image=str(image_path),
            delay_ms=delay_ms,
        )
        self.pending_click_after = self.root.after(delay_ms, lambda p=image_path: self.run_scheduled_choice(p))

    def run_scheduled_choice(self, image_path: Path) -> None:
        self.pending_click_after = None
        self.choose_source(image_path)

    def handle_double_open(self, image_path: Path) -> None:
        if self.pending_click_after is not None:
            self.root.after_cancel(self.pending_click_after)
            self.pending_click_after = None
        self.clear_selection_highlight()
        self.open_full_image(image_path)

    def choose_source(self, image_path: Path) -> None:
        click_started = time.perf_counter()
        if self.current_review_dir is None:
            return
        if self.selection_blocked:
            messagebox.showerror("筛选已暂停", "后台移动队列存在失败任务。请先排查下方队列错误后重启程序继续。")
            return
        prefix, _mode = get_prefix(image_path)
        if prefix is None:
            messagebox.showerror("无法处理", "选中图片缺少 .rf. prefix。")
            return
        if prefix in self.pending_prefixes_for(self.current_review_dir):
            messagebox.showinfo("已在后台队列", f"prefix 已排队，等待后台移动完成: {prefix}")
            return
        try:
            prepare_started = time.perf_counter()
            transaction = self.prepare_fast_transaction(prefix, image_path)
            prepare_ms = (time.perf_counter() - prepare_started) * 1000.0
            enqueue_started = time.perf_counter()
            self.enqueue_move_task(transaction)
            enqueue_ms = (time.perf_counter() - enqueue_started) * 1000.0
        except Exception as exc:
            log_event(
                "choose_source_failed",
                image=str(image_path),
                prefix=prefix,
                error=str(exc),
                duration_ms=round((time.perf_counter() - click_started) * 1000.0, 3),
            )
            messagebox.showerror("整组移动已阻断", str(exc))
            self.refresh_current_review()
            return
        front_update_started = time.perf_counter()
        self.current_groups = [(item_prefix, members) for item_prefix, members in self.current_groups if item_prefix != prefix]
        self.current_group_members_by_prefix.pop(prefix, None)
        if self.current_index >= len(self.current_groups):
            self.current_index = max(0, len(self.current_groups) - 1)
        front_update_ms = (time.perf_counter() - front_update_started) * 1000.0
        render_started = time.perf_counter()
        if self.auto_next.get():
            self.manual_continue_pending = False
            self.render_current_group()
        else:
            self.manual_continue_pending = True
            self.group_var.set(f"已排队 | {prefix}")
            self.render_current_group()
        render_call_ms = (time.perf_counter() - render_started) * 1000.0
        self.last_click_ms = (time.perf_counter() - click_started) * 1000.0
        log_event(
            "choose_source_done",
            image=str(image_path),
            prefix=prefix,
            remaining_groups=len(self.current_groups),
            prepare_ms=round(prepare_ms, 3),
            enqueue_ms=round(enqueue_ms, 3),
            front_update_ms=round(front_update_ms, 3),
            render_call_ms=round(render_call_ms, 3),
            total_ms=round(self.last_click_ms, 3),
            render_cache_hits=self.render_cache_hits,
            render_cache_misses=self.render_cache_misses,
            render_ms=round(self.last_render_ms, 3),
        )
        self.update_queue_status()

    def open_full_image(self, image_path: Path) -> None:
        try:
            image = Image.open(image_path).copy()
        except Exception as exc:
            messagebox.showerror("图片读取失败", str(exc))
            return
        top = tk.Toplevel(self.root)
        top.title(image_path.name)
        canvas = tk.Canvas(top, background="#111")
        hbar = ttk.Scrollbar(top, orient="horizontal", command=canvas.xview)
        vbar = ttk.Scrollbar(top, orient="vertical", command=canvas.yview)
        canvas.configure(xscrollcommand=hbar.set, yscrollcommand=vbar.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        vbar.grid(row=0, column=1, sticky="ns")
        hbar.grid(row=1, column=0, sticky="ew")
        top.rowconfigure(0, weight=1)
        top.columnconfigure(0, weight=1)
        photo = ImageTk.PhotoImage(image)
        canvas.image_ref = photo
        canvas.create_image(0, 0, anchor="nw", image=photo)
        canvas.configure(scrollregion=(0, 0, image.width, image.height))
        top.geometry("1000x720")

    def next_group(self) -> None:
        if self.manual_continue_pending:
            self.manual_continue_pending = False
            self.render_current_group()
            return
        if self.current_groups:
            self.current_index = min(self.current_index + 1, len(self.current_groups) - 1)
            self.render_current_group()

    def prev_group(self) -> None:
        if self.manual_continue_pending:
            self.manual_continue_pending = False
        if self.current_groups:
            self.current_index = max(self.current_index - 1, 0)
            self.render_current_group()

    def undo_last(self) -> None:
        if self.active_background_task_count():
            messagebox.showinfo("撤销暂不可用", "后台仍有排队或正在移动的任务。请等待队列完成后再撤销上一组。")
            return
        if self.last_transaction is None:
            messagebox.showinfo("撤销", "没有可撤销的上一组。")
            return
        try:
            undo_transaction(self.last_transaction)
            self.last_transaction = None
            self.refresh_current_review()
        except Exception as exc:
            messagebox.showerror("撤销失败", str(exc))

    def export_report(self) -> None:
        if self.id_root is None:
            messagebox.showerror("无法导出", "请先选择 ID 根目录。")
            return
        try:
            run_dir = export_audit_report(self.id_root)
            messagebox.showinfo("导出完成", f"校核报告已导出:\n{run_dir}")
        except Exception as exc:
            messagebox.showerror("导出失败", str(exc))

    def on_close(self) -> None:
        active = self.active_background_task_count()
        log_event("gui_close_requested", active_background_tasks=active)
        if active:
            ok = messagebox.askyesno(
                "后台队列仍在运行",
                f"仍有 {active} 个后台移动任务未完成。现在退出会停止未开始的队列；正在移动的任务会尽量完成当前文件操作。确认退出？",
            )
            if not ok:
                return
        self.is_closing = True
        self.move_runner.stop()
        self.thumbnail_loader.stop()
        if self.preload_after is not None:
            self.root.after_cancel(self.preload_after)
            self.preload_after = None
        if self.pending_click_after is not None:
            self.root.after_cancel(self.pending_click_after)
            self.pending_click_after = None
        log_event("gui_close_destroy")
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CIVL7009 ManualReview source image picker GUI.")
    parser.add_argument("--id-root", default="", help="Dataset/Source_Archive/<ID> root, e.g. Dataset/Source_Archive/01.")
    parser.add_argument("--image-dir", default="", help="Target image working folder under an <ID>/images branch.")
    parser.add_argument("--label-dir", default="", help="Optional paired label working folder. If omitted, inferred from image-dir.")
    parser.add_argument("--review-dir", default="", help="Backward-compatible alias for --image-dir.")
    parser.add_argument("--audit-only", action="store_true", help="Export an audit report and exit without launching GUI.")
    parser.add_argument("--output-root", default="", help="Optional Select_Programme output root for --audit-only.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    ensure_runtime_logger()
    started = time.perf_counter()
    try:
        args = parse_args(argv)
        log_event("main_args", args=vars(args))
        id_root = Path(args.id_root).resolve() if args.id_root else None
        review_value = args.image_dir or args.review_dir
        review_dir = Path(review_value).resolve() if review_value else None
        if args.audit_only:
            audit_started = time.perf_counter()
            if review_dir:
                output_root = Path(args.output_root).resolve() if args.output_root else None
                label_dir = Path(args.label_dir).resolve() if args.label_dir else None
                run_dir = export_target_audit_report(review_dir, output_root=output_root, label_dir=label_dir)
                log_event(
                    "audit_only_target_done",
                    duration_ms=round((time.perf_counter() - audit_started) * 1000.0, 3),
                    review_dir=str(review_dir),
                    run_dir=str(run_dir),
                )
                print(json.dumps({"status": STATUS, "run_dir": str(run_dir)}, ensure_ascii=False))
                return 0
            if not id_root:
                raise ManualReviewError("--audit-only requires --id-root or --image-dir.")
            output_root = Path(args.output_root).resolve() if args.output_root else None
            run_dir = export_audit_report(id_root, output_root=output_root)
            log_event(
                "audit_only_id_done",
                duration_ms=round((time.perf_counter() - audit_started) * 1000.0, 3),
                id_root=str(id_root),
                run_dir=str(run_dir),
            )
            print(json.dumps({"status": STATUS, "run_dir": str(run_dir)}, ensure_ascii=False))
            return 0
        app = ManualReviewPickerApp(id_root=id_root, review_dir=review_dir)
        log_event("gui_mainloop_start")
        app.run()
        log_event("gui_mainloop_end")
        return 0
    except Exception as exc:
        log_event("main_exception", error=str(exc))
        raise
    finally:
        log_event("main_end", duration_ms=round((time.perf_counter() - started) * 1000.0, 3))
        close_runtime_logger()


if __name__ == "__main__":
    raise SystemExit(main())
