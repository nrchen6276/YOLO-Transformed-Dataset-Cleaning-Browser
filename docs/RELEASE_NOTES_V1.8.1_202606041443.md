# Release Notes - V1.8.1_202606041443

[中文](#中文)

## English

`V1.8.1_202606041443` is the next internal-version release after `V1.8_202606040320`. It remains in the Tkinter line and focuses on performance hotfixes for large review folders while retaining the V1.8 safe-transaction and recovery layer. Later PySide6, Manual Objects, conflict-review, Tier-prefix, and N20_PLUS features are intentionally not included.

### Added / Improved

- `FastReviewIndex` for in-memory current-review indexing.
- Quick preview loading so the first visible groups can render before the full index is ready.
- Current-group transaction preparation through the fast index rather than repeated large-directory scans.
- Incremental audit count updates after a committed group.
- Performance probes for root scan, label scan, fast index build, transaction preparation, and target conflict checks.
- Runtime log splitting for production/test/debug-style runs.
- `IN_PROGRESS_SYNCED` label-sync state for in-progress folders with complete labels.
- Bounded thumbnail preloading: default next groups are limited to reduce disk contention.
- Large-directory performance test coverage.

### Kept

- Persistent transaction journal, recovery snapshots, unfinished transaction scan, and review-directory lock controls from V1.8.
- ID Initialisation page and YOLO image-label audit/export.
- Traditional numeric-keypad layout and number-key image selection.
- Background move queue for image-label `done/out` transactions.
- Process log (Plog), thumbnail cache, rollback-on-failure, undo, dynamic `.rf.` grouping, and audit export.

### Verified

- V1.8.1 tests: `32 tests OK, skipped=1`.
- The skipped test is a Windows platform limitation for simultaneously creating `done` and `Done` sibling directories on the default filesystem.
- Executable help smoke: `--help` exit code `0`.
- Release package excludes raw images, labels, runtime logs, audit outputs, model files, and dataset archives.

### Status

All audit outputs remain `PENDING_AUDIT`. This release is operational review, initialisation, safe-transaction, and performance tooling, not model-performance evidence.

## 中文

`V1.8.1_202606041443` 是严格接在内部 `V1.8_202606040320` 之后的下一版。它仍属于 Tkinter 线，重点修复大目录复核性能，同时保留 V1.8 的安全事务与恢复层。后续 PySide6、Manual Objects、冲突复核、Tier 前缀治理或 N20_PLUS 功能不属于本版本。

### 新增 / 改进

- 新增快速复核索引（FastReviewIndex），用于当前 review 目录的内存索引。
- 新增 quick preview 加载，让首批可见组在完整索引完成前渲染。
- 当前组事务准备通过快速索引执行，避免反复扫描大目录。
- 已提交组后增量更新 audit 计数。
- 新增 root scan、label scan、fast index build、transaction preparation 和 target conflict check 的性能探针。
- 运行日志分流到生产/测试/调试类目录。
- 新增 `IN_PROGRESS_SYNCED` 标签同步状态，用于进行中但标签完整的文件夹。
- 限制缩略图预加载数量，降低大目录磁盘抢占。
- 新增大目录性能测试覆盖。

### 保留

- V1.8 的持久化事务日志、恢复快照、未完成事务扫描和 review 目录锁控制。
- ID 初始化页与 YOLO 图片-标签校核/导出。
- 传统数字小键盘布局和数字键图片选择。
- 后台移动队列，用于执行图片与标签同步的 `done/out` 事务。
- 过程日志（Process Log, Plog）、缩略图缓存、失败回滚、撤销、动态 `.rf.` 分组和校核报告导出。

### 验证

- V1.8.1 测试：`32 tests OK, skipped=1`。
- 跳过项是 Windows 默认文件系统无法同时创建 `done` 与 `Done` 兄弟目录的大小写碰撞测试。
- 可执行文件 help smoke：`--help` 退出码 `0`。
- 发布包不包含原始图片、标签、运行日志、审计输出、模型文件或数据集压缩包。

### 状态

所有校核输出保持 `PENDING_AUDIT`。本版本是数据复核、初始化、安全事务与性能工具，不是模型性能证据。
