# PyInstaller build recipe.  Build with:  python -m PyInstaller --noconfirm --clean CAPracticeManager.spec
# (or just double-click build_exe.bat on Windows)
import sys

from PyInstaller.utils.hooks import collect_all, collect_submodules, copy_metadata

datas, binaries, hiddenimports = [], [], []
packages = ["streamlit", "plotly", "fpdf", "webview"]
if sys.platform == "win32":
    packages += ["pythonnet", "clr_loader"]  # the Windows app window (WebView2) needs these
for pkg in packages:
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception as e:
        print(f"WARNING: could not collect {pkg}: {e}")
for pkg in ["streamlit", "pandas", "plotly", "sqlalchemy", "openpyxl", "fpdf2", "psycopg2-binary", "pyarrow",
            "altair", "pywebview"]:
    try:
        datas += copy_metadata(pkg)
    except Exception:
        pass

# Our own files: app.py is run by Streamlit as a script, so ship the sources too
datas += [
    ("app.py", "."),
    ("seed.py", "."),
    ("due_dates.json", "."),
    (".streamlit/config.toml", ".streamlit"),
    ("assets", "assets"),
    ("core", "core"),
    ("views", "views"),
]
hiddenimports += collect_submodules("core") + collect_submodules("views") + [
    "seed", "psycopg2", "openpyxl", "pypdf", "sqlalchemy.dialects.postgresql", "sqlalchemy.dialects.sqlite",
    "webview", "tkinter",
]
if sys.platform == "win32":
    hiddenimports += ["clr", "webview.platforms.winforms", "webview.platforms.edgechromium"]

a = Analysis(
    ["run_app.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["matplotlib", "IPython", "notebook", "pytest", "playwright"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="CAPracticeManager",
    console=False,  # a proper windowed app: no black console window
    icon="assets/app.ico",
    version="version_info.txt",
)
coll = COLLECT(exe, a.binaries, a.datas, name="CAPracticeManager")
