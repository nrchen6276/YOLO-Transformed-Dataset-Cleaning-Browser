# YOLO Transformed Dataset Cleaning Browser

[中文说明](README.zh-CN.md)

![Version](https://img.shields.io/badge/latest-V2.1__202606041930-094438)
![Python](https://img.shields.io/badge/python-3.11-D1C18D)
![GUI](https://img.shields.io/badge/GUI-PySide6-009CD5)
![Status](https://img.shields.io/badge/audit-PENDING__AUDIT-EF4022)

A desktop review browser for cleaning transformed, duplicated, or near-duplicated image variants in YOLO-style computer-vision datasets. It helps dataset maintainers compare related image groups, keep or separate candidates, synchronise YOLO `.txt` labels, and keep the whole review process auditable.

This repository is released in the same order as the internal programme builds. The current public release is aligned with internal build `V2.1_202606041930`.

## Current Release: V2.1_202606041930

`V2.1_202606041930` rebuilds the interaction layer on top of the V2 framework. It restores the fast review workflow from the earlier stable line and makes the manual review page image-first again.

New in V2.1:

- Rebuilt PySide6 package: `civl7009_picker_v2_1/`.
- Clear directory entry points for selecting an ID root or directly selecting a review folder.
- Horizontal workflow navigation rather than a space-hungry vertical sidebar.
- Dynamic image keypad stage for group sizes from 1 to 9+, with number-key shortcuts.
- image2/procedural abstract UI assets for empty states, loading, safe-gate badges, review board, diagnostics, and shortcuts.
- Safe Gate preview mode preserved: file moves happen only after the gated review flow is ready.
- Background move queue, undo, red highlight feedback, and audit export remain part of the review workflow.

Verification:

```text
V2.1 Qt tests: 5/5 OK
V1.9.1 Qt tests: 7/7 OK
V1.8.1 backend tests: 32 OK, skipped=1
source --help OK
source --smoke-open OK
exe --help OK
exe --smoke-open OK
zip extraction smoke OK
```

## What It Is For

YOLO training datasets often contain transformed versions of the same underlying image: rotations, crops, colour edits, augmentations, re-exports, or near-duplicates. If those variants are treated as independent samples without review, later training, leakage checks, and data-quality audits become harder to explain.

This tool turns that cleaning task into a visual review workflow. A reviewer sees one related group at a time, makes a decision, and keeps a process trail. Governance outputs remain `PENDING_AUDIT`; they are operational evidence, not model-performance claims.

## Quick Start

Download:

```text
YOLO_Transformed_Dataset_Cleaning_Browser_V2.1_202606041930.zip
```

Run:

```text
Dataset/Select_Programme/Executable/CIVL7009_Source_Group_Picker_V2.1_202606041930.exe
```

Run from source:

```powershell
uv run --with PySide6==6.11.1 --with Pillow python Dataset/Select_Programme/CIVL7009_source_group_picker_qt_V2.1_202606041930.py
```

Run tests:

```powershell
uv run --with PySide6==6.11.1 --with Pillow python Dataset/Select_Programme/test_source_group_picker_qt_V2.1_202606041930.py
uv run --with PySide6==6.11.1 --with Pillow python Dataset/Select_Programme/test_source_group_picker_qt_V1.9.1_202606041705.py
uv run python Dataset/Select_Programme/test_source_group_picker_gui_V1.8.1_202606041443.py
```

## Safety Boundary

The release package does not contain raw dataset images, labels, runtime logs, audit outputs, model weights, or dataset archives. File movement remains limited to explicit review workflows and guarded features. Audit outputs remain `PENDING_AUDIT`.

