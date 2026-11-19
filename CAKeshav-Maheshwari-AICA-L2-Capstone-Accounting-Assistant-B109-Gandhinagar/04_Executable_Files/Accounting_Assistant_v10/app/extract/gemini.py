"""Gemini extraction over plain HTTPS (no SDK: its dependencies include native modules that Smart App
Control blocks). Sends the redacted page image(s) and masked text, with the buying company as a hint.
If the answer fails GST arithmetic, Gemini is asked once to re-check against the document.

Gemini extracts fields only; ledgers, tax treatment and posting stay local.
"""
from __future__ import annotations

import base64
import json
import re
from datetime import datetime
from decimal import Decimal

import requests

from ..config import app_dir
from .parser import parse_date
from .schema import Invoice, Line, TaxRow

BASE = "https://generativelanguage.googleapis.com/v1beta"
_model_cache: dict[str, str] = {}

_N = {"type": "NUMBER"}
_S = {"type": "STRING"}
SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "document_type": {"type": "STRING", "enum": ["tax_invoice", "bill_of_supply", "credit_note", "debit_note",
                                                     "utility_bill", "receipt", "proforma", "other"]},
        "supplier_name": _S, "supplier_gstin": _S, "buyer_name": _S, "buyer_gstin": _S,
        "invoice_no": {"type": "STRING", "description": "invoice / credit note / debit note number"},
        "invoice_date": {"type": "STRING", "description": "DD-MM-YYYY"},
        "original_invoice_no": {"type": "STRING",
                                "description": "credit/debit note only: the invoice number it is issued against"},
        "place_of_supply_state_code": {"type": "STRING", "description": "2-digit GST state code"},
        "reverse_charge": {"type": "BOOLEAN"},
        "tax_summary": {"type": "ARRAY", "description": "one row per GST rate", "items": {"type": "OBJECT",
                        "properties": {"gst_rate": _N, "taxable": _N, "igst": _N, "cgst": _N, "sgst": _N,
                                       "cess": _N}, "required": ["gst_rate", "taxable"]}},
        "taxable_total": _N, "igst_total": _N, "cgst_total": _N, "sgst_total": _N, "cess_total": _N,
        "tcs": _N, "round_off": {"type": "NUMBER", "description": "negative if deducted"},
        "grand_total": {"type": "NUMBER", "description": "final amount payable on this invoice"},
        "lines": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
            "description": _S, "hsn": _S, "qty": _N, "uom": _S, "rate": _N, "taxable": _N, "gst_rate": _N}}},
        "notes": {"type": "STRING", "description": "anything unclear or illegible"},
    },
    "required": ["document_type", "supplier_gstin", "invoice_no", "invoice_date", "taxable_total", "grand_total"],
}


def _prompt(buyer_name: str, buyer_gstin: str) -> str:
    return (
        "You are reading an Indian purchase/expense document received by "
        f"{buyer_name or 'the buyer'}" + (f" (GSTIN {buyer_gstin})" if buyer_gstin else "") + ". "
        "Extract exactly what is printed.\n"
        "Rules:\n"
        "- supplier = the party issuing the document (usually top of page, near 'Tax Invoice'); the buyer is "
        "the company named above. Never swap them.\n"
        "- invoice_no exactly as printed (keep / - and leading zeros). In Tally-printed invoices the value sits "
        "in the box BELOW the label 'Invoice No.' / 'Dated'.\n"
        "- Amounts: plain numbers, no commas, Indian grouping like 2,36,140.00 means 236140.00. Ignore phone, "
        "account, PIN, HSN and invoice numbers when looking for amounts.\n"
        "- taxable_total is the value before GST; use the HSN/SAC tax summary table if present. tax_summary has "
        "one row per GST rate (gst_rate = total rate, e.g. 18 for CGST 9% + SGST 9%).\n"
        "- grand_total is the final invoice amount (after round-off and TCS), not 'amount after due date'.\n"
        "- round_off negative if shown as (-) or less.\n"
        "- For utility bills/receipts without GST, put the net payable in grand_total and taxable_total.\n"
        "- Text shown as [REDACTED] or black boxes was hidden on purpose; ignore it.\n"
        "- Use 0 or empty string for anything not printed; say what was unclear in notes."
    )


class GeminiError(Exception):
    pass


def _log_upload(kind: str, size: int, file_name: str, redactions: int, model: str) -> None:
    try:
        with open(app_dir() / "gemini_uploads.log", "a", encoding="utf-8") as f:
            f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S}\t{file_name}\t{kind}\t{size} bytes\t"
                    f"{redactions} items redacted\t{model}\n")
    except OSError:
        pass


