# CIVL7009 Source Group Picker V2.1

## English

`PENDING_AUDIT` — operational tooling release note only.

V2.1 rebuilds the PySide6 manual review cockpit around the working V1.9.1 interaction flow while preserving V2 framework pages. The Review page now has explicit directory entry points, a real Review Board, quick-preview/full-index opening flow, dynamic image cards, numpad-style layout, Safe Gate-controlled file movement, optimistic next group, background move queue, undo, and audit export.

Main executable:

`D:/P/CIVL7009/Dataset/Select_Programme/Executable/CIVL7009_Source_Group_Picker_V2.1_202606041930.exe`

Key safety defaults:

- Safe Gate starts OFF on every launch.
- Safe Gate OFF means preview only; no move queue and no file movement.
- Safe Gate ON enables high-speed single-click / numeric-key commit.
- Physical staging remains disabled.
- image2 assets are abstract UI decoration only and contain no dataset-derived imagery.

Verification:

- V2.1 Qt tests: 5/5 OK
- V1.9.1 Qt regression: 7/7 OK
- V1.8.1 backend regression: 32 OK, 1 skipped
- source/exe help and smoke-open: OK
- exe normal start: remained running after 8 seconds
- Select_Programme raster file count: 0

## 中文

`PENDING_AUDIT` — 仅为操作性工具发布说明。

V2.1 重新构建了 PySide6 人工筛选驾驶舱：不再沿用 V2.0 的静态占位壳，而是把 V1.9.1 已经可用的真实交互链路迁回 V2 架构。现在 Review 页具备明确的目录选择入口、目录大盘、快速预览、完整索引、动态图片卡片、小键盘布局、Safe Gate 控制的文件移动、前台快速切组、后台移动队列、撤销和校核导出。

主程序 exe：

`D:/P/CIVL7009/Dataset/Select_Programme/Executable/CIVL7009_Source_Group_Picker_V2.1_202606041930.exe`

安全默认值：

- Safe Gate 每次启动默认关闭。
- Safe Gate OFF 时只做预览，不入队、不移动文件。
- Safe Gate ON 后启用高速单击 / 数字键提交。
- Physical staging 仍保持关闭。
- image2 资产只用于抽象 UI 装饰，不含任何数据集派生图像。

验证：

- V2.1 Qt 测试：5/5 OK
- V1.9.1 Qt 回归：7/7 OK
- V1.8.1 后端回归：32 OK，1 skipped
- source/exe help 与 smoke-open：通过
- exe 正常启动：8 秒后仍保持运行
- Select_Programme raster 文件数：0
