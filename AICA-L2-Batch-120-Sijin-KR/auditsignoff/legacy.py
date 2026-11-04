"""Old Office formats (.doc, .xls, .rtf, .odt, .ods) -> .docx/.xlsx, fully offline.
Order tried: LibreOffice (if installed) -> Microsoft Word/Excel on this PC (via PowerShell COM) -> clear error."""
from __future__ import annotations
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TARGET = {".doc": ".docx", ".rtf": ".docx", ".odt": ".docx", ".dot": ".docx",
          ".xls": ".xlsx", ".ods": ".xlsx"}
LEGACY_EXT = set(TARGET)


def _soffice():
    for n in ("soffice", "libreoffice"):
        p = shutil.which(n)
        if p:
            return p
    for p in (r"C:\Program Files\LibreOffice\program\soffice.exe", r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"):
        if os.path.exists(p):
            return p
    return None


def _via_soffice(src: Path, out_dir: Path, target_ext: str):
    exe = _soffice()
    if not exe:
        return None
    prof = tempfile.mkdtemp(prefix="lo_profile_")
    cmd = [exe, f"-env:UserInstallation={Path(prof).as_uri()}", "--headless", "--convert-to", target_ext.lstrip("."),
           "--outdir", str(out_dir), str(src)]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=180)
    except Exception:
        return None
    out = out_dir / (src.stem + target_ext)
    return out if out.exists() else None


def _via_office_com(src: Path, out_dir: Path, target_ext: str):
    if sys.platform != "win32":
        return None
    out = out_dir / (src.stem + target_ext)
    if target_ext == ".docx":
        ps = ("$a=New-Object -ComObject Word.Application;$a.Visible=$false;$a.DisplayAlerts=0;"
              f"$d=$a.Documents.Open('{src}',$false,$true);$d.SaveAs2('{out}',16);$d.Close($false);$a.Quit()")
    else:
        ps = ("$a=New-Object -ComObject Excel.Application;$a.Visible=$false;$a.DisplayAlerts=$false;"
              f"$w=$a.Workbooks.Open('{src}');$w.SaveAs('{out}',51);$w.Close($false);$a.Quit()")
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True, capture_output=True, timeout=180)
    except Exception:
        return None
    return out if out.exists() else None


def ensure_modern(path) -> Path:
    """Return a .docx/.xlsx path for a legacy file; any other file is returned unchanged."""
    src = Path(path).resolve()
    ext = src.suffix.lower()
    if ext not in LEGACY_EXT:
        return Path(path)
    tgt = TARGET[ext]
    out_dir = Path(tempfile.mkdtemp(prefix="as_conv_"))
    for conv in (_via_soffice, _via_office_com):
        out = conv(src, out_dir, tgt)
        if out:
            return out
    raise ValueError(f"'{src.name}' is an old Office format ({ext}). Automatic conversion needs Microsoft Word/Excel or "
                     f"LibreOffice on this PC. Alternatively open it and use File > Save As > {tgt[1:].upper()} (or PDF), then upload that.")
