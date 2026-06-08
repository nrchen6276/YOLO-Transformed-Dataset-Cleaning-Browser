# YOLO Transformed Dataset Cleaning Browser V2.2.4_202606042313

## English

V2.2.4 is a compatibility hotfix after V2.2.3. It preserves the compact UI polish while adding support for dynamic, non-standard review folders through the V1.8.2 core line.

### Highlights

- Uses the V1.8.2 core for source-group review logic.
- Supports non-standard folders such as `images/special` with paired labels.
- Handles mixed group-size review directories rather than requiring a fixed `ManualReview_GroupSize_N` name.
- Keeps automatic move readiness, compact status chip, single-line Safe Gate badge, red selection feedback, in-place undo refresh, and draggable queue/event panels.

### Validation

- V2.2.4 Qt tests: `10/10 OK`
- V2.2.3 Qt regression: `9/9 OK`
- V2.2.2 Qt regression: `8/8 OK`
- V2.2.1 Qt regression: `8/8 OK`
- V2.1 Qt regression: `5/5 OK`
- V1.9.1 Qt regression: `7/7 OK`
- V1.8.1 backend regression: `32 OK, 1 skipped`
- Executable smoke and copied-exe smoke: passed
- Release zip smoke: passed
- Raw dataset raster count in `Dataset/Select_Programme`: `0`

### Asset

Download:

`YOLO_Transformed_Dataset_Cleaning_Browser_V2.2.4_202606042313.zip`

The archive contains the Windows executable, source entrypoint, V1.8.2 core, versioned Python package, tests, build metadata, and abstract UI assets. It excludes raw dataset images, labels, model weights, and dataset YAML files.

All operational conclusions remain `PENDING_AUDIT`.

## 中文

V2.2.4 是 V2.2.3 之后的兼容性热修复版本。它保留紧凑 UI 优化，同时通过 V1.8.2 core 支持动态分组和非常规筛选目录。

### 更新重点

- 使用 V1.8.2 core 承接图源组筛选逻辑。
- 支持 `images/special` 等非常规目录，只要有对应 labels 目录。
- 支持混合组大小的筛选目录，不再只依赖固定的 `ManualReview_GroupSize_N` 命名。
- 保留自动移动准备、紧凑状态 chip、中文单行 Safe Gate badge、红色选中反馈、撤销原地刷新和底部队列/事件可拖动面板。

### 验证

- V2.2.4 Qt 测试：`10/10 OK`
- V2.2.3 Qt 回归：`9/9 OK`
- V2.2.2 Qt 回归：`8/8 OK`
- V2.2.1 Qt 回归：`8/8 OK`
- V2.1 Qt 回归：`5/5 OK`
- V1.9.1 Qt 回归：`7/7 OK`
- V1.8.1 后端回归：`32 OK, 1 skipped`
- exe smoke 与复制到临时目录后的 standalone exe smoke：通过
- release zip smoke：通过
- `Dataset/Select_Programme` 中 raw dataset raster 文件数：`0`

### 下载资产

`YOLO_Transformed_Dataset_Cleaning_Browser_V2.2.4_202606042313.zip`

压缩包包含 Windows exe、源码入口、V1.8.2 core、版本化 Python 包、测试、构建元数据和抽象 UI 资产，不包含原始数据集图片、标签、模型权重或数据集 YAML。

所有运行和治理结论仍保持 `PENDING_AUDIT`。
