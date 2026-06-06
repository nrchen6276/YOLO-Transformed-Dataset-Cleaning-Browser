# Release Notes - V1.8_202606040320

[中文](#中文)

## English

`V1.8_202606040320` is the next internal-version release after `V1.7_202606040155`. It remains in the Tkinter line and adds stronger safe-transaction, recovery, and review-lock controls. Later PySide6, Manual Objects, conflict-review, Tier-prefix, and N20_PLUS features are intentionally not included.

### Added / Improved

- Persistent file transaction journal with `PLANNED`, `RUNNING`, `COMMITTED`, `FAILED`, and undo states.
- Recovery snapshot generation when transaction execution fails.
- Startup-style unfinished transaction scanning helpers.
- Single review-directory lock with active PID blocking and stale lock recovery.
- Windows casefold child-directory checks for `done/out` safety.
- Duplicate-label audit errors are surfaced as blocking errors.
- Root group-size mismatches now block selection rather than being a soft warning.
- Non-ManualReview target folders are excluded from ID-root scan candidates.

### Kept

- ID Initialisation page and YOLO image-label audit/export from V1.7.
- Cached-state transaction planning for the current group.
- Traditional numeric-keypad layout and number-key image selection.
- Background move queue for image-label `done/out` transactions.
- Process log (Plog), thumbnail cache, preload, rollback-on-failure, undo, dynamic `.rf.` grouping, and audit export.

### Verified

- V1.8 tests: `28 tests OK, skipped=1`.
- The skipped test is a Windows platform limitation for simultaneously creating `done` and `Done` sibling directories on the default filesystem.
- Executable help smoke: `--help` exit code `0`.
- Release package excludes raw images, labels, runtime logs, audit outputs, model files, and dataset archives.

### Status

All audit outputs remain `PENDING_AUDIT`. This release is operational review, initialisation, and safe-transaction tooling, not model-performance evidence.

## 中文

`V1.8_202606040320` 是严格接在内部 `V1.7_202606040155` 之后的下一版。它仍属于 Tkinter 线，并加强安全事务、恢复和 review 目录锁控制。后续 PySide6、Manual Objects、冲突复核、Tier 前缀治理或 N20_PLUS 功能不属于本版本。

### 新增 / 改进

- 新增持久化文件事务日志，记录 `PLANNED`、`RUNNING`、`COMMITTED`、`FAILED` 与撤销状态。
- 事务执行失败时生成恢复快照。
- 新增未完成事务扫描辅助逻辑。
- 新增单个 review 目录锁，支持活动 PID 阻断和 stale lock 恢复。
- 新增 Windows casefold 子目录检查，提升 `done/out` 安全性。
- 标签重复 audit 错误会作为阻断错误展示。
- root 组大小不匹配从软警告升级为阻断筛选问题。
- 非 ManualReview 目标文件夹不会进入 ID 根目录扫描候选。

### 保留

- V1.7 的 ID 初始化页与 YOLO 图片-标签校核/导出。
- 当前组基于缓存状态（cached state）的事务准备。
- 传统数字小键盘布局和数字键图片选择。
- 后台移动队列，用于执行图片与标签同步的 `done/out` 事务。
- 过程日志（Process Log, Plog）、缩略图缓存、预加载、失败回滚、撤销、动态 `.rf.` 分组和校核报告导出。

### 验证

- V1.8 测试：`28 tests OK, skipped=1`。
- 跳过项是 Windows 默认文件系统无法同时创建 `done` 与 `Done` 兄弟目录的大小写碰撞测试。
- 可执行文件 help smoke：`--help` 退出码 `0`。
- 发布包不包含原始图片、标签、运行日志、审计输出、模型文件或数据集压缩包。

### 状态

所有校核输出保持 `PENDING_AUDIT`。本版本是数据复核、初始化与安全事务工具，不是模型性能证据。
