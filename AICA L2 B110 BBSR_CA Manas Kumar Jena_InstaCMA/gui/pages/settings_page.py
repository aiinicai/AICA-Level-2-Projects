"""Settings: CA firm details, AI model (any provider), OCR, default bank norms, master format."""
import os
import shutil

from PyQt5.QtWidgets import (QGroupBox, QFormLayout, QLineEdit, QComboBox, QPushButton, QHBoxLayout, QLabel,
                             QFileDialog, QInputDialog, QMessageBox, QPlainTextEdit, QCheckBox)

from ai.providers import PROVIDERS, test_connection, AIError
from config.settings import reset_settings
from extraction.ocr_engine import tesseract_available
from gui.pages.base_page import BasePage
from gui.pages.common import buttons, pct, times
from reports.master_template import prepare_master, user_master_path


class AIBox(QGroupBox):
    def __init__(self, title):
        super().__init__(title)
        f = QFormLayout(self)
        self.prov = QComboBox()
        self.prov.addItem("None (no AI - OCR and keywords only)", "none")
        for k, v in PROVIDERS.items():
            self.prov.addItem(v["label"], k)
        self.key = QLineEdit()
        self.key.setEchoMode(QLineEdit.Password)
        self.model = QComboBox()
        self.model.setEditable(True)
        self.base = QLineEdit()
        self.prov.currentIndexChanged.connect(lambda *_: self._prov_changed())
        self.result = QLabel("")
        b = QPushButton("Test connection")
        b.setObjectName("Secondary")
        b.clicked.connect(lambda *_: self.test())
        h = QHBoxLayout()
        h.addWidget(b)
        h.addWidget(self.result)
        h.addStretch()
        for lab, w in (("Provider", self.prov), ("API key", self.key), ("Model", self.model), ("Base URL", self.base)):
            f.addRow(lab, w)
        f.addRow("", h)

    def _prov_changed(self):
        k = self.prov.currentData()
        p = PROVIDERS.get(k, {})
        cur = self.model.currentText()
        self.model.clear()
        self.model.addItems(p.get("models", []))
        if cur and k != "none":
            self.model.setCurrentText(cur if cur in p.get("models", []) or not p.get("models") else p["models"][0])
        self.base.setEnabled(k in ("compatible", "ollama", "openai"))
        if k in ("compatible", "ollama") and not self.base.text():
            self.base.setText(p.get("base", ""))
        self.key.setEnabled(k not in ("none", "ollama"))

    def get(self):
        return {"provider": self.prov.currentData(), "api_key": self.key.text().strip(),
                "model": self.model.currentText().strip(), "base_url": self.base.text().strip()}

    def set(self, cfg):
        i = self.prov.findData(cfg.get("provider", "none"))
        self.prov.setCurrentIndex(max(i, 0))
        self._prov_changed()
        self.key.setText(cfg.get("api_key", ""))
        if cfg.get("model"):
            self.model.setCurrentText(cfg["model"])
        self.base.setText(cfg.get("base_url", ""))

    def test(self):
        try:
            self.result.setText("Connected - reply: " + test_connection(self.get()))
        except AIError as e:
            self.result.setText("Failed: %s" % str(e)[:120])


