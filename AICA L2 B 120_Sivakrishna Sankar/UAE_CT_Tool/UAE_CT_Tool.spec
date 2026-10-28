# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_all

root_dir = Path.cwd()

datas = [
    (str(root_dir / 'ct_tool' / 'config'), 'ct_tool/config'),
    (str(root_dir / 'templates'), 'templates'),
    (str(root_dir / 'docs'), 'docs'),
    (str(root_dir / 'sample_data' / 'marjan' / 'Marjan_answers.json'), 'sample_data/marjan'),
    (str(root_dir / 'sample_data' / 'marjan' / 'Marjan_decisions_ILLUSTRATIVE.json'), 'sample_data/marjan'),
    (str(root_dir / 'sample_data' / 'marjan' / 'Marjan_Gulf_Trading_TB_31Dec2025.xlsx'), 'sample_data/marjan'),
]

# Collect data files for docx, pdfminer, and pdfplumber
datas += collect_data_files('docx')
datas += collect_data_files('pdfminer')
datas += collect_data_files('pdfplumber')

binaries = []
hiddenimports = [
    'openpyxl',
    'openpyxl.cell._writer',
    'xlrd',
    'pytesseract',
    'PIL',
    'PIL.Image',
    'pandas.io.formats.excel',
    'ct_tool',
    'ct_tool.resources',
]

# Collect all of pypdfium2 (data, binaries, submodules)
pypdfium2_datas, pypdfium2_binaries, pypdfium2_hiddenimports = collect_all('pypdfium2')
datas += pypdfium2_datas
binaries += pypdfium2_binaries
hiddenimports += pypdfium2_hiddenimports

excludes = [
    'pytest',
    '_pytest',
    'reportlab',
    'tests',
    'unittest',
    'tkinter',
    'PySide6.QtWebEngineCore',
    'PySide6.QtWebEngineWidgets',
    'PySide6.QtWebEngineQuick',
    'PySide6.QtQuick',
    'PySide6.QtQml',
    'PySide6.Qt3DCore',
    'PySide6.Qt3DRender',
    'PySide6.Qt3DInput',
    'PySide6.Qt3DAnimation',
    'PySide6.Qt3DExtras',
    'PySide6.QtMultimedia',
    'PySide6.QtMultimediaWidgets',
    'PySide6.QtBluetooth',
    'PySide6.QtSensors',
    'PySide6.QtPositioning',
    'PySide6.QtTest',
    'PySide6.QtSql',
    'PySide6.QtXml',
    'PySide6.QtDesigner',
    'PySide6.QtHelp',
    'PySide6.QtRemoteObjects',
    'PySide6.QtScxml',
    'PySide6.QtNetworkAuth',
    'PySide6.QtSerialPort',
    'PySide6.QtSerialBus',
    'PySide6.QtCharts',
    'PySide6.QtSpatialAudio',
    'PySide6.QtPdf',
    'PySide6.QtPdfWidgets',
    'PySide6.QtVirtualKeyboard',
    'PySide6.QtQuick3D',
    'PySide6.QtQuickWidgets',
]

a = Analysis(
    ['run_app.py'],
    pathex=[str(root_dir)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='UAE_CT_Tool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='UAE_CT_Tool',
)
