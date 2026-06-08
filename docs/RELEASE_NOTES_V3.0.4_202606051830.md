# YOLO Transformed Dataset Cleaning Browser V3.0.4_202606051830

## English

V3.0.4 adds per-dataset class-file support for YOLO `.txt` bounding-box overlays in Manual Objects Review.

When a Manual Objects root is opened, the application detects dataset IDs from the global index and prepares `Manual_Objects/ID_Classes/<dataset_id>/` folders. Reviewers can place any non-empty `.txt` class list into the corresponding ID folder. The filename does not have to be `classes.txt`. The first valid `.txt` file in filename order is used to label bounding boxes for that dataset ID.

### Highlights

- Auto-detect dataset IDs from Manual Objects.
- Auto-create `ID_Classes/<dataset_id>/` support folders.
- Accept arbitrary non-empty `.txt` class-file names.
- Detect missing, empty, multiple, and valid class-file states.
- Add a class-file status dialog with open-folder and refresh actions.
- Refresh BBox labels when class maps change.
- Keeps V3 safety boundaries: no hash scanning, no candidate generation, no source-library movement, and no staged image or label modification.

### Validation

- V3.0.4 tests: `13/13 OK`
- V3.0.3 regression: `11/11 OK`
- V2.2.4 regression: `10/10 OK`
- Source-run `--help`: OK
- Source-run `--smoke-open`: OK
- Packaged exe `--smoke-open`: OK
- Package and asset safety scan: clean.

## 中文

V3.0.4 为 Manual Objects 复核中的 YOLO `.txt` BBox 叠加预览新增按数据集 ID 的类别文件支持。

打开 Manual Objects 根目录后，程序会从全局 index 中识别涉及的数据集 ID，并准备 `Manual_Objects/ID_Classes/<dataset_id>/` 文件夹。人工可以把任意非空 `.txt` 类别列表放入对应 ID 文件夹，文件名不必是 `classes.txt`。程序按文件名排序读取第一个有效 `.txt`，用于该 ID 的 BBox 类别名显示。

### 更新重点

- 从 Manual Objects 自动识别 dataset ID。
- 自动创建 `ID_Classes/<dataset_id>/` 支持目录。
- 支持任意非空 `.txt` 类别文件名。
- 检测缺失、空文件、多文件和有效类别文件状态。
- 新增类别文件状态弹窗，支持打开目录和刷新检测。
- 类别映射变化后刷新 BBox 标签。
- 保持 V3 安全边界：不执行哈希扫描、不生成候选区、不移动主库文件、不修改候选图片或标签。

### 验证

- V3.0.4 测试：`13/13 OK`
- V3.0.3 回归：`11/11 OK`
- V2.2.4 回归：`10/10 OK`
- source-run `--help`: OK
- source-run `--smoke-open`: OK
- exe `--smoke-open`: OK
- 包与 UI asset 安全扫描：干净。
