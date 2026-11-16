from __future__ import annotations

from PySide6.QtWidgets import (QComboBox, QLabel, QLineEdit, QPushButton, QSplitter, QTabWidget, QVBoxLayout,
                               QWidget)
from PySide6.QtCore import Qt

from .. import export
from ..paths import now_iso
from ..scanner import accept_incomplete_as_baseline, compare_snapshots
from .common import sel_row, NumItem, ask, date_item, error, fill, hbox, info, label, save_path, size_item, table

KINDS = ["New", "Modified", "Deleted", "Moved", "Possible move", "Unverified"]


class ChangesPage(QWidget):
    def __init__(self, main):
        super().__init__()
        self.main = main
        self.st = None
        self.result = None
        v = QVBoxLayout(self)
        v.setContentsMargins(16, 14, 16, 14)
        v.addWidget(label("Changes", "H1"))
        self.rescan = QPushButton("Re-scan now")
        self.rescan.setObjectName("Primary")
        self.rescan.clicked.connect(lambda: self.main.start_scan(self.main.st.project))
        self.c_from = QComboBox()
        self.c_to = QComboBox()
        self.c_from.setMinimumWidth(220)
        self.c_to.setMinimumWidth(220)
        self.c_from.setAccessibleName("Compare from snapshot")
        self.c_to.setAccessibleName("Compare to snapshot")
        go = QPushButton("Compare")
        go.clicked.connect(self.compare)
        self.b_export = QPushButton("Export change report...")
        self.b_export.clicked.connect(self._export)
        v.addLayout(hbox(self.rescan, QLabel("  From:"), self.c_from, QLabel("To:"), self.c_to, go, self.b_export))
        self.summary = label("", None, wrap=True)
        self.summary.setAccessibleDescription("Changes summary")
        v.addWidget(self.summary)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search changes by path")
        self.search.textChanged.connect(self._render)
        v.addWidget(self.search)

        split = QSplitter(Qt.Vertical)
        top = QWidget()
        tv = QVBoxLayout(top)
        tv.setContentsMargins(0, 0, 0, 0)
        self.tabs = QTabWidget()
        self.tables = {}
        for k in KINDS:
            t = table(["Change", "Old path", "New path", "Old size", "New size", "Old modified", "New modified",
                       "How detected", "Detected (scan)"], stretch_col=None)
            t.setAccessibleName(f"Changes {k}")
            self.tables[k] = t
            self.tabs.addTab(t, k)
        tv.addWidget(self.tabs)
        self.b_confirm = QPushButton("Confirm as moved")
        self.b_reject = QPushButton("Not a move")
        self.b_confirm.clicked.connect(lambda: self._review("Confirmed move"))
        self.b_reject.clicked.connect(lambda: self._review("Rejected - delete + new"))
        self.review_row = hbox(label("Possible moves need your review:", "Hint"), self.b_confirm, self.b_reject)
        tv.addLayout(self.review_row)
        self.unchecked = label("", "Warn", wrap=True)
        self.unchecked.hide()
        tv.addWidget(self.unchecked)
        split.addWidget(top)

        bottom = QWidget()
        bv = QVBoxLayout(bottom)
        bv.setContentsMargins(0, 6, 0, 0)
        self.tl_search = QLineEdit()
        self.tl_search.setPlaceholderText("Search scan timeline")
        self.tl_search.textChanged.connect(self._render_timeline)
        self.b_accept = QPushButton("Accept selected incomplete scan as baseline...")
        self.b_accept.clicked.connect(self._accept)
        self.b_issues = QPushButton("Show locations not checked")
        self.b_issues.clicked.connect(self._show_issues)
        bv.addLayout(hbox(label("Scan timeline", None), self.tl_search, self.b_issues, self.b_accept, stretch_end=False))
        self.timeline = table(["#", "Started", "Finished", "Status", "Baseline", "Files", "Not checked", "Links skipped",
                               "Changes found", "Message", "Snapshot ID"], stretch_col=9)
        self.timeline.setAccessibleName("Scan timeline")
        bv.addWidget(self.timeline)
        split.addWidget(bottom)
        split.setSizes([520, 260])
        v.addWidget(split, 1)

    def clear(self):
        self.st = None
        self.result = None
        self.c_from.clear()
        self.c_to.clear()
        for t in self.tables.values():
            t.setRowCount(0)
        self.timeline.setRowCount(0)
        self.summary.setText("")
        self.unchecked.hide()

    def load(self, st):
        self.clear()
        self.st = st
        if st.db is None:
            return
        scans = [s for s in st.db.scans() if s["status"] in ("Completed", "Incomplete")]
        for c in (self.c_from, self.c_to):
            c.blockSignals(True)
            for s in scans:
                c.addItem(f"#{s['seq']} {(s['finished'] or s['started'])[:19].replace('T', ' ')} {s['status']} "
                          f"({s['files_found']:,} files)", s["scan_id"])
            c.blockSignals(False)
        self._render_timeline()
        if len(scans) >= 2:
            latest = scans[0]
            base = latest["base_scan_id"] or scans[1]["scan_id"]
            self.c_to.setCurrentIndex(0)
            j = self.c_from.findData(base)
            self.c_from.setCurrentIndex(j if j >= 0 else 1)
            self.compare()
        else:
            self.summary.setText("At least two scans of this project are needed to show changes. "
                                 "Use Re-scan after files change.")

    def compare(self):
        st = self.st
        a, b = self.c_from.currentData(), self.c_to.currentData()
        if not st or not a or not b:
            return
        if a == b:
            self.summary.setText("Choose two different snapshots.")
            return
        sa, sb = st.db.scan(a), st.db.scan(b)
        if sa["seq"] > sb["seq"]:
            error(self, "Compare", "'From' must be the older snapshot.")
            return
        self.result = compare_snapshots(st.db, a, b)
        self.sa, self.sb = sa, sb
        self._render()

    def _render(self):
        if not self.result or not self.st:
            return
        reviews = {(r["old_path"], r["new_path"]): r["decision"]
                   for r in self.st.db.con.execute("SELECT * FROM move_reviews")}
        q = self.search.text().lower().strip()
        counts = {}
        detected = (self.sb["finished"] or self.sb["started"])[:19].replace("T", " ")
        for k in KINDS:
            rows = []
            for c in self.result.by_kind(k):
                o, n = c.old, c.new
                if q and q not in ((o.rel_path if o else "") + " " + (n.rel_path if n else "")).lower():
                    continue
                method = c.method
                if k == "Possible move" and (o.rel_path, n.rel_path) in reviews:
                    method += f"  [Reviewed: {reviews[(o.rel_path, n.rel_path)]}]"
                rows.append([k, o.rel_path if o else "", n.rel_path if n else "",
                             size_item(o.size) if o else "", size_item(n.size) if n else "",
                             date_item(o.mtime) if o else "", date_item(n.mtime) if n else "", method,
                             f"#{self.sb['seq']} {detected}"])
            counts[k] = len(rows)
            fill(self.tables[k], rows, colors={0: True})
            self.tabs.setTabText(KINDS.index(k), f"{k} ({len(rows):,})")
        self.summary.setText(
            f"Snapshot #{self.sa['seq']} -> #{self.sb['seq']} ({self.sb['status']}):  " +
            ",  ".join(f"{k}: {counts[k]:,}" for k in KINDS))
        if self.sb["inaccessible_count"]:
            self.unchecked.setText(
                f"{self.sb['inaccessible_count']} location(s) could not be checked in snapshot #{self.sb['seq']}. "
                "Files in those locations are listed as Unverified, not Deleted. Use 'Show locations not checked'.")
            self.unchecked.show()
        else:
            self.unchecked.hide()

    def _render_timeline(self):
        st = self.st
        if not st or not st.db:
            return
        q = self.tl_search.text().lower().strip()
        counts = {r[0]: r[1] for r in st.db.con.execute("SELECT scan_id, COUNT(*) FROM changes GROUP BY scan_id")}
        rows = []
        for s in st.db.scans():
            vals = [NumItem(s["seq"]), (s["started"] or "")[:19].replace("T", " "),
                    (s["finished"] or "")[:19].replace("T", " "), s["status"],
                    "Yes" + (" (accepted)" if s["accepted_manually"] else "") if s["is_baseline"] else "",
                    NumItem(s["files_found"] or 0), NumItem(s["inaccessible_count"] or 0),
                    NumItem(s["links_skipped"] or 0), NumItem(counts.get(s["scan_id"], 0)), s["message"] or "",
                    s["scan_id"]]
            if q and q not in " ".join(str(x.text() if hasattr(x, "text") else x) for x in vals).lower():
                continue
            rows.append(vals)
        fill(self.timeline, rows, colors={3: True})

    def _selected_scan(self):
        r = sel_row(self.timeline)
        return self.timeline.item(r, 10).text() if r >= 0 else None

    def _show_issues(self):
        sid = self._selected_scan() or (self.sb["scan_id"] if self.result else None)
        if not sid:
            return
        from .common import sel_row, ResultsDialog
        rows = [[r["rel_path"] or "(project folder)", r["kind"], r["reason"]] for r in self.st.db.issues(sid)]
        s = self.st.db.scan(sid)
        ResultsDialog(self, "Locations not checked / skipped",
                      f"Scan #{s['seq']} of {self.st.project.name} ({self.st.project.root_path}): {len(rows)} item(s)",
                      rows, ["Relative location", "Kind", "Reason"]).exec()

    def _accept(self):
        sid = self._selected_scan()
        if not sid:
            return
        s = self.st.db.scan(sid)
        if s["status"] != "Incomplete":
            error(self, "Accept", "Select an Incomplete scan in the timeline.")
            return
        if not ask(self, "Accept incomplete scan",
                   f"Scan #{s['seq']} could not check {s['inaccessible_count']} location(s).\n\n"
                   "Accepting it makes it the baseline for future comparisons. Files in the locations that were "
                   "not checked will not be part of the baseline.", yes="Accept as baseline"):
            return
        accept_incomplete_as_baseline(self.st.db, sid)
        self.main._reload_snapshots(select_latest=True)

    def _review(self, decision):
        t = self.tables["Possible move"]
        r = sel_row(t)
        if r < 0:
            info(self, "Review", "Select a possible move first.")
            return
        old, new = t.item(r, 1).text(), t.item(r, 2).text()
        with self.st.db._write_lock:
            self.st.db.con.execute("INSERT OR REPLACE INTO move_reviews VALUES(?,?,?,?)", (old, new, decision, now_iso()))
            self.st.db.con.commit()
        self.st.db.log_action("Review possible move", decision, source=old, destination=new)
        self._render()

    def _export(self):
        if not self.result:
            return
        path = save_path(self, "Export change report",
                         f"{self.st.project.name} - changes #{self.sa['seq']} to #{self.sb['seq']}.xlsx")
        if not path:
            return
        try:
            n = export.export_changes(self.st.db, self.sa["scan_id"], self.sb["scan_id"], path)
        except Exception as e:
            error(self, "Export", str(e))
            return
        info(self, "Export", f"Exported {n:,} changes to\n{path}")
