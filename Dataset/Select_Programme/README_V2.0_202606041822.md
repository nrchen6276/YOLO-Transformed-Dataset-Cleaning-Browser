# CIVL7009 Source Group Picker V2.0 README

Status: `PENDING_AUDIT`

## English

V2.0 is a modular PySide6 full-framework upgrade over V1.9.1. It keeps V1.8.1/V1.9.1 safety behaviour while adding capability matrix, manifest-only queue, SQLite manifest integrity, default-off physical staging framework, recovery centre, diagnostics, productivity dashboard, ID initialisation wizard, and image2 glass UI assets.

Run source mode:

```powershell
uv run --with PySide6 --with Pillow python Dataset/Select_Programme/CIVL7009_source_group_picker_qt_V2.0_202606041822.py
```

Executable:

```text
Dataset/Select_Programme/Executable/CIVL7009_Source_Group_Picker_V2.0_202606041822.exe
```

Physical staging is disabled by default. Manifest-only queue is enabled and does not move raw files. Diagnostic bundles never include raw images or labels.

## 中文

V2.0 是基于 V1.9.1 的模块化 PySide6 全框架升级，保留 V1.8.1/V1.9.1 的安全事务与审计边界，并新增能力矩阵（Capability Matrix）、清单队列（Manifest-only Queue）、SQLite 清单完整性、默认关闭的物理暂存（Physical Staging）框架、恢复中心、诊断中心、操作仪表盘、ID 初始化向导和 image2 glass UI 资产。

源码运行：

```powershell
uv run --with PySide6 --with Pillow python Dataset/Select_Programme/CIVL7009_source_group_picker_qt_V2.0_202606041822.py
```

可执行文件：

```text
Dataset/Select_Programme/Executable/CIVL7009_Source_Group_Picker_V2.0_202606041822.exe
```

物理暂存默认关闭。清单队列默认启用且不移动 raw files。诊断包永不包含 raw images/labels。