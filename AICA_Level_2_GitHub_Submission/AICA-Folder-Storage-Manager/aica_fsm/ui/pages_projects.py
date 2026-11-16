from __future__ import annotations

import os

from PySide6.QtWidgets import (QCheckBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QInputDialog,
                               QLineEdit, QPushButton, QVBoxLayout, QWidget)

from ..paths import location_kind, normalize_root
from ..store import ProjectDB
from .common import sel_row, ask, error, fill, hbox, label, pick_folder, table, NumItem


class NewProjectDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("New Project")
        self.resize(720, 230)
        v = QVBoxLayout(self)
        v.addWidget(label("Choose a local folder, external drive, mapped network drive or a network folder "
                          "such as \\\\server\\share\\folder. Only this location and its subfolders will be scanned, "
                          "using your current Windows permissions.", "Hint", wrap=True))
        f = QFormLayout()
        self.name = QLineEdit()
        self.name.setAccessibleName("Project name")
        self.path = QLineEdit()
        self.path.setAccessibleName("Project folder path")
        self.path.setPlaceholderText(r"e.g. D:\Clients  or  \\server\share\folder")
        browse = QPushButton("Browse...")
        browse.clicked.connect(self._browse)
        row = QHBoxLayout()
        row.addWidget(self.path, 1)
        row.addWidget(browse)
        f.addRow("Project name:", self.name)
        f.addRow("Folder / drive / share:", row)
        v.addLayout(f)
        self.scan_now = QCheckBox("Start the first scan now")
        self.scan_now.setChecked(True)
        v.addWidget(self.scan_now)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText("Create Project")
        bb.accepted.connect(self._ok)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def _browse(self):
        p = pick_folder(self, "Select project folder")
        if p:
            self.path.setText(p)
            if not self.name.text().strip():
                self.name.setText(os.path.basename(p.rstrip("\\")) or p)

    def _ok(self):
        p = normalize_root(self.path.text())
        if not self.name.text().strip():
            error(self, "New Project", "Enter a project name.")
            return
        if not p:
            error(self, "New Project", "Choose a folder.")
            return
        try:
            ok = os.path.isdir(p)
            if ok:
                os.listdir(p)
        except OSError as e:
            ok = False
            reason = str(e)
        else:
            reason = "The folder does not exist or is not reachable."
        if not ok:
            error(self, "New Project", f"Cannot access:\n{p}\n\n{reason}\n\nThe project was not created.")
            return
        self.result_path = p
        self.accept()


class ProjectsPage(QWidget):
    def __init__(self, main):
        super().__init__()
        self.main = main
        v = QVBoxLayout(self)
        v.setContentsMargins(16, 14, 16, 14)
        v.addWidget(label("Projects", "H1"))
        v.addWidget(label("Each project has its own ID, its own folder and its own separate database "
                          "(file index, snapshots, duplicates, review queue, settings, audit history).", "Hint", wrap=True))
        self.btn_new = QPushButton("New Project...")
        self.btn_new.setObjectName("Primary")
        self.btn_open = QPushButton("Open")
        self.btn_scan = QPushButton("Scan / Re-scan")
        self.btn_rename = QPushButton("Rename...")
        self.btn_remove = QPushButton("Remove...")
        v.addLayout(hbox(self.btn_new, self.btn_open, self.btn_scan, self.btn_rename, self.btn_remove))
        self.t = table(["Name", "Scan path", "Location type", "Last completed scan", "Files", "Latest scan status",
                        "Project ID"], stretch_col=1)
        self.t.setAccessibleName("Projects table")
        v.addWidget(self.t, 1)
        self.btn_new.clicked.connect(self.new_project)
        self.btn_open.clicked.connect(self.open_selected)
        self.t.doubleClicked.connect(lambda *_: self.open_selected())
        self.btn_scan.clicked.connect(self.scan_selected)
        self.btn_rename.clicked.connect(self.rename_selected)
        self.btn_remove.clicked.connect(self.remove_selected)
        self.refresh()

    def load(self, st):
        self.refresh()

    def clear(self):
        pass

    def refresh(self):
        rows = []
        active = self.main.st.project.project_id if self.main.st.project else None
        for p in self.main.st.catalog.list():
            last, files, status = "", None, "Never scanned"
            try:
                db = ProjectDB.open(p)
                b = db.baseline()
                scans = db.scans()
                if b:
                    last = (b["finished"] or "")[:19].replace("T", " ")
                    files = b["files_found"]
                if scans:
                    status = scans[0]["status"]
                db.close()
            except Exception as e:
                status = f"Error: {e}"
            if p.project_id in self.main.scan_workers:
                status = "Running"
            name = p.name + ("   (open)" if p.project_id == active else "")
            rows.append([name, p.root_path, location_kind(p.root_path), last,
                         NumItem(files or 0, f"{files:,}" if files is not None else ""), status, p.project_id])
        fill(self.t, rows, colors={5: True})

    def _selected_id(self):
        r = sel_row(self.t)
        if r < 0:
            return None
        return self.t.item(r, 6).text()

    def new_project(self):
        d = NewProjectDialog(self)
        if d.exec() != QDialog.Accepted:
            return
        try:
            p = self.main.st.catalog.create(d.name.text(), d.result_path)
        except Exception as e:
            error(self, "New Project", str(e))
            return
        self.main.set_active(p)
        self.refresh()
        self.main.go("Overview")
        if d.scan_now.isChecked():
            self.main.start_scan(p)

    def open_selected(self):
        pid = self._selected_id()
        if pid:
            self.main.open_project(pid)
            self.refresh()

    def scan_selected(self):
        pid = self._selected_id()
        if pid:
            self.main.start_scan(self.main.st.catalog.get(pid))

    def rename_selected(self):
        pid = self._selected_id()
        if not pid:
            return
        p = self.main.st.catalog.get(pid)
        name, ok = QInputDialog.getText(self, "Rename project", "New name:", text=p.name)
        if ok and name.strip():
            try:
                self.main.st.catalog.rename(pid, name)
            except Exception as e:
                error(self, "Rename", str(e))
                return
            if self.main.st.project and self.main.st.project.project_id == pid:
                self.main.set_active(self.main.st.catalog.get(pid))
            self.refresh()

    def remove_selected(self):
        pid = self._selected_id()
        if not pid:
            return
        if pid in self.main.scan_workers:
            error(self, "Remove", "A scan of this project is running.")
            return
        p = self.main.st.catalog.get(pid)
        if not ask(self, "Remove project", f"Remove project '{p.name}' and its saved scan history?\n\n"
                   f"Files in {p.root_path} are NOT touched.", yes="Remove project"):
            return
        if self.main.st.project and self.main.st.project.project_id == pid:
            self.main.set_active(None)
        self.main.st.catalog.remove(pid)
        self.refresh()
