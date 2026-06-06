# YOLO 变换数据集清洗浏览器

[English README](README.md)

![Version](https://img.shields.io/badge/latest-V1.4__202606032328-094438)
![Python](https://img.shields.io/badge/python-3.11-D1C18D)
![GUI](https://img.shields.io/badge/GUI-Tkinter-009CD5)
![Status](https://img.shields.io/badge/audit-PENDING__AUDIT-EF4022)

这是一个轻量桌面浏览器，用于清洗 YOLO 视觉训练数据集中同源变换、重复或近重复的图片变体。它帮助复核者同屏比较同源图片、选择代表性图源、把变体移动到 `out`，并同步移动对应 YOLO `.txt` 标签。

本仓库后续按内部程序版本顺序发版。当前公开 release 对齐内部 `V1.4_202606032328` 构建。

## 为什么需要它

YOLO 训练数据集中经常会混入同一原图的多种变换版本，例如旋转、裁剪、调色、重新导出、增强样本或近重复图。如果这些变体在训练前被默认当作完全独立的图源，后续训练、泄漏检查和数据质量审计都会更难解释。

这个工具把清洗任务变成可视化复核流程：一次展示一个 source-prefix 组，人工选择代表图源，其余变体与标签同步进入 `out`，并保留 `PENDING_AUDIT` 的过程证据。

## 当前版本：V1.4_202606032328

内部 `V1.4_202606032328` 属于 Tkinter 图源组筛选线。

V1.4 包含：

- 过程日志（Process Log, Plog），记录复核动作和关键耗时。
- 后台移动队列，用于执行图片与标签同步的 `done/out` 事务。
- 移动失败时回滚并阻断队列，避免半组移动。
- 缩略图后台工作队列、预览缓存和后续组预加载。
- 继承 V1.3 的标签索引缓存和当前组事务准备。
- 支持非常规目录里的动态 `.rf.` source-prefix 分组。
- ManualReview 校核摘要、公式检查、标签同步检查和报告导出。
- 支持撤销上一组已完成图源事务。

## 核心能力

- 直接选择图片工作文件夹。
- 自动从 `images/...` 推断对应 `labels/...`。
- 支持显式传入 `--label-dir`。
- 支持非常规清洗目录中的动态 `.rf.` source-prefix 分组。
- 兼容经典 `ManualReview_GroupSize_N` 文件夹。
- 严格阻断标签重复、标签缺失和目标文件冲突。
- 图片与标签同步移动到 `done/out`。
- 导出 JSON、CSV 和 Markdown 校核报告。
- 支持上一组 / 下一组导航与双击 100% 原图查看。
- 提供 Windows 可执行文件 release asset。

## 它不做什么

- 不训练、评估或修改任何模型。
- 不生成哈希或近哈希 Manual Objects 候选组。
- 不包含后续 PySide6 Manual Objects、冲突复核、Tier 前缀治理或 N20_PLUS 工作流。
- 不删除、不覆盖、不上传、不暴露原始图片或标签。
- 校核输出保持 `PENDING_AUDIT`，它是数据清洗过程证据，不是模型性能结论。

## 工作目录模型

V1.4 支持 YOLO 风格数据集树下的标准或非常规复核目录：

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

经典目录名 `ManualReview_GroupSize_N` 仍然兼容。非常规目录也可以使用，只要文件能按 `.rf.` prefix 分组，并且每个可筛选 prefix 至少包含两张图片。

## 快速开始

下载 release asset：

```text
YOLO_Transformed_Dataset_Cleaning_Browser_V1.4_202606032328.zip
```

解压后运行：

```text
Dataset/Select_Programme/Executable/CIVL7009_Source_Group_Picker_V1.4_202606032328.exe
```

从源码运行：

```powershell
uv run --with pillow python Dataset/Select_Programme/CIVL7009_source_group_picker_gui_V1.4_202606032328.py
```

运行测试：

```powershell
uv run python Dataset/Select_Programme/test_source_group_picker_gui_V1.4_202606032328.py
```

预期验证结果：

```text
16/16 OK
exe --help OK
```

## 安全边界

发布包不包含原始数据集图片、标签、运行日志、审计输出、模型权重或数据集压缩包。只有在复核者执行图源组事务时，程序才会在所选工作目录内部移动文件。
