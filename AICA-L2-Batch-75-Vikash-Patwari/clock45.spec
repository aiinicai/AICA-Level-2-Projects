# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules

hidden = [
    name for name in collect_submodules("webview")
    if not any(part in name for part in ("platforms.gtk", "platforms.cocoa", "platforms.android"))
]

a = Analysis(
    ["app.py"],
    pathex=["."],
    binaries=[],
    datas=[("web", "web")],
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "IPython"],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="The45DayClock",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets/clock45.ico",
    # Version metadata is intentionally omitted from the public AICA source build
    # so this spec remains buildable even when packaging/version_info.txt is not included.
    version=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="The45DayClock",
)
