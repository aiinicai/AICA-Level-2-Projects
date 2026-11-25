# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec to build standalone Windows AssetTrack_v0.exe."""

from PyInstaller.utils.hooks import collect_submodules

hidden_imports = (
    collect_submodules("uvicorn")
    + collect_submodules("fastapi")
    + collect_submodules("starlette")
    + collect_submodules("pydantic")
    + ["multipart", "python_multipart", "openpyxl", "jinja2", "sqlite3"]
)

a = Analysis(
    ["run_v0.py"],
    pathex=["."],
    binaries=[],
    datas=[("templates", "templates"), ("static", "static")],
    hiddenimports=hidden_imports,
    excludes=["tkinter", "unittest", "pydoc", "doctest", "test"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="AssetTrack_v0",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
)
