# YOLO Transformed Dataset Cleaning Browser

Desktop tooling for reviewing, comparing, and cleaning merged YOLO visual-training datasets. The project focuses on high-throughput manual decisions for groups of related images: selecting a source image, moving transformed variants into an output bucket, synchronising labels, auditing counts, and preserving a recoverable operation trail.

Latest release: **V2.2.4_202606042313**

## What It Does

- Opens grouped image-review folders produced during YOLO dataset cleaning.
- Shows related images together in a keypad-style comparison grid.
- Lets reviewers select the source image while the remaining images become variants.
- Keeps image and label movement synchronised through a transaction-safe workflow.
- Supports undo, background move queues, audit summaries, operation logs, compact status feedback, and non-standard grouped review folders.
- Packages a Windows executable for users who do not want to launch Python manually.

## V2.2.4 Highlights

- Switches the Qt shell to the V1.8.2 core line.
- Adds support for non-standard review folders such as `images/special` when the paired `labels/special` folder exists.
- Supports mixed group sizes in one review directory instead of assuming one fixed `ManualReview_GroupSize_N`.
- Keeps the V2.2.3 compact status chip, single-line Safe Gate badge, in-place undo, red selection feedback, and resizable bottom panel.

## Download

Use the latest release asset:

`YOLO_Transformed_Dataset_Cleaning_Browser_V2.2.4_202606042313.zip`

The archive contains the executable, source entrypoint, V1.8.2 core, versioned package, tests, build metadata, and abstract UI assets. It does **not** contain raw dataset images, labels, model weights, or dataset YAML files.

## Safety Boundary

This browser is intended for dataset-cleaning operations where file movement must be explicit, auditable, and reversible where practical. The release artifacts keep raw training data outside the program package.

All dataset-governance outputs remain **PENDING_AUDIT** until separately verified by the relevant data-governance workflow.

## Chinese README

中文说明见 [README.zh-CN.md](README.zh-CN.md).
