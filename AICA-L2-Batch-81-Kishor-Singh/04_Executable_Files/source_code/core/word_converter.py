"""Word (.doc/.docx) -> PDF conversion.

Two backends are supported:

* ``MS_WORD_COM`` -- drives a real, installed copy of Microsoft Word via COM
  automation (``pywin32``). This is the highest-fidelity option: Word itself
  performs the conversion, so fonts, margins, tables, headers/footers, page
  numbering, orientation, images and section breaks are preserved exactly as
  Word would print them. Windows + Microsoft Word only.

* ``LIBREOFFICE`` -- shells out to ``soffice --headless --convert-to pdf``.
  Used as a fallback when Word is not installed. Layout fidelity is usually
  good but not guaranteed to be pixel-identical to Word's own rendering
  (different layout engines), which is why it is presented as an *optional
  fallback*, not the default.

``AUTO`` tries Word first and falls back to LibreOffice automatically.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from models.enums import WordEngine
from utils.logging_utils import get_logger
from utils.validation import ValidationError, validate_word_path

logger = get_logger("word_converter")


@dataclass
class ConversionResult:
    output_path: str
    engine_used: WordEngine


@dataclass
class WordDocumentInfo:
    """Lightweight metadata read straight from the .docx XML, without opening Word.

    Used to show the user something useful about a queued file (paragraph/
    table/section counts) before conversion runs, and to estimate whether a
    document is large enough to warrant a progress warning. `.doc` (legacy
    binary format) is not introspectable this way -- ``python-docx`` only
    reads the modern `.docx`/OOXML format -- so those return ``None`` fields
    with ``supported`` set to ``False``.
    """

    paragraph_count: int = 0
    table_count: int = 0
    section_count: int = 0
    approx_word_count: int = 0
    supported: bool = True


def inspect_word_document(path: str | Path) -> WordDocumentInfo:
    """Read basic structural metadata from a .docx file using python-docx.

    This never converts or renders the document -- it only parses the
    document XML, so it's fast enough to run on every file as it's added
    to a batch. Legacy `.doc` files (pre-2007 binary format) aren't
    supported by python-docx and return ``supported=False``.
    """
    path = Path(path)
    if path.suffix.lower() != ".docx":
        return WordDocumentInfo(supported=False)
    try:
        import docx
    except ImportError:
        return WordDocumentInfo(supported=False)
    try:
        document = docx.Document(str(path))
    except Exception:
        return WordDocumentInfo(supported=False)

    paragraphs = document.paragraphs
    word_count = sum(len(p.text.split()) for p in paragraphs)
    return WordDocumentInfo(
        paragraph_count=len(paragraphs),
        table_count=len(document.tables),
        section_count=len(document.sections),
        approx_word_count=word_count,
        supported=True,
    )


def is_word_com_available() -> bool:
    """Check whether Microsoft Word can be automated on this machine."""
    if sys.platform != "win32":
        return False
    try:
        import win32com.client
    except ImportError:
        return False
    try:
        # Attempt a lightweight dispatch; GetActiveObject/Dispatch will raise
        # com_error if Word is not installed/registered.
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        word.Quit()
        return True
    except Exception:
        return False


def find_libreoffice(explicit_path: str = "") -> str | None:
    if explicit_path and Path(explicit_path).exists():
        return explicit_path
    candidates = [
        shutil.which("soffice"),
        shutil.which("soffice.exe"),
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    ]
    for c in candidates:
        if c and Path(c).exists():
            return c
    return None


def is_libreoffice_available(explicit_path: str = "") -> bool:
    return find_libreoffice(explicit_path) is not None


class WordToPdfConverter:
    """Facade selecting and running the appropriate conversion backend."""

    def __init__(self, engine: WordEngine = WordEngine.AUTO, libreoffice_path: str = ""):
        self.engine = engine
        self.libreoffice_path = libreoffice_path

    def convert(self, source_path: str | Path, output_path: str | Path) -> ConversionResult:
        source_path = validate_word_path(source_path)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        engine = self.engine
        if engine == WordEngine.AUTO:
            engine = WordEngine.MS_WORD_COM if is_word_com_available() else WordEngine.LIBREOFFICE

        if engine == WordEngine.MS_WORD_COM:
            if not is_word_com_available():
                if self.engine == WordEngine.AUTO:
                    logger.info("Microsoft Word not available; falling back to LibreOffice.")
                    return self._convert_libreoffice(source_path, output_path)
                raise ValidationError(
                    "Microsoft Word is not installed or could not be automated on this "
                    "computer. Install Microsoft Word, or switch the conversion engine "
                    "to LibreOffice in Settings."
                )
            try:
                return self._convert_word_com(source_path, output_path)
            except ValidationError:
                raise
            except Exception as exc:
                if self.engine == WordEngine.AUTO and is_libreoffice_available(self.libreoffice_path):
                    logger.warning("Word COM conversion failed (%s); retrying with LibreOffice.", exc)
                    return self._convert_libreoffice(source_path, output_path)
                raise ValidationError(f"Word failed to convert '{source_path.name}': {exc}") from exc

        return self._convert_libreoffice(source_path, output_path)

    def _convert_word_com(self, source_path: Path, output_path: Path) -> ConversionResult:
        import pythoncom
        import win32com.client

        # COM must be initialized on the thread it's used from -- callers
        # running this inside a QThread must ensure CoInitialize is called
        # (BatchWorker does this for every worker thread it starts).
        pythoncom.CoInitialize()
        word = None
        doc = None
        try:
            word = win32com.client.DispatchEx("Word.Application")
            word.Visible = False
            word.DisplayAlerts = 0  # wdAlertsNone
            doc = word.Documents.Open(str(source_path), ReadOnly=True)
            # 17 == wdFormatPDF
            doc.SaveAs(str(output_path), FileFormat=17)
        finally:
            if doc is not None:
                try:
                    doc.Close(False)
                except Exception:
                    pass
            if word is not None:
                try:
                    word.Quit()
                except Exception:
                    pass
            pythoncom.CoUninitialize()

        if not output_path.exists():
            raise ValidationError(f"Word did not produce an output file for '{source_path.name}'.")
        return ConversionResult(output_path=str(output_path), engine_used=WordEngine.MS_WORD_COM)

    def _convert_libreoffice(self, source_path: Path, output_path: Path) -> ConversionResult:
        soffice = find_libreoffice(self.libreoffice_path)
        if not soffice:
            raise ValidationError(
                "Neither Microsoft Word nor LibreOffice was found on this computer. "
                "Install Microsoft Word, or install LibreOffice "
                "(https://www.libreoffice.org/) and set its path in Settings."
            )
        out_dir = output_path.parent
        cmd = [
            soffice,
            "--headless",
            "--norestore",
            "--convert-to",
            "pdf",
            "--outdir",
            str(out_dir),
            str(source_path),
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        except subprocess.TimeoutExpired as exc:
            raise ValidationError(f"LibreOffice timed out converting '{source_path.name}'.") from exc
        if proc.returncode != 0:
            raise ValidationError(
                f"LibreOffice failed to convert '{source_path.name}':\n{proc.stderr.strip()}"
            )
        produced = out_dir / f"{source_path.stem}.pdf"
        if not produced.exists():
            raise ValidationError(f"LibreOffice did not produce an output file for '{source_path.name}'.")
        if produced != output_path:
            produced.replace(output_path)
        return ConversionResult(output_path=str(output_path), engine_used=WordEngine.LIBREOFFICE)
