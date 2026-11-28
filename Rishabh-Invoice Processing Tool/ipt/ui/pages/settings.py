"""Application Settings and Backup & Restore."""
from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFileDialog,
                               QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSpinBox,
                               QVBoxLayout)

from ipt.core.permissions import PermissionDenied, has_permission
from ipt.core.timefmt import fmt
from ipt.services.backup_service import BackupError
from ipt.ui import worker
from ipt.ui.helpers import confirm, error, fill_table, info, make_table, muted, selected_id, title
from ipt.ui.pages.base import BasePage


def ocr_status() -> str:
    from ipt.services.extraction.sources import find_tesseract, ocr_engine, rapid_available
    exe = find_tesseract()
    try:
        engine = ocr_engine()
    except Exception as e:  # noqa: BLE001
        engine = str(e)
    rapid = "RapidOCR PP-OCRv6: installed" if rapid_available() else "RapidOCR: not installed (install_ocr_models.bat)"
    try:
        import cv2  # noqa: F401  (only checks that it is installed)
        cv = "OpenCV installed (image cleaning + deskew)"
    except ImportError:
        cv = "OpenCV not installed – run install_ocr_boost.bat for better scans"
    return (f"Engine in use: {engine} · {rapid} · Tesseract: {exe or 'not found'} · {cv}")


class ResetDialog(QDialog):
    """Choose what to delete for the selected company; the company name must be typed to confirm."""

    def __init__(self, services, parent=None):
        super().__init__(parent)
        from ipt.services.reset_service import DEFAULT, GROUPS
        self.s = services
        c = services.companies.get_company(services.ctx.company_id)
        self.company_name = c.name
        self.setWindowTitle("Reset company data")
        self.resize(620, 460)
        lay = QVBoxLayout(self)
        warn = QLabel(f"<b>Delete IPT data of '{c.name}'.</b><br>A full backup is made first (Settings &amp; Backup "
                      "→ Restore brings it back). Your Tally books are never touched. The company, its years, users "
                      "and the audit trail stay.")
        warn.setWordWrap(True)
        warn.setStyleSheet("background:#fee2e2; color:#7f1d1d; padding:8px; border-radius:6px;")
        lay.addWidget(warn)
        counts = services.resets.summary(c.id)
        self.boxes = {}
        for k, label in GROUPS.items():
            cb = QCheckBox(f"{label}  ({counts.get(k, 0)} records)")
            cb.setChecked(k in DEFAULT)
            self.boxes[k] = cb
            lay.addWidget(cb)
        lay.addWidget(muted("Removing the invoices also removes IPT's record of which bills went to Tally. Duplicates "
                            "are still caught against the purchase register fetched from Tally."))
        lay.addWidget(QLabel(f"Type the company name <b>{c.name}</b> to confirm:"))
        self.name = QLineEdit()
        lay.addWidget(self.name)
        self.status = muted("")
        lay.addWidget(self.status)
        bb = QDialogButtonBox()
        self.btn_go = bb.addButton("Delete selected data", QDialogButtonBox.AcceptRole)
        self.btn_go.setStyleSheet("background:#b91c1c; color:white;")
        bb.addButton(QDialogButtonBox.Cancel)
        bb.accepted.connect(self._go)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.result_ = None

    def groups(self) -> list[str]:
        return [k for k, cb in self.boxes.items() if cb.isChecked()]

    def _go(self) -> None:
        from ipt.services.reset_service import ResetError
        if not self.groups():
            error(self, "Tick what to delete")
            return
        if self.name.text().strip().lower() != self.company_name.strip().lower():
            error(self, "The company name does not match")
            return
        self.btn_go.setEnabled(False)

        def done(res):
            self.result_ = res
            self.accept()

        def failed(msg):
            self.btn_go.setEnabled(True)
            self.status.setText("")
            error(self, msg)

        try:
            self._job = worker.start(worker.Job(self.s.resets.reset, self.s.ctx.company_id, self.groups(),
                                                self.name.text(), with_progress=True), done, failed,
                                     self.status.setText)
        except (ResetError, PermissionDenied) as e:
            failed(str(e))


