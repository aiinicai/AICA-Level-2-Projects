"""Offline OCR.

1. Windows built-in OCR (Windows.Media.Ocr) driven through Windows PowerShell 5.1: no install,
   signed by Microsoft, works offline. Needs an English language pack (present on most PCs).
2. Tesseract, if installed (tesseract.exe on PATH or in Program Files).
Both return words with pixel boxes, so redaction can black out PAN / bank details.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Word:
    text: str
    x: float
    y: float
    w: float
    h: float


@dataclass
class OcrResult:
    text: str = ""
    words: list[Word] = field(default_factory=list)
    engine: str = ""
    error: str = ""


_PS_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
$path = $args[0]
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
  $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and
  $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]
function Await($op, $type) {
  $t = $asTaskGeneric.MakeGenericMethod($type).Invoke($null, @($op)); $t.Wait(-1) | Out-Null; $t.Result }
[Windows.Storage.StorageFile,Windows.Storage,ContentType=WindowsRuntime] | Out-Null
[Windows.Media.Ocr.OcrEngine,Windows.Foundation,ContentType=WindowsRuntime] | Out-Null
[Windows.Graphics.Imaging.BitmapDecoder,Windows.Graphics,ContentType=WindowsRuntime] | Out-Null
$file = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($path)) ([Windows.Storage.StorageFile])
$stream = Await ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
$decoder = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
$bmp = Await ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
if ($engine -eq $null) { throw "No Windows OCR language installed (Settings > Time & language > Language: add English with OCR)" }
$res = Await ($engine.RecognizeAsync($bmp)) ([Windows.Media.Ocr.OcrResult])
$lines = @()
foreach ($l in $res.Lines) {
  $words = @()
  foreach ($w in $l.Words) { $r = $w.BoundingRect; $words += @{t=$w.Text; x=$r.X; y=$r.Y; w=$r.Width; h=$r.Height} }
  $lines += @{text=$l.Text; words=$words}
}
$stream.Dispose()
@{lines=$lines} | ConvertTo-Json -Depth 5 -Compress
"""


def _temp_path(suffix: str) -> Path:
    """mkstemp returns an open handle; close it or Windows keeps the file locked for other processes."""
    fd, name = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    return Path(name)


def _image_to_png_file(img: bytes) -> Path:
    """Normalise any Qt-readable image (JPEG/TIFF/PNG) to PNG; upscale small scans for accuracy."""
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QImage
    q = QImage.fromData(img)
    if q.isNull():
        raise ValueError("Image could not be decoded")
    if q.width() < 1600:
        q = q.scaledToWidth(1600, Qt.TransformationMode.SmoothTransformation)
    if q.width() > 9000 or q.height() > 9000:          # Windows OCR max dimension is ~10000
        q = q.scaled(9000, 9000, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    p = _temp_path(".png")
    q.save(str(p), "PNG")
    return p


def ocr_width(img: bytes) -> float:
    """Width of the image as OCR saw it (small scans are upscaled first) - word boxes are in this space."""
    from PyQt6.QtGui import QImage
    q = QImage.fromData(img)
    w = q.width()
    if w < 1600:
        return 1600.0
    if w > 9000 or q.height() > 9000:
        return w * min(9000 / w, 9000 / q.height())
    return float(w)


def windows_ocr(img: bytes, timeout: int = 90) -> OcrResult:
    if os.name != "nt":
        return OcrResult(error="Windows OCR is only available on Windows")
    png = _image_to_png_file(img)
    script = _temp_path(".ps1")
    script.write_text(_PS_SCRIPT, encoding="utf-8-sig")
    try:
        r = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                            "-File", str(script), str(png)], capture_output=True, timeout=timeout,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if r.returncode != 0:
            return OcrResult(engine="windows", error=r.stderr.decode(errors="replace")[-400:])
        data = json.loads(r.stdout.decode("utf-8", errors="replace") or "{}")
        lines = data.get("lines") or []
        if isinstance(lines, dict):
            lines = [lines]
        words, text_lines = [], []
        for ln in lines:
            ws = ln.get("words") or []
            if isinstance(ws, dict):
                ws = [ws]
            words += [Word(w["t"], w["x"], w["y"], w["w"], w["h"]) for w in ws]
            text_lines.append(ln.get("text", ""))
        return OcrResult(text=_layout_text(words) or "\n".join(text_lines), words=words, engine="windows")
    except Exception as e:
        return OcrResult(engine="windows", error=str(e))
    finally:
        for p in (png, script):
            try:
                p.unlink()
            except OSError:
                pass


