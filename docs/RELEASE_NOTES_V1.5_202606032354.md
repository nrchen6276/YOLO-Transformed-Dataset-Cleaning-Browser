# Release Notes - V1.5_202606032354

[中文](#中文)

## English

`V1.5_202606032354` is the next internal-version release after `V1.4_202606032328`. It remains in the Tkinter source-group review line and intentionally excludes later PySide6, Manual Objects, conflict-review, Tier-prefix, and N20_PLUS features.

### Added / Improved

- Cached-state transaction planning for the current group.
- Faster click preparation by using cached label paths and target stem sets instead of repeating full target/label discovery.
- Traditional numeric-keypad layout helpers:
  - `1-3` groups display continuously.
  - `4-9` groups follow the classic keypad semantics.
- Number-key selection support aligned with the displayed image order.

### Kept

- Background move queue for image-label `done/out` transactions.
- Process log (Plog) and timing evidence.
- Thumbnail worker queue, preview caching, and upcoming-group preload.
- Failure rollback and queue blocking for failed move tasks.
- Dynamic `.rf.` source-prefix grouping in ad-hoc folders.
- Duplicate-label, missing-label, and target-conflict blocking.
- Undo for the last completed source-group transaction.
- JSON, CSV, and Markdown audit/report export.

### Verified

- V1.5 tests: `18/18 OK`.
- Executable help smoke: `--help` exit code `0`.
- Release package excludes raw images, labels, runtime logs, audit outputs, model files, and dataset archives.

### Status

All audit outputs remain `PENDING_AUDIT`. This release is operational review tooling, not model-performance evidence.

## 中文

`V1.5_202606032354` 是严格接在内部 `V1.4_202606032328` 之后的下一版。它仍属于 Tkinter 图源组筛选线，不包含后续 PySide6、Manual Objects、冲突复核、Tier 前缀治理或 N20_PLUS 功能。

### 新增 / 改进

- 当前组基于缓存状态（cached state）的事务准备。
- 点击准备阶段使用缓存标签路径和目标 stem 集合，减少重复目标/标签发现工作。
- 传统数字小键盘布局辅助：
  - `1-3` 图组连续横向显示。
  - `4-9` 图组按经典小键盘语义排布。
- 数字键选择支持，并与界面中的图片顺序对齐。

### 保留

- 后台移动队列，用于执行图片与标签同步的 `done/out` 事务。
- 过程日志（Process Log, Plog）与耗时证据。
- 缩略图后台队列、预览缓存和后续组预加载。
- 移动失败时回滚并阻断队列。
- 非常规目录中的动态 `.rf.` source-prefix 分组。
- 标签重复、标签缺失和目标文件冲突阻断。
- 撤销上一组已完成图源事务。
- JSON、CSV、Markdown 校核/报告导出。

### 验证

- V1.5 测试：`18/18 OK`。
- 可执行文件 help smoke：`--help` 退出码 `0`。
- 发布包不包含原始图片、标签、运行日志、审计输出、模型文件或数据集压缩包。

### 状态

所有校核输出保持 `PENDING_AUDIT`。本版本是数据复核工具，不是模型性能证据。
