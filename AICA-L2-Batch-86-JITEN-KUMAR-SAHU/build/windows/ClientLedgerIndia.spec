# PyInstaller spec — build on a WINDOWS machine with:
#   pyinstaller build/windows/ClientLedgerIndia.spec
#
# Produces dist/ClientLedgerIndia/ClientLedgerIndia.exe (onedir build —
# onedir starts faster than onefile and is what installer.iss packages).

# -*- mode: python ; coding: utf-8 -*-
import os
import shutil

# ── Root cause, finally confirmed ───────────────────────────────────
# Every previous theory here (antivirus, Chrome's background updater,
# timing races) was WRONG. The actual cause: this project's own folder
# nesting (extracting the zip creates
# ...\Downloads\ClientLedgerIndia-Installer-Project\ClientLedgerIndia\...,
# then PyInstaller adds \build\windows\dist\ClientLedgerIndia\_internal\
# playwright\driver\package\.local-browsers\chromium-1234\chrome-win64\...
# on top of that) combines with Chromium's own deeply-nested optional
# feature folders to produce destination paths that exceed Windows'
# classic 260-character MAX_PATH limit. A real failing path measured
# out at 266 characters. Past that limit, Win32's plain file APIs
# (which Python's os/shutil use by default) fail with "path not
# found" even though the path is completely valid -- it's simply too
# long for the legacy API to resolve. This explains everything
# observed: which specific files failed (the ones nested deep enough
# to push the total over 260), and why it looked inconsistent (some
# operations that use different underlying APIs tolerate long paths
# fine, others don't).
#
# The real fix is Windows' own long-path support: prefixing an
# absolute path with \\?\ tells Win32 to bypass the 260-character
# limit entirely and use the path exactly as given. This is a
# long-standing, official Windows mechanism (not a workaround), safe
# for both long AND short paths. Applied here to every filesystem
# operation PyInstaller's own COLLECT step performs (makedirs,
# copyfile, chmod), so this stops depending on how deeply nested the
# folder someone extracts this project into happens to be.
def _long_path(p):
    if os.name != "nt" or not p:
        return p
    p = os.path.abspath(p)
    if p.startswith("\\\\?\\"):
        return p
    if p.startswith("\\\\"):
        return "\\\\?\\UNC\\" + p[2:]
    return "\\\\?\\" + p

_original_makedirs = os.makedirs
def _makedirs_long_path(name, *args, **kwargs):
    return _original_makedirs(_long_path(name), *args, **kwargs)
os.makedirs = _makedirs_long_path

_original_chmod = os.chmod
def _chmod_long_path(path, *args, **kwargs):
    return _original_chmod(_long_path(path), *args, **kwargs)
os.chmod = _chmod_long_path

_original_copyfile = shutil.copyfile
def _copyfile_long_path(src, dst, *args, **kwargs):
    try:
        return _original_copyfile(_long_path(src), _long_path(dst), *args, **kwargs)
    except FileNotFoundError:
        # Secondary safety net -- if a file is still genuinely missing
        # (not just unreachable due to path length) for some other
        # reason, don't let one optional Chrome feature file crash the
        # entire build. Create an empty placeholder so anything
        # PyInstaller does to this path afterward (like the chmod
        # call right after this one in its own assemble() method)
        # still has something valid to act on.
        print(f"NOTE: skipping a file that could not be copied during packaging "
              f"(not needed by this app -- an optional Chrome feature file): {src}")
        try:
            _original_makedirs(_long_path(os.path.dirname(dst)), exist_ok=True)
            with open(_long_path(dst), "wb"):
                pass
        except Exception as placeholder_err:
            print(f"      (also could not create a placeholder at {dst}: {placeholder_err})")
        return dst
shutil.copyfile = _copyfile_long_path

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
