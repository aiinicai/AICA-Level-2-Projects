from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (QComboBox, QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMainWindow,
                               QMessageBox, QProgressBar, QPushButton, QStackedWidget, QVBoxLayout, QWidget)

from .. import APP_NAME, APP_VERSION
from ..paths import human_size, location_kind
from ..scanner import Scanner
from ..store import Catalog, Project, ProjectDB
from .common import STATUS_COLORS, Worker, error, label

NAV = ["Projects", "Overview", "Files", "Changes", "Duplicates", "Compare Versions", "Organize", "History"]


class AppState:
    def __init__(self, catalog: Catalog):
        self.catalog = catalog
        self.project: Project | None = None
        self.db: ProjectDB | None = None
        self.snapshot_id: str | None = None
        self.generation = 0

    @property
    def snapshot(self):
        return self.db.scan(self.snapshot_id) if self.db and self.snapshot_id else None


class MainWindow(QMainWindow):
    def __init__(self, catalog: Catalog):
        super().__init__()
        self.st = AppState(catalog)
        self.scan_workers: dict[str, Worker] = {}
        self.last_progress: dict[str, object] = {}
        self.setWindowTitle(APP_NAME)
        self.resize(1360, 860)

        from .pages_changes import ChangesPage
        from .pages_duplicates import DuplicatesPage
        from .pages_files import FilesPage
        from .pages_history import HistoryPage
        from .pages_organize import OrganizePage
        from .pages_overview import OverviewPage
        from .pages_projects import ProjectsPage
        from .pages_versions import VersionsPage

        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.nav = QListWidget()
        self.nav.setObjectName("Nav")
        self.nav.setAccessibleName("Navigation")
        self.nav.setFixedWidth(200)
        for n in NAV:
            QListWidgetItem(n, self.nav)
        root.addWidget(self.nav)

        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(0)
        root.addLayout(right, 1)

        # ---- context bar: active project + exact path + snapshot, always visible
        bar = QFrame()
        bar.setObjectName("ContextBar")
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(14, 8, 14, 8)
        col = QVBoxLayout()
        self.ctx_project = label("No project open", "CtxProject")
        self.ctx_project.setAccessibleDescription("Active project")
        self.ctx_path = label("Create or open a project on the Projects page", "CtxPath")
        self.ctx_path.setAccessibleDescription("Active project path")
        col.addWidget(self.ctx_project)
        col.addWidget(self.ctx_path)
        bl.addLayout(col, 1)
        bl.addWidget(QLabel("Showing snapshot:"))
        self.snap_combo = QComboBox()
        self.snap_combo.setMinimumWidth(300)
        self.snap_combo.setAccessibleName("Snapshot selector")
        self.snap_combo.currentIndexChanged.connect(self._snapshot_changed)
        bl.addWidget(self.snap_combo)
        self.scan_btn = QPushButton("Re-scan")
        self.scan_btn.setObjectName("Primary")
        self.scan_btn.setAccessibleName("Re-scan project")
        self.scan_btn.clicked.connect(lambda: self.start_scan(self.st.project))
        bl.addWidget(self.scan_btn)
        right.addWidget(bar)

        # ---- scan progress (separate from completed results)
        self.scan_panel = QFrame()
        self.scan_panel.setObjectName("ScanPanel")
        sp = QHBoxLayout(self.scan_panel)
        sp.setContentsMargins(14, 6, 14, 6)
        self.scan_text = label("", None)
        self.scan_text.setAccessibleDescription("Scan progress")
        self.scan_text.setWordWrap(True)
        self.ctx_path.setWordWrap(True)
        self.scan_bar = QProgressBar()
        self.scan_bar.setMaximumWidth(260)
        self.scan_cancel = QPushButton("Cancel scan")
        self.scan_cancel.clicked.connect(self.cancel_active_scan)
        sp.addWidget(self.scan_text, 1)
        sp.addWidget(self.scan_bar)
        sp.addWidget(self.scan_cancel)
        self.scan_panel.hide()
        right.addWidget(self.scan_panel)

        self.stack = QStackedWidget()
        right.addWidget(self.stack, 1)
        self.pages = [ProjectsPage(self), OverviewPage(self), FilesPage(self), ChangesPage(self),
                      DuplicatesPage(self), VersionsPage(self), OrganizePage(self), HistoryPage(self)]
        for p in self.pages:
            p.setObjectName("Page")
            self.stack.addWidget(p)
        self.nav.currentRowChanged.connect(self._nav_changed)
        self.nav.itemSelectionChanged.connect(self._nav_selection)
        self.setCentralWidget(central)
        self.statusBar().showMessage(f"{APP_NAME} {APP_VERSION} - all data is stored locally on this computer")
        for i in range(len(NAV)):
            QShortcut(QKeySequence(f"Ctrl+{i + 1}"), self, activated=lambda i=i: self.nav.setCurrentRow(i))

        # interrupted scans from previous sessions
        for p in catalog.list():
            try:
                db = ProjectDB.open(p)
                db.mark_interrupted()
                db.close()
            except Exception:
                pass
        self.set_active(None)
        self.nav.setCurrentRow(0)

    # ------------------------------------------------------------------ project switching
    def set_active(self, project: Project | None):
        if self.st.db is not None:
            self.st.db.close()
        self.st.generation += 1
        self.st.project = project
        self.st.db = None
        self.st.snapshot_id = None
        if project is not None:
            try:
                self.st.db = ProjectDB.open(project)
                self.st.catalog.touch(project.project_id)
            except Exception as e:
                error(self, "Cannot open project", str(e))
                self.st.project = None
        for i in range(1, self.nav.count()):
            it = self.nav.item(i)
            it.setFlags(it.flags() | Qt.ItemIsEnabled if self.st.project else it.flags() & ~Qt.ItemIsEnabled)
        self._update_context()
        self._reload_snapshots(select_latest=True)
        self._update_scan_panel()

    def _update_context(self):
        p = self.st.project
        if p is None:
            self.ctx_project.setText("No project open")
            self.ctx_path.setText("Create or open a project on the Projects page")
            self.scan_btn.setEnabled(False)
            self.setWindowTitle(APP_NAME)
            return
        self.ctx_project.setText(f"Project: {p.name}")
        self.ctx_path.setText(f"Scan path: {p.root_path}    [{location_kind(p.root_path)}]    ID {p.project_id[:8]}")
        self.ctx_path.setToolTip(p.root_path)
        self.scan_btn.setEnabled(True)
        self.setWindowTitle(f"{p.name} - {p.root_path} - {APP_NAME}")

    def _reload_snapshots(self, select_latest=False):
        cur = self.st.snapshot_id
        self.snap_combo.blockSignals(True)
        self.snap_combo.clear()
        snaps = self.st.db.usable_snapshots() if self.st.db else []
        if not snaps:
            self.snap_combo.addItem("No completed scan yet", None)
        for s in snaps:
            txt = (f"#{s['seq']}  {(s['finished'] or s['started'])[:19].replace('T', ' ')}  "
                   f"{s['status']}{' (accepted)' if s['accepted_manually'] else ''}  {s['files_found']:,} files")
            self.snap_combo.addItem(txt, s["scan_id"])
        idx = 0
        if not select_latest and cur:
            j = self.snap_combo.findData(cur)
            idx = j if j >= 0 else 0
        self.snap_combo.setCurrentIndex(idx)
        self.snap_combo.blockSignals(False)
        self.st.snapshot_id = self.snap_combo.currentData()
        self.reload_pages()

    def _snapshot_changed(self, _i):
        self.st.snapshot_id = self.snap_combo.currentData()
        self.reload_pages()

    def reload_pages(self):
        for p in self.pages:
            try:
                p.load(self.st)
            except Exception as e:  # never leave stale data from another project on screen
                p.clear()
                self.statusBar().showMessage(f"Could not load {p.__class__.__name__}: {e}")

    def _nav_changed(self, row):
        if row >= 0:
            self.stack.setCurrentIndex(row)

    def _nav_selection(self):
        items = self.nav.selectedItems()
        if items:
            row = self.nav.row(items[0])
            if row != self.nav.currentRow():
                self.nav.setCurrentRow(row)
            self.stack.setCurrentIndex(row)

    def go(self, page_name: str):
        self.nav.setCurrentRow(NAV.index(page_name))

    def open_project(self, project_id: str):
        p = self.st.catalog.get(project_id)
        if p is None:
            return
        self.set_active(p)
        self.go("Overview")

    # ------------------------------------------------------------------ scanning
    def start_scan(self, project: Project | None, quiet=False):
        if project is None:
            return
        if project.project_id in self.scan_workers:
            if not quiet:
                QMessageBox.information(self, "Scan running", f"A scan of '{project.name}' is already running.")
            return
        proj = project

        def fn(cancel, emit):
            return Scanner(proj, cancel, emit).run()

        w = Worker(proj.project_id, fn, self)
        w.progressed.connect(self._scan_progress)
        w.done.connect(self._scan_done)
        w.failed.connect(self._scan_failed)
        self.scan_workers[proj.project_id] = w
        self.last_progress[proj.project_id] = None
        w.start()
        self._update_scan_panel()
        self.pages[0].refresh()

    def _scan_progress(self, pid, prog):
        self.last_progress[pid] = prog
        if self.st.project and pid == self.st.project.project_id:
            self._update_scan_panel()

    def _update_scan_panel(self):
        p = self.st.project
        if p is None or p.project_id not in self.scan_workers:
            self.scan_panel.hide()
            self.scan_btn.setText("Re-scan" if (self.st.db and self.st.db.scans()) else "Scan")
            self.scan_btn.setEnabled(p is not None)
            return
        self.scan_btn.setEnabled(False)
        self.scan_btn.setText("Scanning...")
        prog = self.last_progress.get(p.project_id)
        self.scan_panel.show()
        if prog is None:
            self.scan_text.setText(f"Scan in progress: starting ...   (results so far are not shown until the scan completes)")
            self.scan_bar.setRange(0, 0)
            return
        if prog.phase.startswith("Fingerprint"):
            self.scan_bar.setRange(0, max(prog.to_hash, 1))
            self.scan_bar.setValue(prog.hashed)
            detail = f"{prog.hashed:,} / {prog.to_hash:,} fingerprinted"
        else:
            self.scan_bar.setRange(0, 0)
            detail = f"{prog.dirs:,} folders"
        self.scan_text.setText(
            f"Scan in progress - {prog.phase}: {prog.files:,} files found ({human_size(prog.bytes)}), {detail}, "
            f"{prog.issues} inaccessible location(s).  Current: {prog.current[-70:]}")

    def cancel_active_scan(self):
        p = self.st.project
        if p and p.project_id in self.scan_workers:
            self.scan_workers[p.project_id].cancel.set()
            self.scan_text.setText("Cancelling ...")

    def _scan_done(self, pid, scan_id):
        self.scan_workers.pop(pid, None)
        proj = self.st.catalog.get(pid)
        name = proj.name if proj else pid
        status = "?"
        try:
            db = ProjectDB.open(proj)
            s = db.scan(scan_id)
            status = s["status"]
            msg = f"Scan of '{name}' finished: {status}, {s['files_found']:,} files"
            if s["inaccessible_count"]:
                msg += f", {s['inaccessible_count']} location(s) could not be checked"
            db.close()
        except Exception as e:
            msg = f"Scan of '{name}' finished ({e})"
        self.statusBar().showMessage(msg, 20000)
        # Only refresh the views if the scan belongs to the project that is on screen.
        if self.st.project and pid == self.st.project.project_id:
            self._reload_snapshots(select_latest=True)
            self._update_scan_panel()
            if status in ("Failed", "Incomplete", "Cancelled"):
                QMessageBox.warning(self, f"Scan {status.lower()}", msg + (
                    "\n\nThe previous completed scan remains the baseline." if status != "Failed" else
                    f"\n\nThe project folder could not be reached:\n{proj.root_path}\n\nNothing else was scanned."))
        self.pages[0].refresh()

    def _scan_failed(self, pid, err):
        self.scan_workers.pop(pid, None)
        self.statusBar().showMessage("Scan failed: " + err.splitlines()[0], 20000)
        if self.st.project and pid == self.st.project.project_id:
            self._update_scan_panel()
            self._reload_snapshots(select_latest=True)
            error(self, "Scan failed", err)
        self.pages[0].refresh()

    def closeEvent(self, ev):
        if self.scan_workers:
            names = ", ".join((self.st.catalog.get(p).name if self.st.catalog.get(p) else p) for p in self.scan_workers)
            if QMessageBox.question(self, "Scans running", f"Scans are running ({names}). Cancel them and exit?\n"
                                    "Cancelled scans are labelled Cancelled; baselines are kept.") != QMessageBox.Yes:
                ev.ignore()
                return
            for w in self.scan_workers.values():
                w.cancel.set()
            for w in list(self.scan_workers.values()):
                w.wait(15000)
        if self.st.db:
            self.st.db.close()
        ev.accept()


def status_html(status: str) -> str:
    return f"<span style='color:{STATUS_COLORS.get(status, '#374151')};font-weight:600'>{status}</span>"
