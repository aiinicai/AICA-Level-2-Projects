"""Parses TallyPrime responses.

Success is decided ONLY from Tally's own counters (CREATED / ALTERED / ERRORS /
EXCEPTIONS / LINEERROR), never from the HTTP status code.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from typing import Any

_INVALID_CHAR_REF = re.compile(r"&#(?:x0*[0-8bBcCeEfF]|x0*1[0-9a-fA-F]|0*[0-8]|0*1[124-9]|0*2[0-9]|0*3[01]);")
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
_COUNTERS = ("CREATED", "ALTERED", "DELETED", "LASTVCHID", "COMBINED", "IGNORED", "ERRORS", "CANCELLED",
             "EXCEPTIONS")


def sanitise_xml(text: str) -> str:
    """Tally sometimes emits control characters (e.g. &#4;) that are illegal in XML 1.0."""
    return _CONTROL.sub("", _INVALID_CHAR_REF.sub("", text)).strip()


def parse_xml(text: str) -> ET.Element | None:
    try:
        return ET.fromstring(sanitise_xml(text))
    except ET.ParseError:
        return None


@dataclass
class TallyImportResult:
    status: str                      # SUCCESS | PARTIAL | FAILED
    message: str
    created: int = 0
    altered: int = 0
    deleted: int = 0
    ignored: int = 0
    errors: int = 0
    cancelled: int = 0
    exceptions: int = 0
    last_voucher_id: str | None = None
    line_errors: list[str] = field(default_factory=list)
    raw: str = ""

    @property
    def success(self) -> bool:
        return self.status == "SUCCESS"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _int(root: ET.Element, tag: str) -> int:
    el = root.find(f".//{tag}") if root.tag != tag else root
    try:
        return int((el.text or "0").strip()) if el is not None else 0
    except ValueError:
        return 0


def parse_import_response(text: str, expected: int) -> TallyImportResult:
    raw = text or ""
    root = parse_xml(raw)
    if root is None:
        snippet = re.sub(r"<[^>]+>", " ", raw)
        snippet = re.sub(r"\s+", " ", snippet).strip()[:300]
        return TallyImportResult("FAILED", f"Tally returned an unreadable response: {snippet or '(empty)'}",
                                 raw=raw)

    line_errors = [re.sub(r"\s+", " ", e.text or "").strip() for e in root.iter("LINEERROR") if (e.text or "").strip()]
    has_counters = any(root.find(f".//{t}") is not None or root.tag == t for t in ("CREATED", "ERRORS"))
    if not has_counters:
        text_content = re.sub(r"\s+", " ", "".join(root.itertext())).strip()
        message = "; ".join(line_errors) or text_content or "Tally did not report any result."
        return TallyImportResult("FAILED", f"Unexpected response from Tally: {message}", line_errors=line_errors,
                                 raw=raw)

    r = TallyImportResult(
        status="FAILED", message="", raw=raw, line_errors=line_errors,
        created=_int(root, "CREATED"), altered=_int(root, "ALTERED"), deleted=_int(root, "DELETED"),
        ignored=_int(root, "IGNORED"), errors=_int(root, "ERRORS"), cancelled=_int(root, "CANCELLED"),
        exceptions=_int(root, "EXCEPTIONS"),
    )
    lv = root.find(".//LASTVCHID")
    r.last_voucher_id = (lv.text or "").strip() or None if lv is not None else None
    done = r.created + r.altered

    if r.errors or r.exceptions or line_errors:
        r.status = "PARTIAL" if done else "FAILED"
        detail = "; ".join(line_errors) or f"{r.errors} error(s), {r.exceptions} exception(s) reported by Tally."
        r.message = (f"{done} of {expected} voucher(s) accepted. " if done else "") + detail
    elif expected and done >= expected:
        r.status = "SUCCESS"
        parts = []
        if r.created:
            parts.append(f"{r.created} voucher{'s' if r.created != 1 else ''} created")
        if r.altered:
            parts.append(f"{r.altered} altered")
        r.message = ", ".join(parts) + " successfully."
    elif r.ignored and not done:
        r.status = "FAILED"
        r.message = f"Tally ignored {r.ignored} voucher(s) (often a duplicate or locked period)."
    elif done:
        r.status = "PARTIAL"
        r.message = f"Only {done} of {expected} voucher(s) were accepted by Tally."
    else:
        r.status = "FAILED"
        r.message = "Tally did not create any voucher."
    return r
