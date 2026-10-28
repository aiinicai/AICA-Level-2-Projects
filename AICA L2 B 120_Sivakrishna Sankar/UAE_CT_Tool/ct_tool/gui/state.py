"""Application state shared by the pages."""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QObject, Signal

from ..pipeline import Analysis, run_analysis
from ..project import Project


class AppState(QObject):
    analysed = Signal()          # analysis refreshed
    changed = Signal()           # project edited (dirty)
    gate_changed = Signal()      # steps unlocked / locked

    def __init__(self):
        super().__init__()
        self.project: Project = Project()
        self.analysis: Optional[Analysis] = None
        self.path: str = ""
        self.dirty: bool = False
        self.error: str = ""

    def new_project(self):
        self.project = Project()
        self.analysis = None
        self.path = ""
        self.dirty = False
        self.error = ""
        self.analysed.emit()
        self.gate_changed.emit()

    def set_project(self, p: Project, path: str = ""):
        self.project = p
        self.path = path
        self.dirty = False
        self.analysis = None
        self.reanalyse()
        self.gate_changed.emit()

    def mark_dirty(self):
        self.dirty = True
        self.changed.emit()

    def reanalyse(self) -> bool:
        """Re-run the deterministic analysis. Returns False (and keeps the message in .error) when the inputs are not ready."""
        p = self.project
        self.error = ""
        if p.tb is None or not p.fx_confirmed:
            self.analysis = None
            self.analysed.emit()
            return False
        try:
            self.analysis = run_analysis(p)
        except Exception as e:    # noqa: BLE001
            self.analysis = None
            self.error = f"{e}"
        self.analysed.emit()
        return self.analysis is not None

    # gating
    @property
    def fx_ready(self) -> bool:
        return self.project.fx_confirmed

    @property
    def tb_ready(self) -> bool:
        return self.project.tb is not None and self.project.tb_confirmed and self.project.fx_confirmed
