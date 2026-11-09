"""
main.py — Petrosuite desktop shell.

Flow on every launch:
  1. Open/create the SQLite DB (per-machine, in %LOCALAPPDATA%).
  2. If this PC has never been activated -> show ActivationDialog (Admin
     password + Activation Key). Quit if cancelled/failed too many times.
  3. Show LoginDialog (Admin or User fixed password). Quit if cancelled.
  4. Show CompanyDialog -> pick an existing company/client or create a new
     one. Every company's data (settings, entries, customers, etc.) is
     fully isolated in SQLite, scoped by company_id.
  5. Build the page: read app.html, inject the selected company's data as
     JSON into window.__PP_BOOT_DATA__, inject window.APP_ROLE, load it
     into a QWebEngineView, and register the Bridge object over QWebChannel
     so the page's saveKey()/reset calls reach SQLite for that company.
  6. A toolbar above the app lets the user switch companies at any time
     without restarting — this reloads the page with the new company's data.
"""
import json
import os
import sys

# MUST be set before QtWebEngine initializes its Chromium subprocess (i.e.
# before the Qt imports below, and definitely before QApplication() is
# created). Fixes a blank/black-screen or hard-crash issue on remote-desktop
# sessions (AnyDesk, RDP, VNC) and VMs, where there's no real GPU: Chromium
# tries a hardware GL context, fails, and — unless explicitly told to use its
# CPU-based SwiftShader software renderer via --enable-unsafe-swiftshader —
# has no fallback left and hard-fails ("ContextResult::kFatalFailure").
# ("unsafe" here just means "not sandboxed the same way as GPU rendering";
# it's the standard, safe way to run Chromium/QtWebEngine on a machine with
# no real graphics hardware, which is exactly this situation.)
os.environ.setdefault(
    "QTWEBENGINE_CHROMIUM_FLAGS",
    "--disable-gpu --disable-gpu-compositing --enable-unsafe-swiftshader"
)

from PySide6.QtCore import QUrl, Qt
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWidgets import (
    QApplication, QMessageBox, QFileDialog, QMainWindow, QToolBar, QLabel,
    QComboBox, QPushButton, QWidget, QSizePolicy
)

from db import Database, default_data_dir
from bridge import Bridge
from login_dialog import LoginDialog
from activation_dialog import ActivationDialog
from company_dialog import CompanyDialog
from import_backup_dialog import ImportBackupDialog
from license_common import get_machine_id, verify_activation_key

APP_TITLE = "Petrosuite"

# When frozen by PyInstaller, bundled data files land in sys._MEIPASS.
BASE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
APP_HTML_PATH = os.path.join(BASE_DIR, "web", "app.html")
APP_HTML_DIR = os.path.join(BASE_DIR, "web")


def ensure_activated(db: Database) -> bool:
    lic = db.get_license()
    machine_id = get_machine_id()
    if lic and lic.get("machine_id") == machine_id and verify_activation_key(machine_id, lic.get("activation_key", "")):
        return True

    dlg = ActivationDialog()
    if dlg.exec() == ActivationDialog.Accepted:
        db.save_license(dlg.machine_id, dlg.activation_key)
        return True
    return False


def do_login() -> str:
    dlg = LoginDialog(APP_TITLE)
    if dlg.exec() == LoginDialog.Accepted:
        return dlg.role
    return None


def choose_company(db: Database):
    """Returns (company_id, company_name) or (None, None) if cancelled."""
    has_companies = len(db.list_companies()) > 0
    dlg = CompanyDialog(db, allow_cancel=has_companies)
    if dlg.exec() == CompanyDialog.Accepted:
        return dlg.company_id, dlg.company_name
    return None, None


