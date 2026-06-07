# YOLO Transformed Dataset Cleaning Browser

[中文说明](README.zh-CN.md)

![Version](https://img.shields.io/badge/latest-V2.0__202606041822-094438)
![Python](https://img.shields.io/badge/python-3.11-D1C18D)
![GUI](https://img.shields.io/badge/GUI-PySide6-009CD5)
![Status](https://img.shields.io/badge/audit-PENDING__AUDIT-EF4022)

A desktop review browser for cleaning transformed, duplicated, or near-duplicated image variants in YOLO-style computer-vision datasets. It helps dataset maintainers compare related image groups, keep or separate candidates, synchronise YOLO `.txt` labels, and keep the whole review process auditable.

This repository is released in the same order requested for the public programme builds. The current public release is aligned with internal build `V2.0_202606041822`.

## Why This Exists

YOLO training datasets often contain multiple transformed versions of the same underlying image: rotations, crops, colour edits, augmentations, re-exports, or near-duplicates. If those variants are treated as independent samples without review, later training, leakage checks, and data-quality audits become harder to explain.

This tool turns that cleaning task into a visual review workflow. A reviewer sees one related group at a time, makes a decision, and keeps a process trail. Governance outputs remain `PENDING_AUDIT`; they are operational evidence, not model-performance claims.

## Current Release: V2.0_202606041822

`V2.0_202606041822` is the full PySide6 framework release. It keeps the V1.8.1/V1.9.1 safety boundary and adds a modular application structure for future review workflows.

New in V2.0:

- Modular PySide6 framework package: `civl7009_picker_v2/`.
- Capability Matrix for feature flags, risk levels, raw-file movement status, and gates.
- Manifest-only queue framework enabled by default, without moving raw files.
- SQLite manifest integrity checks, schema metadata, and migration guardrails.
- Default-off physical staging framework with same-volume and recovery safeguards.
- Recovery Centre, Diagnostics Panel, Productivity Dashboard, and Settings pages.
- ID Initialisation Wizard structure with dry-run-first policy.
- image2/procedural abstract UI assets and design tokens.
- Light, dark, high-contrast, and visual-quality foundations.
- Windows executable included as a release asset.

Verification for this release:

```text
V2.0 Qt/framework tests: 9/9 OK
V1.9.1 Qt tests: 7/7 OK
V1.8.1 backend tests: 32 OK, skipped=1
source --help OK
source --smoke-open OK
exe --help OK
exe --smoke-open OK
zip extraction smoke OK
```

## Core Capabilities

- Review source-related image groups in YOLO-style folders.
- Keep compatibility with classic `ManualReview_GroupSize_N` folders and ad-hoc `.rf.` grouped folders.
- Use Safe Gate controlled file movement for source-group review.
- Keep image-label pairing checks, duplicate-label blocks, target-conflict blocks, recovery snapshots, and review-directory locks.
- Maintain fast in-memory review indexing for large working folders.
- Export audit reports and process metadata.
- Display framework pages for staging, recovery, initialisation, diagnostics, dashboard, and settings.
- Keep physical staging disabled by default.
- Keep manifest-only queue non-mutating by default.

## What It Does Not Include

- It does not train, evaluate, or modify any model.
- It does not generate hash or near-hash candidate groups.
- It does not include later Manual Objects review, conflict review, Tier-prefix governance, or N20_PLUS workflows.
- It does not delete, overwrite, upload, or expose raw dataset images or labels.
- Audit outputs remain `PENDING_AUDIT`.

## Quick Start

Download the release asset:

```text
YOLO_Transformed_Dataset_Cleaning_Browser_V2.0_202606041822.zip
```

Unzip it and run:

```text
Dataset/Select_Programme/Executable/CIVL7009_Source_Group_Picker_V2.0_202606041822.exe
```

Run from source:

```powershell
uv run --with PySide6==6.11.1 --with Pillow python Dataset/Select_Programme/CIVL7009_source_group_picker_qt_V2.0_202606041822.py
```

Run tests:

```powershell
uv run --with PySide6==6.11.1 --with Pillow python Dataset/Select_Programme/test_source_group_picker_qt_V2.0_202606041822.py
uv run --with PySide6==6.11.1 --with Pillow python Dataset/Select_Programme/test_source_group_picker_qt_V1.9.1_202606041705.py
uv run python Dataset/Select_Programme/test_source_group_picker_gui_V1.8.1_202606041443.py
```

## Safety Boundary

The release package does not contain raw dataset images, labels, runtime logs, audit outputs, model weights, or dataset archives. File movement remains limited to explicit review workflows and guarded features. Manifest-only queue is non-mutating; physical staging is off by default.
