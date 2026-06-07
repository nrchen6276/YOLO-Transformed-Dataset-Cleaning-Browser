# YOLO Transformed Dataset Cleaning Browser

[中文说明](README.zh-CN.md)

![Version](https://img.shields.io/badge/latest-V2.0__202606041906-094438)
![Python](https://img.shields.io/badge/python-3.11-D1C18D)
![GUI](https://img.shields.io/badge/GUI-PySide6-009CD5)
![Status](https://img.shields.io/badge/audit-PENDING__AUDIT-EF4022)

A desktop review browser for cleaning transformed, duplicated, or near-duplicated image variants in YOLO-style computer-vision datasets. It helps dataset maintainers compare related image groups, keep or separate candidates, synchronise YOLO `.txt` labels, and keep the whole review process auditable.

This repository is released in the same order as the internal programme builds. The current public release is aligned with internal build `V2.0_202606041906`.

## Current Release: V2.0_202606041906

`V2.0_202606041906` is a V2.0 packaged-executable hotfix build. It preserves the V2.0 full PySide6 framework and fixes packaged startup behaviour: the previous packaged entry path could pass the executable path into `argparse` as an unexpected argument, causing the exe to close immediately on some machines.

It keeps the V2.0 framework:

- Modular PySide6 package: `civl7009_picker_v2/`.
- Capability Matrix for feature flags, risk levels, raw-file movement status, and gates.
- Manifest-only queue framework enabled by default, without moving raw files.
- SQLite manifest integrity checks, schema metadata, and migration guardrails.
- Default-off physical staging framework with same-volume and recovery safeguards.
- Recovery Centre, Diagnostics Panel, Productivity Dashboard, Settings, and ID Initialisation Wizard pages.
- image2/procedural abstract UI assets and design tokens.
- Light, dark, high-contrast, and visual-quality foundations.
- Windows executable included as a release asset.

Verification:

```text
V2.0 framework tests: 9/9 OK
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
YOLO_Transformed_Dataset_Cleaning_Browser_V2.0_202606041906.zip
```

Run:

```text
Dataset/Select_Programme/Executable/CIVL7009_Source_Group_Picker_V2.0_202606041906.exe
```

Run from source:

```powershell
uv run --with PySide6==6.11.1 --with Pillow python Dataset/Select_Programme/CIVL7009_source_group_picker_qt_V2.0_202606041906.py
```

Run tests:

```powershell
uv run --with PySide6==6.11.1 --with Pillow python Dataset/Select_Programme/test_source_group_picker_qt_V2.0_202606041822.py
uv run --with PySide6==6.11.1 --with Pillow python Dataset/Select_Programme/test_source_group_picker_qt_V1.9.1_202606041705.py
uv run python Dataset/Select_Programme/test_source_group_picker_gui_V1.8.1_202606041443.py
```

## Safety Boundary

The release package does not contain raw dataset images, labels, runtime logs, audit outputs, model weights, or dataset archives. File movement remains limited to explicit review workflows and guarded features. Manifest-only queue is non-mutating; physical staging is off by default.

