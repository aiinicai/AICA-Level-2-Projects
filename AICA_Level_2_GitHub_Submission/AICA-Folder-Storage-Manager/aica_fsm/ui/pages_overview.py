from __future__ import annotations

from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QPushButton, QScrollArea, QVBoxLayout, QWidget

from .. import reports
from ..paths import human_size
from .common import NumItem, card, date_item, fill, label, size_item, table


class OverviewPage(QWidget):
    def __init__(self, main):
        super().__init__()
        self.main = main
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 14, 16, 14)
        self.title = label("Overview", "H1")
        outer.addWidget(self.title)
        self.banner = label("", "Warn", wrap=True)
        self.banner.setAccessibleDescription("Overview notice")
        self.banner.hide()
        outer.addWidget(self.banner)
        self.empty = QWidget()
        ev = QVBoxLayout(self.empty)
        self.empty_text = label("This project has no completed scan yet.", "H1", wrap=True)
        self.empty_text.setAccessibleDescription("Overview empty state")
        ev.addWidget(self.empty_text)
        self.empty_btn = QPushButton("Scan now")
        self.empty_btn.setObjectName("Primary")
        self.empty_btn.clicked.connect(lambda: self.main.start_scan(self.main.st.project))
        ev.addWidget(self.empty_btn)
        ev.addStretch(1)
        outer.addWidget(self.empty)

        self.body = QWidget()
        b = QVBoxLayout(self.body)
        b.setContentsMargins(0, 0, 0, 0)
        grid = QGridLayout()
        self.cards = {}
        specs = [("files", "Files", "Overview file count"), ("size", "Total size", "Overview total size"),
                 ("groups", "Duplicate groups (verified)", "Overview duplicate groups"),
                 ("recover", "Recoverable from extra copies", "Overview recoverable"),
                 ("issues", "Locations not checked", "Overview inaccessible"),
                 ("snap", "Snapshot", "Overview snapshot")]
        for i, (k, t, acc) in enumerate(specs):
            f, val = card(t, "-", acc)
            self.cards[k] = val
            grid.addWidget(f, i // 3, i % 3)
        b.addLayout(grid)
        row = QHBoxLayout()
        self.t_folder = table(["Top-level folder", "Files", "Size"], stretch_col=0)
        self.t_type = table(["File type", "Files", "Size"], stretch_col=0)
        self.t_cat = table(["Category", "Files", "Size"], stretch_col=0)
        for t, h in ((self.t_folder, "Storage by folder"), (self.t_type, "Storage by file type"),
                     (self.t_cat, "Storage by category")):
            c = QVBoxLayout()
            c.addWidget(label(h, None))
            c.addWidget(t)
            row.addLayout(c)
        b.addLayout(row, 2)
        b.addWidget(label("Largest files", None))
        self.t_large = table(["Relative path", "Size", "Modified"], stretch_col=0)
        b.addWidget(self.t_large, 2)
        outer.addWidget(self.body, 1)
        self.clear()

    def clear(self):
        self.body.hide()
        self.banner.hide()
        self.empty.show()
        for t in (self.t_folder, self.t_type, self.t_cat, self.t_large):
            t.setRowCount(0)
        for v in self.cards.values():
            v.setText("-")

    def load(self, st):
        self.clear()
        if st.db is None:
            self.empty_text.setText("No project open.")
            self.empty_btn.hide()
            return
        self.empty_btn.show()
        scans = st.db.scans()
        latest = scans[0] if scans else None
        if latest and latest["status"] != "Completed" and latest["scan_id"] != st.snapshot_id and latest["status"] != "Running":
            self.banner.setText(f"Latest scan #{latest['seq']} is {latest['status'].upper()}"
                                f"{' - ' + latest['message'] if latest['message'] else ''}. "
                                f"The results below are from the selected completed snapshot.")
            self.banner.show()
        if not st.snapshot_id:
            self.empty_text.setText(f"Project '{st.project.name}' has no completed scan yet.\n{st.project.root_path}")
            return
        o = reports.overview(st.db, st.snapshot_id)
        s = o["scan"]
        self.empty.hide()
        self.body.show()
        self.cards["files"].setText(f"{o['count']:,}")
        self.cards["size"].setText(human_size(o["total"]))
        self.cards["groups"].setText(f"{o['dup_groups']:,}  ({o['dup_files']:,} files)")
        self.cards["recover"].setText(human_size(o["recoverable"]))
        self.cards["issues"].setText(f"{o['issues']:,}")
        self.cards["snap"].setText(f"#{s['seq']} {s['status']}")
        self.cards["snap"].setToolTip(f"Snapshot {s['scan_id']}\nStarted {s['started']}\nFinished {s['finished']}")
        fill(self.t_folder, [[k, NumItem(n), size_item(sz)] for k, n, sz in o["by_folder"]])
        fill(self.t_type, [[k, NumItem(n), size_item(sz)] for k, n, sz in o["by_type"]])
        fill(self.t_cat, [[k, NumItem(n), size_item(sz)] for k, n, sz in o["by_category"]])
        fill(self.t_large, [[r["rel_path"], size_item(r["size"]), date_item(r["mtime"])] for r in o["largest"]])
