# YOLO Transformed Dataset Cleaning Browser

[中文 README](README.zh-CN.md)

![Version](https://img.shields.io/badge/latest-V1.5-094438)
![Python](https://img.shields.io/badge/python-3.11-D1C18D)
![GUI](https://img.shields.io/badge/GUI-PySide6-009CD5)
![Status](https://img.shields.io/badge/audit-PENDING__AUDIT-EF4022)

A PySide6 desktop browser for cleaning YOLO visual-training datasets that contain transformed images, duplicate samples, near-duplicate samples, or cross-dataset candidate groups. It is designed for fast human review: compare candidate images, inspect YOLO `.txt` bounding boxes, keep or remove candidates, and write structured review decisions for later data-governance scripts.

The tool is intentionally conservative. It is a review and cleaning browser, not a model-training tool and not a destructive dataset mover.

## Why

YOLO datasets often contain rotated, cropped, colour-shifted, re-exported, duplicated, or perceptual-hash-similar versions of the same source material. If these candidates are treated as independent training samples without review, leakage checks, provenance tracking, and downstream experiment interpretation become harder to trust.

This tool turns that work into a visual workflow:

- browse same-source transformed image groups;
- review cross-dataset exact-hash and near-hash candidate groups;
- draw YOLO label boxes and class names on previews;
- mark one, many, all, or no candidates as retained;
- record review history and structured `manual_selection.json` decisions;
- keep operational evidence as `PENDING_AUDIT` rather than overclaiming model quality.

## Current Release: V1.5

Public release `V1.5` packages the internally verified `V5.2_202606061825` build.

New in V1.5:

- Large `N20_PLUS` Manual Objects groups now render all candidate cards in the scrollable review stage.
- Thumbnail previews for large groups load asynchronously in bounded batches instead of truncating to the first 30 candidates.
- The preview status panel reports completed, running, queued, and failed thumbnail loads.
- Manual preview refresh now clears cache for the whole current group.
- Existing Manual Objects review features are retained: YOLO bbox overlay, class-name mapping, review history, `ALL_OUT`, `ALL_DONE`, undo, conflict-aware hints, and object-level conflict review.
- Source-group review features are retained: dynamic `.rf.` grouping, background movement into `done/out`, label synchronisation, undo, and keyboard-driven review.

## Core Capabilities

- Direct review-folder selection for transformed YOLO source groups.
- Automatic image-label pairing between `images/...` and `labels/...`.
- Dynamic same-source grouping for transformed image variants.
- Background movement into `done/out` for source-group review, with transaction safety.
- Manual Objects review from `group_manifest.json` and `_indexes/manual_objects_index.csv`.
- Review statuses: `APPROVED`, `ALL_OUT`, `ALL_DONE`, `SKIP`, `AMBIGUOUS`, `NEEDS_AGENT_CHECK`.
- YOLO bbox overlay and per-dataset class-file detection.
- Object-level conflict-awareness for cross-reason Manual Objects decisions.
- Tier-prefix governance page for prefix-audit workflows.
- JSON, CSV, Markdown, and history outputs for later governance agents.
- Windows executable release asset.

## What It Does Not Do

- It does not train, evaluate, or modify any model.
- It does not generate hash / near-hash candidate groups.
- It does not delete raw dataset images or labels.
- It does not upload or expose raw dataset material.
- It does not execute physical staging by default.
- It does not turn an audit result into a model-performance claim.

## Quick Start

Download the latest release asset:

```text
YOLO_Transformed_Dataset_Cleaning_Browser_V1.5_202606062103.zip
```

After extraction, run:

```text
Dataset/Select_Programme/Executable/CIVL7009_Source_Group_Picker_V5.2_202606061825.exe
```

From source:

```powershell
uv run --with PySide6 --with pillow python Dataset/Select_Programme/CIVL7009_source_group_picker_qt_V5.2_202606061825.py
```

Run tests:

```powershell
uv run --with PySide6 --with pillow python Dataset/Select_Programme/test_source_group_picker_qt_V5.2_202606061825.py
```

Expected verification:

```text
34/34 OK
exe --smoke-open OK
```

## Manual Objects Class Names

For YOLO bbox labels to display class names, place any `.txt` class file under each dataset ID folder:

```text
Manual_Objects/
  ID_Classes/
    ID01/
      any_name.txt
    ID09/
      classes_for_id09.txt
```

The file name does not have to be `classes.txt`; the first valid non-empty `.txt` file in each ID folder is used as that dataset's class list.

## Safety Boundary

Release packages exclude raw dataset images, labels, runtime logs, audit outputs, model weights, and dataset archives. Manual Objects mode writes only review decisions such as `manual_selection.json` and `_selection_history` when the reviewer saves a result. All audit outputs remain `PENDING_AUDIT`.

## Releases

- [Latest release](https://github.com/nrchen6276/YOLO-Transformed-Dataset-Cleaning-Browser/releases/latest)
- [All releases](https://github.com/nrchen6276/YOLO-Transformed-Dataset-Cleaning-Browser/releases)
