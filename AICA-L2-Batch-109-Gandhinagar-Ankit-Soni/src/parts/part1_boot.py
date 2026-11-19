#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
 BALANCE CONFIRMATION GENERATOR  -  desktop edition
 -----------------------------------------------------------------------------
 Generates individual Microsoft Word (.docx) balance-confirmation letters from
 an Excel / CSV schedule of party balances, and e-mails each letter to the
 party from the auditor's own mailbox.

 Single file.  Run it with:      python balance_confirmation_generator.py
 Works from IDLE (Run > Run Module) and from a terminal.

 On the FIRST run the script installs the libraries it needs and then starts.
 When packaged with PyInstaller the installer is skipped automatically.

 Everything stays on this computer.  The only outbound connection the program
 ever makes is to your own mail server when you press Send.
===============================================================================
"""

import os
import sys
import subprocess
import importlib
import importlib.util

APP_NAME = "Balance Confirmation Generator"
APP_VERSION = "3.5"

# ---------------------------------------------------------------------------
# SECTION 1 - FIRST-RUN DEPENDENCY INSTALLER
# ---------------------------------------------------------------------------
# Each entry is (import name, pip requirement, what it is used for, required).
# Optional libraries are offered but the program still starts without them.
# ---------------------------------------------------------------------------
# pip is run with --upgrade, so each of these installs the newest release.
# The lower bounds simply rule out versions too old to behave.
REQUIREMENTS = [
    ("PyQt6",    "PyQt6>=6.7",      "the application window",            True),
    ("openpyxl", "openpyxl>=3.1.5", "reading .xlsx workbooks",           True),
    ("reportlab", "reportlab>=4.2",  "exporting the reports to PDF",     True),
    ("xlrd",     "xlrd>=2.0.1",     "reading older .xls workbooks",      False),
    ("keyring",  "keyring>=25.0",   "storing the mail password safely",  False),
    # reading the PDF or scan a party sends back: text layer, then OCR.
    # All three install from pip alone and work offline; the OCR models are
    # inside the rapidocr package.
    ("pymupdf",  "pymupdf>=1.24",   "opening the PDFs parties send back", False),
    ("onnxruntime", "onnxruntime>=1.17", "running the OCR engine",       False),
    ("rapidocr", "rapidocr>=3.0",   "reading scanned and handwritten slips", False),
]

_FROZEN = getattr(sys, "frozen", False) or hasattr(sys, "_MEIPASS")


def _have(module_name):
    try:
        importlib.import_module(module_name)
        return True
    except Exception:
        return False


def _pip_install(requirement):
    """Install one requirement with the interpreter that is running us."""
    cmd = [sys.executable, "-m", "pip", "install", "--upgrade", requirement]
    # Debian/Ubuntu refuse to install into a managed environment without this.
    if sys.platform.startswith("linux"):
        cmd.insert(4, "--break-system-packages")
    creation = 0
    if os.name == "nt":                       # no console flash on Windows
        creation = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              timeout=900, creationflags=creation) \
            if creation else \
            subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        return proc.returncode == 0, (proc.stderr or proc.stdout or "").strip()
    except Exception as exc:                  # pip missing, offline, blocked
        return False, str(exc)


def ensure_dependencies():
    """Install anything missing.  Returns the list of optional modules absent."""
    if _FROZEN:
        return [name for name, _, _, req in REQUIREMENTS
                if not req and not _have(name)]

    missing = [(n, r, p, req) for (n, r, p, req) in REQUIREMENTS if not _have(n)]
    if missing:
        line = "=" * 74
        print(line)
        print(" %s %s - first-run setup" % (APP_NAME, APP_VERSION))
        print(line)
        print(" The following libraries are needed and will be installed once:")
        for _, req, purpose, required in missing:
            print("   - %-18s %s%s" % (req, purpose,
                                       "" if required else "  (optional)"))
        print(" This usually takes a minute.  Please keep this window open.")
        print(line)

        for name, req, purpose, required in missing:
            print(" Installing %s ..." % req, flush=True)
            ok, detail = _pip_install(req)
            if ok and _have(name):
                print("   done.")
                continue
            if required:
                print("\n Could not install %s automatically." % req)
                print(" Please open a command prompt and run:\n")
                print("     %s -m pip install %s\n" % (sys.executable, req))
                if detail:
                    print(" Reason reported by pip:")
                    print(" " + detail.splitlines()[-1][:300])
                input("\n Press Enter to close. ")
                sys.exit(1)
            print("   skipped - %s will be unavailable." % purpose)
        print(line)
        print(" Setup finished.  Starting %s ...\n" % APP_NAME, flush=True)

    return [name for name, _, _, req in REQUIREMENTS
            if not req and not _have(name)]


OPTIONAL_MISSING = ensure_dependencies()
HAS_XLRD = "xlrd" not in OPTIONAL_MISSING
HAS_KEYRING = "keyring" not in OPTIONAL_MISSING

# ---------------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------------
import csv
import io
import json
import re
import smtplib
import ssl
import traceback
import base64
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zipfile
from datetime import date, datetime, timezone
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid

import openpyxl
from PyQt6.QtCore import (QDate, QObject, QRect, QSize, Qt, QThread, QTimer,
                          pyqtSignal)
from PyQt6.QtGui import (QAction, QColor, QFont, QFontDatabase, QIcon, QPainter,
                         QPalette, QPixmap, QTextDocument)
from PyQt6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox,
                             QComboBox, QDateEdit, QDialog, QDoubleSpinBox, QGraphicsDropShadowEffect, QDialogButtonBox,
                             QFileDialog, QFormLayout, QFrame, QGridLayout,
                             QGroupBox, QHBoxLayout, QHeaderView, QLabel,
                             QLayout, QLineEdit, QListWidget, QListWidgetItem,
                             QMainWindow, QMessageBox, QPlainTextEdit,
                             QProgressBar, QPushButton, QScrollArea,
                             QSizePolicy, QSpinBox, QSplitter, QStackedWidget,
                             QStyle, QTableWidget, QTableWidgetItem, QTabWidget,
                             QTextBrowser, QVBoxLayout, QWidget)

if HAS_KEYRING:
    try:
        import keyring
    except Exception:
        HAS_KEYRING = False
