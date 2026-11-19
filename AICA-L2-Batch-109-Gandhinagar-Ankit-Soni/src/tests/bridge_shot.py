"""Screenshots of the Gmail bridge card and the reconciliation header."""
import importlib.util, os, shutil, sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
WORK = "/home/claude/pytest/swork"
shutil.rmtree(WORK, ignore_errors=True)
os.makedirs(WORK, exist_ok=True)
os.environ["XDG_DATA_HOME"] = os.path.join(WORK, "appdata")

spec = importlib.util.spec_from_file_location(
    "bcg", "/home/claude/balance_confirmation_generator.py")
bcg = importlib.util.module_from_spec(spec)
sys.modules["bcg"] = bcg
spec.loader.exec_module(bcg)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QDate, QEvent

app = QApplication([])
app.setStyle("Fusion")
app.setPalette(bcg.qt_palette())
app.setStyleSheet(bcg.style_sheet())
win = bcg.MainWindow()
win.resize(1500, 950)
win.show()


def pump(n=6):
    for _ in range(n):
        app.processEvents()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)


pump()
win.cl_name.setText("Example Manufacturing Private Limited")
win.add_client()
win.fy_year.setText("2025-26")
win.fy_end.setDate(QDate(2026, 3, 31))
win.add_year()
win.db["settings"]["bridge_feed_url"] = \
    "https://script.google.com/macros/s/AKfycbxExample123456789/exec"
win.db["settings"]["bridge_last_sync"] = "2026-11-06T09:42:00"
win.db["replies"] = [{"id": "m-1"}, {"id": "m-2"}, {"id": "m-3"}]
win._load_settings_into_widgets()
pump()

for mode in ("dark", "light"):
    bcg.apply_theme(app, mode)
    win.refresh_theme_button()
    win.style_paper()
    win.restyle()
    pump()
    for page in ("settings", "recon"):
        win.go(page)
        pump(10)
        if page == "settings":
            # the bridge card sits below the fold, so scroll down to it
            from PyQt6.QtWidgets import QScrollArea
            for area in win.findChildren(QScrollArea):
                bar = area.verticalScrollBar()
                if bar.maximum():
                    bar.setValue(bar.maximum())
            pump(10)
        path = os.path.join("/home/claude/pytest/final",
                            "bridge-%s-%s.png" % (page, mode))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        win.grab().save(path)
        print("wrote", path)
