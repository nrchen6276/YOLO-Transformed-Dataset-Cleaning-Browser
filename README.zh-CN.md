# YOLO 变换数据集清洗浏览器

[English README](README.md)

![Version](https://img.shields.io/badge/latest-V1.4-094438)
![Python](https://img.shields.io/badge/python-3.11-D1C18D)
![GUI](https://img.shields.io/badge/GUI-PySide6-009CD5)
![Status](https://img.shields.io/badge/audit-PENDING__AUDIT-EF4022)

一个用于清洗 YOLO 视觉训练数据集的桌面浏览器，面向变换图、重复图、跨数据集相似候选图等人工复核任务。它可以帮助审核者同屏比较候选组、选择保留对象、查看 YOLO `.txt` 标注框，并写出结构化人工选择结果。

## 为什么需要它

YOLO 数据集中常见同一来源图像的变换版本、跨数据集重复图、近哈希候选组或哈希审计生成的人工复核对象。如果这些候选在训练前被静默当作完全独立样本，后续数据治理、泄漏检查和实验解释都会更难可信。

这个工具把清洗任务变成可视化工作流：

- 对比同源变换图；
- 复核跨数据集重复或近重复候选组；
- 在预览图上显示 YOLO 标签框；
- 把数字类别 ID 映射为每个数据集自己的类别名；
- 写出后续治理 agent 可回读的人工选择结果。

## 当前版本：V1.4

V1.4 是公共发布线中首次包含新版 PySide6 复核界面和 Manual Objects 工作流的版本。

V1.4 新增：

- PySide6 桌面界面和工作流标签页。
- 跨数据集哈希 / 近哈希候选组的 Manual Objects 复核。
- 面向大规模候选区的全局 index 快速读取。
- 选中具体组后才异步加载图片预览。
- 单击保存并在同一 `Reason / Nxx` 内自动进入下一组。
- YOLO `.txt` 标注框叠加预览。
- `ID_Classes/<dataset_id>/` 类别文件检测；类别文件名不必叫 `classes.txt`。
- 更大的自适应图片预览卡片，尽可能利用工作区空间。
- 写出 `manual_selection.json` 供后续治理流程回读。

## 核心能力

- 直接选择图片工作文件夹进行同源变换图清洗。
- 自动从 `images/...` 推断对应 `labels/...`。
- 支持非常规清洗目录中的动态 `.rf.` source-prefix 分组。
- 图源组复核中将图片与标签同步移动到 `done/out`。
- 支持撤销上一组已完成图源事务。
- 基于 `group_manifest.json` 的跨数据集 Manual Objects 复核。
- 人工状态：`APPROVED`、`SKIP`、`AMBIGUOUS`、`NEEDS_AGENT_CHECK`。
- YOLO bbox 叠加和类别名映射。
- 导出 JSON、CSV 和 Markdown 校核/汇总报告。
- 提供 Windows 可执行文件 release asset。

## 不做什么

- 不训练、不评估、不修改任何模型。
- 不删除、不覆盖、不编辑、不上传、不暴露原始图片或标签。
- 不生成哈希或近哈希候选组。
- 不执行 physical staging 或数据集级破坏性操作。
- 校核输出保持 `PENDING_AUDIT`，它是数据清洗过程证据，不是模型性能结论。

## 快速开始

### 使用可执行文件

下载 V1.4 release asset：

```text
YOLO_Transformed_Dataset_Cleaning_Browser_V1.4_202606052324.zip
```

解压后运行：

```text
Executable/CIVL7009_Source_Group_Picker_V3.0.5_202606052235.exe
```

SHA256：

```text
4C3C68454A52E0F4A619EF946CE11A6CAD2060AB1FE7CE3DB088E5F0955CCC37
```

### 从源码运行

```powershell
uv run --with PySide6 --with Pillow python Dataset/Select_Programme/CIVL7009_source_group_picker_qt_V3.0.5_202606052235.py
```

## Manual Objects 类别文件

若需要 bbox 标签显示类别名，请把类别 `.txt` 放到：

```text
Manual_Objects/
  ID_Classes/
    ID01/
      any_name.txt
    ID09/
      classes_for_id09.txt
```

文件名可以自定义。每个 ID 文件夹中第一个有效非空 `.txt` 会作为该 ID 的类别表。

## 测试

```powershell
uv run --with PySide6 --with Pillow python Dataset/Select_Programme/test_source_group_picker_qt_V3.0.5_202606052235.py
```

V1.4 包内测试结果：`14/14 OK`。

回归检查：

- V3.0.4 regression: `13/13 OK`
- V2.2.4 regression: `10/10 OK`
- exe smoke test: OK

## 发布资产

- [V1.4 release](https://github.com/nrchen6276/YOLO-Transformed-Dataset-Cleaning-Browser/releases/tag/v1.4)
- `YOLO_Transformed_Dataset_Cleaning_Browser_V1.4_202606052324.zip`
- 源码入口：`Dataset/Select_Programme/CIVL7009_source_group_picker_qt_V3.0.5_202606052235.py`
- 测试文件：`Dataset/Select_Programme/test_source_group_picker_qt_V3.0.5_202606052235.py`

## 数据安全边界

本仓库和发布包不包含原始数据集图片、YOLO 标签文件、模型权重、运行日志、校核输出或训练产物。可执行文件和 zip 压缩包作为 GitHub Release assets 附加，不提交进仓库。
