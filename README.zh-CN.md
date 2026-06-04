# YOLO 变换数据集清洗浏览器

[English README](README.md)

![Version](https://img.shields.io/badge/latest-V1.3-094438)
![Python](https://img.shields.io/badge/python-3.11-D1C18D)
![GUI](https://img.shields.io/badge/GUI-Tkinter-009CD5)
![Status](https://img.shields.io/badge/audit-PENDING__AUDIT-EF4022)

一个轻量桌面浏览器，用于清洗 YOLO 视觉训练中的变换数据集：同屏比较同源图像变体，选择一张代表性图源，并同步移动对应 YOLO 标签文件到 `done/out` 文件夹。

## 为什么需要它

YOLO 数据集中经常会混入同一原图的多种变换版本，例如旋转、裁剪、色彩变化、重新导出、增强样本或近重复图。如果这些变体在训练前被静默当作完全独立图源，后续的数据审计、训练解释和质量控制都会更难处理。

这个工具把清洗过程变成可视化工作流：一次展示一个同源 prefix 组，人工选择代表图源，其余变体进入 `out`，同时保持 `.txt` 标签同步。

## 当前版本：V1.3

V1.3 重点优化连续人工筛选时的流畅度。

V1.3 新增：

- 标签索引缓存（Cached Label Index），减少重复查找 YOLO `.txt` 标签的开销。
- 基于当前已显示组图成员准备事务，减少点击后重复扫描。
- 后台移动完成后进行后台校核刷新。
- 预加载后续组图，提前温热预览缓存。
- 新增“当前组成员 + 标签缓存”事务准备回归测试。
- 保留 V1.2 的后台移动队列、失败回滚、预览缓存、撤销和校核导出能力。

## 核心能力

- 直接选择图片工作文件夹。
- 自动从 `images/...` 推断对应 `labels/...`。
- 支持显式传入 `--label-dir`。
- 支持非常规清洗目录中的动态 `.rf.` source-prefix 分组。
- 兼容经典 `ManualReview_GroupSize_N` 文件夹。
- 严格阻断标签重复、标签缺失和目标文件冲突。
- 图片与标签同步移动到 `done/out`。
- 支持撤销上一组已完成事务。
- 导出 JSON、CSV 和 Markdown 校核报告。
- 支持上一组/下一组导航与双击 100% 原图查看。
- 提供 Windows 可执行文件 release asset。

## 不做什么

- 不训练、不评估、不修改任何模型。
- 不删除、不覆盖、不编辑、不上传、不暴露原始图片或标签。
- 不包含 V1.8+ FastReviewIndex、V1.9/V2 PySide6、Safe Gate、manifest queue 或 staging 功能。
- 校核输出保持 `PENDING_AUDIT`，它是数据清洗过程证据，不是模型性能结论。

## 工作目录模型

V1.3 支持 YOLO 风格数据集树下的标准或非常规同源变换图清洗目录：

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

### 使用可执行文件

下载 V1.3 release asset：

```text
YOLO_Transformed_Dataset_Cleaning_Browser_V1.3_202606050448.zip
```

解压后运行：

```text
Executable/YOLO_Transformed_Dataset_Cleaning_Browser_V1.3_202606032313.exe
```

SHA256：

```text
ff9f79c7eb8e054385b7f0103deecf48c78590b50425801416da2a1a56dfe7b4
```

### 从源码运行

```powershell
uv run --with Pillow python Dataset/Select_Programme/CIVL7009_source_group_picker_gui_V1.3_202606032313.py
```

### 校核整个数据集根目录

```powershell
uv run --with Pillow python Dataset/Select_Programme/CIVL7009_source_group_picker_gui_V1.3_202606032313.py `
  --audit-only `
  --id-root <dataset-root>
```

### 校核单个图片工作文件夹

```powershell
uv run --with Pillow python Dataset/Select_Programme/CIVL7009_source_group_picker_gui_V1.3_202606032313.py `
  --audit-only `
  --image-dir <dataset-root>/images/<review-folder>
```

## 测试

```powershell
uv run --with Pillow python Dataset/Select_Programme/test_source_group_picker_gui_V1.3_202606032313.py
```

V1.3 包内测试结果：`16/16 OK`。

## 发布资产

- [V1.3 release](https://github.com/nrchen6276/YOLO-Transformed-Dataset-Cleaning-Browser/releases/tag/v1.3)
- `YOLO_Transformed_Dataset_Cleaning_Browser_V1.3_202606050448.zip`
- 源码：`Dataset/Select_Programme/CIVL7009_source_group_picker_gui_V1.3_202606032313.py`
- 测试：`Dataset/Select_Programme/test_source_group_picker_gui_V1.3_202606032313.py`

## 数据安全边界

本仓库和发布包不包含原始数据集图片、YOLO 标签文件、模型权重、运行日志、校核输出或训练产物。可执行文件作为 GitHub Release asset 附加，不提交进仓库。
