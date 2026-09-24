# -*- mode: python ; coding: utf-8 -*-
# Build with:  pyinstaller build.spec
# Produces a single dist/CA_IPO_Compass(.exe) — see README.md for full steps.

a = Analysis(
    ['main.py'],
    pathex=['vendor'],
    binaries=[],
    datas=[('app/ui/web', 'app/ui/web')],
    hiddenimports=['pypdf'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PySide6', 'playwright'],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='CA_IPO_Compass',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    icon=None,
)
