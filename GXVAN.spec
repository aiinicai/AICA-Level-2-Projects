# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for GXVAN.  Windows -> dist/GXVAN/GXVAN.exe ; macOS -> dist/GXVAN.app
# Easiest: run build_windows.bat (Windows) or build_mac.sh (macOS).
# Manual:  pip install -r requirements.txt pyinstaller
#          pip uninstall -y opencv-python && pip install opencv-python-headless   (avoids a Qt clash that hangs the exe)
#          pyinstaller GXVAN.spec --noconfirm
# Use Python 3.10-3.13 so RapidOCR (onnxruntime) and its ONNX models are bundled.
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datas = [("assets", "assets")]
hidden = ["pymupdf", "xlsxwriter", "openpyxl", "dateutil", "rapidfuzz", "qrcode", "reportlab"]
try:
    datas += collect_data_files("rapidocr_onnxruntime")      # ONNX models + config.yaml
    hidden += collect_submodules("rapidocr_onnxruntime")
except Exception:  # OCR not installed in the build environment
    pass

a = Analysis(["GXVAN.py"], pathex=["."], datas=datas, hiddenimports=hidden,
             excludes=["tkinter", "PyQt5", "pytest", "matplotlib", "IPython"], noarchive=False)
pyz = PYZ(a.pure)
icon = "assets/gxvan_icon.icns" if sys.platform == "darwin" else "assets/gxvan_icon.ico"
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="GXVAN", console=False, icon=icon)
coll = COLLECT(exe, a.binaries, a.datas, name="GXVAN")
if sys.platform == "darwin":
    app = BUNDLE(coll, name="GXVAN.app", icon=icon, bundle_identifier="com.vantage.gxvan")
