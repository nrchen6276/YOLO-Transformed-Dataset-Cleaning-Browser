# Release Notes — V1.1

[中文](#中文)

## English

`CIVL7009 Source Group Picker V1.1` is an incremental release for YOLO-style visual training dataset source-group review and cleanup. It keeps the V1.0 transaction safety model and expands the workflow from fixed review-folder names to more flexible target image-folder selection.

### Added

- Direct target image-folder selection from the GUI.
- `--image-dir` command-line option for auditing or opening one image working folder.
- `--label-dir` command-line option for explicitly pairing a label working folder.
- Backward-compatible `--review-dir` alias.
- Automatic paired label-folder inference from an `images/...` path to the matching `labels/...` path.
- Dynamic group-size support for ad-hoc review folders where different `.rf.` prefixes may have different member counts.
- Target-folder audit export for a single selected working folder.

### Changed

- `ManualReview_GroupSize_N` is now treated as a group-size hint rather than the only valid review-folder form.
- Root group-size mismatch against the folder-name hint is reported as a warning when the prefix is otherwise valid and selectable.
- Audit summaries describe source-group working folders rather than a project-specific local data-governance path.

### Kept

- Synchronous image-label movement into `done/out`.
- Strict duplicate/missing-label and target-conflict blocking.
- Undo for the last completed transaction.
- JSON, CSV, and Markdown audit reports.
- Windows executable release asset.

### Verified

- Unit tests: `13/13 OK`.
- Release package excludes raw images, labels, runtime logs, audit outputs, model files, and dataset archives.

### Status

Audit outputs are operational cleaning evidence and do not make model-performance claims.

## 中文

`CIVL7009 Source Group Picker V1.1` 是面向 YOLO 风格视觉训练数据集图源组审核与清洗的增量发布版本。它保留 V1.0 的事务安全模型，并把工作流从固定审核目录名扩展为更灵活的目标图片文件夹选择。

### 新增

- GUI 支持直接选择目标图片工作文件夹。
- 新增 `--image-dir` 命令行参数，用于审计或打开单个图片工作文件夹。
- 新增 `--label-dir` 命令行参数，用于显式指定配对标签工作文件夹。
- 保留向后兼容的 `--review-dir` 别名。
- 支持从 `images/...` 路径自动推断匹配的 `labels/...` 路径。
- 支持非常规审核目录中的动态组大小；不同 `.rf.` prefix 可以拥有不同成员数。
- 支持为单个目标工作文件夹导出校核报告。

### 改动

- `ManualReview_GroupSize_N` 现在被视为组大小提示，而不是唯一合法的审核目录形式。
- 当实际 root 组大小与目录名提示不一致，但 prefix 本身有效且可筛时，报告 warning 而不是直接阻断。
- 审计摘要改为描述图源组工作文件夹，不再绑定某个本地数据治理路径。

### 保留

- 图片与标签同步移动到 `done/out`。
- 严格阻断标签重复、标签缺失和目标冲突。
- 撤销上一组已完成事务。
- JSON、CSV、Markdown 校核报告。
- Windows exe 发布资产。

### 验证

- 单元测试：`13/13 OK`。
- 发布包不包含原始图片、标签、运行日志、审计输出、模型文件或数据集压缩包。

### 状态

校核输出只作为数据清洗过程证据，不代表模型性能结论。
