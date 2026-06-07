# YOLO 变换数据集清洗浏览器

[English README](README.md)

![Version](https://img.shields.io/badge/latest-V2.2__202606042006-094438)
![Python](https://img.shields.io/badge/python-3.11-D1C18D)
![GUI](https://img.shields.io/badge/GUI-PySide6-009CD5)
![Status](https://img.shields.io/badge/audit-PENDING__AUDIT-EF4022)

这是一个面向 YOLO 风格视觉训练数据集的桌面复核浏览器，用于清洗同源变换、重复或近重复图片变体。它帮助数据集维护者同屏比较相关图片组，执行保留或分流决策，同步 YOLO `.txt` 标签，并保留可审计的过程记录。

本仓库按内部程序构建顺序补发公开版本。当前公开版本与内部构建 `V2.2_202606042006` 对齐。

## 当前版本：V2.2_202606042006

`V2.2_202606042006` 是基于 V2.1 的交互打磨版本。它保留高速图源组复核链路，同时减少高吞吐人工清洗时的操作摩擦。

V2.2 新增或改进：

- 取消手动输入 `MOVE`。
- 启动时显示中文安全说明，确认后进入自动移动准备状态。
- 只有目录锁、恢复扫描、快速索引（FastReviewIndex）、完整校核和事务日志路径检查全部通过后，才自动启用真实文件移动。
- 将左侧竖向侧栏改为顶部横向导航卡片，节约横向空间。
- 目录大盘表格随窗口宽度自适应，目录列优先获得宽度。
- 恢复图片卡片的 HKU Academic Red `#EF4022` 红色选中反馈。
- 统一并收紧全局圆角，让界面更紧凑，更适合长时间筛选。
- 保留 image2 / 程序化抽象 UI 资产，并继续遵守无 raster UI asset 策略。

验证结果：

```text
V2.2 Qt tests: 7/7 OK
V2.1 Qt regression: 5/5 OK
V1.9.1 Qt regression: 7/7 OK
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
YOLO_Transformed_Dataset_Cleaning_Browser_V2.2_202606042006.zip
```

解压后运行：

```text
Dataset/Select_Programme/Executable/CIVL7009_Source_Group_Picker_V2.2_202606042006.exe
```

从源码运行：

```powershell
uv run --with PySide6==6.11.1 --with Pillow python Dataset/Select_Programme/CIVL7009_source_group_picker_qt_V2.2_202606042006.py
```

运行测试：

```powershell
uv run --with PySide6==6.11.1 --with Pillow python Dataset/Select_Programme/test_source_group_picker_qt_V2.2_202606042006.py
uv run --with PySide6==6.11.1 --with Pillow python Dataset/Select_Programme/test_source_group_picker_qt_V2.1_202606041930.py
uv run --with PySide6==6.11.1 --with Pillow python Dataset/Select_Programme/test_source_group_picker_qt_V1.9.1_202606041705.py
uv run python Dataset/Select_Programme/test_source_group_picker_gui_V1.8.1_202606041443.py
```

## 安全边界

发布包不包含原始数据集图片、标签、运行日志、审计输出、模型权重或数据集压缩包。文件移动仅限明确的复核工作流和受保护功能。审计输出保持 `PENDING_AUDIT`。

