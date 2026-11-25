"""Local-only configuration for the Windows v0 Edition (PyInstaller-compatible)."""

from __future__ import annotations

import inspect
import os
import sys
from pathlib import Path


def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"))


if _is_frozen():
    BUNDLE_DIR = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    APP_DIR = Path(sys.executable).resolve().parent
else:
    BUNDLE_DIR = Path(__file__).resolve().parent.parent
    APP_DIR = BUNDLE_DIR

TEMPLATES_DIR = BUNDLE_DIR / "templates"
STATIC_DIR = BUNDLE_DIR / "static"
DATA_DIR = Path(os.getenv("V0_DATA_DIR", str(APP_DIR / "data")))
EXPORTS_DIR = DATA_DIR / "exports"
UPLOADS_DIR = Path(
    os.getenv(
        "V0_UPLOADS_DIR",
        str(APP_DIR / "uploads" if _is_frozen() else APP_DIR / "static" / "uploads"),
    )
)
DB_PATH = Path(os.getenv("V0_DB_PATH", str(DATA_DIR / "v0_assets.db")))
MASTER_EXCEL_PATH = EXPORTS_DIR / "v0_assets_master.xlsx"

COMPANY_NAME = os.getenv("COMPANY_NAME", "AssetTrack")
PORT = int(os.getenv("PORT", "8000"))


def ensure_directories() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


def render_template(templates, request, name: str, context: dict | None = None):
    """Version-proof Starlette TemplateResponse helper (Starlette 0.27 through 1.0+)."""
    ctx = dict(context or {})
    params = list(inspect.signature(templates.TemplateResponse).parameters.keys())
    if params and params[0] == "request":
        return templates.TemplateResponse(request=request, name=name, context=ctx)
    ctx["request"] = request
    return templates.TemplateResponse(name, ctx)
