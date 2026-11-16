from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QDialog, QDialogButtonBox, QHeaderView, QLineEdit, QPushButton, QSplitter,
                               QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from .. import actions, export, reports
from ..paths import human_size, ts_to_iso
from .common import (ResultsDialog, error, fill, hbox, info, label, open_containing, run_with_progress, save_path,
                     size_item, table)

KEEP_COL, DEL_COL, PATH_COL = 0, 1, 2


class DeleteReviewDialog(QDialog):
    """Shows the exact full paths that will be kept and deleted."""

    def __init__(self, parent, project, plan, recyclable, permanent):
        super().__init__(parent)
        self.setWindowTitle("Review deletion - " + project.name)
        self.resize(1150, 620)
        v = QVBoxLayout(self)
        v.addWidget(label(f"Project: {project.name}     Scan path: {project.root_path}", "H1", wrap=True))
        total = sum(g.size * len(g.delete) for g in plan)
        n = sum(len(g.delete) for g in plan)
        v.addWidget(label(f"{n} file(s) in {len(plan)} group(s) will be deleted, freeing about {human_size(total)}. "
                          f"One verified copy per group is kept. Every file is fingerprinted again (SHA-256) "
                          f"immediately before deletion; a group is skipped if anything changed.", None, wrap=True))
        if permanent:
            w = label(f"WARNING: {len(permanent)} file(s) are on a location without a Recycle Bin (network share or "
                      "removable drive). They would be PERMANENTLY deleted and need a separate confirmation.",
                      "Danger", wrap=True)
            v.addWidget(w)
        t = table(["Group", "Action", "Full path", "Size", "Method"], stretch_col=2)
        t.setAccessibleName("Deletion review table")
        rows = []
        perm = set(permanent)
        for i, g in enumerate(plan, 1):
            rows.append([str(i), "KEEP", os.path.join(project.root_path, g.keep), size_item(g.size), "Not touched"])
            for d in g.delete:
                rows.append([str(i), "DELETE", os.path.join(project.root_path, d), size_item(g.size),
                             "PERMANENT deletion" if d in perm else "Recycle Bin"])
        fill(t, rows)
        t.setSortingEnabled(False)
        v.addWidget(t, 1)
        bb = QDialogButtonBox()
        self.ok = bb.addButton("Delete Selected Copies", QDialogButtonBox.AcceptRole)
        self.ok.setObjectName("DangerBtn")
        bb.addButton("Cancel", QDialogButtonBox.RejectRole)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)


class PermanentDialog(QDialog):
    def __init__(self, parent, project, permanent):
        super().__init__(parent)
        self.setWindowTitle("Permanent deletion")
        self.resize(950, 420)
        v = QVBoxLayout(self)
        v.addWidget(label(f"These {len(permanent)} file(s) cannot go to the Recycle Bin and will be deleted "
                          "PERMANENTLY. They cannot be restored by this app.", "Danger", wrap=True))
        t = table(["Full path"], stretch_col=0)
        fill(t, [[os.path.join(project.root_path, p)] for p in permanent])
        v.addWidget(t, 1)
        self.chk = QCheckBox("I understand these files will be permanently deleted")
        v.addWidget(self.chk)
        bb = QDialogButtonBox()
        self.ok = bb.addButton(f"Permanently delete {len(permanent)} file(s)", QDialogButtonBox.AcceptRole)
        self.ok.setObjectName("DangerBtn")
        self.ok.setEnabled(False)
        bb.addButton("Skip these files", QDialogButtonBox.RejectRole)
        self.chk.toggled.connect(self.ok.setEnabled)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)


