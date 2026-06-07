# YOLO 变换数据集清洗浏览器

[English README](README.md)

![Version](https://img.shields.io/badge/latest-V1.9.1__202606041705-094438)
![Python](https://img.shields.io/badge/python-3.11-D1C18D)
![GUI](https://img.shields.io/badge/GUI-PySide6-009CD5)
![Status](https://img.shields.io/badge/audit-PENDING__AUDIT-EF4022)

这是一个桌面复核浏览器，用于清洗 YOLO 风格视觉训练数据集中的同源变换、重复或近重复图片变体。它帮助数据集维护者同屏比较同一图源相关的一组图片，保留代表性图源，把其他变体分流到 `out`，并同步移动对应的 YOLO `.txt` 标签。

本仓库按公开程序构建要求顺序发布。当前公开版本与内部构建 `V1.9.1_202606041705` 对齐。

## 为什么需要它

YOLO 训练数据集中经常混入同一底图的多个变换版本，例如旋转、裁剪、调色、增强、重新导出或近重复图片。如果这些变体在训练前被默认当作完全独立图源，后续训练解释、泄漏检查和数据质量审计都会变得更难说明。

这个工具把清洗任务变成可视化复核流程：一次展示一个图源相关组，人工选择代表图源，其余变体与标签同步进入目标复核文件夹，并保留过程证据。所有治理输出仍保持 `PENDING_AUDIT`。

## 当前版本：V1.9.1_202606041705

`V1.9.1_202606041705` 是 PySide6 复核驾驶舱（Review Cockpit）版本。它新增现代 Qt 桌面外壳，同时继续复用已测试的 V1.8.1 后端核心，用于图源组审计、快速复核索引（FastReviewIndex）、文件事务、恢复、目录锁和撤销。

V1.9.1 新增或改进：

- PySide6 / macOS glass 风格复核驾驶舱，界面更清晰、更接近现代桌面工具。
- 安全门（Safe Gate）工作流：默认只预览；真实文件移动必须在程序内显式启用。
- 核心可审计性：日志同时记录 UI 版本、后端 core 版本、core 文件路径和 SHA256。
- Core load 校验：后端符号缺失或版本异常时 fail closed，不允许继续真实移动。
- 打开筛选目录时显示进度遮罩和 ready 状态。
- Qt-safe worker 模式，用于打开 review、后台索引、缩略图、审计和导出。
- UI assets 仅使用抽象 SVG 装饰，并通过 asset manifest 声明不包含数据集图像。
- ID 初始化在本版本中保留只读/回退说明，写入动作仍由旧后端工作流处理。
- 包含 Windows 可执行程序。

本次验证结果：

```text
V1.9.1 Qt tests: 7/7 OK
V1.8.1 backend tests: 32 OK, skipped=1
source --help OK
exe audit-only smoke OK on a temporary sample dataset
```

说明：由于 V1.9.1 exe 是 windowed PyInstaller（`console=False`）程序，部分 PowerShell 会出现 `--help` 文本已打印但退出码不干净的现象。本次 release smoke 因此采用 `--audit-only`，该测试正常通过。

## 核心能力

- 直接选择图片复核文件夹。
- 从 `images/...` 自动推断对应 `labels/...`。
- 支持普通或临时复核目录中的动态 `.rf.` source-prefix 分组。
- 兼容经典 `ManualReview_GroupSize_N` 文件夹。
- 阻断标签重复、标签缺失、目标文件冲突、不完整组和恢复冲突。
- 在 Safe Gate 启用后，将选中图源及标签移动到 `done`，将变体移动到 `out`。
- 导出 JSON、CSV 和 Markdown 审计报告。
- 为图源组移动记录事务日志和恢复快照。
- 使用 review 目录锁避免同一工作目录被并发编辑。
- 使用快速内存索引和 quick preview 加速大目录工作流。
- 支持上一组/下一组导航和双击 100% 原图查看。
- 支持符合传统小键盘顺序的数字快捷键。

## 它不包含什么

- 不训练、评估或修改任何模型。
- 不生成哈希或近哈希 Manual Objects 候选组。
- 不包含后续 Manual Objects 复核、冲突复核、Tier 前缀治理或 N20_PLUS 工作流。
- 不删除、不覆盖、不上传、不暴露原始数据集图片或标签。
- 审计输出保持 `PENDING_AUDIT`；它是过程证据，不是模型性能结论。

## 预期工作目录形态

V1.9.1 支持 YOLO 风格数据集树下的标准或临时复核目录：

```text
<dataset-root>/
  images/
    <review-folder>/
      *.jpg
      done/
      out/
  labels/
    <review-folder>/
      *.txt
      done/
      out/
      Done_auto/
      Out_auto/
```

经典目录名 `ManualReview_GroupSize_N` 仍然兼容。非常规目录也可以使用，只要文件能够按 `.rf.` prefix 分组，并且每个可筛选 prefix 至少包含两张图片。

## 快速开始

下载 release asset：

```text
YOLO_Transformed_Dataset_Cleaning_Browser_V1.9.1_202606041705.zip
```

解压后运行：

```text
Dataset/Select_Programme/Executable/CIVL7009_Source_Group_Picker_V1.9.1_202606041705.exe
```

从源代码运行：

```powershell
uv run --with PySide6==6.11.1 --with Pillow python Dataset/Select_Programme/CIVL7009_source_group_picker_qt_V1.9.1_202606041705.py
```

运行测试：

```powershell
uv run --with PySide6==6.11.1 --with Pillow python Dataset/Select_Programme/test_source_group_picker_qt_V1.9.1_202606041705.py
uv run python Dataset/Select_Programme/test_source_group_picker_gui_V1.8.1_202606041443.py
```

## 安全边界

发布包不包含原始数据集图片、标签、运行日志、审计输出、模型权重或数据集压缩包。只有在复核者启用 Safe Gate 工作流之后，程序才会在用户所选复核目录内部移动文件。
