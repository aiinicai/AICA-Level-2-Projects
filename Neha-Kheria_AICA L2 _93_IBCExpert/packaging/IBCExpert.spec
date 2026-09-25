# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller onedir specification for the ordinary IBC Expert customer application.

This specification deliberately packages ONLY the customer launcher/application. Owner-only
licensing tools and private signing material are excluded. The owner's PUBLIC verification key
must be supplied explicitly with the IBC_EXPERT_PUBLIC_KEY environment variable at build time.
"""
from pathlib import Path
import os
import re

from PyInstaller.utils.hooks import collect_submodules

PROJECT_ROOT = Path(SPECPATH).resolve().parent.parent
PUBLIC_KEY_ENV = "IBC_EXPERT_PUBLIC_KEY"


def validated_public_key() -> Path:
    raw = os.environ.get(PUBLIC_KEY_ENV, "").strip()
    if not raw:
        raise SystemExit(
            f"{PUBLIC_KEY_ENV} is required. Point it to the owner's licence_public_key.hex. "
            "Never provide owner_private_key.ibckey to the customer build."
        )
    path = Path(raw).expanduser().resolve()
    if not path.is_file():
        raise SystemExit(f"Public licence verification key not found: {path}")
    if path.name.lower() != "licence_public_key.hex":
        raise SystemExit("The customer build key file must be named licence_public_key.hex.")
    text = path.read_text(encoding="ascii").strip()
    if re.fullmatch(r"[0-9a-fA-F]{64}", text) is None:
        raise SystemExit("licence_public_key.hex must contain exactly one 32-byte key in hexadecimal.")
    return path


PUBLIC_KEY = validated_public_key()

# Keep every browser asset local. These paths intentionally mirror the source package layout so
# Path(__file__) based resource discovery continues to work in PyInstaller onedir mode.
datas = [
    (str(PROJECT_ROOT / "app" / "web" / "templates"), "app/web/templates"),
    (str(PROJECT_ROOT / "app" / "web" / "static"), "app/web/static"),
    (str(PROJECT_ROOT / "app" / "resources" / "README.txt"), "app/resources"),
    (str(PUBLIC_KEY), "app/resources"),
]

# PyWebView selects a Windows GUI backend dynamically, and Uvicorn selects protocol/lifespan
# implementations dynamically. Collect those runtime-selected modules explicitly.
hiddenimports = sorted(
    set(
        collect_submodules("webview")
        + [
            "uvicorn.logging",
            "uvicorn.loops.auto",
            "uvicorn.protocols.http.auto",
            "uvicorn.protocols.websockets.auto",
            "uvicorn.lifespan.on",
            "jinja2.ext",
            "multipart",
        ]
    )
)

# Defence in depth: owner tools are not imported by launch_desktop.py, and are also explicitly
# excluded. Test/development packages are excluded from the customer distribution as well.
excludes = [
    "owner_tools",
    "tests",
    "pytest",
    "pytest_cov",
    "coverage",
    "setuptools",
    "pip",
]

analysis = Analysis(
    [str(PROJECT_ROOT / "launch_desktop.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=1,
)
pyz = PYZ(analysis.pure)

exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="IBCExpert",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    name="IBCExpert",
)
