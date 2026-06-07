# CIVL7009 Source Group Picker V2.2.2 Hotfix Note

## English Record

V2.2.2 is an interaction hotfix over V2.2.1. It keeps the standalone executable bundled-core fix and the V2.2 automatic move workflow, while addressing three user-facing issues.

Changes:

- Undo now refreshes the current review directory in place. After undoing the last successful transaction, the UI rebuilds the fast index and audit state for the current review directory, keeps that directory open, and tries to jump back to the restored prefix.
- Image selection feedback now uses stable Qt dynamic properties. Selected image cards use HKU Academic Red `#EF4022`, with a 3px card border, thumbnail outline, and `已选图源预览` status chip.
- The bottom Move Queue / Recent Events region is now resizable. The Review page uses a vertical splitter for top-vs-bottom height, and the bottom region uses a horizontal splitter for queue-vs-events width.

Validation:

- V2.2.2 Qt tests: `8/8 OK`
- V2.2.1 Qt regression: `8/8 OK`
- V2.1 Qt regression: `5/5 OK`
- V1.9.1 Qt regression: `7/7 OK`
- V1.8.1 backend regression: `32 OK, 1 skipped`
- Executable smoke and standalone copied-exe smoke: passed
- `Dataset/Select_Programme` raster file count: `0`

Executable:

- `D:/P/CIVL7009/Dataset/Select_Programme/Executable/CIVL7009_Source_Group_Picker_V2.2.2_202606042205.exe`

All operational conclusions remain `PENDING_AUDIT`.

## 中文说明

V2.2.2 是基于 V2.2.1 的交互热修复版本。它保留单文件 exe 内置 core 修复和 V2.2 自动移动工作流，同时修复三处影响人工筛选体验的问题。

更新内容：

- 点击“撤销上一组”后不再退出当前筛选目录。撤销成功后，程序会在当前目录中原地重建快速索引和校核状态，并尽量跳回刚撤销的 prefix。
- 图片选中高亮改为稳定的 Qt 动态属性。被选中的图片卡片会显示 HKU 红色 `#EF4022` 边框、缩略图红色描边和 `已选图源预览` 状态 chip。
- 底部任务队列与 Recent Events 区域改为可拖动：上下高度可调，底部左右宽度也可调。

本版没有创建 `_ManualReview_Staging`，也没有把 raw dataset images/labels 写入 `Dataset/Select_Programme`。
