# YOLO Transformed Dataset Cleaning Browser

[中文 README](README.zh-CN.md)

![Version](https://img.shields.io/badge/latest-V1.4__202606032328-094438)
![Python](https://img.shields.io/badge/python-3.11-D1C18D)
![GUI](https://img.shields.io/badge/GUI-Tkinter-009CD5)
![Status](https://img.shields.io/badge/audit-PENDING__AUDIT-EF4022)

A lightweight desktop browser for cleaning YOLO visual-training datasets that contain transformed or duplicated source-image variants. It helps reviewers compare same-origin images, choose the representative source image, move variants into `out`, and keep YOLO `.txt` labels synchronised.

This repository now follows the internal programme version sequence. The current public release is the internal `V1.4_202606032328` build.

## Why

YOLO training datasets often contain transformed versions of the same original image: rotations, crops, colour shifts, re-exports, augmentations, or near-duplicate variants. If these variants are treated as independent source material without review, downstream training, leakage checks, and data-quality audits become harder to trust.

This tool turns that cleanup task into a visual review workflow: one source-prefix group at a time, one chosen representative, label-synchronised movement for variants, and process evidence that remains `PENDING_AUDIT`.

## Current Release: V1.4_202606032328

Internal `V1.4_202606032328` is a Tkinter release in the source-group review line.

Included in V1.4:

- Runtime process logging (Plog) for review actions and timing evidence.
- Background move queue for label-synchronised `done/out` transactions.
- Failure rollback and queue blocking when a transaction fails.
- Thumbnail worker queue with preview caching and upcoming-group preloading.
- Cached label lookup and current-group transaction preparation inherited from V1.3.
- Dynamic `.rf.` source-prefix group sizes for ad-hoc transformed review folders.
- ManualReview audit summaries, formula checks, label-sync checks, and report export.
- Undo for the last completed source-group transaction.

## Core Capabilities

- Direct image working-folder selection.
- Automatic `images/...` to `labels/...` pairing.
- Optional explicit `--label-dir`.
- Dynamic `.rf.` source-prefix group sizes for ad-hoc transformed review folders.
- Backward-compatible `ManualReview_GroupSize_N` folders.
- Strict duplicate-label, missing-label, and target-conflict blocking.
- Label-synchronised movement into `done/out`.
- JSON, CSV, and Markdown audit reports.
- Previous/next navigation and double-click full-size image viewing.
- Windows executable release asset.

## What It Does Not Do

- It does not train, evaluate, or modify any model.
- It does not generate hash / near-hash Manual Objects candidate groups.
- It does not include later PySide6 Manual Objects, conflict-resolution, Tier-prefix, or N20_PLUS workflows.
- It does not delete, overwrite, upload, or expose raw images or labels.
- Audit output remains `PENDING_AUDIT`; it is operational data-cleaning evidence, not a model-performance claim.

## Working Folder Model

V1.4 supports standard and ad-hoc review folders under a YOLO-style dataset tree:

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

Download the release asset:

```text
YOLO_Transformed_Dataset_Cleaning_Browser_V1.4_202606032328.zip
```

After extraction, run:

```text
Dataset/Select_Programme/Executable/CIVL7009_Source_Group_Picker_V1.4_202606032328.exe
```

From source:

```powershell
uv run --with pillow python Dataset/Select_Programme/CIVL7009_source_group_picker_gui_V1.4_202606032328.py
```

Run tests:

```powershell
uv run python Dataset/Select_Programme/test_source_group_picker_gui_V1.4_202606032328.py
```

Expected verification:

```text
16/16 OK
exe --help OK
```

## Safety Boundary

Release packages exclude raw dataset images, labels, runtime logs, audit outputs, model weights, and dataset archives. The tool only moves files inside the selected review working folder when the reviewer performs a source-group transaction.