class DuplicatesPage(QWidget):
    def __init__(self, main):
        super().__init__()
        self.main = main
        self.st = None
        self.groups = []
        v = QVBoxLayout(self)
        v.setContentsMargins(16, 14, 16, 14)
        v.addWidget(label("Exact duplicates", "H1"))
        v.addWidget(label("Groups below are verified with a full-file SHA-256 fingerprint. Similar files that are not "
                          "byte-identical never appear here (see Compare Versions). Tick one KEEP per group and the "
                          "extra copies to delete.", "Hint", wrap=True))
        self.summary = label("", None)
        self.summary.setAccessibleDescription("Duplicates summary")
        self.search = QLineEdit()
        self.search.setPlaceholderText("Filter groups by path")
        self.search.setAccessibleName("Duplicate filter")
        self.search.textChanged.connect(self._render)
        b_all = QPushButton("Tick extra copies (shown groups)")
        b_all.clicked.connect(self._tick_all)
        b_none = QPushButton("Clear ticks")
        b_none.clicked.connect(self._clear_ticks)
        b_open = QPushButton("Open containing folder")
        b_open.clicked.connect(self._open)
        self.b_review = QPushButton("Review && delete selected copies...")
        self.b_review.setObjectName("DangerBtn")
        self.b_review.clicked.connect(self._review)
        b_exp = QPushButton("Export duplicate report...")
        b_exp.clicked.connect(self._export)
        v.addLayout(hbox(self.summary, None, self.search, stretch_end=False))
        v.addLayout(hbox(b_all, b_none, b_open, None, b_exp, self.b_review, stretch_end=False))
        split = QSplitter(Qt.Vertical)
        self.tree = QTreeWidget()
        self.tree.setAccessibleName("Duplicate groups")
        self.tree.setHeaderLabels(["Keep", "Delete", "Path", "Size", "Modified", "Copies / savings"])
        self.tree.header().setSectionResizeMode(PATH_COL, QHeaderView.Stretch)
        self.tree.setAlternatingRowColors(True)
        self.tree.itemChanged.connect(self._item_changed)
        split.addWidget(self.tree)
        w = QWidget()
        wl = QVBoxLayout(w)
        wl.setContentsMargins(0, 4, 0, 0)
        wl.addWidget(label("Not verified (same size as other files, but could not be read completely - "
                           "these are never offered for deletion):", None, wrap=True))
        self.unv = table(["Relative path", "Size", "Modified", "Reason"], stretch_col=0)
        self.unv.setAccessibleName("Unverified duplicate candidates")
        wl.addWidget(self.unv)
        split.addWidget(w)
        split.setSizes([560, 160])
        v.addWidget(split, 1)
        self._updating = False

    def clear(self):
        self.st = None
        self.groups = []
        self.tree.clear()
        self.unv.setRowCount(0)
        self.summary.setText("No completed snapshot")

    def load(self, st):
        self.clear()
        self.st = st
        if st.db is None or not st.snapshot_id:
            return
        self.groups = reports.duplicate_groups(st.db, st.snapshot_id)
        for g in self.groups:
            # default keep = oldest copy (earliest modified), then shortest path
            g["keep"] = sorted(g["files"], key=lambda f: (f["mtime"] or 0, len(f["rel_path"])))[0]["rel_path"]
            g["delete"] = set()
        unv = reports.unverified_duplicate_candidates(st.db, st.snapshot_id)
        fill(self.unv, [[r["rel_path"], size_item(r["size"]), ts_to_iso(r["mtime"]), r["hash_error"]] for r in unv])
        self._render()

    def _render(self):
        self._updating = True
        self.tree.clear()
        q = self.search.text().lower().strip()
        total = sum(g["savings"] for g in self.groups)
        shown = 0
        for gi, g in enumerate(self.groups):
            if q and not any(q in f["rel_path"].lower() for f in g["files"]):
                continue
            shown += 1
            top = QTreeWidgetItem(["", "", f"Group {gi + 1}: {len(g['files'])} identical copies   SHA-256 {g['sha256'][:16]}...",
                                   human_size(g["size"]), "", f"save {human_size(g['savings'])}"])
            top.setFirstColumnSpanned(False)
            top.setData(0, Qt.UserRole, gi)
            f = top.font(2)
            f.setBold(True)
            top.setFont(2, f)
            for fobj in g["files"]:
                ch = QTreeWidgetItem(["", "", fobj["rel_path"], human_size(g["size"]), ts_to_iso(fobj["mtime"]), ""])
                ch.setData(0, Qt.UserRole, (gi, fobj["rel_path"]))
                ch.setFlags(ch.flags() | Qt.ItemIsUserCheckable)
                keep = fobj["rel_path"] == g["keep"]
                ch.setCheckState(KEEP_COL, Qt.Checked if keep else Qt.Unchecked)
                ch.setCheckState(DEL_COL, Qt.Checked if fobj["rel_path"] in g["delete"] else Qt.Unchecked)
                if keep:
                    ch.setText(DEL_COL, "kept")
                top.addChild(ch)
            self.tree.addTopLevelItem(top)
            top.setExpanded(True)
        for c in (0, 1, 3, 4):
            self.tree.resizeColumnToContents(c)
        self._updating = False
        self._update_summary(total, shown)

    def _update_summary(self, total=None, shown=None):
        if total is None:
            total = sum(g["savings"] for g in self.groups)
        sel = sum(len(g["delete"]) for g in self.groups)
        sel_bytes = sum(len(g["delete"]) * g["size"] for g in self.groups)
        snap = self.st.snapshot if self.st else None
        self.summary.setText(f"{len(self.groups):,} verified groups, {sum(len(g['files']) for g in self.groups):,} files, "
                             f"up to {human_size(total)} recoverable  |  selected for deletion: {sel} "
                             f"({human_size(sel_bytes)})" + (f"  |  snapshot #{snap['seq']}" if snap else ""))
        self.b_review.setEnabled(sel > 0)

    def _item_changed(self, item, col):
        if self._updating:
            return
        data = item.data(0, Qt.UserRole)
        if not isinstance(data, tuple):
            return
        gi, rel = data
        g = self.groups[gi]
        if col == KEEP_COL:
            if item.checkState(KEEP_COL) == Qt.Checked:
                g["keep"] = rel
                g["delete"].discard(rel)
            elif g["keep"] == rel:
                pass  # must always keep one: re-check below
            self._render()
        elif col == DEL_COL:
            if rel == g["keep"]:
                self._render()
                return
            if item.checkState(DEL_COL) == Qt.Checked:
                g["delete"].add(rel)
            else:
                g["delete"].discard(rel)
            # at least one copy must remain
            if len(g["delete"]) >= len(g["files"]):
                g["delete"].discard(rel)
                self._render()
            self._update_summary()

    def _tick_all(self):
        """Ticks the extra copies of the groups currently shown (respects the filter)."""
        q = self.search.text().lower().strip()
        for g in self.groups:
            if q and not any(q in f["rel_path"].lower() for f in g["files"]):
                continue
            g["delete"] = {f["rel_path"] for f in g["files"] if f["rel_path"] != g["keep"]}
        self._render()

    def _clear_ticks(self):
        for g in self.groups:
            g["delete"] = set()
        self._render()

    def _open(self):
        it = self.tree.currentItem()
        if it and isinstance(it.data(0, Qt.UserRole), tuple):
            open_containing(os.path.join(self.st.project.root_path, it.data(0, Qt.UserRole)[1]))

    def _review(self):
        st = self.st
        plan = [actions.DeletePlanGroup(g["sha256"], g["size"], g["keep"], sorted(g["delete"]))
                for g in self.groups if g["delete"]]
        if not plan:
            return
        for p in plan:
            assert p.keep not in p.delete
        all_del = [d for p in plan for d in p.delete]
        rec, perm = actions.classify_deletion(st.project.root_path, all_del)
        d = DeleteReviewDialog(self, st.project, plan, rec, perm)
        if d.exec() != QDialog.Accepted:
            return
        allow_perm = False
        if perm:
            pd = PermanentDialog(self, st.project, perm)
            allow_perm = pd.exec() == QDialog.Accepted
        project, scan_id = st.project, st.snapshot_id
        from ..store import ProjectDB

        def work(cancel, prog):
            db = ProjectDB.open(project)
            try:
                return actions.delete_duplicates(db, scan_id, plan, allow_perm, progress=prog, cancel=cancel)
            finally:
                db.close()

        ok, rep = run_with_progress(self, project.project_id, "Deleting selected copies", work)
        if not ok:
            error(self, "Delete", str(rep))
            return
        rows = [[r.path, r.outcome, r.error] for r in rep.results]
        summ = (f"Recycled: {rep.count('Recycled')}   Permanently deleted: {rep.count('Deleted permanently')}   "
                f"Skipped: {rep.count('Skipped')}   Failed: {rep.count('Failed')}   (each outcome is in History)")
        ResultsDialog(self, "Deletion results", summ, rows, ["File", "Outcome", "Error / reason"]).exec()
        # refresh: hide acted files now, and re-scan the project for fresh results
        if self.main.st.project and self.main.st.project.project_id == project.project_id:
            self.main.reload_pages()
        self.main.start_scan(project, quiet=True)

    def _export(self):
        st = self.st
        if not st or not st.snapshot_id:
            return
        path = save_path(self, "Export duplicate report", f"{st.project.name} - duplicates - snapshot {st.snapshot['seq']}.xlsx")
        if not path:
            return
        try:
            n = export.export_duplicates(st.db, st.snapshot_id, path)
        except Exception as e:
            error(self, "Export", str(e))
            return
        info(self, "Export", f"Exported {n:,} rows to\n{path}")
