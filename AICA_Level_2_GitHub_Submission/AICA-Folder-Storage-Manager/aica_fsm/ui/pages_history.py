from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QCheckBox, QLineEdit, QPushButton, QVBoxLayout, QWidget

from .. import export, reports
from .common import error, fill, hbox, info, label, save_path, table


class HistoryPage(QWidget):
    def __init__(self, main):
        super().__init__()
        self.main = main
        self.st = None
        self.items = []
        v = QVBoxLayout(self)
        v.setContentsMargins(16, 14, 16, 14)
        v.addWidget(label("History", "H1"))
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search history (path, action, outcome, error...)")
        self.search.setAccessibleName("History search")
        self.c_scan = QCheckBox("Scans")
        self.c_change = QCheckBox("Detected changes")
        self.c_action = QCheckBox("User actions")
        for c in (self.c_scan, self.c_change, self.c_action):
            c.setChecked(True)
            c.toggled.connect(self.refresh)
        self._t = QTimer(self)
        self._t.setSingleShot(True)
        self._t.setInterval(250)
        self._t.timeout.connect(self.refresh)
        self.search.textChanged.connect(self._t.start)
        b1 = QPushButton("Export this view...")
        b1.clicked.connect(self._export_view)
        b2 = QPushButton("Export action log...")
        b2.clicked.connect(self._export_actions)
        v.addLayout(hbox(self.search, self.c_scan, self.c_change, self.c_action, b1, b2, stretch_end=False))
        self.count = label("", None)
        self.count.setAccessibleDescription("History count")
        v.addWidget(self.count)
        self.t = table(["Time", "Type", "Action", "Source", "Destination", "Outcome / scan", "Detail"], stretch_col=6)
        self.t.setAccessibleName("History table")
        v.addWidget(self.t, 1)

    def clear(self):
        self.st = None
        self.items = []
        self.t.setRowCount(0)
        self.count.setText("")

    def load(self, st):
        self.clear()
        self.st = st
        self.refresh()

    def refresh(self):
        st = self.st
        if not st or not st.db:
            return
        kinds = tuple(k for k, c in (("scan", self.c_scan), ("change", self.c_change), ("action", self.c_action))
                      if c.isChecked())
        self.items = reports.timeline(st.db, self.search.text(), kinds)
        rows = [[(e["time"] or "")[:19].replace("T", " "), e["type"], e["action"], e["source"], e["destination"],
                 e["outcome"], e["detail"]] for e in self.items[:20000]]
        fill(self.t, rows, colors={2: True, 5: True})
        self.count.setText(f"{len(self.items):,} entries for project '{st.project.name}' ({st.project.root_path})")

    def _export_view(self):
        if not self.st:
            return
        path = save_path(self, "Export history", f"{self.st.project.name} - history.xlsx")
        if path:
            try:
                n = export.export_history(self.st.db, self.items, path)
                info(self, "Export", f"Exported {n:,} entries to\n{path}")
            except Exception as e:
                error(self, "Export", str(e))
            self.refresh()

    def _export_actions(self):
        if not self.st:
            return
        path = save_path(self, "Export action log", f"{self.st.project.name} - action log.xlsx")
        if path:
            try:
                n = export.export_actions(self.st.db, path)
                info(self, "Export", f"Exported {n:,} actions to\n{path}")
            except Exception as e:
                error(self, "Export", str(e))
            self.refresh()
