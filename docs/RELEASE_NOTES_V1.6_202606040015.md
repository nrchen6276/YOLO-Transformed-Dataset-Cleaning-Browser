# Release Notes - V1.6_202606040015

[中文](#中文)

## English

`V1.6_202606040015` is the next internal-version release after `V1.5_202606032354`. It remains in the Tkinter source-group review line and intentionally excludes later PySide6, Manual Objects, conflict-review, Tier-prefix, and N20_PLUS features.

### Added / Improved

- GUI issue details now include concrete abnormal prefixes and filenames.
- Prefix-level audit rows are carried into the GUI text panel for more direct triage.
- Reviewers can see which group and files caused duplicate, size-mismatch, or done/out rule issues without manually guessing from aggregate counters.

### Kept

- Cached-state transaction planning for the current group.
- Traditional numeric-keypad layout and number-key image selection.
- Background move queue for image-label `done/out` transactions.
- Process log (Plog) and timing evidence.
- Thumbnail worker queue, preview caching, and upcoming-group preload.
- Failure rollback and queue blocking for failed move tasks.
- Dynamic `.rf.` source-prefix grouping in ad-hoc folders.
- Duplicate-label, missing-label, and target-conflict blocking.
- Undo for the last completed source-group transaction.
- JSON, CSV, and Markdown audit/report export.

### Verified

- V1.6 tests: `19/19 OK`.
- Executable help smoke: `--help` exit code `0`.
- Release package excludes raw images, labels, runtime logs, audit outputs, model files, and dataset archives.

### Status

All audit outputs remain `PENDING_AUDIT`. This release is operational review tooling, not model-performance evidence.

## 中文

`V1.6_202606040015` 是严格接在内部 `V1.5_202606032354` 之后的下一版。它仍属于 Tkinter 图源组筛选线，不包含后续 PySide6、Manual Objects、冲突复核、Tier 前缀治理或 N20_PLUS 功能。

### 新增 / 改进

- GUI 异常明细现在会显示具体异常 prefix 和文件名。
- prefix 级校核行会进入界面文本区，便于直接排查。
- 复核者可以看到是哪一个组、哪些文件导致了重复、组大小不匹配或 `done/out` 规则问题，而不必只根据总数猜测。

### 保留

- 当前组基于缓存状态（cached state）的事务准备。
- 传统数字小键盘布局和数字键图片选择。
- 后台移动队列，用于执行图片与标签同步的 `done/out` 事务。
- 过程日志（Process Log, Plog）与耗时证据。
- 缩略图后台队列、预览缓存和后续组预加载。
- 移动失败时回滚并阻断队列。
- 非常规目录中的动态 `.rf.` source-prefix 分组。
- 标签重复、标签缺失和目标文件冲突阻断。
- 撤销上一组已完成图源事务。
- JSON、CSV、Markdown 校核/报告导出。

### 验证

- V1.6 测试：`19/19 OK`。
- 可执行文件 help smoke：`--help` 退出码 `0`。
- 发布包不包含原始图片、标签、运行日志、审计输出、模型文件或数据集压缩包。

### 状态

所有校核输出保持 `PENDING_AUDIT`。本版本是数据复核工具，不是模型性能证据。
