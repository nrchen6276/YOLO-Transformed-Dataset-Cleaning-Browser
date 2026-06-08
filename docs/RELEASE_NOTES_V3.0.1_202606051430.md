# YOLO Transformed Dataset Cleaning Browser V3.0.1_202606051430

## English

V3.0.1 is the first performance hotfix for the V3 Manual Objects Review workflow.

The previous V3.0 release introduced the Manual Objects Review page. V3.0.1 makes that workflow practical for the landed Step08A06 candidate area by using the global `_indexes/manual_objects_index.csv` as the fast entry point and by loading each `group_manifest.json` only when a reviewer opens the corresponding group.

### Highlights

- Fast Manual Objects index loading from `_indexes/manual_objects_index.csv`.
- Lazy group manifest loading for the current group only.
- Paginated and filtered group board for large candidate sets.
- Background prefetch for nearby groups and thumbnails.
- Save-and-next support for higher-throughput human review.
- Preserves V3.0 safety boundaries: no hash scanning, no candidate generation, no source-library movement, and no staged image or label modification.

### Validation

- V3.0.1 tests: `9/9 OK`
- V3.0 regression: `6/6 OK`
- V2.2.4 regression: `10/10 OK`
- V1.8.1 backend regression: `32 OK, 1 skipped`
- Real Manual Objects read-only check: `43,563` groups and `135,349` rows loaded through the index path.

### Safety

This release is still a review-result writer. Manual Objects mode writes `manual_selection.json` and `_selection_history/` only. It does not move source-library files, does not create candidates, and does not delete staged copies.

All governance outputs remain `PENDING_AUDIT`.

## 中文

V3.0.1 是 V3 Manual Objects 复核工作流的第一个性能热修复版本。

上一版 V3.0 引入了跨库候选复核页面。V3.0.1 进一步让它适配已经落地的 Step08A06 候选区：程序优先读取全局 `_indexes/manual_objects_index.csv` 作为快速入口，只有当人工打开某一组时，才读取该组的 `group_manifest.json`。

### 更新重点

- 通过 `_indexes/manual_objects_index.csv` 快速加载 Manual Objects 大盘。
- 只对当前组懒加载 `group_manifest.json`。
- 为大规模候选集提供分页与筛选。
- 后台预取邻近组与缩略图。
- 支持保存并进入下一组，提高人工复核吞吐。
- 保持 V3.0 安全边界：不执行哈希扫描、不生成候选区、不移动主库文件、不修改候选图片或标签。

### 验证

- V3.0.1 测试：`9/9 OK`
- V3.0 回归：`6/6 OK`
- V2.2.4 回归：`10/10 OK`
- V1.8.1 后端回归：`32 OK, 1 skipped`
- 真实 Manual Objects 只读检查：通过 index 路径读取 `43,563` 个组和 `135,349` 行。

### 安全边界

本版本仍是人工复核结果写入工具。Manual Objects 模式只写 `manual_selection.json` 和 `_selection_history/`。它不移动主库文件，不创建候选组，也不删除候选副本。

所有治理输出继续保持 `PENDING_AUDIT`。
