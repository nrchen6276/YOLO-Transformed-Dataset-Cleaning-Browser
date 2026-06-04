# Release Notes — V1.3

[中文](#中文)

## English

`YOLO Transformed Dataset Cleaning Browser V1.3` is an incremental release focused on faster transaction preparation and smoother manual browsing after the V1.2 background move queue.

### Added

- Cached label index for faster repeated label lookup.
- Current-group transaction preparation from already displayed group members.
- Unit test for cached-member and label-index transaction preparation.
- Background audit refresh after queued move completion.
- Upcoming-group preloading to warm the preview cache.

### Kept

- Background move queue and failure rollback.
- Queue status panel.
- Preview cache.
- Direct target image-folder selection.
- Automatic `images/...` to `labels/...` pairing.
- Dynamic `.rf.` prefix group-size handling for ad-hoc review folders.
- Strict image-label cleanup into `done/out`.
- Undo for the last completed transaction.
- JSON, CSV, and Markdown audit reports.

### Verified

- Unit tests: `16/16 OK`.
- Release package excludes raw images, labels, runtime logs, audit outputs, model files, and dataset archives.

### Status

Audit outputs are operational cleaning evidence and do not make model-performance claims.

## 中文

`YOLO Transformed Dataset Cleaning Browser V1.3` 是一次增量发布，重点是在 V1.2 后台移动队列之后继续提升事务准备速度和人工浏览流畅度。

### 新增

- 标签索引缓存，用于加速重复标签定位。
- 基于已显示当前组成员的事务准备。
- 新增缓存成员与标签索引事务准备单元测试。
- 队列移动完成后的后台审计刷新。
- 后续图片组预加载，用于提前温热预览缓存。

### 保留

- 后台移动队列和失败回滚。
- 队列状态面板。
- 预览缓存。
- 直接选择目标图片工作文件夹。
- 自动从 `images/...` 推断对应 `labels/...`。
- 支持非常规审核目录中的动态 `.rf.` prefix 组大小。
- 严格图片-标签同步清理到 `done/out`。
- 撤销上一组已完成事务。
- JSON、CSV、Markdown 校核报告。

### 验证

- 单元测试：`16/16 OK`。
- 发布包不包含原始图片、标签、运行日志、审计输出、模型文件或数据集压缩包。

### 状态

校核输出只作为数据清洗过程证据，不代表模型性能结论。
