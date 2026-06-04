# YOLO Transformed Dataset Cleaning Browser

[中文说明](README.zh-CN.md)

![Version](https://img.shields.io/badge/latest-V1.2-094438)
![Python](https://img.shields.io/badge/python-3.11-D1C18D)
![GUI](https://img.shields.io/badge/GUI-Tkinter-009CD5)
![Status](https://img.shields.io/badge/audit-PENDING__AUDIT-EF4022)

A lightweight desktop browser for YOLO-style transformed training datasets: review same-origin image variants, choose one representative source image, and synchronise image-label cleanup into `done/out` folders.

## Why

YOLO datasets often contain source images plus transformed versions: rotated, cropped, colour-shifted, re-exported, or otherwise augmented samples. Before training, these same-origin groups often need human review so that near-duplicates are not silently treated as independent source material.

This tool presents one `.rf.` prefix group at a time, lets the reviewer choose the representative source image, moves variants to `out`, and keeps YOLO `.txt` labels synchronised.

## Current Release: V1.2

V1.2 keeps V1.1's flexible target-folder workflow and adds smoother interaction through background file movement and preview caching.

New in V1.2:

- Background move queue for non-blocking `done/out` file operations.
- Queue status panel for queued, running, moved, and failed tasks.
- Background failure rollback where partial move operations can be safely reversed.
- Failure blocking: follow-up queued moves stop after a failed background task.
- Preview cache to reduce repeated thumbnail decoding.
- Unit tests for successful background moves and failed background rollback.

## Core Capabilities

- Direct image working-folder selection.
- Automatic `images/...` to `labels/...` pairing.
- Optional explicit `--label-dir`.
- Dynamic `.rf.` prefix group sizes for ad-hoc review folders.
- Backward-compatible `ManualReview_GroupSize_N` workflow.
- Strict duplicate/missing-label and target-conflict blocking.
- Synchronous image-label cleanup into `done/out`.
- Undo for the last completed transaction.
- JSON, CSV, and Markdown audit reports.
- Previous/next navigation and double-click full-size image viewing.
- Windows executable release asset.

## What It Does Not Do

- It does not train, evaluate, or modify any model.
- It does not delete, overwrite, edit, upload, or expose raw images or labels.
- It does not include V1.8+ FastReviewIndex, V1.9/V2 PySide6, Safe Gate, manifest queue, or staging features.

## Working Folder Model

V1.2 supports both standard and ad-hoc transformed-image review folders under a YOLO-style dataset tree:

```text
<dataset-id-root>/
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

Download the V1.2 release asset:

```text
YOLO_Transformed_Dataset_Cleaning_Browser_V1.2_202606050237.zip
```

Extract it and run:

```text
Executable/YOLO_Transformed_Dataset_Cleaning_Browser_V1.2_202606032251.exe
```

### Run from source

```powershell
uv run --with Pillow python Dataset/Select_Programme/CIVL7009_source_group_picker_gui_V1.2_202606032251.py
```

### Audit a dataset root

```powershell
uv run --with Pillow python Dataset/Select_Programme/CIVL7009_source_group_picker_gui_V1.2_202606032251.py `
  --audit-only `
  --id-root <dataset-id-root>
```

### Audit a direct image working folder

```powershell
uv run --with Pillow python Dataset/Select_Programme/CIVL7009_source_group_picker_gui_V1.2_202606032251.py `
  --audit-only `
  --image-dir <dataset-id-root>/images/<review-folder>
```

## Tests

```powershell
uv run --with Pillow python Dataset/Select_Programme/test_source_group_picker_gui_V1.2_202606032251.py
```

Current V1.2 verification:

```text
15/15 tests OK
```

## Release Asset

The V1.2 binary package is attached to the GitHub Release, not committed into the repository.

Package:

```text
YOLO_Transformed_Dataset_Cleaning_Browser_V1.2_202606050237.zip
```

SHA256:

```text
0df7a5c9a562a176b7e5640abcead808322887c247166ab23e87d337a78222ed
```

## Data Safety

This repository is program-only. It excludes raw dataset images, labels, model artefacts, runtime logs, and generated audit outputs. Audit outputs are operational cleaning evidence, not model-performance claims.

## Licence

No open-source licence has been selected yet. Until a licence is added, all rights are reserved by the project owner.
