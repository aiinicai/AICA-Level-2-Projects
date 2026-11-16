import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path
import sys

sys.path.insert(0, str(Path(r"c:\Users\ADMIN\Desktop\Capstone\Application\source\FinstockEventScope")))

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase
from app.database.store import Database
from app.ui.theme import get_style, STYLE
from app.ui.window import MainWindow

app = QApplication([])
for f in ("segoeui.ttf", "segoeuib.ttf", "seguisb.ttf", "seguiemj.ttf", "seguisym.ttf"):
    font_path = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / f
    if font_path.exists():
        QFontDatabase.addApplicationFont(str(font_path))

app.setStyle("Fusion")
app.setStyleSheet(STYLE)

db_path = r"c:\Users\ADMIN\Desktop\Capstone\Application\FinstockEventScope-TradingView\data\eventscope.db"
db = Database(db_path)
window = MainWindow(db, background=False)
window.resize(1600, 940)
window.show()
app.processEvents()

target = Path(r"c:\Users\ADMIN\Desktop\Capstone\Application\source\FinstockEventScope\docs\screenshots")
target.mkdir(parents=True, exist_ok=True)

# 1. Capture Dashboard with Detail Drawer open
if window.table.model().rowCount() > 0:
    window.table.selectRow(0)
    app.processEvents()
window.grab().save(str(target / "dashboard_live_verified.png"))
print("Saved dashboard_live_verified.png")

# 2. Capture Unified Calendar with the redesigned day cells
window.navigation.setCurrentRow(1)
app.processEvents()
window.grab().save(str(target / "unified_calendar_redesigned.png"))
print("Saved unified_calendar_redesigned.png")

window.quitting = True
window.tray.hide()
window.close()
print("Verification capture complete.")
