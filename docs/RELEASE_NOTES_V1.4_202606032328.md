# Release Notes - V1.4_202606032328

[中文](#中文)

## English

`V1.4_202606032328` is an internal-version release in the Tkinter source-group review line. It should be read after `V1.3_202606032313`; later PySide6, Manual Objects, conflict-review, Tier-prefix, and N20_PLUS features are intentionally not included in this release.

### Added / Improved

- Runtime process log (Plog) for review actions and timing evidence.
- Background move queue for image-label `done/out` transactions.
- Failure rollback and queue blocking for failed move tasks.
- Thumbnail worker queue with preview caching and upcoming-group preload.
- ManualReview audit summaries with formula checks and label-sync status.
- Continued support for dynamic `.rf.` source-prefix grouping in ad-hoc folders.

### Kept

- Cached label lookup and current-group transaction preparation from V1.3.
- Duplicate-label, missing-label, and target-conflict blocking.
- Label-synchronised movement into `done/out`.
- Undo for the last completed source-group transaction.
- JSON, CSV, and Markdown audit/report export.

### Verified

- V1.4 tests: `16/16 OK`.
- Executable help smoke: `--help` exit code `0`.
- Release package excludes raw images, labels, runtime logs, audit outputs, model files, and dataset archives.

### Status

All audit outputs remain `PENDING_AUDIT`. This release is operational review tooling, not model-performance evidence.

## 中文

`V1.4_202606032328` 是 Tkinter 图源组筛选线中的内部版本发版。它应接在 `V1.3_202606032313` 之后阅读；后续 PySide6、Manual Objects、冲突复核、Tier 前缀治理和 N20_PLUS 功能不属于本版本。

### 新增 / 改进

- 过程日志（Process Log, Plog），记录复核动作和关键耗时证据。
- 后台移动队列，用于执行图片与标签同步的 `done/out` 事务。
- 移动任务失败时回滚并阻断队列。
- 缩略图后台工作队列、预览缓存和后续组预加载。
- ManualReview 校核摘要，包含公式检查和标签同步状态。
- 继续支持非常规目录中的动态 `.rf.` source-prefix 分组。

### 保留

- V1.3 的标签索引缓存和当前组事务准备。
- 标签重复、标签缺失和目标文件冲突阻断。
- 图片与标签同步移动到 `done/out`。
- 撤销上一组已完成图源事务。
- JSON、CSV、Markdown 校核/报告导出。

### 验证

- V1.4 测试：`16/16 OK`。
- 可执行文件 help smoke：`--help` 退出码 `0`。
- 发布包不包含原始图片、标签、运行日志、审计输出、模型文件或数据集压缩包。

### 状态

所有校核输出保持 `PENDING_AUDIT`。本版本是数据复核工具，不是模型性能证据。
