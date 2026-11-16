import argparse
from datetime import date
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import sys

from app.database.store import Database
from app.services.bootstrap import initialize
from app.utils.paths import data_dir


def main(argv=None):
    parser=argparse.ArgumentParser(description="Finstock EventScope desktop application")
    parser.add_argument("--data-dir",help="Override the local user data folder")
    parser.add_argument("--smoke-test",action="store_true",help="Run packaged backend checks and write smoke-report.json")
    parser.add_argument("--no-background",action="store_true",help="Disable background timers for controlled UI tests")
    parser.add_argument("--ui-smoke-test",action="store_true",help="Construct the packaged GUI offscreen and write a report")
    args=parser.parse_args(argv)
    if args.ui_smoke_test:os.environ["QT_QPA_PLATFORM"]="offscreen"
    if args.data_dir:os.environ["FINSTOCK_DATA_DIR"]=str(Path(args.data_dir).resolve())
    folder=data_dir()
    handler=RotatingFileHandler(folder/"eventscope.log",maxBytes=1_000_000,backupCount=3,encoding="utf-8")
    logging.basicConfig(level=logging.INFO,handlers=[handler],format="%(asctime)s %(levelname)s %(message)s")
    db=Database(folder/"eventscope.db")
    initialize(db)
    if args.smoke_test:
        from app.services.demo import load_demo
        from app.database.events import EventRepository
        from app.utils.time import normalize_time,display_time
        import pandas,feedparser,tzdata
        report={"sample_import":load_demo(db,date(2026,11,13)).describe(),"events":len(EventRepository(db).search(limit=10000)[0]),"timezone":display_time(normalize_time("2026-01-15T08:30:00-05:00"),"Asia/Kolkata"),"sqlite_integrity":db.rows("PRAGMA integrity_check"),"frozen":bool(getattr(sys,"frozen",False)),"python":sys.version}
        if sys.platform=="win32":
            from windows_toasts import Toast
            report["windows_toasts_import"]=True
        (folder/"smoke-report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
        return 0
    from PySide6.QtCore import QLockFile
    from PySide6.QtWidgets import QApplication,QMessageBox
    from app.ui.theme import get_style, STYLE
    from app.ui.window import MainWindow
    current_theme = db.setting("theme", "Dark Navy")
    application=QApplication(sys.argv[:1]); application.setApplicationName("Finstock EventScope"); application.setOrganizationName("Finstock Capital"); application.setStyle("Fusion"); application.setStyleSheet(get_style(current_theme))
    lock = QLockFile(str(folder / "eventscope.lock"))
    lock.setStaleLockTime(5000)
    if not lock.tryLock(200):
        if not lock.removeStaleLockFile():
            QMessageBox.information(None, "Finstock EventScope", "EventScope is already active for this workspace. Please check your system tray (near the clock).")
            return 0
        lock.tryLock(200)
    db.set_setting("app_build_version", 7)
    db.set_setting("first_run_complete", True)
    def unhandled(exc_type,value,tb):
        logging.getLogger("finstock").error("Unhandled application error: %s",exc_type.__name__)
        QMessageBox.critical(None,"Application error",f"{exc_type.__name__}: {value}\nYour previously committed records remain stored.")
    sys.excepthook=unhandled
    window=MainWindow(db,background=not (args.no_background or args.ui_smoke_test)); window.show()
    if args.ui_smoke_test:
        application.processEvents()
        (folder/"ui-smoke-report.json").write_text(json.dumps({"frozen":bool(getattr(sys,"frozen",False)),"window_title":window.windowTitle(),"visible":window.isVisible(),"width":window.width(),"height":window.height()},indent=2),encoding="utf-8")
        lock.unlock()
        return 0
    result=application.exec()
    lock.unlock()
    return result


if __name__=="__main__":
    raise SystemExit(main())

