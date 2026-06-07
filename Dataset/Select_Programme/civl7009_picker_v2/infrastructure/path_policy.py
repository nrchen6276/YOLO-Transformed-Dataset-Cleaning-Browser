from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class PathPolicyResult:
    ok: bool
    error_code: str = ""
    message: str = ""


def is_probably_network_drive(path: Path) -> bool:
    raw = str(path)
    return raw.startswith("\\\\")


def is_same_volume(a: Path, b: Path) -> bool:
    return Path(a).resolve().drive.casefold() == Path(b).resolve().drive.casefold()


def validate_inside(parent: Path, child: Path) -> PathPolicyResult:
    parent_resolved = parent.resolve()
    child_resolved = child.resolve()
    try:
        child_resolved.relative_to(parent_resolved)
    except ValueError:
        return PathPolicyResult(False, "PATH_INVALID", f"目标路径逃逸 review dir: {child_resolved}")
    return PathPolicyResult(True)


def validate_for_staging(review_dir: Path, target: Path, same_volume_required: bool = True) -> PathPolicyResult:
    if len(str(target.resolve())) > 240:
        return PathPolicyResult(False, "LONG_PATH_EXCEEDED", "路径接近或超过 Windows 兼容长度限制。")
    if is_probably_network_drive(target):
        return PathPolicyResult(False, "NETWORK_DRIVE_UNSUPPORTED", "默认不支持网络盘 staging。")
    if same_volume_required and not is_same_volume(review_dir, target):
        return PathPolicyResult(False, "CROSS_VOLUME_MOVE_BLOCKED", "physical staging 默认要求同一卷。")
    if target.exists() and target.is_symlink():
        return PathPolicyResult(False, "SYMLINK_OR_JUNCTION_BLOCKED", "默认阻断符号链接或 junction。")
    return validate_inside(review_dir, target)


def casefold_child_map(path: Path) -> dict[str, list[Path]]:
    mapping: dict[str, list[Path]] = {}
    if not path.exists():
        return mapping
    for child in path.iterdir():
        if child.is_dir():
            mapping.setdefault(child.name.casefold(), []).append(child)
    return mapping


def detect_casefold_collision(path: Path, names: set[str]) -> PathPolicyResult:
    mapping = casefold_child_map(path)
    for wanted in names:
        variants = mapping.get(wanted.casefold(), [])
        if len(variants) > 1:
            return PathPolicyResult(False, "CASEFOLD_COLLISION", f"目录大小写碰撞: {[v.name for v in variants]}")
    return PathPolicyResult(True)


def is_read_only(path: Path) -> bool:
    try:
        return not os.access(path, os.W_OK)
    except OSError:
        return True