def list_models(api_key: str, timeout: int = 20) -> list[str]:
    r = requests.get(f"{BASE}/models", headers={"x-goog-api-key": api_key}, timeout=timeout,
                     params={"pageSize": 200})
    if r.status_code != 200:
        raise GeminiError(f"Gemini HTTP {r.status_code}: {r.text[:300]}")
    out = []
    for m in r.json().get("models", []):
        if "generateContent" in m.get("supportedGenerationMethods", []):
            out.append(m["name"].split("/", 1)[-1])
    return out


def best_flash(models: list[str], lite: bool = False) -> str:
    """Newest stable 'flash' (or 'flash-lite') model by version number (no preview/tts/image variants)."""
    suffix = "-flash-lite" if lite else "-flash"

    def ver(name: str):
        m = re.match(r"gemini-(\d+)(?:\.(\d+))?" + re.escape(suffix) + "$", name)
        return (int(m.group(1)), int(m.group(2) or 0)) if m else None
    stable = sorted((v, n) for n in models if (v := ver(n)))
    if stable:
        return stable[-1][1]
    if lite:
        return best_flash(models, lite=False)
    flashes = [n for n in models if "flash" in n and "lite" not in n and "image" not in n and "tts" not in n]
    return sorted(flashes)[-1] if flashes else ""


def resolve_model(api_key: str, preferred: str) -> str:
    """Configured model if it exists, else the newest Flash model (cached per session)."""
    if re.match(r"gemini-(1|2)\.", preferred or ""):
        preferred = "auto"                     # 1.x / 2.x models are retired for new users
    key = f"{preferred}"
    if key in _model_cache:
        return _model_cache[key]
    try:
        models = list_models(api_key)
    except (GeminiError, requests.RequestException):
        return preferred or "gemini-flash-latest"
    if preferred in models:
        choice = preferred
    else:                                       # auto / auto-lite / withdrawn name -> newest of that kind
        choice = best_flash(models, lite=(preferred or "auto-lite") != "auto" and "lite" in (preferred or "lite"))
    _model_cache[key] = choice or preferred
    return _model_cache[key]


def _call(api_key: str, model: str, parts: list[dict], timeout: int) -> dict:
    body = {"contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"temperature": 0, "responseMimeType": "application/json",
                                 "responseSchema": SCHEMA}}
    try:
        r = requests.post(f"{BASE}/models/{model}:generateContent", json=body, timeout=timeout,
                          headers={"x-goog-api-key": api_key, "Content-Type": "application/json"})
    except requests.RequestException as e:
        raise GeminiError(f"Gemini not reachable: {e}") from e
    if r.status_code != 200:
        raise GeminiError(f"Gemini HTTP {r.status_code} ({model}): {r.text[:300]}")
    try:
        cand = r.json()["candidates"][0]
        txt = "".join(p.get("text", "") for p in cand["content"]["parts"])
        return json.loads(txt)
    except (KeyError, IndexError, ValueError) as e:
        raise GeminiError(f"Unexpected Gemini reply: {r.text[:300]}") from e


BANKING_MODULES = ("app.engine.bank", "app.ui.bank_page", "app.engine.entry")


def assert_not_banking() -> None:
    """Hard block: bank statements and banking entries are never sent to Gemini, whatever the settings say.
    Gemini is for invoice reading only."""
    import inspect
    frame = inspect.currentframe()
    while frame is not None:
        mod = frame.f_globals.get("__name__", "")
        if mod.startswith(BANKING_MODULES) or (mod.startswith("app.") and "bank" in mod.rsplit(".", 1)[-1]):
            raise GeminiError("Blocked: banking data is never sent to Gemini (invoices only)")
        frame = frame.f_back


