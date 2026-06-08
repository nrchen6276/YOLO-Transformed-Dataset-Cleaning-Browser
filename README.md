# YOLO Transformed Dataset Cleaning Browser

Desktop tooling for reviewing, comparing, and cleaning merged YOLO visual-training datasets. The project focuses on high-throughput manual decisions for groups of related images and cross-dataset candidate objects: selecting a source image, reviewing duplicate or near-duplicate candidates, synchronising labels, auditing counts, and preserving machine-readable review outputs for downstream governance.

Latest release: **V3.0_202606050530**

## What It Does

- Opens grouped image-review folders produced during YOLO dataset cleaning.
- Shows related images together in a keypad-style comparison grid.
- Lets reviewers select the source image while the remaining images become variants.
- Keeps image and label movement synchronised through a transaction-safe workflow.
- Adds a Manual Objects Review workflow for cross-dataset duplicate or near-duplicate candidates.
- Reads group manifests as the authority for candidate metadata and writes `manual_selection.json` for downstream processing.
- Packages a Windows executable for users who do not want to launch Python manually.

## V3.0 Highlights

- Adds top-level workflow tabs: Source Group Review, Manual Objects Review, and Diagnostics / Settings.
- Introduces Manual Objects Review for candidate folders organised by reason, group size, and group ID.
- Supports single-keep and multi-keep review modes.
- Writes `APPROVED`, `SKIP`, `AMBIGUOUS`, and `NEEDS_AGENT_CHECK` selections without touching source-library files.
- Preserves V2.2.4 dynamic folder support for non-standard source-group review directories.

## Download

Use the latest release asset:

`YOLO_Transformed_Dataset_Cleaning_Browser_V3.0_202606050530.zip`

The archive contains the executable, source entrypoint, V1.8.2 core, versioned package, tests, build metadata, and abstract UI assets. It does **not** contain raw dataset images, labels, model weights, or dataset YAML files.

## Safety Boundary

Manual Objects Review is a review-result writer, not a hash scanner and not a source-library governance mover. It does not create candidate groups, does not delete staged copies, and does not move source-library images or labels.

All dataset-governance outputs remain **PENDING_AUDIT** until separately verified by the relevant data-governance workflow.

## Chinese README

中文说明见 [README.zh-CN.md](README.zh-CN.md).
