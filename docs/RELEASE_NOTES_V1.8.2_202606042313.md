# Release Notes: YOLO Transformed Dataset Cleaning Browser V1.8.2_202606042313

## English

`V1.8.2_202606042313` is published to keep the public GitHub release sequence aligned with the internal programme sequence. It follows `V1.8.1_202606041443` exactly.

This release is a source-only core compatibility release. The internal artefact set contains the versioned V1.8.2 core source file, but no same-version standalone executable, PyInstaller spec, or dedicated V1.8.2 test file. The release asset therefore packages the core source and release metadata only.

### Included

- `Dataset/Select_Programme/CIVL7009_source_group_picker_gui_V1.8.2_202606042313.py`
- Build report and release manifest.
- Bilingual README files.
- SHA256 record for the release zip.

### Continued Capabilities

- Source-group review and dynamic `.rf.` prefix grouping.
- Fast in-memory review indexing (`FastReviewIndex`).
- Quick preview and current-group transaction preparation.
- Transaction journals, recovery snapshots, review locks, background move queue, rollback-on-failure, and undo.
- Audit export and `--audit-only` CLI support.

### Verification

Release verification was intentionally conservative and source-only:

```text
source --help OK
V1.8.1 regression replay against V1.8.2 core: 30 OK, 2 errors, skipped=1
```

Known issue:

- The two replayed regression errors are both in YOLO initialisation helper tests.
- Root cause: `audit_yolo_dataset()` references an undefined `group_size` variable in the original V1.8.2 source.
- Source-group review, transaction, lock, undo, fast-index, and audit-path tests passed.

### Safety Boundary

The release package does not include raw dataset images, labels, runtime logs, audit reports, model weights, or dataset archives. It does not train or evaluate models. All governance outputs remain `PENDING_AUDIT`.

## 中文

`V1.8.2_202606042313` 用于保持 GitHub 公开发版顺序与内部程序版本顺序一致，严格接在 `V1.8.1_202606041443` 之后。

本版本是仅包含源代码核心的兼容版本。内部产物集中存在 V1.8.2 核心源文件，但没有同版本独立 exe、PyInstaller spec 或专用 V1.8.2 测试文件。因此本次 release asset 只打包核心源代码和发布元数据。

### 本次包含

- `Dataset/Select_Programme/CIVL7009_source_group_picker_gui_V1.8.2_202606042313.py`
- 构建报告与发布 manifest。
- 中英双语 README。
- release zip 的 SHA256 记录。

### 继承能力

- 图源组复核与动态 `.rf.` prefix 分组。
- 快速内存复核索引（FastReviewIndex）。
- 快速预览和当前组事务准备。
- 事务日志、恢复快照、目录锁、后台移动队列、失败回滚和撤销。
- 审计报告导出和 `--audit-only` 命令行支持。

### 验证情况

本次发布按 source-only 方式保守验证：

```text
source --help OK
V1.8.1 回归测试套件复放到 V1.8.2 核心：30 OK, 2 errors, skipped=1
```

已知问题：

- 两个回归错误均来自 YOLO 初始化辅助函数测试。
- 根因是原始 V1.8.2 源文件中的 `audit_yolo_dataset()` 引用了未定义的 `group_size` 变量。
- 图源组复核、事务、目录锁、撤销、快速索引和审计路径相关测试均通过。

### 安全边界

发布包不包含原始数据集图片、标签、运行日志、审计报告、模型权重或数据集压缩包。本工具不训练或评估模型。所有治理输出保持 `PENDING_AUDIT`。
