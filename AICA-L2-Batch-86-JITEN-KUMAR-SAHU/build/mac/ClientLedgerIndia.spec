# PyInstaller spec — build on a MACOS machine with:
#   pyinstaller build/mac/ClientLedgerIndia.spec
#
# Produces dist/ClientLedgerIndia.app

# -*- mode: python ; coding: utf-8 -*-
import os

APP_DIR = os.path.join(os.path.dirname(os.path.abspath(SPEC)), "..", "..", "app")
APP_DIR = os.path.normpath(APP_DIR)

_datas = [
    (os.path.join(APP_DIR, "templates", "ClientLedger-India.html"), "templates"),
]

# Bundle the Chromium browser Playwright downloaded during build.sh
# (installed with PLAYWRIGHT_BROWSERS_PATH=0, i.e. inside the playwright
# package itself) into the same relative location inside the frozen
# .app — that's exactly where Playwright's driver looks by default.
try:
    import playwright
    _pw_pkg_dir = os.path.dirname(os.path.abspath(playwright.__file__))
    _pw_local_browsers = os.path.join(_pw_pkg_dir, "driver", "package", ".local-browsers")
    if os.path.isdir(_pw_local_browsers):
        _datas.append((_pw_local_browsers, os.path.join("playwright", "driver", "package", ".local-browsers")))
    else:
        print(f"WARNING: Chromium not found at {_pw_local_browsers} — "
              f"did build.sh's 'playwright install chromium' step run with "
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
    console=False,
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

app = BUNDLE(
    coll,
    name="ClientLedgerIndia.app",
    icon=None,   # put an .icns path here if you have a logo
    bundle_identifier="com.yourfirm.clientledgerindia",
    info_plist={
        "NSHighResolutionCapable": "True",
        "CFBundleShortVersionString": "1.0.0",
    },
)
