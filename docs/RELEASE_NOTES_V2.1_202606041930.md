# Release Notes: YOLO Transformed Dataset Cleaning Browser V2.1_202606041930

## English

`V2.1_202606041930` follows `V2.0_202606041906` in the internal release order. It rebuilds the PySide6 interaction layer while preserving the safety and transaction logic from the earlier stable line.

### Highlights

- New package: `civl7009_picker_v2_1/`.
- Restores practical review entry points: select an ID root or directly select a review folder.
- Replaces the earlier static V2 shell with a review-first cockpit.
- Uses horizontal workflow navigation to save screen width.
- Adds dynamic keypad-style image layout for group sizes 1 to 9+, with number-key shortcuts.
- Keeps Safe Gate preview behaviour, background move queue, undo, audit export, and red selection feedback.
- Adds V2.1 abstract image2/procedural UI assets and design tokens.

### Included Artefacts

- `Dataset/Select_Programme/CIVL7009_source_group_picker_qt_V2.1_202606041930.py`
- `Dataset/Select_Programme/civl7009_picker_v2_1/`
- `Dataset/Select_Programme/test_source_group_picker_qt_V2.1_202606041930.py`
- `Dataset/Select_Programme/Executable/CIVL7009_Source_Group_Picker_V2.1_202606041930.exe`
- `Dataset/Select_Programme/Build_Spec/CIVL7009_Source_Group_Picker_V2.1_202606041930.spec`
- `Dataset/Select_Programme/Build_Reports/build_environment_V2.1_202606041930.json`
- `Dataset/Select_Programme/UI_Assets/V2.1_202606041930/`
- `Dataset/Select_Programme/README_V2.1_202606041930.md`

### Verification

```text
V2.1 Qt tests: 5/5 OK
V1.9.1 Qt tests: 7/7 OK
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

`V2.1_202606041930` 在内部版本顺序中紧接 `V2.0_202606041906`。它重建 PySide6 交互层，同时保留早期稳定线的安全事务和文件移动逻辑。

### 主要更新

- 新包：`civl7009_picker_v2_1/`。
- 恢复实用目录入口：选择 ID 根目录，或直接选择筛选目录。
- 用复核优先的 cockpit 取代早期 V2 静态占位式 shell。
- 使用横向工作流导航，节约横向空间。
- 新增动态小键盘式图片布局，支持 1 到 9+ 图组和数字快捷键。
- 保留 Safe Gate 预览、后台移动队列、撤销、审计导出和红色选中反馈。
- 新增 V2.1 抽象 image2 / 程序化 UI 资产和设计令牌。

### 本次包含

- `Dataset/Select_Programme/CIVL7009_source_group_picker_qt_V2.1_202606041930.py`
- `Dataset/Select_Programme/civl7009_picker_v2_1/`
- `Dataset/Select_Programme/test_source_group_picker_qt_V2.1_202606041930.py`
- `Dataset/Select_Programme/Executable/CIVL7009_Source_Group_Picker_V2.1_202606041930.exe`
- `Dataset/Select_Programme/Build_Spec/CIVL7009_Source_Group_Picker_V2.1_202606041930.spec`
- `Dataset/Select_Programme/Build_Reports/build_environment_V2.1_202606041930.json`
- `Dataset/Select_Programme/UI_Assets/V2.1_202606041930/`
- `Dataset/Select_Programme/README_V2.1_202606041930.md`

### 验证结果

```text
V2.1 Qt tests: 5/5 OK
V1.9.1 Qt tests: 7/7 OK
V1.8.1 backend tests: 32 OK, skipped=1
source --help OK
source --smoke-open OK
exe --help OK
exe --smoke-open OK
zip extraction smoke OK
```

### 安全边界

发布包不包含原始数据集图片、标签、运行日志、审计报告、模型权重或数据集压缩包。它不训练或评估模型。治理输出保持 `PENDING_AUDIT`。

