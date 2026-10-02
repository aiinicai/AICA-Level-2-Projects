# -*- mode: python ; coding: utf-8 -*-
# Build with: pyinstaller build.spec
# Output: a single portable .exe at dist/GST Inward HSN-SAC Fetcher.exe
# (onefile mode — easiest to upload as one GitHub Release asset and hand to users)

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('ui.html', '.')],
    hiddenimports=['webview.platforms.edgechromium'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='GST Inward HSN-SAC Fetcher',
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
