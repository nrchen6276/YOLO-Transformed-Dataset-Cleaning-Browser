from __future__ import annotations


def v2_qss(theme: str = "light", quality: str = "Balanced") -> str:
    dark = theme == "dark"
    bg = "#111827" if dark else "#EEF2F6"
    panel = "rgba(31,41,55,0.78)" if dark else "rgba(255,255,255,0.78)"
    text = "#F9FAFB" if dark else "#17201C"
    sub = "#CBD5E1" if dark else "#667085"
    border = "#3A6960" if dark else "#D8DEE6"
    return f"""
    QWidget {{ background: {bg}; color: {text}; font-family: 'Microsoft YaHei UI', 'Segoe UI', sans-serif; font-size: 13px; }}
    QFrame#glassPanel, QFrame#card {{ background: {panel}; border: 1px solid {border}; border-radius: 18px; }}
    QLabel#muted {{ color: {sub}; }}
    QLabel#title {{ font-size: 20px; font-weight: 700; color: {text}; }}
    QLabel#context {{ padding: 7px 10px; border-radius: 10px; background: rgba(9,68,56,0.10); color: {text}; }}
    QPushButton {{ padding: 9px 12px; border-radius: 11px; border: 1px solid {border}; background: rgba(255,255,255,0.68); color: {text}; }}
    QPushButton:hover {{ border-color: #009CD5; }}
    QPushButton:disabled {{ color: #94A3B8; background: rgba(148,163,184,0.18); }}
    QPushButton#navButton[active="true"] {{ background: #094438; color: white; border-color: #094438; }}
    QPushButton#dangerButton {{ background: rgba(239,64,34,0.14); color: #EF4022; border-color: #EF4022; }}
    QTableView {{ background: rgba(255,255,255,0.64); border-radius: 12px; gridline-color: #E5E7EB; selection-background-color: rgba(0,156,213,0.18); }}
    QHeaderView::section {{ background: rgba(9,68,56,0.10); padding: 8px; border: 0; font-weight: 700; }}
    QProgressBar {{ border-radius: 8px; background: rgba(148,163,184,0.22); height: 10px; text-align: center; }}
    QProgressBar::chunk {{ border-radius: 8px; background: #009CD5; }}
    """
