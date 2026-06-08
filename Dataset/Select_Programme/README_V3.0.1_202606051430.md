# CIVL7009 Source Group Picker V3.0.1

## English Summary

V3.0.1 is a performance-focused update for the Manual Objects review workflow. It keeps the existing source-group review workflow and adds a fast browser for the landed Step08A06 `Manual_Objects` delivery: `43,563` candidate groups and `135,349` staged image-label pairs in the current CIVL7009 data-governance context.

The important change is that opening `Manual_Objects` no longer parses every `group_manifest.json`. The application first reads `_indexes/manual_objects_index.csv` to build a fast review board, then lazily loads the current group's `group_manifest.json` only when the reviewer opens that group.

This release does not run hash or near-hash scanning, does not create candidate folders, does not move source-library files, and does not modify staged images or labels. Manual Objects mode only writes `manual_selection.json` and `_selection_history/`.

## 中文说明

V3.0.1 是针对 Manual Objects 复核工作流的性能热修复版本。它保留原有图源组筛选（Source Group Review），并针对已经落地的 Step08A06 `Manual_Objects` 交付物加入高速浏览能力：在当前 CIVL7009 数据治理语境中，真实规模为 `43,563` 个候选组和 `135,349` 个 staged image-label pairs。

核心变化是：打开 `Manual_Objects` 根目录时不再逐组解析所有 `group_manifest.json`。程序优先读取 `_indexes/manual_objects_index.csv` 生成快速大盘；只有打开某一组时，才懒加载该组的 `group_manifest.json`。

本版本不执行哈希或近哈希扫描，不创建候选区，不移动主库文件，也不修改 staged images/labels。Manual Objects 模式只写入 `manual_selection.json` 和 `_selection_history/`。

## Key Features / 关键功能

- Global index review board from `manual_objects_index.csv`.
- Current-group lazy loading from `group_manifest.json`.
- Pagination and filters for reason, N bucket, review status, dataset ID, label class, copy status, and selection status.
- Background prefetch for the next groups and thumbnails.
- Save-and-next workflow for high-throughput review.
- Large-group protection: `N20_PLUS` groups avoid freezing the main UI.
- Preserved source-group review capability: dynamic folder grouping, automatic move mode, undo, keypad layout, red selection feedback, and non-standard `images/special` support.

## Safety Boundary / 安全边界

- Does not generate Step08A06 candidates.
- Does not scan SHA256, pHash, or dHash.
- Does not move, delete, or overwrite `Dataset/Source_Archive/<ID>` source-library files.
- Does not modify staged images or labels.
- Does not create `_ManualReview_Staging`.
- Writes only `manual_selection.json` and `_selection_history/`.
- Keeps all governance claims at `PENDING_AUDIT`.

## Verified Results / 已验证结果

- V3.0.1 tests: `9/9 OK`
- V3.0 regression: `6/6 OK`
- V2.2.4 regression: `10/10 OK`
- V1.8.1 backend regression: `32 OK, 1 skipped`
- Real Manual Objects read-only check:
  - groups: `43,563`
  - rows: `135,349`
  - index load: about `1.8s` on the current machine
  - example `SHA256_EXACT_IMAGE/N02/G000001`: `2` items, label class difference loaded successfully

## Run / 运行

```powershell
uv run --with PySide6 --with Pillow python Dataset\Select_Programme\CIVL7009_source_group_picker_qt_V3.0.1_202606051430.py
```

## Package / 打包

```powershell
uv run --with PySide6 --with Pillow --with pyinstaller pyinstaller --noconfirm Dataset\Select_Programme\Build_Spec\CIVL7009_Source_Group_Picker_V3.0.1_202606051430.spec
```
