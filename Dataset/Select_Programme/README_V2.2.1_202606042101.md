# CIVL7009 Source Group Picker V2.2.1 Hotfix Note

Status: `PENDING_AUDIT`

## English

V2.2.1 is a standalone executable hotfix for V2.2. Logs from another computer showed that V2.2 could start from a folder outside `Dataset/Select_Programme` and then fail with `Core Load Failed` after a review folder was selected. The bundled V1.8.1 core existed inside the PyInstaller package, but the loader did not check the `_MEIPASS` extraction directory first.

Fix:

- Check PyInstaller `_MEIPASS` bundled core first.
- Then check executable/programme sibling paths.
- Log candidate paths and failure details if core loading still fails.
- Keep V2.2 automatic move, horizontal navigation, keypad layout, and selection feedback behaviour.

## 中文

V2.2.1 是 V2.2 的单文件 exe 热修复版。换电脑测试日志显示，V2.2 从 `Dataset/Select_Programme` 之外的目录启动后，选择筛选目录会出现 `Core Load Failed`。V1.8.1 core 实际已经打包进 PyInstaller，但加载器没有优先检查 `_MEIPASS` 临时解包目录。

修复：

- 优先检查 PyInstaller `_MEIPASS` 内置 core。
- 再检查 exe 同级 / programme sibling 路径。
- 如果仍加载失败，记录候选路径和失败细节。
- 保留 V2.2 的自动移动、横向导航、小键盘布局和选中反馈行为。

所有操作结论保持 `PENDING_AUDIT`。

