# CIVL7009 Source Group Picker V3.0.2

## English Summary

V3.0.2 is a Manual Objects preview hotfix. It keeps the V3.0.1 fast index workflow but changes image loading into an explicit, observable, on-demand process.

Opening `Manual_Objects` now loads only the global index and group list. The application does not load candidate previews until the reviewer selects a concrete `Reason / Nxx / Gxxxxx` group. Preview loading runs in background workers, reports progress in the right-side status pane, and logs thumbnail start, completion, and error events for later diagnosis.

## 中文说明

V3.0.2 是 Manual Objects 图片预览热修复版本。它保留 V3.0.1 的全局 index 快速大盘，但把图片预览改为显式、可观察、按需加载的流程。

打开 `Manual_Objects` 根目录时，软件只读取全局索引和候选组列表。只有用户点击具体的 `Reason / Nxx / Gxxxxx` 组之后，才会加载该组的 manifest 和图片预览。预览加载由后台 worker 执行，进度和错误会显示在右侧状态窗格，并写入缩略图加载日志事件。

## Key Fixes / 关键修复

- Root opening no longer auto-loads the first group images.
- Preview loading starts only after a concrete group has been selected.
- Current-group thumbnails are decoded in background workers.
- Active worker references are retained to avoid premature Python garbage collection.
- The right-side preview status pane shows completed, pending, failed counts, and error details.
- Adds a `Refresh current group preview` action.
- Adds thumbnail diagnostic events: `manual_thumbnail_start`, `manual_thumbnail_done`, `manual_thumbnail_error`, and `manual_thumbnail_refresh_requested`.
- Single-keep mode can save and move to the next unreviewed group in the same reason and N bucket.
- Multi-keep mode disables automatic next-group movement; reviewers must manually go next or use `+ Save and Next`.
- Keyboard `+` is bound to approved save-and-next.

## Safety Boundary / 安全边界

- Does not run hash or near-hash scanning.
- Does not create candidate folders.
- Does not move, delete, or overwrite source-library files.
- Does not modify staged images or labels.
- Does not create `_ManualReview_Staging`.
- Manual Objects mode writes only `manual_selection.json` and `_selection_history/`.
- Keeps all governance claims at `PENDING_AUDIT`.

## Verified Results / 已验证结果

- V3.0.2 tests: `9/9 OK`
- V3.0.1 regression: `9/9 OK`
- V2.2.4 regression: `10/10 OK`
- Source-run `--help`: OK
- Source-run `--smoke-open`: OK
- Packaged exe `--smoke-open`: OK
- Safety scan: no raw image, model weight, or dataset YAML files in the release tree.

## Run / 运行

```powershell
uv run --with PySide6 --with Pillow python Dataset\Select_Programme\CIVL7009_source_group_picker_qt_V3.0.2_202606051620.py
```