_PS_RENDER = r"""
$ErrorActionPreference = 'Stop'
$path = $args[0]; $outDir = $args[1]; $max = [int]$args[2]; $dpi = [double]$args[3]
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$m = [System.WindowsRuntimeSystemExtensions].GetMethods()
$asTaskGeneric = ($m | Where-Object { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and
  $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]
$asTaskAction = ($m | Where-Object { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and
  $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncAction' })[0]
function Await($op, $type) { $t = $asTaskGeneric.MakeGenericMethod($type).Invoke($null, @($op)); $t.Wait(-1) | Out-Null; $t.Result }
function AwaitAction($a) { $t = $asTaskAction.Invoke($null, @($a)); $t.Wait(-1) | Out-Null }
[Windows.Storage.StorageFile,Windows.Storage,ContentType=WindowsRuntime] | Out-Null
[Windows.Storage.StorageFolder,Windows.Storage,ContentType=WindowsRuntime] | Out-Null
[Windows.Data.Pdf.PdfDocument,Windows.Data.Pdf,ContentType=WindowsRuntime] | Out-Null
$file = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($path)) ([Windows.Storage.StorageFile])
$doc = Await ([Windows.Data.Pdf.PdfDocument]::LoadFromFileAsync($file)) ([Windows.Data.Pdf.PdfDocument])
$folder = Await ([Windows.Storage.StorageFolder]::GetFolderFromPathAsync($outDir)) ([Windows.Storage.StorageFolder])
$n = [Math]::Min([int]$doc.PageCount, $max)
for ($i = 0; $i -lt $n; $i++) {
  $page = $doc.GetPage([uint32]$i)
  $out = Await ($folder.CreateFileAsync("p$i.png", [Windows.Storage.CreationCollisionOption]::ReplaceExisting)) ([Windows.Storage.StorageFile])
  $stream = Await ($out.OpenAsync([Windows.Storage.FileAccessMode]::ReadWrite)) ([Windows.Storage.Streams.IRandomAccessStream])
  $opt = New-Object Windows.Data.Pdf.PdfPageRenderOptions
  $opt.DestinationWidth = [uint32]([double]$page.Size.Width * $dpi / 96)
  AwaitAction ($page.RenderToStreamAsync($stream, $opt))
  $stream.Dispose(); $page.Dispose()
}
Write-Output $n
"""


def windows_render_pdf(path: Path, max_pages: int = 3, dpi: int = 200, timeout: int = 90) -> list[bytes]:
    """Render PDF pages with Windows' built-in PDF engine (Windows.Data.Pdf) - no native Python library."""
    if os.name != "nt":
        return []
    out_dir = Path(tempfile.mkdtemp())
    script = _temp_path(".ps1")
    script.write_text(_PS_RENDER, encoding="utf-8-sig")
    try:
        r = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                            "-File", str(script), str(Path(path).resolve()), str(out_dir), str(max_pages), str(dpi)],
                           capture_output=True, timeout=timeout,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if r.returncode != 0:
            return []
        return [p.read_bytes() for p in sorted(out_dir.glob("p*.png"), key=lambda p: int(p.stem[1:]))]
    except Exception:
        return []
    finally:
        try:
            script.unlink()
            shutil.rmtree(out_dir, ignore_errors=True)
        except OSError:
            pass


def _tesseract_exe() -> str | None:
    return shutil.which("tesseract") or next((p for p in (
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe") if Path(p).exists()), None)


def tesseract_ocr(img: bytes, timeout: int = 120) -> OcrResult:
    exe = _tesseract_exe()
    if not exe:
        return OcrResult(error="Tesseract not installed")
    png = _image_to_png_file(img)
    try:
        r = subprocess.run([exe, str(png), "stdout", "--psm", "6", "tsv"], capture_output=True, timeout=timeout,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if r.returncode != 0:
            return OcrResult(engine="tesseract", error=r.stderr.decode(errors="replace")[-400:])
        words = []
        for row in r.stdout.decode("utf-8", errors="replace").splitlines()[1:]:
            parts = row.split("\t")
            if len(parts) == 12 and parts[11].strip() and parts[10] != "-1":
                words.append(Word(parts[11], float(parts[6]), float(parts[7]), float(parts[8]), float(parts[9])))
        return OcrResult(text=_layout_text(words), words=words, engine="tesseract")
    except Exception as e:
        return OcrResult(engine="tesseract", error=str(e))
    finally:
        try:
            png.unlink()
        except OSError:
            pass


def _layout_text(words: list[Word]) -> str:
    """Rebuild reading order: group words into rows by vertical centre, keep column gaps."""
    if not words:
        return ""
    ws = sorted(words, key=lambda w: (w.y + w.h / 2, w.x))
    med_h = sorted(w.h for w in ws)[len(ws) // 2] or 10
    rows, cur, cur_y = [], [], None
    for w in ws:
        cy = w.y + w.h / 2
        if cur_y is None or abs(cy - cur_y) <= med_h * 0.6:
            cur.append(w)
            cur_y = cy if cur_y is None else (cur_y + cy) / 2
        else:
            rows.append(cur)
            cur, cur_y = [w], cy
    rows.append(cur)
    out = []
    for r in rows:
        r.sort(key=lambda w: w.x)
        line, last_end = "", None
        for w in r:
            gap = 1 if last_end is None else max(1, int((w.x - last_end) / (med_h * 0.5)))
            line += (" " * (3 if gap > 2 else 1) if line else "") + w.text
            last_end = w.x + w.w
        out.append(line)
    return "\n".join(out)


def ocr(img: bytes) -> OcrResult:
    """Best available engine; errors from every engine are kept for the user."""
    errors = []
    for fn in (windows_ocr, tesseract_ocr):
        r = fn(img)
        if r.text.strip():
            return r
        if r.error:
            errors.append(f"{fn.__name__}: {r.error}")
    return OcrResult(error=" | ".join(errors) or "No OCR engine produced text")
