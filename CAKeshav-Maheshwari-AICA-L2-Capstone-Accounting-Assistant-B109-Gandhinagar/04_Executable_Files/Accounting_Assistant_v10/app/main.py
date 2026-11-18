import sys

from PyQt6.QtWidgets import QApplication

from app.config import Settings
from app.ui.main_window import MainWindow
from app.ui.state import AppState


def install_safety_net(app_dir_fn=None):
    """PyQt6 closes the whole app on any unhandled error inside a button/signal handler. Instead: write it to
    logs/errors.log, tell the user in a message, and keep running. Native crashes (Qt itself) are written to
    logs/crash.log by faulthandler, so they can be diagnosed."""
    import datetime as _dt
    import faulthandler
    import traceback
    from app.config import app_dir
    logs = (app_dir_fn or app_dir)() / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    try:
        faulthandler.enable(open(logs / "crash.log", "a", buffering=1))
    except Exception:
        pass
    state = {"last": None}

    def hook(etype, value, tb):
        text = "".join(traceback.format_exception(etype, value, tb))
        try:
            with open(logs / "errors.log", "a", encoding="utf-8") as f:
                f.write(f"\n===== {_dt.datetime.now():%d-%m-%Y %H:%M:%S}\n{text}")
        except Exception:
            pass
        sys.__stderr__ and sys.__stderr__.write(text)
        key = (etype, str(value)[:120])
        if key == state["last"]:
            return                                   # same error again: logged, don't pop up repeatedly
        state["last"] = key
        try:
            from PyQt6.QtCore import QTimer
            from PyQt6.QtWidgets import QMessageBox
            QTimer.singleShot(0, lambda: QMessageBox.warning(
                None, "Something went wrong",
                f"The app hit an error and skipped that step - nothing was posted for it.\n\n"
                f"{etype.__name__}: {str(value)[:300]}\n\nDetails saved in {logs / 'errors.log'} "
                f"(send that file if it repeats)."))
        except Exception:
            pass
    sys.excepthook = hook
    return logs


def main() -> int:
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QGuiApplication
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setApplicationName("Accounting Assistant")
    install_safety_net()
    from app.ui import theme
    settings = Settings.load()
    app.setStyleSheet(theme.apply(settings.theme))
    app.setWindowIcon(theme.app_icon())
    try:                                            # Windows: own taskbar icon instead of Python's
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("AccountingAssistant.Tally")
    except Exception:
        pass
    win = MainWindow(AppState(settings))
    win.show_fitted()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
