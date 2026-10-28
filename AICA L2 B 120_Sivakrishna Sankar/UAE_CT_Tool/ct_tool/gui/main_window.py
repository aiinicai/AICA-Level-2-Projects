"""Main window: step navigation on the left, pages on the right."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (QApplication, QDialog, QFileDialog, QHBoxLayout, QListWidget, QListWidgetItem, QMainWindow, QMessageBox, QStackedWidget,
                               QVBoxLayout, QWidget, QPushButton, QPlainTextEdit)

from ..models import load_json
from ..project import Project
from . import widgets as W
from .pages_results import AdjustmentsPage, ComputationPage, ExportPage, LogPage, RiskPage
from .pages_review import MappingPage, QuestionnairePage
from .pages_setup import FilesPage, FXPage, HomePage
from .state import AppState

STEPS = [("home", "Project / dashboard", None), ("fx", "1. Currency and FX", None), ("files", "2. Files", "fx"), ("mapping", "3. Account mapping", "tb"),
         ("questionnaire", "4. Questionnaire", "tb"), ("risk", "5. Risk review", "tb"), ("adjustments", "6. Adjustments", "tb"), ("computation", "7. Computation and checks", "tb"),
         ("export", "8. Export", "tb"), ("log", "Log / audit trail", None)]

LIMITS = """Known limitations (read before relying on any output)

