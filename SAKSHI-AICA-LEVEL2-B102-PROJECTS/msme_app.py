"""
MSME Verification System - PySide6 desktop application
======================================================

Modern Windows front-end for the Udyam (MSME) registration verifier.  All
verification work is done by udyam_core.py (unchanged logic from the original
Tkinter udyam_verifier.py).  No licence key is required.

Workflow (same as before):
  1. Load a CSV with a 'udyam_number' column, or type a single number.
  2. The app opens the OFFICIAL verify page and shows the portal's CAPTCHA.
  3. You type the CAPTCHA and press "Verify MSME".
  4. Details are shown only if the portal actually returned them.
  5. "Save & Next" appends the row to udyam_extractedresults.csv (Downloads).

Internet access to https://udyamregistration.gov.in is required.
Run:  python msme_app.py
"""

import csv
import datetime
import os
import sys
import threading
import time
import webbrowser
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import (QAction, QColor, QDesktopServices, QFont, QIcon,
                           QKeySequence, QPalette, QPixmap)
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QComboBox,
                               QDialog, QDialogButtonBox, QFileDialog,
                               QFormLayout, QFrame, QGridLayout, QHBoxLayout,
                               QHeaderView, QLabel, QLineEdit, QMainWindow,
                               QMessageBox, QPlainTextEdit, QProgressBar,
                               QPushButton, QScrollArea, QSizePolicy,
                               QSpinBox, QSplitter, QStyleFactory,
                               QTableWidget, QTableWidgetItem, QToolButton,
                               QVBoxLayout, QWidget)

from udyam_core import (CAT_ERROR, CAT_NOT_VERIFIED, CAT_PENDING,
                        CAT_VERIFIED, COLUMN_TITLES, DETAIL_COLUMNS,
                        ENTERPRISE_TYPES,
                        MIN_SECONDS_BETWEEN_LOOKUPS, PORTAL_HOME,
                        UDYAM_PATTERN, PortalClient, PortalError,
                        ResultsStore, clean, downloads_folder,
                        interpret_response, normalise_udyam, read_input,
                        status_category)

APP_NAME = "MSME Verification System"
APP_VERSION = "2.0.0"


def resource_path(rel):
    """Path to a bundled file - works from source and inside PyInstaller."""
    base = getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)
    return str(Path(base) / rel)


# --------------------------------------------------------------------------
# Look and feel
# --------------------------------------------------------------------------
LEVEL_COLORS = {            # level -> (text, background)
    "success": ("#1B7A2E", "#E6F4EA"),
    "warning": ("#9A5400", "#FFF4E5"),
    "error": ("#B00020", "#FDECEE"),
    "pending": ("#2F4F86", "#E8EEF8"),
    "info": ("#1A3F7A", "#E8EEF8"),
}
CATEGORY_LEVEL = {
    CAT_VERIFIED: "success",
    CAT_NOT_VERIFIED: "warning",
    CAT_ERROR: "error",
    CAT_PENDING: "pending",
}
CATEGORY_ICON = {CAT_VERIFIED: "✔", CAT_NOT_VERIFIED: "✖",
                 CAT_ERROR: "⚠", CAT_PENDING: "⏳"}

STYLESHEET = """
QMainWindow, QWidget#Central, QScrollArea, QWidget#LeftPane,
QWidget#RightPane { background: #F3F5F9; }
QFrame#Card { background: #FFFFFF; border: 1px solid #E2E7F0;
    border-bottom: 2px solid #D2D9E5; border-radius: 12px; }
QLabel#CardTitle { font-size: 11pt; font-weight: 600; color: #1B2A41; }
QLabel#Step { background: #1E4DB7; color: white; border-radius: 11px;
    font-weight: 700; min-width: 22px; max-width: 22px; min-height: 22px;
    max-height: 22px; qproperty-alignment: AlignCenter; }
QLabel#Muted { color: #5B6B82; }
QLabel#FieldLabel { color: #5B6B82; font-weight: 600; }
QLabel#FieldValue { color: #1B2A41; }
QFrame#Header { background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
    stop:0 #14306E, stop:1 #1E4DB7); }
QLabel#AppTitle { color: white; font-size: 18pt; font-weight: 700; }
QLabel#AppSubtitle { color: #C9D6F5; }
QPushButton { background: #FFFFFF; border: 1px solid #C9D2E0;
    border-radius: 8px; padding: 7px 14px; color: #1B2A41; }
QPushButton:hover { background: #F0F4FB; border-color: #9FB3D9; }
QPushButton:pressed { background: #E3EAF7; }
QPushButton:disabled { color: #A3AEC0; background: #F5F7FA;
    border-color: #E2E7F0; }
QPushButton#Primary, QPushButton#Verify { background: #1E4DB7;
    color: white; border: none; font-weight: 600; }
QPushButton#Primary:hover, QPushButton#Verify:hover { background: #1A43A0; }
QPushButton#Primary:disabled, QPushButton#Verify:disabled {
    background: #A9BBE3; color: #EEF2FA; }
QPushButton#Verify { font-size: 12pt; font-weight: 700; padding: 11px 26px;
    border-radius: 10px; }
QPushButton#Success { background: #1B7A2E; color: white; border: none;
    font-weight: 600; }
QPushButton#Success:hover { background: #166726; }
QPushButton#Success:disabled { background: #A8CDB2; color: #F1F7F2; }
QPushButton#HeaderBtn { background: rgba(255,255,255,0.12); color: white;
    border: 1px solid rgba(255,255,255,0.35); }
QPushButton#HeaderBtn:hover { background: rgba(255,255,255,0.22); }
QLineEdit, QSpinBox, QComboBox { border: 1px solid #C9D2E0;
    border-radius: 8px; padding: 7px 10px; background: white;
    selection-background-color: #1E4DB7; }
QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
    border: 2px solid #1E4DB7; padding: 6px 9px; }
QLineEdit[invalid="true"] { border: 2px solid #B00020; padding: 6px 9px; }
QLineEdit#CaptchaEdit { font-family: Consolas; font-size: 16pt; }
QProgressBar { border: none; background: #E3E8F1; border-radius: 4px;
    max-height: 8px; min-height: 8px; }
QProgressBar::chunk { background: #1E4DB7; border-radius: 4px; }
QLabel#Banner { border-radius: 10px; padding: 10px 14px; font-weight: 600; }
QLabel#Badge { border-radius: 12px; padding: 5px 14px; font-weight: 700; }
QLabel#Chip { border-radius: 10px; padding: 6px 12px; font-weight: 600; }
QLabel#Captcha { background: white; border: 1px dashed #B7C3D7;
    border-radius: 8px; color: #8A97AB; }
QLabel#BigNumber { font-family: Consolas; font-size: 17pt; font-weight: 700;
    color: #14306E; }
QToolButton#Disclosure { border: none; font-weight: 600; color: #1E4DB7;
    padding: 4px 0px; }
QTableWidget { background: white; border: 1px solid #E2E7F0;
    border-radius: 8px; gridline-color: #EEF1F6;
    alternate-background-color: #F8FAFD;
    selection-background-color: #DCE6FA; selection-color: #1B2A41; }
QHeaderView::section { background: #F3F6FB; color: #3A4A63; border: none;
    border-bottom: 1px solid #E2E7F0; padding: 6px 8px; font-weight: 600; }
QMenuBar { background: white; border-bottom: 1px solid #E2E7F0; }
QMenuBar::item { padding: 6px 12px; }
QMenuBar::item:selected { background: #E8EEF8; color: #14306E; }
QMenu { background: white; border: 1px solid #D5DBE5; }
QMenu::item { padding: 6px 28px 6px 20px; }
QMenu::item:selected { background: #E8EEF8; color: #14306E; }
QMenu::item:disabled { color: #A3AEC0; }
QStatusBar { background: white; border-top: 1px solid #E2E7F0;
    color: #5B6B82; }
QSplitter::handle { background: transparent; }
"""


