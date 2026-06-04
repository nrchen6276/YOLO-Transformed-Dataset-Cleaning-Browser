# CIVL7009 图源筛选器

[English README](README.md)

![Version](https://img.shields.io/badge/latest-V1.1-094438)
![Python](https://img.shields.io/badge/python-3.11-D1C18D)
![GUI](https://img.shields.io/badge/GUI-Tkinter-009CD5)
![Status](https://img.shields.io/badge/audit-PENDING__AUDIT-EF4022)

一个面向 YOLO 风格视觉训练数据集的轻量桌面工具：用于多源图像集合整合后的人工筛选、同源变换图清洗、图源代表图选择，以及图片-标签同步整理到 `done/out` 文件夹。

## 为什么需要它

大型 YOLO 数据集经常混合多个来源、下载批次、标注工具导出结果或增强流水线。同一张源图可能带有旋转、裁剪、颜色变化、重新导出或其他处理版本。人工在 Windows 文件资源管理器里逐组清理这些图片，速度慢，也容易错放标签。

这个工具把清理过程变成一个聚焦的图源组审核工作流：一次显示一个同源 `.rf.` prefix 图片组，人工选择要保留为图源代表的图片，其余变换图移入 `out`，并同步整理 YOLO 标签。

## 当前版本：V1.1

V1.1 保留 V1.0 的安全模型，并把工作流从固定审核目录名扩展为更灵活的目标文件夹审核。

V1.1 新增：

- GUI 支持直接选择目标图片工作文件夹。
- 新增 `--image-dir`，用于审计或打开单个图片工作文件夹。
- 新增可选 `--label-dir`，用于显式指定图片-标签配对目录。
- 支持从 `images/...` 路径自动推断匹配的 `labels/...` 路径。
- 支持非常规审核目录中的动态组大小；不同 `.rf.` prefix 可以拥有不同成员数。
- 对 `ManualReview_GroupSize_N` 目录名提示与实际组大小不一致的情况改为 warning；有效 prefix 仍可筛选。
- 支持为单个目标工作文件夹导出校核报告。
- 继续兼容 V1.0 的 `ManualReview_GroupSize_N` 工作流。

## 核心能力

- 使用文件 stem 中最后一个 `.rf.` 标记进行 prefix 分组。
- 选中的图源进入 `images/.../done`。
- 同 prefix 的其他变换图进入 `images/.../out`。
- 对应 `.txt` 标签同步进入 `labels/.../done` 和 `labels/.../out`。
- 标签查找兼容 root、`done`、`out`、`Done_auto`、`Out_auto`。
- 标签缺失、标签重复、目标文件已存在等情况会阻断移动。
- 当目录提供组大小提示时，校核 root/done/out 图片数、prefix 数、组大小分布和公式关系。
- 导出 JSON、CSV、Markdown 校核报告。
- 支持撤销上一组事务。
- 支持上一组/下一组导航和双击 100% 原图查看。
- 通过 GitHub Releases 提供 Windows 可执行文件。

## 不包含什么

- 不训练、不评估、不修改任何模型。
- 不删除、不覆盖、不编辑、不上传、不暴露原始图片或标签。
- 不包含 V1.2+、V1.8+、V1.9/V2 PySide6、Safe Gate、FastReviewIndex、manifest queue 或 staging 功能。

## 工作目录模型

V1.1 支持 YOLO 风格数据集树下的标准和非常规图源组审核目录：

```text
<dataset-id-root>/
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

经典 V1.0 目录名 `ManualReview_GroupSize_N` 仍然支持。V1.1 也支持非标准审核目录，只要文件能够按 `.rf.` prefix 分组，并且每个可筛 prefix 至少包含两张图片。

## 快速开始

### 使用 exe

下载 V1.1 release asset：

```text
CIVL7009_Source_Group_Picker_V1.1_202606050147.zip
```

解压后运行：

```text
Executable/CIVL7009_Source_Group_Picker_V1.1_202606032239.exe
```

### 从源码运行

```powershell
uv run --with Pillow python Dataset/Select_Programme/CIVL7009_source_group_picker_gui_V1.1_202606032239.py
```

### 审计数据集根目录

```powershell
uv run --with Pillow python Dataset/Select_Programme/CIVL7009_source_group_picker_gui_V1.1_202606032239.py `
  --audit-only `
  --id-root <dataset-id-root>
```

### 审计单个图片工作文件夹

```powershell
uv run --with Pillow python Dataset/Select_Programme/CIVL7009_source_group_picker_gui_V1.1_202606032239.py `
  --audit-only `
  --image-dir <dataset-id-root>/images/<review-folder>
```

## 测试

```powershell
uv run --with Pillow python Dataset/Select_Programme/test_source_group_picker_gui_V1.1_202606032239.py
```

当前 V1.1 验证结果：

```text
13/13 tests OK
```

## Release 资产

V1.1 二进制包作为 GitHub Release asset 上传，不提交到源码仓库。

包名：

```text
CIVL7009_Source_Group_Picker_V1.1_202606050147.zip
```

SHA256：

```text
6b9d5c23d58c5010c36dc6d692f94e6988736e20719d020cd1490d3aa977e429
```

## 数据安全

本仓库只包含程序，不包含原始数据集图片、标签、模型产物、运行日志或生成的审计输出。校核报告只作为数据清洗过程证据，不代表模型性能结论。

## 许可证

当前尚未选择开源许可证。在加入许可证之前，本项目由项目所有者保留所有权利。
