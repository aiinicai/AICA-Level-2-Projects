import sys
import logging
from app.main import main

if __name__ == "__main__":
    try:
        result = main()
    except Exception as exc:
        logging.exception("Application startup failed")
        try:
            from PySide6.QtWidgets import QApplication, QMessageBox
            app = QApplication.instance() or QApplication(sys.argv[:1])
            QMessageBox.critical(None, "Finstock EventScope", f"Application failed to start:\n{exc}")
        except Exception:
            pass
        result = 1
    raise SystemExit(result)

