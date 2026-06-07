from __future__ import annotations

from typing import Any

try:
    from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
except Exception:  # pragma: no cover
    QAbstractTableModel = object
    QModelIndex = object
    Qt = None


class SimpleTableModel(QAbstractTableModel):
    def __init__(self, headers: list[str], rows: list[list[Any]] | None = None) -> None:
        super().__init__()
        self.headers = headers
        self.rows = rows or []

    def rowCount(self, parent: QModelIndex | None = None) -> int:
        return len(self.rows)

    def columnCount(self, parent: QModelIndex | None = None) -> int:
        return len(self.headers)

    def data(self, index: QModelIndex, role: int = None) -> Any:
        if not index.isValid() or role not in (Qt.DisplayRole, Qt.ToolTipRole):
            return None
        try:
            return str(self.rows[index.row()][index.column()])
        except IndexError:
            return ""

    def headerData(self, section: int, orientation: int, role: int = None) -> Any:
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.headers[section]
        return None

    def set_rows(self, rows: list[list[Any]]) -> None:
        self.beginResetModel()
        self.rows = rows
        self.endResetModel()
