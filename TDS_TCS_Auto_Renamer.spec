# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = [
    'openpyxl',
    'csv',
]

# Only collect pymupdf
tmp_ret = collect_all('pymupdf')
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]

excludes = [
    'numpy',
    'pandas',
    'scipy',
    'matplotlib',
    'tkinter',
    'unittest',
    'pytest',
    'IPython',
    'jupyter',
    'notebook',
    'PIL.ImageTk',
    'PyQt6.QtQuick',
    'PyQt6.QtQuick3D',
    'PyQt6.QtQuickWidgets',
    'PyQt6.QtQml',
    'PyQt6.QtWebEngine',
    'PyQt6.QtWebEngineCore',
    'PyQt6.QtWebEngineWidgets',
    'PyQt6.QtWebEngineQuick',
    'PyQt6.Qt3DCore',
    'PyQt6.Qt3DRender',
    'PyQt6.Qt3DQuick',
    'PyQt6.Qt3DAnimation',
    'PyQt6.Qt3DExtras',
    'PyQt6.Qt3DInput',
    'PyQt6.QtNetwork',
    'PyQt6.QtSql',
    'PyQt6.QtMultimedia',
    'PyQt6.QtMultimediaWidgets',
    'PyQt6.QtDesigner',
    'PyQt6.QtBluetooth',
    'PyQt6.QtPositioning',
    'PyQt6.QtSensors',
    'PyQt6.QtSerialPort',
    'PyQt6.QtTest',
    'PyQt6.QtXml',
    'PyQt6.QtPdf',
    'PyQt6.QtPdfWidgets',
    'PyQt6.QtSpatialAudio',
    'PyQt6.QtNfc',
    'PyQt6.QtRemoteObjects',
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=2,
)

# Strip out unnecessary Qt6 DLLs and QML plugins from binaries
filtered_binaries = []
unwanted_dll_patterns = [
    'qt6qml', 'qt6quick', 'qt63d', 'qt6webengine', 'qt6multimedia',
    'qt6network', 'qt6sql', 'qt6bluetooth', 'qt6positioning',
    'qt6sensors', 'qt6serialport', 'qt6test', 'qt6designer',
    'qt6spatialaudio', 'qt6nfc', 'qt6remoteobjects',
    'qml', 'scenegraph', 'sqldrivers', 'multimedia',
]

for b in a.binaries:
    dest_name = b[0].lower()
    if any(pat in dest_name for pat in unwanted_dll_patterns):
        continue
    filtered_binaries.append(b)

a.binaries = filtered_binaries

# Strip out QML and translation data files
filtered_datas = []
for d in a.datas:
    dest_name = d[0].lower()
    if 'qml' in dest_name or 'translations' in dest_name:
        continue
    filtered_datas.append(d)

a.datas = filtered_datas

pyz = PYZ(a.pure, optimize=2)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='TDS_TCS_Auto_Renamer',
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
)
