# CIVL7009 图源筛选器

[English README](README.md)

![Version](https://img.shields.io/badge/version-V1.0-094438)
![Python](https://img.shields.io/badge/python-3.11-D1C18D)
![GUI](https://img.shields.io/badge/GUI-Tkinter-009CD5)
![Status](https://img.shields.io/badge/audit-PENDING__AUDIT-EF4022)

一个轻量桌面工具，用于在 CIVL7009 `ManualReview_GroupSize_N` 目录中，从同一 `.rf.` prefix 图片组里人工选择“图源”。

## 为什么需要它

当一张源图对应多张变换图时，在 Windows 文件资源管理器里逐组挑选会很慢，也容易错放文件。这个工具一次显示一个同 prefix 图片组，人工点击图源后，自动把图源和变换图分入 `done/out`，并同步移动标签。

## V1.0 功能

- 扫描 `Dataset/Source_Archive/<ID>/images/ManualReview_GroupSize_N`。
- 匹配对应的 `labels/ManualReview_GroupSize_N`。
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

## 目录约定

```text
Dataset/Source_Archive/<ID>/
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
  --id-root Dataset/Source_Archive/01
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
f3aa42488236db6764ee43d985679012a5246497ae6bf858b576b261c5943f8a
```

## 数据安全

本仓库只包含程序，不包含原始数据集图片、标签、模型产物、运行日志或生成的审计输出。所有治理输出均保持 `PENDING_AUDIT` 状态。

## 许可证

当前尚未选择开源许可证。在加入许可证之前，本项目由项目所有者保留所有权利。
