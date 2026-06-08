# CIVL7009 Source Group Picker V2.2.3 Hotfix Note

## English Record

V2.2.3 is a UI status-routing and top-bar compaction hotfix over V2.2.2. It keeps V2.2.2's in-place undo refresh, red image-card selection feedback, draggable bottom panel, and standalone executable bundled-core behaviour.

Changes:

- Undo refresh progress no longer opens the large image-stage overlay. It now appears in the right-side status chip on the horizontal navigation row.
- The navigation row now has a `nav_status_chip` for short operational states such as `撤销完成：当前目录已刷新` and `FastReviewIndex 已完成`.
- The Safe Gate badge is now single-line Chinese text: `文件移动已启用`, `自动移动准备中`, or `只读预览`.
- The Command Bar is more compact: smaller default font, tighter button padding, and long context paths elided with full tooltip text.

Validation:

- V2.2.3 Qt tests: `9/9 OK`
- V2.2.2 Qt regression: `8/8 OK`
- V2.2.1 Qt regression: `8/8 OK`
- V2.1 Qt regression: `5/5 OK`
- V1.9.1 Qt regression: `7/7 OK`
- V1.8.1 backend regression: `32 OK, 1 skipped`
- Executable smoke and standalone copied-exe smoke: passed
- `Dataset/Select_Programme` raster file count: `0`

Executable:

- `D:/P/CIVL7009/Dataset/Select_Programme/Executable/CIVL7009_Source_Group_Picker_V2.2.3_202606042231.exe`

All operational conclusions remain `PENDING_AUDIT`.

## 中文说明

V2.2.3 是基于 V2.2.2 的 UI 状态提示与顶栏压缩热修复。它保留 V2.2.2 的撤销原地刷新、红色选中反馈、底部可拖动面板和单文件 exe 内置 core 能力。

更新内容：

- 撤销刷新不再弹出图片区的大 overlay，而是显示在横向导航栏右侧的小状态 chip。
- 横向导航行新增 `nav_status_chip`，用于显示 `撤销完成：当前目录已刷新`、`FastReviewIndex 已完成` 等短状态。
- Safe Gate 状态 badge 改为中文单行：`文件移动已启用`、`自动移动准备中` 或 `只读预览`，避免换行撑高顶栏。
- Command Bar 默认字号和按钮 padding 收紧；右侧长路径文本自动省略，完整路径保留在 tooltip。

本版不修改文件移动事务语义，不创建 `_ManualReview_Staging`，也没有把 raw dataset images/labels 写入 `Dataset/Select_Programme`。
