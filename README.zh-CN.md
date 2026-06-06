# YOLO 变换数据集清洗浏览器

[English README](README.md)

![Version](https://img.shields.io/badge/latest-V1.8.2__202606042313-094438)
![Python](https://img.shields.io/badge/python-3.11-D1C18D)
![GUI](https://img.shields.io/badge/GUI-Tkinter-009CD5)
![Status](https://img.shields.io/badge/audit-PENDING__AUDIT-EF4022)

这是一个轻量桌面复核浏览器，用于清洗 YOLO 风格视觉训练数据集中的同源变换、重复或近重复图片变体。它帮助数据集维护者同屏比较同一图源相关的一组图片，保留代表性图源，把其他变体分流到 `out`，并同步移动对应的 YOLO `.txt` 标签。

本仓库严格按照内部程序版本顺序发布。当前公开版本与内部构建 `V1.8.2_202606042313` 对齐。

## 为什么需要它

YOLO 训练数据集中经常混入同一底图的多个变换版本，例如旋转、裁剪、调色、增强、重新导出或近重复图片。如果这些变体在训练前被默认当作完全独立图源，后续训练解释、泄漏检查和数据质量审计都会变得更难说明。

这个工具把清洗任务变成可视化复核流程：一次展示一个图源相关组，人工选择代表图源，其余变体与标签同步进入目标复核文件夹，并保留过程证据。所有治理输出仍保持 `PENDING_AUDIT`。

## 当前版本：V1.8.2_202606042313

`V1.8.2_202606042313` 是一个仅包含源代码核心（source-only core）的兼容版本。它严格接在内部 `V1.8.1_202606041443` 之后，并保留后续 Qt/PySide6 外壳所复用的核心文件。

重要边界：

- 内部产物集中存在 V1.8.2 核心源文件，但没有同版本独立 exe、PyInstaller spec 或专用 V1.8.2 测试文件。
- 因此本次 GitHub release asset 是源代码核心包，不是 Windows 可执行程序包。
- 为保持内外版本号一致，本次按内部 V1.8.2 原始源文件如实发布。

V1.8.2 保留或承接的能力：

- 继承 V1.8.1 的快速复核索引（FastReviewIndex）、快速预览（quick preview）、事务日志、恢复扫描、目录锁、动态 `.rf.` 分组、标签定位、后台移动队列与审计导出核心。
- 保留 GUI 启动、直接筛选目录、`--audit-only` 等命令行入口。
- 保留按运行模式分流日志和图源组事务安全机制。
- 作为后续 Qt/PySide6 界面版本打包复用的版本化核心。

发布验证中发现的已知问题：

- 使用 V1.8.1 回归测试套件复放到 V1.8.2 核心时，结果为 `30 tests OK, 2 errors, skipped=1`。
- 两个错误都来自 YOLO 初始化辅助函数测试，原因是 `audit_yolo_dataset()` 内部引用了未定义的 `group_size`。
- 图源组复核、事务、目录锁、撤销、快速索引与审计路径相关测试均通过。

## 核心能力

- 直接选择图片复核文件夹。
- 从 `images/...` 自动推断对应 `labels/...`。
- 支持显式传入 `--label-dir`。
- 支持普通或临时复核目录中的动态 `.rf.` source-prefix 分组。
- 兼容经典 `ManualReview_GroupSize_N` 文件夹。
- 阻断标签重复、标签缺失、目标文件冲突和不完整组。
- 将选中图源及标签移动到 `done`，将变体移动到 `out`。
- 导出 JSON、CSV 和 Markdown 审计报告。
- 为图源组移动记录事务日志和恢复快照。
- 使用 review 目录锁避免同一工作目录被并发编辑。
- 使用快速内存索引和 quick preview 加速大目录工作流。
- 支持上一组/下一组导航和双击 100% 原图查看。
- 支持符合传统小键盘顺序的数字快捷键。

## 它不包含什么

- 不训练、评估或修改任何模型。
- 不生成哈希或近哈希 Manual Objects 候选组。
- 不包含后续 PySide6、Manual Objects 复核、冲突复核、Tier 前缀治理或 N20_PLUS 工作流。
- 不提供同版本 V1.8.2 Windows exe。
- 不删除、不覆盖、不上传、不暴露原始数据集图片或标签。
- 审计输出保持 `PENDING_AUDIT`；它是过程证据，不是模型性能结论。

## 预期工作目录形态

V1.8.2 支持 YOLO 风格数据集树下的标准或临时复核目录：

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
YOLO_Transformed_Dataset_Cleaning_Browser_V1.8.2_202606042313.zip
```

从源代码运行：

```powershell
uv run --with pillow python Dataset/Select_Programme/CIVL7009_source_group_picker_gui_V1.8.2_202606042313.py
```

查看命令行帮助：

```powershell
uv run --with pillow python Dataset/Select_Programme/CIVL7009_source_group_picker_gui_V1.8.2_202606042313.py --help
```

本次发布验证结果：

```text
source --help OK
V1.8.1 回归测试套件复放到 V1.8.2 核心：30 OK, 2 errors, skipped=1
```

## 安全边界

发布包不包含原始数据集图片、标签、运行日志、审计输出、模型权重或数据集压缩包。只有在复核者执行图源组决策时，程序才会在用户所选复核目录内部移动文件。
