# YOLO Transformed Dataset Cleaning Browser

Desktop tooling for reviewing, comparing, and cleaning merged YOLO visual-training datasets. It is designed for data-governance workflows where multiple sources, augmentations, transformed variants, duplicate candidates, or near-duplicate candidates must be reviewed by a human before downstream dataset changes are made.

Latest release: **V3.0.4_202606051830**

## What It Does

- Reviews grouped images and labels produced during YOLO dataset cleaning.
- Shows related images together in a keypad-style comparison grid.
- Supports source-image selection, label-synchronised moves, undo, audit reports, and transaction-safe review in the source-group workflow.
- Provides a Manual Objects workflow for duplicate and near-duplicate cross-dataset candidates.
- Reads the global Manual Objects index first, then lazy-loads each group only when the reviewer opens it.
- Shows YOLO `.txt` bounding boxes over Manual Objects previews when requested.
- Supports per-dataset class-name files for bounding-box labels.
- Writes structured `manual_selection.json` review results for downstream governance agents.
- Packages a Windows executable for users who do not want to launch Python manually.

## V3.0.4 Highlights

- Adds per-dataset class-name support for YOLO `.txt` bounding-box overlays.
- Automatically creates `Manual_Objects/ID_Classes/<dataset_id>/` folders for IDs found in the Manual Objects index.
- Accepts any non-empty `.txt` class file name; it does not have to be `classes.txt`.
- Adds a class-file status dialog with folder-open and refresh actions.
- Detects missing, empty, multiple, and valid class-file states.
- Invalidates preview cache when class maps change so BBox labels refresh correctly.
- Keeps V3 safety boundaries: no hash scanning, no candidate creation, no source-library file movement, and no staged image or label modification.

## Download

Use the latest release asset:

`YOLO_Transformed_Dataset_Cleaning_Browser_V3.0.4_202606051830.zip`

The archive contains the executable, source entrypoint, V1.8.2 core, versioned package, tests, build metadata, and abstract UI assets. It does **not** contain raw dataset images, labels, model weights, or dataset YAML files.

## Safety Boundary

Manual Objects Review is a review-result writer, not a hash scanner and not a source-library governance mover. It does not create candidate groups, does not delete staged copies, and does not move source-library images or labels. It only writes `manual_selection.json`, `_selection_history/`, and user-supplied class files under `Manual_Objects/ID_Classes/`.

All dataset-governance outputs remain **PENDING_AUDIT** until separately verified by the relevant data-governance workflow.

## Chinese README

中文说明见 [README.zh-CN.md](README.zh-CN.md).
