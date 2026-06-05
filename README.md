# YOLO Transformed Dataset Cleaning Browser

[中文 README](README.zh-CN.md)

![Version](https://img.shields.io/badge/latest-V1.4-094438)
![Python](https://img.shields.io/badge/python-3.11-D1C18D)
![GUI](https://img.shields.io/badge/GUI-PySide6-009CD5)
![Status](https://img.shields.io/badge/audit-PENDING__AUDIT-EF4022)

A desktop browser for cleaning YOLO visual-training datasets that contain transformed, duplicated, or cross-dataset similar image candidates. It helps reviewers compare image groups, keep one or more intended representatives, inspect YOLO `.txt` bounding boxes, and write review decisions without exposing raw dataset material to the repository.

## Why

YOLO datasets often contain transformed versions of the same source image, near-duplicate images across datasets, or candidate groups produced by hash and perceptual-hash audits. Treating these candidates as independent training material can make dataset governance, leakage review, and downstream experiment interpretation harder to trust.

This tool turns those cleanup tasks into a visual review workflow:

- compare same-origin transformed image variants;
- review cross-dataset duplicate or near-duplicate candidate groups;
- display YOLO label boxes on the preview image;
- map numeric label IDs to per-dataset class names;
- write structured manual-selection outputs for later governance agents.

## Current Release: V1.4

V1.4 is the first public release line to include the newer PySide6 review cockpit and Manual Objects workflow.

New in V1.4:

- PySide6 desktop shell with workflow tabs.
- Manual Objects review for cross-dataset hash / near-hash candidate groups.
- Fast global index loading for large candidate stores.
- On-demand asynchronous image preview loading after a concrete group is selected.
- Click-to-save and auto-next within the same `Reason / Nxx` bucket.
- YOLO `.txt` bounding-box overlays on image previews.
- Per-dataset class-file detection under `ID_Classes/<dataset_id>/`; class file names do not have to be `classes.txt`.
- Larger adaptive preview cards that use available workspace area.
- Structured `manual_selection.json` output for later governance workflows.

## Core Capabilities

- Direct image working-folder selection for transformed source-group review.
- Automatic `images/...` to `labels/...` pairing.
- Dynamic `.rf.` source-prefix group sizes for ad-hoc transformed review folders.
- Label-synchronised movement into `done/out` for source-group review.
- Undo for the last completed source-group transaction.
- Cross-dataset Manual Objects review based on `group_manifest.json`.
- Selection statuses: `APPROVED`, `SKIP`, `AMBIGUOUS`, `NEEDS_AGENT_CHECK`.
- YOLO bbox overlay with class-name mapping.
- JSON, CSV, and Markdown audit/report outputs.
- Windows executable release asset.

## What It Does Not Do

- It does not train, evaluate, or modify any model.
- It does not delete, overwrite, edit, upload, or expose raw images or labels.
- It does not generate hash / near-hash candidate groups.
- It does not execute physical staging or dataset-wide destructive operations.
- Audit output remains `PENDING_AUDIT`; it is operational cleaning evidence, not a model-performance claim.

## Quick Start

### Use the executable

Download the V1.4 release asset:

```text
YOLO_Transformed_Dataset_Cleaning_Browser_V1.4_202606052324.zip
```

After extraction, run:

```text
Executable/CIVL7009_Source_Group_Picker_V3.0.5_202606052235.exe
```

SHA256:

```text
4C3C68454A52E0F4A619EF946CE11A6CAD2060AB1FE7CE3DB088E5F0955CCC37
```

### Run from source

```powershell
uv run --with PySide6 --with Pillow python Dataset/Select_Programme/CIVL7009_source_group_picker_qt_V3.0.5_202606052235.py
```

## Manual Objects Class Files

For bbox labels, place class-name text files under:

```text
Manual_Objects/
  ID_Classes/
    ID01/
      any_name.txt
    ID09/
      classes_for_id09.txt
```

The filename is flexible. The first valid non-empty `.txt` file in each ID folder is used as that ID's class list.

## Tests

```powershell
uv run --with PySide6 --with Pillow python Dataset/Select_Programme/test_source_group_picker_qt_V3.0.5_202606052235.py
```

V1.4 package test result: `14/14 OK`.

Regression checks:

- V3.0.4 regression: `13/13 OK`
- V2.2.4 regression: `10/10 OK`
- executable smoke test: OK

## Release Assets

- [V1.4 release](https://github.com/nrchen6276/YOLO-Transformed-Dataset-Cleaning-Browser/releases/tag/v1.4)
- `YOLO_Transformed_Dataset_Cleaning_Browser_V1.4_202606052324.zip`
- Source entry: `Dataset/Select_Programme/CIVL7009_source_group_picker_qt_V3.0.5_202606052235.py`
- Test file: `Dataset/Select_Programme/test_source_group_picker_qt_V3.0.5_202606052235.py`

## Data Safety

This repository and release package do not include raw dataset images, YOLO label files, model weights, runtime logs, audit outputs, or training artefacts. The executable and zip archive are attached as GitHub Release assets rather than committed into the repository.