class SettingsPage(BasePage):
    title_text = "Settings & Backup"

    def __init__(self, services, parent=None):
        super().__init__(services, parent)
        self.layout_.addWidget(title("Settings & Backup"))
        top = QHBoxLayout()
        g1 = QGroupBox("Application")
        f = QFormLayout(g1)
        self.data_folder = QLineEdit(str(services.data_root))
        self.data_folder.setReadOnly(True)
        open_btn = QPushButton("Open folder")
        open_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.s.data_root))))
        row = QHBoxLayout()
        row.addWidget(self.data_folder, 1)
        row.addWidget(open_btn)
        f.addRow("Data folder", row)
        self.tolerance = QDoubleSpinBox()
        self.tolerance.setRange(0, 1000)
        self.tolerance.setDecimals(2)
        self.tolerance.setPrefix("₹ ")
        f.addRow("Invoice rounding tolerance", self.tolerance)
        self.tesseract = QLineEdit()
        self.tesseract.setPlaceholderText("Leave empty to find Tesseract automatically")
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse_tesseract)
        trow = QHBoxLayout()
        trow.addWidget(self.tesseract, 1)
        trow.addWidget(browse)
        f.addRow("Tesseract (tesseract.exe)", trow)
        self.ocr = muted("")
        self.ocr.setWordWrap(True)
        self.engine = QComboBox()
        self.engine.addItem("Automatic (RapidOCR if installed, else Tesseract)", "auto")
        self.engine.addItem("Tesseract only", "tesseract")
        f.addRow("OCR engine", self.engine)
        f.addRow("OCR", self.ocr)
        from ipt.services import claude_assist
        self.claude_mode = QComboBox()
        for k, v in claude_assist.MODES.items():
            self.claude_mode.addItem(v, k)
        self.claude_mode.setToolTip("For the company selected at the top. Bills that need review after extraction "
                                    "are checked by Claude Code with your Claude login. The page images go to "
                                    "Anthropic – keep it Off for clients who do not allow that.")
        f.addRow("Claude Code check\n(this company)", self.claude_mode)
        self.claude_status = muted("")
        self.claude_status.setWordWrap(True)
        crow = QHBoxLayout()
        self.btn_claude_run = QPushButton("Check waiting bills now")
        self.btn_claude_folder = QPushButton("Open cases folder")
        crow.addWidget(self.btn_claude_run)
        crow.addWidget(self.btn_claude_folder)
        f.addRow(self.claude_status)
        f.addRow(crow)
        self.btn_save = QPushButton("Save settings")
        self.btn_save.setObjectName("Primary")
        f.addRow(self.btn_save)
        top.addWidget(g1, 1)
        g2 = QGroupBox("Backup")
        b = QFormLayout(g2)
        self.backup_folder = QLineEdit()
        self.backup_folder.setPlaceholderText("Default: Backups inside the data folder")
        bb = QPushButton("Choose…")
        bb.clicked.connect(self._browse_backup)
        brow = QHBoxLayout()
        brow.addWidget(self.backup_folder, 1)
        brow.addWidget(bb)
        b.addRow("Backup folder", brow)
        b.addRow(muted("Tip: choose a OneDrive / Google Drive / pen-drive folder so a copy lives outside this PC."))
        self.schedule = QComboBox()
        self.schedule.addItem("Off", "off")
        self.schedule.addItem("Daily (when IPT is opened)", "daily")
        self.schedule.addItem("Weekly (when IPT is opened)", "weekly")
        b.addRow("Automatic backup", self.schedule)
        self.keep = QSpinBox()
        self.keep.setRange(1, 100)
        b.addRow("Keep automatic backups", self.keep)
        self.btn_save_b = QPushButton("Save backup settings")
        b.addRow(self.btn_save_b)
        top.addWidget(g2, 1)
        self.layout_.addLayout(top)
        bar = QHBoxLayout()
        self.btn_now = QPushButton("Back up now")
        self.btn_now.setObjectName("Primary")
        self.btn_verify = QPushButton("Verify selected")
        self.btn_restore = QPushButton("Restore selected…")
        self.btn_restore_file = QPushButton("Restore from a file…")
        self.btn_reset = QPushButton("Reset company data…")
        self.btn_reset.setStyleSheet("color:#b91c1c;")
        self.btn_reset.setToolTip("Delete this company's invoices, GSTR-2B, purchase register and reconciliation "
                                  "data in IPT (a backup is made first; Tally is never touched)")
        for w in (self.btn_now, self.btn_verify, self.btn_restore, self.btn_restore_file, self.btn_reset):
            bar.addWidget(w)
        bar.addStretch(1)
        self.progress = muted("")
        bar.addWidget(self.progress)
        self.layout_.addLayout(bar)
        self.table = make_table(["Made at", "Kind", "File", "Size", "Verified", "Check result", "By"])
        self.layout_.addWidget(self.table, 1)
        self.layout_.addWidget(muted("Restore: the backup is checked, your current data is backed up first, and the "
                                     "switch happens when IPT is next opened. The replaced data is kept, never "
                                     "deleted."))
        self.btn_save.clicked.connect(self._save)
        self.btn_claude_run.clicked.connect(self._claude_run)
        self.btn_claude_folder.clicked.connect(self._claude_folder)
        self.btn_save_b.clicked.connect(self._save_backup)
        self.btn_now.clicked.connect(self._backup_now)
        self.btn_verify.clicked.connect(self._verify)
        self.btn_restore.clicked.connect(self._restore_selected)
        self.btn_restore_file.clicked.connect(self._restore_file)
        self.btn_reset.clicked.connect(self._reset)

    def refresh(self) -> None:
        role = self.s.ctx.user.role if self.s.ctx.user else None
        admin = has_permission(role, "settings.edit")
        for w in (self.btn_save, self.btn_save_b, self.btn_restore, self.btn_restore_file):
            w.setEnabled(admin)
        self.btn_now.setEnabled(has_permission(role, "backup.run"))
        self.btn_reset.setEnabled(has_permission(role, "company.reset") and self.s.ctx.company_id is not None)
        st = self.s.settings
        self.tolerance.setValue(float(st.get("rounding_tolerance", "1.00")))
        self.tesseract.setText(st.get("tesseract_path", ""))
        self.engine.setCurrentIndex(max(0, self.engine.findData(st.get("ocr_engine", "auto"))))
        self.backup_folder.setText(st.get("backup_folder", ""))
        self.schedule.setCurrentIndex(max(0, self.schedule.findData(st.get("backup_schedule", "weekly"))))
        self.keep.setValue(int(st.get("backup_keep", "10")))
        self.ocr.setText(ocr_status())
        from ipt.services import claude_assist
        cid = self.s.ctx.company_id
        self.claude_mode.setEnabled(admin and cid is not None)
        self.claude_mode.setCurrentIndex(max(0, self.claude_mode.findData(claude_assist.mode(st, cid))))
        exe = claude_assist.find_claude()
        waiting = len(claude_assist.pending(self.s.data_root))
        self.claude_status.setText(
            (f"Claude Code found: {exe}" if exe else "Claude Code not found on this PC – install it and sign in once "
             "(or run it yourself in the cases folder).")
            + f" · Bills waiting: {waiting}" + (" · checking now…" if claude_assist.running() else ""))
        self.btn_claude_run.setEnabled(bool(exe) and waiting > 0 and not claude_assist.running())
        bks = self.s.backups.list()
        fill_table(self.table, [[fmt(x.created_at), x.kind, Path(x.path).name, f"{x.size_bytes / 1e6:.1f} MB",
                                 "Yes" if x.verified else "No", x.verify_message, x.created_by] for x in bks],
                   [x.id for x in bks])

    def _audit(self, what: dict) -> None:
        from ipt.services import audit_service
        with self.s.db.session() as s:
            audit_service.record(s, self.s.ctx.user, "settings.update", "settings", "", after=what)

    def _save(self) -> None:
        path = self.tesseract.text().strip()
        if path and not Path(path).is_file():
            error(self, "That Tesseract file does not exist")
            return
        self.s.settings.set("rounding_tolerance", f"{self.tolerance.value():.2f}")
        self.s.settings.set("tesseract_path", path)
        self.s.settings.set("ocr_engine", self.engine.currentData())
        os.environ["IPT_OCR_ENGINE"] = self.engine.currentData()
        if path:
            os.environ["IPT_TESSERACT"] = path
        else:
            os.environ.pop("IPT_TESSERACT", None)
        cid = self.s.ctx.company_id
        if cid is not None:
            old = self.s.settings.get(f"claude_assist.{cid}", "off")
            new = self.claude_mode.currentData()
            if new != "off" and old == "off" and not confirm(
                    self, "With the Claude Code check on, page images of bills that need review are sent to "
                          "Anthropic through your Claude login (Claude Code).\n\nDo it for this company?"):
                new = "off"
            self.s.settings.set(f"claude_assist.{cid}", new)
        self._audit({"rounding_tolerance": f"{self.tolerance.value():.2f}", "tesseract_path": path,
                     "ocr_engine": self.engine.currentData(),
                     "claude_assist": self.claude_mode.currentData() if cid is not None else None})
        self.refresh()
        info(self, "Settings saved.")

    def _reset(self) -> None:
        dlg = ResetDialog(self.s, self)
        if dlg.exec() and dlg.result_ is not None:
            r = dlg.result_
            total = sum(r.counts.values())
            info(self, f"Done: {total} records and {r.files_removed} files deleted.\nBackup made first: "
                       f"{r.backup_file}")
            w = self.window()
            if hasattr(w, "_on_company"):
                w._on_company()                    # every page shows the empty company
        self.refresh()

    def _claude_run(self) -> None:
        from ipt.services import claude_assist
        info(self, claude_assist.launch(self.s.data_root) + "\n\nAnswers are filled in automatically (IPT checks "
                   "every value first). You still approve each bill.")
        self.refresh()

    def _claude_folder(self) -> None:
        from ipt.services import claude_assist
        q = claude_assist.queue_dir(self.s.data_root)
        claude_assist.write_instructions(q)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(q)))

    def _save_backup(self) -> None:
        folder = self.backup_folder.text().strip()
        if folder:
            try:
                Path(folder).mkdir(parents=True, exist_ok=True)
                (Path(folder) / ".ipt_write_test").write_text("ok")
                (Path(folder) / ".ipt_write_test").unlink()
            except OSError as e:
                error(self, f"IPT cannot write to that folder: {e}")
                return
        self.s.settings.set("backup_folder", folder)
        self.s.settings.set("backup_schedule", self.schedule.currentData())
        self.s.settings.set("backup_keep", str(self.keep.value()))
        self._audit({"backup_folder": folder, "backup_schedule": self.schedule.currentData(),
                     "backup_keep": self.keep.value()})
        info(self, "Backup settings saved.")

    def _browse_tesseract(self) -> None:
        p, _ = QFileDialog.getOpenFileName(self, "tesseract.exe", "", "tesseract.exe (tesseract.exe);;All (*)")
        if p:
            self.tesseract.setText(p)

    def _browse_backup(self) -> None:
        p = QFileDialog.getExistingDirectory(self, "Backup folder")
        if p:
            self.backup_folder.setText(p)

    def _backup_now(self) -> None:
        self.btn_now.setEnabled(False)

        def done(b):
            self.btn_now.setEnabled(True)
            self.progress.setText("")
            self.refresh()
            info(self, f"Backup made and checked: {b.verify_message}\n{b.path}")

        def failed(msg):
            self.btn_now.setEnabled(True)
            self.progress.setText("")
            error(self, msg)

        self._job = worker.start(worker.Job(self.s.backups.create, "manual", with_progress=True), done, failed,
                                 self.progress.setText)

    def _verify(self) -> None:
        bid = selected_id(self.table)
        if bid is None:
            error(self, "Select a backup")
            return
        ok, msg = self.s.backups.verify(bid)
        self.refresh()
        (info if ok else error)(self, msg)

    def _restore(self, path: Path) -> None:
        if not confirm(self, f"Restore all IPT data from\n{path}?\n\nYour current data is backed up first and kept. "
                             "IPT must be closed and opened again to finish the restore."):
            return
        try:
            safety = self.s.backups.stage_restore(path)
        except (BackupError, PermissionDenied) as e:
            error(self, str(e))
            return
        self.refresh()
        info(self, f"Restore is ready. Close IPT and open it again to finish.\n\nSafety backup of today's data:\n{safety}")

    def _restore_selected(self) -> None:
        bid = selected_id(self.table)
        b = self.s.backups.get(bid) if bid else None
        if b is None:
            error(self, "Select a backup")
            return
        self._restore(Path(b.path))

    def _restore_file(self) -> None:
        p, _ = QFileDialog.getOpenFileName(self, "IPT backup", str(self.s.backups.folder()), "IPT backup (*.zip)")
        if p:
            self._restore(Path(p))
