# PyInstaller spec for MSME Verification System
# Build with:  pyinstaller --noconfirm --clean msme_app.spec
# Set ONEFILE = False below to build a folder (faster start-up, fewer
# antivirus false alarms) instead of a single .exe.

ONEFILE = True
NAME = "MSME_Verification_System"

a = Analysis(
    ["msme_app.py"],
    pathex=[],
    binaries=[],
    datas=[("assets/app.ico", "assets"), ("assets/app.png", "assets")],
    hiddenimports=["openpyxl", "excel_export"],
    hookspath=[],
    runtime_hooks=[],
    # not used by the app - keeps the .exe smaller
    excludes=["tkinter", "unittest", "pydoc", "doctest", "pdb", "PIL", "numpy",
              "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtNetwork",
              "PySide6.QtOpenGL", "PySide6.QtSql", "PySide6.QtTest",
              "PySide6.QtSvg", "PySide6.QtPdf",
              # optional compressors (zipfile/openpyxl fall back to zlib) and
              # C decimal (falls back to the pure-Python version)
              "bz2", "_bz2", "lzma", "_lzma", "compression.zstd", "_zstd",
              "_decimal", "sqlite3", "xmlrpc", "multiprocessing"],
    noarchive=False,
    optimize=2,             # strip docstrings/asserts from bundled code
)


# Qt files the app never uses - leaving them out keeps the .exe under 25 MB
# (GitHub's website upload limit).  Kept: the Windows platform plugin, the
# .ico image plugin, and everything Python needs for HTTPS.
def _wanted(entry):
    name = entry[0].replace("\\", "/").lower()
    if name.endswith("opengl32sw.dll"):            # software OpenGL, 20 MB
        return False
    if "/translations/" in name:                   # Qt's own UI translations
        return False
    for lib in ("qt6network", "qt6svg", "qt6pdf", "qt6qml", "qt6quick",
                "qt6opengl", "qt6virtualkeyboard"):
        if lib in name:
            return False
    if "/plugins/" in name:
        return (name.endswith("/platforms/qwindows.dll")
                or name.endswith("/imageformats/qico.dll"))
    return True


a.binaries = [b for b in a.binaries if _wanted(b)]
a.datas = [d for d in a.datas if _wanted(d)]
pyz = PYZ(a.pure)

common = dict(
    name=NAME,
    icon="assets/app.ico",
    version="version_info.txt",
    console=False,          # no command prompt window
    upx=False,              # UPX often triggers antivirus false alarms
    debug=False,
    strip=False,
)

if ONEFILE:
    exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], **common)
else:
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, **common)
    coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name=NAME)
