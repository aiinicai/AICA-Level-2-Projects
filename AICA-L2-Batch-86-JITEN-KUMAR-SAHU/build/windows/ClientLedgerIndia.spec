# PyInstaller spec — build on a WINDOWS machine with:
#   pyinstaller build/windows/ClientLedgerIndia.spec
#
# Produces dist/ClientLedgerIndia/ClientLedgerIndia.exe (onedir build —
# onedir starts faster than onefile and is what installer.iss packages).

# -*- mode: python ; coding: utf-8 -*-
import os

APP_DIR = os.path.join(os.path.dirname(os.path.abspath(SPEC)), "..", "..", "app")
APP_DIR = os.path.normpath(APP_DIR)

_datas = [
    (os.path.join(APP_DIR, "templates", "ClientLedger-India.html"), "templates"),
]

# Bundle the Chromium browser Playwright downloaded during build.bat
# (which runs `playwright install chromium` with PLAYWRIGHT_BROWSERS_PATH=0,
# installing it INSIDE the playwright package itself). We copy that same
# .local-browsers folder from the build venv into the same relative
# location inside the frozen app, because that is exactly where
# Playwright's own driver looks for it by default at runtime — no env
# var override needed, it "just matches".
try:
    import playwright
    _pw_pkg_dir = os.path.dirname(os.path.abspath(playwright.__file__))
    _pw_local_browsers = os.path.join(_pw_pkg_dir, "driver", "package", ".local-browsers")
    if os.path.isdir(_pw_local_browsers):
        _datas.append((_pw_local_browsers, os.path.join("playwright", "driver", "package", ".local-browsers")))
    else:
        print(f"WARNING: Chromium not found at {_pw_local_browsers} — "
              f"did build.bat's 'playwright install chromium' step run with "
              f"PLAYWRIGHT_BROWSERS_PATH=0? The app will fail to launch a browser.")
except ImportError:
    print("WARNING: playwright not importable while building the spec — "
          "make sure you're running PyInstaller from inside build_venv.")

a = Analysis(
    [os.path.join(APP_DIR, "launcher.py")],
    pathex=[APP_DIR],
    binaries=[],
    datas=_datas,
    hiddenimports=["gst_rpa", "config", "dbstore", "webview"],
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
    [],
    exclude_binaries=True,
    name="ClientLedgerIndia",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,   # no console window — set True temporarily if you need to debug startup errors
    icon=None,       # put an .ico path here if you have a logo, e.g. "..\\assets\\app.ico"
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="ClientLedgerIndia",
)
