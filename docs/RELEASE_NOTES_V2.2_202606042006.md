# Release Notes: YOLO Transformed Dataset Cleaning Browser V2.2_202606042006

## English

`V2.2_202606042006` follows `V2.1_202606041930` in the internal release order. It is an interaction polish release focused on high-throughput source-group review.

### Highlights

- New package: `civl7009_picker_v2_2/`.
- Removes typed `MOVE` confirmation while preserving safety gates.
- Adds a startup safety notice and automatic move readiness.
- Automatically enables file movement only after lock, recovery, fast index, full audit, and transaction-log checks pass.
- Replaces the left sidebar with compact horizontal navigation.
- Makes the Review Board table width-responsive.
- Restores HKU red selection feedback on image cards.
- Tightens global rounded-corner radii for a denser review workspace.

### Included Artefacts

- `Dataset/Select_Programme/CIVL7009_source_group_picker_qt_V2.2_202606042006.py`
- `Dataset/Select_Programme/civl7009_picker_v2_2/`
- `Dataset/Select_Programme/test_source_group_picker_qt_V2.2_202606042006.py`
- `Dataset/Select_Programme/Executable/CIVL7009_Source_Group_Picker_V2.2_202606042006.exe`
- `Dataset/Select_Programme/Build_Spec/CIVL7009_Source_Group_Picker_V2.2_202606042006.spec`
- `Dataset/Select_Programme/Build_Reports/build_environment_V2.2_202606042006.json`
- `Dataset/Select_Programme/UI_Assets/V2.2_202606042006/`
- `Dataset/Select_Programme/README_V2.2_202606042006.md`

### Verification

```text
V2.2 Qt tests: 7/7 OK
V2.1 Qt regression: 5/5 OK
V1.9.1 Qt regression: 7/7 OK
V1.8.1 backend tests: 32 OK, skipped=1
source --help OK
source --smoke-open OK
exe --help OK
exe --smoke-open OK
zip extraction smoke OK
```

### Safety Boundary

The release package does not include raw dataset images, labels, runtime logs, audit reports, model weights, or dataset archives. It does not train or evaluate models. Governance outputs remain `PENDING_AUDIT`.

## 中文

`V2.2_202606042006` 在内部版本顺序中紧接 `V2.1_202606041930`。它是一次面向高吞吐图源组复核的交互打磨版本。

### 主要更新

- 新包：`civl7009_picker_v2_2/`。
- 取消手动输入 `MOVE`，但保留安全门检查。
- 新增启动安全说明和自动移动准备状态。
- 只有目录锁、恢复扫描、快速索引、完整校核和事务日志检查全部通过后，才自动启用文件移动。
- 将左侧侧栏改为紧凑横向导航。
- 目录大盘表格支持随窗口宽度自适应。
- 图片卡片恢复 HKU 红色选中反馈。
- 收紧全局圆角，让复核工作区更紧凑。

### 本次包含

- `Dataset/Select_Programme/CIVL7009_source_group_picker_qt_V2.2_202606042006.py`
- `Dataset/Select_Programme/civl7009_picker_v2_2/`
- `Dataset/Select_Programme/test_source_group_picker_qt_V2.2_202606042006.py`
- `Dataset/Select_Programme/Executable/CIVL7009_Source_Group_Picker_V2.2_202606042006.exe`
- `Dataset/Select_Programme/Build_Spec/CIVL7009_Source_Group_Picker_V2.2_202606042006.spec`
- `Dataset/Select_Programme/Build_Reports/build_environment_V2.2_202606042006.json`
- `Dataset/Select_Programme/UI_Assets/V2.2_202606042006/`
- `Dataset/Select_Programme/README_V2.2_202606042006.md`

### 验证结果

```text
V2.2 Qt tests: 7/7 OK
V2.1 Qt regression: 5/5 OK
V1.9.1 Qt regression: 7/7 OK
V1.8.1 backend tests: 32 OK, skipped=1
source --help OK
source --smoke-open OK
exe --help OK
exe --smoke-open OK
zip extraction smoke OK
```

### 安全边界

发布包不包含原始数据集图片、标签、运行日志、审计报告、模型权重或数据集压缩包。它不训练或评估模型。治理输出保持 `PENDING_AUDIT`。

