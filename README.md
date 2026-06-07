# YOLO Transformed Dataset Cleaning Browser

[中文说明](README.zh-CN.md)

![Version](https://img.shields.io/badge/latest-V2.2__202606042006-094438)
![Python](https://img.shields.io/badge/python-3.11-D1C18D)
![GUI](https://img.shields.io/badge/GUI-PySide6-009CD5)
![Status](https://img.shields.io/badge/audit-PENDING__AUDIT-EF4022)

A desktop review browser for cleaning transformed, duplicated, or near-duplicated image variants in YOLO-style computer-vision datasets. It helps dataset maintainers compare related image groups, keep or separate candidates, synchronise YOLO `.txt` labels, and keep the whole review process auditable.

This repository is released in the same order as the internal programme builds. The current public release is aligned with internal build `V2.2_202606042006`.

## Current Release: V2.2_202606042006

`V2.2_202606042006` is an interaction polish release over V2.1. It keeps the fast source-group review workflow while reducing friction for high-throughput manual cleaning.

New in V2.2:

- Removes typed `MOVE` confirmation.
- Shows a Chinese startup safety notice, then arms automatic move readiness.
- Automatically enables file movement only after lock, recovery scan, FastReviewIndex, full audit, and transaction-log checks pass.
- Replaces the left vertical sidebar with a compact horizontal navigation card row.
- Makes the Review Board table resize with the window, with priority width for directory names.
- Restores HKU Academic Red `#EF4022` selection feedback on image cards.
- Tightens global rounded-corner radii for a denser, more practical review workspace.
- Keeps image2/procedural abstract UI assets and no-raster-asset policy.

Verification:

```text
V2.2 Qt tests: 7/7 OK
V2.1 Qt regression: 5/5 OK
V1.9.1 Qt regression: 7/7 OK
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
YOLO_Transformed_Dataset_Cleaning_Browser_V2.2_202606042006.zip
```

Run:

```text
Dataset/Select_Programme/Executable/CIVL7009_Source_Group_Picker_V2.2_202606042006.exe
```

Run from source:

```powershell
uv run --with PySide6==6.11.1 --with Pillow python Dataset/Select_Programme/CIVL7009_source_group_picker_qt_V2.2_202606042006.py
```

Run tests:

```powershell
uv run --with PySide6==6.11.1 --with Pillow python Dataset/Select_Programme/test_source_group_picker_qt_V2.2_202606042006.py
uv run --with PySide6==6.11.1 --with Pillow python Dataset/Select_Programme/test_source_group_picker_qt_V2.1_202606041930.py
uv run --with PySide6==6.11.1 --with Pillow python Dataset/Select_Programme/test_source_group_picker_qt_V1.9.1_202606041705.py
uv run python Dataset/Select_Programme/test_source_group_picker_gui_V1.8.1_202606041443.py
```

## Safety Boundary

The release package does not contain raw dataset images, labels, runtime logs, audit outputs, model weights, or dataset archives. File movement remains limited to explicit review workflows and guarded features. Audit outputs remain `PENDING_AUDIT`.

