# Release Notes - V1.7_202606040155

[中文](#中文)

## English

`V1.7_202606040155` is the next internal-version release after `V1.6_202606040015`. It remains in the Tkinter line and adds an ID Initialisation workflow for ordinary YOLO datasets. Later PySide6, Manual Objects, conflict-review, Tier-prefix, and N20_PLUS features are intentionally not included.

### Added / Improved

- ID Initialisation page for YOLO-style datasets.
- Detection of common dataset layouts:
  - `root/images` with `root/labels`;
  - `root/train|valid|val|test/images` with matching labels.
- Image-label pairing audit with missing-label, orphan-label, missing `.rf.` prefix, and target-conflict reporting.
- Markdown export for the YOLO initialisation audit.
- Initialisation into `ManualReview_GroupSize_N` boards by copying matched `.rf.` image-label pairs.
- Original YOLO folders are not moved or deleted during initialisation.
- Background audit refresh for the review board.

### Kept

- Concrete prefix/file issue details from V1.6.
- Cached-state transaction planning for the current group.
- Traditional numeric-keypad layout and number-key image selection.
- Background move queue for image-label `done/out` transactions.
- Process log (Plog), thumbnail cache, preload, rollback-on-failure, undo, dynamic `.rf.` grouping, and audit export.

### Verified

- V1.7 tests: `21/21 OK`.
- Executable help smoke: `--help` exit code `0`.
- Release package excludes raw images, labels, runtime logs, audit outputs, model files, and dataset archives.

### Status

All audit outputs remain `PENDING_AUDIT`. This release is operational review and initialisation tooling, not model-performance evidence.

## 中文

`V1.7_202606040155` 是严格接在内部 `V1.6_202606040015` 之后的下一版。它仍属于 Tkinter 线，并新增普通 YOLO 数据集的 ID 初始化工作流。后续 PySide6、Manual Objects、冲突复核、Tier 前缀治理或 N20_PLUS 功能不属于本版本。

### 新增 / 改进

- 新增 YOLO 风格数据集的 ID 初始化页。
- 识别常见数据集结构：
  - `root/images` 与 `root/labels`；
  - `root/train|valid|val|test/images` 与对应 labels。
- 图片-标签匹配校核，包含缺失标签、孤立标签、缺少 `.rf.` prefix 和目标文件冲突报告。
- 可导出 YOLO 初始化 Markdown 校核报告。
- 将匹配成功且带 `.rf.` prefix 的图片-标签对复制到 `ManualReview_GroupSize_N` 大盘。
- 初始化过程不会移动或删除原始 YOLO 文件夹。
- Review Board 支持后台校核刷新。

### 保留

- V1.6 的具体 prefix/文件异常明细。
- 当前组基于缓存状态（cached state）的事务准备。
- 传统数字小键盘布局和数字键图片选择。
- 后台移动队列，用于执行图片与标签同步的 `done/out` 事务。
- 过程日志（Process Log, Plog）、缩略图缓存、预加载、失败回滚、撤销、动态 `.rf.` 分组和校核报告导出。

### 验证

- V1.7 测试：`21/21 OK`。
- 可执行文件 help smoke：`--help` 退出码 `0`。
- 发布包不包含原始图片、标签、运行日志、审计输出、模型文件或数据集压缩包。

### 状态

所有校核输出保持 `PENDING_AUDIT`。本版本是数据复核与初始化工具，不是模型性能证据。
