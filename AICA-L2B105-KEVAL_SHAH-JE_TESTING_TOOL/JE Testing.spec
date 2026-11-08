# -*- mode: python ; coding: utf-8 -*-
# Build a Windows .exe:   pip install pyinstaller   then   pyinstaller "JE Testing.spec"
# The vendor's licence_generator.py and private key are deliberately NOT included.
# WARNING: build into the default 'dist' folder (or any EMPTY folder), then copy
# the .exe where it is needed. PyInstaller empties the target folder first, so
# never point --distpath at a folder holding users.json, data or workpapers.
import os

HERE = SPECPATH
ICON = os.path.join(HERE, "icon.ico")

a = Analysis(
    [os.path.join(HERE, "je_testing_app.py")],
    pathex=[HERE],
    datas=[(ICON, ".")],              # window title-bar icon
    hiddenimports=["openpyxl", "pandas", "numpy", "defusedxml", "je_access",
                   "cryptography.hazmat.primitives.asymmetric.ed25519"],
    excludes=["scipy", "matplotlib", "sklearn", "PyQt5", "IPython", "pytest",
              "licence_generator"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name="JE Testing",
    console=False,
    upx=False,
    icon=ICON if os.path.exists(ICON) else None,
)
