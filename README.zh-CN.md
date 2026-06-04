# YOLO Transformed Dataset Cleaning Browser

[English README](README.md)

![Version](https://img.shields.io/badge/latest-V1.2-094438)
![Python](https://img.shields.io/badge/python-3.11-D1C18D)
![GUI](https://img.shields.io/badge/GUI-Tkinter-009CD5)
![Status](https://img.shields.io/badge/audit-PENDING__AUDIT-EF4022)

一个面向 YOLO 风格变换训练数据集的轻量桌面浏览器：用于审核同源图像变体、选择一张图源代表图，并把图片-标签同步清理到 `done/out` 文件夹。

## 为什么需要它

YOLO 数据集经常包含源图及其变换版本：旋转、裁剪、颜色变化、重新导出或其他增强样本。训练前通常需要人工审核这些同源组，避免近重复变体被静默当作独立图源。

这个工具一次展示一个 `.rf.` prefix 图片组，让审核者选择图源代表图，把变体移入 `out`，并同步整理 YOLO `.txt` 标签。

## 当前版本：V1.2

V1.2 保留 V1.1 的灵活目标文件夹工作流，并通过后台文件移动和预览缓存提升交互流畅度。

V1.2 新增：

- 后台移动队列（Background Move Queue），用于非阻塞处理 `done/out` 文件移动。
- 队列状态面板，显示 queued、running、moved、failed 等任务状态。
- 后台失败回滚：当部分移动可安全逆转时，失败任务会尽可能回滚。
- 失败阻断：后台任务失败后，后续队列移动会停止。
- 预览缓存（Preview Cache），减少重复缩略图解码。
- 新增后台移动成功和后台失败回滚单元测试。

## 核心能力

- 直接选择图片工作文件夹。
- 自动从 `images/...` 推断对应 `labels/...`。
- 可选显式 `--label-dir`。
- 支持非常规审核目录中的动态 `.rf.` prefix 组大小。
- 兼容 `ManualReview_GroupSize_N` 工作流。
- 严格阻断标签重复、标签缺失和目标冲突。
- 图片与标签同步清理到 `done/out`。
- 撤销上一组已完成事务。
- JSON、CSV、Markdown 校核报告。
- 上一组/下一组导航和双击 100% 原图查看。
- Windows exe 发布资产。

## 不包含什么

- 不训练、不评估、不修改任何模型。
- 不删除、不覆盖、不编辑、不上传、不暴露原始图片或标签。
- 不包含 V1.8+ FastReviewIndex、V1.9/V2 PySide6、Safe Gate、manifest queue 或 staging 功能。

## 工作目录模型

V1.2 支持 YOLO 风格数据集树下的标准和非常规同源变换图审核目录：

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

经典目录名 `ManualReview_GroupSize_N` 仍然支持。非标准审核目录也可使用，只要文件能够按 `.rf.` prefix 分组，并且每个可筛 prefix 至少包含两张图片。

## 快速开始

### 使用 exe

下载 V1.2 release asset：

```text
YOLO_Transformed_Dataset_Cleaning_Browser_V1.2_202606050237.zip
```

解压后运行：

```text
Executable/YOLO_Transformed_Dataset_Cleaning_Browser_V1.2_202606032251.exe
```

### 从源码运行

```powershell
uv run --with Pillow python Dataset/Select_Programme/CIVL7009_source_group_picker_gui_V1.2_202606032251.py
```

### 审计数据集根目录

```powershell
uv run --with Pillow python Dataset/Select_Programme/CIVL7009_source_group_picker_gui_V1.2_202606032251.py `
  --audit-only `
  --id-root <dataset-id-root>
```

### 审计单个图片工作文件夹

```powershell
uv run --with Pillow python Dataset/Select_Programme/CIVL7009_source_group_picker_gui_V1.2_202606032251.py `
  --audit-only `
  --image-dir <dataset-id-root>/images/<review-folder>
```

## 测试

```powershell
uv run --with Pillow python Dataset/Select_Programme/test_source_group_picker_gui_V1.2_202606032251.py
```

当前 V1.2 验证结果：

```text
15/15 tests OK
```

## Release 资产

V1.2 二进制包作为 GitHub Release asset 上传，不提交到源码仓库。

包名：

```text
YOLO_Transformed_Dataset_Cleaning_Browser_V1.2_202606050237.zip
```

SHA256：

```text
0df7a5c9a562a176b7e5640abcead808322887c247166ab23e87d337a78222ed
```

## 数据安全

本仓库只包含程序，不包含原始数据集图片、标签、模型产物、运行日志或生成的审计输出。校核报告只作为数据清洗过程证据，不代表模型性能结论。

## 许可证

当前尚未选择开源许可证。在加入许可证之前，本项目由项目所有者保留所有权利。
