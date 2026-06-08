# YOLO 变换数据集清洗浏览器

这是一个面向 YOLO 视觉训练数据集的数据清洗桌面工具，用于在人类复核阶段比较和整理多来源、增强变换、合并后重复或近重复的图片与标签。它的目标不是替代算法治理，而是让人工复核更快、更一致，并把选择结果保存为后续治理 agent 可读取的结构化文件。

当前最新版本：**V3.0.1_202606051430**

## 工具能力

- 打开数据清洗流程生成的图片组复核目录。
- 在同一界面展示同组图片，支持小键盘式布局。
- 支持图源选择、图片与 YOLO 标签同步移动、撤销、校核报告和事务安全。
- 新增跨库候选复核（Manual Objects Review），用于复核重复或近重复候选对象。
- 优先读取已落地的 `Manual_Objects/_indexes/manual_objects_index.csv`，快速生成复核大盘。
- 只有打开某一组时，才懒加载该组的 `group_manifest.json`。
- 写入结构化 `manual_selection.json`，供后续治理流程回读。
- 提供 Windows exe，用户不需要通过命令行启动 Python。

## V3.0.1 更新重点

- 针对 Manual Objects 复核工作流的性能热修复。
- 从 `_indexes/manual_objects_index.csv` 快速构建全局大盘。
- 启动时不再逐组解析全部 `group_manifest.json`。
- 支持大规模候选集的分页与筛选。
- 支持邻近组和缩略图后台预取。
- 支持“保存并进入下一组”的高吞吐人工复核链路。
- 继续保持 V3.0 安全边界：不执行哈希扫描、不创建候选区、不移动主库文件、不改写候选图片或标签。

## 下载

请下载最新 release asset：

`YOLO_Transformed_Dataset_Cleaning_Browser_V3.0.1_202606051430.zip`

压缩包包含 exe、源码入口、V1.8.2 core、版本化包、测试、构建元数据和抽象 UI 资产。压缩包不包含原始数据集图片、标签、模型权重或数据集 YAML。

## 安全边界

跨库候选复核是人工选择结果写入工具，不是哈希扫描器，也不是主库治理移动器。它不创建候选组，不删除候选副本，不移动主库图片或标签。Manual Objects 模式只写入 `manual_selection.json` 和 `_selection_history/`。

所有数据治理结论仍保持 **PENDING_AUDIT**，不能直接升级为论文、模型或数据质量实证结论。
