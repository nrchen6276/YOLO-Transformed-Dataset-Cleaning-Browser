# YOLO Transformed Dataset Cleaning Browser

[Chinese README](README.zh-CN.md)

![Version](https://img.shields.io/badge/latest-V1.3-094438)
![Python](https://img.shields.io/badge/python-3.11-D1C18D)
![GUI](https://img.shields.io/badge/GUI-Tkinter-009CD5)
![Status](https://img.shields.io/badge/audit-PENDING__AUDIT-EF4022)

A lightweight desktop browser for cleaning YOLO transformed datasets. It helps reviewers compare same-origin image variants, choose the representative source image, and keep YOLO label files synchronised while moving reviewed files into `done/out` folders.

## Why

YOLO training datasets often contain transformed versions of the same original image: rotations, crops, colour shifts, re-exports, augmentations, or near-duplicate variants. If those variants are treated as independent source material, downstream training and audit work can become harder to trust.

This tool turns that cleanup task into a visual review workflow: one source-prefix group at a time, one chosen representative, and label-synchronised movement for the rest.

## Current Release: V1.3

V1.3 focuses on smoother repeated review work.

New in V1.3:

- Cached label index for faster repeated YOLO `.txt` lookup.
- Current-group transaction preparation from already displayed image members.
- Background audit refresh after queued move completion.
- Upcoming-group preloading to warm preview cache.
- Regression coverage for cached-member and cached-label transaction preparation.
- V1.2 background move queue, failure rollback, preview cache, undo, and audit export remain available.

## Core Capabilities

- Direct image working-folder selection.
- Automatic `images/...` to `labels/...` pairing.
- Optional explicit `--label-dir`.
- Dynamic `.rf.` source-prefix group sizes for ad-hoc transformed review folders.
- Backward-compatible `ManualReview_GroupSize_N` folders.
- Strict duplicate-label, missing-label, and target-conflict blocking.
- Label-synchronised movement into `done/out`.
- Undo for the last completed transaction.
- JSON, CSV, and Markdown audit reports.
- Previous/next navigation and double-click full-size image viewing.
- Windows executable release asset.

## What It Does Not Do

- It does not train, evaluate, or modify any model.
- It does not delete, overwrite, edit, upload, or expose raw images or labels.
- It does not include V1.8+ FastReviewIndex, V1.9/V2 PySide6, Safe Gate, manifest queue, or staging features.
- Audit output remains `PENDING_AUDIT`; it is operational evidence, not a model-performance claim.

## Working Folder Model

V1.3 supports standard and ad-hoc review folders under a YOLO-style dataset tree:

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

The classic folder name `ManualReview_GroupSize_N` is still supported. Non-standard review folders are also supported when files can be grouped by `.rf.` prefix and each selectable prefix has more than one image.

## Quick Start

### Use the executable

Download the V1.3 release asset:

```text
YOLO_Transformed_Dataset_Cleaning_Browser_V1.3_202606050448.zip
```

After extraction, run:

```text
Executable/YOLO_Transformed_Dataset_Cleaning_Browser_V1.3_202606032313.exe
```

SHA256:

```text
ff9f79c7eb8e054385b7f0103deecf48c78590b50425801416da2a1a56dfe7b4
```

### Run from source

```powershell
uv run --with Pillow python Dataset/Select_Programme/CIVL7009_source_group_picker_gui_V1.3_202606032313.py
```

### Audit a dataset root

```powershell
uv run --with Pillow python Dataset/Select_Programme/CIVL7009_source_group_picker_gui_V1.3_202606032313.py `
  --audit-only `
  --id-root <dataset-root>
```

### Audit a single image working folder

```powershell
uv run --with Pillow python Dataset/Select_Programme/CIVL7009_source_group_picker_gui_V1.3_202606032313.py `
  --audit-only `
  --image-dir <dataset-root>/images/<review-folder>
```

## Tests

```powershell
uv run --with Pillow python Dataset/Select_Programme/test_source_group_picker_gui_V1.3_202606032313.py
```

V1.3 package test result: `16/16 OK`.

## Release Assets

- [V1.3 release](https://github.com/nrchen6276/YOLO-Transformed-Dataset-Cleaning-Browser/releases/tag/v1.3)
- `YOLO_Transformed_Dataset_Cleaning_Browser_V1.3_202606050448.zip`
- Source file: `Dataset/Select_Programme/CIVL7009_source_group_picker_gui_V1.3_202606032313.py`
- Test file: `Dataset/Select_Programme/test_source_group_picker_gui_V1.3_202606032313.py`

## Data Safety

This repository and release package do not include raw dataset images, YOLO label files, model weights, runtime logs, audit outputs, or training artefacts. The executable is attached as a GitHub Release asset rather than committed into the repository.
