# YOLO 变换数据集清洗浏览器

[English README](README.md)

![Version](https://img.shields.io/badge/latest-V1.5-094438)
![Python](https://img.shields.io/badge/python-3.11-D1C18D)
![GUI](https://img.shields.io/badge/GUI-PySide6-009CD5)
![Status](https://img.shields.io/badge/audit-PENDING__AUDIT-EF4022)

这是一个用于清洗 YOLO 视觉训练数据集的 PySide6 桌面浏览器，面向变换图、重复图、近重复图和跨数据集候选组等人工复核任务。它帮助用户快速比较候选图片、查看 YOLO `.txt` 标注框、选择保留或移除对象，并写出后续数据治理脚本可回读的结构化人工选择结果。

它是一个保守的数据清洗与复核工具，不是训练工具，也不是破坏性数据集移动器。

## 为什么需要它

YOLO 数据集中经常会出现旋转、裁剪、调色、重导出、重复或感知哈希相似的图片。如果这些候选在训练前没有被人工复核，就更难判断样本来源、泄漏风险和后续实验解释是否可信。

这个工具把这些清洗任务变成可视化工作流：

- 浏览同源变换图片组；
- 复核跨数据集精确哈希和近哈希候选组；
- 在预览图上绘制 YOLO 标签框和类别名；
- 支持保留一个、保留多个、全部保留或全部移除；
- 记录操作历史，并写出 `manual_selection.json`；
- 将所有治理输出保持为 `PENDING_AUDIT`，避免把过程证据误写成模型效果结论。

## 当前版本：V1.5

公开发布版本 `V1.5` 打包了内部已验证的 `V5.2_202606061825` 构建。

V1.5 新增：

- `N20_PLUS` 大型 Manual Objects 候选组现在会在可滚动图片区显示全部候选卡片。
- 大组缩略图改为分批异步加载，不再只显示前 30 张候选。
- 预览状态面板会显示已完成、进行中、排队和失败的缩略图数量。
- “刷新当前组预览”会刷新当前组全部候选缓存。
- 保留已有 Manual Objects 复核能力：YOLO 标注框叠加、类别名映射、操作历史、`ALL_OUT`、`ALL_DONE`、撤销、冲突提示和对象级冲突复核。
- 保留图源组筛选能力：动态 `.rf.` 分组、后台移动到 `done/out`、标签同步、撤销和键盘驱动复核。

## 核心能力

- 直接选择 YOLO 变换图源组工作目录。
- 自动匹配 `images/...` 与 `labels/...`。
- 对同源变换图进行动态分组。
- 在图源组复核中后台移动到 `done/out`，并保持标签同步。
- 基于 `group_manifest.json` 与 `_indexes/manual_objects_index.csv` 执行跨库候选复核。
- 支持复核状态：`APPROVED`、`ALL_OUT`、`ALL_DONE`、`SKIP`、`AMBIGUOUS`、`NEEDS_AGENT_CHECK`。
- YOLO 标注框叠加和按数据集 ID 的类别文件检测。
- 跨 reason 决策的对象级冲突提示。
- Tier 前缀治理页面，用于统一前缀标记审计。
- 导出 JSON、CSV、Markdown 和历史记录，供后续治理 agent 回读。
- 提供 Windows 可执行文件 release asset。

## 它不做什么

- 不训练、评估或修改任何模型。
- 不生成哈希或近哈希候选组。
- 不删除原始数据集图片或标签。
- 不上传或暴露原始数据集材料。
- 默认不执行 physical staging。
- 不把审计结果升级为模型性能结论。

## 快速开始

下载最新 release asset：

```text
YOLO_Transformed_Dataset_Cleaning_Browser_V1.5_202606062103.zip
```

解压后运行：

```text
Dataset/Select_Programme/Executable/CIVL7009_Source_Group_Picker_V5.2_202606061825.exe
```

从源码运行：

```powershell
uv run --with PySide6 --with pillow python Dataset/Select_Programme/CIVL7009_source_group_picker_qt_V5.2_202606061825.py
```

运行测试：

```powershell
uv run --with PySide6 --with pillow python Dataset/Select_Programme/test_source_group_picker_qt_V5.2_202606061825.py
```

预期验证结果：

```text
34/34 OK
exe --smoke-open OK
```

## Manual Objects 类别文件

如果需要在 YOLO 标注框上显示类别名，请把任意 `.txt` 类别文件放入每个数据集 ID 文件夹：

```text
Manual_Objects/
  ID_Classes/
    ID01/
      any_name.txt
    ID09/
      classes_for_id09.txt
```

类别文件名不必叫 `classes.txt`；每个 ID 文件夹中第一个有效的非空 `.txt` 会作为该数据集的类别表。

## 安全边界

发布包不包含原始数据集图片、标签、运行日志、审计输出、模型权重或数据集压缩包。Manual Objects 模式只会在用户保存复核结果时写入 `manual_selection.json` 和 `_selection_history`。所有审计输出继续保持 `PENDING_AUDIT`。

## 发布

- [最新版本](https://github.com/nrchen6276/YOLO-Transformed-Dataset-Cleaning-Browser/releases/latest)
- [全部版本](https://github.com/nrchen6276/YOLO-Transformed-Dataset-Cleaning-Browser/releases)
