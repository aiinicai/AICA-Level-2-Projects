"""Branding & static app identity constants.

Everything a reseller/firm would need to change to re-brand the application
lives in this one module: application name, organisation name, version and
the paths to the logo/icon assets. Nothing elsewhere in the codebase should
hardcode the app name -- always import it from here.
"""
from __future__ import annotations

from pathlib import Path

#: Change this single value to rebrand the whole application (window titles,
#: About tab, generated report headers, Windows executable name via the
#: PyInstaller spec, etc.)
APP_NAME = "CA DocuFlow AI"

#: Short name used for file/folder naming (registry-safe, no special chars).
APP_SHORT_NAME = "CADocuFlowAI"

#: Shown in the About tab / installer. Replace with the licensing firm's name.
ORGANIZATION_NAME = "Kishor Singh and Co., Chartered Accountants"

#: Shown beneath APP_NAME on the Dashboard/About screens.
APP_TAGLINE = "AI-Powered Document Intelligence & PDF Automation for Chartered Accountants"

APP_VERSION = "4.0.0"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets"
ICONS_DIR = ASSETS_DIR / "icons"

#: Replace this file to change the window/taskbar icon and the logo shown on
#: the About/Dashboard pages. Falls back gracefully to Qt's default icon if
#: missing, so shipping without a custom logo is fine.
APP_ICON_PATH = ICONS_DIR / "app_icon.png"
APP_LOGO_PATH = ICONS_DIR / "app_logo.png"

#: Legal/compliance blurb shown in the About tab and near digital-signature
#: controls, reinforcing that image signatures are cosmetic, not cryptographic.
SIGNATURE_DISCLAIMER = (
    "A visible signature image confirms intent/approval in the same way a "
    "scanned wet-ink signature does, but it is NOT a cryptographically "
    "verified digital signature. For legally verifiable, tamper-evident "
    "signing, use the Certificate-Based Digital Signature option, which "
    "signs the PDF with a PKCS#12 (.pfx/.p12) certificate."
)
