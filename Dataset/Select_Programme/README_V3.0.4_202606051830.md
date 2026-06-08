# CIVL7009 Source Group Picker V3.0.4

## English Summary

V3.0.4 extends the Manual Objects review workflow with per-dataset class-name support for YOLO `.txt` bounding-box overlays. When a `Manual_Objects` root is opened, the application detects the dataset IDs involved in the global index and automatically creates:

```text
Manual_Objects/
  ID_Classes/
    ID01/
    ID09/
    ...
```

Each ID folder may contain any non-empty `.txt` class file. The file does not need to be named `classes.txt`. The first valid `.txt` file in filename order is used as the class list for that ID. Bounding boxes still work if a class file is missing, but the label falls back to `class 0`, `class 1`, and so on.

V3.0.4 keeps the V3.0.3 high-throughput Manual Objects workflow: click-to-save can still advance within the same `Reason / Nxx` bucket, preview loading remains asynchronous and on-demand, and Manual Objects mode still writes only `manual_selection.json` and `_selection_history/` unless the user places class files under `ID_Classes/`.

## 中文说明

V3.0.4 为 Manual Objects 人工复核流程新增“按数据集 ID 读取类别文件，并用于 YOLO `.txt` 标注框显示”的能力。打开 `Manual_Objects` 根目录后，程序会根据全局 index 中涉及的 `dataset_id` 自动创建：

```text
Manual_Objects/
  ID_Classes/
    ID01/
    ID09/
    ...
```

每个 ID 文件夹内可以放入任意非空 `.txt` 类别文件，文件名不限定，不必叫 `classes.txt`。程序按文件名排序读取第一个有效 `.txt` 作为该 ID 的类别表。若类别文件缺失，BBox 仍可显示，但标签会回退为 `class 0`、`class 1` 等原始编号。

V3.0.4 保留 V3.0.3 的高吞吐 Manual Objects 工作流：单保留模式下点击保存可进入同一 `Reason / Nxx` 的下一组；图片预览仍然异步、按当前组加载；Manual Objects 模式仍只写 `manual_selection.json` 和 `_selection_history/`，除非用户自行把类别文件放入 `ID_Classes/`。

## New Capability / 新增能力

- Auto-detect dataset IDs used by `Manual_Objects`.
- Auto-create `Manual_Objects/ID_Classes/<dataset_id>/`.
- Accept any non-empty `.txt` filename as the class list.
- Detect `MISSING`, `EMPTY`, `MULTIPLE`, and `OK` class-file states.
- Provide a class-file status dialog with open-folder and refresh actions.
- Render BBox labels with per-ID class names when available.
- Invalidate thumbnail cache when class maps change.

## Safety Boundary / 安全边界

- Does not run hash or near-hash scanning.
- Does not create Manual Objects candidate folders.
- Does not move, delete, overwrite, or edit source-library images or labels.
- Does not edit staged images or labels.
- Does not create `_ManualReview_Staging`.
- The only newly created Manual Objects support folders are `ID_Classes/<dataset_id>/`.
- Manual Objects mode writes only `manual_selection.json`, `_selection_history/`, and user-provided class files in `ID_Classes/`.
- Keeps all governance claims at `PENDING_AUDIT`.

## Test Result / 测试结果

- V3.0.4 tests: `13/13 OK`
- V3.0.3 regression: `11/11 OK`
- V2.2.4 regression: `10/10 OK`
- Source-run `--help`: OK
- Source-run `--smoke-open`: OK
- Packaged exe `--smoke-open`: OK
- Package and asset safety scan: no raw image, model weight, or dataset YAML files found in the V3.0.4 package or UI assets.
- `_ManualReview_Staging` scan: no directory found.

## Run / 运行

```powershell
uv run --with PySide6 --with Pillow python Dataset\Select_Programme\CIVL7009_source_group_picker_qt_V3.0.4_202606051830.py
```
