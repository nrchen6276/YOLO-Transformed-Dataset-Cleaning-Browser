# YOLO 变换数据集清洗浏览器

[English README](README.md)

![Version](https://img.shields.io/badge/latest-V2.0__202606041822-094438)
![Python](https://img.shields.io/badge/python-3.11-D1C18D)
![GUI](https://img.shields.io/badge/GUI-PySide6-009CD5)
![Status](https://img.shields.io/badge/audit-PENDING__AUDIT-EF4022)

这是一个桌面复核浏览器，用于清洗 YOLO 风格视觉训练数据集中的同源变换、重复或近重复图片变体。它帮助数据集维护者同屏比较相关图片组，执行保留或分流决策，同步 YOLO `.txt` 标签，并保留可审计的治理过程。

本仓库按公开程序构建要求顺序发布。当前公开版本与内部构建 `V2.0_202606041822` 对齐。

## 为什么需要它

YOLO 训练数据集中经常混入同一底图的多个变换版本，例如旋转、裁剪、调色、增强、重新导出或近重复图片。如果这些变体在训练前被默认当作完全独立样本，后续训练解释、泄漏检查和数据质量审计都会变得更难说明。

这个工具把清洗任务变成可视化复核流程：一次展示一个相关图片组，由人工作出选择，并保留过程证据。所有治理输出仍保持 `PENDING_AUDIT`；它们是操作证据，不是模型性能结论。

## 当前版本：V2.0_202606041822

`V2.0_202606041822` 是 PySide6 全框架版本。它保留 V1.8.1/V1.9.1 的安全边界，并新增模块化应用结构，为后续复核工作流扩展做准备。

V2.0 新增或改进：

- 模块化 PySide6 框架包：`civl7009_picker_v2/`。
- 能力矩阵（Capability Matrix），用于显示功能开关、风险等级、是否移动 raw files 和启用门槛。
- 清单队列（Manifest-only Queue）框架默认启用，不移动 raw files。
- SQLite 清单完整性检查、schema metadata 和迁移保护。
- 物理暂存（Physical Staging）框架默认关闭，并带有同盘和恢复保护。
- 恢复中心（Recovery Centre）、诊断面板（Diagnostics Panel）、操作仪表盘（Productivity Dashboard）和设置页。
- ID 初始化向导（ID Initialisation Wizard）结构，默认 dry-run first。
- image2 / 程序化抽象 UI 资产与设计令牌（Design Tokens）。
- light、dark、high contrast 和视觉质量模式基础。
- 包含 Windows 可执行程序。

本次验证结果：

```text
V2.0 Qt/framework tests: 9/9 OK
V1.9.1 Qt tests: 7/7 OK
V1.8.1 backend tests: 32 OK, skipped=1
source --help OK
source --smoke-open OK
exe --help OK
exe --smoke-open OK
zip extraction smoke OK
```

## 核心能力

- 在 YOLO 风格目录中复核相关图片组。
- 兼容经典 `ManualReview_GroupSize_N` 目录和临时 `.rf.` 分组目录。
- 在图源组复核中使用安全门（Safe Gate）控制真实文件移动。
- 保留图片-标签配对检查、重复标签阻断、目标冲突阻断、恢复快照和目录锁。
- 使用快速内存索引加速大目录复核。
- 导出审计报告和过程元数据。
- 提供暂存、恢复、初始化、诊断、仪表盘和设置等框架页面。
- 物理暂存默认关闭。
- 清单队列默认不改变 raw files。

## 它不包含什么

- 不训练、评估或修改任何模型。
- 不生成哈希或近哈希候选组。
- 不包含后续 Manual Objects 复核、冲突复核、Tier 前缀治理或 N20_PLUS 工作流。
- 不删除、不覆盖、不上传、不暴露原始数据集图片或标签。
- 审计输出保持 `PENDING_AUDIT`。

## 快速开始

下载 release asset：

```text
YOLO_Transformed_Dataset_Cleaning_Browser_V2.0_202606041822.zip
```

解压后运行：

```text
Dataset/Select_Programme/Executable/CIVL7009_Source_Group_Picker_V2.0_202606041822.exe
```

从源代码运行：

```powershell
uv run --with PySide6==6.11.1 --with Pillow python Dataset/Select_Programme/CIVL7009_source_group_picker_qt_V2.0_202606041822.py
```

运行测试：

```powershell
uv run --with PySide6==6.11.1 --with Pillow python Dataset/Select_Programme/test_source_group_picker_qt_V2.0_202606041822.py
uv run --with PySide6==6.11.1 --with Pillow python Dataset/Select_Programme/test_source_group_picker_qt_V1.9.1_202606041705.py
uv run python Dataset/Select_Programme/test_source_group_picker_gui_V1.8.1_202606041443.py
```

## 安全边界

发布包不包含原始数据集图片、标签、运行日志、审计输出、模型权重或数据集压缩包。文件移动仅限明确的复核工作流和受保护功能。清单队列默认不改变 raw files；物理暂存默认关闭。
