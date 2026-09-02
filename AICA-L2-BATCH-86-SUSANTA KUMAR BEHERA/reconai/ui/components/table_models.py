from typing import Any, Dict, List, Optional
from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PyQt6.QtGui import QColor

from reconai.models.transaction import (
    StatementTransaction,
    LedgerEntry,
    MatchRecord,
    AuditFlag,
    AuditSeverity,
)


class StatementTableModel(QAbstractTableModel):
    """Table model for bank statement transactions."""

    HEADERS = ["Row", "Date", "Narration", "Amount (INR)", "Type", "Balance", "Matched"]

    def __init__(self, data: Optional[List[StatementTransaction]] = None):
        super().__init__()
        self._data: List[StatementTransaction] = data or []

    def set_data(self, data: List[StatementTransaction]):
        self.beginResetModel()
        self._data = data
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._data)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self.HEADERS)

    def headerData(self, section: int, orientation: Qt.Orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.HEADERS[section]
        return None

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or index.row() >= len(self._data):
            return None

        tx = self._data[index.row()]
        col = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0:
                return str(tx.source_row_ref)
            elif col == 1:
                return tx.date.strftime("%d-%b-%Y")
            elif col == 2:
                return tx.description
            elif col == 3:
                return f"₹ {tx.amount:,.2f}"
            elif col == 4:
                return tx.type.value
            elif col == 5:
                return f"₹ {tx.balance:,.2f}" if tx.balance else "-"
            elif col == 6:
                return "✓ Matched" if tx.matched else "Unmatched"

        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col in (0, 1, 4, 6):
                return Qt.AlignmentFlag.AlignCenter
            elif col in (3, 5):
                return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter

        return None


class LedgerTableModel(QAbstractTableModel):
    """Table model for client ledger entries."""

    HEADERS = ["Voucher No", "Date", "Particulars / Account", "Amount (INR)", "Type", "Approver", "GSTIN", "TDS", "Matched"]

    def __init__(self, data: Optional[List[LedgerEntry]] = None):
        super().__init__()
        self._data: List[LedgerEntry] = data or []

    def set_data(self, data: List[LedgerEntry]):
        self.beginResetModel()
        self._data = data
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._data)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self.HEADERS)

    def headerData(self, section: int, orientation: Qt.Orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.HEADERS[section]
        return None

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or index.row() >= len(self._data):
            return None

        e = self._data[index.row()]
        col = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0:
                return str(e.source_row_ref)
            elif col == 1:
                return e.date.strftime("%d-%b-%Y")
            elif col == 2:
                return f"{e.description} ({e.account_name})" if e.account_name else e.description
            elif col == 3:
                return f"₹ {e.amount:,.2f}"
            elif col == 4:
                return e.type.value
            elif col == 5:
                return e.approver_ref or "-"
            elif col == 6:
                return e.gstin or "-"
            elif col == 7:
                return e.tds_section or "-"
            elif col == 8:
                return "✓ Matched" if e.matched else "Unmatched"

        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col in (0, 1, 4, 5, 6, 7, 8):
                return Qt.AlignmentFlag.AlignCenter
            elif col == 3:
                return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter

        return None


class MatchedRecordsTableModel(QAbstractTableModel):
    """Table model for matched / probable pairs."""

    HEADERS = [
        "Score", "Rule", "Bank Date", "Bank Narration", "Bank Amt",
        "Ledger Date", "Ledger Particulars", "Voucher", "Ledger Amt", "Reason",
    ]

    def __init__(
        self,
        matches: Optional[List[MatchRecord]] = None,
        stmt_map: Optional[Dict[str, StatementTransaction]] = None,
        ledger_map: Optional[Dict[str, LedgerEntry]] = None,
    ):
        super().__init__()
        self._matches: List[MatchRecord] = matches or []
        self._stmt_map: Dict[str, StatementTransaction] = stmt_map or {}
        self._ledger_map: Dict[str, LedgerEntry] = ledger_map or {}

    def set_data(
        self,
        matches: List[MatchRecord],
        stmt_map: Dict[str, StatementTransaction],
        ledger_map: Dict[str, LedgerEntry],
    ):
        self.beginResetModel()
        self._matches = matches
        self._stmt_map = stmt_map
        self._ledger_map = ledger_map
        self.endResetModel()

    def get_record(self, row: int) -> Optional[MatchRecord]:
        if 0 <= row < len(self._matches):
            return self._matches[row]
        return None

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._matches)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self.HEADERS)

    def headerData(self, section: int, orientation: Qt.Orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.HEADERS[section]
        return None

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or index.row() >= len(self._matches):
            return None

        m = self._matches[index.row()]
        col = index.column()
        s = self._stmt_map.get(m.statement_tx_id) or self._stmt_map.get(str(m.statement_tx_id))
        l = self._ledger_map.get(m.ledger_entry_id) or self._ledger_map.get(str(m.ledger_entry_id))

        if not s and self._stmt_map:
            try:
                s = self._stmt_map.get(str(int(m.statement_tx_id)))
            except Exception:
                pass

        if not l and self._ledger_map:
            try:
                l = self._ledger_map.get(str(int(m.ledger_entry_id)))
            except Exception:
                pass

        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0:
                return f"{int(m.confidence_score * 100)}%"
            elif col == 1:
                return m.rule_applied
            elif col == 2:
                return s.date.strftime("%d-%b-%Y") if s else "-"
            elif col == 3:
                return s.description if s else "-"
            elif col == 4:
                return f"₹ {s.amount:,.2f}" if s else "-"
            elif col == 5:
                return l.date.strftime("%d-%b-%Y") if l else "-"
            elif col == 6:
                return l.description if l else "-"
            elif col == 7:
                return str(l.source_row_ref) if l else "-"
            elif col == 8:
                return f"₹ {l.amount:,.2f}" if l else "-"
            elif col == 9:
                return m.plain_english_reason

        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col in (0, 2, 5, 7):
                return Qt.AlignmentFlag.AlignCenter
            elif col in (4, 8):
                return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter

        return None


class AuditFlagsTableModel(QAbstractTableModel):
    """Table model for expense and compliance audit flags."""

    HEADERS = ["Voucher Ref", "Severity", "Category", "Rule Fired", "Reason & Forensic Risk", "Suggested Action"]

    def __init__(self, flags: Optional[List[AuditFlag]] = None):
        super().__init__()
        self._flags: List[AuditFlag] = flags or []

    def set_data(self, flags: List[AuditFlag]):
        self.beginResetModel()
        self._flags = flags
        self.endResetModel()

    def get_flag(self, row: int) -> Optional[AuditFlag]:
        if 0 <= row < len(self._flags):
            return self._flags[row]
        return None

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._flags)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self.HEADERS)

    def headerData(self, section: int, orientation: Qt.Orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.HEADERS[section]
        return None

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or index.row() >= len(self._flags):
            return None

        f = self._flags[index.row()]
        col = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0:
                return str(f.source_row_ref)
            elif col == 1:
                return f.severity.value
            elif col == 2:
                return f.category.value
            elif col == 3:
                return f.rule_name
            elif col == 4:
                return f.plain_english_reason
            elif col == 5:
                return f.suggested_action

        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col in (0, 1, 2):
                return Qt.AlignmentFlag.AlignCenter
            return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter

        return None
