# Petrosuite.spec — PyInstaller build spec.
# Build with:  pyinstaller Petrosuite.spec
#
# Produces: dist\Petrosuite\Petrosuite.exe  (a folder build — faster startup
# than a single-file exe, and PySide6/QtWebEngine apps strongly prefer this
# mode since QtWebEngineProcess.exe must sit alongside the main exe).

import os

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('web', 'web'),   # app.html, fonts/, lib/ (xlsx.js, exceljs.js, html2canvas.js, jspdf.js)
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Petrosuite',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # no black terminal window for end users
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='app_icon.ico' if os.path.exists('app_icon.ico') else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Petrosuite',
)
