# CIVL7009 Source Group Picker

[中文说明](README.zh-CN.md)

![Version](https://img.shields.io/badge/version-V1.0-094438)
![Python](https://img.shields.io/badge/python-3.11-D1C18D)
![GUI](https://img.shields.io/badge/GUI-Tkinter-009CD5)
![Status](https://img.shields.io/badge/audit-PENDING__AUDIT-EF4022)

A lightweight desktop utility for YOLO-style visual training datasets: consolidate multi-source image collections, review same-origin augmentations, choose one representative source image, and synchronise image-label cleanup into `done/out` folders.

## Why

Large YOLO datasets often combine several sources, scraped batches, Roboflow-style exports, or augmentation pipelines. A single source image may appear together with rotated, cropped, colour-shifted, or otherwise transformed variants. Cleaning these groups manually in Windows File Explorer is slow and easy to get wrong.

This tool turns that task into a focused source-group review workflow: show one same-origin `.rf.` prefix group, choose the image to keep as the representative source sample, move variants aside, and keep YOLO labels synchronised.

## What V1.0 Does

- Scans a YOLO-style dataset root with sibling `images/` and `labels/` folders.
- Recognises the V1.0 group-size working-folder convention, `ManualReview_GroupSize_N`, under `images/` and matches the corresponding folder under `labels/`.
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

## Working Folder Contract

V1.0 expects a YOLO-style dataset root prepared for source-group review and cleanup:

```text
<dataset-id-root>/
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

This naming convention is the V1.0 working-folder contract. The tool itself is intended for general multi-source YOLO dataset consolidation, review, and cleaning, and is not tied to a single local dataset layout.

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
  --id-root <dataset-id-root>
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
e170f10a15ae095bf9647be4f3ea7ef0160f4aec7022cc1889a68a32d9246420
```

## Data Safety

This repository is program-only. It excludes raw dataset images, labels, model artefacts, runtime logs, and generated audit outputs. Audit outputs are operational cleaning evidence, not model-performance claims.

## Licence

No open-source licence has been selected yet. Until a licence is added, all rights are reserved by the project owner.
