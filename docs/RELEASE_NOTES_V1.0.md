# Release Notes — V1.0

[中文](#中文)

## English

`CIVL7009 Source Group Picker V1.0` is the first lightweight release of a source-group review tool for multi-source YOLO-style visual training dataset consolidation and cleaning.

### Added

- Tkinter desktop GUI for same-prefix image group review.
- YOLO-style dataset-root scanning with sibling `images` and `labels` folders.
- V1.0 group-size working-folder support through the `ManualReview_GroupSize_N` convention for grouped same-origin review batches.
- `.rf.` prefix grouping.
- Click-to-select movement into `done/out`.
- Synchronous image-label movement.
- Strict transaction preflight checks.
- Root/done/out validator and formula checks.
- JSON, CSV, and Markdown audit report export.
- Undo for the last completed transaction.
- Previous/next group navigation.
- Double-click full-size image viewer.
- Command-line `--audit-only` mode.
- Windows executable release asset.

### Verified

- Unit tests: `12/12 OK`.
- Release package excludes raw images, labels, runtime logs, audit outputs, model files, and dataset archives.

### Status

Audit outputs are operational cleaning evidence and do not make model-performance claims.

## 中文

`CIVL7009 Source Group Picker V1.0` 是面向多源 YOLO 风格视觉训练数据集合并与清洗的图源组人工审核工具的第一个轻量发布版本。

### 新增

- Tkinter 桌面 GUI，用于同 prefix 图片组筛选。
- 扫描包含同级 `images` 与 `labels` 的 YOLO 风格数据集根目录。
- 通过 V1.0 组大小工作目录约定 `ManualReview_GroupSize_N` 支持同源图片组的人工筛选。
- 基于 `.rf.` 的 prefix 分组。
- 点击选择后移动到 `done/out`。
- 图片与标签同步移动。
- 文件移动前严格事务预检。
- root/done/out 校核器与公式校核。
- JSON、CSV、Markdown 校核报告导出。
- 撤销上一组事务。
- 上一组/下一组导航。
- 双击 100% 原图查看。
- 命令行 `--audit-only` 模式。
- Windows exe 发布资产。

### 验证

- 单元测试：`12/12 OK`。
- 发布包不包含原始图片、标签、运行日志、审计输出、模型文件或数据集压缩包。

### 状态

校核输出只作为数据清洗过程证据，不代表模型性能结论。