- This is a preliminary-review tool. It does not replace a professional review of the records, contracts, elections and supporting documents.
- Tax rules are held in config/rules.json with a verification status. Rules marked SECONDARY or UNVERIFIED were not read from the official text and must be checked.
- Mapping, risk indicators and proposed amounts come from account names, balances and narrations. They can be wrong.
- Exchange rates are never fetched online: you enter or upload them. A derived translation difference needs your approval.
- Tax EBITDA (interest limitation) is approximated; opening tax losses, prior-period unrealised amounts and elections are as you state them.
- Group relief, business restructuring relief, transfer pricing and Pillar Two are flagged only; they are not computed.
- The GL must be Excel/CSV. Scanned TB PDFs need Tesseract OCR installed; OCR results must be checked against the image.
- Nothing is filed; no AI/online service is used unless you enable it (not enabled in this version)."""


class TextDialog(QDialog):
    def __init__(self, parent, title, text):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(760, 520)
        lay = QVBoxLayout(self)
        t = QPlainTextEdit(text)
        t.setReadOnly(True)
        lay.addWidget(t)
        b = QPushButton("Close")
        b.clicked.connect(self.accept)
        lay.addWidget(b)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.state = AppState()
        self.setWindowTitle("UAE Corporate Tax computation assistant")
        self.resize(1320, 840)
        root = QWidget()
        self.setCentralWidget(root)
        h = QHBoxLayout(root)
        self.nav = QListWidget()
        self.nav.setFixedWidth(230)
        self.nav.setStyleSheet("QListWidget{background:#283A4A;color:white;font-size:11pt;} QListWidget::item{padding:10px;} "
                               "QListWidget::item:selected{background:#FDC50A;color:#283A4A;} QListWidget::item:disabled{color:#7F8C97;}")
        self.stack = QStackedWidget()
        h.addWidget(self.nav)
        h.addWidget(self.stack, 1)
        self.pages = {}
        classes = {"home": HomePage, "fx": FXPage, "files": FilesPage, "mapping": MappingPage, "questionnaire": QuestionnairePage, "risk": RiskPage,
                   "adjustments": AdjustmentsPage, "computation": ComputationPage, "export": ExportPage, "log": LogPage}
        for key, label, _ in STEPS:
            page = classes[key](self)
            self.pages[key] = page
            self.stack.addWidget(page)
            it = QListWidgetItem(label)
            it.setData(Qt.UserRole, key)
            self.nav.addItem(it)
        self.nav.currentRowChanged.connect(self.on_nav)
        self._menus()
        self.state.gate_changed.connect(self.apply_gates)
        self.state.analysed.connect(self.apply_gates)
        self.state.changed.connect(self.update_title)
        self.apply_gates()
        self.goto("fx")
        self.update_title()
        self.statusBar().showMessage("Start with Step 1: the currency of the trial balance.")

    # ------------------------------------------------------------------ menu
    def _menus(self):
        m = self.menuBar().addMenu("&File")
        for text, fn, key in (("&New project", self.action_new, QKeySequence.New), ("&Open project...", self.action_open, QKeySequence.Open),
                              ("&Save", self.action_save, QKeySequence.Save), ("Save &as...", self.action_save_as, None), ("E&xit", self.close, None)):
            a = QAction(text, self)
            if key:
                a.setShortcut(key)
            a.triggered.connect(fn)
            m.addAction(a)
        hm = self.menuBar().addMenu("&Help")
        for text, fn in (("Known limitations", lambda: TextDialog(self, "Known limitations", LIMITS).exec()), ("Tax rules and verification status", self.show_rules),
                         ("About", self.show_about)):
            a = QAction(text, self)
            a.triggered.connect(fn)
            hm.addAction(a)

    def show_rules(self):
        reg = load_json("rules.json")
        lines = [f"Rules file version {reg.get('version')}", ""]
        for r in reg["rules"]:
            lines += [f"[{r['verification']}] {r['id']} - {r['topic']}", f"    {r['summary']}", f"    Source: {r['source']} {r.get('reference', '')} (checked {r.get('date_checked', '?')})",
                      f"    Note: {r.get('note', '')}", ""]
        lines += ["Parameters:", *[f"    {k}: {v}" for k, v in reg["params"].items()]]
        TextDialog(self, "Tax rules and verification status", "\n".join(lines)).exec()

    def show_about(self):
        QMessageBox.about(self, "About", "UAE Corporate Tax computation assistant\nPreliminary-review tool: analyses a trial balance and general ledger, "
                                         "converts to AED, proposes adjustments for your decision, and produces an Excel computation, a review workbook and a Word risk report.\n\n"
                                         "It does not file returns or give tax advice.")

    # ------------------------------------------------------------------ navigation / gating
    def goto(self, key):
        for i in range(self.nav.count()):
            if self.nav.item(i).data(Qt.UserRole) == key and self.nav.item(i).flags() & Qt.ItemIsEnabled:
                self.nav.setCurrentRow(i)
                return

    def on_nav(self, row):
        if row >= 0:
            self.stack.setCurrentIndex(row)

    def apply_gates(self):
        s = self.state
        ok = {None: True, "fx": s.fx_ready, "tb": s.analysis is not None}
        for i, (key, _, need) in enumerate(STEPS):
            it = self.nav.item(i)
            en = ok[need]
            it.setFlags(it.flags() | Qt.ItemIsEnabled if en else it.flags() & ~Qt.ItemIsEnabled)
            tip = "" if en else ("Confirm the currency settings first." if need == "fx" else "Load and confirm the trial balance first.")
            it.setToolTip(tip)

    def busy(self, msg):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.statusBar().showMessage(msg)

    def idle(self):
        QApplication.restoreOverrideCursor()
        self.statusBar().showMessage("Ready", 3000)

    def update_title(self):
        p = self.state.project
        self.setWindowTitle(f"{'* ' if self.state.dirty else ''}{p.name} - UAE Corporate Tax computation assistant")

    # ------------------------------------------------------------------ project actions
    def maybe_save(self) -> bool:
        if not self.state.dirty:
            return True
        r = QMessageBox.question(self, "Unsaved changes", "Save the current project first?", QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel, QMessageBox.Yes)
        if r == QMessageBox.Cancel:
            return False
        if r == QMessageBox.Yes:
            return self.action_save()
        return True

    def action_new(self):
        if not self.maybe_save():
            return
        self.state.new_project()
        self.pages["home"].pull()
        self.pages["fx"].populate()
        self.goto("fx")
        self.update_title()

    def action_open(self):
        if not self.maybe_save():
            return
        path, _ = QFileDialog.getOpenFileName(self, "Open project", str(Path.home()), "Corporate Tax project (*.ctproj)")
        if not path:
            return
        try:
            p = Project.load(path)
        except Exception as e:      # noqa: BLE001
            W.warn(self, "Open project", f"Could not open the project: {e}")
            return
        self.state.set_project(p, path)
        p.log("Project opened", path)
        self.pages["fx"].populate()
        self.update_title()
        self.goto("home")

    def action_save(self) -> bool:
        if not self.state.path:
            return self.action_save_as()
        return self._save(self.state.path)

    def action_save_as(self) -> bool:
        path, _ = QFileDialog.getSaveFileName(self, "Save project", str(Path.home() / f"{self.state.project.name}.ctproj"), "Corporate Tax project (*.ctproj)")
        if not path:
            return False
        if not path.endswith(".ctproj"):
            path += ".ctproj"
        return self._save(path)

    def _save(self, path) -> bool:
        try:
            self.state.project.save(path)
        except Exception as e:      # noqa: BLE001
            W.warn(self, "Save", f"Could not save: {e}")
            return False
        self.state.path, self.state.dirty = path, False
        self.update_title()
        self.statusBar().showMessage(f"Saved {path}", 4000)
        return True

    def closeEvent(self, ev):
        if self.maybe_save():
            ev.accept()
        else:
            ev.ignore()


def main():
    import sys
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle("Fusion")
    w = MainWindow()
    w.show()
    return app.exec()
