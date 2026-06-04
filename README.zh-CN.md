# CIVL7009 图源筛选器

[English README](README.md)

![Version](https://img.shields.io/badge/version-V1.0-094438)
![Python](https://img.shields.io/badge/python-3.11-D1C18D)
![GUI](https://img.shields.io/badge/GUI-Tkinter-009CD5)
![Status](https://img.shields.io/badge/audit-PENDING__AUDIT-EF4022)

一个面向 YOLO 风格视觉训练数据集的轻量桌面工具：用于多源图像集合整合后的人工筛选、同源变换图清洗、图源代表图选择，以及图片-标签同步整理。

## 为什么需要它

YOLO 数据集经常来自多个来源、多个下载批次、Roboflow 风格导出或增强流水线。同一张源图可能带有旋转、裁剪、颜色变化等多个变换版本。人工在 Windows 文件资源管理器里逐组清理这些图片，速度慢，也容易错放标签。

这个工具把清理过程变成一个聚焦的图源组审核工作流：一次显示一个同源 `.rf.` prefix 图片组，人工选择要保留为图源代表的图片，其余变换图移入 `out`，并同步移动 YOLO `.txt` 标签。

## V1.0 功能

- 扫描包含同级 `images/` 与 `labels/` 的 YOLO 风格数据集根目录。
- 识别 V1.0 的组大小工作目录约定 `ManualReview_GroupSize_N`，并匹配 `labels/` 下的对应目录。
- 使用文件 stem 中最后一个 `.rf.` 标记进行 prefix 分组。
- 选中的图源进入 `images/.../done`。
- 同 prefix 的其他变换图进入 `images/.../out`。
- 对应 `.txt` 标签同步进入 `labels/.../done` 和 `labels/.../out`。
- 标签查找兼容 root、`done`、`out`、`Done_auto`、`Out_auto`。
- 标签缺失、标签重复、目标文件已存在等情况会阻断移动。
- 校核 root/done/out 图片数、prefix 数、组大小分布，以及 `out = done x (N - 1)`。
- 导出 JSON、CSV、Markdown 校核报告。
- 支持撤销上一组。
- 支持上一组/下一组导航。
- 支持双击打开 100% 原图查看窗口。
- 提供 GitHub Release 中的 Windows 可执行文件。

## V1.0 不包含什么

- 不处理全局 `images/Done`、`images/transformations`、`labels/Done`、`labels/transformations`。
- 不训练、不评估、不修改任何模型。
- 不删除、不覆盖、不编辑、不上传、不暴露原始图片或标签。
- 不包含 V1.1、V1.8、V1.9、V2.x、PySide6、staging、Safe Gate、FastReviewIndex 等后续功能。

## 工作目录约定

V1.0 需要先把待清洗数据整理成下面这种 YOLO 风格图源组审核与清洗目录：

```text
<dataset-id-root>/
  images/
    ManualReview_GroupSize_N/
      *.jpg
      done/
      out/
  labels/
    ManualReview_GroupSize_N/
      *.txt
      done/
      out/
      Done_auto/
      Out_auto/
```

`ManualReview_GroupSize_1` 会被视为原始单图统计目录，不进入人工择一队列。

这个命名方式是 V1.0 的工作目录约定。工具目标是通用的多源 YOLO 数据集合并、审核与清洗，不绑定某一个本地数据集结构。

## 快速开始

### 使用 exe

下载 V1.0 Release asset：

```text
CIVL7009_Source_Group_Picker_V1.0_202606050035.zip
```

解压后运行：

```text
Executable/CIVL7009_Source_Group_Picker_V1.0_202606032227.exe
```

### 从源码运行

```powershell
uv run --with Pillow python Dataset/Select_Programme/CIVL7009_manualreview_source_picker_gui_V1.0_202606032227.py
```

### 只导出校核报告

```powershell
uv run --with Pillow python Dataset/Select_Programme/CIVL7009_manualreview_source_picker_gui_V1.0_202606032227.py `
  --audit-only `
  --id-root <dataset-id-root>
```

## 测试

```powershell
uv run --with Pillow python Dataset/Select_Programme/test_manualreview_source_picker_gui_V1.0_202606032227.py
```

当前 V1.0 验证结果：

```text
12/12 tests OK
```

## Release 资产

V1.0 的二进制包作为 GitHub Release asset 上传，不提交到源码仓库。

包名：

```text
CIVL7009_Source_Group_Picker_V1.0_202606050035.zip
```

SHA256：

```text
e170f10a15ae095bf9647be4f3ea7ef0160f4aec7022cc1889a68a32d9246420
```

## 数据安全

本仓库只包含程序，不包含原始数据集图片、标签、模型产物、运行日志或生成的审计输出。校核报告只作为数据清洗过程证据，不代表模型性能结论。

## 许可证

当前尚未选择开源许可证。在加入许可证之前，本项目由项目所有者保留所有权利。
