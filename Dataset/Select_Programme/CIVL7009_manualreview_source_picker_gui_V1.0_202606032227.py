from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
from collections import Counter, defaultdict
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


SCRIPT_VERSION = "V1.0"
SCRIPT_TIMECODE = "202606032227"
STATUS = "PENDING_AUDIT"
REVIEW_DIR_RE = re.compile(r"^ManualReview_GroupSize_(\d+)$")
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
LABEL_EXT = ".txt"
RF_MARKER = ".rf."
ALLOWED_IMAGE_SUBDIRS = {"done", "out"}
ALLOWED_LABEL_SUBDIRS = {"done", "out", "done_auto", "out_auto"}

class ManualReviewError(RuntimeError):
    """Raised when a source-group review directory is unsafe for GUI processing."""


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


def parse_review_dir(image_review_dir: Path) -> tuple[int, Path, Path]:
    image_review_dir = image_review_dir.resolve()
    match = REVIEW_DIR_RE.match(image_review_dir.name)
    if not match:
        raise ManualReviewError(
            f"目录必须命名为 images/ManualReview_GroupSize_N: {image_review_dir}"
        )
    if image_review_dir.parent.name.lower() != "images":
        raise ManualReviewError(f"目录必须位于 images 下: {image_review_dir}")
    id_root = image_review_dir.parent.parent
    label_review_dir = id_root / "labels" / image_review_dir.name
    return int(match.group(1)), id_root, label_review_dir


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


