from __future__ import annotations

import os
from datetime import datetime, time

from PySide6.QtCore import QAbstractTableModel, QDate, QModelIndex, Qt, QTimer
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QDateEdit, QDoubleSpinBox, QHeaderView, QLineEdit,
                               QPushButton, QTableView, QVBoxLayout, QWidget)

from .. import export, reports
from ..paths import human_size, ts_to_iso
from .common import error, hbox, info, label, open_containing, open_path, save_path

COLS = [("File name", "name"), ("Relative path", "path"), ("Size", "size"), ("Type", "type"), ("Last modified", "modified")]


class FileModel(QAbstractTableModel):
    BLOCK = 500

    def __init__(self):
        super().__init__()
        self.db = None
        self.scan_id = None
        self.flt = {}
        self.total = 0
        self.rows = []
        self.sort_key = "path"
        self.desc = False

    def reset(self, db, scan_id, flt):
        self.beginResetModel()
        self.db, self.scan_id, self.flt = db, scan_id, flt
        self.rows = []
        self.total = 0
        if db is not None and scan_id:
            self.total, self.total_bytes = reports.files_count(db, scan_id, **flt)
            self._fetch()
        self.endResetModel()

    def _fetch(self):
        more = reports.files_page(self.db, self.scan_id, len(self.rows), self.BLOCK, self.sort_key, self.desc, **self.flt)
        self.rows.extend(more)

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent=QModelIndex()):
        return len(COLS)

    def canFetchMore(self, parent):
        return not parent.isValid() and len(self.rows) < self.total

    def fetchMore(self, parent):
        start = len(self.rows)
        more = reports.files_page(self.db, self.scan_id, start, self.BLOCK, self.sort_key, self.desc, **self.flt)
        if not more:
            self.total = start
            return
        self.beginInsertRows(QModelIndex(), start, start + len(more) - 1)
        self.rows.extend(more)
        self.endInsertRows()

    def data(self, idx, role=Qt.DisplayRole):
        if not idx.isValid():
            return None
        r = self.rows[idx.row()]
        c = idx.column()
        if role == Qt.DisplayRole:
            return [r["name"], r["rel_path"], human_size(r["size"]), r["ext"] or "(none)", ts_to_iso(r["mtime"])][c]
        if role == Qt.TextAlignmentRole and c == 2:
            return int(Qt.AlignRight | Qt.AlignVCenter)
        if role == Qt.ToolTipRole:
            return r["rel_path"]
        return None

    def headerData(self, s, o, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and o == Qt.Horizontal:
            return COLS[s][0]
        return None

    def sort(self, col, order=Qt.AscendingOrder):
        self.sort_key = COLS[col][1]
        self.desc = order == Qt.DescendingOrder
        self.reset(self.db, self.scan_id, self.flt)


class FilesPage(QWidget):
    def __init__(self, main):
        super().__init__()
        self.main = main
        v = QVBoxLayout(self)
        v.setContentsMargins(16, 14, 16, 14)
        v.addWidget(label("Files", "H1"))
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search name or path (space-separated words)")
        self.search.setAccessibleName("File search")
        self.ext = QLineEdit()
        self.ext.setPlaceholderText("Types e.g. pdf,docx")
        self.ext.setMaximumWidth(160)
        self.folder = QLineEdit()
        self.folder.setPlaceholderText("In folder (relative)")
        self.folder.setMaximumWidth(200)
        self.min_mb = QDoubleSpinBox()
        self.min_mb.setRange(0, 10_000_000)
        self.min_mb.setPrefix("min ")
        self.min_mb.setSuffix(" MB")
        self.min_mb.setDecimals(2)
        self.max_mb = QDoubleSpinBox()
        self.max_mb.setRange(0, 10_000_000)
        self.max_mb.setPrefix("max ")
        self.max_mb.setSuffix(" MB")
        self.max_mb.setSpecialValueText("max: any")
        self.max_mb.setDecimals(2)
        self.use_dates = QCheckBox("Modified between")
        self.d_from = QDateEdit(QDate.currentDate().addYears(-1))
        self.d_to = QDateEdit(QDate.currentDate())
        for d in (self.d_from, self.d_to):
            d.setCalendarPopup(True)
            d.setDisplayFormat("yyyy-MM-dd")
        reset = QPushButton("Clear filters")
        reset.clicked.connect(self._clear_filters)
        v.addLayout(hbox(self.search, self.ext, self.folder, stretch_end=False))
        v.addLayout(hbox(self.min_mb, self.max_mb, self.use_dates, self.d_from, self.d_to, reset))
        self.count = label("", None)
        self.count.setAccessibleDescription("Files count")
        self.b_open = QPushButton("Open file")
        self.b_folder = QPushButton("Open containing folder")
        self.b_export = QPushButton("Export inventory...")
        v.addLayout(hbox(self.count, None, self.b_open, self.b_folder, self.b_export, stretch_end=False))
        self.model = FileModel()
        self.view = QTableView()
        self.view.setModel(self.model)
        self.view.setAccessibleName("Files table")
        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.view.setAlternatingRowColors(True)
        self.view.verticalHeader().setVisible(False)
        self.view.verticalHeader().setDefaultSectionSize(24)
        self.view.setSortingEnabled(True)
        self.view.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.view.setColumnWidth(0, 260)
        self.view.doubleClicked.connect(lambda *_: self._open())
        v.addWidget(self.view, 1)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(250)
        self._timer.timeout.connect(self.apply)
        for w in (self.search, self.ext, self.folder):
            w.textChanged.connect(self._timer.start)
        for w in (self.min_mb, self.max_mb):
            w.valueChanged.connect(self._timer.start)
        for w in (self.d_from, self.d_to):
            w.dateChanged.connect(self._timer.start)
        self.use_dates.toggled.connect(self._timer.start)
        self.b_open.clicked.connect(self._open)
        self.b_folder.clicked.connect(self._open_folder)
        self.b_export.clicked.connect(self._export)
        self.st = None

    def _clear_filters(self):
        for w in (self.search, self.ext, self.folder):
            w.clear()
        self.min_mb.setValue(0)
        self.max_mb.setValue(0)
        self.use_dates.setChecked(False)

    def _filters(self):
        f = {"search": self.search.text().strip(), "ext": self.ext.text().strip(), "folder": self.folder.text().strip()}
        if self.min_mb.value() > 0:
            f["min_size"] = int(self.min_mb.value() * 1024 * 1024)
        if self.max_mb.value() > 0:
            f["max_size"] = int(self.max_mb.value() * 1024 * 1024)
        if self.use_dates.isChecked():
            f["mod_from"] = datetime.combine(self.d_from.date().toPython(), time.min).timestamp()
            f["mod_to"] = datetime.combine(self.d_to.date().toPython(), time.max).timestamp()
        return f

    def clear(self):
        self.st = None
        self.model.reset(None, None, {})
        self.count.setText("No completed snapshot")

    def load(self, st):
        self.st = st
        self.apply()

    def apply(self):
        st = self.st
        if st is None or st.db is None or not st.snapshot_id:
            self.model.reset(None, None, {})
            self.count.setText("No completed snapshot")
            return
        self.model.reset(st.db, st.snapshot_id, self._filters())
        s = st.snapshot
        self.count.setText(f"{self.model.total:,} files ({human_size(getattr(self.model, 'total_bytes', 0))}) "
                           f"in snapshot #{s['seq']} of {st.project.name}")

    def _current_full(self):
        idx = self.view.currentIndex()
        if not idx.isValid() or self.st is None:
            return None
        return os.path.join(self.st.project.root_path, self.model.rows[idx.row()]["rel_path"])

    def _open(self):
        p = self._current_full()
        if p and not open_path(p):
            error(self, "Open file", f"The file is no longer available at:\n{p}")

    def _open_folder(self):
        p = self._current_full()
        if p and not open_containing(p):
            error(self, "Open folder", f"The folder is no longer available:\n{os.path.dirname(p)}")

    def _export(self):
        st = self.st
        if not st or not st.snapshot_id:
            return
        s = st.snapshot
        path = save_path(self, "Export file inventory", f"{st.project.name} - inventory - snapshot {s['seq']}.xlsx")
        if not path:
            return
        try:
            n = export.export_inventory(st.db, st.snapshot_id, path)
        except Exception as e:
            error(self, "Export", str(e))
            return
        info(self, "Export", f"Exported {n:,} files of project '{st.project.name}' (snapshot #{s['seq']}) to\n{path}")