def set_level(widget, level, text=None):
    """Colour a Banner / Badge / Chip label by level."""
    fg, bg = LEVEL_COLORS.get(level, LEVEL_COLORS["info"])
    widget.setStyleSheet(f"color: {fg}; background: {bg}; "
                         f"border: 1px solid {QColor(fg).lighter(260).name()};")
    if text is not None:
        widget.setText(text)


def set_invalid(edit, invalid):
    edit.setProperty("invalid", bool(invalid))
    edit.style().unpolish(edit)
    edit.style().polish(edit)


class Card(QFrame):
    """White rounded panel with an optional numbered title."""

    def __init__(self, title="", step=None, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(18, 14, 18, 16)
        self.body.setSpacing(10)
        if title:
            row = QHBoxLayout()
            row.setSpacing(8)
            if step is not None:
                s = QLabel(str(step))
                s.setObjectName("Step")
                row.addWidget(s)
            t = QLabel(title)
            t.setObjectName("CardTitle")
            row.addWidget(t)
            row.addStretch(1)
            self.header_row = row
            self.body.addLayout(row)


class Bridge(QObject):
    """Carries results from worker threads back to the GUI thread."""
    done = Signal(str, int, str, object)      # tag, generation, kind, payload


# --------------------------------------------------------------------------
# Dialogs
# --------------------------------------------------------------------------
class ManualEntryDialog(QDialog):
    """Record what the official portal shows when you verified in a browser."""

    RESULTS = ["Verified (manual)", "Not found (manual)", "Failed (manual)"]

    def __init__(self, number, prefill, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Manual entry - {number}")
        self.setMinimumWidth(620)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 18, 20, 16)
        info = QLabel("Copy exactly what the official portal shows. Leave "
                      "unavailable fields blank.")
        info.setWordWrap(True)
        lay.addWidget(info)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setVerticalSpacing(8)
        self.entries = {}
        for col in DETAIL_COLUMNS:
            e = QLineEdit(prefill.get(col, ""))
            if col == "enterprise_type":
                e.setPlaceholderText("Micro / Small / Medium (latest year)")
            form.addRow(COLUMN_TITLES[col], e)
            self.entries[col] = e
        self.outcome = QComboBox()
        self.outcome.addItems(self.RESULTS)
        form.addRow("Portal result", self.outcome)
        self.note = QLineEdit()
        form.addRow("Note / error", self.note)
        lay.addLayout(form)
        bb = QDialogButtonBox()
        save = bb.addButton("Save && Next", QDialogButtonBox.ButtonRole.AcceptRole)
        save.setObjectName("Primary")
        bb.addButton(QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self._check)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.row = None

    def _check(self):
        row = {c: clean(self.entries[c].text()) for c in DETAIL_COLUMNS}
        kind = row["enterprise_type"]
        row["enterprise_type"] = ENTERPRISE_TYPES.get(kind.lower(), kind)
        status = self.outcome.currentText()
        if status.startswith("Verified") and not row["enterprise_name"]:
            QMessageBox.warning(self, "Missing name",
                                "Enter the enterprise name shown by the portal, "
                                "or choose another result.")
            set_invalid(self.entries["enterprise_name"], True)
            return
        row.update(status=status, error=clean(self.note.text()))
        self.row = row
        self.accept()


class TextDialog(QDialog):
    def __init__(self, title, text, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(780, 560)
        lay = QVBoxLayout(self)
        box = QPlainTextEdit()
        box.setReadOnly(True)
        box.setPlainText(text)
        box.setFont(QFont("Consolas", 10))
        lay.addWidget(box)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)


# --------------------------------------------------------------------------
# Main window
# --------------------------------------------------------------------------
TABLE_COLS = ["#", "Udyam Registration No.", "Name of Enterprise",
              "MSME Type", "Status", "Remarks"]
COL_TYPE, COL_STATUS, COL_REMARKS = 3, 4, 5


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.numbers = []
        self.index = -1
        self.row_offset = 0          # table row of numbers[0]
        self.source_label = ""
        self.skip_done = True
        self.client = PortalClient()
        self.busy = False
        self._submitting = False     # busy with a verify (not a CAPTCHA load)
        self.gen = 0                 # bumps on Reset; stale results ignored
        self.pending = None          # result awaiting "Save & Next"
        self.last_error = ""
        self.retry_note = ""
        self.last_visible = ""
        self.last_request_time = 0.0
        self.store = ResultsStore()
        self.output_ready = False
        self.done_numbers = set()
        self.row_cats = []           # category of each table row

        self.bridge = Bridge()
        self.bridge.done.connect(self._on_done)

        self.setWindowTitle(APP_NAME)
        self.resize(1280, 820)
        self.setMinimumSize(760, 600)
        self._build_menu()
        self._build_ui()
        self._clear_details()
        self._update_counts()
        self._set_state()
        self.banner("Load a CSV file or type a Udyam Registration Number to "
                    "begin.", "info")

    # ---------------- menu ----------------
    def _action(self, menu, text, slot, shortcut=None):
        a = QAction(text, self)
        if shortcut:
            a.setShortcut(QKeySequence(shortcut))
        a.triggered.connect(slot)
        menu.addAction(a)
        return a

    def _build_menu(self):
        mb = self.menuBar()
        m = mb.addMenu("&File")
        self.act_open = self._action(m, "Open CSV file...", self.browse, "Ctrl+O")
        self._action(m, "Save CSV template...", self.save_template)
        m.addSeparator()
        self.act_export = self._action(m, "Export results to Excel...",
                                       self.export_excel, "Ctrl+E")
        self._action(m, "Open results folder", self.open_results_folder)
        m.addSeparator()
        self._action(m, "Exit", self.close, "Alt+F4")

        m = mb.addMenu("&Verification")
        self.act_verify = self._action(m, "Verify MSME", self.submit, "Ctrl+Return")
        self.act_retry = self._action(m, "New CAPTCHA / Retry", self.load_captcha, "F5")
        self.act_save = self._action(m, "Save && Next", self.save_next, "Ctrl+S")
        self.act_skip = self._action(m, "Skip number", self.skip)
        m.addSeparator()
        self.act_manual = self._action(m, "Manual entry...", self.manual_entry)
        self._action(m, "Open official portal", self.open_portal)
        self.act_view = self._action(m, "View last portal response",
                                     self.view_response)
        m.addSeparator()
        self.act_reset = self._action(m, "Clear / Reset", self.reset, "Ctrl+R")

        m = mb.addMenu("&Help")
        self._action(m, "How to use", self.show_help, "F1")
        self._action(m, "About " + APP_NAME, self.show_about)

    # ---------------- layout ----------------
    def _build_ui(self):
        central = QWidget()
        central.setObjectName("Central")
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.setCentralWidget(central)

        # Header
        header = QFrame()
        header.setObjectName("Header")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(24, 14, 24, 14)
        icon_lbl = QLabel()
        pm = QPixmap(resource_path("assets/app.png"))
        if not pm.isNull():
            icon_lbl.setPixmap(pm.scaled(44, 44, Qt.AspectRatioMode.KeepAspectRatio,
                                         Qt.TransformationMode.SmoothTransformation))
            hl.addWidget(icon_lbl)
            hl.addSpacing(10)
        tbox = QVBoxLayout()
        tbox.setSpacing(0)
        t = QLabel(APP_NAME)
        t.setObjectName("AppTitle")
        s = QLabel("Udyam Registration verification on the official "
                   "Government of India portal  ·  CAPTCHA entered by you")
        s.setObjectName("AppSubtitle")
        s.setWordWrap(True)
        tbox.addWidget(t)
        tbox.addWidget(s)
        hl.addLayout(tbox, 1)
        help_btn = QPushButton("How to use")
        help_btn.setObjectName("HeaderBtn")
        help_btn.clicked.connect(self.show_help)
        hl.addWidget(help_btn)
        root.addWidget(header)

        # Body
        body = QWidget()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(18, 14, 18, 12)
        bl.setSpacing(12)
        self.banner_lbl = QLabel()
        self.banner_lbl.setObjectName("Banner")
        self.banner_lbl.setWordWrap(True)
        self.banner_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        bl.addWidget(self.banner_lbl)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(12)
        self.splitter.addWidget(self._build_left())
        self.splitter.addWidget(self._build_right())
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes([440, 820])
        bl.addWidget(self.splitter, 1)
        root.addWidget(body, 1)

        self.file_status = QLabel()
        self.statusBar().addWidget(self.file_status, 1)
        net = QLabel("Internet connection required  ·  "
                     "udyamregistration.gov.in")
        self.statusBar().addPermanentWidget(net)
        self._show_results_path()

    def _build_left(self):
        pane = QWidget()
        pane.setObjectName("LeftPane")
        lay = QVBoxLayout(pane)
        lay.setContentsMargins(0, 0, 4, 0)
        lay.setSpacing(12)

        # 1. Input
        c = Card("Choose what to verify", 1)
        self.btn_browse = QPushButton("\U0001F4C2  Load CSV file...")
        self.btn_browse.setObjectName("Primary")
        self.btn_browse.setToolTip("CSV must have a column named udyam_number")
        self.btn_browse.clicked.connect(self.browse)
        c.body.addWidget(self.btn_browse)
        self.file_lbl = QLabel("No file selected")
        self.file_lbl.setObjectName("Muted")
        self.file_lbl.setWordWrap(True)
        c.body.addWidget(self.file_lbl)
        or_lbl = QLabel("— or verify a single number —")
        or_lbl.setObjectName("Muted")
        or_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        c.body.addWidget(or_lbl)
        row = QHBoxLayout()
        self.single_edit = QLineEdit()
        self.single_edit.setPlaceholderText("UDYAM-MH-01-0001234")
        self.single_edit.setFont(QFont("Consolas", 11))
        self.single_edit.returnPressed.connect(self.verify_single)
        self.single_edit.textEdited.connect(lambda _: (set_invalid(self.single_edit, False),
                                                       self.single_err.hide()))
        row.addWidget(self.single_edit, 1)
        self.btn_single = QPushButton("Start")
        self.btn_single.clicked.connect(self.verify_single)
        row.addWidget(self.btn_single)
        c.body.addLayout(row)
        self.single_err = QLabel("Format must be UDYAM-XX-00-0000000 "
                                 "(e.g. UDYAM-MH-01-0001234).")
        self.single_err.setStyleSheet("color: #B00020;")
        self.single_err.setWordWrap(True)
        self.single_err.hide()
        c.body.addWidget(self.single_err)
        lay.addWidget(c)

        # 2. Current number
        c = Card("Current number", 2)
        self.progress_lbl = QLabel("Processing 0 of 0")
        self.progress_lbl.setObjectName("Muted")
        c.header_row.addWidget(self.progress_lbl)
        self.number_lbl = QLabel("—")
        self.number_lbl.setObjectName("BigNumber")
        self.number_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        c.body.addWidget(self.number_lbl)
        self.pbar = QProgressBar()
        self.pbar.setTextVisible(False)
        self.pbar.setRange(0, 1)
        self.pbar.setValue(0)
        c.body.addWidget(self.pbar)
        lay.addWidget(c)

        # 3. CAPTCHA
        c = Card("Enter the portal's CAPTCHA", 3)
        self.captcha_lbl = QLabel("(no CAPTCHA loaded)")
        self.captcha_lbl.setObjectName("Captcha")
        self.captcha_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.captcha_lbl.setMinimumHeight(110)
        c.body.addWidget(self.captcha_lbl)
        hint = QLabel("Type exactly as shown — CAPTCHA is case sensitive.")
        hint.setObjectName("Muted")
        c.body.addWidget(hint)
        self.captcha_edit = QLineEdit()
        self.captcha_edit.setObjectName("CaptchaEdit")
        self.captcha_edit.setPlaceholderText("CAPTCHA")
        self.captcha_edit.returnPressed.connect(self.submit)
        self.captcha_edit.textEdited.connect(lambda _: set_invalid(self.captcha_edit, False))
        c.body.addWidget(self.captcha_edit)
        row = QHBoxLayout()
        self.btn_verify = QPushButton("✔  Verify MSME")
        self.btn_verify.setObjectName("Verify")
        self.btn_verify.clicked.connect(self.submit)
        row.addWidget(self.btn_verify, 1)
        self.btn_retry = QPushButton("↻  New CAPTCHA")
        self.btn_retry.setToolTip("Load a fresh CAPTCHA from the portal (F5)")
        self.btn_retry.clicked.connect(self.load_captcha)
        row.addWidget(self.btn_retry)
        c.body.addLayout(row)
        self.busy_bar = QProgressBar()
        self.busy_bar.setRange(0, 0)           # indeterminate animation
        self.busy_bar.setTextVisible(False)
        self.busy_bar.setVisible(False)
        c.body.addWidget(self.busy_bar)
        lay.addWidget(c)

        # Advanced (collapsible)
        c = Card()
        self.adv_btn = QToolButton()
        self.adv_btn.setObjectName("Disclosure")
        self.adv_btn.setText("Advanced options")
        self.adv_btn.setCheckable(True)
        self.adv_btn.setArrowType(Qt.ArrowType.RightArrow)
        self.adv_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        c.body.addWidget(self.adv_btn)
        adv = QWidget()
        al = QGridLayout(adv)
        al.setContentsMargins(0, 0, 0, 0)
        al.setVerticalSpacing(8)
        al.addWidget(QLabel("Results file:"), 0, 0)
        self.adv_path = QLabel()
        self.adv_path.setObjectName("Muted")
        self.adv_path.setWordWrap(True)
        self.adv_path.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        al.addWidget(self.adv_path, 0, 1)
        self.btn_change_out = QPushButton("Change...")
        self.btn_change_out.clicked.connect(self.change_results_file)
        al.addWidget(self.btn_change_out, 0, 2)
        al.addWidget(QLabel("Pause between lookups:"), 1, 0)
        self.gap_spin = QSpinBox()
        self.gap_spin.setRange(MIN_SECONDS_BETWEEN_LOOKUPS, 60)
        self.gap_spin.setValue(MIN_SECONDS_BETWEEN_LOOKUPS)
        self.gap_spin.setSuffix(" seconds")
        self.gap_spin.setToolTip("Minimum wait before contacting the portal "
                                 "again (cannot go below "
                                 f"{MIN_SECONDS_BETWEEN_LOOKUPS} s).")
        al.addWidget(self.gap_spin, 1, 1, 1, 2)
        self.btn_view = QPushButton("View last portal response")
        self.btn_view.clicked.connect(self.view_response)
        al.addWidget(self.btn_view, 2, 0, 1, 3)
        al.setColumnStretch(1, 1)
        adv.setVisible(False)
        c.body.addWidget(adv)

        def toggle(on):
            adv.setVisible(on)
            self.adv_btn.setArrowType(Qt.ArrowType.DownArrow if on
                                      else Qt.ArrowType.RightArrow)
        self.adv_btn.toggled.connect(toggle)
        lay.addWidget(c)
        lay.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(pane)
        scroll.setMinimumWidth(360)
        return scroll

    def _build_right(self):
        pane = QWidget()
        pane.setObjectName("RightPane")
        lay = QVBoxLayout(pane)
        lay.setContentsMargins(4, 0, 0, 0)
        lay.setSpacing(12)

        # Details
        c = Card("Details returned by the portal")
        self.badge = QLabel()
        self.badge.setObjectName("Badge")
        c.header_row.addWidget(self.badge)
        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(8)
        self.detail_lbls = {}
        for i, col in enumerate(DETAIL_COLUMNS):
            r, cc = divmod(i, 2)
            if col == "enterprise_address":
                r, cc = 3, 0
            name = QLabel(COLUMN_TITLES[col])
            name.setObjectName("FieldLabel")
            val = QLabel("")
            val.setObjectName("FieldValue")
            val.setWordWrap(True)
            val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            val.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            box = QVBoxLayout()
            box.setSpacing(2)
            box.addWidget(name)
            box.addWidget(val)
            span = 2 if col == "enterprise_address" else 1
            grid.addLayout(box, r, cc, 1, span)
            self.detail_lbls[col] = val
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        c.body.addLayout(grid)
        self.note_lbl = QLabel("")
        self.note_lbl.setWordWrap(True)
        self.note_lbl.setStyleSheet("color: #9A5400;")
        c.body.addWidget(self.note_lbl)
        row = QHBoxLayout()
        self.btn_save = QPushButton("\U0001F4BE  Save && Next")
        self.btn_save.setObjectName("Success")
        self.btn_save.clicked.connect(self.save_next)
        row.addWidget(self.btn_save)
        self.btn_skip = QPushButton("Skip number")
        self.btn_skip.clicked.connect(self.skip)
        row.addWidget(self.btn_skip)
        self.btn_manual = QPushButton("Manual entry...")
        self.btn_manual.setToolTip("Record what the portal shows in your browser")
        self.btn_manual.clicked.connect(self.manual_entry)
        row.addWidget(self.btn_manual)
        self.btn_portal = QPushButton("Open official portal ↗")
        self.btn_portal.clicked.connect(self.open_portal)
        row.addWidget(self.btn_portal)
        row.addStretch(1)
        c.body.addLayout(row)
        lay.addWidget(c)

        # Session results
        c = Card("Results this session")
        self.chips = {}
        chip_row = QHBoxLayout()
        chip_row.setSpacing(8)
        for cat in (CAT_VERIFIED, CAT_NOT_VERIFIED, CAT_ERROR, CAT_PENDING):
            chip = QLabel()
            chip.setObjectName("Chip")
            set_level(chip, CATEGORY_LEVEL[cat])
            chip_row.addWidget(chip)
            self.chips[cat] = chip
        chip_row.addStretch(1)
        c.body.addLayout(chip_row)
        self.table = QTableWidget(0, len(TABLE_COLS))
        self.table.setHorizontalHeaderLabels(TABLE_COLS)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setWordWrap(False)
        hh = self.table.horizontalHeader()
        # fixed widths; the enterprise name takes the spare room.  Long
        # remarks show in full as a tooltip.
        hh.setStretchLastSection(False)
        hh.setMinimumSectionSize(36)
        for col, width in ((0, 34), (1, 165), (COL_TYPE, 85),
                           (COL_STATUS, 210), (COL_REMARKS, 130)):
            hh.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
            hh.resizeSection(col, width)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setMinimumHeight(180)
        c.body.addWidget(self.table, 1)
        row = QHBoxLayout()
        self.btn_export = QPushButton("\U0001F4CA  Export to Excel")
        self.btn_export.setObjectName("Primary")
        self.btn_export.clicked.connect(self.export_excel)
        row.addWidget(self.btn_export)
        btn_folder = QPushButton("Open results folder")
        btn_folder.clicked.connect(self.open_results_folder)
        row.addWidget(btn_folder)
        row.addStretch(1)
        self.btn_reset = QPushButton("Clear / Reset")
        self.btn_reset.clicked.connect(self.reset)
        row.addWidget(self.btn_reset)
        c.body.addLayout(row)
        lay.addWidget(c, 1)

        # scrolls instead of squashing when the window is short
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(pane)
        return scroll

    def resizeEvent(self, event):
        # Narrow window: stack the two columns instead of side by side.
        narrow = self.width() < 1000
        want = Qt.Orientation.Vertical if narrow else Qt.Orientation.Horizontal
        if self.splitter.orientation() != want:
            self.splitter.setOrientation(want)
            if narrow:
                self.splitter.setSizes([520, 480])
            else:
                self.splitter.setSizes([440, max(500, self.width() - 480)])
        super().resizeEvent(event)

    # ---------------- small UI helpers ----------------
    def banner(self, text, level="info"):
        set_level(self.banner_lbl, level, text)

    def _show_results_path(self):
        self.file_status.setText(f"Results file: {self.store.path}")
        self.adv_path.setText(str(self.store.path))

    def _show_captcha_text(self, text):
        self.captcha_lbl.setPixmap(QPixmap())
        self.captcha_lbl.setText(text)

    def _has_num(self):
        return 0 <= self.index < len(self.numbers)

    def _queue_active(self):
        return self._has_num()

    def _set_badge(self, category=None, text=None):
        if category is None:
            set_level(self.badge, "pending", "Awaiting verification")
        else:
            set_level(self.badge, CATEGORY_LEVEL[category],
                      f"{CATEGORY_ICON[category]}  {text or category}")

    def _set_state(self):
        has_num = self._has_num()
        idle = not self.busy
        can_verify = (idle and has_num and self.client.form_ok
                      and self.pending is None)
        for w, ok in (
                (self.btn_browse, idle), (self.act_open, idle),
                (self.btn_single, idle), (self.single_edit, idle),
                (self.btn_verify, can_verify), (self.act_verify, can_verify),
                (self.captcha_edit, can_verify),
                (self.btn_retry, idle and has_num), (self.act_retry, idle and has_num),
                (self.btn_save, idle and has_num and self.pending is not None),
                (self.act_save, idle and has_num and self.pending is not None),
                (self.btn_skip, idle and has_num), (self.act_skip, idle and has_num),
                (self.btn_manual, idle and has_num), (self.act_manual, idle and has_num),
                (self.btn_view, bool(self.last_visible)),
                (self.act_view, bool(self.last_visible)),
                (self.btn_reset, idle), (self.act_reset, idle),
                (self.btn_change_out, idle and not has_num)):
            w.setEnabled(ok)
        self.busy_bar.setVisible(self.busy)
        self.btn_verify.setText("Verifying…" if self.busy and self._submitting
                                else "✔  Verify MSME")

    # ---------------- results table ----------------
    def _add_table_row(self, number):
        r = self.table.rowCount()
        self.table.insertRow(r)
        self.row_cats.append(CAT_PENDING)
        for c, text in enumerate([str(r + 1), number] + [""] * (len(TABLE_COLS) - 2)):
            item = QTableWidgetItem(text)
            if c == 1:
                item.setFont(QFont("Consolas", 10))
            self.table.setItem(r, c, item)
        self._paint_status(r, CAT_PENDING, "Pending")
        return r

    def _paint_status(self, r, cat, raw):
        fg, bg = LEVEL_COLORS[CATEGORY_LEVEL[cat]]
        label = f"{CATEGORY_ICON[cat]}  {cat}"
        if raw and raw.lower() not in (cat.lower(), "pending"):
            label += f" ({raw})"
        item = QTableWidgetItem(label)
        item.setForeground(QColor(fg))
        item.setBackground(QColor(bg))
        f = item.font()
        f.setBold(True)
        item.setFont(f)
        item.setToolTip(f"Saved status: {raw}" if raw else cat)
        self.table.setItem(r, COL_STATUS, item)
        self.row_cats[r] = cat

    def _update_table_row(self, idx, row, raw_status=None):
        r = self.row_offset + idx
        if not (0 <= r < self.table.rowCount()):
            return
        status = raw_status or row.get("status", "")
        self.table.item(r, 2).setText(row.get("enterprise_name", ""))
        self.table.item(r, 2).setToolTip(row.get("enterprise_name", ""))
        self.table.item(r, COL_TYPE).setText(row.get("enterprise_type", ""))
        self._paint_status(r, status_category(status), status)
        remark = QTableWidgetItem(row.get("error", ""))
        remark.setToolTip(row.get("error", ""))
        self.table.setItem(r, COL_REMARKS, remark)
        self._update_counts()

    def _update_counts(self):
        counts = {k: 0 for k in self.chips}
        for cat in self.row_cats:
            counts[cat] += 1
        for cat, chip in self.chips.items():
            chip.setText(f"{CATEGORY_ICON[cat]}  {cat}: {counts[cat]}")

    # ---------------- background work ----------------
    def run_bg(self, tag, label, func, *args):
        self.busy = True
        self._submitting = tag == "submit"
        self._set_state()
        self.banner(label, "info")
        gen = self.gen

        def worker():
            try:
                kind, payload = "ok", func(*args)
            except PortalError as e:
                kind, payload = "err", str(e)
            except Exception as e:     # unexpected - never crash the GUI
                kind, payload = "err", f"Unexpected error: {e!r}"
            self.bridge.done.emit(tag, gen, kind, payload)

        # daemon thread: closing the app never waits for a slow portal
        threading.Thread(target=worker, daemon=True).start()

    def _on_done(self, tag, gen, kind, payload):
        if gen != self.gen:
            return                     # result of a list that was reset
        self.busy = False
        self._submitting = False
        if tag == "captcha":
            self._after_captcha(kind, payload)
        else:
            self._after_submit(kind, payload)
        self._set_state()

    # ---------------- starting a list ----------------
    def _confirm_abandon(self):
        if not self._queue_active():
            return True
        left = len(self.numbers) - self.index
        ans = QMessageBox.question(
            self, "Stop current list?",
            f"{left} number(s) of the current list are not finished.\n\n"
            "Stop the current list and start the new one? Rows already saved "
            "stay in the results file.")
        return ans == QMessageBox.StandardButton.Yes

    def browse(self):
        if self.busy:
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Select CSV with a 'udyam_number' column",
            str(downloads_folder()), "CSV files (*.csv);;All files (*.*)")
        if path:
            self.load_csv(path)

    def load_csv(self, path):
        try:
            numbers = read_input(path)
        except UnicodeDecodeError:
            QMessageBox.critical(self, "Cannot read CSV",
                                 "The file is not UTF-8 text. In Excel use "
                                 "File > Save As > 'CSV UTF-8 (Comma delimited)'.")
            return
        except Exception as e:
            QMessageBox.critical(self, "Cannot read CSV", str(e))
            return
        if not numbers:
            QMessageBox.warning(self, "No numbers",
                                "The 'udyam_number' column is empty.")
            return
        if not self._confirm_abandon():
            return
        if not self._prepare_output(ask=True):
            return
        bad = sum(1 for n in numbers if not UDYAM_PATTERN.match(n))
        note = f"  ·  {bad} not in UDYAM format" if bad else ""
        self.file_lbl.setText(f"{os.path.basename(path)}  ({len(numbers)} "
                              f"numbers){note}")
        self._start_queue(numbers, skip_done=True)

    def verify_single(self):
        if self.busy:
            return
        num = normalise_udyam(self.single_edit.text())
        self.single_edit.setText(num)
        if not UDYAM_PATTERN.match(num):
            set_invalid(self.single_edit, True)
            self.single_err.show()
            self.single_edit.setFocus()
            return
        if not self._confirm_abandon():
            return
        if not self._prepare_output(ask=not self.output_ready):
            return
        self.file_lbl.setText(f"Single number: {num}")
        # an explicitly typed number is always checked again, even if an
        # earlier run already marked it Verified
        self._start_queue([num], skip_done=False)

    def _start_queue(self, numbers, skip_done):
        self.gen += 1
        self.client = PortalClient()
        self.numbers = numbers
        self.skip_done = skip_done
        self.row_offset = self.table.rowCount()
        for n in numbers:
            self._add_table_row(n)
        self._update_counts()
        self.pbar.setRange(0, len(numbers))
        self.pbar.setValue(0)
        self.index = -1
        self.next_number()

    def _prepare_output(self, ask):
        """Same rules as the original app: append (skipping numbers already
        Verified) or start a new file."""
        if not ask and self.output_ready:
            return True
        self.done_numbers = set()
        if self.store.exists():
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Icon.Question)
            box.setWindowTitle("Results file exists")
            box.setText(f"<b>{self.store.path.name}</b> already exists in "
                        f"{self.store.path.parent}.")
            box.setInformativeText(
                "Append – keep earlier rows (numbers already marked "
                "Verified will be skipped)\n"
                "Start new file – overwrite it with a new, empty file\n"
                "Cancel – stop")
            b_append = box.addButton("Append", QMessageBox.ButtonRole.AcceptRole)
            b_new = box.addButton("Start new file", QMessageBox.ButtonRole.DestructiveRole)
            box.addButton(QMessageBox.StandardButton.Cancel)
            box.setDefaultButton(b_append)
            box.exec()
            clicked = box.clickedButton()
            if clicked is b_append:
                try:
                    self.done_numbers = self.store.verified_numbers()
                except Exception as e:
                    QMessageBox.critical(self, "Cannot read results file", str(e))
                    return False
                self.output_ready = True
                return True
            if clicked is not b_new:
                return False
        try:
            self.store.start_new()
        except OSError as e:
            QMessageBox.critical(self, "Cannot write results file",
                                 f"{e}\n\nIs the file open in Excel? Close it and retry.")
            return False
        self.output_ready = True
        return True

    def write_row(self, row):
        while True:
            try:
                self.store.append(row)
                break
            except OSError as e:
                ans = QMessageBox.warning(
                    self, "Cannot save row",
                    f"{e}\n\nIf the results file is open in Excel, close it "
                    "and press Retry.",
                    QMessageBox.StandardButton.Retry | QMessageBox.StandardButton.Cancel)
                if ans != QMessageBox.StandardButton.Retry:
                    return False
        self._update_table_row(self.index, row)
        return True

    # ---------------- per-number flow ----------------
    def current(self):
        return self.numbers[self.index]

    def _clear_details(self):
        for lbl in self.detail_lbls.values():
            lbl.setText("—")
        self.note_lbl.setText("")
        self.pending = None
        self._set_badge(None)

    def next_number(self):
        self._clear_details()
        self.last_error = ""
        self.captcha_edit.clear()
        while True:
            self.index += 1
            self.pbar.setValue(self.index)
            if self.index >= len(self.numbers):
                self._finished()
                return
            num = self.current()
            self.progress_lbl.setText(f"Processing {self.index + 1} of "
                                      f"{len(self.numbers)}")
            self.number_lbl.setText(num)
            self.table.selectRow(self.row_offset + self.index)
            if self.skip_done and num in self.done_numbers:
                # already verified in an earlier run - not checked again
                self._update_table_row(self.index, {
                    "status": "Verified",
                    "error": "Already Verified in the results file "
                             "(earlier run) - not checked again."})
                continue
            if not UDYAM_PATTERN.match(num):
                self.write_row({"udyam_number": num, "status": "Invalid format",
                                "error": "Not in UDYAM-XX-00-0000000 format; "
                                         "not sent to portal."})
                continue
            break
        self.load_captcha()

    def _finished(self):
        n = len(self.numbers)
        self.number_lbl.setText("—")
        self.progress_lbl.setText(f"Finished {n} of {n}")
        self._show_captcha_text("(done)")
        self.client.form_ok = False
        self.banner(f"All numbers processed. Results saved to {self.store.path}. "
                    "Export to Excel, or load / type another number to verify "
                    "another record.", "success")
        self.single_edit.clear()
        self._set_state()
        self.single_edit.setFocus()

    def load_captcha(self):
        if not self._has_num() or self.busy:
            return
        self._clear_details()
        self.captcha_edit.clear()
        set_invalid(self.captcha_edit, False)
        self._show_captcha_text("Loading CAPTCHA…")
        gap = max(MIN_SECONDS_BETWEEN_LOOKUPS, self.gap_spin.value())
        wait = gap - (time.time() - self.last_request_time)
        if wait > 0:
            self.banner(f"Waiting {wait:.0f}s before contacting the portal…",
                        "info")
            self.busy = True
            self._set_state()
            gen = self.gen
            QTimer.singleShot(int(wait * 1000), lambda: self._load_now(gen))
        else:
            self._load_now(self.gen)

    def _load_now(self, gen):
        if gen != self.gen:
            return
        self.busy = False
        self.last_request_time = time.time()
        self.run_bg("captcha", "Loading official verify page and CAPTCHA…",
                    self.client.load_form)

    def _after_captcha(self, kind, payload):
        if kind == "err":
            self.last_error = payload
            self.retry_note = ""
            self._show_captcha_text("(CAPTCHA unavailable)")
            self._set_badge(CAT_ERROR, "Technical failure")
            self.banner(f"Technical failure: {payload}\nPress 'New CAPTCHA' to "
                        "retry, 'Skip number', or use 'Open official portal' + "
                        "'Manual entry'.", "error")
            return
        pm = QPixmap()
        if not pm.loadFromData(payload):
            self.last_error = "Could not display CAPTCHA image."
            self._show_captcha_text("(CAPTCHA unavailable)")
            self._set_badge(CAT_ERROR, "Technical failure")
            self.banner(self.last_error + " Press 'New CAPTCHA' to retry.", "error")
            return
        if pm.width() < 300:          # enlarge for readability
            pm = pm.scaled(pm.width() * 2, pm.height() * 2,
                           Qt.AspectRatioMode.IgnoreAspectRatio,
                           Qt.TransformationMode.FastTransformation)
        if pm.width() > 380 or pm.height() > 140:      # keep the card tidy
            pm = pm.scaled(380, 140, Qt.AspectRatioMode.KeepAspectRatio,
                           Qt.TransformationMode.SmoothTransformation)
        self.captcha_lbl.setText("")
        self.captcha_lbl.setPixmap(pm)
        self._set_state()
        self.captcha_edit.setFocus()
        if self.retry_note:
            self.banner(self.retry_note + "\nPlease enter the NEW CAPTCHA and "
                        "press Verify MSME, or Skip / use Manual entry.", "warning")
            self.retry_note = ""
        else:
            self.banner("Please enter the CAPTCHA (exactly as shown, case "
                        "sensitive), then press Verify MSME.", "info")

    def submit(self):
        if self.busy or not self.client.form_ok or self.pending is not None:
            return
        text = self.captcha_edit.text().strip()
        if not text:
            set_invalid(self.captcha_edit, True)
            self.banner("Please enter the CAPTCHA shown above.", "warning")
            self.captcha_edit.setFocus()
            return
        self.last_request_time = time.time()
        self.run_bg("submit", "Fetching details from the official portal…",
                    self._submit_and_parse, self.current(), text)

    def _submit_and_parse(self, number, captcha):
        """Runs in a background thread: POST the form, interpret the page."""
        _, page = self.client.submit(number, captcha)
        return interpret_response(number, page)

    def _after_submit(self, kind, payload):
        num = self.current()
        if kind == "err":
            self.last_error = payload
            self._set_badge(CAT_ERROR, "Technical failure")
            self.banner(f"Technical failure: {payload}\nNothing was saved. Press "
                        "'New CAPTCHA' to try again.", "error")
            return
        result = payload
        self.last_visible = result["visible"]
        if result["outcome"] == "verified":
            for col in DETAIL_COLUMNS:
                self.detail_lbls[col].setText(result["details"][col] or "—")
            self.pending = {"udyam_number": num, **result["details"],
                            "status": "Verified", "error": result["message"]}
            self._set_badge(CAT_VERIFIED, "Verified by portal")
            notes = [result["message"]] if result["message"] else []
            if not result["details"]["enterprise_type"]:
                notes.append("Type of enterprise (Micro/Small/Medium) was not "
                             "found on the page - see Advanced > View last "
                             "portal response.")
            if notes:
                self.note_lbl.setText("⚠  " + " ".join(notes))
            self.banner("The portal returned registration details. Review them, "
                        "then press 'Save & Next'.", "success")
            self.btn_save.setFocus()
        elif result["outcome"] == "not_found":
            self.last_error = result["message"]
            self.pending = {"udyam_number": num, "status": "Not found",
                            "error": result["message"]}
            self._set_badge(CAT_NOT_VERIFIED, "Not verified – not found")
            self.banner(f"{result['message']}\nPress 'Save & Next' to record it "
                        "as Not found, or 'New CAPTCHA' if you think the CAPTCHA "
                        "was wrong.", "warning")
            self.btn_save.setFocus()
        else:
            # Wrong CAPTCHA or unconfirmed: nothing is saved; fetch a fresh
            # CAPTCHA automatically so the user can try again (or Skip).
            self.last_error = result["message"]
            self.retry_note = f"Not verified yet: {result['message']}"
            self.load_captcha()

    def save_next(self):
        if self.pending is None or self.busy:
            return
        if self.write_row(self.pending):
            self.next_number()
        self._set_state()

    def skip(self):
        if not self._has_num() or self.busy:
            return
        if self.write_row({"udyam_number": self.current(), "status": "Skipped",
                           "error": self.last_error or "Skipped by user."}):
            self.next_number()
        self._set_state()

    def open_portal(self):
        # Direct links to the verify page are redirected to the home page by
        # the portal, so open the home page and tell the user where to click.
        webbrowser.open(PORTAL_HOME)
        self.banner("Official portal opened in your browser. Go to Print/Verify "
                    "> Verify Udyam Registration, enter the number and CAPTCHA "
                    "there, then use 'Manual entry...' to record what the "
                    "portal shows.", "info")

    def manual_entry(self):
        if not self._has_num() or self.busy:
            return
        prefill = {c: (self.detail_lbls[c].text().replace("—", ""))
                   for c in DETAIL_COLUMNS}
        dlg = ManualEntryDialog(self.current(), prefill, self)
        if dlg.exec() != QDialog.DialogCode.Accepted or dlg.row is None:
            return
        row = dict(dlg.row, udyam_number=self.current())
        if self.write_row(row):
            self.next_number()
        self._set_state()

    def view_response(self):
        TextDialog("Text of the last portal response (not saved)",
                   self.last_visible or "(nothing yet)", self).exec()

    # ---------------- reports & files ----------------
    def export_excel(self):
        try:
            from excel_export import export_results
        except ImportError:
            QMessageBox.critical(self, "Excel export unavailable",
                                 "The 'openpyxl' library is missing. Install it "
                                 "with:  pip install openpyxl")
            return
        try:
            rows = self.store.read_all()
        except Exception as e:
            QMessageBox.critical(self, "Cannot read results file", str(e))
            return
        if not rows:
            QMessageBox.information(self, "Nothing to export",
                                    "The results file has no saved rows yet.")
            return
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        default = str(self.store.path.parent /
                      f"MSME_Verification_Results_{stamp}.xlsx")
        path, _ = QFileDialog.getSaveFileName(self, "Export results to Excel",
                                              default, "Excel workbook (*.xlsx)")
        if not path:
            return
        if not path.lower().endswith(".xlsx"):
            path += ".xlsx"
        try:
            counts = export_results(rows, path)
        except PermissionError:
            QMessageBox.critical(self, "Cannot save Excel file",
                                 "The file is open in Excel or the folder is "
                                 "read-only. Close it and try again.")
            return
        except Exception as e:
            QMessageBox.critical(self, "Cannot save Excel file", str(e))
            return
        extra = ("\n\nThe result on screen has not been saved yet, so it is "
                 "not included." if self.pending else "")
        summary = "\n".join(f"{k}: {v}" for k, v in counts.items())
        ans = QMessageBox.question(
            self, "Export complete",
            f"{len(rows)} row(s) exported to:\n{path}\n\n{summary}{extra}\n\n"
            "Open the file now?")
        if ans == QMessageBox.StandardButton.Yes:
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def open_results_folder(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.store.path.parent)))

    def change_results_file(self):
        if self.busy or self._has_num():
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Results CSV file", str(self.store.path),
            "CSV files (*.csv)", options=QFileDialog.Option.DontConfirmOverwrite)
        if not path:
            return
        if not path.lower().endswith(".csv"):
            path += ".csv"
        self.store = ResultsStore(path)
        self.output_ready = False
        self._show_results_path()

    def save_template(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save CSV template",
            str(downloads_folder() / "udyam_numbers_template.csv"),
            "CSV files (*.csv)")
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f)
                w.writerow(["udyam_number"])
                w.writerow(["UDYAM-XX-00-0000000"])
        except OSError as e:
            QMessageBox.critical(self, "Cannot save template", str(e))
            return
        self.banner(f"Template saved to {path}. Replace the sample row with "
                    "your Udyam numbers (one per row).", "success")

    def reset(self):
        if self.busy:
            return
        if self._queue_active() or self.table.rowCount():
            ans = QMessageBox.question(
                self, "Clear / Reset",
                "Clear the screen and stop the current list?\n\n"
                "Rows already saved in the results file are kept.")
            if ans != QMessageBox.StandardButton.Yes:
                return
        self.gen += 1
        self.numbers = []
        self.index = -1
        self.client = PortalClient()
        self.last_error = ""
        self.retry_note = ""
        self.table.setRowCount(0)
        self.row_cats = []
        self._update_counts()
        self._clear_details()
        self.captcha_edit.clear()
        self.single_edit.clear()
        self._show_captcha_text("(no CAPTCHA loaded)")
        self.number_lbl.setText("—")
        self.progress_lbl.setText("Processing 0 of 0")
        self.pbar.setRange(0, 1)
        self.pbar.setValue(0)
        self.file_lbl.setText("No file selected")
        self.banner("Cleared. Load a CSV file or type a Udyam Registration "
                    "Number to verify another record.", "info")
        self._set_state()
        self.single_edit.setFocus()

    # ---------------- help ----------------
    def show_help(self):
        QMessageBox.information(self, "How to use", (
            "<b>1.</b> Load a CSV that has a column named <i>udyam_number</i>, "
            "or type one number and press Start.<br><br>"
            "<b>2.</b> The CAPTCHA from the official Udyam portal appears. Type "
            "it exactly (case sensitive) and press <b>Verify MSME</b>.<br><br>"
            "<b>3.</b> If the portal returns details they are shown as "
            "<span style='color:#1B7A2E'><b>Verified</b></span>. Review and press "
            "<b>Save &amp; Next</b>.<br><br>"
            "<b>Not Verified</b> = the portal said the number was not found.<br>"
            "<b>Error</b> = technical failure (network, portal down) – "
            "nothing is saved; retry or skip.<br>"
            "<b>Verification Pending</b> = not yet checked, or skipped.<br><br>"
            "If automatic reading stops working, use <b>Open official portal</b> "
            "and <b>Manual entry</b>.<br><br>"
            f"Each saved row goes to <i>{self.store.path}</i>. Use "
            "<b>Export to Excel</b> for a formatted report."))

    def show_about(self):
        QMessageBox.about(self, "About " + APP_NAME, (
            f"<h3>{APP_NAME}</h3>"
            f"<p>Version {APP_VERSION}</p>"
            "<p>Verifies Udyam (MSME) registration numbers on the official "
            "Government of India portal "
            "<a href='https://udyamregistration.gov.in'>udyamregistration.gov.in</a>.</p>"
            "<p>You read and type each CAPTCHA yourself. The app never solves "
            "CAPTCHAs, never logs in, sends one request at a time and waits "
            "between lookups. An internet connection is required.</p>"
            "<p>A record is shown as <b>Verified</b> only when the portal "
            "returned its registration details.</p>"
            "<p>Not affiliated with or endorsed by the Ministry of MSME.</p>"))

    def closeEvent(self, event):
        if self.pending is not None:
            ans = QMessageBox.question(
                self, "Unsaved result",
                "The result on screen has not been saved. Exit anyway?")
            if ans != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
        event.accept()


