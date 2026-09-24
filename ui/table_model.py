"""
Table model and custom item delegates for displaying certificate data in PyQt6.
"""

from typing import List, Any, Optional
from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex, QSortFilterProxyModel
from PyQt6.QtGui import QColor, QBrush, QFont

from core.models import CertificateData, ProcessingStatus
from ui.styles import STATUS_COLORS, ACT_COLORS


class CertificateTableModel(QAbstractTableModel):
    """Data model holding rows of CertificateData for display in QTableView."""

    COLUMNS = [
        ("Original File", "original_filename"),
        ("Governing Act", "act"),
        ("Form Type", "form_type"),
        ("Category", "category"),
        ("Deductee / Collectee", "deductee_name"),
        ("PAN", "deductee_pan"),
        ("TAN", "deductor_tan"),
        ("FY", "financial_year"),
        ("AY", "assessment_year"),
        ("Quarter", "quarter"),
        ("Proposed Filename", "proposed_filename"),
        ("Status", "status"),
    ]

    def __init__(self, data: Optional[List[CertificateData]] = None, parent=None):
        super().__init__(parent)
        self._data: List[CertificateData] = data or []

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._data)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self.COLUMNS)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            if 0 <= section < len(self.COLUMNS):
                return self.COLUMNS[section][0]
        elif orientation == Qt.Orientation.Vertical and role == Qt.ItemDataRole.DisplayRole:
            return str(section + 1)
        return None

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._data)):
            return None

        cert = self._data[index.row()]
        col_key = self.COLUMNS[index.column()][1]

        if role == Qt.ItemDataRole.DisplayRole:
            val = getattr(cert, col_key, "")
            if isinstance(val, ProcessingStatus):
                return val.value
            return str(val) if val else ""

        elif role == Qt.ItemDataRole.TextAlignmentRole:
            # Center-align short codes (PAN, TAN, FY, AY, Quarter, Status, Form)
            if col_key in ("act", "form_type", "category", "deductee_pan", "deductor_tan", "financial_year", "assessment_year", "quarter", "status"):
                return Qt.AlignmentFlag.AlignCenter
            return Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft

        elif role == Qt.ItemDataRole.BackgroundRole:
            # Highlight Act column with subtle tone
            if col_key == "act":
                bg_hex = ACT_COLORS.get(cert.act, ("#FFFFFF", "#000000"))[0]
                return QBrush(QColor(bg_hex))
            # Highlight Status column
            elif col_key == "status":
                status_str = cert.status.value if isinstance(cert.status, ProcessingStatus) else str(cert.status)
                bg_hex = STATUS_COLORS.get(status_str, ("#FFFFFF", "#000000"))[0]
                return QBrush(QColor(bg_hex))

        elif role == Qt.ItemDataRole.ForegroundRole:
            if col_key == "act":
                fg_hex = ACT_COLORS.get(cert.act, ("#FFFFFF", "#000000"))[1]
                return QBrush(QColor(fg_hex))
            elif col_key == "status":
                status_str = cert.status.value if isinstance(cert.status, ProcessingStatus) else str(cert.status)
                fg_hex = STATUS_COLORS.get(status_str, ("#FFFFFF", "#000000"))[1]
                return QBrush(QColor(fg_hex))
            elif col_key == "deductee_name":
                return QBrush(QColor("#0F172A"))

        elif role == Qt.ItemDataRole.FontRole:
            if col_key in ("act", "deductee_name", "status"):
                font = QFont()
                font.setBold(True)
                return font

        elif role == Qt.ItemDataRole.ToolTipRole:
            if col_key == "status" and cert.message:
                return cert.message
            if col_key == "proposed_filename":
                return f"Path: {cert.final_filepath or cert.file_path}"
            return None

        return None

    def get_certificate(self, row: int) -> Optional[CertificateData]:
        if 0 <= row < len(self._data):
            return self._data[row]
        return None

    def set_data(self, certificates: List[CertificateData]):
        self.beginResetModel()
        self._data = list(certificates)
        self.endResetModel()

    def update_item(self, cert: CertificateData):
        """Update a specific item in place or append if new."""
        for idx, item in enumerate(self._data):
            if str(item.file_path) == str(cert.file_path):
                self._data[idx] = cert
                start_idx = self.index(idx, 0)
                end_idx = self.index(idx, len(self.COLUMNS) - 1)
                self.dataChanged.emit(start_idx, end_idx)
                return

        # Not found: append
        self.beginInsertRows(QModelIndex(), len(self._data), len(self._data))
        self._data.append(cert)
        self.endInsertRows()

    def clear(self):
        self.beginResetModel()
        self._data.clear()
        self.endResetModel()

    def get_all(self) -> List[CertificateData]:
        return list(self._data)


class CertificateFilterProxyModel(QSortFilterProxyModel):
    """Enables multi-field searching and dropdown filtering."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.search_text = ""
        self.act_filter = ""
        self.status_filter = ""
        self.form_filter = ""

    def set_search_text(self, text: str):
        self.search_text = text.lower().strip()
        self.invalidateFilter()

    def set_act_filter(self, act: str):
        self.act_filter = act.strip()
        self.invalidateFilter()

    def set_status_filter(self, status: str):
        self.status_filter = status.strip()
        self.invalidateFilter()

    def set_form_filter(self, form_name: str):
        self.form_filter = form_name.strip()
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        model: CertificateTableModel = self.sourceModel()
        cert = model.get_certificate(source_row)
        if not cert:
            return False

        # Act filter
        if self.act_filter and self.act_filter != "All Acts":
            if cert.act != self.act_filter:
                return False

        # Status filter
        if self.status_filter and self.status_filter != "All Statuses":
            status_val = cert.status.value if isinstance(cert.status, ProcessingStatus) else str(cert.status)
            if status_val != self.status_filter:
                return False

        # Form filter
        if self.form_filter and self.form_filter != "All Forms":
            if cert.form_type != self.form_filter and cert.form_code != self.form_filter:
                return False

        # Free text search across all major columns
        if self.search_text:
            searchable = " ".join([
                cert.original_filename,
                cert.deductee_name,
                cert.deductee_pan,
                cert.deductor_tan,
                cert.form_type,
                cert.act,
                cert.proposed_filename,
                cert.quarter,
                cert.financial_year,
            ]).lower()
            if self.search_text not in searchable:
                return False

        return True
