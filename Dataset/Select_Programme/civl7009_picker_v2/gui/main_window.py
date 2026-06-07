from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QKeySequence, QShortcut
    from PySide6.QtWidgets import (
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QLabel,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QStackedWidget,
        QTableView,
        QTextEdit,
        QToolTip,
        QVBoxLayout,
        QWidget,
    )
except Exception as exc:  # pragma: no cover
    QT_IMPORT_ERROR = exc
else:
    QT_IMPORT_ERROR = None

from ..config import ASSET_DIR
from ..domain.models import Capability, ProductivitySnapshot
from ..services.asset_service import AssetService
from ..services.capability_service import CapabilityMatrixService
from ..services.diagnostic_service import DiagnosticService
from ..services.productivity_service import ProductivityService
from ..services.recovery_service import RecoveryService
from ..services.staging_service import StagingService
from ..version import STATUS, UI_VERSION
from .models_qt import SimpleTableModel
from .style import v2_qss


class MainWindow(QMainWindow):
    NAV = [
        ("Review", "图源筛选（Review）"),
        ("Staging", "暂存队列（Staging）"),
        ("Recovery", "恢复中心（Recovery）"),
        ("Initialise", "ID 初始化（Initialise）"),
        ("Diagnostics", "诊断中心（Diagnostics）"),
        ("Dashboard", "操作仪表盘（Dashboard）"),
        ("Settings", "设置（Settings）"),
    ]

    def __init__(self, run_mode: str = "gui_production") -> None:
        super().__init__()
        if QT_IMPORT_ERROR is not None:
            raise RuntimeError(QT_IMPORT_ERROR)
        self.run_mode = run_mode
        self.asset_service = AssetService()
        self.asset_service.ensure_assets()
        self.capability_service = CapabilityMatrixService()
        self.diagnostic_service = DiagnosticService()
        self.recovery_service = RecoveryService()
        self.staging_service = StagingService()
        self.productivity_service = ProductivityService()
        self.active_id_root = ""
        self.active_review_dir = ""
        self.group_size = ""
        self.session_short = "session"
        self.safe_gate_status = "文件移动已启用"
        self.manifest_status = "清单队列已启用"
        self.recovery_status = "恢复状态正常"
        self.theme = "light"
        self.visual_quality = "Balanced"
        self.nav_buttons: dict[str, QPushButton] = {}
        self.stack = QStackedWidget()
        self.context_label = QLabel()
        self.reason_label = QLabel("就绪。")
        self.setWindowTitle("CIVL7009 图源筛选器 V2.0")
        self.resize(1500, 900)
        self.setMinimumSize(1366, 768)
        self.build_ui()
        self.apply_style()
        self.install_shortcuts()

    def apply_style(self) -> None:
        self.setStyleSheet(v2_qss(self.theme, self.visual_quality))

    def build_ui(self) -> None:
        root = QWidget()
        layout = QHBoxLayout(root)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(14)
        sidebar = self.build_sidebar()
        content = self.build_content()
        layout.addWidget(sidebar, 0)
        layout.addWidget(content, 1)
        self.setCentralWidget(root)

    def panel(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("glassPanel")
        return frame

    def build_sidebar(self) -> QWidget:
        sidebar = self.panel()
        sidebar.setFixedWidth(250)
        layout = QVBoxLayout(sidebar)
        title = QLabel("CIVL7009\n图源筛选器 V2.0")
        title.setObjectName("title")
        layout.addWidget(title)
        subtitle = QLabel("PENDING_AUDIT\n中文界面 + English terms")
        subtitle.setObjectName("muted")
        layout.addWidget(subtitle)
        for idx, (key, label) in enumerate(self.NAV):
            btn = QPushButton(label)
            btn.setObjectName("navButton")
            btn.setCheckable(True)
            btn.clicked.connect(lambda _=False, i=idx: self.set_page(i))
            self.nav_buttons[key] = btn
            layout.addWidget(btn)
        layout.addStretch(1)
        self.reason_label.setWordWrap(True)
        self.reason_label.setObjectName("muted")
        layout.addWidget(self.reason_label)
        return sidebar

    def build_content(self) -> QWidget:
        content = QWidget()
        layout = QVBoxLayout(content)
        header = self.panel()
        header_layout = QVBoxLayout(header)
        title = QLabel("V2.0 全框架控制台（Full Framework Console）")
        title.setObjectName("title")
        header_layout.addWidget(title)
        self.context_label.setObjectName("context")
        header_layout.addWidget(self.context_label)
        layout.addWidget(header)
        self.stack.addWidget(self.build_review_page())
        self.stack.addWidget(self.build_staging_page())
        self.stack.addWidget(self.build_recovery_page())
        self.stack.addWidget(self.build_initialise_page())
        self.stack.addWidget(self.build_diagnostics_page())
        self.stack.addWidget(self.build_dashboard_page())
        self.stack.addWidget(self.build_settings_page())
        layout.addWidget(self.stack, 1)
        self.set_page(0)
        self.update_context_header()
        return content

    def update_context_header(self) -> None:
        self.context_label.setText(
            f"ID 根目录: {self.active_id_root or '未选择'} | "
            f"筛选目录: {self.active_review_dir or '未选择'} | "
            f"组大小: {self.group_size or '未识别'} | "
            f"会话: {self.session_short} | "
            f"安全门: {self.safe_gate_status} | "
            f"Manifest: {self.manifest_status} | "
            f"Recovery: {self.recovery_status}"
        )

    def set_page(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        for i, (key, _) in enumerate(self.NAV):
            self.nav_buttons[key].setChecked(i == index)
            self.nav_buttons[key].setProperty("active", i == index)
            self.nav_buttons[key].style().unpolish(self.nav_buttons[key])
            self.nav_buttons[key].style().polish(self.nav_buttons[key])

    def build_review_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        kpi = self.kpi_strip(["Root 剩余", "Done 组", "Out 图片", "Move Queue", "Label Sync", "Recovery"])
        layout.addWidget(kpi)
        body = QHBoxLayout()
        grid = self.panel()
        grid_layout = QGridLayout(grid)
        for i in range(1, 7):
            card = self.image_card(i)
            grid_layout.addWidget(card, (i - 1) // 3, (i - 1) % 3)
        inspector = self.panel()
        inspector_layout = QVBoxLayout(inspector)
        inspector_layout.addWidget(QLabel("当前组检查器（Current Group Inspector）"))
        inspector_layout.addWidget(QLabel("状态: preview_selected / committing / blocked 会显示 icon + text。"))
        inspector_layout.addWidget(QLabel("禁用原因: Full audit 未完成 / Recovery issue / Safe Gate 关闭。"))
        body.addWidget(grid, 3)
        body.addWidget(inspector, 1)
        layout.addLayout(body, 1)
        bottom = self.panel()
        bottom_layout = QVBoxLayout(bottom)
        bottom_layout.addWidget(QLabel("移动队列 / 最近事件（Move Queue / Recent Events）"))
        bottom_layout.addWidget(self.table(["时间", "事件", "状态"], [["--", "等待操作", "就绪"]]))
        layout.addWidget(bottom)
        return page

    def image_card(self, index: int) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.addWidget(QLabel(f"[{index}] 图片卡片（ImageCard）"))
        preview = QLabel("抽象预览区域\n无 raw dataset image")
        preview.setAlignment(Qt.AlignCenter)
        preview.setMinimumHeight(145)
        preview.setStyleSheet("border: 1px dashed #94A3B8; border-radius: 14px;")
        layout.addWidget(preview)
        layout.addWidget(QLabel("文件名: sample_prefix.rf.x.jpg"))
        layout.addWidget(QLabel("分辨率: -- | 标签: Label OK | 目标: done/out"))
        return card

    def build_staging_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("暂存队列（Staging）- Physical Staging 默认关闭"))
        pipeline = QHBoxLayout()
        for label in ["Root", "Manifest Ready", "Staging", "Staged Ready", "Displayed", "Committing", "Done/Out", "Failed"]:
            card = self.panel()
            card_layout = QVBoxLayout(card)
            card_layout.addWidget(QLabel(label))
            card_layout.addWidget(QLabel("组: 0 | 图: 0 | 标签: 0"))
            card_layout.addWidget(QLabel("警告/错误: 0"))
            pipeline.addWidget(card)
        layout.addLayout(pipeline)
        layout.addWidget(QLabel("Manifest queue = 虚拟队列，不移动文件；Physical staging queue = review dir 内 raw files 暂存；Move queue = done/out 提交队列。"))
        layout.addWidget(self.table(["Prefix", "State", "Images", "Labels", "Last Operation", "Error", "Action"], []), 1)
        return page

    def build_recovery_page(self) -> QWidget:
        page = QWidget()
        layout = QHBoxLayout(page)
        issue_list = self.panel()
        issue_layout = QVBoxLayout(issue_list)
        issue_layout.addWidget(QLabel("恢复问题列表（Recovery Issues）"))
        issue_layout.addWidget(self.table(["Severity", "Error Code", "Prefix"], [["INFO", "NONE", "--"]]))
        timeline = self.panel()
        timeline_layout = QVBoxLayout(timeline)
        timeline_layout.addWidget(QLabel("时间线 / 文件操作图（Timeline / File-operation Graph）"))
        timeline_layout.addWidget(QTextEdit("选择一个 issue 后显示 affected paths、why it blocks、suggested action。"))
        actions = self.panel()
        actions_layout = QVBoxLayout(actions)
        actions_layout.addWidget(QLabel("动作面板（Actions）"))
        for text in ["Inspect", "Export Diagnostic", "Rebuild State", "Retry", "Rollback", "Restore to Root", "Mark Manually Resolved", "Open Folder"]:
            btn = QPushButton(text)
            btn.setToolTip("高风险动作需要输入 ROLLBACK / RESTORE / RESOLVE。")
            actions_layout.addWidget(btn)
        layout.addWidget(issue_list, 1)
        layout.addWidget(timeline, 2)
        layout.addWidget(actions, 1)
        return page

    def build_initialise_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("ID 初始化向导（ID Initialisation Wizard）"))
        steps = [
            "1. 选择 ID Root",
            "2. 发现 YOLO 分支",
            "3. 匹配图片和标签",
            "4. 按 .rf. prefix 分组",
            "5. 检查目标冲突",
            "6. Dry-run 报告",
            "7. 输入 INIT 确认",
            "8. Copy and Journal",
            "9. Final Audit",
        ]
        for step in steps:
            layout.addWidget(QLabel(step))
        layout.addWidget(QLabel("原始 YOLO folders 永不移动/删除；冲突 target 阻断。"))
        return page

    def build_diagnostics_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(self.kpi_strip(["session_id", "trace_id", "Manifest", "Recovery", "慢操作", "最后错误"]))
        caps = self.capability_rows()
        layout.addWidget(QLabel("能力矩阵（Capability Matrix）"))
        layout.addWidget(self.table(["能力", "默认", "风险", "移动 raw files", "Gate", "状态"], caps), 1)
        buttons = QHBoxLayout()
        for text in ["导出完整诊断包", "导出脱敏诊断包", "打开日志目录", "打开 Manifest 目录"]:
            buttons.addWidget(QPushButton(text))
        layout.addLayout(buttons)
        return page

    def build_dashboard_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("Session Operations Dashboard"))
        layout.addWidget(QLabel("PENDING_AUDIT — operational metrics only"))
        snap: ProductivitySnapshot = self.productivity_service.snapshot()
        layout.addWidget(
            self.kpi_strip(
                [
                    f"完成组: {snap.groups_completed}",
                    f"Groups/min: {snap.groups_per_min}",
                    f"Median click-to-next: {snap.median_click_to_next_ms}",
                    f"p95 move: {snap.p95_move_ms}",
                    f"Undo: {snap.undo_count}",
                    f"Recovery: {snap.recovery_count}",
                    "剩余时间: rough estimate, not a data quality metric",
                ]
            )
        )
        layout.addWidget(QLabel("图表占位: last 20 commits latency sparkline / errors by type / throughput by 10-minute window"))
        return page

    def build_settings_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("设置（Settings）"))
        layout.addWidget(QLabel("主题: light / dark / high_contrast；默认 light。"))
        layout.addWidget(QLabel("视觉质量: Performance / Balanced / Glass；默认 Balanced。"))
        layout.addWidget(QLabel("动效: normal / reduced motion。"))
        layout.addWidget(QLabel("Physical Staging: 默认关闭，高风险，需要 STAGE。"))
        layout.addWidget(QLabel("image2 Assets: 可用则启用；缺失时 fallback procedural SVG/PNG。"))
        layout.addWidget(self.table(["能力", "默认", "风险", "移动 raw files", "Gate", "状态"], self.capability_rows()))
        return page

    def kpi_strip(self, labels: list[str]) -> QWidget:
        strip = QWidget()
        layout = QHBoxLayout(strip)
        for label in labels:
            card = self.panel()
            card_layout = QVBoxLayout(card)
            card_layout.addWidget(QLabel(label))
            layout.addWidget(card)
        return strip

    def table(self, headers: list[str], rows: list[list[Any]]) -> QTableView:
        view = QTableView()
        view.setModel(SimpleTableModel(headers, rows))
        view.horizontalHeader().setStretchLastSection(True)
        return view

    def capability_rows(self) -> list[list[Any]]:
        rows = []
        for cap in self.capability_service.get_matrix():
            rows.append([cap.display_name, cap.default_state, cap.risk, "是" if cap.raw_file_movement else "否", cap.gate, "启用" if cap.enabled else "关闭"])
        return rows

    def install_shortcuts(self) -> None:
        shortcuts = {
            "1": "选择/提交第 1 张",
            "2": "选择/提交第 2 张",
            "3": "选择/提交第 3 张",
            "4": "选择/提交第 4 张",
            "5": "选择/提交第 5 张",
            "6": "选择/提交第 6 张",
            "7": "选择/提交第 7 张",
            "8": "选择/提交第 8 张",
            "Ctrl+Z": "撤销上一组",
            "Space": "打开 100% viewer",
            "?": "快捷键说明",
        }
        for key, reason in shortcuts.items():
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.activated.connect(lambda r=reason: self.show_disabled_reason(r))

    def show_disabled_reason(self, reason: str) -> None:
        self.reason_label.setText(f"快捷键/控件说明: {reason}")
        QToolTip.showText(self.mapToGlobal(self.rect().center()), reason, self)

    def export_diagnostic_for_tests(self, mode: str = "redacted_share") -> Path:
        result = self.diagnostic_service.export_bundle("ui_test_session", mode=mode)
        return result.path
