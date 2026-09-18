"""Shared enumerations used across the whole application.

Keeping every controlled vocabulary in one module avoids magic strings
scattered through the UI and engines, and makes it trivial for
``combo_box.addItems([e.value for e in Enum])`` style UI code.
"""
from __future__ import annotations

from enum import Enum


class PositionPreset(str, Enum):
    """Predefined signature/stamp/watermark placements on a page."""

    BOTTOM_LEFT = "Bottom Left"
    BOTTOM_CENTRE = "Bottom Centre"
    BOTTOM_RIGHT = "Bottom Right"
    TOP_LEFT = "Top Left"
    TOP_CENTRE = "Top Centre"
    TOP_RIGHT = "Top Right"
    CENTRE = "Centre"
    CUSTOM = "Custom"


class PageSelectionMode(str, Enum):
    """High level page-selection strategies exposed in the UI.

    ``CUSTOM`` allows any raw expression such as ``1,3,5-8,last``.
    """

    SINGLE_PAGE = "Single Page"
    MULTIPLE_PAGES = "Multiple Pages"
    PAGE_RANGE = "Page Range"
    FIRST_PAGE = "First Page"
    LAST_PAGE = "Last Page"
    FIRST_AND_LAST = "First and Last Page"
    ALL_PAGES = "All Pages"
    ODD_PAGES = "Odd Pages"
    EVEN_PAGES = "Even Pages"
    EVERY_NTH_PAGE = "Every Nth Page"
    LAST_N_PAGES = "Last N Pages"
    CUSTOM = "Custom Expression"


class SignatureKind(str, Enum):
    """The role a visible-image layer plays; purely descriptive/organisational."""

    SIGNATURE = "Signature"
    INITIAL = "Initial"
    STAMP = "Stamp"
    SEAL = "Company Seal"


class NamingMode(str, Enum):
    KEEP_ORIGINAL = "Keep Original Filename"
    ADD_SUFFIX = "Add Suffix"
    ADD_PREFIX = "Add Prefix"
    OVERWRITE_ORIGINAL = "Overwrite Original"


class CollisionPolicy(str, Enum):
    SKIP = "Skip"
    REPLACE = "Replace"
    RENAME = "Rename Automatically"


class JobStatus(str, Enum):
    PENDING = "Pending"
    PROCESSING = "Processing"
    SUCCESS = "Success"
    FAILED = "Failed"
    SKIPPED = "Skipped"
    CANCELLED = "Cancelled"


class WordEngine(str, Enum):
    AUTO = "Auto (Word if available, else LibreOffice)"
    MS_WORD_COM = "Microsoft Word (COM Automation)"
    LIBREOFFICE = "LibreOffice (headless)"


class ThemeMode(str, Enum):
    SYSTEM = "System"
    LIGHT = "Light"
    DARK = "Dark"


class SplitMode(str, Enum):
    EVERY_PAGE = "Split Every Page"
    BY_RANGE = "Split by Page Range"
    EXTRACT_PAGES = "Extract Pages"
    EVERY_N_PAGES = "Split Every N Pages"
    EQUAL_PARTS = "Split Into Equal Parts"
    REMOVE_PAGES = "Remove Pages"


class SignatureType(str, Enum):
    """Distinguishes a cosmetic image stamp from a cryptographic PDF signature.

    This distinction is surfaced in the UI so a visible image is never
    represented to the user as a cryptographically verified signature.
    """

    VISIBLE_IMAGE = "Visible Signature Image"
    DIGITAL_CERTIFICATE = "Cryptographic Digital Signature"
