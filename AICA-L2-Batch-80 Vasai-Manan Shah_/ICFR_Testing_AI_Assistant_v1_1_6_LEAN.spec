# -*- mode: python ; coding: utf-8 -*-
"""Lean Windows PyInstaller build for ICFR Testing AI Assistant v1.1.6."""
import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

APP_NAME = "ICFR_Testing_AI_Assistant_v1_1_6"
SCRIPT = "ICFR_Testing_AI_Assistant_v1_1_6.py"


def find_tesseract_home():
    candidates=[]
    env=os.environ.get("TESSERACT_HOME","").strip()
    if env:
        candidates.append(Path(env))
    candidates.extend([
        Path(r"C:\Program Files\Tesseract-OCR"),
        Path(r"C:\Program Files (x86)\Tesseract-OCR"),
    ])
    for p in candidates:
        if (p/"tesseract.exe").exists():
            return p
    raise SystemExit(
        "Tesseract not found. Set TESSERACT_HOME to the folder containing tesseract.exe."
    )


tess=find_tesseract_home()
eng=tess/"tessdata"/"eng.traineddata"
if not eng.exists():
    raise SystemExit(f"Required English OCR language data not found: {eng}")

# Bundle only the OCR runtime and English traineddata used by the application.
binaries=[(str(tess/"tesseract.exe"),"tesseract")]
for dll in tess.glob("*.dll"):
    binaries.append((str(dll),"tesseract"))

datas=[(str(eng),"tesseract/tessdata")]
for name in ("LICENSE","LICENSE.txt","COPYING"):
    p=tess/name
    if p.exists():
        datas.append((str(p),"tesseract"))

hiddenimports=[
    "tkinter","tkinter.ttk","tkinter.filedialog","tkinter.messagebox","tkinter.simpledialog",
    "win32timezone","win32com","win32com.client","pythoncom","pywintypes","win32cred",
    "PIL.Image","PIL.ImageTk","PIL.ImageOps","PIL.ImageEnhance","PIL.ImageFilter",
]
try:
    hiddenimports += collect_submodules("win32com")
except Exception:
    pass

# These packages are not used in v1.1.6. Excluding them materially reduces the EXE.
excludes=[
    "matplotlib","numpy","reportlab","pandas","scipy","sympy","IPython","jupyter",
    "notebook","pytest","setuptools.tests","tkinter.test","unittest.test",
]

a=Analysis(
    [SCRIPT],
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
pyz=PYZ(a.pure)
exe=EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
)
