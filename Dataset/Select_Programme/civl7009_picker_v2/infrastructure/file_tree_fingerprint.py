from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ..config import IMAGE_EXTENSIONS, LABEL_EXTENSIONS


def file_tree_fingerprint(root: Path) -> dict[str, object]:
    counts = {"images": 0, "labels": 0, "manualreview_staging": 0, "done": 0, "out": 0, "root": 0}
    records: list[str] = []
    if not root.exists():
        return {"root": str(root), "exists": False, "counts": counts, "hash": ""}
    for item in root.rglob("*"):
        try:
            rel = item.relative_to(root).as_posix()
        except ValueError:
            continue
        if item.is_dir() and item.name == "_ManualReview_Staging":
            counts["manualreview_staging"] += 1
        if not item.is_file():
            continue
        ext = item.suffix.casefold()
        if ext in IMAGE_EXTENSIONS:
            counts["images"] += 1
        elif ext in LABEL_EXTENSIONS:
            counts["labels"] += 1
        parent = item.parent.name.casefold()
        if parent == "done":
            counts["done"] += 1
        elif parent == "out":
            counts["out"] += 1
        else:
            counts["root"] += 1
        stat = item.stat()
        records.append(f"{rel}|{stat.st_size}|{int(stat.st_mtime_ns)}")
    digest = hashlib.sha256("\n".join(sorted(records)).encode("utf-8")).hexdigest()
    return {"root": str(root), "exists": True, "counts": counts, "hash": digest}


def write_fingerprint(path: Path, root: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(file_tree_fingerprint(root), ensure_ascii=False, indent=2), encoding="utf-8")
