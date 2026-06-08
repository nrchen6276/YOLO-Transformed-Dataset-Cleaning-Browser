# CIVL7009 Source Group Picker V3.0 Release Note

## English Record

V3.0 adds a second human-review workflow on top of the V2.2.4 PySide6 application. The existing Source Group Review workflow remains available, while the new Manual Objects Review page reads `Manual_Objects/<REASON>/Nxx/Gxxxxxx/group_manifest.json`, displays cross-dataset candidate objects, and writes `manual_selection.json` for downstream governance agents.

This release does not run hash or near-hash scanning, does not create `Manual_Objects`, and does not move or delete source-library files. Manual Objects mode only reads candidate copies and writes the review-result file plus `_selection_history` backups.

Key features:

- Main workflow tabs: Source Group Review, Manual Objects Review, and Diagnostics / Settings.
- Manual Objects Review uses `group_manifest.json` as the authority for item metadata.
- Single-keep and multi-keep modes are supported.
- Review outcomes include `APPROVED`, `SKIP`, `AMBIGUOUS`, and `NEEDS_AGENT_CHECK`.
- Existing `manual_selection.json` files are backed up to `_selection_history` before replacement.
- Invalid manifests, missing fields, duplicated `item_id`, missing images or labels, and hash mismatches are shown as issues and block writes.
- V2.2.4 Source Group Review behaviour remains available, including non-standard `images/special` dynamic grouping.

Validation:

- V3.0 Qt tests: `6/6 OK`
- V2.2.4 Qt regression: `10/10 OK`
- V1.8.1 backend regression: `32 OK, 1 skipped`
- Source import and packaged executable checks: passed
- Clean-machine / copied-exe smoke was not part of this V3.0 iteration

All operational conclusions remain `PENDING_AUDIT`.

## 中文说明

V3.0 在 V2.2.4 的 PySide6 程序基础上新增第二套人工复核工作流。原有“图源组筛选（Source Group Review）”继续保留；新增“跨库候选复核（Manual Objects Review）”页面，用于读取 `Manual_Objects/<REASON>/Nxx/Gxxxxxx/group_manifest.json`，展示跨数据集候选对象，并写入后续治理流程可回读的 `manual_selection.json`。

本版不执行哈希或近哈希扫描，不创建 `Manual_Objects`，不移动或删除主库文件。Manual Objects 模式只读取候选副本，并只写入人工选择结果文件和 `_selection_history` 备份。

关键功能：

- 主工作流标签：图源组筛选、跨库候选复核、诊断与设置。
- Manual Objects Review 以 `group_manifest.json` 作为候选项元数据权威来源。
- 支持单保留模式和多保留模式。
- 复核结果包括 `APPROVED`、`SKIP`、`AMBIGUOUS`、`NEEDS_AGENT_CHECK`。
- 重新写入 `manual_selection.json` 前会把旧文件备份到 `_selection_history`。
- manifest 缺失、字段缺失、`item_id` 重复、图片/标签缺失、哈希不一致都会进入异常表并阻断写入。
- V2.2.4 的图源组筛选能力继续保留，包括非常规 `images/special` 动态分组。

验证记录：

- V3.0 Qt 测试：`6/6 OK`
- V2.2.4 Qt 回归：`10/10 OK`
- V1.8.1 后端回归：`32 OK, 1 skipped`
- source import 与已打包 exe 基础检查：通过
- clean-machine / copied-exe smoke 不属于本次 V3.0 验收范围

所有运行与治理结论仍保持 `PENDING_AUDIT`。
