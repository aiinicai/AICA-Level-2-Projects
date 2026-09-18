from typing import Callable, List, Optional
from PyQt6.QtGui import QUndoCommand

from reconai.models.transaction import MatchRecord, MatchStatus, StatementTransaction, LedgerEntry
from reconai.models.session import ReconciliationSession


class MatchOverrideCommand(QUndoCommand):
    """Undoable command for manually pairing, unpairing, or overriding matches."""

    def __init__(
        self,
        session: ReconciliationSession,
        action_name: str,
        new_matches: List[MatchRecord],
        previous_matches: List[MatchRecord],
        on_change_callback: Optional[Callable[[], None]] = None,
        parent=None,
    ):
        super().__init__(action_name, parent)
        self.session = session
        self.new_matches = [m.model_copy() for m in new_matches]
        self.previous_matches = [m.model_copy() for m in previous_matches]
        self.callback = on_change_callback

    def redo(self):
        self.session.matches = [m.model_copy() for m in self.new_matches]
        self._update_matched_flags()
        self.session.log_event("MANUAL_MATCH_OVERRIDE", f"Executed: {self.text()}")
        if self.callback:
            self.callback()

    def undo(self):
        self.session.matches = [m.model_copy() for m in self.previous_matches]
        self._update_matched_flags()
        self.session.log_event("UNDO_MATCH_OVERRIDE", f"Undone: {self.text()}")
        if self.callback:
            self.callback()

    def _update_matched_flags(self):
        matched_stmt_ids = {m.statement_tx_id for m in self.session.matches if m.status in (MatchStatus.MATCHED, MatchStatus.PROBABLE) and m.statement_tx_id}
        matched_ledger_ids = {m.ledger_entry_id for m in self.session.matches if m.status in (MatchStatus.MATCHED, MatchStatus.PROBABLE) and m.ledger_entry_id}

        for s in self.session.statements:
            s.matched = s.id in matched_stmt_ids
        for l in self.session.ledger_entries:
            l.matched = l.id in matched_ledger_ids
