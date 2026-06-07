# CIVL7009 Source Group Picker V2.0_202606041906 README

Status: `PENDING_AUDIT`

## English

`V2.0_202606041906` is a packaged-executable hotfix rebuild of V2.0. It keeps the V2.0 modular PySide6 framework and fixes packaged startup behaviour by normalising command-line arguments before `argparse` and calling `main()` from the executable entry script.

Run source mode:

```powershell
uv run --with PySide6==6.11.1 --with Pillow python Dataset/Select_Programme/CIVL7009_source_group_picker_qt_V2.0_202606041906.py
```

Executable:

```text
Dataset/Select_Programme/Executable/CIVL7009_Source_Group_Picker_V2.0_202606041906.exe
```

This build preserves the V2.0 safety model: manifest-only queue is non-mutating, physical staging remains disabled by default, and diagnostic bundles do not include raw images or labels.

## 中文

`V2.0_202606041906` 是 V2.0 的封装可执行文件启动修复版。它保留 V2.0 的模块化 PySide6 框架，并通过在 `argparse` 前归一化命令行参数、在 exe 入口中调用 `main()`，修复部分电脑上 packaged exe 打开后立即退出的问题。

源码运行：

```powershell
uv run --with PySide6==6.11.1 --with Pillow python Dataset/Select_Programme/CIVL7009_source_group_picker_qt_V2.0_202606041906.py
```

可执行文件：

```text
Dataset/Select_Programme/Executable/CIVL7009_Source_Group_Picker_V2.0_202606041906.exe
```

本构建保留 V2.0 的安全模型：清单队列不移动 raw files，物理暂存默认关闭，诊断包不包含 raw images 或 labels。

