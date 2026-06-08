# CIVL7009 Source Group Picker V3.0.3

## English Summary

V3.0.3 is a Manual Objects workflow hotfix for high-throughput review. It keeps the V3.0.2 on-demand image loading model and fixes the save-and-next behaviour so that a single click in single-keep mode can save the current `Gxxxxx` group and advance to the next unreviewed group inside the same `Reason / Nxx` bucket.

This version also adds live YOLO `.txt` bounding-box overlays to Manual Objects previews. The implementation follows the common LabelImg-style review idea of displaying annotation rectangles over image previews, but it uses a fresh lightweight parser and renderer in this codebase. No external LabelImg source code is vendored, copied, or bundled.

V3.0.3 still does not run hash scans, does not create `Manual_Objects`, does not move source-library files, and does not modify staged images or labels. Manual Objects mode writes only `manual_selection.json` and `_selection_history/` when the reviewer explicitly saves or uses click-to-save mode.

## 中文说明

V3.0.3 是面向 Manual Objects 人工复核流程的高吞吐热修复版本。它保留 V3.0.2 的按需图片加载逻辑，并修复“保存并进入下一组”的真实语义：在单保留模式下，点击当前 `Gxxxxx` 组中的某张候选图后，程序会保存本组选择，并自动进入同一个 `Reason / Nxx` 桶内的下一组未复核对象。

本版本新增 YOLO `.txt` 标签框实时叠加预览。实现思路参考 LabelImg 这类标注浏览器的交互目标，即在图片预览上显示标注矩形；但 V3.0.3 没有复制、嵌入或打包 LabelImg 代码，而是在本项目内重新实现了轻量 YOLO 标签解析与绘制逻辑。

V3.0.3 仍然不执行哈希或近哈希扫描，不创建 `Manual_Objects` 候选区，不移动主库文件，也不修改 staged images/labels。Manual Objects 模式只在保存人工选择时写入 `manual_selection.json` 和 `_selection_history/`。

## Key Fixes / 关键修复

- Click-to-save now works inside the current `Reason / Nxx` bucket.
- Selecting one image in single-keep mode writes the selection and advances to the next unreviewed `Gxxxxx` group in the same bucket.
- Turning auto-next off makes clicks preview-only until the reviewer saves manually.
- Multi-keep mode disables auto-next, because unresolved multi-item decisions should remain deliberate.
- Manual Objects thumbnails can draw YOLO `.txt` bounding boxes in real time.
- The bounding-box cache key includes image and label path, size, mtime, and overlay mode.
- Adds a `显示 txt BBox` checkbox.
- Preview loading remains asynchronous and scoped to the currently opened group.

## Safety Boundary / 安全边界

- Does not run hash or near-hash scanning.
- Does not create Manual Objects candidate folders.
- Does not move, delete, overwrite, or edit source-library images or labels.
- Does not edit staged images or labels.
- Does not create `_ManualReview_Staging`.
- Manual Objects mode writes only `manual_selection.json` and `_selection_history/`.
- Keeps all governance claims at `PENDING_AUDIT`.

## Test Result / 测试结果

- V3.0.3 tests: `11/11 OK`
- V3.0.2 regression: `9/9 OK`
- V2.2.4 regression: `10/10 OK`
- Source-run `--help`: OK
- Source-run `--smoke-open`: OK
- Packaged exe `--smoke-open`: OK
- Package and asset safety scan: no raw image, model weight, or dataset YAML files found in the V3.0.3 package or UI assets.
- `_ManualReview_Staging` scan: no directory found.

## Run / 运行

```powershell
uv run --with PySide6 --with Pillow python Dataset\Select_Programme\CIVL7009_source_group_picker_qt_V3.0.3_202606051705.py
```
