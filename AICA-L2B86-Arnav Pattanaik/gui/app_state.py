"""
Shared application state for the desktop GUI.

Mirrors the AI Studio UI's App.tsx top-level state (CompilationState,
uploaded files, compiled dataset, settings) so the screen-to-screen data
flow matches the original design: Screen 1 populates this, Screens 2-4
read from it.
"""

from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd

from core.ingestion import FileIngestSpec, DivisionLoadLog


@dataclass
class UploadedFileEntry:
    file_path: str
    file_name: str
    detected_division: str
    detected_header_row: int
    header_confidence: str
    row_count: int = 0
    status: str = "Pending"  # Pending | Compiling | Compiled | Error
    error_message: str = ""


@dataclass
class AppSettings:
    default_electricity_duty_rate: float = 0.0
    default_dps_rate: float = 1.0
    audit_firm_name: str = "SRB & Associates, Chartered Accountants"
    discom_name: str = ""
    theme_name: str = "Dark"


class AppState:
    """
    Single shared mutable state object passed to every screen widget.
    Not a dataclass because PyQt widgets need to mutate and react to this
    live (e.g. via simple callbacks), rather than immutable state updates.
    """

    def __init__(self):
        self.billing_month: str = "August"
        self.billing_year: int = 2026

        self.uploaded_files: list[UploadedFileEntry] = []
        self.load_logs: list[DivisionLoadLog] = []

        self.compiled_df: pd.DataFrame | None = None
        self.is_compiled: bool = False
        self.compile_timestamp: str | None = None
        self.total_rows_read: int = 0
        self.total_rows_rejected: int = 0
        self.has_warnings_or_errors: bool = False
        self.warnings_acknowledged: bool = False

        self.settings = AppSettings()

        # Simple observer pattern: screens can subscribe to be notified when
        # compilation state changes (e.g. sidebar needs to unlock screens 2-4)
        self._listeners: list = []

    def on_change(self, callback):
        self._listeners.append(callback)

    def notify(self):
        for cb in self._listeners:
            cb()

    def reset_compilation(self):
        self.uploaded_files = []
        self.load_logs = []
        self.compiled_df = None
        self.is_compiled = False
        self.compile_timestamp = None
        self.total_rows_read = 0
        self.total_rows_rejected = 0
        self.has_warnings_or_errors = False
        self.warnings_acknowledged = False
        self.notify()

    def mark_compiled(self, compiled_df, load_logs, total_read, total_rejected, has_warnings):
        self.compiled_df = compiled_df
        self.load_logs = load_logs
        self.is_compiled = True
        self.compile_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.total_rows_read = total_read
        self.total_rows_rejected = total_rejected
        self.has_warnings_or_errors = has_warnings

        # Auto-save session cache
        try:
            from core.session_manager import save_session
            save_session(self)
        except Exception:
            pass

        self.notify()

    @property
    def total_divisions_compiled(self) -> int:
        return len({log.division for log in self.load_logs if log.rows_read > 0})

    @property
    def screens_unlocked(self) -> bool:
        return self.is_compiled and (not self.has_warnings_or_errors or self.warnings_acknowledged)
