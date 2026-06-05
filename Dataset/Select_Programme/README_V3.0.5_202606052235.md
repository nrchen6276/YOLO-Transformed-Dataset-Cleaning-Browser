# CIVL7009 Source Group Picker V3.0.5

## English Summary

V3.0.5 improves the Manual Objects image review stage. It fixes the oversized empty preview area by making each candidate image scale to the available card preview area rather than being capped by the previous small thumbnail size. The preview widget now stores the decoded image and rescales it with `KeepAspectRatio` whenever the card area changes.

The version also improves YOLO `.txt` bounding-box visibility. Bounding-box labels now use larger text, thicker outlines, and a larger label background. If `Manual_Objects/ID_Classes/<dataset_id>/` contains a valid class `.txt`, the bbox label uses the mapped class name instead of only showing `class 0`.

An additional label row is shown directly under each image filename:

```text
标签：person (0)、knife (1)
```

This row is derived from the current item's `label_class_set` and the loaded per-ID class map.

## 中文说明

V3.0.5 优化 Manual Objects 的图片区显示。此前卡片区域很大，但图片仍受旧的 430×250 缩略图限制，导致图片只在卡片中央显示一小块。本版改为可缩放预览控件：图片会根据当前卡片预览区的宽高自动等比放大，尽可能利用工作区空间，同时保留下方文件名、类别、尺寸和 metrics 区域。

本版也增强了 YOLO `.txt` 标注框的可读性：bbox 线条更粗，标签底色更大，标签文字字号更大。如果 `Manual_Objects/ID_Classes/<dataset_id>/` 下存在有效类别 `.txt`，bbox 标签会显示类别名，而不是只显示 `class 0`。

每张候选图的文件名下方新增一行当前图片涉及的标签类别，例如：

```text
标签：person (0)、knife (1)
```

这一行来自当前 item 的 `label_class_set`，并自动对应到已加载的 ID 类别文件。

## Key Fixes

- Manual Object image previews now scale to the available card preview area.
- Thumbnail workers now generate larger preview payloads by default (`1280×960`) to avoid tiny previews in large cards.
- Preview widgets rescale stored image data on resize, preserving aspect ratio.
- Detail rows are height-limited so that the image area gets most of the card height.
- bbox labels use larger fonts and thicker outlines.
- bbox labels prefer Windows UI fonts that can display Chinese class names.
- A new `标签：...` row shows mapped class names for the current image.

## 关键修复

- Manual Objects 图片预览会根据卡片图片区自动放大。
- 缩略图 worker 默认生成更大的预览 payload（`1280×960`），避免大卡片里显示小图。
- 预览控件在尺寸变化时自动等比重绘图片。
- 下方详情行限制高度，把更多空间留给图片区。
- bbox 标签字体更大、边框更粗。
- bbox 标签优先使用 Windows UI 字体，尽量支持中文类别名。
- 新增 `标签：...` 行，显示当前图片映射后的类别名。

## Safety Boundary

- No hash or near-hash scan is executed.
- No Manual Objects candidate folder is created.
- No source-library image or label is moved, deleted, overwritten, or edited.
- No staged image or label is edited.
- No `_ManualReview_Staging` directory is created.
- Manual Objects mode writes only `manual_selection.json`, `_selection_history/`, and user-provided class files in `ID_Classes/`.
- All governance outputs remain `PENDING_AUDIT`.

## 安全边界

- 不执行哈希或近哈希扫描。
- 不创建 Manual Objects 候选区。
- 不移动、不删除、不覆盖、不编辑主库图片或标签。
- 不编辑 staged image 或 staged label。
- 不创建 `_ManualReview_Staging`。
- Manual Objects 模式只写 `manual_selection.json`、`_selection_history/`，以及用户自行放入 `ID_Classes/` 的类别文件。
- 所有治理结论保持 `PENDING_AUDIT`。

## Test Result

- V3.0.5 tests: `14/14 OK`
- V3.0.4 regression: `13/13 OK`
- V2.2.4 regression: `10/10 OK`
- Source-run `--help`: OK
- Source-run `--smoke-open`: OK
- exe `--smoke-open`: OK
- Package and asset safety scan: no raw image/model/YAML files found in the V3.0.5 package or UI assets.
- `_ManualReview_Staging` scan: no directory found.

## Run

```powershell
uv run --with PySide6 --with Pillow python Dataset\Select_Programme\CIVL7009_source_group_picker_qt_V3.0.5_202606052235.py
```

## Executable

```text
Dataset/Select_Programme/Executable/CIVL7009_Source_Group_Picker_V3.0.5_202606052235.exe
SHA256: 4C3C68454A52E0F4A619EF946CE11A6CAD2060AB1FE7CE3DB088E5F0955CCC37
Size: 73,052,856 bytes
```
