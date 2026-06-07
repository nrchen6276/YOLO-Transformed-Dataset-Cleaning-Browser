# Release Notes: YOLO Transformed Dataset Cleaning Browser V2.2.1_202606042101

## English

`V2.2.1_202606042101` follows `V2.2_202606042006` in the internal release order. It is a standalone executable hotfix for the V2.2 interaction release.

### Highlights

- New package: `civl7009_picker_v2_2_1/`.
- Fixes `Core Load Failed` when the exe is moved to another computer or folder without the source tree beside it.
- Loads the V1.8.1 backend core from PyInstaller `_MEIPASS` before checking sibling paths.
- Adds clearer core-load failure logging.
- Preserves V2.2 automatic move readiness, horizontal navigation, keypad layout, and HKU red selection feedback.

### Included Artefacts

- `Dataset/Select_Programme/CIVL7009_source_group_picker_qt_V2.2.1_202606042101.py`
- `Dataset/Select_Programme/civl7009_picker_v2_2_1/`
- `Dataset/Select_Programme/test_source_group_picker_qt_V2.2.1_202606042101.py`
- `Dataset/Select_Programme/Executable/CIVL7009_Source_Group_Picker_V2.2.1_202606042101.exe`
- `Dataset/Select_Programme/Build_Spec/CIVL7009_Source_Group_Picker_V2.2.1_202606042101.spec`
- `Dataset/Select_Programme/Build_Reports/build_environment_V2.2.1_202606042101.json`
- `Dataset/Select_Programme/UI_Assets/V2.2.1_202606042101/`
- `Dataset/Select_Programme/README_V2.2.1_202606042101.md`

### Verification

```text
V2.2.1 Qt tests: 8/8 OK
V2.2 Qt regression: 7/7 OK
V2.1 Qt regression: 5/5 OK
V1.8.1 backend tests: 32 OK, skipped=1
source --help OK
source --smoke-open --run-mode debug OK
exe --help OK
exe --smoke-open OK
standalone copied-exe smoke OK
zip extraction smoke OK
```

### Safety Boundary

The release package does not include raw dataset images, labels, runtime logs, audit reports, model weights, or dataset archives. It does not train or evaluate models. Governance outputs remain `PENDING_AUDIT`.

## 中文

`V2.2.1_202606042101` 在内部版本顺序中紧接 `V2.2_202606042006`。它是 V2.2 交互版本的单文件 exe 热修复版。

### 主要更新

- 新包：`civl7009_picker_v2_2_1/`。
- 修复 exe 移动到另一台电脑或其他文件夹、旁边没有源码树时出现的 `Core Load Failed`。
- 加载 V1.8.1 后端 core 时优先检查 PyInstaller `_MEIPASS`，再检查同级路径。
- 增加更清晰的 core 加载失败日志。
- 保留 V2.2 的自动移动准备、横向导航、小键盘布局和 HKU 红色选中反馈。

### 本次包含

- `Dataset/Select_Programme/CIVL7009_source_group_picker_qt_V2.2.1_202606042101.py`
- `Dataset/Select_Programme/civl7009_picker_v2_2_1/`
- `Dataset/Select_Programme/test_source_group_picker_qt_V2.2.1_202606042101.py`
- `Dataset/Select_Programme/Executable/CIVL7009_Source_Group_Picker_V2.2.1_202606042101.exe`
- `Dataset/Select_Programme/Build_Spec/CIVL7009_Source_Group_Picker_V2.2.1_202606042101.spec`
- `Dataset/Select_Programme/Build_Reports/build_environment_V2.2.1_202606042101.json`
- `Dataset/Select_Programme/UI_Assets/V2.2.1_202606042101/`
- `Dataset/Select_Programme/README_V2.2.1_202606042101.md`

### 验证结果

```text
V2.2.1 Qt tests: 8/8 OK
V2.2 Qt regression: 7/7 OK
V2.1 Qt regression: 5/5 OK
V1.8.1 backend tests: 32 OK, skipped=1
source --help OK
source --smoke-open --run-mode debug OK
exe --help OK
exe --smoke-open OK
standalone copied-exe smoke OK
zip extraction smoke OK
```

### 安全边界

发布包不包含原始数据集图片、标签、运行日志、审计报告、模型权重或数据集压缩包。它不训练或评估模型。治理输出保持 `PENDING_AUDIT`。

