# YOLO Transformed Dataset Cleaning Browser

[中文说明](README.zh-CN.md)

![Version](https://img.shields.io/badge/latest-V1.8.2__202606042313-094438)
![Python](https://img.shields.io/badge/python-3.11-D1C18D)
![GUI](https://img.shields.io/badge/GUI-Tkinter-009CD5)
![Status](https://img.shields.io/badge/audit-PENDING__AUDIT-EF4022)

A lightweight review browser for cleaning transformed, duplicated, or near-duplicated image variants in YOLO-style computer-vision datasets. It helps dataset maintainers compare source-related image groups, keep a representative source image, separate variant images into `out`, and keep YOLO `.txt` labels synchronised with the image decision.

This repository is released in the same order as the internal programme builds. The current public release is aligned with internal build `V1.8.2_202606042313`.

## Why This Exists

YOLO training datasets often contain multiple transformed versions of the same underlying image: rotations, crops, colour edits, augmentations, re-exports, or near-duplicates. If those variants are treated as independent sources without review, later training, leakage checks, and data-quality audits become harder to explain.

This tool turns that cleaning task into a visual review workflow. A reviewer sees one source-related group at a time, selects the image to keep as the source representative, and lets the tool move variants and labels into the intended review folders with a process trail. Governance outputs remain `PENDING_AUDIT`.

## Current Release: V1.8.2_202606042313

`V1.8.2_202606042313` is a source-only core compatibility release. It follows `V1.8.1_202606041443` exactly in the internal version sequence and preserves the core file later bundled by Qt/PySide6 shells.

Important boundary:

- The internal artefact set contains the V1.8.2 core source file, but no same-version standalone executable, PyInstaller spec, or dedicated V1.8.2 test file.
- The GitHub asset for this release is therefore a source/core package, not a Windows executable package.
- The original V1.8.2 source is released as-is for version-order fidelity.

New or relevant in V1.8.2:

- Keeps the V1.8.1 `FastReviewIndex`, quick preview, transaction journal, recovery scan, review lock, dynamic `.rf.` grouping, label lookup, background move queue, and audit export core.
- Keeps the CLI entry points for GUI launch, direct review-folder selection, and `--audit-only`.
- Keeps runtime log splitting by run mode and source-group transaction safety.
- Acts as the versioned core used by later Qt/PySide6 UI builds.

Known issue found during release verification:

- Replaying the V1.8.1 regression suite against the V1.8.2 core produced `30 tests OK, 2 errors, skipped=1`.
- The two errors are both in YOLO initialisation helper tests and trace to `audit_yolo_dataset()` referencing an undefined `group_size`.
- Source-group review, transaction, lock, undo, fast-index, and audit-path tests in the replayed suite passed.

## Core Capabilities

- Select an image review folder directly.
- Infer the matching `labels/...` folder from the selected `images/...` folder.
- Accept an explicit `--label-dir` when needed.
- Group images by dynamic `.rf.` source-prefix logic in ordinary or ad-hoc review folders.
- Keep compatibility with classic `ManualReview_GroupSize_N` folders.
- Block duplicate labels, missing labels, target conflicts, and incomplete groups.
- Move selected source image/label to `done` and variants to `out`.
- Export JSON, CSV, and Markdown audit reports.
- Record transaction journals and recovery snapshots for source-group moves.
- Use review-directory locks to avoid concurrent edits to the same working folder.
- Use fast in-memory review indexing and quick preview loading for large working folders.
- Navigate previous/next groups and open a 100% original image viewer.
- Use number-key shortcuts following the traditional keypad layout.

## What It Does Not Include

- It does not train, evaluate, or modify any model.
- It does not generate hash or near-hash Manual Objects candidate groups.
- It does not include later PySide6, Manual Objects review, conflict review, Tier-prefix governance, or N20_PLUS workflows.
- It does not provide a same-version V1.8.2 Windows executable.
- It does not delete, overwrite, upload, or expose raw dataset images or labels.
- Audit outputs remain `PENDING_AUDIT`; they are process evidence, not model-performance claims.

## Expected Working Folder Shape

V1.8.2 supports standard or ad-hoc YOLO-style review trees:

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
YOLO_Transformed_Dataset_Cleaning_Browser_V1.8.2_202606042313.zip
```

Run from source:

```powershell
uv run --with pillow python Dataset/Select_Programme/CIVL7009_source_group_picker_gui_V1.8.2_202606042313.py
```

Show CLI help:

```powershell
uv run --with pillow python Dataset/Select_Programme/CIVL7009_source_group_picker_gui_V1.8.2_202606042313.py --help
```

Expected release verification:

```text
source --help OK
V1.8.1 regression suite replayed against V1.8.2 core: 30 OK, 2 errors, skipped=1
```

## Safety Boundary

The release package does not contain raw dataset images, labels, runtime logs, audit outputs, model weights, or dataset archives. File movement happens only inside the review folder selected by the user, and only when the reviewer executes a source-group decision.
