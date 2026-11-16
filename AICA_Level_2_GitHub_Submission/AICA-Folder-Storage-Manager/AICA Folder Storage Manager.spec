# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.hooks import collect_dynamic_libs
from PyInstaller.utils.hooks import collect_submodules

datas = [('assets/app.ico', 'assets')]
binaries = []
hiddenimports = ['send2trash']
datas += collect_data_files('pypdfium2')
datas += collect_data_files('pypdfium2_raw')
datas += collect_data_files('docx')
binaries += collect_dynamic_libs('winrt')
binaries += collect_dynamic_libs('pypdfium2')
binaries += collect_dynamic_libs('pypdfium2_raw')
hiddenimports += collect_submodules('winrt')


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'PySide6.QtWebEngineQuick', 'PySide6.QtWebChannel', 'PySide6.QtQuick', 'PySide6.QtQml', 'PySide6.QtQuickWidgets', 'PySide6.Qt3DCore', 'PySide6.QtMultimedia', 'PySide6.QtPdf', 'PySide6.QtPdfWidgets', 'PySide6.QtCharts', 'PySide6.QtDataVisualization', 'PySide6.QtBluetooth', 'PySide6.QtPositioning', 'PySide6.QtSql', 'PySide6.QtTest', 'PySide6.QtNetwork', 'PySide6.QtOpenGL', 'PySide6.QtSvg', 'PySide6.QtDesigner', 'tkinter', 'pytest', 'pywinauto', 'pdf2docx', 'numpy', 'cv2', 'fitz'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='AICA Folder Storage Manager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets/app.ico'],
)
