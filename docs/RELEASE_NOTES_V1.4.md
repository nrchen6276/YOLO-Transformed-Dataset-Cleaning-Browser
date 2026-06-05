# Release Notes — V1.4

[中文](#中文)

## English

`YOLO Transformed Dataset Cleaning Browser V1.4` is the next public release after V1.3. It introduces the newer PySide6 review cockpit and expands the tool from same-origin transformed-image cleanup to cross-dataset Manual Objects review.

### Added

- PySide6 workflow shell with separate review modes.
- Manual Objects review for hash / near-hash candidate groups.
- Fast global index loading for large candidate stores.
- On-demand asynchronous preview loading after selecting a concrete candidate group.
- Click-to-save and auto-next within the same `Reason / Nxx` bucket.
- YOLO `.txt` bounding-box overlays on previews.
- Per-dataset class-name folders under `ID_Classes/<dataset_id>/`.
- Flexible class-file names; `classes.txt` is not required.
- Larger adaptive preview cards that use available workspace area.
- Structured `manual_selection.json` writing for later governance agents.

### Kept

- Source-group review for transformed YOLO image variants.
- Label-synchronised movement into `done/out` for source-group review.
- Undo for the last completed source-group transaction.
- Strict missing-label, duplicate-label, and target-conflict blocking.
- JSON, CSV, and Markdown report outputs.

### Verified

- V1.4 package tests: `14/14 OK`.
- V3.0.4 regression: `13/13 OK`.
- V2.2.4 regression: `10/10 OK`.
- Source-run smoke and executable smoke tests passed.
- Release package excludes raw images, labels, runtime logs, audit outputs, model files, and dataset archives.

### Status

Audit and dashboard outputs are operational cleaning evidence and remain `PENDING_AUDIT`; they do not make model-performance claims.

## 中文

`YOLO Transformed Dataset Cleaning Browser V1.4` 是 V1.3 之后的下一个公共发布版本。本版引入新版 PySide6 复核界面，并把工具能力从同源变换图清洗扩展到跨数据集 Manual Objects 候选复核。

### 新增

- PySide6 工作流界面。
- 哈希 / 近哈希候选组的 Manual Objects 复核。
- 面向大规模候选区的全局 index 快速读取。
- 选中具体候选组后才异步加载预览图。
- 单击保存并进入同一 `Reason / Nxx` 内下一组。
- YOLO `.txt` bbox 叠加预览。
- `ID_Classes/<dataset_id>/` 按数据集 ID 存放类别文件。
- 类别文件名可自定义，不必叫 `classes.txt`。
- 更大的自适应图片预览卡片，尽可能利用工作区空间。
- 写出结构化 `manual_selection.json` 供后续治理 agent 回读。

### 保留

- YOLO 变换图的图源组复核。
- 图源组复核中的图片/标签同步移动到 `done/out`。
- 撤销上一组已完成图源事务。
- 严格阻断缺标签、重复标签和目标冲突。
- JSON、CSV、Markdown 报告输出。

### 验证

- V1.4 包内测试：`14/14 OK`。
- V3.0.4 回归：`13/13 OK`。
- V2.2.4 回归：`10/10 OK`。
- source-run smoke 与 exe smoke 均通过。
- 发布包不包含原始图片、标签、运行日志、审计输出、模型文件或数据集压缩包。

### 状态

校核和仪表盘输出只作为数据清洗过程证据，保持 `PENDING_AUDIT`，不代表模型性能结论。
