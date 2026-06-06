# CIVL7009 Source Group Picker V5.2

## English Overview

V5.2 is a Manual Objects Review hotfix for large `N20_PLUS` candidate groups. Earlier builds created preview cards for only the first 30 candidates and left the remaining items hidden in the manifest. V5.2 renders every candidate item in the scrollable review stage and loads thumbnails asynchronously in bounded batches.

Key changes:

- `N20_PLUS` groups now create cards for all items in `group_manifest.json`.
- The centre image stage remains scrollable, so reviewers can inspect every candidate in a large group.
- Thumbnail decoding is batched to avoid saturating the UI thread, thread pool, or disk reads.
- The preview status panel now reports completed, running, queued, and failed thumbnails.
- Manual refresh clears thumbnail cache for the whole current group, not only the first 30 items.

Safety notes:

- V5.2 does not change staged images, labels, source files, or governance outputs.
- Manual Objects mode still writes only `manual_selection.json` and `_selection_history` when the reviewer explicitly saves a selection.
- All governance conclusions remain `PENDING_AUDIT`.

## 中文说明

V5.2 是针对跨库候选复核（Manual Objects Review）里 `N20_PLUS` 大组显示问题的热修复。旧版本只为前 30 张候选创建预览卡片，其余候选虽然保留在 `group_manifest.json` 中，但不能直接滚动查看。V5.2 改为在图片区生成全部候选卡片，并通过分批异步缩略图加载保持界面可响应。

主要变化：

- `N20_PLUS` 大组会显示 manifest 内全部候选图片。
- 中央图片工作区可滚动查看完整大组，不再硬截断前 30 张。
- 缩略图按小批量后台加载，避免一次性压满 UI、线程池或磁盘读取。
- 预览状态面板显示已完成、进行中、排队和失败数量。
- “刷新当前组预览”会刷新当前组全部候选的缩略图缓存。

安全边界：

- V5.2 不修改候选图片、标签、主库源文件或治理扫描产物。
- 跨库候选复核模式仍只在人工保存选择时写入 `manual_selection.json` 与 `_selection_history`。
- 所有治理结论继续保持 `PENDING_AUDIT`。

## Verification / 验证

```powershell
uv run --with PySide6 --with pillow python Dataset\Select_Programme\test_source_group_picker_qt_V5.2_202606061825.py
```

Expected result:

```text
All tests pass, including the N20_PLUS all-item render test.
```
