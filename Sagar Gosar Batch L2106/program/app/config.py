"""Application constants and Tesseract discovery."""
import os
import shutil
import sys

APP_NAME = "Agreement Compare"
PREVIEW_DPI = 110
MAX_SCAN_CROPS = 60

_WIN_PATHS = [r"C:\Program Files\Tesseract-OCR\tesseract.exe", r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
              os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
              os.path.expandvars(r"%LOCALAPPDATA%\Tesseract-OCR\tesseract.exe")]


def configure_tesseract():
    """Point pytesseract at tesseract(.exe).  Returns True when an executable was found."""
    try:
        import pytesseract
    except ImportError:
        return False
    # bundled copy (portable package: <root>/tesseract/tesseract.exe, program files in <root>/program)
    here = os.path.dirname(os.path.abspath(__file__))
    for root in (os.path.dirname(os.path.dirname(here)), os.path.dirname(os.path.dirname(os.path.dirname(here)))):
        exe = os.path.join(root, "tesseract", "tesseract.exe" if sys.platform.startswith("win") else "tesseract")
        if os.path.isfile(exe):
            os.environ.setdefault("TESSDATA_PREFIX", os.path.join(root, "tesseract", "tessdata"))
            pytesseract.pytesseract.tesseract_cmd = exe
            return True
    cands = [os.environ.get("TESSERACT_CMD"), shutil.which("tesseract")]
    if sys.platform.startswith("win"):
        cands += _WIN_PATHS
    for c in cands:
        if c and os.path.isfile(c):
            pytesseract.pytesseract.tesseract_cmd = c
            return True
    return False
