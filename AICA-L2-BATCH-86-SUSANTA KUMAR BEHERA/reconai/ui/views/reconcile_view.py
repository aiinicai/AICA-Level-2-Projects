from decimal import Decimal
from typing import Dict, List, Optional
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QTableView,
    QHeaderView,
    QPushButton,
    QLabel,
    QMessageBox,
    QInputDialog,
    QSplitter,
    QFrame,
    QLineEdit,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QUndoStack

from reconai.models.session import ReconciliationSession
from reconai.models.transaction import (
    StatementTransaction,
    LedgerEntry,
    MatchRecord,
    MatchStatus,
)
from reconai.ui.components.stat_card import StatCard
from reconai.ui.components.table_models import (
    MatchedRecordsTableModel,
    StatementTableModel,
    LedgerTableModel,
)
from reconai.ui.components.undo_commands import MatchOverrideCommand


class ReconcileView(QWidget):
    """Reconciliation management view with tabbed match buckets, manual override, and Undo/Redo."""

    matches_changed = pyqtSignal()

    def __init__(self, session: ReconciliationSession, undo_stack: QUndoStack, parent=None):
        super().__init__(parent)
        self.session = session
        self.undo_stack = undo_stack

        self.matched_model = MatchedRecordsTableModel()
        self.probable_model = MatchedRecordsTableModel()
        self.unmatched_stmt_model = StatementTableModel()
        self.unmatched_ledger_model = LedgerTableModel()

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 1. Summary KPI Cards Bar
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(12)

        self.card_matched = StatCard("Matched Pairs", "0", "₹ 0.00 Reconciled")
        self.card_probable = StatCard("Probable Matches", "0", "Requires confirmation")
        self.card_unmatched_stmt = StatCard("Unmatched Bank", "0", "Timing / Bank Charges")
        self.card_unmatched_ledger = StatCard("Unmatched Books", "0", "Unpresented / Uncredited")

        cards_layout.addWidget(self.card_matched)
        cards_layout.addWidget(self.card_probable)
        cards_layout.addWidget(self.card_unmatched_stmt)
        cards_layout.addWidget(self.card_unmatched_ledger)
        layout.addLayout(cards_layout)

        # 2. Action Toolbar (Undo, Redo, Confirm Match, Unpair, Manual Pair)
        toolbar = QHBoxLayout()

        self.undo_btn = self.undo_stack.createUndoAction(self, "Undo")
        self.redo_btn = self.undo_stack.createRedoAction(self, "Redo")

        btn_undo = QPushButton("⟲ Undo Override")
        btn_undo.setObjectName("secondaryBtn")
        btn_undo.clicked.connect(self.undo_stack.undo)

        btn_redo = QPushButton("⟳ Redo Override")
        btn_redo.setObjectName("secondaryBtn")
        btn_redo.clicked.connect(self.undo_stack.redo)

        self.confirm_btn = QPushButton("✓ Confirm Match")
        self.confirm_btn.setObjectName("successBtn")
        self.confirm_btn.clicked.connect(self._confirm_selected_probable)

        self.unpair_btn = QPushButton("✕ Unpair / Mark Unmatched")
        self.unpair_btn.setObjectName("dangerBtn")
        self.unpair_btn.clicked.connect(self._unpair_selected)

        self.manual_pair_btn = QPushButton("🔗 Manual Pair Selected Rows")
        self.manual_pair_btn.setObjectName("secondaryBtn")
        self.manual_pair_btn.clicked.connect(self._manual_pair_unmatched)

        toolbar.addWidget(btn_undo)
        toolbar.addWidget(btn_redo)
        toolbar.addSpacing(15)
        toolbar.addWidget(self.confirm_btn)
        toolbar.addWidget(self.unpair_btn)
        toolbar.addWidget(self.manual_pair_btn)
        toolbar.addStretch()

        layout.addLayout(toolbar)

        # 3. Main Tabbed Table View
        self.tabs = QTabWidget()

        # Tab 1: Matched
        self.matched_table = QTableView()
        self.matched_table.setModel(self.matched_model)
        self.matched_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.matched_table.horizontalHeader().setStretchLastSection(True)
        self.tabs.addTab(self.matched_table, "Matched (0)")

        # Tab 2: Probable
        self.probable_table = QTableView()
        self.probable_table.setModel(self.probable_model)
        self.probable_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.probable_table.horizontalHeader().setStretchLastSection(True)
        self.tabs.addTab(self.probable_table, "Probable Matches (0)")

        # Tab 3: Unmatched Bank Statements
        self.unmatched_stmt_table = QTableView()
        self.unmatched_stmt_table.setModel(self.unmatched_stmt_model)
        self.unmatched_stmt_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.unmatched_stmt_table.horizontalHeader().setStretchLastSection(True)
        self.tabs.addTab(self.unmatched_stmt_table, "Unmatched Bank Statement (0)")

        # Tab 4: Unmatched Client Books
        self.unmatched_ledger_table = QTableView()
        self.unmatched_ledger_table.setModel(self.unmatched_ledger_model)
        self.unmatched_ledger_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.unmatched_ledger_table.horizontalHeader().setStretchLastSection(True)
        self.tabs.addTab(self.unmatched_ledger_table, "Unmatched Client Books (0)")

        layout.addWidget(self.tabs, 1)

    def refresh_data(self):
        """Update tables, tab counters, and KPI cards."""
        stmt_map = {}
        for s in self.session.statements:
            stmt_map[s.id] = s
            stmt_map[str(s.id)] = s
            stmt_map[str(s.source_row_ref)] = s

        ledger_map = {}
        for l in self.session.ledger_entries:
            ledger_map[l.id] = l
            ledger_map[str(l.id)] = l
            ledger_map[str(l.source_row_ref)] = l

        matched = [m for m in self.session.matches if m.status == MatchStatus.MATCHED]
        probable = [m for m in self.session.matches if m.status == MatchStatus.PROBABLE]
        
        # Unmatched objects
        unmatched_stmts = [s for s in self.session.statements if not s.matched]
        unmatched_ledgers = [l for l in self.session.ledger_entries if not l.matched]

        self.matched_model.set_data(matched, stmt_map, ledger_map)
        self.probable_model.set_data(probable, stmt_map, ledger_map)
        self.unmatched_stmt_model.set_data(unmatched_stmts)
        self.unmatched_ledger_model.set_data(unmatched_ledgers)

        # Set readable column widths
        for table in (self.matched_table, self.probable_table):
            table.setColumnWidth(0, 65)
            table.setColumnWidth(1, 140)
            table.setColumnWidth(2, 95)
            table.setColumnWidth(3, 240)
            table.setColumnWidth(4, 110)
            table.setColumnWidth(5, 95)
            table.setColumnWidth(6, 240)
            table.setColumnWidth(7, 75)
            table.setColumnWidth(8, 110)

        # Tab labels
        self.tabs.setTabText(0, f"Matched ({len(matched)})")
        self.tabs.setTabText(1, f"Probable Matches ({len(probable)})")
        self.tabs.setTabText(2, f"Unmatched Bank ({len(unmatched_stmts)})")
        self.tabs.setTabText(3, f"Unmatched Books ({len(unmatched_ledgers)})")

        # KPI amounts
        matched_amt = sum([stmt_map[m.statement_tx_id].amount for m in matched if m.statement_tx_id in stmt_map], Decimal("0.00"))
        probable_amt = sum([stmt_map[m.statement_tx_id].amount for m in probable if m.statement_tx_id in stmt_map], Decimal("0.00"))
        unmatched_stmt_amt = sum([s.amount for s in unmatched_stmts], Decimal("0.00"))
        unmatched_ledger_amt = sum([l.amount for l in unmatched_ledgers], Decimal("0.00"))

        self.card_matched.set_value(str(len(matched)), f"₹ {matched_amt:,.2f} Reconciled")
        self.card_probable.set_value(str(len(probable)), f"₹ {probable_amt:,.2f} under review")
        self.card_unmatched_stmt.set_value(str(len(unmatched_stmts)), f"₹ {unmatched_stmt_amt:,.2f} outstanding")
        self.card_unmatched_ledger.set_value(str(len(unmatched_ledgers)), f"₹ {unmatched_ledger_amt:,.2f} unpresented")

    def _confirm_selected_probable(self):
        current_tab = self.tabs.currentIndex()
        if current_tab != 1:
            QMessageBox.information(self, "Select Probable Match", "Please select a record from the 'Probable Matches' tab.")
            return

        selected_indexes = self.probable_table.selectionModel().selectedRows()
        if not selected_indexes:
            QMessageBox.information(self, "No Selection", "Please select a probable match row to confirm.")
            return

        row = selected_indexes[0].row()
        match_rec = self.probable_model.get_record(row)
        if not match_rec:
            return

        previous_matches = [m.model_copy() for m in self.session.matches]
        new_matches = [m.model_copy() for m in self.session.matches]

        for m in new_matches:
            if m.id == match_rec.id:
                m.status = MatchStatus.MATCHED
                m.confidence_score = 1.0
                m.rule_applied = "MANUALLY_CONFIRMED"
                m.manual_override = True
                m.plain_english_reason = "Manually confirmed by auditor as correct match."

        cmd = MatchOverrideCommand(
            session=self.session,
            action_name=f"Confirm Match for ₹{match_rec.confidence_score}",
            new_matches=new_matches,
            previous_matches=previous_matches,
            on_change_callback=self._on_override_executed,
        )
        self.undo_stack.push(cmd)

    def _unpair_selected(self):
        current_tab = self.tabs.currentIndex()
        table = self.matched_table if current_tab == 0 else self.probable_table if current_tab == 1 else None
        model = self.matched_model if current_tab == 0 else self.probable_model if current_tab == 1 else None

        if not table or not model:
            QMessageBox.information(self, "Invalid Selection", "Select a match from either 'Matched' or 'Probable Matches' tab to unpair.")
            return

        selected_indexes = table.selectionModel().selectedRows()
        if not selected_indexes:
            QMessageBox.information(self, "No Selection", "Please select a row to unpair.")
            return

        row = selected_indexes[0].row()
        match_rec = model.get_record(row)
        if not match_rec:
            return

        previous_matches = [m.model_copy() for m in self.session.matches]
        new_matches = [m for m in self.session.matches if m.id != match_rec.id]

        # Add explicit unmatched records for the uncoupled items
        if match_rec.statement_tx_id:
            new_matches.append(
                MatchRecord(
                    statement_tx_id=match_rec.statement_tx_id,
                    ledger_entry_id=None,
                    status=MatchStatus.UNMATCHED,
                    confidence_score=0.0,
                    rule_applied="MANUAL_UNPAIR_OVERRIDE",
                    plain_english_reason="Manually uncoupled by auditor.",
                    manual_override=True,
                )
            )
        if match_rec.ledger_entry_id:
            new_matches.append(
                MatchRecord(
                    statement_tx_id=None,
                    ledger_entry_id=match_rec.ledger_entry_id,
                    status=MatchStatus.UNMATCHED,
                    confidence_score=0.0,
                    rule_applied="MANUAL_UNPAIR_OVERRIDE",
                    plain_english_reason="Manually uncoupled by auditor.",
                    manual_override=True,
                )
            )

        cmd = MatchOverrideCommand(
            session=self.session,
            action_name="Unpair Match",
            new_matches=new_matches,
            previous_matches=previous_matches,
            on_change_callback=self._on_override_executed,
        )
        self.undo_stack.push(cmd)

    def _manual_pair_unmatched(self):
        stmt_indexes = self.unmatched_stmt_table.selectionModel().selectedRows()
        ledger_indexes = self.unmatched_ledger_table.selectionModel().selectedRows()

        unmatched_stmts = [s for s in self.session.statements if not s.matched]
        unmatched_ledgers = [l for l in self.session.ledger_entries if not l.matched]

        if not stmt_indexes or not ledger_indexes:
            QMessageBox.information(
                self,
                "Selection Required",
                "To manually pair: Select 1 row in 'Unmatched Bank' tab and 1 row in 'Unmatched Books' tab.",
            )
            return

        stmt_row = stmt_indexes[0].row()
        ledger_row = ledger_indexes[0].row()

        if stmt_row >= len(unmatched_stmts) or ledger_row >= len(unmatched_ledgers):
            return

        s = unmatched_stmts[stmt_row]
        l = unmatched_ledgers[ledger_row]

        note, ok = QInputDialog.getText(
            self,
            "Manual Pair Confirmation",
            f"Pair Statement (₹{s.amount:,.2f}, {s.date}) with Ledger (₹{l.amount:,.2f}, {l.date})?\nEnter auditor justification / note:",
        )
        if not ok:
            return

        previous_matches = [m.model_copy() for m in self.session.matches]
        # Remove any existing unmatched records for these two
        new_matches = [
            m for m in self.session.matches
            if not (m.statement_tx_id == s.id and m.ledger_entry_id is None)
            and not (m.ledger_entry_id == l.id and m.statement_tx_id is None)
        ]

        # Add the new manual match
        new_matches.append(
            MatchRecord(
                statement_tx_id=s.id,
                ledger_entry_id=l.id,
                status=MatchStatus.MATCHED,
                confidence_score=1.0,
                rule_applied="MANUAL_PAIR_BY_AUDITOR",
                plain_english_reason=f"Manually paired by auditor. Note: {note or 'Confirmed correct pair.'}",
                manual_override=True,
                notes=note,
            )
        )

        cmd = MatchOverrideCommand(
            session=self.session,
            action_name=f"Manual Pair: {s.description[:20]} <-> {l.description[:20]}",
            new_matches=new_matches,
            previous_matches=previous_matches,
            on_change_callback=self._on_override_executed,
        )
        self.undo_stack.push(cmd)

    def _on_override_executed(self):
        self.refresh_data()
        self.matches_changed.emit()