def build_page_html(db: Database, company_id: int, role: str) -> str:
    with open(APP_HTML_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    boot_data = db.get_all(company_id)
    boot_json = json.dumps(boot_data)
    role_json = json.dumps(role)

    injection = (
        f"<script>window.__PP_BOOT_DATA__ = {boot_json}; "
        f"window.APP_ROLE = {role_json};</script>\n"
    )
    # Inject right before the app's own main <script> block opens — simplest
    # reliable anchor is the opening '<script>\n/* ====... PETROL PUMP ...'
    # block itself (inserting before </head> is NOT safe, app.html defines
    # #app markup in <body>).
    marker = "<script>\n/* ====================================================================="
    if marker not in html:
        raise RuntimeError("Could not find injection anchor in app.html — file may have changed structure.")
    html = html.replace(marker, injection + marker, 1)

    # The assembled HTML (with a full company's data inlined) is written to
    # a runtime file elsewhere (see load_page()), not loaded from web/
    # directly — so relative asset paths (lib/xlsx.full.min.js, fonts/...)
    # need an explicit <base> pointing back at the real web/ folder.
    base_href = QUrl.fromLocalFile(APP_HTML_DIR + os.sep).toString()
    html = html.replace("<head>", f'<head>\n<base href="{base_href}">', 1)

    return html


class DiagnosticPage(QWebEnginePage):
    """Forwards the page's JS console output (console.log/warn/error, and
    uncaught exceptions) to the terminal, so failures inside export/report
    code are visible instead of failing silently."""

    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        print(f"[JS {level}] {message}  (line {lineNumber})")


class WebPane(QWebEngineView):
    """The actual app content. Kept separate from MainWindow (QMainWindow)
    so the toolbar/company-switcher lives outside the web page entirely —
    switching companies never touches app.html's own JS/markup."""

    def __init__(self, db: Database, role: str, company_id: int):
        super().__init__()
        self.db = db
        self.role = role

        self.diag_page = DiagnosticPage(self)
        self.setPage(self.diag_page)

        self.channel = QWebChannel()
        self.bridge = Bridge(db, on_reload_requested=self.reload_with_fresh_data, company_id=company_id)
        self.channel.registerObject("bridge", self.bridge)
        self.page().setWebChannel(self.channel)

        # Excel/PDF/invoice exports (xlsx.js, exceljs, jsPDF) all trigger a
        # browser "download" action under the hood. QtWebEngine blocks any
        # download that isn't explicitly accepted by the host app — without
        # this handler, export buttons appear to do nothing.
        profile = self.page().profile()
        profile.downloadRequested.connect(self._handle_download)

        # Diagnostics: if a page reload (company switch / reset) goes blank,
        # these tell us whether the Chromium render subprocess actually
        # crashed (e.g. a GPU context failure) versus the page loading fine
        # but something else being wrong.
        self.page().loadFinished.connect(self._on_load_finished)
        self.page().renderProcessTerminated.connect(self._on_render_process_terminated)

        self.load_page()

    def _on_load_finished(self, ok):
        print(f"[page] loadFinished ok={ok} (company_id={self.bridge.company_id})")

    def _on_render_process_terminated(self, status, exit_code):
        print(f"[page] RENDER PROCESS TERMINATED status={status} exit_code={exit_code} "
              f"(company_id={self.bridge.company_id}) — this means Chromium's render "
              f"subprocess crashed, most likely a GPU/graphics context failure.")

    def _handle_download(self, download):
        suggested = download.suggestedFileName() or download.downloadFileName() or "export"

        # Blob-based downloads (how the Excel/PDF/PNG exports all work) often
        # don't carry the intended filename through to Qt correctly, landing
        # here as something with no extension. If so, infer the correct one
        # from the download's MIME type so the saved file is never extension-less
        # (which is also why Windows showed no file type/icon/properties for it).
        if not os.path.splitext(suggested)[1]:
            mime = download.mimeType()
            ext_map = {
                "application/pdf": ".pdf",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
                "application/vnd.ms-excel": ".xls",
                "image/png": ".png",
                "image/jpeg": ".jpg",
                "text/csv": ".csv",
            }
            suggested += ext_map.get(mime, "")

        save_path, _ = QFileDialog.getSaveFileName(self, "Save File", suggested)
        if not save_path:
            download.cancel()
            return

        # If the user edited the filename in the dialog and dropped the
        # extension, put it back so the saved file always opens correctly.
        if not os.path.splitext(save_path)[1] and os.path.splitext(suggested)[1]:
            save_path += os.path.splitext(suggested)[1]

        directory = os.path.dirname(save_path)
        filename = os.path.basename(save_path)
        download.setDownloadDirectory(directory)
        download.setDownloadFileName(filename)
        download.accept()

    def load_page(self):
        html = build_page_html(self.db, self.bridge.company_id, self.role)
        runtime_path = os.path.join(default_data_dir(), "runtime_session.html")
        with open(runtime_path, "w", encoding="utf-8") as f:
            f.write(html)
        self.load(QUrl.fromLocalFile(runtime_path))

    def reload_with_fresh_data(self):
        # Called by Bridge.request_reload() (Reset Application flow).
        self.load_page()

    def switch_company(self, company_id: int):
        self.bridge.set_company(company_id)
        self.load_page()


class MainWindow(QMainWindow):
    def __init__(self, db: Database, role: str, company_id: int, company_name: str):
        super().__init__()
        self.db = db
        self.role = role
        self.setWindowTitle(f"{APP_TITLE} — {company_name}")
        self.resize(1400, 900)

        self.web_pane = WebPane(db, role, company_id)
        self.setCentralWidget(self.web_pane)

        self._build_toolbar(company_id, company_name)

    def _build_toolbar(self, company_id: int, company_name: str):
        toolbar = QToolBar("Company")
        toolbar.setMovable(False)
        toolbar.setStyleSheet("QToolBar{spacing:8px;padding:4px 8px;background:#1F2937;} QLabel{color:#E5E7EB;}")
        self.addToolBar(Qt.TopToolBarArea, toolbar)

        label = QLabel("Company:")
        label.setStyleSheet("font-weight:600;")
        toolbar.addWidget(label)

        self.company_combo = QComboBox()
        self.company_combo.setMinimumWidth(260)
        self._refresh_company_combo(selected_id=company_id)
        self.company_combo.currentIndexChanged.connect(self._on_company_combo_changed)
        toolbar.addWidget(self.company_combo)

        change_btn = QPushButton("Change Company")
        change_btn.setToolTip("Open the company selector to switch to a different client, or add a new one")
        change_btn.clicked.connect(self._open_company_dialog)
        toolbar.addWidget(change_btn)

        new_btn = QPushButton("+ New Company")
        new_btn.clicked.connect(self._open_company_dialog)
        toolbar.addWidget(new_btn)

        import_btn = QPushButton("Import Backup...")
        import_btn.setToolTip(
            "Import a backup .json file from a client — you'll be asked whether\n"
            "to create a new company from it, or overwrite an existing one."
        )
        import_btn.clicked.connect(self._open_import_backup)
        toolbar.addWidget(import_btn)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        toolbar.addWidget(spacer)

        role_label = QLabel(f"Logged in as: {self.role.capitalize()}")
        role_label.setStyleSheet("color:#9CA3AF;")
        toolbar.addWidget(role_label)

    def _refresh_company_combo(self, selected_id: int):
        self.company_combo.blockSignals(True)
        self.company_combo.clear()
        companies = self.db.list_companies()
        select_index = 0
        for i, c in enumerate(companies):
            self.company_combo.addItem(c["name"], c["id"])
            if c["id"] == selected_id:
                select_index = i
        self.company_combo.setCurrentIndex(select_index)
        self.company_combo.blockSignals(False)

    def _on_company_combo_changed(self, index: int):
        if index < 0:
            return
        company_id = self.company_combo.itemData(index)
        company_name = self.company_combo.itemText(index)
        if company_id == self.web_pane.bridge.company_id:
            return
        self.setWindowTitle(f"{APP_TITLE} — {company_name}")
        self.web_pane.switch_company(company_id)

    def _open_company_dialog(self):
        dlg = CompanyDialog(self.db, allow_cancel=True)
        if dlg.exec() == CompanyDialog.Accepted:
            self._refresh_company_combo(selected_id=dlg.company_id)
            self.setWindowTitle(f"{APP_TITLE} — {dlg.company_name}")
            self.web_pane.switch_company(dlg.company_id)

    def _open_import_backup(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Backup File to Import", "", "JSON Backup Files (*.json);;All Files (*)"
        )
        if not file_path:
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                backup_text = f.read()
            backup_data = json.loads(backup_text)
        except Exception as e:
            QMessageBox.critical(self, "Could not read file", f"This doesn't look like a valid backup file.\n\n({e})")
            return

        suggested_name = ""
        settings = backup_data.get("settings") if isinstance(backup_data, dict) else None
        if isinstance(settings, dict) and settings.get("companyName"):
            suggested_name = settings["companyName"]

        dlg = ImportBackupDialog(self.db, suggested_name=suggested_name)
        if dlg.exec() != ImportBackupDialog.Accepted:
            return

        if dlg.mode == "new":
            try:
                target_id = self.db.create_company(dlg.new_company_name)
            except ValueError as e:
                QMessageBox.warning(self, "Could not create company", str(e))
                return
            except Exception as e:
                QMessageBox.warning(self, "Could not create company", f"A company with this name may already exist.\n({e})")
                return
        else:
            target_id = dlg.target_company_id

        try:
            self.db.import_json_backup(target_id, backup_text)
        except Exception as e:
            QMessageBox.critical(self, "Import failed", f"Could not import this backup.\n\n({e})")
            return

        self._refresh_company_combo(selected_id=target_id)
        target_name = self.company_combo.currentText()
        self.setWindowTitle(f"{APP_TITLE} — {target_name}")
        self.web_pane.switch_company(target_id)
        QMessageBox.information(self, "Import complete", f"Backup imported successfully into '{target_name}'.")


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_TITLE)

    db = Database()

    if not ensure_activated(db):
        db.close()
        sys.exit(0)

    role = do_login()
    if role is None:
        db.close()
        sys.exit(0)

    company_id, company_name = choose_company(db)
    if company_id is None:
        db.close()
        sys.exit(0)

    window = MainWindow(db, role, company_id, company_name)
    window.show()

    exit_code = app.exec()
    db.close()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
