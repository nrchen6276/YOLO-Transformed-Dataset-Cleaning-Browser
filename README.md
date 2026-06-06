# YOLO Transformed Dataset Cleaning Browser

[中文说明](README.zh-CN.md)

![Version](https://img.shields.io/badge/latest-V1.7__202606040155-094438)
![Python](https://img.shields.io/badge/python-3.11-D1C18D)
![GUI](https://img.shields.io/badge/GUI-Tkinter-009CD5)
![Status](https://img.shields.io/badge/audit-PENDING__AUDIT-EF4022)

A lightweight desktop browser for cleaning transformed, duplicated, or near-duplicated image variants in YOLO-style vision datasets. It helps reviewers compare one source-related image group at a time, choose the representative source image, move the remaining variants to `out`, and keep the corresponding YOLO `.txt` labels synchronised.

This repository is released in the same order as the internal programme builds. The current public release is aligned with internal build `V1.7_202606040155`.

## Why This Exists

YOLO training datasets often contain multiple transformed versions of the same original image: rotations, crops, colour edits, augmentations, re-exports, or near-duplicates. If these variants are treated as independent sources without review, later training, leakage checks, and data-quality audit become harder to explain.

This tool turns that cleaning task into a fast visual review workflow. A reviewer sees one source-prefix group at a time, selects the image to keep as the source representative, and lets the tool move the variants and labels into `done/out` with a process trail. All governance outputs remain `PENDING_AUDIT`.

## Current Release: V1.7_202606040155

`V1.7_202606040155` is a Tkinter source-group review and dataset-initialisation release. It follows `V1.6_202606040015` exactly in the internal version sequence.

New in V1.7:

- Adds an ID Initialisation page for ordinary YOLO datasets.
- Audits common YOLO layouts: `images/labels` at root level, or `train|valid|val|test/images` with matching labels.
- Exports a Markdown image-label pairing audit before initialisation.
- Copies matched `.rf.` image-label pairs into `ManualReview_GroupSize_N` boards without moving or deleting the original YOLO folders.
- Adds background audit refresh so the review board can be refreshed without freezing the main workflow.
- Keeps V1.6 issue detail lines, cached-state transaction planning, keypad shortcuts, background move queue, thumbnail cache, process logging, rollback-on-failure, undo, dynamic `.rf.` grouping, and audit export.
- Test coverage increased to `21/21 OK`.

## Core Capabilities

- Select an image review folder directly.
- Infer the matching `labels/...` folder from the selected `images/...` folder.
- Accept an explicit `--label-dir` when needed.
- Group images by dynamic `.rf.` source-prefix logic in ordinary or ad-hoc review folders.
- Keep compatibility with classic `ManualReview_GroupSize_N` folders.
- Block duplicate labels, missing labels, target conflicts, and incomplete groups.
- Move selected source image/label to `done` and variants to `out`.
- Export JSON, CSV, and Markdown audit reports.
- Audit and initialise ordinary YOLO datasets into source-group review boards.
- Navigate previous/next groups and open a 100% original image viewer.
- Use number-key shortcuts following the traditional keypad layout.
- Provide a Windows executable as the release asset.

## What It Does Not Include

- It does not train, evaluate, or modify any model.
- It does not generate hash or near-hash Manual Objects candidate groups.
- It does not include later PySide6, Manual Objects review, conflict review, Tier-prefix governance, or N20_PLUS workflows.
- It does not delete, overwrite, upload, or expose raw dataset images or labels.
- Audit outputs remain `PENDING_AUDIT`; they are process evidence, not model-performance claims.

## Expected Working Folder Shape

V1.5 supports standard or ad-hoc YOLO-style review trees:

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
YOLO_Transformed_Dataset_Cleaning_Browser_V1.7_202606040155.zip
```

Unzip it and run:

```text
Dataset/Select_Programme/Executable/CIVL7009_Source_Group_Picker_V1.7_202606040155.exe
```

Run from source:

```powershell
uv run --with pillow python Dataset/Select_Programme/CIVL7009_source_group_picker_gui_V1.7_202606040155.py
```

Run tests:

```powershell
uv run python Dataset/Select_Programme/test_source_group_picker_gui_V1.7_202606040155.py
```

Expected verification:

```text
21/21 OK
exe --help OK
```

## Safety Boundary

The release package does not contain raw dataset images, labels, runtime logs, audit outputs, model weights, or dataset archives. File movement happens only inside the review folder selected by the user, and only when the reviewer executes a source-group decision.
