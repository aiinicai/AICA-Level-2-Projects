"""OCR back-ends (all offline by default).

Order of preference (auto):
  1. RapidOCR — PaddleOCR PP-OCRv4 models on ONNX Runtime (pip-installable, bundled models)
  2. Tesseract — if the tesseract executable is installed
  3. Local vision LLM via Ollama (e.g. llama3.2-vision, qwen2.5vl, gemma3) — slow but works on any CPU/ARM64
  4. Claude vision — only when cloud AI is allowed for the entity AND confirmed for the document
Each back-end returns OCR lines: {"text", "conf", "bbox": [x0, y0, x1, y1] in pixel coords}.
"""
from __future__ import annotations

import base64
import io
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

from PIL import Image


@dataclass
class OcrLine:
    text: str
    conf: float
    bbox: tuple[float, float, float, float]


@lru_cache(maxsize=1)
def _rapid():
    try:
        from rapidocr_onnxruntime import RapidOCR  # type: ignore
        return RapidOCR()
    except Exception:
        return None


def rapidocr_available() -> bool:
    try:
        import rapidocr_onnxruntime  # noqa: F401  type: ignore
        return True
    except Exception:
        return False


def tesseract_path() -> Optional[str]:
    p = shutil.which("tesseract")
    if p:
        return p
    for cand in (r"C:\Program Files\Tesseract-OCR\tesseract.exe", r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"):
        try:
            import os
            if os.path.exists(cand):
                return cand
        except Exception:
            pass
    return None


def ocr_rapid(img: Image.Image) -> list[OcrLine]:
    import numpy as np  # type: ignore
    eng = _rapid()
    if eng is None:
        raise RuntimeError("RapidOCR not available")
    arr = np.array(img.convert("RGB"))[:, :, ::-1]
    try:
        # word-box mode makes RapidOCR re-insert inter-word spaces for Latin text (CTC gap analysis)
        result, _ = eng(arr, return_word_box=True)
    except TypeError:  # older versions
        result, _ = eng(arr)
    out = []
    for item in result or []:
        box, text, score = item[0], item[1], item[2]
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        out.append(OcrLine(text, float(score), (min(xs), min(ys), max(xs), max(ys))))
    return out


def ocr_tesseract(img: Image.Image) -> list[OcrLine]:
    exe = tesseract_path()
    if not exe:
        raise RuntimeError("Tesseract not installed")
    with tempfile.TemporaryDirectory() as td:
        ip = f"{td}/page.png"
        img.save(ip)
        proc = subprocess.run([exe, ip, "stdout", "-l", "eng", "--psm", "3", "tsv"], capture_output=True, text=True, timeout=180)
    lines: dict[tuple, list] = {}
    for row in proc.stdout.splitlines()[1:]:
        parts = row.split("\t")
        if len(parts) < 12 or not parts[11].strip():
            continue
        key = (parts[2], parts[3], parts[4])  # block, par, line
        x, y, w, h, conf = int(parts[6]), int(parts[7]), int(parts[8]), int(parts[9]), float(parts[10])
        lines.setdefault(key, []).append((x, y, x + w, y + h, parts[11], conf))
    out = []
    for words in lines.values():
        text = " ".join(w[4] for w in words)
        conf = sum(w[5] for w in words) / len(words) / 100.0
        out.append(OcrLine(text, conf, (min(w[0] for w in words), min(w[1] for w in words), max(w[2] for w in words),
                                        max(w[3] for w in words))))
    return out


def ocr_vision_llm(img: Image.Image, llm) -> list[OcrLine]:
    """Transcribe with a vision-capable local model (no bounding boxes)."""
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG")
    text = llm.transcribe_image(base64.b64encode(buf.getvalue()).decode())
    return [OcrLine(t, 0.6, (0, i * 20, img.width, i * 20 + 18)) for i, t in enumerate(text.splitlines()) if t.strip()]


def lines_to_text(lines: list[OcrLine]) -> str:
    """Reading order: group by vertical position, then left-to-right."""
    if not lines:
        return ""
    heights = sorted((l.bbox[3] - l.bbox[1]) for l in lines)
    med_h = heights[len(heights) // 2] or 10
    rows: list[list[OcrLine]] = []
    for ln in sorted(lines, key=lambda l: ((l.bbox[1] + l.bbox[3]) / 2, l.bbox[0])):
        cy = (ln.bbox[1] + ln.bbox[3]) / 2
        if rows:
            last = rows[-1]
            lcy = sum((x.bbox[1] + x.bbox[3]) / 2 for x in last) / len(last)
            if abs(cy - lcy) < med_h * 0.6:
                last.append(ln)
                continue
        rows.append([ln])
    return "\n".join(" ".join(x.text for x in sorted(r, key=lambda l: l.bbox[0])) for r in rows)


def available_engines(llm=None) -> list[str]:
    eng = []
    if rapidocr_available():
        eng.append("rapidocr")
    if tesseract_path():
        eng.append("tesseract")
    if llm is not None and getattr(llm, "vision_model", None):
        eng.append("vision-llm")
    return eng


def run_ocr(img: Image.Image, preferred: str = "auto", llm=None) -> tuple[list[OcrLine], str]:
    order = ["rapidocr", "tesseract", "vision-llm"] if preferred == "auto" else [preferred]
    errors = []
    for eng in order:
        try:
            if eng == "rapidocr" and rapidocr_available():
                return ocr_rapid(img), "RapidOCR (PP-OCRv4, ONNX Runtime)"
            if eng == "tesseract" and tesseract_path():
                return ocr_tesseract(img), "Tesseract OCR"
            if eng == "vision-llm" and llm is not None and getattr(llm, "vision_model", None):
                return ocr_vision_llm(img, llm), f"Vision LLM ({llm.vision_model})"
        except Exception as exc:  # pragma: no cover - depends on local install
            errors.append(f"{eng}: {exc}")
    raise RuntimeError("No OCR engine available for scanned pages. " + "; ".join(errors) +
                       " Install RapidOCR (x64 Python), Tesseract, or configure a local vision model.")
