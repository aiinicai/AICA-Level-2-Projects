"""GXVAN launcher - open this file in IDLE and press F5.

GST Purchase Register, 2A/2B Reconciliation & Smart PDF Suite
a product of Vantage  |  (c) 2026 Vantage Tax Consulting LLP

The bootstrap below runs BEFORE any third-party import: it installs whatever is
missing with pip (the only network use, one time), then starts the app.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# 1. Bootstrap (standard library only)
# ---------------------------------------------------------------------------
import importlib
import importlib.util
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

# import name -> (pip name, required?)
PACKAGES: dict[str, tuple[str, bool]] = {
    "PyQt6": ("PyQt6", True),
    "pandas": ("pandas", True),
    "numpy": ("numpy", True),
    "openpyxl": ("openpyxl", True),
    "xlsxwriter": ("xlsxwriter", True),
    "pymupdf": ("PyMuPDF", True),
    "reportlab": ("reportlab", True),
    "PIL": ("Pillow", True),
    "rapidfuzz": ("rapidfuzz", True),
    "dateutil": ("python-dateutil", True),
    "qrcode": ("qrcode", True),
    "rapidocr_onnxruntime": ("rapidocr-onnxruntime", False),  # OCR - optional if no wheel for this Python
}
PIP_LINE = "pip install " + " ".join(p for p, _ in PACKAGES.values())


def _pip(pkg: str, user: bool = False) -> bool:
    cmd = [sys.executable, "-m", "pip", "install", "--upgrade", pkg]
    if user:
        cmd.append("--user")
    try:
        subprocess.check_call(cmd)  # noqa: S603 - fixed argument list, no shell
        return True
    except (subprocess.CalledProcessError, OSError):
        return False


SKIP_FILE = HERE / "logs" / f".optional_skip_py{sys.version_info.major}{sys.version_info.minor}"


def _skipped() -> set[str]:
    """Optional packages that already failed to install on this Python (don't retry every launch)."""
    try:
        return set(SKIP_FILE.read_text(encoding="utf-8").split())
    except OSError:
        return set()


def bootstrap() -> bool:
    """Install missing packages. Returns False if a *required* package is still missing."""
    if getattr(sys, "frozen", False):
        return True   # packaged exe: everything is bundled; sys.executable is the exe, not Python
    missing = []
    skipped = _skipped()
    for mod, (pkg, required) in PACKAGES.items():
        if importlib.util.find_spec(mod) is not None:
            continue
        if not required and pkg in skipped:
            continue
        if mod == "PyQt6" and importlib.util.find_spec("PyQt5") is not None:
            continue  # PyQt5 fallback is acceptable
        missing.append((mod, pkg, required))
    if not missing:
        return True
    print(f"[GXVAN] First run: installing {len(missing)} package(s). This needs internet once.")
    for i, (mod, pkg, required) in enumerate(missing, 1):
        print(f"[GXVAN] ({i}/{len(missing)}) pip install {pkg} ...")
        ok = _pip(pkg) or _pip(pkg, user=True)
        if not ok and mod == "PyQt6":
            print("[GXVAN] PyQt6 failed - trying PyQt5 instead ...")
            ok = _pip("PyQt5") or _pip("PyQt5", user=True)
        print(f"[GXVAN]     {'OK' if ok else 'FAILED'}: {pkg}")
    importlib.invalidate_caches()
    still = []
    for mod, pkg, required in missing:
        found = importlib.util.find_spec(mod) is not None or (mod == "PyQt6" and
                                                             importlib.util.find_spec("PyQt5") is not None)
        if not found:
            still.append((pkg, required))
    for pkg, required in still:
        if not required:
            try:
                SKIP_FILE.parent.mkdir(parents=True, exist_ok=True)
                SKIP_FILE.write_text(" ".join(_skipped() | {pkg}), encoding="utf-8")
            except OSError:
                pass
            print(f"[GXVAN] Optional package '{pkg}' could not be installed on Python "
                  f"{sys.version_info.major}.{sys.version_info.minor}. OCR of scanned pages will be disabled; "
                  "text PDFs still work. (Python 3.10-3.13 is recommended for OCR.) "
                  f"Delete {SKIP_FILE.name} in the logs folder to retry.")
    hard = [p for p, r in still if r]
    if hard:
        print("\n[GXVAN] Could not install: " + ", ".join(hard))
        print("[GXVAN] Please run this command in a terminal / command prompt, then start GXVAN again:\n")
        print("    " + PIP_LINE + "\n")
        return False
    return True


# ---------------------------------------------------------------------------
# 2. Application
# ---------------------------------------------------------------------------
def _setup_logging():
    import logging
    from logging.handlers import RotatingFileHandler

    from config import LOG_DIR, LOG_FILE

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger("gxvan")
    if not root.handlers:
        h = RotatingFileHandler(LOG_FILE, maxBytes=2_000_000, backupCount=3, encoding="utf-8")
        h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        root.addHandler(h)
        root.setLevel(logging.INFO)
    return root


def _splash(app):
    from config import APP_NAME, APP_TAGLINE, FOOTER_TEXT, NAVY
    from ui.qt import Qt, QtCore, QtGui, QtWidgets
    from ui.theme import make_logo_pixmap

    pm = QtGui.QPixmap(520, 300)
    pm.fill(QtGui.QColor(NAVY))
    p = QtGui.QPainter(pm)
    p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
    p.drawPixmap(40, 70, make_logo_pixmap(110))
    p.setPen(QtGui.QColor("white"))
    f = QtGui.QFont()
    f.setPixelSize(46)
    f.setBold(True)
    p.setFont(f)
    p.drawText(QtCore.QRectF(175, 80, 330, 60), Qt.AlignmentFlag.AlignVCenter, APP_NAME)
    f.setPixelSize(16)
    f.setBold(False)
    f.setItalic(True)
    p.setFont(f)
    p.setPen(QtGui.QColor("#F2C14E"))
    p.drawText(QtCore.QRectF(178, 138, 330, 30), Qt.AlignmentFlag.AlignVCenter, APP_TAGLINE)
    f.setItalic(False)
    f.setPixelSize(11)
    p.setFont(f)
    p.setPen(QtGui.QColor(255, 255, 255, 170))
    p.drawText(QtCore.QRectF(40, 250, 440, 24), Qt.AlignmentFlag.AlignVCenter, FOOTER_TEXT + "  ·  offline")
    p.end()
    s = QtWidgets.QSplashScreen(pm)
    s.show()
    app.processEvents()
    return s


def main() -> int:
    """Start the GUI. Safe to run repeatedly from IDLE (reuses QApplication, no sys.exit)."""
    if not bootstrap():
        return 1
    import os
    if os.environ.get("GXVAN_DEBUG"):   # dump stack traces if startup hangs (troubleshooting builds)
        import faulthandler
        faulthandler.dump_traceback_later(int(os.environ["GXVAN_DEBUG"]), exit=False, file=sys.stderr)
    log = _setup_logging()
    from config import APP_NAME, load_settings
    from ui.qt import QT_API, QtWidgets
    from ui.theme import build_qss

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv[:1])
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")
    app.setStyleSheet(build_qss(load_settings().get("theme", "light")))
    splash = _splash(app)

    old_hook = sys.excepthook

    def hook(etype, value, tb):
        import traceback
        log.error("Unhandled exception", exc_info=(etype, value, tb))
        try:
            box = QtWidgets.QMessageBox()
            box.setIcon(QtWidgets.QMessageBox.Icon.Warning)
            box.setWindowTitle(f"{APP_NAME} - something went wrong")
            box.setText(f"{etype.__name__}: {value}\n\nThe details were saved to logs/gxvan.log. "
                        "Your source files were not changed.")
            box.setDetailedText("".join(traceback.format_exception(etype, value, tb)))
            box.exec() if hasattr(box, "exec") else box.exec_()
        except Exception:  # noqa: BLE001
            old_hook(etype, value, tb)

    sys.excepthook = hook
    try:
        from ui.main_window import MainWindow

        win = MainWindow()
        win.show()
        splash.finish(win)
        log.info("Started %s with %s on Python %s", APP_NAME, QT_API, sys.version.split()[0])
        rc = app.exec() if hasattr(app, "exec") else app.exec_()
    finally:
        sys.excepthook = old_hook
    return rc


if __name__ == "__main__":
    main()
