import datetime
import sys
import traceback
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt

from reconai.config import AppConfig, get_app_base_dir
from reconai.models.session import ReconciliationSession
from reconai.ui.main_window import MainWindow
from reconai.ui.theme import apply_theme


def handle_uncaught_exception(exc_type, exc_value, exc_traceback):
    """Global exception handler to ensure all startup or runtime errors are logged and visible."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    err_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    print(err_msg, file=sys.stderr)

    log_path = get_app_base_dir() / "reconai_crash.log"
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"\n[{datetime.datetime.now().isoformat()}] CRITICAL UNCAUGHT ERROR:\n{err_msg}\n")
    except Exception:
        pass

    app = QApplication.instance()
    if app:
        try:
            QMessageBox.critical(
                None,
                "ReconAI Error",
                f"An unexpected error occurred in ReconAI:\n\n{exc_value}\n\nTechnical details have been written to:\n{log_path}",
            )
        except Exception:
            pass


def main():
    sys.excepthook = handle_uncaught_exception

    # Enable High DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("ReconAI")
    app.setOrganizationName("CharteredAccountants")

    config = AppConfig.load_from_env()
    apply_theme(app, config.theme)

    session = ReconciliationSession(config=config)
    window = MainWindow(session)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