def extract(api_key: str, model: str, *, text: str = "", images: list[bytes] | None = None,
            image_png: bytes = b"", file_name: str = "", redactions: int = 0, buyer_name: str = "",
            buyer_gstin: str = "", timeout: int = 120, check=None) -> Invoice:
    """check(inv) -> list of error strings; if any, Gemini is asked once to re-check them."""
    assert_not_banking()
    if not api_key:
        raise GeminiError("Gemini API key not set (Settings)")
    images = list(images or []) + ([image_png] if image_png else [])
    model = resolve_model(api_key, model)
    parts: list[dict] = [{"text": _prompt(buyer_name, buyer_gstin)}]
    for img in images[:3]:
        mime = "image/jpeg" if img[:3] == b"\xff\xd8\xff" else "image/png"
        parts.append({"inline_data": {"mime_type": mime, "data": base64.b64encode(img).decode()}})
    if text:
        parts.append({"text": "TEXT LAYER / OCR OF THE SAME DOCUMENT (may contain reading errors; the image "
                              "wins if they disagree):\n" + text[:30000]})
    _log_upload("image+text" if images else "text", sum(map(len, images)) + len(text), file_name, redactions, model)
    try:
        data = _call(api_key, model, parts, timeout)
    except GeminiError as e:
        if "HTTP 404" not in str(e):
            raise
        _model_cache.clear()                   # model withdrawn: pick the newest of the same kind, retry once
        model = best_flash(list_models(api_key), lite="lite" in model) or model
        _model_cache[""] = model
        data = _call(api_key, model, parts, timeout)
    inv = from_payload(data)
    if check:
        errs = check(inv)
        if errs:
            parts2 = parts + [{"text": "Your previous answer was:\n" + json.dumps(data) +
                               "\nIt fails these checks:\n- " + "\n- ".join(errs) +
                               "\nLook at the document again and return corrected values. If the document "
                               "itself is inconsistent, keep the printed values and explain in notes."}]
            data2 = _call(api_key, model, parts2, timeout)
            inv2 = from_payload(data2)
            if len(check(inv2)) < len(errs):
                inv2.notes = (inv2.notes + " (corrected on re-check)").strip()
                inv = inv2
    if check and "lite" in model and check(inv):
        try:
            strong = best_flash(list_models(api_key), lite=False)
            if strong:
                data3 = _call(api_key, strong, parts, timeout)
                inv3 = from_payload(data3)
                if len(check(inv3)) < len(check(inv)):
                    inv3.notes = (inv3.notes + f" (re-read with {strong} after {model} failed checks)").strip()
                    inv3.model = strong
                    return inv3
        except (GeminiError, requests.RequestException):
            pass
    inv.model = model
    return inv


def from_payload(d: dict) -> Invoice:
    D = lambda v: Decimal(str(v or 0)).quantize(Decimal("0.01"))
    inv = Invoice(source="gemini",
                  supplier_name=(d.get("supplier_name") or "").strip(),
                  supplier_gstin=(d.get("supplier_gstin") or "").upper().replace(" ", ""),
                  buyer_gstin=(d.get("buyer_gstin") or "").upper().replace(" ", ""),
                  invoice_no=(d.get("invoice_no") or "").strip(),
                  invoice_date=parse_date(d.get("invoice_date") or ""),
                  place_of_supply=(d.get("place_of_supply_state_code") or "")[:2],
                  reverse_charge=bool(d.get("reverse_charge")),
                  taxable_total=D(d.get("taxable_total")), igst_total=D(d.get("igst_total")),
                  cgst_total=D(d.get("cgst_total")), sgst_total=D(d.get("sgst_total")),
                  cess_total=D(d.get("cess_total")), tcs=D(d.get("tcs")), round_off=D(d.get("round_off")),
                  grand_total=D(d.get("grand_total")))
    inv.document_type = d.get("document_type") or ""
    inv.original_invoice_no = (d.get("original_invoice_no") or "").strip()
    inv.notes = d.get("notes") or ""
    inv.supplier_pan = inv.supplier_gstin[2:12] if len(inv.supplier_gstin) == 15 else ""
    for l in d.get("lines") or []:
        inv.lines.append(Line(l.get("description", "") or "", str(l.get("hsn", "") or ""), D(l.get("qty")),
                              l.get("uom", "") or "", D(l.get("rate")), D(l.get("taxable")), D(l.get("gst_rate"))))
    for t in d.get("tax_summary") or []:
        if D(t.get("gst_rate")) or D(t.get("taxable")):
            inv.taxes.append(TaxRow(D(t.get("gst_rate")), D(t.get("taxable")), D(t.get("igst")), D(t.get("cgst")),
                                    D(t.get("sgst")), D(t.get("cess"))))
    # totals missing but summary present -> sum it
    if inv.taxes:
        if not inv.taxable_total:
            inv.taxable_total = sum((t.taxable for t in inv.taxes), Decimal(0))
        for head in ("igst", "cgst", "sgst"):
            if not getattr(inv, f"{head}_total"):
                setattr(inv, f"{head}_total", sum((getattr(t, head) for t in inv.taxes), Decimal(0)))
    elif inv.lines:
        slabs: dict[Decimal, TaxRow] = {}
        for l in inv.lines:
            if l.gst_rate:
                slabs.setdefault(l.gst_rate, TaxRow(rate=l.gst_rate)).taxable += l.taxable
        if len(slabs) == 1:
            r = next(iter(slabs.values()))
            r.taxable = inv.taxable_total or r.taxable
            r.igst, r.cgst, r.sgst = inv.igst_total, inv.cgst_total, inv.sgst_total
        inv.taxes = sorted(slabs.values(), key=lambda r: r.rate)
    inv.hsn_codes = [l.hsn for l in inv.lines if l.hsn]
    inv.field_confidence = {k: 0.85 for k in ("supplier_name", "supplier_gstin", "buyer_gstin", "invoice_no",
                                             "invoice_date", "grand_total", "taxable_total", "cgst_total",
                                             "sgst_total", "igst_total") if getattr(inv, k)}
    return inv
