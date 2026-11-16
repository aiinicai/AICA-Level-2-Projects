"""AICA Folder Storage Manager - entry point."""
import os
import sys


def main():
    if "--data" in sys.argv:
        os.environ["AICA_FSM_DATA"] = sys.argv[sys.argv.index("--data") + 1]
    if "--selftest" in sys.argv:
        from aica_fsm.selftest import run
        return run(sys.argv[sys.argv.index("--selftest") + 1])
    if "--selfcheck" in sys.argv:
        # Packaging check: OCR engine, PDF, Word and Excel libraries load inside the exe.
        from aica_fsm.textextract import ocr_available
        import openpyxl, pypdf, pypdfium2, docx, send2trash  # noqa
        ok = ocr_available()
        out = os.environ.get("AICA_SELFCHECK_OUT")
        msg = f"ocr={ok} openpyxl={openpyxl.__version__} pypdf={pypdf.__version__}"
        if out:
            with open(out, "w") as f:
                f.write(msg)
        return 0 if ok else 2

    import traceback
    from aica_fsm.paths import app_data_dir

    log_path = os.path.join(app_data_dir(), "error.log")

    def hook(et, ev, tb):
        text = "".join(traceback.format_exception(et, ev, tb))
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(text + "\n")
        except OSError:
            pass
        try:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(None, "Unexpected error", f"{ev}\n\nDetails were written to:\n{log_path}")
        except Exception:
            pass

    sys.excepthook = hook

    from PySide6.QtWidgets import QApplication
    from aica_fsm import APP_NAME
    from aica_fsm.store import Catalog
    from aica_fsm.ui.common import STYLE
    from aica_fsm.ui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    cat = Catalog()
    w = MainWindow(cat)
    w.show()
    rc = app.exec()
    cat.close()
    return rc


if __name__ == "__main__":
    sys.exit(main())
