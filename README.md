# CIVL7009 Source Group Picker

[中文说明](README.zh-CN.md)

![Version](https://img.shields.io/badge/version-V1.0-094438)
![Python](https://img.shields.io/badge/python-3.11-D1C18D)
![GUI](https://img.shields.io/badge/GUI-Tkinter-009CD5)
![Status](https://img.shields.io/badge/audit-PENDING__AUDIT-EF4022)

A lightweight desktop tool for manually choosing the source image from `.rf.`-prefix image groups in CIVL7009 ManualReview folders.

## Why

Manual source-image selection is slow and error-prone in Windows File Explorer when every source image has multiple transformed variants. This tool shows one same-prefix group at a time, lets the reviewer choose the source image, and moves the selected image and labels into a traceable `done/out` layout.

## What V1.0 Does

- Scans `Dataset/Source_Archive/<ID>/images/ManualReview_GroupSize_N`.
- Matches the corresponding `labels/ManualReview_GroupSize_N` folder.
- Groups files by the last `.rf.` marker in the filename stem.
- Moves the selected source image to `images/.../done`.
- Moves same-prefix variant images to `images/.../out`.
- Moves matching `.txt` labels to `labels/.../done` and `labels/.../out`.
- Looks up labels from root, `done`, `out`, `Done_auto`, and `Out_auto`.
- Blocks unsafe moves when labels are missing, duplicated, or target files already exist.
- Audits root/done/out counts, prefix counts, group-size distributions, and the formula `out = done x (N - 1)`.
- Exports JSON, CSV, and Markdown audit reports.
- Supports undo for the last completed group transaction.
- Supports previous/next navigation and double-click full-size image viewing.
- Provides a Windows executable through GitHub Releases.

## What V1.0 Does Not Do

- It does not process global `images/Done`, `images/transformations`, `labels/Done`, or `labels/transformations`.
- It does not train, evaluate, or modify any model.
- It does not delete, overwrite, edit, upload, or expose raw images or labels.
- It does not include V1.1, V1.8, V1.9, V2.x, PySide6, staging, Safe Gate, or FastReviewIndex features.

## Directory Contract

```text
Dataset/Source_Archive/<ID>/
  images/
    ManualReview_GroupSize_N/
      *.jpg
      done/
      out/
  labels/
    ManualReview_GroupSize_N/
      *.txt
      done/
      out/
      Done_auto/
      Out_auto/
```

`ManualReview_GroupSize_1` is treated as an original singleton statistics directory and is not entered into the manual choose-one queue.

## Quick Start

### Use the executable

Download the V1.0 release asset:

```text
CIVL7009_Source_Group_Picker_V1.0_202606050035.zip
```

Extract it and run:

```text
Executable/CIVL7009_Source_Group_Picker_V1.0_202606032227.exe
```

### Run from source

```powershell
uv run --with Pillow python Dataset/Select_Programme/CIVL7009_manualreview_source_picker_gui_V1.0_202606032227.py
```

### Audit only

```powershell
uv run --with Pillow python Dataset/Select_Programme/CIVL7009_manualreview_source_picker_gui_V1.0_202606032227.py `
  --audit-only `
  --id-root Dataset/Source_Archive/01
```

## Tests

```powershell
uv run --with Pillow python Dataset/Select_Programme/test_manualreview_source_picker_gui_V1.0_202606032227.py
```

Current V1.0 verification:

```text
12/12 tests OK
```

## Release Asset

The V1.0 binary package is attached to the GitHub Release, not committed into the repository.

Package:

```text
CIVL7009_Source_Group_Picker_V1.0_202606050035.zip
```

SHA256:

```text
f3aa42488236db6764ee43d985679012a5246497ae6bf858b576b261c5943f8a
```

## Data Safety

This repository is program-only. It excludes raw dataset images, labels, model artefacts, runtime logs, and generated audit outputs. All governance outputs remain `PENDING_AUDIT`.

## Licence

No open-source licence has been selected yet. Until a licence is added, all rights are reserved by the project owner.
