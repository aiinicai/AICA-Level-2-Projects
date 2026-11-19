import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
root=Path(__file__).resolve().parents[1]
app=QApplication([])
icon=QIcon(str(root/'assets/finstock.svg'))
if not icon.pixmap(128,128).save(str(root/'assets/finstock.ico'),'ICO'):
    raise RuntimeError('Could not create application icon')
print('Created assets/finstock.ico')

