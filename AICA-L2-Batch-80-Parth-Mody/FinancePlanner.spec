# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the Personal Finance & Debt Impact Calculator.

Streamlit needs three things a default build does not give it: its static web
assets, its package metadata (it reads its own version at import), and a long
tail of lazily imported submodules. collect_all covers data/binaries/submodules;
copy_metadata covers the version lookups.
"""
from PyInstaller.utils.hooks import collect_all, copy_metadata

datas, binaries, hiddenimports = [], [], []

# Packages whose data files and submodules must come along wholesale.
for pkg in ("streamlit", "plotly", "narwhals", "altair", "pyarrow",
            "xlsxwriter", "openpyxl", "pandas", "numpy"):
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception as exc:                                   # noqa: BLE001
        print(f"[spec] collect_all({pkg}) skipped: {exc}")

# Distributions whose metadata is read at runtime (importlib.metadata.version).
for dist in ("streamlit", "altair", "pyarrow", "pandas", "numpy", "plotly",
             "narwhals", "xlsxwriter", "openpyxl", "click", "tornado",
             "protobuf", "packaging", "tenacity", "typing_extensions",
             "watchdog", "GitPython", "gitdb", "pydeck", "blinker",
             "cachetools", "toml", "rich", "requests", "pillow", "jsonschema",
             "attrs", "jinja2", "python-dateutil", "pytz", "tzdata", "six",
             "smmap", "urllib3", "certifi", "charset-normalizer", "idna",
             "markupsafe", "pygments", "markdown-it-py", "mdurl",
             "referencing", "rpds-py", "jsonschema-specifications"):
    try:
        datas += copy_metadata(dist)
    except Exception:                                          # noqa: BLE001
        pass

# The Streamlit script itself travels as data and is executed by the bootstrap.
datas += [("Finance.py", ".")]

hiddenimports += [
    "streamlit.web.bootstrap",
    "streamlit.web.cli",
    "streamlit.runtime.scriptrunner.magic_funcs",
    "streamlit.runtime.caching",
    "streamlit.runtime.state",
    "xlsxwriter",
    "openpyxl.cell._writer",
    "pandas._libs.tslibs.base",
    "plotly.graph_objects",
    "plotly.express",
]

# Big, unused GUI/scientific stacks that otherwise get pulled in.
excludes = ["tkinter", "matplotlib", "PyQt5", "PyQt6", "PySide2", "PySide6",
            "IPython", "notebook", "jupyter", "pytest", "sphinx", "scipy",
            "torch", "tensorflow", "PIL.ImageQt"]

a = Analysis(
    ["launcher.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,          # onedir: libraries live beside the exe
    name="FinancePlanner",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,          # the console carries the local URL and any error
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# A onedir build does not self-extract 130 MB to a temp folder on every launch,
# which is both far faster to start and avoids the extraction failure that a
# onefile build of this size hit during interpreter start-up.
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="FinancePlanner",
)
