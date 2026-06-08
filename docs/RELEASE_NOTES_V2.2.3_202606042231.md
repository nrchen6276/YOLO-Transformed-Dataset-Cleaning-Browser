# YOLO Transformed Dataset Cleaning Browser V2.2.3_202606042231

## English

V2.2.3 is a compact UI-status hotfix after V2.2.2. It keeps the standalone executable bundled-core fix, automatic move workflow, in-place undo refresh, red image-card selection feedback, and resizable bottom panel.

### Highlights

- Undo refresh no longer leaves a large overlay in the image stage.
- Short operational states now appear in a navigation-row status chip.
- Safe Gate status uses single-line Chinese badges to avoid top-bar wrapping.
- The Command Bar is denser and better suited to long review-directory paths.
- Long context paths are elided in the UI while retaining full tooltips.

### Validation

- V2.2.3 Qt tests: `9/9 OK`
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

`YOLO_Transformed_Dataset_Cleaning_Browser_V2.2.3_202606042231.zip`

The archive contains the Windows executable, source entrypoint, versioned Python package, tests, build metadata, and abstract UI assets. It excludes raw dataset images, labels, model weights, and dataset YAML files.

All operational conclusions remain `PENDING_AUDIT`.

## 中文

V2.2.3 是 V2.2.2 之后的紧凑状态栏热修复版本。它保留单文件 exe 内置 core 修复、自动移动工作流、撤销原地刷新、红色选中反馈和底部可拖动面板。

### 更新重点

- 撤销刷新不再把大 overlay 留在图片区。
- 短状态提示进入横向导航行右侧的小状态 chip。
- Safe Gate 状态使用中文单行 badge，避免顶栏换行。
- Command Bar 更紧凑，更适合显示长筛选目录路径。
- 长路径在界面中省略显示，但完整内容保留在 tooltip。

### 验证

- V2.2.3 Qt 测试：`9/9 OK`
- V2.2.2 Qt 回归：`8/8 OK`
- V2.2.1 Qt 回归：`8/8 OK`
- V2.1 Qt 回归：`5/5 OK`
- V1.9.1 Qt 回归：`7/7 OK`
- V1.8.1 后端回归：`32 OK, 1 skipped`
- exe smoke 与复制到临时目录后的 standalone exe smoke：通过
- release zip smoke：通过
- `Dataset/Select_Programme` 中 raw dataset raster 文件数：`0`

### 下载资产

`YOLO_Transformed_Dataset_Cleaning_Browser_V2.2.3_202606042231.zip`

压缩包包含 Windows exe、源码入口、版本化 Python 包、测试、构建元数据和抽象 UI 资产，不包含原始数据集图片、标签、模型权重或数据集 YAML。

所有运行和治理结论仍保持 `PENDING_AUDIT`。
