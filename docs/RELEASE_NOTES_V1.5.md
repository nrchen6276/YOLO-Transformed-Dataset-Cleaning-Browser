# Release Notes - V1.5

[中文](#中文)

## English

`YOLO Transformed Dataset Cleaning Browser V1.5` packages the internally verified `V5.2_202606061825` build. This release focuses on large Manual Objects candidate groups, especially `N20_PLUS` groups.

### Added

- Full-card rendering for `N20_PLUS` Manual Objects groups.
- Scrollable access to every candidate item in a large group.
- Bounded asynchronous thumbnail loading for large groups.
- Preview-status reporting for completed, running, queued, and failed thumbnail loads.
- A regression test that verifies a 35-item `N20_PLUS` group renders all items and loads all thumbnails.

### Fixed

- Large groups no longer stop at the first 30 visible candidates.
- Manual preview refresh now clears the whole current group thumbnail cache.

### Kept

- Manual Objects review from `_indexes/manual_objects_index.csv` and `group_manifest.json`.
- YOLO bbox overlays and class-name mapping.
- `APPROVED`, `ALL_OUT`, `ALL_DONE`, `SKIP`, `AMBIGUOUS`, and `NEEDS_AGENT_CHECK` outputs.
- Review history and undo for Manual Objects selections.
- Conflict-aware hints and object-level conflict review.
- Source-group review with background movement, label synchronisation, undo, and keyboard shortcuts.
- Tier-prefix governance workflow.

### Verified

- V1.5 package tests: `34/34 OK`.
- Executable smoke test: `--smoke-open` exit code `0`.
- Release package excludes raw dataset images, labels, runtime logs, audit outputs, model files, and dataset archives.

### Status

All audit and dashboard outputs remain `PENDING_AUDIT`. They are operational data-cleaning evidence, not model-performance claims.

## 中文

`YOLO Transformed Dataset Cleaning Browser V1.5` 打包了内部已验证的 `V5.2_202606061825` 构建。本次重点修复大型 Manual Objects 候选组，尤其是 `N20_PLUS` 大组的完整显示问题。

### 新增

- `N20_PLUS` 大组现在会为全部候选创建卡片。
- 大型候选组可以在可滚动图片区查看每一张候选图。
- 大组缩略图采用有限批次的异步加载。
- 预览状态面板显示已完成、进行中、排队和失败数量。
- 新增 35 项 `N20_PLUS` 回归测试，验证全部候选和缩略图加载。

### 修复

- 大型候选组不再停留在前 30 张可见候选。
- 手动刷新当前组预览时会清理整组缩略图缓存。

### 保留

- 基于 `_indexes/manual_objects_index.csv` 和 `group_manifest.json` 的 Manual Objects 复核。
- YOLO 标注框叠加和类别名映射。
- `APPROVED`、`ALL_OUT`、`ALL_DONE`、`SKIP`、`AMBIGUOUS`、`NEEDS_AGENT_CHECK` 输出。
- Manual Objects 操作历史和撤销。
- 冲突提示和对象级冲突复核。
- 图源组筛选中的后台移动、标签同步、撤销和快捷键。
- Tier 前缀治理工作流。

### 验证

- V1.5 包内测试：`34/34 OK`。
- 可执行文件 smoke test：`--smoke-open` 退出码 `0`。
- 发布包不包含原始数据集图片、标签、运行日志、审计输出、模型文件或数据集压缩包。

### 状态

所有审计和仪表盘输出仍保持 `PENDING_AUDIT`。它们是数据清洗过程证据，不是模型性能结论。
