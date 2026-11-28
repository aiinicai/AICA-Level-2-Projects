"""Application entry point: logging, database, login, main window."""
from __future__ import annotations

import logging
import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from ipt import config
from ipt.db.base import Database
from ipt.logging_setup import setup_logging
from ipt.ui.login_dialogs import FirstRunDialog, LoginDialog
from ipt.ui.main_window import MainWindow
from ipt.ui.services import Services
from ipt.ui.theme import STYLESHEET

log = logging.getLogger("ipt")


def _scheduled_backup(services) -> None:
    """Make the scheduled backup in the background if one is due (Settings -> Backup)."""
    try:
        if not services.backups.due():
            return
    except Exception:  # noqa: BLE001 - a backup check must never stop IPT from opening
        log.exception("Backup schedule check failed")
        return
    from ipt.ui import worker
    worker.start(worker.Job(services.backups.create, "scheduled"),
                 lambda b: log.info("Scheduled backup made: %s", b.path),
                 lambda msg: log.warning("Scheduled backup failed: %s", msg))


def main() -> int:
    root = config.data_dir()
    setup_logging(config.logs_dir(root))
    log.info("Starting IPT, data folder %s", root)
    app = QApplication(sys.argv)
    app.setApplicationName("IPT")
    app.setStyle("Fusion")  # same look on every Windows theme (no red accent-colour selections)
    from PySide6.QtGui import QColor, QPalette
    pal = app.palette()
    pal.setColor(QPalette.Highlight, QColor("#dbeafe"))
    pal.setColor(QPalette.HighlightedText, QColor("#1f2937"))
    app.setPalette(pal)
    app.setStyleSheet(STYLESHEET)
    from ipt.ui.helpers import install_wheel_guard
    install_wheel_guard(app)           # parented to the app: lives for the whole session
    restored = None
    try:
        from ipt.services.backup_service import apply_pending_restore
        restored = apply_pending_restore(root)
    except Exception as exc:  # pragma: no cover - shown to user
        log.exception("Restore could not be applied")
        QMessageBox.critical(None, "IPT", f"The staged restore could not be applied:\n{exc}\n\n"
                                          "Your current data was not changed.")
    if restored:
        log.info(restored)
        QMessageBox.information(None, "IPT", restored)
    try:
        db = Database.for_file(config.db_path(root))
        db.create_schema()
    except Exception as exc:  # pragma: no cover - shown to user
        log.exception("Database could not be opened")
        QMessageBox.critical(None, "IPT", f"The database could not be opened:\n{exc}")
        return 1
    services = Services.build(db, root)
    import os as _os
    _os.environ["IPT_OCR_ENGINE"] = services.settings.get("ocr_engine", "auto")
    tess = services.settings.get("tesseract_path", "")
    if tess:
        import os
        os.environ["IPT_TESSERACT"] = tess

    if not services.auth.has_users():
        if not FirstRunDialog(services.auth).exec():
            return 0

    while True:
        login = LoginDialog(services.auth)
        if not login.exec():
            return 0
        services.ctx.user = login.user
        services.ctx.company_id = services.ctx.fy_id = None
        window = MainWindow(services)
        _scheduled_backup(services)
        logged_out = {"flag": False}

        def _logout(w=window, f=logged_out):
            f["flag"] = True
            w.close()

        window.logout_requested.connect(_logout)
        window.show()
        app.exec()
        if not logged_out["flag"]:
            return 0
        services.ctx.user = None
