# CIVL7009 Source Group Picker

[中文说明](README.zh-CN.md)

![Version](https://img.shields.io/badge/latest-V1.1-094438)
![Python](https://img.shields.io/badge/python-3.11-D1C18D)
![GUI](https://img.shields.io/badge/GUI-Tkinter-009CD5)
![Status](https://img.shields.io/badge/audit-PENDING__AUDIT-EF4022)

A lightweight desktop utility for YOLO-style visual training datasets: consolidate multi-source image collections, review same-origin augmentations, choose one representative source image, and synchronise image-label cleanup into `done/out` folders.

## Why

Large YOLO datasets often combine several sources, scraped batches, annotation-tool exports, or augmentation pipelines. A single source image may appear with rotated, cropped, colour-shifted, re-exported, or otherwise transformed variants. Cleaning these groups manually in Windows File Explorer is slow and easy to get wrong.

This tool turns that task into a focused source-group review workflow: show one same-origin `.rf.` prefix group, choose the image to keep as the representative source sample, move variants aside, and keep YOLO labels synchronised.

## Current Release: V1.1

V1.1 keeps the V1.0 safety model and expands the workflow from fixed review-folder names to flexible target-folder review.

New in V1.1:

- Direct target image-folder selection from the GUI.
- `--image-dir` audit/open mode for a single image working folder.
- Optional `--label-dir` for explicit image-label folder pairing.
- Automatic paired label-folder inference from an `images/...` path to the matching `labels/...` path.
- Dynamic group-size handling for ad-hoc folders, where different `.rf.` prefixes may have different member counts.
- Softer `ManualReview_GroupSize_N` hint handling: mismatches are warnings when a prefix is otherwise valid and selectable.
- Target-folder audit export for one selected working folder.
- Backward compatibility with the V1.0 `ManualReview_GroupSize_N` workflow.

## Core Capabilities

- Groups image files by the last `.rf.` marker in the filename stem.
- Moves the selected source image to `images/.../done`.
- Moves same-prefix variant images to `images/.../out`.
- Moves matching `.txt` labels to `labels/.../done` and `labels/.../out`.
- Looks up labels from root, `done`, `out`, `Done_auto`, and `Out_auto`.
- Blocks unsafe moves when labels are missing, duplicated, or target files already exist.
- Audits root/done/out counts, prefix counts, group-size distributions, and formula checks when a folder supplies a group-size hint.
- Exports JSON, CSV, and Markdown audit reports.
- Supports undo for the last completed group transaction.
- Supports previous/next navigation and double-click full-size image viewing.
- Provides a Windows executable through GitHub Releases.

## What It Does Not Do

- It does not train, evaluate, or modify any model.
- It does not delete, overwrite, edit, upload, or expose raw images or labels.
- It does not include V1.2+, V1.8+, V1.9/V2 PySide6, Safe Gate, FastReviewIndex, manifest queue, or staging features.

## Working Folder Model

V1.1 supports both standard and ad-hoc source-group review folders under a YOLO-style dataset tree:

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

The classic V1.0 folder name `ManualReview_GroupSize_N` is still supported. In V1.1, non-standard review folders are also supported when files can be grouped by `.rf.` prefix and each selectable prefix has more than one image.

## Quick Start

### Use the executable

Download the V1.1 release asset:

```text
CIVL7009_Source_Group_Picker_V1.1_202606050147.zip
```

Extract it and run:

```text
Executable/CIVL7009_Source_Group_Picker_V1.1_202606032239.exe
```

### Run from source

```powershell
uv run --with Pillow python Dataset/Select_Programme/CIVL7009_source_group_picker_gui_V1.1_202606032239.py
```

### Audit a dataset root

```powershell
uv run --with Pillow python Dataset/Select_Programme/CIVL7009_source_group_picker_gui_V1.1_202606032239.py `
  --audit-only `
  --id-root <dataset-id-root>
```

### Audit a direct image working folder

```powershell
uv run --with Pillow python Dataset/Select_Programme/CIVL7009_source_group_picker_gui_V1.1_202606032239.py `
  --audit-only `
  --image-dir <dataset-id-root>/images/<review-folder>
```

## Tests

```powershell
uv run --with Pillow python Dataset/Select_Programme/test_source_group_picker_gui_V1.1_202606032239.py
```

Current V1.1 verification:

```text
13/13 tests OK
```

## Release Asset

The V1.1 binary package is attached to the GitHub Release, not committed into the repository.

Package:

```text
CIVL7009_Source_Group_Picker_V1.1_202606050147.zip
```

SHA256:

```text
6b9d5c23d58c5010c36dc6d692f94e6988736e20719d020cd1490d3aa977e429
```

## Data Safety

This repository is program-only. It excludes raw dataset images, labels, model artefacts, runtime logs, and generated audit outputs. Audit outputs are operational cleaning evidence, not model-performance claims.

## Licence

No open-source licence has been selected yet. Until a licence is added, all rights are reserved by the project owner.
