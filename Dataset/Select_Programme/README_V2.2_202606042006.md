# CIVL7009 Source Group Picker V2.2 Build Note

Status: `PENDING_AUDIT`

## English

This V2.2 build is a targeted interaction upgrade over V2.1. It keeps the V2.1 review workflow, FastReviewIndex-backed preparation path, background move queue, undo, export flow, numeric-keypad image layout, and abstract image2 asset policy.

Key changes:

- Typed `MOVE` confirmation is removed.
- The application shows a Chinese safety explanation at startup, arms automatic move readiness after acknowledgement, and automatically enables file moves only after the review lock, recovery scan, FastReviewIndex, full audit, and transaction-log write checks pass.
- The left vertical navigation is removed. Navigation is now a compact horizontal card row below the command bar.
- The Review Board table resizes with the main window; directory names receive priority width.
- Image selection feedback is restored with HKU Academic Red `#EF4022`.
- Visual density is tightened with smaller global radii: panels/cards use `12px`; buttons, chips, tables, and text panels use `8px`.

## 中文

V2.2 是基于 V2.1 的交互优化版本。它保留 V2.1 的复核流程、快速索引（FastReviewIndex）准备链路、后台移动队列、撤销、导出、小键盘图片区布局和抽象 image2 资产策略。

关键变化：

- 取消手动输入 `MOVE`。
- 程序启动后显示中文安全说明，确认后进入自动移动准备状态；只有目录锁、恢复扫描、快速索引、完整校核和事务日志写入检查都通过后，才自动启用真实文件移动。
- 删除左侧竖向导航，改为命令栏下方的横向导航卡片。
- 目录大盘表格随主窗口宽度自适应，目录名称列优先获得宽度。
- 图片选中反馈恢复为 HKU Academic Red `#EF4022` 红色高亮。
- 视觉密度收紧：panel/card 使用 `12px` 圆角，button/chip/table/text panel 使用 `8px` 圆角。

本版本不创建 `_ManualReview_Staging`，也不把 raw dataset images/labels 写入 `Dataset/Select_Programme`。

