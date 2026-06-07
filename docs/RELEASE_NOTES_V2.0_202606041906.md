# Release Notes: YOLO Transformed Dataset Cleaning Browser V2.0_202606041906

## English

`V2.0_202606041906` follows `V2.0_202606041822` in the internal release order. It is a packaged-executable hotfix rebuild for the V2.0 PySide6 full-framework release.

### What Changed

- Fixed packaged exe startup behaviour.
- Normalised command-line arguments before `argparse`.
- Changed the versioned entry script to call `main()` rather than passing `sys.argv` into the application entrypoint.
- Added/kept `--smoke-open` startup diagnostics for source and exe mode.
- Rebuilt the Windows executable as `CIVL7009_Source_Group_Picker_V2.0_202606041906.exe`.

### What Stayed the Same

- V2.0 modular PySide6 framework: `civl7009_picker_v2/`.
- Capability Matrix, manifest-only queue framework, SQLite manifest integrity, recovery centre, diagnostics, dashboard, settings, ID Initialisation Wizard, and image2/procedural assets.
- Manifest-only queue remains non-mutating.
- Physical staging remains default off.
- Governance outputs remain `PENDING_AUDIT`.

### Included Artefacts

- `Dataset/Select_Programme/CIVL7009_source_group_picker_qt_V2.0_202606041906.py`
- `Dataset/Select_Programme/civl7009_picker_v2/`
- `Dataset/Select_Programme/Executable/CIVL7009_Source_Group_Picker_V2.0_202606041906.exe`
- `Dataset/Select_Programme/Build_Spec/CIVL7009_Source_Group_Picker_V2.0_202606041906.spec`
- `Dataset/Select_Programme/Build_Reports/build_environment_V2.0_202606041906.json`
- `Dataset/Select_Programme/UI_Assets/V2.0_202606041906/`
- `Dataset/Select_Programme/README_V2.0_202606041906.md`

### Verification

```text
V2.0 framework tests: 9/9 OK
V1.9.1 Qt tests: 7/7 OK
V1.8.1 backend tests: 32 OK, skipped=1
source --help OK
source --smoke-open OK
exe --help OK
exe --smoke-open OK
zip extraction smoke OK
```

### Safety Boundary

The release package does not include raw dataset images, labels, runtime logs, audit reports, model weights, or dataset archives. It does not train or evaluate models, does not generate hash candidate groups, and does not upgrade any data-governance claim beyond `PENDING_AUDIT`.

## 中文

`V2.0_202606041906` 在内部版本顺序中紧接 `V2.0_202606041822`。它是 V2.0 PySide6 全框架版本的 packaged executable hotfix（封装可执行文件启动修复）重构建。

### 本次变化

- 修复 packaged exe 启动行为。
- 在 `argparse` 前归一化命令行参数。
- 将版本化入口脚本改为调用 `main()`，不再把 `sys.argv` 直接传入应用入口。
- 保留 `--smoke-open` 启动诊断，覆盖源码模式和 exe 模式。
- 重新构建 Windows 可执行文件：`CIVL7009_Source_Group_Picker_V2.0_202606041906.exe`。

### 保持不变

- V2.0 模块化 PySide6 框架：`civl7009_picker_v2/`。
- 能力矩阵、清单队列框架、SQLite 清单完整性、恢复中心、诊断中心、仪表盘、设置页、ID 初始化向导和 image2 / 程序化 UI 资产。
- 清单队列不移动 raw files。
- 物理暂存默认关闭。
- 治理输出仍保持 `PENDING_AUDIT`。

### 本次包含

- `Dataset/Select_Programme/CIVL7009_source_group_picker_qt_V2.0_202606041906.py`
- `Dataset/Select_Programme/civl7009_picker_v2/`
- `Dataset/Select_Programme/Executable/CIVL7009_Source_Group_Picker_V2.0_202606041906.exe`
- `Dataset/Select_Programme/Build_Spec/CIVL7009_Source_Group_Picker_V2.0_202606041906.spec`
- `Dataset/Select_Programme/Build_Reports/build_environment_V2.0_202606041906.json`
- `Dataset/Select_Programme/UI_Assets/V2.0_202606041906/`
- `Dataset/Select_Programme/README_V2.0_202606041906.md`

### 验证结果

```text
V2.0 framework tests: 9/9 OK
V1.9.1 Qt tests: 7/7 OK
V1.8.1 backend tests: 32 OK, skipped=1
source --help OK
source --smoke-open OK
exe --help OK
exe --smoke-open OK
zip extraction smoke OK
```

### 安全边界

发布包不包含原始数据集图片、标签、运行日志、审计报告、模型权重或数据集压缩包。它不训练或评估模型，不生成哈希候选组，也不把任何数据治理结论升级到 `PENDING_AUDIT` 之外。

