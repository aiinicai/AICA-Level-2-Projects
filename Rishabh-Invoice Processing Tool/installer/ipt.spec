# PyInstaller spec – one-folder build of IPT.  Run from the project folder:  pyinstaller installer\ipt.spec
# Result: dist\IPT\IPT.exe (+ its libraries). build_exe.bat copies Tesseract into dist\IPT\tesseract.
import os

block_cipher = None
root = os.path.abspath(os.path.join(SPECPATH, ".."))

a = Analysis(
    [os.path.join(root, "ipt", "__main__.py")],
    pathex=[root],
    datas=[(os.path.join(root, "docs"), "docs")],
    hiddenimports=["PySide6.QtCharts", "openpyxl", "pytesseract", "cv2", "numpy"],
    excludes=["tkinter", "pytest", "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.Qt3DCore"],
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="IPT", console=False,
          icon=os.path.join(root, "installer", "ipt.ico") if os.path.exists(os.path.join(root, "installer", "ipt.ico")) else None)
coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas, strip=False, upx=False, name="IPT")
