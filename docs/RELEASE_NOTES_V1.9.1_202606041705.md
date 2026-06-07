# Release Notes: YOLO Transformed Dataset Cleaning Browser V1.9.1_202606041705

## English

`V1.9.1_202606041705` is the first public PySide6 Review Cockpit package in this release line. It keeps the tested V1.8.1 backend core and adds a safer modern Qt shell for source-group review.

### Highlights

- PySide6/macOS-glass-style review cockpit.
- Safe Gate workflow: preview by default; file moves only after explicit in-app enabling.
- Core auditability: UI version, core version, core path, and SHA256 are logged separately.
- Core validation: missing backend symbols or import side effects fail closed.
- Open-review progress overlay and ready state.
- Qt-safe worker model for quick preview, full index, audit, thumbnail loading, and export.
- Abstract SVG UI assets with manifest; no dataset-derived imagery.
- Windows executable included.

### Included Artefacts

- `Dataset/Select_Programme/CIVL7009_source_group_picker_qt_V1.9.1_202606041705.py`
- `Dataset/Select_Programme/test_source_group_picker_qt_V1.9.1_202606041705.py`
- `Dataset/Select_Programme/CIVL7009_source_group_picker_gui_V1.8.1_202606041443.py`
- `Dataset/Select_Programme/Executable/CIVL7009_Source_Group_Picker_V1.9.1_202606041705.exe`
- `Dataset/Select_Programme/Build_Spec/CIVL7009_Source_Group_Picker_V1.9.1_202606041705.spec`
- `Dataset/Select_Programme/Build_Reports/build_environment_V1.9.1_202606041705.json`
- `Dataset/Select_Programme/UI_Assets/V1.9.1_202606041705/`

### Verification

```text
V1.9.1 Qt tests: 7/7 OK
V1.8.1 backend tests: 32 OK, skipped=1
source --help OK
exe audit-only smoke OK on a temporary sample dataset
zip extraction smoke OK
```

The windowed executable may print `--help` text with a non-clean PowerShell process code because it is packaged with `console=False`. The accepted executable smoke test is therefore `--audit-only`, which exits successfully.

### Safety Boundary

The release package does not include raw dataset images, labels, runtime logs, audit reports, model weights, or dataset archives. File movement remains restricted to the selected review folder and the Safe Gate workflow.

## 中文

`V1.9.1_202606041705` 是本发版线中首个公开 PySide6 复核驾驶舱包。它保留已测试的 V1.8.1 后端核心，并新增更安全、现代的 Qt 桌面外壳，用于图源组复核。

### 主要更新

- PySide6 / macOS glass 风格复核驾驶舱。
- 安全门（Safe Gate）工作流：默认只预览；真实文件移动必须在程序内显式启用。
- 核心可审计性：日志分别记录 UI 版本、core 版本、core 路径和 SHA256。
- Core 校验：后端符号缺失或导入副作用异常时 fail closed。
- 打开复核目录时显示进度遮罩和 ready 状态。
- Qt-safe worker 模型，用于快速预览、完整索引、审计、缩略图加载和导出。
- 抽象 SVG UI 资产与 manifest；不包含数据集派生图像。
- 包含 Windows 可执行程序。

### 本次包含

- `Dataset/Select_Programme/CIVL7009_source_group_picker_qt_V1.9.1_202606041705.py`
- `Dataset/Select_Programme/test_source_group_picker_qt_V1.9.1_202606041705.py`
- `Dataset/Select_Programme/CIVL7009_source_group_picker_gui_V1.8.1_202606041443.py`
- `Dataset/Select_Programme/Executable/CIVL7009_Source_Group_Picker_V1.9.1_202606041705.exe`
- `Dataset/Select_Programme/Build_Spec/CIVL7009_Source_Group_Picker_V1.9.1_202606041705.spec`
- `Dataset/Select_Programme/Build_Reports/build_environment_V1.9.1_202606041705.json`
- `Dataset/Select_Programme/UI_Assets/V1.9.1_202606041705/`

### 验证结果

```text
V1.9.1 Qt tests: 7/7 OK
V1.8.1 backend tests: 32 OK, skipped=1
source --help OK
exe audit-only smoke OK on a temporary sample dataset
zip extraction smoke OK
```

由于本版本 exe 使用 `console=False` 打包，部分 PowerShell 会出现 `--help` 文本已打印但进程退出码不干净的现象。因此本次接受的 exe smoke test 是 `--audit-only`，该测试正常通过。

### 安全边界

发布包不包含原始数据集图片、标签、运行日志、审计报告、模型权重或数据集压缩包。文件移动仍限制在用户所选复核目录内部，并受 Safe Gate 工作流保护。
