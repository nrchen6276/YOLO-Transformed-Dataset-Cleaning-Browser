# YOLO Transformed Dataset Cleaning Browser V3.0_202606050530

## English

V3.0 is the first Manual Objects Review release. It expands the browser from source-group selection into a two-workflow review tool for YOLO dataset cleaning: Source Group Review and Manual Objects Review.

### Highlights

- Adds workflow tabs for Source Group Review, Manual Objects Review, and Diagnostics / Settings.
- Reads Manual Objects groups from reason / bucket / group folders.
- Treats `group_manifest.json` as the authority for candidate metadata.
- Displays cross-dataset candidate images and label metadata.
- Supports single-keep and multi-keep selection modes.
- Writes `manual_selection.json` with `APPROVED`, `SKIP`, `AMBIGUOUS`, or `NEEDS_AGENT_CHECK`.
- Backs up existing selections to `_selection_history` before replacement.
- Keeps V2.2.4 dynamic source-group review for non-standard folders such as `images/special`.

### Safety Boundary

Manual Objects Review does not run hash scanning, does not create candidate groups, does not move source-library files, and does not delete candidate copies. It only writes review-result files inside the candidate group folder.

### Validation

- V3.0 Qt tests: `6/6 OK`
- V2.2.4 Qt regression: `10/10 OK`
- V1.8.1 backend regression: `32 OK, 1 skipped`
- Source import and packaged executable checks: passed
- Clean-machine / copied-exe smoke was not part of this V3.0 iteration
- Release zip smoke: passed
- Raw dataset raster count in `Dataset/Select_Programme`: `0`

### Asset

Download:

`YOLO_Transformed_Dataset_Cleaning_Browser_V3.0_202606050530.zip`

The archive contains the Windows executable, source entrypoint, V1.8.2 core, versioned Python package, tests, build metadata, and abstract UI assets. It excludes raw dataset images, labels, model weights, and dataset YAML files.

All operational conclusions remain `PENDING_AUDIT`.

## 中文

V3.0 是首个跨库候选复核（Manual Objects Review）版本。它把工具从单一图源组筛选扩展为双工作流清洗浏览器：图源组筛选与跨库候选复核。

### 更新重点

- 新增图源组筛选、跨库候选复核、诊断与设置三个主工作流标签。
- 按 reason / bucket / group 读取 Manual Objects 候选组。
- 以 `group_manifest.json` 作为候选元数据权威来源。
- 展示跨数据集候选图片和标签元数据。
- 支持单保留和多保留选择模式。
- 写入 `manual_selection.json`，状态包括 `APPROVED`、`SKIP`、`AMBIGUOUS`、`NEEDS_AGENT_CHECK`。
- 重新保存前将旧选择结果备份到 `_selection_history`。
- 保留 V2.2.4 的非常规图源组目录支持，例如 `images/special`。

### 安全边界

Manual Objects Review 不执行哈希扫描，不创建候选组，不移动主库文件，不删除候选副本。它只在候选组文件夹内写入人工复核结果。

### 验证

- V3.0 Qt 测试：`6/6 OK`
- V2.2.4 Qt 回归：`10/10 OK`
- V1.8.1 后端回归：`32 OK, 1 skipped`
- source import 与已打包 exe 基础检查：通过
- clean-machine / copied-exe smoke 不属于本次 V3.0 验收范围
- release zip smoke：通过
- `Dataset/Select_Programme` 中 raw dataset raster 文件数：`0`

### 下载资产

`YOLO_Transformed_Dataset_Cleaning_Browser_V3.0_202606050530.zip`

压缩包包含 Windows exe、源码入口、V1.8.2 core、版本化 Python 包、测试、构建元数据和抽象 UI 资产，不包含原始数据集图片、标签、模型权重或数据集 YAML。

所有运行和治理结论仍保持 `PENDING_AUDIT`。
