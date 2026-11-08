# -*- mode: python ; coding: utf-8 -*-
# Build a Windows .exe:   pip install pyinstaller   then   pyinstaller "JE Testing.spec"
import os

HERE = SPECPATH
ICON = os.path.join(HERE, "icon.ico")

a = Analysis(
    [os.path.join(HERE, "je_testing_app.py")],
    pathex=[HERE],
    hiddenimports=["openpyxl", "pandas", "numpy"],
    excludes=["scipy", "matplotlib", "sklearn", "PyQt5"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name="JE Testing",
    console=False,
    upx=True,
    icon=ICON if os.path.exists(ICON) else None,
)
