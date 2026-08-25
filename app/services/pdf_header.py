"""Client letterhead drawn on every generated PDF report."""

from typing import Dict, List

from reportlab.lib import colors
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import SimpleDocTemplate

HEADER_BAR = 7.0
MIN_TOP_MARGIN = 20.0
CLIENT_TOP_MARGIN = 64.0


def get_report_client() -> Dict[str, str]:
    try:
        from app.core.database import get_active_client_slug
        from app.services.client_store import get_active_client

        client = get_active_client(get_active_client_slug())
    except Exception:
        client = None
    if not client:
        return {"name": "", "address": "", "gstin": ""}
    return {
        "name": (client.get("name") or "").strip(),
        "address": (client.get("address") or "").strip(),
        "gstin": (client.get("gstin") or "").strip().upper(),
    }


def header_top_margin() -> float:
    info = get_report_client()
    if info["name"] or info["address"] or info["gstin"]:
        return CLIENT_TOP_MARGIN
    return MIN_TOP_MARGIN


def pdf_document(buffer, pagesize, left=22, right=22, bottom=36, title=""):
    kwargs = {
        "pagesize": pagesize,
        "leftMargin": left,
        "rightMargin": right,
        "topMargin": header_top_margin(),
        "bottomMargin": bottom,
    }
    if title:
        kwargs["title"] = title
    return SimpleDocTemplate(buffer, **kwargs)


def _wrap_text(text: str, font_name: str, font_size: float, max_width: float, max_lines: int = 2) -> List[str]:
    normalized = " ".join((text or "").replace("\r", "\n").replace("\n", ", ").split())
    if not normalized:
        return []
    words = normalized.split(" ")
    lines: List[str] = []
    current = ""
    for word in words:
        trial = word if not current else f"{current} {word}"
        if stringWidth(trial, font_name, font_size) <= max_width:
            current = trial
            continue
        if current:
            lines.append(current)
        current = word
        if len(lines) >= max_lines:
            break
    if current and len(lines) < max_lines:
        lines.append(current)
    elif current and lines:
        last = lines[-1]
        while last and stringWidth(last + "…", font_name, font_size) > max_width:
            last = last[:-1]
        lines[-1] = f"{last.rstrip()}…" if last else "…"
    return lines[:max_lines]


def _fit_text(text: str, font_name: str, font_size: float, max_width: float) -> str:
    if stringWidth(text, font_name, font_size) <= max_width:
        return text
    trimmed = text
    while trimmed and stringWidth(trimmed + "…", font_name, font_size) > max_width:
        trimmed = trimmed[:-1]
    return f"{trimmed.rstrip()}…" if trimmed else ""


def draw_client_header(canvas, page_width: float, page_height: float, font: str = "Helvetica", font_bold: str = "Helvetica-Bold") -> None:
    info = get_report_client()
    canvas.saveState()
    canvas.setFillColor(colors.HexColor("#166534"))
    canvas.rect(0, page_height - HEADER_BAR, page_width, HEADER_BAR, fill=1, stroke=0)

    name = info["name"]
    address = info["address"]
    gstin = info["gstin"]
    if not (name or address or gstin):
        canvas.restoreState()
        return

    left = 28
    right = page_width - 28
    usable = right - left
    y = page_height - HEADER_BAR - 16

    gstin_text = f"GSTIN: {gstin}" if gstin else ""
    gstin_width = stringWidth(gstin_text, font, 8) if gstin_text else 0
    name_max = usable - gstin_width - 12 if gstin_text else usable

    if name:
        canvas.setFillColor(colors.HexColor("#14532D"))
        canvas.setFont(font_bold, 13)
        canvas.drawString(left, y, _fit_text(name, font_bold, 13, name_max))

    if gstin_text:
        canvas.setFillColor(colors.HexColor("#3F5B4A"))
        canvas.setFont(font, 8)
        canvas.drawRightString(right, y + 1, gstin_text)

    y -= 13
    if address:
        canvas.setFillColor(colors.HexColor("#475569"))
        canvas.setFont(font, 8)
        for line in _wrap_text(address, font, 8, usable, 2):
            canvas.drawString(left, y, line)
            y -= 11

    canvas.setStrokeColor(colors.HexColor("#BBD5C3"))
    canvas.setLineWidth(0.6)
    canvas.line(left, page_height - CLIENT_TOP_MARGIN + 10, right, page_height - CLIENT_TOP_MARGIN + 10)
    canvas.restoreState()