def audit_review_dir(image_review_dir: Path, create_missing: bool = False) -> tuple[AuditSummary, list[PrefixAuditRow]]:
    group_size, _id_root, label_review_dir = parse_review_dir(image_review_dir)
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
        if prefix.startswith("__NO_RF__::") or len(members) != group_size
    }
    root_completed_conflicts = {
        prefix
        for prefix in root_by
        if prefix in done_by or prefix in out_by
    }
    if invalid_root:
        errors.append(f"root 未完成区存在非 {group_size} 张同前缀组: {len(invalid_root)}")
    if root_completed_conflicts:
        errors.append(f"root 与 done/out 存在同 prefix 恢复冲突: {len(root_completed_conflicts)}")

    done_duplicates = {prefix: members for prefix, members in done_by.items() if len(members) != 1}
    out_bad = {prefix: members for prefix, members in out_by.items() if len(members) != expected_out}
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
    image_rule_pass = (
        len(done_duplicates) == 0
        and len(out_bad) == 0
        and set(done_by) == set(out_by)
        and len(img_out) == len(done_by) * expected_out
        and len(img_done) == len(done_by)
    )

    selectable_prefixes = [
        prefix
        for prefix, members in root_by.items()
        if not prefix.startswith("__NO_RF__::")
        and len(members) == group_size
        and prefix not in done_by
        and prefix not in out_by
        and group_size > 1
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
        expected_out_image_count=len(done_by) * expected_out,
        out_image_count_equals_done_times_expected=len(img_out) == len(done_by) * expected_out,
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
        if root_members and len(root_members) != group_size:
            status_bits.append(f"root_image_count_{len(root_members)}")
        if done_members and len(done_members) != 1:
            status_bits.append(f"done_image_count_{len(done_members)}")
        if out_members and len(out_members) != expected_out:
            status_bits.append(f"out_image_count_{len(out_members)}")
        if root_members and (done_members or out_members):
            status_bits.append("root_done_out_prefix_conflict")
        if done_members and not out_members:
            status_bits.append("done_prefix_missing_out")
        if out_members and not done_members:
            status_bits.append("out_prefix_missing_done")
        if prefix.startswith("__NO_RF__::"):
            status_bits.append("missing_rf_marker")
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


def selectable_groups(image_review_dir: Path) -> list[tuple[str, list[Path]]]:
    group_size, _id_root, label_review_dir = parse_review_dir(image_review_dir)
    if group_size <= 1:
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
        if len(members) != group_size:
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
    if group_size <= 1:
        raise ManualReviewError("GroupSize_1 不进入人工择一队列。")
    if len(members) != group_size:
        raise ManualReviewError(f"当前 prefix 根部图片数不是 {group_size}: {prefix} -> {len(members)}")
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
        group_size=group_size,
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


def output_root_for_id_root(id_root: Path) -> Path:
    project = id_root.resolve().parents[2] if len(id_root.resolve().parents) >= 3 else Path.cwd()
    return project / "Dataset" / "Select_Programme" / "Audit_Reports"


def export_audit_report(id_root: Path, output_root: Path | None = None) -> Path:
    id_root = id_root.resolve()
    output_root = output_root.resolve() if output_root else output_root_for_id_root(id_root)
    timecode = datetime.now().strftime("%Y%m%d%H%M")
    run_dir = output_root / f"YOLO_Source_Group_Picker_Audit_V1.0_{timecode}"
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


def build_markdown_summary(id_root: Path, summaries: list[dict[str, Any]], timecode: str) -> str:
    rows = []
    for item in summaries:
        n = item["group_size"]
        formula = f"done x {max(n - 1, 0)}" if n > 1 else "original singleton"
        label_sync = "N/A" if n <= 1 else ("PASS" if item.get("label_position_sync_pass") else "PENDING/FAIL")
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
        "# YOLO Source Group Picker Audit Summary\n\n"
        "## English\n"
        f"- Status: {STATUS}.\n"
        f"- Audit target: `{id_root}`.\n"
        "- This audit checks the V1.0 source-group review working folders only. Global `Done` and `transformations` folders are outside scope.\n"
        "- Image rule: `done` has one representative per prefix; `out` has `N - 1` images per same prefix; "
        "`out = done x (N - 1)`.\n"
        "- No images or labels were deleted, overwritten, or edited by this report export.\n\n"
        "## 中文\n"
        f"- 状态：{STATUS}。\n"
        f"- 审计对象：`{id_root}`。\n"
        "- 本审计只检查 V1.0 图源组审核工作目录，全局 `Done` 和 `transformations` 不属于本工具范围。\n"
        "- 图片规则：`done` 每个前缀一张代表图；`out` 同一前缀应有 `N - 1` 张；"
        "`out = done x (N - 1)`。\n"
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
        self.root.title("YOLO Source Group Picker V1.0")
        self.root.geometry("1280x820")
        self.id_root: Path | None = None
        self.current_review_dir: Path | None = None
        self.current_groups: list[tuple[str, list[Path]]] = []
        self.current_index = 0
        self.photo_refs: list[Any] = []
        self.last_transaction: MoveTransaction | None = None
        self.pending_click_after: str | None = None
        self.auto_next = tk.BooleanVar(value=True)

        self._build_ui()
        if review_dir:
            _n, id_root_from_review, _lab = parse_review_dir(review_dir)
            self.load_id_root(id_root_from_review)
            self.select_review_dir(review_dir)
        elif id_root:
            self.load_id_root(id_root)

    def _build_ui(self) -> None:
        top = ttk.Frame(self.root)
        top.pack(fill="x", padx=8, pady=6)
        ttk.Button(top, text="选择 ID 根目录", command=self.choose_id_root).pack(side="left")
        ttk.Button(top, text="导出校核报告", command=self.export_report).pack(side="left", padx=6)
        ttk.Button(top, text="撤销上一组", command=self.undo_last).pack(side="left", padx=6)
        ttk.Checkbutton(top, text="自动进入下一组", variable=self.auto_next).pack(side="left", padx=12)
        self.path_var = tk.StringVar(value="未选择目录")
        ttk.Label(top, textvariable=self.path_var).pack(side="left", padx=12)

        body = ttk.PanedWindow(self.root, orient="horizontal")
        body.pack(fill="both", expand=True, padx=8, pady=6)

        left = ttk.Frame(body, width=360)
        body.add(left, weight=0)
        ttk.Label(left, text="图源组审核目录").pack(anchor="w")
        self.dir_list = tk.Listbox(left, height=16, exportselection=False)
        self.dir_list.pack(fill="both", expand=False, pady=4)
        self.dir_list.bind("<<ListboxSelect>>", self.on_dir_select)
        self.dir_items: list[Path] = []

        self.audit_text = tk.Text(left, height=24, wrap="word")
        self.audit_text.pack(fill="both", expand=True, pady=4)

        right = ttk.Frame(body)
        body.add(right, weight=1)
        self.formula_var = tk.StringVar(value="等待扫描")
        ttk.Label(right, textvariable=self.formula_var, font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=4)
        controls = ttk.Frame(right)
        controls.pack(fill="x")
        ttk.Button(controls, text="上一组", command=self.prev_group).pack(side="left")
        ttk.Button(controls, text="下一组", command=self.next_group).pack(side="left", padx=6)
        self.group_var = tk.StringVar(value="")
        ttk.Label(controls, textvariable=self.group_var).pack(side="left", padx=12)

        self.canvas = tk.Canvas(right, background="#f7f7f7")
        self.canvas.pack(fill="both", expand=True, pady=6)
        self.canvas.bind("<Configure>", lambda _event: self.render_current_group())

    def choose_id_root(self) -> None:
        selected = filedialog.askdirectory(title="选择 YOLO 数据集根目录（包含 images 和 labels）")
        if selected:
            self.load_id_root(Path(selected))

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
        self.refresh_current_review()

    def refresh_current_review(self) -> None:
        if self.current_review_dir is None:
            return
        try:
            summary, _rows = audit_review_dir(self.current_review_dir, create_missing=True)
            self.current_groups = selectable_groups(self.current_review_dir)
            self.write_audit(summary)
            self.formula_var.set(self.formula_text(summary))
        except Exception as exc:
            self.current_groups = []
            self.audit_text.delete("1.0", "end")
            self.audit_text.insert("end", str(exc))
            self.formula_var.set("目录校核失败")
        self.render_current_group()

    def write_audit(self, summary: AuditSummary) -> None:
        self.audit_text.delete("1.0", "end")
        data = asdict(summary)
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
            json.dumps(data, ensure_ascii=False, indent=2),
        ]
        self.audit_text.insert("end", "\n".join(lines))

    @staticmethod
    def formula_text(summary: AuditSummary) -> str:
        if summary.group_size <= 1:
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

    def render_current_group(self) -> None:
        self.canvas.delete("all")
        self.photo_refs = []
        if not self.current_groups:
            self.canvas.create_text(30, 30, anchor="nw", text="没有可筛选组或目录存在阻断项。", fill="#333")
            self.group_var.set("0 / 0")
            return
        self.current_index = max(0, min(self.current_index, len(self.current_groups) - 1))
        prefix, members = self.current_groups[self.current_index]
        self.group_var.set(f"{self.current_index + 1} / {len(self.current_groups)} | {prefix}")
        width = max(self.canvas.winfo_width(), 800)
        height = max(self.canvas.winfo_height(), 500)
        cols = min(len(members), 3)
        card_w = max(260, (width - 40) // max(cols, 1))
        card_h = max(240, (height - 60) // ((len(members) + cols - 1) // cols))
        for idx, image_path in enumerate(members):
            col = idx % cols
            row = idx // cols
            x = 18 + col * card_w
            y = 18 + row * card_h
            self.draw_card(image_path, x, y, card_w - 16, card_h - 16)

    def draw_card(self, image_path: Path, x: int, y: int, w: int, h: int) -> None:
        bg_id = self.canvas.create_rectangle(x, y, x + w, y + h, outline="#999", width=1, fill="#ffffff")
        preview_h = h - 58
        image_item_id: int | None = None
        try:
            with Image.open(image_path) as img:
                img = img.copy()
                img.thumbnail((w - 16, preview_h - 10), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.photo_refs.append(photo)
                image_item_id = self.canvas.create_image(x + w // 2, y + 8, anchor="n", image=photo)
        except Exception as exc:
            self.canvas.create_text(x + 10, y + 20, anchor="nw", text=f"读取失败: {exc}", fill="#b00020")
        label = image_path.name if len(image_path.name) <= 62 else image_path.name[:58] + "..."
        text_id = self.canvas.create_text(x + 8, y + h - 44, anchor="nw", text=label, fill="#222", width=w - 16)
        bind_ids = [bg_id, text_id]
        if image_item_id is not None:
            bind_ids.append(image_item_id)
        for item_id in bind_ids:
            self.canvas.tag_bind(item_id, "<Button-1>", lambda _event, p=image_path: self.schedule_choose_source(p))
            self.canvas.tag_bind(item_id, "<Double-Button-1>", lambda _event, p=image_path: self.handle_double_open(p))

    def schedule_choose_source(self, image_path: Path) -> None:
        if self.pending_click_after is not None:
            self.root.after_cancel(self.pending_click_after)
        self.pending_click_after = self.root.after(240, lambda p=image_path: self.run_scheduled_choice(p))

    def run_scheduled_choice(self, image_path: Path) -> None:
        self.pending_click_after = None
        self.choose_source(image_path)

    def handle_double_open(self, image_path: Path) -> None:
        if self.pending_click_after is not None:
            self.root.after_cancel(self.pending_click_after)
            self.pending_click_after = None
        self.open_full_image(image_path)

    def choose_source(self, image_path: Path) -> None:
        if self.current_review_dir is None:
            return
        prefix, _mode = get_prefix(image_path)
        if prefix is None:
            messagebox.showerror("无法处理", "选中图片缺少 .rf. prefix。")
            return
        try:
            transaction = prepare_transaction(self.current_review_dir, prefix, image_path)
            self.last_transaction = execute_transaction(transaction)
        except Exception as exc:
            messagebox.showerror("整组移动已阻断", str(exc))
            self.refresh_current_review()
            return
        self.refresh_current_review()
        if not self.auto_next.get():
            messagebox.showinfo("已完成", f"已处理 prefix: {prefix}")

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
        if self.current_groups:
            self.current_index = min(self.current_index + 1, len(self.current_groups) - 1)
            self.render_current_group()

    def prev_group(self) -> None:
        if self.current_groups:
            self.current_index = max(self.current_index - 1, 0)
            self.render_current_group()

    def undo_last(self) -> None:
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

    def run(self) -> None:
        self.root.mainloop()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="YOLO source-group image picker and label-synchronised cleanup GUI.")
    parser.add_argument("--id-root", default="", help="YOLO-style dataset root containing sibling images/ and labels/ folders.")
    parser.add_argument("--review-dir", default="", help="Specific images/ManualReview_GroupSize_N source-group review directory.")
    parser.add_argument("--audit-only", action="store_true", help="Export an audit report and exit without launching GUI.")
    parser.add_argument("--output-root", default="", help="Optional Select_Programme output root for --audit-only.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    id_root = Path(args.id_root).resolve() if args.id_root else None
    review_dir = Path(args.review_dir).resolve() if args.review_dir else None
    if args.audit_only:
        if not id_root and review_dir:
            _n, id_root_from_review, _lab = parse_review_dir(review_dir)
            id_root = id_root_from_review
        if not id_root:
            raise ManualReviewError("--audit-only requires --id-root or --review-dir.")
        output_root = Path(args.output_root).resolve() if args.output_root else None
        run_dir = export_audit_report(id_root, output_root=output_root)
        print(json.dumps({"status": STATUS, "run_dir": str(run_dir)}, ensure_ascii=False))
        return 0
    app = ManualReviewPickerApp(id_root=id_root, review_dir=review_dir)
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
