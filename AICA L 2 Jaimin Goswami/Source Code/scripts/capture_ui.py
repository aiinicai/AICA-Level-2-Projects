"""Render the application with synthetic fixtures for documentation, not live data."""
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
from datetime import date
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QDate
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase
from app.database.store import Database
from app.services.bootstrap import initialize
from app.services.demo import load_demo
from app.ui.theme import STYLE
from app.ui.window import MainWindow

root=Path(__file__).resolve().parents[1]
app=QApplication([])
# The offscreen platform does not enumerate Windows fonts; load the installed system fonts for QA only.
for font in ('segoeui.ttf','segoeuib.ttf','seguisb.ttf'):
    QFontDatabase.addApplicationFont(str(Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts'/font))
app.setStyle("Fusion");app.setStyleSheet(STYLE)
db=Database(root/"qa-data/screenshots.db");initialize(db);load_demo(db,date(2026,11,13))
window=MainWindow(db,background=False);window.resize(1600,940);window.show();app.processEvents()
target=root/"docs/screenshots";target.mkdir(parents=True,exist_ok=True)
window.anchor.setDate(QDate(2026,11,13));window.table.selectRow(0);app.processEvents()
window.grab().save(str(target/"dashboard.png"))
window.navigation.setCurrentRow(1);window.view.setCurrentText("Month");app.processEvents();window.grab().save(str(target/"calendar.png"))
window.navigation.setCurrentRow(8);window.simulate();app.processEvents();window.grab().save(str(target/"notifications.png"))
window.quitting=True;window.tray.hide();window.close()
print("Saved synthetic-workspace UI screenshots")

