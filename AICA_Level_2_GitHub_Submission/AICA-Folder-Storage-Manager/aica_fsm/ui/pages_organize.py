from __future__ import annotations

import json
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QFormLayout, QGroupBox, QLineEdit, QPushButton,
                               QSplitter, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget)

from .. import actions, organize
from ..store import ProjectDB
from .common import sel_row
from .common import (ResultsDialog, ask, error, fill, hbox, info, label, open_path, pick_folder, run_with_progress,
                     table)

STATUSES = ["", "Detected", "Several names", "Suggestion", "Manual review", "Name confirmed", "Skipped", "Moved",
            "Move failed"]


class MoveReviewDialog(QDialog):
    """Exact source -> destination for every selected file; conflicts must be resolved here."""

    def __init__(self, parent, project, pre):
        super().__init__(parent)
        self.pre = pre
        self.setWindowTitle("Review moves - " + project.name)
        self.resize(1250, 600)
        v = QVBoxLayout(self)
        v.addWidget(label(f"Project: {project.name}     Scan path: {project.root_path}", "H1", wrap=True))
        v.addWidget(label("Only the files listed with 'Will move' are moved. Existing files are never overwritten. "
                          "Moves to another drive or share are copied, verified (SHA-256) and only then removed "
                          "from the source.", "Hint", wrap=True))
        self.t = table(["Source (full path)", "Destination (full path)", "Status", "If name exists"], stretch_col=None,
                       sortable=False)
        self.t.setAccessibleName("Move review table")
        self.t.setRowCount(len(pre))
        self.combos = {}
        for r, p in enumerate(pre):
            self.t.setItem(r, 0, QTableWidgetItem(p["source"]))
            self.t.setItem(r, 1, QTableWidgetItem(p["destination"]))
            if p["problems"] and not (p["conflict"] and len(p["problems"]) == 0):
                st = "NOT MOVED: " + "; ".join(p["problems"])
            elif p["conflict"]:
                st = "CONFLICT: a file with this name already exists"
            else:
                st = "Will move" + (" (destination folder will be created)" if p["creates_folder"] else "")
            self.t.setItem(r, 2, QTableWidgetItem(st))
            if p["conflict"] and not p["problems"]:
                cb = QComboBox()
                cb.addItems(["Skip this file", "Keep both (add a number to the new name)"])
                cb.setAccessibleName(f"Conflict choice {r}")
                self.t.setCellWidget(r, 3, cb)
                self.combos[r] = cb
        self.t.resizeColumnsToContents()
        v.addWidget(self.t, 1)
        n_ok = sum(1 for p in pre if not p["problems"])
        bb = QDialogButtonBox()
        self.ok = bb.addButton(f"Move Selected Files", QDialogButtonBox.AcceptRole)
        self.ok.setObjectName("Primary")
        self.ok.setEnabled(n_ok > 0)
        bb.addButton("Cancel", QDialogButtonBox.RejectRole)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def plan(self) -> list[actions.MovePlanItem]:
        out = []
        for r, p in enumerate(self.pre):
            if p["problems"]:
                continue
            it = p["item"]
            if p["conflict"]:
                if self.combos[r].currentIndex() == 0:
                    continue
                it.on_conflict = "keep_both"
            out.append(it)
        return out


class NameDialog(QDialog):
    def __init__(self, parent, row=None):
        super().__init__(parent)
        self.setWindowTitle("Client name and folder")
        self.resize(700, 200)
        f = QFormLayout(self)
        self.name = QLineEdit(row["name"] if row else "")
        self.aliases = QLineEdit(row["aliases"] if row else "")
        self.aliases.setPlaceholderText("Other spellings, separated by ;")
        self.folder = QLineEdit(row["folder"] if row else "")
        self.name.setAccessibleName("Client name")
        self.aliases.setAccessibleName("Client aliases")
        self.folder.setAccessibleName("Client folder")
        b = QPushButton("Browse...")
        b.clicked.connect(self._browse)
        f.addRow("Client name:", self.name)
        f.addRow("Aliases:", self.aliases)
        f.addRow("Destination folder:", hbox(self.folder, b, stretch_end=False))
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        f.addRow(bb)

    def _browse(self):
        p = pick_folder(self, "Destination folder for this client", self.folder.text())
        if p:
            self.folder.setText(p)


