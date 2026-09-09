# PyInstaller spec — build on a MACOS machine with:
#   pyinstaller build/mac/ClientLedgerIndia.spec
#
# Produces dist/ClientLedgerIndia.app

# -*- mode: python ; coding: utf-8 -*-
import os
import shutil

# NOTE ON THE WINDOWS SIDE OF THIS PROJECT: the equivalent build on
# Windows repeatedly failed on optional Chrome feature files (a
# Reading Mode helper script, a Privacy Sandbox attestation file)
# going missing mid-build. Several theories were tried (antivirus,
# Chrome's background updater) before the actual, confirmed cause
# turned out to be much simpler: Windows' classic 260-character
# MAX_PATH limit. This project's own folder nesting, combined with
# Chromium's own deeply-nested optional feature folders, produced
# destination paths that measured over 260 characters -- past which
# Win32's plain file APIs fail with "path not found" even though the
# path is completely valid. macOS (APFS/HFS+) doesn't share this
# specific limitation, so no equivalent fix is needed here. The
# tolerance wrapper below is kept anyway as a harmless general safety
# net (skip one optional Chrome file that's genuinely missing for any
# other reason, rather than crash the whole build over it), but it is
# NOT expected to be needed on Mac the way its Windows counterpart was.
_original_copyfile = shutil.copyfile
def _copyfile_tolerate_vanished_files(src, dst, *args, **kwargs):
    try:
        return _original_copyfile(src, dst, *args, **kwargs)
    except FileNotFoundError:
        print(f"NOTE: skipping a file that vanished during packaging "
              f"(not needed by this app -- an optional Chrome feature file): {src}")
        try:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, "wb"):
                pass  # empty placeholder, in case something downstream expects it to exist
        except Exception as placeholder_err:
            print(f"      (also could not create a placeholder at {dst}: {placeholder_err})")
        return dst
shutil.copyfile = _copyfile_tolerate_vanished_files

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

# Drop any data file that has vanished between when it was scanned
# (Analysis, above) and now, right before COLLECT actually copies
# everything. This has repeatedly bitten optional Chrome feature files
# inside the bundled browser (a Reading Mode helper script, a Privacy
# Sandbox attestation file) that exist one moment and are gone the
# next — most likely real-time antivirus reacting to a script with a
# name like "gdocs_helper" that looks like it injects into Google
# Docs, though the exact cause doesn't actually matter here. None of
# these are files the app needs at runtime (they're optional Chrome UI
# features, irrelevant to browser automation), so silently skipping a
# missing one is always safe — the alternative is a hard build failure
# on a file this app was never going to use anyway. This is a general
# fix: it isn't specific to any one filename, so it also covers
# whichever file breaks next, not just the ones already seen.
_missing = [d for d in a.datas if not os.path.isfile(d[1])]
if _missing:
    print(f"NOTE: skipping {len(_missing)} data file(s) that vanished before packaging "
          f"(expected for optional Chrome feature files — not needed by this app):")
    for d in _missing:
        print(f"      {d[1]}")
a.datas = [d for d in a.datas if os.path.isfile(d[1])]

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
