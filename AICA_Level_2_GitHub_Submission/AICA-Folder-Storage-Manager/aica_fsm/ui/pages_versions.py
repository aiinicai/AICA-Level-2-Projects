from __future__ import annotations

import html
import json
import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QGridLayout, QLabel, QLineEdit, QPushButton, QScrollArea, QSplitter, QTextEdit,
                               QVBoxLayout, QWidget)

from .. import versions
from ..paths import human_size, ts_to_iso
from ..store import ProjectDB
from ..textextract import IMAGE_EXTS, cached_extract
from .common import sel_row, error, fill, hbox, label, open_containing, run_with_progress, table


class VersionsPage(QWidget):
    def __init__(self, main):
        super().__init__()
        self.main = main
        self.st = None
        self.pairs = []
        v = QVBoxLayout(self)
        v.setContentsMargins(16, 14, 16, 14)
        v.addWidget(label("Compare versions & similar files", "H1"))
        v.addWidget(label("Possible versions found by file-name patterns, extracted text similarity (PDF, Word, text) "
                          "and visual similarity (images). These are NOT exact duplicates - nothing can be deleted here. "
                          "Older/newer labels are candidates based on the evidence shown.", "Hint", wrap=True))
        self.b_run = QPushButton("Analyse this snapshot")
        self.b_run.setObjectName("Primary")
        self.b_run.clicked.connect(self._analyse)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Filter by path")
        self.search.textChanged.connect(self._render)
        self.summary = label("", None)
        self.summary.setAccessibleDescription("Versions summary")
        v.addLayout(hbox(self.b_run, self.summary, None, self.search, stretch_end=False))
        split = QSplitter(Qt.Vertical)
        self.t = table(["File A", "File B", "Why suggested", "Similarity", "Older (candidate)", "Order evidence"],
                       stretch_col=2)
        self.t.setAccessibleName("Version pairs")
        self.t.itemSelectionChanged.connect(self._show_pair)
        split.addWidget(self.t)
        cmp = QWidget()
        g = QGridLayout(cmp)
        g.setContentsMargins(0, 6, 0, 0)
        self.hdr = [label("", None, wrap=True), label("", None, wrap=True)]
        self.order = label("", "Warn", wrap=True)
        g.addWidget(self.order, 0, 0, 1, 2)
        g.addWidget(self.hdr[0], 1, 0)
        g.addWidget(self.hdr[1], 1, 1)
        self.img = [QLabel(), QLabel()]
        self.sc = []
        for i, im in enumerate(self.img):
            im.setAlignment(Qt.AlignCenter)
            sa = QScrollArea()
            sa.setWidget(im)
            sa.setWidgetResizable(True)
            self.sc.append(sa)
            g.addWidget(sa, 2, i)
        self.diff = QTextEdit()
        self.diff.setReadOnly(True)
        self.diff.setAccessibleName("Text differences")
        g.addWidget(self.diff, 3, 0, 1, 2)
        b_oa = QPushButton("Open folder of A")
        b_ob = QPushButton("Open folder of B")
        b_oa.clicked.connect(lambda: self._open(0))
        b_ob.clicked.connect(lambda: self._open(1))
        g.addLayout(hbox(b_oa, b_ob), 4, 0, 1, 2)
        split.addWidget(cmp)
        split.setSizes([300, 480])
        v.addWidget(split, 1)
        self._sel = None

    def clear(self):
        self.st = None
        self.pairs = []
        self.t.setRowCount(0)
        self.summary.setText("")
        self._clear_compare()

    def _clear_compare(self):
        for h in self.hdr:
            h.setText("")
        for i in self.img:
            i.clear()
        self.diff.clear()
        self.order.setText("Select a pair to compare side by side.")
        for s in self.sc:
            s.hide()

    def load(self, st):
        self.clear()
        self.st = st
        if st.db is None or not st.snapshot_id:
            self.summary.setText("No completed snapshot")
            self.b_run.setEnabled(False)
            return
        self.b_run.setEnabled(True)
        self.pairs = versions.pairs_for(st.db, st.snapshot_id)
        if not self.pairs:
            self.summary.setText("Not analysed yet for this snapshot (or no candidates). Click 'Analyse this snapshot'.")
        self._render()

    def _render(self):
        q = self.search.text().lower().strip()
        rows = []
        self.visible = []
        for p in self.pairs:
            if q and q not in (p["path_a"] + " " + p["path_b"]).lower():
                continue
            self.visible.append(p)
            reasons = "; ".join(json.loads(p["reasons"] or "[]"))
            rows.append([p["path_a"], p["path_b"], reasons, f"{(p['score'] or 0):.0%}",
                         p["older"] or "Order uncertain",
                         ("" if p["order_certain"] else "UNCERTAIN - ") + (p["order_note"] or "")])
        fill(self.t, rows)
        self.t.setSortingEnabled(False)
        if self.pairs:
            self.summary.setText(f"{len(self.pairs):,} candidate pair(s) in snapshot #{self.st.snapshot['seq']}")

    def _analyse(self):
        st = self.st
        project, sid = st.project, st.snapshot_id

        def work(cancel, prog):
            db = ProjectDB.open(project)
            try:
                return versions.analyse(db, sid, progress=prog, cancel=cancel)
            finally:
                db.close()

        ok, res = run_with_progress(self, project.project_id, "Analysing versions (reading documents, OCR, images)", work)
        if not ok:
            error(self, "Analyse", str(res))
        if self.main.st.project and self.main.st.project.project_id == project.project_id:
            self.load(self.main.st)

    def _open(self, i):
        if self._sel:
            open_containing(os.path.join(self.st.project.root_path, self._sel[i]))

    def _show_pair(self):
        r = sel_row(self.t)
        if r < 0 or r >= len(self.visible):
            return
        p = self.visible[r]
        root = self.st.project.root_path
        paths = [p["path_a"], p["path_b"]]
        self._sel = paths
        snap = self.st.snapshot_id
        for i, rp in enumerate(paths):
            meta = self.st.db.con.execute("SELECT size, mtime FROM files WHERE scan_id=? AND rel_path=?",
                                          (snap, rp)).fetchone()
            full = os.path.join(root, rp)
            avail = os.path.isfile(full)
            role = ""
            if p["older"]:
                role = ("OLDER candidate" if p["older"] == rp else "NEWER candidate")
                if not p["order_certain"]:
                    role += " (uncertain)"
            else:
                role = "Order uncertain"
            dt = self.st.db.con.execute("SELECT doc_modified FROM doc_text WHERE rel_path=?", (rp,)).fetchone()
            self.hdr[i].setText(
                f"<b>{'AB'[i]}: {html.escape(role)}</b><br>{html.escape(full)}<br>"
                f"Size {human_size(meta['size']) if meta else '?'} &nbsp; Modified {ts_to_iso(meta['mtime']) if meta else '?'}"
                + (f" &nbsp; Document date {dt['doc_modified']}" if dt and dt["doc_modified"] else "")
                + ("" if avail else "<br><span style='color:#b91c1c'><b>Content unavailable</b> - the file is no "
                                    "longer at this path. Only the saved metadata is shown.</span>"))
        self.order.setText(("Order: " if p["order_certain"] else "Order UNCERTAIN: ") + (p["order_note"] or ""))
        ext = os.path.splitext(paths[0])[1].lower().lstrip(".")
        self.diff.clear()
        for s in self.sc:
            s.hide()
        if ext in IMAGE_EXTS:
            for i, rp in enumerate(paths):
                full = os.path.join(root, rp)
                if os.path.isfile(full):
                    pm = QPixmap(full)
                    if not pm.isNull():
                        self.img[i].setPixmap(pm.scaled(560, 380, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                    else:
                        self.img[i].setText("Preview not available")
                else:
                    self.img[i].setText("Content unavailable")
                self.sc[i].show()
            self.diff.setPlainText("Image pair: compare the previews above.")
            return
        texts = []
        for rp in paths:
            full = os.path.join(root, rp)
            if not os.path.isfile(full):
                texts.append(None)
                continue
            try:
                texts.append(cached_extract(self.st.db, rp).text)
            except Exception:
                texts.append(None)
        if None in texts:
            self.diff.setHtml("<p style='color:#b91c1c'><b>Content unavailable</b> for at least one file "
                              "(no longer available or not readable). Text differences cannot be shown.</p>")
            return
        if not any(t.strip() for t in texts):
            self.diff.setPlainText("No extractable text for this file type.")
            return
        out = ["<pre style='font-family:Consolas;font-size:9pt'>"]
        for tag, line in versions.text_diff(texts[0], texts[1]):
            esc = html.escape(line)
            if tag == "-":
                out.append(f"<span style='background:#fde2e2'>- A: {esc}</span>")
            elif tag == "+":
                out.append(f"<span style='background:#dcfce7'>+ B: {esc}</span>")
            else:
                out.append(f"   {esc}")
        out.append("</pre>")
        self.diff.setHtml("\n".join(out))