class OrganizePage(QWidget):
    def __init__(self, main):
        super().__init__()
        self.main = main
        self.st = None
        self.rows = []
        v = QVBoxLayout(self)
        v.setContentsMargins(16, 14, 16, 14)
        v.addWidget(label("Organize", "H1"))
        v.addWidget(label("1) Read documents   2) click a file (or tick several), check the name and destination, then "
                          "Confirm Name - the file stays where it is and is ticked for moving   3) click Move Selected "
                          "Files to review the exact moves.",
                          "Hint", wrap=True))
        self.tabs = QTabWidget()
        v.addWidget(self.tabs, 1)

        # --- queue tab
        q = QWidget()
        qv = QVBoxLayout(q)
        self.b_read = QPushButton("Read documents (text, Word, OCR)")
        self.b_read.setObjectName("Primary")
        self.b_read.clicked.connect(self._read)
        self.sub = QLineEdit()
        self.sub.setPlaceholderText("Only this subfolder (optional, relative)")
        self.sub.setMaximumWidth(280)
        self.f_status = QComboBox()
        self.f_status.addItems([s or "All statuses" for s in STATUSES])
        self.f_status.currentIndexChanged.connect(self.refresh)
        self.f_search = QLineEdit()
        self.f_search.setPlaceholderText("Search file or name")
        self.f_search.textChanged.connect(self.refresh)
        qv.addLayout(hbox(self.b_read, self.sub, None, self.f_status, self.f_search, stretch_end=False))
        split = QSplitter(Qt.Horizontal)
        self.t = table(["Select", "File (relative)", "Detected name", "Evidence (page / excerpt)", "Source", "Status",
                        "Confirmed name", "Destination folder", "Note"], stretch_col=None, sortable=False)
        self.t.setAccessibleName("Organize queue")
        self.t.itemSelectionChanged.connect(self._row_selected)
        self.t.itemChanged.connect(self._check_changed)
        split.addWidget(self.t)
        side = QGroupBox("Selected file")
        sv = QVBoxLayout(side)
        self.s_file = label("", None, wrap=True)
        self.s_evidence = label("", None, wrap=True)
        self.s_name = QComboBox()
        self.s_name.setEditable(True)
        self.s_name.setAccessibleName("Name to confirm")
        self.s_name.currentTextChanged.connect(self._name_edited)
        self.s_dest = QLineEdit()
        self.s_dest.setAccessibleName("Destination folder")
        b_br = QPushButton("Browse...")
        b_br.clicked.connect(self._browse_dest)
        self.b_confirm = QPushButton("Confirm Name")
        self.b_confirm.setObjectName("Primary")
        self.b_confirm.clicked.connect(self._confirm)
        self.b_confirm_ticked = QPushButton("Confirm this name for all ticked files")
        self.b_confirm_ticked.clicked.connect(self._confirm_ticked)
        self.b_skip = QPushButton("Skip file")
        self.b_skip.clicked.connect(self._skip)
        self.b_reopen = QPushButton("Reopen")
        self.b_reopen.clicked.connect(self._reopen)
        self.b_openf = QPushButton("Open file")
        self.b_openf.clicked.connect(self._open_file)
        sv.addWidget(self.s_file)
        sv.addWidget(self.s_evidence)
        sv.addWidget(label("Name:", None))
        sv.addWidget(self.s_name)
        sv.addWidget(label("Destination folder:", None))
        sv.addLayout(hbox(self.s_dest, b_br, stretch_end=False))
        sv.addLayout(hbox(self.b_confirm, self.b_skip, self.b_reopen))
        sv.addWidget(self.b_confirm_ticked)
        sv.addWidget(self.b_openf)
        sv.addStretch(1)
        split.addWidget(side)
        split.setSizes([900, 360])
        qv.addWidget(split, 1)
        self.sel_info = label("", None)
        b_tick = QPushButton("Tick all shown")
        b_tick.clicked.connect(lambda: self._tick_shown(True))
        b_untick = QPushButton("Untick all shown")
        b_untick.clicked.connect(lambda: self._tick_shown(False))
        self.b_move = QPushButton("Move Selected Files...")
        self.b_move.setObjectName("Primary")
        self.b_move.setAccessibleName("Move Selected Files")
        self.b_move.clicked.connect(self._move)
        qv.addLayout(hbox(b_tick, b_untick, self.sel_info, None, self.b_move, stretch_end=False))
        self.tabs.addTab(q, "Review queue")

        # --- names tab
        n = QWidget()
        nv = QVBoxLayout(n)
        nv.addWidget(label("Client names the app looks for in documents, and the folder each client's files go to.",
                           "Hint", wrap=True))
        b_add = QPushButton("Add...")
        b_add.clicked.connect(self._add_name)
        b_edit = QPushButton("Edit...")
        b_edit.clicked.connect(self._edit_name)
        b_del = QPushButton("Remove")
        b_del.clicked.connect(self._del_name)
        nv.addLayout(hbox(b_add, b_edit, b_del))
        self.nt = table(["Client name", "Aliases", "Destination folder", "id"], stretch_col=2)
        self.nt.setAccessibleName("Client names")
        self.nt.setColumnHidden(3, True)
        nv.addWidget(self.nt, 1)
        self.tabs.addTab(n, "Client names && folders")
        self._loading = False

    # ------------------------------------------------------------------
    def clear(self):
        self.st = None
        self.rows = []
        self.t.setRowCount(0)
        self.nt.setRowCount(0)
        self.s_file.setText("")
        self.s_evidence.setText("")

    def load(self, st):
        self.clear()
        self.st = st
        if st.db is None:
            return
        self.b_read.setEnabled(bool(st.snapshot_id))
        self.refresh()
        self._load_names()

    def refresh(self):
        st = self.st
        if not st or not st.db:
            return
        status = STATUSES[self.f_status.currentIndex()]
        self.rows = organize.queue(st.db, status, self.f_search.text().strip())
        self._loading = True
        self.t.setRowCount(len(self.rows))
        for r, q in enumerate(self.rows):
            chk = QTableWidgetItem()
            if q["status"] != "Moved":
                chk.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                chk.setCheckState(Qt.Checked if q["selected"] else Qt.Unchecked)
                if q["status"] != "Name confirmed":
                    chk.setToolTip("Ticked files can be confirmed together; only confirmed files are moved")
            else:
                chk.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.t.setItem(r, 0, chk)
            ev = f"{q['page_ref'] or ''}: {q['excerpt'] or ''}" if q["excerpt"] else ""
            vals = [q["rel_path"], q["detected_name"] or "", ev, q["source"] or "", q["status"],
                    q["confirmed_name"] or "", q["destination"] or "", q["note"] or ""]
            for c, val in enumerate(vals, 1):
                it = QTableWidgetItem(val)
                it.setToolTip(val)
                self.t.setItem(r, c, it)
        self._loading = False
        self.t.resizeColumnsToContents()
        self.t.setColumnWidth(1, min(self.t.columnWidth(1), 380))
        for c in (2, 3, 7, 8):
            self.t.setColumnWidth(c, min(self.t.columnWidth(c), 300))
        self._update_counts()

    def _update_counts(self):
        con = self.st.db.con
        n_move = con.execute("SELECT COUNT(*) FROM organize_queue WHERE selected=1 AND status='Name confirmed'").fetchone()[0]
        n_tick = con.execute("SELECT COUNT(*) FROM organize_queue WHERE selected=1 AND status<>'Moved'").fetchone()[0]
        tot = con.execute("SELECT status, COUNT(*) FROM organize_queue GROUP BY status").fetchall()
        extra = f" ({n_tick - n_move} not yet confirmed)" if n_tick > n_move else ""
        self.sel_info.setText(f"{n_tick} ticked{extra}, {n_move} ready to move   |   queue: " +
                              ", ".join(f"{r[0]} {r[1]}" for r in tot))
        self.b_move.setEnabled(n_move > 0)
        self.b_confirm_ticked.setEnabled(n_tick > 0)
        self.b_confirm_ticked.setText(f"Confirm this name for all {n_tick} ticked file(s)" if n_tick
                                      else "Confirm this name for all ticked files")

    def _tick_shown(self, on: bool):
        if not self.st or not self.st.db:
            return
        for q in self.rows:
            if q["status"] != "Moved":
                organize.set_selected(self.st.db, q["id"], on)
        self.refresh()

    def _confirm_ticked(self):
        st = self.st
        name = self.s_name.currentText().strip()
        dest = self.s_dest.text().strip()
        ticked = st.db.con.execute("SELECT id, rel_path FROM organize_queue WHERE selected=1 AND status<>'Moved'").fetchall()
        if not ticked:
            return
        if not name:
            error(self, "Confirm Name", "Type or pick a name first.")
            return
        if not ask(self, "Confirm name for ticked files",
                   f"Confirm the name '{name}' for {len(ticked)} ticked file(s)?\n"
                   f"Destination folder: {dest or '(not set)'}\n\nThe files are NOT moved now.", yes="Confirm"):
            return
        for r in ticked:
            organize.confirm_name(st.db, r["id"], name, dest)
        self.main.statusBar().showMessage(f"Name '{name}' confirmed for {len(ticked)} file(s) - nothing was moved.", 8000)
        self.refresh()

    def _load_names(self):
        rows = [[r["name"], r["aliases"], r["folder"], str(r["id"])] for r in organize.list_names(self.st.db)]
        fill(self.nt, rows)

    def _current(self):
        r = sel_row(self.t)
        return self.rows[r] if 0 <= r < len(self.rows) else None

    def _row_selected(self):
        q = self._current()
        if not q:
            return
        self.s_file.setText(f"<b>{q['rel_path']}</b><br>Status: {q['status']}")
        self.s_evidence.setText(f"Evidence: {q['page_ref'] or '-'}<br><i>{q['excerpt'] or 'No excerpt'}</i>"
                                f"<br>Source: {q['source'] or '-'}")
        self.s_name.blockSignals(True)
        self.s_name.clear()
        names = []
        for c in json.loads(q["candidates"] or "[]"):
            names.append(c["name"])
        for r in organize.list_names(self.st.db):
            if r["name"] not in names:
                names.append(r["name"])
        self.s_name.addItems(names)
        self.s_name.setEditText(q["confirmed_name"] or q["detected_name"] or "")
        self.s_name.blockSignals(False)
        self.s_dest.setText(q["destination"] or organize.folder_for(self.st.db, q["confirmed_name"] or q["detected_name"] or ""))
        moved = q["status"] == "Moved"
        self.b_confirm.setEnabled(not moved)
        self.b_skip.setEnabled(not moved)

    def _name_edited(self, text):
        f = organize.folder_for(self.st.db, text) if self.st else ""
        if f:
            self.s_dest.setText(f)

    def _browse_dest(self):
        p = pick_folder(self, "Destination folder", self.s_dest.text())
        if p:
            self.s_dest.setText(p)

    def _confirm(self):
        q = self._current()
        if not q:
            return
        try:
            organize.confirm_name(self.st.db, q["id"], self.s_name.currentText(), self.s_dest.text().strip())
        except Exception as e:
            error(self, "Confirm Name", str(e))
            return
        self.main.statusBar().showMessage(f"Name confirmed for {q['rel_path']} - the file was not moved.", 8000)
        row = sel_row(self.t)
        self.refresh()
        self.t.selectRow(min(row, self.t.rowCount() - 1))

    def _skip(self):
        q = self._current()
        if q:
            organize.skip(self.st.db, q["id"])
            self.refresh()

    def _reopen(self):
        q = self._current()
        if q:
            organize.reopen(self.st.db, q["id"])
            self.refresh()

    def _open_file(self):
        q = self._current()
        if q and not open_path(os.path.join(self.st.project.root_path, q["rel_path"])):
            error(self, "Open", "File is not available at its saved location.")

    def _check_changed(self, item):
        if self._loading or item.column() != 0:
            return
        q = self.rows[item.row()]
        organize.set_selected(self.st.db, q["id"], item.checkState() == Qt.Checked)
        self._update_counts()

    def _read(self):
        st = self.st
        if not st or not st.snapshot_id:
            return
        if not organize.list_names(st.db) and not ask(
                self, "No client names", "No client names are set up yet. Only label-based suggestions "
                "(e.g. 'Client: ...') will be found. Continue?", yes="Continue"):
            return
        project, sid, sub = st.project, st.snapshot_id, self.sub.text().strip()

        def work(cancel, prog):
            db = ProjectDB.open(project)
            try:
                return organize.build_queue(db, sid, sub, progress=prog, cancel=cancel)
            finally:
                db.close()

        ok, res = run_with_progress(self, project.project_id, "Reading documents", work)
        if not ok:
            error(self, "Read documents", str(res))
            return
        info(self, "Read documents", f"{res['files']} document(s)/image(s) checked:\n"
             f"  {res['detected']} with one client name\n  {res['suggested']} with a suggested name (not in list)\n"
             f"  {res['review']} need manual review\n  {res['kept']} already confirmed/skipped/moved (unchanged)")
        if self.main.st.project and self.main.st.project.project_id == project.project_id:
            self.refresh()

    def _move(self):
        st = self.st
        sel = [q for q in organize.queue(st.db, "Name confirmed") if q["selected"]]
        if not sel:
            return
        items = [actions.MovePlanItem(q["rel_path"], q["destination"] or "", os.path.basename(q["rel_path"]), "ask",
                                      q["id"]) for q in sel]
        pre = actions.preflight_moves(st.project.root_path, items)
        d = MoveReviewDialog(self, st.project, pre)
        if d.exec() != QDialog.Accepted:
            return
        plan = d.plan()
        planned = {id(it) for it in plan}
        for p in pre:  # record files that will not be moved, with the reason
            if id(p["item"]) in planned:
                continue
            why = "; ".join(p["problems"]) if p["problems"] else "Destination name exists - skipped by user (no overwrite)"
            st.db.log_action("Move file", "Skipped", source=p["source"], destination=p["destination"], error=why,
                             scan_id=st.snapshot_id)
        if not plan:
            info(self, "Move", "Nothing to move.")
            return
        project, sid = st.project, st.snapshot_id

        def work(cancel, prog):
            db = ProjectDB.open(project)
            try:
                return actions.move_files(db, sid, plan, progress=prog, cancel=cancel)
            finally:
                db.close()

        ok, rep = run_with_progress(self, project.project_id, "Moving files", work)
        if not ok:
            error(self, "Move", str(rep))
            return
        rows = [[r.path, r.destination, r.outcome, r.error] for r in rep.results]
        ResultsDialog(self, "Move results", f"Moved: {rep.count('Moved')}   Failed: {rep.count('Failed')}   "
                      "(each outcome is in History)", rows, ["Source", "Destination", "Outcome", "Error"]).exec()
        if self.main.st.project and self.main.st.project.project_id == project.project_id:
            self.refresh()
        self.main.start_scan(project, quiet=True)

    # names
    def _add_name(self):
        d = NameDialog(self)
        if d.exec() == QDialog.Accepted:
            try:
                organize.save_name(self.st.db, d.name.text(), d.aliases.text(), d.folder.text().strip())
            except Exception as e:
                error(self, "Client name", str(e))
            self._load_names()

    def _edit_name(self):
        r = sel_row(self.nt)
        if r < 0:
            return
        nid = int(self.nt.item(r, 3).text())
        row = {"name": self.nt.item(r, 0).text(), "aliases": self.nt.item(r, 1).text(), "folder": self.nt.item(r, 2).text()}
        d = NameDialog(self, row)
        if d.exec() == QDialog.Accepted:
            try:
                organize.save_name(self.st.db, d.name.text(), d.aliases.text(), d.folder.text().strip(), nid)
            except Exception as e:
                error(self, "Client name", str(e))
            self._load_names()

    def _del_name(self):
        r = sel_row(self.nt)
        if r >= 0:
            organize.delete_name(self.st.db, int(self.nt.item(r, 3).text()))
            self._load_names()
