# YOLO Transformed Dataset Cleaning Browser

[中文说明](README.zh-CN.md)

![Version](https://img.shields.io/badge/latest-V2.2.1__202606042101-094438)
![Python](https://img.shields.io/badge/python-3.11-D1C18D)
![GUI](https://img.shields.io/badge/GUI-PySide6-009CD5)
![Status](https://img.shields.io/badge/audit-PENDING__AUDIT-EF4022)

A desktop review browser for cleaning transformed, duplicated, or near-duplicated image variants in YOLO-style computer-vision datasets. It helps dataset maintainers compare related image groups, keep or separate candidates, synchronise YOLO `.txt` labels, and keep the whole review process auditable.

This repository is released in the same order as the internal programme builds. The current public release is aligned with internal build `V2.2.1_202606042101`.

## Current Release: V2.2.1_202606042101

`V2.2.1_202606042101` is a standalone executable hotfix for V2.2. It fixes `Core Load Failed` when the exe is copied to another computer or folder without the source tree beside it.

What changed:

- The core loader now checks the PyInstaller `_MEIPASS` bundled core before sibling paths.
- Single-file exe smoke confirms that the V1.8.1 backend core is loaded from the bundled extraction directory.
- Core-load failures now log candidate paths and failure details.
- V2.2 automatic move readiness, horizontal navigation, dynamic keypad layout, and HKU red selection feedback are preserved.

Verification:

```text
V2.2.1 Qt tests: 8/8 OK
V2.2 Qt regression: 7/7 OK
V2.1 Qt regression: 5/5 OK
V1.8.1 backend tests: 32 OK, skipped=1
source --help OK
source --smoke-open --run-mode debug OK
exe --help OK
exe --smoke-open OK
standalone copied-exe smoke OK
zip extraction smoke OK
```

## What It Is For

YOLO training datasets often contain transformed versions of the same underlying image: rotations, crops, colour edits, augmentations, re-exports, or near-duplicates. If those variants are treated as independent samples without review, later training, leakage checks, and data-quality audits become harder to explain.

This tool turns that cleaning task into a visual review workflow. A reviewer sees one related group at a time, makes a decision, and keeps a process trail. Governance outputs remain `PENDING_AUDIT`; they are operational evidence, not model-performance claims.

## Quick Start

Download:

```text
YOLO_Transformed_Dataset_Cleaning_Browser_V2.2.1_202606042101.zip
```

Run:

```text
Dataset/Select_Programme/Executable/CIVL7009_Source_Group_Picker_V2.2.1_202606042101.exe
```

Run from source:

```powershell
uv run --with PySide6==6.11.1 --with Pillow python Dataset/Select_Programme/CIVL7009_source_group_picker_qt_V2.2.1_202606042101.py
```

Run tests:

```powershell
uv run --with PySide6==6.11.1 --with Pillow python Dataset/Select_Programme/test_source_group_picker_qt_V2.2.1_202606042101.py
uv run --with PySide6==6.11.1 --with Pillow python Dataset/Select_Programme/test_source_group_picker_qt_V2.2_202606042006.py
uv run --with PySide6==6.11.1 --with Pillow python Dataset/Select_Programme/test_source_group_picker_qt_V2.1_202606041930.py
uv run python Dataset/Select_Programme/test_source_group_picker_gui_V1.8.1_202606041443.py
```

## Safety Boundary

The release package does not contain raw dataset images, labels, runtime logs, audit outputs, model weights, or dataset archives. File movement remains limited to explicit review workflows and guarded features. Audit outputs remain `PENDING_AUDIT`.

