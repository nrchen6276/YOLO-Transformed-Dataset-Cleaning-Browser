# YOLO Transformed Dataset Cleaning Browser

[中文说明](README.zh-CN.md)

![Version](https://img.shields.io/badge/latest-V1.9__202606041626-094438)
![Python](https://img.shields.io/badge/python-3.11-D1C18D)
![GUI](https://img.shields.io/badge/GUI-PySide6-009CD5)
![Status](https://img.shields.io/badge/audit-PENDING__AUDIT-EF4022)

A desktop review browser for cleaning transformed, duplicated, or near-duplicated image variants in YOLO-style computer-vision datasets. It helps dataset maintainers compare source-related image groups, keep a representative source image, separate variant images into `out`, and keep YOLO `.txt` labels synchronised with the image decision.

This repository is released in internal-version order. The current public release is aligned with internal build `V1.9_202606041626`.

## Why This Exists

YOLO training datasets often contain multiple transformed versions of the same underlying image: rotations, crops, colour edits, augmentations, re-exports, or near-duplicates. If those variants are treated as independent sources without review, later training, leakage checks, and data-quality audits become harder to explain.

This tool turns that cleaning task into a visual review workflow. A reviewer sees one source-related group at a time, selects the image to keep as the source representative, and lets the tool move variants and labels into the intended review folders with a process trail. Governance outputs remain `PENDING_AUDIT`.

## Current Release: V1.9_202606041626

`V1.9_202606041626` is the first PySide6 Review Cockpit release in the internal sequence. It adds a Qt desktop shell while preserving the tested V1.8.1 backend core for source-group audit, FastReviewIndex, file transactions, recovery, locks, and undo.

New in V1.9:

- PySide6 Review Cockpit desktop shell.
- Safe Gate workflow: preview-only by default; file movement requires explicit enabling inside the app.
- Core auditability: logs record UI version, backend core version, core file path, and SHA256.
- Core load validation: missing symbols or invalid backend core fails closed.
- Open-review progress overlay and ready state before committing moves.
- Qt-safe worker pattern for review opening, background indexing, thumbnails, audit, and export.
- Abstract SVG UI assets with an asset manifest declaring no dataset imagery.
- ID Initialisation remains a read-only/fallback area in this release.
- Windows executable included as the release asset.

Verification for this release:

```text
V1.9 Qt tests: 6/6 OK
V1.8.1 backend tests: 32 OK, skipped=1
source --help OK
exe audit-only smoke OK on a temporary sample dataset
```

## Core Capabilities

- Select an image review folder directly.
- Infer the matching `labels/...` folder from the selected `images/...` folder.
- Group images by dynamic `.rf.` source-prefix logic in ordinary or ad-hoc review folders.
- Keep compatibility with classic `ManualReview_GroupSize_N` folders.
- Block duplicate labels, missing labels, target conflicts, incomplete groups, and recovery conflicts.
- Move selected source image/label to `done` and variants to `out` after Safe Gate is enabled.
- Export JSON, CSV, and Markdown audit reports.
- Record transaction journals and recovery snapshots for source-group moves.
- Use review-directory locks to avoid concurrent edits to the same working folder.
- Use fast in-memory review indexing and quick preview loading for large working folders.
- Navigate previous/next groups and open a 100% original image viewer.
- Use number-key shortcuts following the traditional keypad layout.

## What It Does Not Include

- It does not train, evaluate, or modify any model.
- It does not generate hash or near-hash Manual Objects candidate groups.
- It does not include later Manual Objects review, conflict review, Tier-prefix governance, or N20_PLUS workflows.
- It does not delete, overwrite, upload, or expose raw dataset images or labels.
- Audit outputs remain `PENDING_AUDIT`; they are process evidence, not model-performance claims.

## Expected Working Folder Shape

V1.9 supports standard or ad-hoc YOLO-style review trees:

```text
<dataset-root>/
  images/
    <review-folder>/
      *.jpg
      done/
      out/
  labels/
    <review-folder>/
      *.txt
      done/
      out/
      Done_auto/
      Out_auto/
```

Classic names such as `ManualReview_GroupSize_N` remain supported. Non-standard review folders may also be used when files can be grouped by `.rf.` prefix and each selectable prefix has at least two images.

## Quick Start

Download the release asset:

```text
YOLO_Transformed_Dataset_Cleaning_Browser_V1.9_202606041626.zip
```

Unzip it and run:

```text
Dataset/Select_Programme/Executable/CIVL7009_Source_Group_Picker_V1.9_202606041626.exe
```

Run from source:

```powershell
uv run --with PySide6==6.11.1 --with Pillow python Dataset/Select_Programme/CIVL7009_source_group_picker_qt_V1.9_202606041626.py
```

Run tests:

```powershell
uv run --with PySide6==6.11.1 --with Pillow python Dataset/Select_Programme/test_source_group_picker_qt_V1.9_202606041626.py
uv run python Dataset/Select_Programme/test_source_group_picker_gui_V1.8.1_202606041443.py
```

## Safety Boundary

The release package does not contain raw dataset images, labels, runtime logs, audit outputs, model weights, or dataset archives. File movement happens only inside the review folder selected by the user, and only after the reviewer enables the Safe Gate workflow.
