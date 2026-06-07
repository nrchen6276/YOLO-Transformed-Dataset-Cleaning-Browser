from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from PySide6.QtWidgets import QApplication
except Exception as exc:  # pragma: no cover
    QT_IMPORT_ERROR = exc
else:
    QT_IMPORT_ERROR = None

from .main_window import MainWindow


def normalise_cli_args(argv: list[str] | None = None) -> list[str] | None:
    """Return argparse-ready args, tolerating callers that pass sys.argv."""
    if argv is None:
        return None
    args = list(argv)
    if not args:
        return args
    first_name = Path(args[0]).name.casefold()
    if first_name.endswith((".py", ".pyw", ".exe")):
        return args[1:]
    return args


def create_app(argv: list[str] | None = None) -> QApplication:
    if QT_IMPORT_ERROR is not None:
        raise RuntimeError(QT_IMPORT_ERROR)
    app = QApplication.instance()
    if app is None:
        qt_argv = argv if argv is not None else [sys.argv[0]]
        app = QApplication(qt_argv)
    app.setApplicationName("CIVL7009 Source Group Picker V2.0")
    return app


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CIVL7009 图源筛选器 V2.0 全框架控制台。")
    parser.add_argument("--run-mode", default="")
    parser.add_argument("--audit-only", action="store_true")
    parser.add_argument("--id-root", default="")
    parser.add_argument("--smoke-open", action="store_true", help="创建窗口、处理一次事件并退出，用于启动诊断。")
    return parser.parse_args(normalise_cli_args(argv))


def main(argv: list[str] | None = None) -> int:
    cli_args = normalise_cli_args(argv)
    args = parse_args(cli_args)
    app = create_app([sys.argv[0]])
    window = MainWindow(run_mode=args.run_mode or ("audit_only" if args.audit_only else "gui_production"))
    window.show()
    if args.smoke_open:
        app.processEvents()
        window.close()
        app.processEvents()
        return 0
    return app.exec()
