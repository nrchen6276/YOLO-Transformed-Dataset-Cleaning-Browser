# CIVL7009 Source Group Picker V2.2.4 Hotfix Note

## English Record

V2.2.4 is a compatibility hotfix over V2.2.3. It keeps the V2.2.3 compact UI status handling while switching the Qt shell to the V1.8.2 core line for dynamic, non-standard review folders.

Changes:

- The Qt package now targets `CIVL7009_source_group_picker_gui_V1.8.2_202606042313.py` as its core.
- Non-standard review folders such as `images/special` can be opened when the paired labels folder exists.
- Mixed group-size directories can prepare transactions, including 2-image groups and 3-image groups in the same review directory.
- Existing behaviours remain: automatic move readiness, red selected-card feedback, compact nav status chip, in-place undo refresh, and draggable bottom panels.

Validation:

- V2.2.4 Qt tests: `10/10 OK`
- V2.2.3 Qt regression: `9/9 OK`
- V2.2.2 Qt regression: `8/8 OK`
- V2.2.1 Qt regression: `8/8 OK`
- V2.1 Qt regression: `5/5 OK`
- V1.9.1 Qt regression: `7/7 OK`
- V1.8.1 backend regression: `32 OK, 1 skipped`
- Executable smoke and standalone copied-exe smoke: passed
- `Dataset/Select_Programme` raw dataset raster file count: `0`

Executable:

- `D:/P/CIVL7009/Dataset/Select_Programme/Executable/CIVL7009_Source_Group_Picker_V2.2.4_202606042313.exe`

All operational conclusions remain `PENDING_AUDIT`.

## 中文说明

V2.2.4 是基于 V2.2.3 的兼容性热修复。它保留 V2.2.3 的紧凑 UI 状态显示，同时把 Qt 前端切换到 V1.8.2 core，用于支持动态分组和非常规筛选目录。

更新内容：

- Qt 包现在使用 `CIVL7009_source_group_picker_gui_V1.8.2_202606042313.py` 作为 core。
- 支持 `images/special` 这类非常规筛选目录，只要存在对应的 labels 目录。
- 支持同一目录内混合 2 图组、3 图组等不同组大小，并能准备移动事务。
- 保留自动移动准备、红色选中反馈、导航行状态 chip、撤销原地刷新和底部可拖动面板。

本版不创建 `_ManualReview_Staging`，也没有把 raw dataset images/labels 写入 `Dataset/Select_Programme`。
