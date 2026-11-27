"""
InstaCMA - application entry point.

    python main.py
"""
import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)


def _excepthook(exc_type, exc, tb):
    msg = "".join(traceback.format_exception(exc_type, exc, tb))
    try:
        log = os.path.join(os.path.expanduser("~"), ".cma_builder2", "error.log")
        os.makedirs(os.path.dirname(log), exist_ok=True)
        with open(log, "a", encoding="utf-8") as fh:
            fh.write(msg + "\n")
    except OSError:
        pass
    try:
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.critical(None, "InstaCMA", "Something went wrong:\n\n%s\n\nDetails were written to "
                             "%%USERPROFILE%%\\.cma_builder2\\error.log" % exc)
    except Exception:
        print(msg)


def main():
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import QApplication
    if hasattr(Qt, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setApplicationName("InstaCMA")
    try:
        from PyQt5.QtGui import QIcon
        from reports.master_template import resource_path
        ico = resource_path("assets", "instacma.ico")
        if os.path.exists(ico):
            app.setWindowIcon(QIcon(ico))
    except Exception:
        pass
    sys.excepthook = _excepthook
    from gui.main_window import MainWindow
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
