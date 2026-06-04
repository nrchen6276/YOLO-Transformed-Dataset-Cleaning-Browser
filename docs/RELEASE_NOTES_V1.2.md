# Release Notes — V1.2

[中文](#中文)

## English

`YOLO Transformed Dataset Cleaning Browser V1.2` is an incremental release focused on interaction smoothness and safer asynchronous file movement for YOLO-style transformed-dataset cleanup.

### Added

- Background move queue for non-blocking `done/out` file operations.
- Queue status panel for queued, running, moved, and failed tasks.
- Background failure rollback where partial move operations can be safely reversed.
- Failure blocking: once a background task fails, follow-up queued moves are blocked instead of silently continuing.
- Preview cache to reduce repeated thumbnail decoding during manual review.
- Unit tests for successful background moves and failed background rollback.

### Kept

- Direct target image-folder selection.
- Automatic `images/...` to `labels/...` pairing.
- Optional explicit `--label-dir`.
- Dynamic `.rf.` prefix group-size handling for ad-hoc review folders.
- Backward-compatible `ManualReview_GroupSize_N` workflow.
- Synchronous image-label cleanup into `done/out`.
- Undo for the last completed transaction.
- JSON, CSV, and Markdown audit reports.

### Verified

- Unit tests: `15/15 OK`.
- Release package excludes raw images, labels, runtime logs, audit outputs, model files, and dataset archives.

### Status

Audit outputs are operational cleaning evidence and do not make model-performance claims.

## 中文

`YOLO Transformed Dataset Cleaning Browser V1.2` 是一次增量发布，重点提升 YOLO 风格变换数据集清洗过程中的交互流畅度和后台文件移动安全性。

### 新增

- 后台移动队列（Background Move Queue），用于非阻塞处理 `done/out` 文件移动。
- 队列状态面板，显示 queued、running、moved、failed 等任务状态。
- 后台失败回滚：当部分移动可安全逆转时，失败任务会尽可能回滚。
- 失败阻断：后台任务失败后，后续队列移动不会静默继续执行。
- 预览缓存（Preview Cache），减少人工筛选时的重复缩略图解码。
- 新增后台移动成功和后台失败回滚单元测试。

### 保留

- 直接选择目标图片工作文件夹。
- 自动从 `images/...` 推断对应 `labels/...`。
- 可选显式 `--label-dir`。
- 支持非常规审核目录中的动态 `.rf.` prefix 组大小。
- 兼容 `ManualReview_GroupSize_N` 工作流。
- 图片与标签同步清理到 `done/out`。
- 撤销上一组已完成事务。
- JSON、CSV、Markdown 校核报告。

### 验证

- 单元测试：`15/15 OK`。
- 发布包不包含原始图片、标签、运行日志、审计输出、模型文件或数据集压缩包。

### 状态

校核输出只作为数据清洗过程证据，不代表模型性能结论。
