from pathlib import Path
from typing import Dict, List, Optional
from PyQt6.QtCore import QThread, pyqtSignal

from reconai.models.transaction import StatementTransaction, LedgerEntry, MatchRecord, AuditFlag
from reconai.models.session import ReconciliationSession
from reconai.ingest.statement_parser import StatementParser
from reconai.ingest.ledger_parser import LedgerParser
from reconai.reconcile.matcher import Reconciler
from reconai.audit.audit_manager import AuditManager
from reconai.report.report_builder import ReportBuilder


class ParseWorker(QThread):
    """Asynchronous worker for parsing statement and ledger files."""

    finished = pyqtSignal(list, list)  # (statements, ledgers)
    error = pyqtSignal(str)

    def __init__(
        self,
        stmt_path: Optional[str] = None,
        ledger_path: Optional[str] = None,
        ledger_sheet: Optional[str] = None,
        api_key: Optional[str] = None,
        # Backward-compatible
        anthropic_key: Optional[str] = None,
        cached_stmts: Optional[List[StatementTransaction]] = None,
        cached_ledgers: Optional[List[LedgerEntry]] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.stmt_path = stmt_path
        self.ledger_path = ledger_path
        self.ledger_sheet = ledger_sheet
        self.api_key = api_key or anthropic_key
        self.cached_stmts = cached_stmts
        self.cached_ledgers = cached_ledgers

    def run(self):
        try:
            stmts: List[StatementTransaction] = []
            ledgers: List[LedgerEntry] = []

            if self.cached_stmts is not None:
                stmts = self.cached_stmts
            elif self.stmt_path:
                stmt_parser = StatementParser(api_key=self.api_key)
                raw_paths = [p.strip() for p in self.stmt_path.split(";") if p.strip()] if isinstance(self.stmt_path, str) else self.stmt_path
                for p in raw_paths:
                    parsed_sub = stmt_parser.parse(p)
                    stmts.extend(parsed_sub)
                stmts.sort(key=lambda x: x.date)

            if self.cached_ledgers is not None:
                ledgers = self.cached_ledgers
            elif self.ledger_path:
                ledger_parser = LedgerParser()
                raw_l_paths = [p.strip() for p in self.ledger_path.split(";") if p.strip()] if isinstance(self.ledger_path, str) else self.ledger_path
                for p in raw_l_paths:
                    parsed_l = ledger_parser.parse(p, sheet_name=self.ledger_sheet)
                    ledgers.extend(parsed_l)
                ledgers.sort(key=lambda x: x.date)

            self.finished.emit(stmts, ledgers)
        except Exception as e:
            self.error.emit(str(e))


class ReconcileWorker(QThread):
    """Asynchronous worker for running multi-pass reconciliation."""

    finished = pyqtSignal(list)  # list of MatchRecord
    error = pyqtSignal(str)

    def __init__(self, session: ReconciliationSession, parent=None):
        super().__init__(parent)
        self.session = session

    def run(self):
        try:
            reconciler = Reconciler(self.session.config.reconciliation)
            matches = reconciler.reconcile(
                self.session.statements, self.session.ledger_entries
            )
            self.finished.emit(matches)
        except Exception as e:
            self.error.emit(str(e))


class AuditWorker(QThread):
    """Asynchronous worker for running deterministic and AI audit checks."""

    finished = pyqtSignal(list)  # list of AuditFlag
    error = pyqtSignal(str)

    def __init__(self, session: ReconciliationSession, parent=None):
        super().__init__(parent)
        self.session = session

    def run(self):
        try:
            manager = AuditManager(self.session.config)
            flags = manager.run_audit(self.session.ledger_entries)
            self.finished.emit(flags)
        except Exception as e:
            self.error.emit(str(e))


class ExportWorker(QThread):
    """Asynchronous worker for generating Excel and PDF reports."""

    finished = pyqtSignal(dict)  # {"excel": path, "pdf": path}
    error = pyqtSignal(str)

    def __init__(self, session: ReconciliationSession, base_output_path: str, parent=None):
        super().__init__(parent)
        self.session = session
        self.base_output_path = base_output_path

    def run(self):
        try:
            builder = ReportBuilder()
            results = builder.export_all(self.session, self.base_output_path)
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))
