# Release Notes — V1.0

[中文](#中文)

## English

`CIVL7009 Source Group Picker V1.0` is the first lightweight release of the ManualReview source-image selection tool.

### Added

- Tkinter desktop GUI for same-prefix image group review.
- `ManualReview_GroupSize_N` scanning under `images` and `labels`.
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

All governance and audit outputs remain `PENDING_AUDIT`.

## 中文

`CIVL7009 Source Group Picker V1.0` 是 ManualReview 图源人工筛选工具的第一个轻量发布版本。

### 新增

- Tkinter 桌面 GUI，用于同 prefix 图片组筛选。
- 扫描 `images` 与 `labels` 下的 `ManualReview_GroupSize_N`。
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

所有治理与校核输出均保持 `PENDING_AUDIT`。
