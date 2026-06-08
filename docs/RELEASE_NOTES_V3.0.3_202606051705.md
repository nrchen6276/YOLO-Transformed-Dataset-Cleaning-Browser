# YOLO Transformed Dataset Cleaning Browser V3.0.3_202606051705

## English

V3.0.3 is a Manual Objects review hotfix for the click-to-save workflow and YOLO `.txt` bounding-box previews.

It fixes save-and-next semantics inside the current `Reason / Nxx` bucket. In single-keep mode, selecting one candidate can save the current group and advance to the next unreviewed `Gxxxxx` group in the same bucket. It also adds live YOLO annotation overlays to candidate previews without vendoring or bundling LabelImg source code.

### Highlights

- Correct click-to-save and next-group behaviour within the active `Reason / Nxx` bucket.
- Optional YOLO `.txt` bounding-box overlays on Manual Objects image cards.
- A fresh lightweight YOLO label parser and renderer in this codebase.
- BBox cache invalidation based on image path, image metadata, label path, label metadata, and overlay mode.
- Multi-keep mode disables automatic next-group movement to keep complex decisions deliberate.
- Keeps V3 safety boundaries: no hash scanning, no candidate generation, no source-library movement, and no staged image or label modification.

### Validation

- V3.0.3 tests: `11/11 OK`
- V3.0.2 regression: `9/9 OK`
- V2.2.4 regression: `10/10 OK`
- Source-run `--help`: OK
- Source-run `--smoke-open`: OK
- Packaged exe `--smoke-open`: OK
- Package and asset safety scan: clean.

## 中文

V3.0.3 是针对 Manual Objects 复核链路的热修复版本，重点修复点击保存并进入下一组的行为，并新增 YOLO `.txt` 标注框预览。

本版修复同一个 `Reason / Nxx` 桶内的保存并下一组语义。在单保留模式下，选择某个候选项后可以保存当前组，并进入同一桶内下一组未复核 `Gxxxxx`。同时，本版在候选图片预览中加入 YOLO 标注框叠加显示；该功能由本项目内轻量解析与绘制逻辑实现，没有复制、嵌入或打包 LabelImg 源码。

### 更新重点

- 修复当前 `Reason / Nxx` 桶内点击保存并进入下一组的行为。
- 在 Manual Objects 图片卡片上可选显示 YOLO `.txt` BBox。
- 在本项目内重新实现轻量 YOLO 标签解析和绘制逻辑。
- BBox 缓存会根据图片路径、图片元数据、标签路径、标签元数据和显示模式失效。
- 多保留模式禁用自动下一组，避免复杂决策被误提交。
- 保持 V3 安全边界：不执行哈希扫描、不生成候选区、不移动主库文件、不修改候选图片或标签。

### 验证

- V3.0.3 测试：`11/11 OK`
- V3.0.2 回归：`9/9 OK`
- V2.2.4 回归：`10/10 OK`
- source-run `--help`: OK
- source-run `--smoke-open`: OK
- exe `--smoke-open`: OK
- 包与 UI asset 安全扫描：干净。
