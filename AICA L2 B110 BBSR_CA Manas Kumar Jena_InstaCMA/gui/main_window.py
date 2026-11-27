"""Main window of InstaCMA."""
import os
import traceback

from PyQt5.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QListWidget, QStackedWidget, QLabel,
                             QStatusBar, QFileDialog, QMessageBox, QAction)

from config.settings import load_settings, save_settings
from core.models import CMAProject
from core.audit_trail import TRAIL
from core import sample_data
from analysis.engine import compute
from analysis import validator2 as V
from gui.theme import STYLESHEET
from gui.pages.quick_page import QuickPage
from gui.pages.dashboard_page import DashboardPage
from gui.pages.client_page import ClientPage
from gui.pages.upload_page import UploadPage
from gui.pages.review_page import ReviewPage
from gui.pages.inputs_page import InputsPage
from gui.pages.results_pages import ProjectionPage, TermLoanPage, BankTestsPage, ChecksPage
from gui.pages.export_page import ExportPage
from gui.pages.settings_page import SettingsPage
from gui.pages.help_page import HelpPage

PAGES = [("Quick CMA", QuickPage), ("Dashboard", DashboardPage), ("Client & years", ClientPage), ("Upload statements", UploadPage),
         ("Review & group", ReviewPage), ("Inputs", InputsPage), ("Projections", ProjectionPage),
         ("Term loan", TermLoanPage), ("Bank tests", BankTestsPage), ("Checks & warnings", ChecksPage),
         ("Export", ExportPage), ("Settings", SettingsPage), ("Help", HelpPage)]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("InstaCMA - Developed by CA Manas Kumar Jena")
        self.resize(1380, 880)
        self.setStyleSheet(STYLESHEET)
        self.settings = load_settings()
        self.project = CMAProject()
        self.result = None
        self.checks = []
        self.current_file = None
        root = QWidget()
        lay = QHBoxLayout(root)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        side = QWidget()
        side.setFixedWidth(230)
        sv = QVBoxLayout(side)
        sv.setContentsMargins(0, 0, 0, 0)
        sv.setSpacing(0)
        t = QLabel("InstaCMA")
        t.setObjectName("AppTitle")
        sv.addWidget(t)
        cr = QLabel("Developed by CA Manas Kumar Jena\nContact: +91 9337820330")
        cr.setObjectName("AppCredit")
        cr.setWordWrap(True)
        sv.addWidget(cr)
        self.nav = QListWidget()
        self.nav.setObjectName("Sidebar")
        sv.addWidget(self.nav)
        lay.addWidget(side)
        self.stack = QStackedWidget()
        lay.addWidget(self.stack)
        self.setCentralWidget(root)
        self.pages = {}
        for name, cls in PAGES:
            pg = cls(self)
            self.pages[name] = pg
            self.stack.addWidget(pg)
            self.nav.addItem(name)
        self.nav.currentRowChanged.connect(self._nav)
        self.setStatusBar(QStatusBar())
        m = self.menuBar().addMenu("&File")
        for text, fn, sc in (("New client", self.new_project, "Ctrl+N"), ("Open client file...", self.open_project, "Ctrl+O"),
                             ("Save client file", self.save_project, "Ctrl+S")):
            a = QAction(text, self)
            a.setShortcut(sc)
            a.triggered.connect(lambda *_, f=fn: f())
            m.addAction(a)
        self.nav.setCurrentRow(0)
        if not self.settings.get("firm_name"):
            self.status("Welcome. Enter your firm details in Settings once - they print on the covering letter.")

    def _nav(self, row):
        if row < 0:
            return
        self.stack.setCurrentIndex(row)
        try:
            self.stack.widget(row).refresh()
        except Exception:
            traceback.print_exc()

    def goto(self, name):
        names = [n for n, _ in PAGES]
        if name in names:
            self.nav.setCurrentRow(names.index(name))

    def status(self, msg):
        self.statusBar().showMessage(msg, 9000)

    def persist_settings(self):
        try:
            save_settings(self.settings)
        except OSError as e:
            QMessageBox.warning(self, "Settings", "Could not save settings: %s" % e)

    def recompute(self):
        try:
            if self.project.years and self.project.lines:
                self.result = compute(self.project, self.settings.get("defaults"))
                self.checks = V.validate(self.project, self.result)
            else:
                self.result, self.checks = None, []
        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Calculation", "Calculation failed: %s" % e)
            self.result, self.checks = None, []
        for pg in self.pages.values():
            try:
                pg.refresh()
            except Exception:
                traceback.print_exc()
        errs = sum(1 for c in self.checks if c[0] == "ERROR")
        self.status("Recalculated. " + ("%d error(s) - see Checks." % errs if errs else "All checks passed."))

    def new_project(self):
        if self.project.source_lines and QMessageBox.question(self, "New client", "Start a new client? Unsaved "
                                                              "changes will be lost.") != QMessageBox.Yes:
            return
        self.project = CMAProject()
        self.current_file = None
        TRAIL.clear()
        TRAIL.log("New client")
        self.recompute()
        self.goto("Client & years")

    def open_project(self):
        p, _ = QFileDialog.getOpenFileName(self, "Open client file", self.settings.get("output_folder", ""),
                                           "CMA client file (*.cma.json)")
        if not p:
            return
        try:
            self.project = CMAProject.load(p)
        except Exception as e:
            QMessageBox.critical(self, "Open", "Could not open: %s" % e)
            return
        self.current_file = p
        TRAIL.log("Client file opened", p)
        self.recompute()
        self.goto("Dashboard")

    def save_project(self):
        p = self.current_file
        if not p:
            name = (self.project.intake.client_name or "Client") + ".cma.json"
            p, _ = QFileDialog.getSaveFileName(self, "Save client file",
                                               os.path.join(self.settings.get("output_folder", ""), name),
                                               "CMA client file (*.cma.json)")
            if not p:
                return
        try:
            self.project.save(p)
            self.current_file = p
            self.status("Saved " + p)
        except OSError as e:
            QMessageBox.warning(self, "Save", str(e))

    def load_sample(self, which):
        self.project = sample_data.sample_trading() if which == "sm" else sample_data.sample_company()
        self.project.locked = True
        self.current_file = None
        TRAIL.log("Sample loaded", which)
        self.recompute()
        self.goto("Dashboard")

    def closeEvent(self, e):
        self.persist_settings()
        e.accept()
