# YOLO Transformed Dataset Cleaning Browser V3.0.2_202606051620

## English

V3.0.2 is a focused hotfix for Manual Objects image preview loading.

The application now opens a Manual Objects root by reading only the global index and group list. It does not start loading candidate images until the reviewer selects a concrete `Reason / Nxx / Gxxxxx` group. This keeps the opening path responsive and makes preview work observable through the right-side status pane.

### Highlights

- Preview loading is now on-demand rather than automatic at root open.
- Current-group thumbnails are decoded in background workers.
- A preview status pane reports completed, pending, failed counts, and error details.
- A manual refresh button reloads the current group's previews.
- Single-keep mode supports save-and-next within the same reason and N bucket.
- Multi-keep mode intentionally disables automatic next-group movement.
- Keeps V3 safety boundaries: no hash scanning, no candidate generation, no source-library movement, and no staged image or label modification.

### Validation

- V3.0.2 tests: `9/9 OK`
- V3.0.1 regression: `9/9 OK`
- V2.2.4 regression: `10/10 OK`
- Source-run `--help`: OK
- Source-run `--smoke-open`: OK
- Packaged exe `--smoke-open`: OK
- Release tree safety scan: clean.

## 中文

V3.0.2 是针对 Manual Objects 图片预览加载的热修复版本。

现在打开 Manual Objects 根目录时，程序只读取全局索引和候选组列表。只有人工选择具体 `Reason / Nxx / Gxxxxx` 组之后，才会开始加载候选图片。这样可以保持打开根目录的链路足够轻，并且通过右侧状态窗格让预览加载进度和错误可见。

### 更新重点

- 图片预览改为按需加载，不再在打开根目录时自动加载。
- 当前组缩略图由后台 worker 解码。
- 右侧预览状态窗格显示已完成、待加载、失败数量和错误说明。
- 新增手动刷新当前组预览按钮。
- 单保留模式支持在同 reason 和同 N bucket 内保存并进入下一组。
- 多保留模式禁用自动下一组，必须由人工手动切组或使用 `+ 保存并下一组`。
- 保持 V3 安全边界：不执行哈希扫描、不生成候选区、不移动主库文件、不修改候选图片或标签。

### 验证

- V3.0.2 测试：`9/9 OK`
- V3.0.1 回归：`9/9 OK`
- V2.2.4 回归：`10/10 OK`
- source-run `--help`: OK
- source-run `--smoke-open`: OK
- exe `--smoke-open`: OK
- 发布树安全扫描：干净。