# --------------------------------------------------------------------------
def apply_theme(app):
    app.setStyle(QStyleFactory.create("Fusion"))
    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window, QColor("#F3F5F9"))
    pal.setColor(QPalette.ColorRole.WindowText, QColor("#1B2A41"))
    pal.setColor(QPalette.ColorRole.Base, QColor("#FFFFFF"))
    pal.setColor(QPalette.ColorRole.AlternateBase, QColor("#F8FAFD"))
    pal.setColor(QPalette.ColorRole.Text, QColor("#1B2A41"))
    pal.setColor(QPalette.ColorRole.Button, QColor("#FFFFFF"))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor("#1B2A41"))
    pal.setColor(QPalette.ColorRole.Highlight, QColor("#1E4DB7"))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
    pal.setColor(QPalette.ColorRole.ToolTipBase, QColor("#FFFFFF"))
    pal.setColor(QPalette.ColorRole.ToolTipText, QColor("#1B2A41"))
    pal.setColor(QPalette.ColorRole.PlaceholderText, QColor("#8A97AB"))
    pal.setColor(QPalette.ColorRole.Link, QColor("#1E4DB7"))
    app.setPalette(pal)
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(STYLESHEET)


def main():
    if sys.platform == "win32":
        try:   # own taskbar icon instead of the generic python one
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "MSMEVerificationSystem.App")
        except Exception:
            pass
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    icon = QIcon(resource_path("assets/app.ico"))
    if not icon.isNull():
        app.setWindowIcon(icon)
    apply_theme(app)

    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
