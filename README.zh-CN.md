# YOLO 变换数据集清洗浏览器

[English README](README.md)

![Version](https://img.shields.io/badge/latest-V1.6__202606040015-094438)
![Python](https://img.shields.io/badge/python-3.11-D1C18D)
![GUI](https://img.shields.io/badge/GUI-Tkinter-009CD5)
![Status](https://img.shields.io/badge/audit-PENDING__AUDIT-EF4022)

这是一个轻量桌面浏览器，用于清洗 YOLO 风格视觉训练数据集中的同源变换、重复或近重复图片变体。它帮助复核者同屏比较同一图源相关的一组图片，选择代表性图源，把其余变体移动到 `out`，并同步移动对应的 YOLO `.txt` 标签。

本仓库严格按照内部程序版本顺序发版。当前公开 release 与内部构建 `V1.6_202606040015` 对齐。

## 为什么需要它

YOLO 训练数据集中经常会混入同一原图的多种变换版本，例如旋转、裁剪、调色、增强、重新导出或近重复图。如果这些变体在训练前被默认当作完全独立的图源，后续训练解释、泄漏检查和数据质量审计都会变得更困难。

这个工具把清洗任务变成可视化复核流程：一次展示一个 source-prefix 组，人工选择代表图源，其余变体与标签同步进入 `out`，并保留 `PENDING_AUDIT` 的过程证据。

## 当前版本：V1.6_202606040015

`V1.6_202606040015` 属于 Tkinter 图源组筛选线，严格接在内部 `V1.5_202606032354` 之后。

V1.6 新增或改进：

- GUI 异常明细现在会显示具体异常 prefix 和文件名，复核者不再需要只靠统计数字推测问题组。
- 校核摘要把 prefix 级异常行带入界面文本区，便于人工排查。
- 继承 V1.5 的缓存状态事务准备、数字小键盘布局、数字键选择、后台移动队列、缩略图缓存、过程日志、失败回滚、撤销、动态 `.rf.` 分组和校核报告导出。
- 测试覆盖增加到 `19/19 OK`。

## 核心能力

- 直接选择图片复核文件夹。
- 自动从 `images/...` 推断对应 `labels/...`。
- 支持显式传入 `--label-dir`。
- 支持普通或临时复核目录中的动态 `.rf.` source-prefix 分组。
- 兼容经典 `ManualReview_GroupSize_N` 文件夹。
- 严格阻断标签重复、标签缺失、目标文件冲突和不完整组。
- 将选中图源及标签移动到 `done`，将变体移动到 `out`。
- 导出 JSON、CSV 和 Markdown 校核报告。
- 支持上一组/下一组导航和双击 100% 原图查看。
- 支持符合传统小键盘顺序的数字快捷键。
- 提供 Windows 可执行文件作为 release asset。

## 它不包含什么

- 不训练、评估或修改任何模型。
- 不生成哈希或近哈希 Manual Objects 候选组。
- 不包含后续 PySide6、Manual Objects 复核、冲突复核、Tier 前缀治理或 N20_PLUS 工作流。
- 不删除、不覆盖、不上传、不暴露原始数据集图片或标签。
- 校核输出保持 `PENDING_AUDIT`；它是过程证据，不是模型性能结论。

## 预期工作目录形态

V1.5 支持 YOLO 风格数据集树下的标准或临时复核目录：

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
YOLO_Transformed_Dataset_Cleaning_Browser_V1.6_202606040015.zip
```

解压后运行：

```text
Dataset/Select_Programme/Executable/CIVL7009_Source_Group_Picker_V1.6_202606040015.exe
```

从源码运行：

```powershell
uv run --with pillow python Dataset/Select_Programme/CIVL7009_source_group_picker_gui_V1.6_202606040015.py
```

运行测试：

```powershell
uv run python Dataset/Select_Programme/test_source_group_picker_gui_V1.6_202606040015.py
```

预期验证结果：

```text
19/19 OK
exe --help OK
```

## 安全边界

发布包不包含原始数据集图片、标签、运行日志、审计输出、模型权重或数据集压缩包。只有在复核者执行图源组决策时，程序才会在用户所选复核目录内部移动文件。
