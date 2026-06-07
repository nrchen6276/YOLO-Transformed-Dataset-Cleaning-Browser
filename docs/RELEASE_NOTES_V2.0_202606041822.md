# Release Notes: YOLO Transformed Dataset Cleaning Browser V2.0_202606041822

## English

`V2.0_202606041822` is the full PySide6 framework release. It follows `V1.9.1_202606041705` in the internal release sequence and keeps the tested V1.8.1/V1.9.1 safety boundary while adding a modular application framework for future dataset-cleaning workflows.

### Highlights

- Modular PySide6 framework package: `civl7009_picker_v2/`.
- Capability Matrix for feature flags, risk levels, raw-file movement status, and gates.
- Manifest-only Queue framework enabled by default; it does not move raw files.
- SQLite manifest integrity checks, schema metadata, and migration guardrails.
- Default-off Physical Staging framework with same-volume and recovery safeguards.
- Recovery Centre, Diagnostics Panel, Productivity Dashboard, Settings, and ID Initialisation Wizard pages.
- image2/procedural abstract UI assets with manifest, prompt log, and design tokens.
- Light, dark, high-contrast, and visual-quality foundations.
- Windows executable included.

### Included Artefacts

- `Dataset/Select_Programme/CIVL7009_source_group_picker_qt_V2.0_202606041822.py`
- `Dataset/Select_Programme/civl7009_picker_v2/`
- `Dataset/Select_Programme/test_source_group_picker_qt_V2.0_202606041822.py`
- `Dataset/Select_Programme/Executable/CIVL7009_Source_Group_Picker_V2.0_202606041822.exe`
- `Dataset/Select_Programme/Build_Spec/CIVL7009_Source_Group_Picker_V2.0_202606041822.spec`
- `Dataset/Select_Programme/Build_Reports/build_environment_V2.0_202606041822.json`
- `Dataset/Select_Programme/Build_Reports/UI_Snapshots/V2.0_202606041822/`
- `Dataset/Select_Programme/UI_Assets/V2.0_202606041822/`
- `Dataset/Select_Programme/README_V2.0_202606041822.md`

### Verification

```text
V2.0 Qt/framework tests: 9/9 OK
V1.9.1 Qt tests: 7/7 OK
V1.8.1 backend tests: 32 OK, skipped=1
source --help OK
source --smoke-open OK
exe --help OK
exe --smoke-open OK
zip extraction smoke OK
```

### Safety Boundary

The release package does not include raw dataset images, labels, runtime logs, audit reports, model weights, or dataset archives. Manifest-only Queue is non-mutating. Physical Staging is implemented only as a guarded framework and remains off by default.

## 中文

`V2.0_202606041822` 是 PySide6 全框架版本。它在内部版本顺序中接在 `V1.9.1_202606041705` 之后，保留已测试的 V1.8.1/V1.9.1 安全边界，并新增模块化应用框架，方便后续扩展数据集清洗工作流。

### 主要更新

- 模块化 PySide6 框架包：`civl7009_picker_v2/`。
- 能力矩阵（Capability Matrix），用于显示功能开关、风险等级、raw-file movement 状态和启用门槛。
- 清单队列（Manifest-only Queue）框架默认启用；它不移动 raw files。
- SQLite 清单完整性检查、schema metadata 和迁移保护。
- 物理暂存（Physical Staging）框架默认关闭，并带同盘和恢复保护。
- 恢复中心、诊断面板、操作仪表盘、设置页和 ID 初始化向导页面。
- image2 / 程序化抽象 UI 资产，包含 asset manifest、prompt log 和 design tokens。
- light、dark、high contrast 与视觉质量模式基础。
- 包含 Windows 可执行程序。

### 本次包含

- `Dataset/Select_Programme/CIVL7009_source_group_picker_qt_V2.0_202606041822.py`
- `Dataset/Select_Programme/civl7009_picker_v2/`
- `Dataset/Select_Programme/test_source_group_picker_qt_V2.0_202606041822.py`
- `Dataset/Select_Programme/Executable/CIVL7009_Source_Group_Picker_V2.0_202606041822.exe`
- `Dataset/Select_Programme/Build_Spec/CIVL7009_Source_Group_Picker_V2.0_202606041822.spec`
- `Dataset/Select_Programme/Build_Reports/build_environment_V2.0_202606041822.json`
- `Dataset/Select_Programme/Build_Reports/UI_Snapshots/V2.0_202606041822/`
- `Dataset/Select_Programme/UI_Assets/V2.0_202606041822/`
- `Dataset/Select_Programme/README_V2.0_202606041822.md`

### 验证结果

```text
V2.0 Qt/framework tests: 9/9 OK
V1.9.1 Qt tests: 7/7 OK
V1.8.1 backend tests: 32 OK, skipped=1
source --help OK
source --smoke-open OK
exe --help OK
exe --smoke-open OK
zip extraction smoke OK
```

### 安全边界

发布包不包含原始数据集图片、标签、运行日志、审计报告、模型权重或数据集压缩包。清单队列不改变 raw files。物理暂存仅作为受保护框架存在，并默认关闭。
