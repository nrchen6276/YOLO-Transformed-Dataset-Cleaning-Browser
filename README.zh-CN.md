# YOLO 变换数据集清洗浏览器

[English README](README.md)

![Version](https://img.shields.io/badge/latest-V2.0__202606041906-094438)
![Python](https://img.shields.io/badge/python-3.11-D1C18D)
![GUI](https://img.shields.io/badge/GUI-PySide6-009CD5)
![Status](https://img.shields.io/badge/audit-PENDING__AUDIT-EF4022)

这是一个面向 YOLO 风格视觉训练数据集的桌面复核浏览器，用于清洗同源变换、重复或近重复图片变体。它帮助数据集维护者同屏比较相关图片组，执行保留或分流决策，同步 YOLO `.txt` 标签，并保留可审计的过程记录。

本仓库按内部程序构建顺序补发公开版本。当前公开版本与内部构建 `V2.0_202606041906` 对齐。

## 当前版本：V2.0_202606041906

`V2.0_202606041906` 是 V2.0 的 packaged executable hotfix（封装可执行文件启动修复）构建。它保留 V2.0 的完整 PySide6 框架，并修复了封装 exe 启动行为：前一版封装入口可能把 exe 路径误传给 `argparse`，在部分电脑上导致程序打开后立即退出。

它继续保留 V2.0 的能力：

- 模块化 PySide6 包：`civl7009_picker_v2/`。
- 能力矩阵（Capability Matrix）：显示功能开关、风险等级、raw-file movement 状态和启用门槛。
- 清单队列（Manifest-only Queue）框架默认启用，不移动 raw files。
- SQLite 清单完整性检查、schema metadata 和迁移保护。
- 物理暂存（Physical Staging）框架默认关闭，并带同盘和恢复保护。
- 恢复中心、诊断面板、操作仪表盘、设置页和 ID 初始化向导。
- image2 / 程序化抽象 UI 资产与设计令牌（Design Tokens）。
- light、dark、high contrast 与视觉质量模式基础。
- 包含 Windows 可执行程序。

验证结果：

```text
V2.0 framework tests: 9/9 OK
V1.9.1 Qt tests: 7/7 OK
V1.8.1 backend tests: 32 OK, skipped=1
source --help OK
source --smoke-open OK
exe --help OK
exe --smoke-open OK
zip extraction smoke OK
```

## 它解决什么问题

YOLO 训练数据集中经常混入同一底图的多个变换版本，例如旋转、裁剪、调色、增强、重新导出或近重复图片。如果这些变体在训练前被默认当作完全独立样本，后续训练解释、泄漏检查和数据质量审计都会变得更难说明。

这个工具把清洗任务变成可视化复核流程：一次展示一个相关图片组，由人工作出选择，并保留过程证据。所有治理输出仍保持 `PENDING_AUDIT`；它们是操作证据，不是模型性能结论。

## 快速开始

下载：

```text
YOLO_Transformed_Dataset_Cleaning_Browser_V2.0_202606041906.zip
```

解压后运行：

```text
Dataset/Select_Programme/Executable/CIVL7009_Source_Group_Picker_V2.0_202606041906.exe
```

从源码运行：

```powershell
uv run --with PySide6==6.11.1 --with Pillow python Dataset/Select_Programme/CIVL7009_source_group_picker_qt_V2.0_202606041906.py
```

运行测试：

```powershell
uv run --with PySide6==6.11.1 --with Pillow python Dataset/Select_Programme/test_source_group_picker_qt_V2.0_202606041822.py
uv run --with PySide6==6.11.1 --with Pillow python Dataset/Select_Programme/test_source_group_picker_qt_V1.9.1_202606041705.py
uv run python Dataset/Select_Programme/test_source_group_picker_gui_V1.8.1_202606041443.py
```

## 安全边界

发布包不包含原始数据集图片、标签、运行日志、审计输出、模型权重或数据集压缩包。文件移动仅限明确的复核工作流和受保护功能。清单队列默认不改变 raw files；物理暂存默认关闭。

