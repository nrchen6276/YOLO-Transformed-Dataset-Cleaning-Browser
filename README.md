# YOLO Transformed Dataset Cleaning Browser

Desktop tooling for reviewing, comparing, and cleaning merged YOLO visual-training datasets. It is designed for data-governance workflows where multiple sources, augmentations, transformed variants, duplicate candidates, or near-duplicate candidates must be reviewed by a human before downstream dataset changes are made.

Latest release: **V3.0.1_202606051430**

## What It Does

- Reviews grouped images and labels produced during YOLO dataset cleaning.
- Shows related images together in a keypad-style comparison grid.
- Supports source-image selection, label-synchronised moves, undo, audit reports, and transaction-safe review in the source-group workflow.
- Adds a Manual Objects workflow for duplicate and near-duplicate cross-dataset candidates.
- Reads the landed `Manual_Objects/_indexes/manual_objects_index.csv` first, then lazy-loads each group's `group_manifest.json` only when the reviewer opens that group.
- Writes structured `manual_selection.json` review results for downstream governance agents.
- Packages a Windows executable for users who do not want to launch Python manually.

## V3.0.1 Highlights

- Performance hotfix for the Manual Objects Review workflow.
- Fast global review board from `_indexes/manual_objects_index.csv`.
- Current-group lazy loading instead of parsing every `group_manifest.json` at startup.
- Pagination and filtering for large candidate sets.
- Background prefetch of nearby groups and thumbnails.
- Save-and-next workflow for high-throughput human review.
- Keeps V3.0 Manual Objects safety boundaries: no hash scanning, no candidate creation, no source-library file movement, and no staged image or label modification.

## Download

Use the latest release asset:

`YOLO_Transformed_Dataset_Cleaning_Browser_V3.0.1_202606051430.zip`

The archive contains the executable, source entrypoint, V1.8.2 core, versioned package, tests, build metadata, and abstract UI assets. It does **not** contain raw dataset images, labels, model weights, or dataset YAML files.

## Safety Boundary

Manual Objects Review is a review-result writer, not a hash scanner and not a source-library governance mover. It does not create candidate groups, does not delete staged copies, and does not move source-library images or labels. It only writes `manual_selection.json` and `_selection_history/` inside candidate group folders.

All dataset-governance outputs remain **PENDING_AUDIT** until separately verified by the relevant data-governance workflow.

## Chinese README

中文说明见 [README.zh-CN.md](README.zh-CN.md).