class SettingsPage(BasePage):
    title = "Settings"
    subtitle = "Saved on this PC. Firm details print on the covering letter and the assessment note (no UDIN)."

    def build(self):
        g = QGroupBox("CA firm")
        f = QFormLayout(g)
        self.f = {}
        for k, lab in [("firm_name", "Firm name"), ("firm_frn", "Firm registration no. (FRN)"),
                       ("preparer_name", "Partner / proprietor (signs)"), ("preparer_designation", "Designation"),
                       ("preparer_membership", "Membership no."), ("firm_address", "Address"),
                       ("firm_phone", "Phone"), ("firm_email", "Email"), ("firm_place", "Place")]:
            self.f[k] = QLineEdit()
            f.addRow(lab, self.f[k])
        self.lh = QLineEdit()
        b = QPushButton("Browse...")
        b.setObjectName("Secondary")
        b.clicked.connect(lambda *_: self._pick(self.lh, "Images (*.png *.jpg *.jpeg)"))
        h = QHBoxLayout()
        h.addWidget(self.lh)
        h.addWidget(b)
        f.addRow("Letterhead image (optional)", h)
        self.note = QPlainTextEdit()
        self.note.setMaximumHeight(70)
        f.addRow("Note under audited statements", self.note)
        self.body.addWidget(g)
        self.ai1, self.ai2 = AIBox("AI model - main (any provider)"), AIBox("AI model - backup")
        self.body.addWidget(self.ai1)
        self.body.addWidget(self.ai2)
        self.use_ai = QCheckBox("Use the AI model to read PDFs and photos")
        self.body.addWidget(self.use_ai)
        g3 = QGroupBox("OCR for scanned PDFs (used when no AI model is set)")
        f3 = QFormLayout(g3)
        self.tess = QLineEdit()
        b = QPushButton("Browse...")
        b.setObjectName("Secondary")
        b.clicked.connect(lambda *_: self._pick(self.tess, "tesseract.exe (tesseract.exe)"))
        h = QHBoxLayout()
        h.addWidget(self.tess)
        h.addWidget(b)
        f3.addRow("tesseract.exe", h)
        self.tess_ok = QLabel("")
        f3.addRow("", self.tess_ok)
        self.body.addWidget(g3)
        g4 = QGroupBox("Default bank norms (used when a client's value is left at default)")
        f4 = QFormLayout(g4)
        self.d = {"dscr_min": times(10), "dscr_max": times(10), "turnover_fail_below": times(20),
                  "turnover_pass_from": times(20), "stock_margin": pct(), "debtor_margin": pct(),
                  "default_growth": pct(200, 1), "cc_rate": pct(30), "tl_rate": pct(30)}
        labels = {"dscr_min": "DSCR minimum", "dscr_max": "DSCR maximum", "turnover_fail_below": "Turnover fail below (x)",
                  "turnover_pass_from": "Turnover pass from (x)", "stock_margin": "DP margin on stock",
                  "debtor_margin": "DP margin on debtors", "default_growth": "Sales growth",
                  "cc_rate": "CC rate", "tl_rate": "Term loan rate"}
        for k, w in self.d.items():
            f4.addRow(labels[k], w)
        self.body.addWidget(g4)
        g5 = QGroupBox("Master CMA format (admin)")
        f5 = QFormLayout(g5)
        self.master_info = QLabel("")
        f5.addRow(self.master_info)
        f5.addRow(buttons(self, [("Update master format...", self.update_master, "Secondary"),
                                 ("Back to built-in format", self.reset_master, "Secondary"),
                                 ("Change admin password", self.change_pw, "Secondary")]))
        self.body.addWidget(g5)
        self.body.addLayout(buttons(self, [("Save settings", self.save, "Accent"),
                                           ("Restore factory defaults", self.reset, "Secondary")]))
        self.body.addStretch()

    PCT = {"stock_margin", "debtor_margin", "default_growth", "cc_rate", "tl_rate"}

    def _pick(self, edit, flt):
        p, _ = QFileDialog.getOpenFileName(self, "Select", edit.text(), flt)
        if p:
            edit.setText(p)

    def refresh(self):
        s = self.app.settings
        for k, w in self.f.items():
            w.setText(s.get(k, ""))
        self.lh.setText(s.get("letterhead_image", ""))
        self.note.setPlainText(s.get("audited_note", ""))
        self.ai1.set(s.get("ai_main", {}))
        self.ai2.set(s.get("ai_backup", {}))
        self.use_ai.setChecked(s.get("use_ai_for_pdf", True))
        self.tess.setText(s.get("tesseract_path", ""))
        self.tess_ok.setText("Found" if tesseract_available() else "Not found - install the free UB-Mannheim build "
                                                                     "(only needed without an AI model)")
        for k, w in self.d.items():
            v = s["defaults"].get(k, 0)
            w.setValue(v * 100 if k in self.PCT else v)
        self.master_info.setText("In use: %s" % ("format loaded by admin (%s)" % user_master_path()
                                                 if os.path.exists(user_master_path()) else
                                                 "built-in format (the firm's CMA layout)"))

    def save(self):
        s = self.app.settings
        for k, w in self.f.items():
            s[k] = w.text().strip()
        s["letterhead_image"] = self.lh.text().strip()
        s["audited_note"] = self.note.toPlainText().strip()
        s["ai_main"], s["ai_backup"] = self.ai1.get(), self.ai2.get()
        s["use_ai_for_pdf"] = self.use_ai.isChecked()
        s["tesseract_path"] = self.tess.text().strip()
        for k, w in self.d.items():
            s["defaults"][k] = w.value() / 100 if k in self.PCT else w.value()
        self.app.persist_settings()
        self.app.recompute()
        self.app.status("Settings saved.")

    def _admin(self):
        pw, ok = QInputDialog.getText(self, "Admin", "Admin password:", QLineEdit.Password)
        if ok and pw == self.app.settings.get("admin_password", "admin"):
            return True
        if ok:
            QMessageBox.warning(self, "Admin", "Wrong password.")
        return False

    def update_master(self):
        if not self._admin():
            return
        p, _ = QFileDialog.getOpenFileName(self, "Filled CMA workbook in the new format", "", "Excel (*.xlsx)")
        if not p:
            return
        try:
            prepare_master(p, user_master_path())
            QMessageBox.information(self, "Master format", "The new master format will be used for every export.")
        except Exception as e:
            QMessageBox.warning(self, "Master format", str(e))
        self.refresh()

    def reset_master(self):
        if self._admin() and os.path.exists(user_master_path()):
            os.remove(user_master_path())
            self.refresh()

    def change_pw(self):
        if not self._admin():
            return
        pw, ok = QInputDialog.getText(self, "Admin", "New admin password:", QLineEdit.Password)
        if ok and pw:
            self.app.settings["admin_password"] = pw
            self.app.persist_settings()

    def reset(self):
        if QMessageBox.question(self, "Settings", "Restore factory defaults (firm details are kept)?") == QMessageBox.Yes:
            self.app.settings = reset_settings()
            self.refresh()
