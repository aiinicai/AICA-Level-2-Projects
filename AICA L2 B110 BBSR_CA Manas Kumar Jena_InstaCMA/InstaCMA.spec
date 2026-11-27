# -*- mode: python ; coding: utf-8 -*-
# PyInstaller specification for InstaCMA (used by build_exe.bat)
from PyInstaller.utils.hooks import collect_all

datas = [("templates/cma_master.xlsx", "templates"), ("assets/instacma.ico", "assets"),
         ("samples/CMA_Input_Template.xlsx", "samples"),
         ("user_manual/USER_MANUAL.md", "user_manual")]
binaries = []
hiddenimports = ["matplotlib.backends.backend_agg", "xlrd", "win32com", "win32com.client", "pythoncom", "pywintypes"]
for pkg in ("pypdfium2", "pypdfium2_raw", "pdfplumber", "pdfminer", "rapidfuzz"):
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        pass

a = Analysis(["main.py"], pathex=["."], binaries=binaries, datas=datas, hiddenimports=hiddenimports,
             excludes=["tkinter", "PySide2", "PySide6", "PyQt6", "IPython", "notebook", "pytest"])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="InstaCMA", console=False, upx=False, icon="assets/instacma.ico")
coll = COLLECT(exe, a.binaries, a.datas, upx=False, name="InstaCMA")
