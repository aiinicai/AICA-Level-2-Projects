"""Local PII detection and redaction (no network, no external models).

Design:
* Regex detectors for Indian identifiers (PAN, TAN, GSTIN, Aadhaar, IFSC, bank
  account numbers, DIN/notice references), contact data (e-mail, phone, PIN code
  in context) and case-specific terms (assessee / party names supplied by user).
* `redact()` replaces every hit with a stable placeholder, e.g. [PAN_1].
* `verify_redaction()` re-scans the redacted text with every detector; any
  residual hit means the redaction FAILED and the AI gateway must block.
* Fail-closed: any exception during redaction is reported as failure.

Limitations (also in README): free-text postal addresses and personal names that
the user has not entered as redaction terms cannot be detected reliably by
regex. The user must review the preview before approving transmission.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# Order matters: more specific patterns first (GSTIN contains a PAN).
DETECTORS: list[tuple[str, re.Pattern]] = [
    ("GSTIN", re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b")),
    ("PAN", re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")),
    ("TAN", re.compile(r"\b[A-Z]{4}\d{5}[A-Z]\b")),
    ("IFSC", re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b")),
    ("DIN", re.compile(r"\b(?:ITBA|CBDT|DIN)[/:\s-]*[A-Z0-9][A-Z0-9/().\-]{8,}", re.I)),
    ("EMAIL", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("AADHAAR", re.compile(r"(?<!\d)(?<!\d[,.])[2-9]\d{3}[ -]?\d{4}[ -]?\d{4}(?!\d)(?![,.]\d)")),
    ("PHONE", re.compile(r"(?<!\d)(?<!\d[,.])(?:\+91[\s-]?|0)?[6-9]\d{9}(?!\d)(?![,.]\d)")),
    ("ACCOUNT_NO", re.compile(r"(?i)(?:a/?c|account)\s*(?:no\.?|number|#)?\s*[:\-]?\s*[X*\d][X*\d\s-]{5,20}\d")),
    ("LONG_NUMBER", re.compile(r"(?<!\d)(?<!\d[,.])\d{9,18}(?!\d)(?![,.]\d)")),
    ("PINCODE", re.compile(r"(?i)\bpin\s*(?:code)?\s*[:\-]?\s*\d{3}\s?\d{3}\b")),
    ("DOB", re.compile(r"(?i)\b(?:dob|date of birth)\s*[:\-]?\s*\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}")),
]


@dataclass
class RedactionResult:
    redacted_text: str
    counts: dict[str, int] = field(default_factory=dict)
    ok: bool = True
    residual: dict[str, int] = field(default_factory=dict)
    error: str | None = None
    restore: dict[str, str] = field(default_factory=dict)  # placeholder → original; kept on this computer only

    @property
    def summary(self) -> dict:
        return {"counts": self.counts, "ok": self.ok, "residual": self.residual, "error": self.error}


def _term_patterns(terms: list[str]) -> list[re.Pattern]:
    pats = []
    for t in sorted({t.strip() for t in terms if t and len(t.strip()) >= 3}, key=len, reverse=True):
        # tolerate variable whitespace inside multi-word names
        body = r"\s+".join(re.escape(p) for p in t.split())
        pats.append(re.compile(rf"(?i)(?<![A-Za-z0-9]){body}(?![A-Za-z0-9])"))
    return pats


def detect(text: str, terms: list[str] | None = None) -> dict[str, int]:
    counts: dict[str, int] = {}
    for label, pat in DETECTORS:
        n = len(pat.findall(text))
        if n:
            counts[label] = n
    for pat in _term_patterns(terms or []):
        n = len(pat.findall(text))
        if n:
            counts["PARTY_NAME"] = counts.get("PARTY_NAME", 0) + n
    return counts


def redact(text: str, terms: list[str] | None = None) -> RedactionResult:
    try:
        mapping: dict[tuple[str, str], str] = {}
        restore: dict[str, str] = {}
        counters: dict[str, int] = {}
        counts: dict[str, int] = {}

        def make_sub(label: str):
            def _sub(m: re.Match) -> str:
                key = (label, m.group(0).upper())
                if key not in mapping:
                    counters[label] = counters.get(label, 0) + 1
                    mapping[key] = f"[{label}_{counters[label]}]"
                    restore[mapping[key]] = m.group(0)
                counts[label] = counts.get(label, 0) + 1
                return mapping[key]

            return _sub

        out = text
        # names first so a name containing digits-like tokens is handled as a whole
        for pat in _term_patterns(terms or []):
            out = pat.sub(make_sub("PARTY_NAME"), out)
        for label, pat in DETECTORS:
            out = pat.sub(make_sub(label), out)
        residual = verify_redaction(out, terms)
        return RedactionResult(out, counts, ok=not residual, residual=residual, restore=restore)
    except Exception as exc:  # fail closed
        return RedactionResult("", {}, ok=False, error=f"redaction error: {type(exc).__name__}")


_PLACEHOLDER = re.compile(r"\[[A-Z_]+_\d+\]")


def verify_redaction(redacted: str, terms: list[str] | None = None) -> dict[str, int]:
    """Return residual detections (empty dict == clean)."""
    stripped = _PLACEHOLDER.sub(" ", redacted)
    return detect(stripped, terms)


_LOG_PATTERNS = [p for _, p in DETECTORS if _ not in {"DIN"}]


def scrub_for_log(text: str) -> str:
    out = text
    for p in _LOG_PATTERNS:
        out = p.sub("[REDACTED]", out)
    return out


def mask_pan(pan: str | None) -> str:
    if not pan or len(pan) < 4:
        return "NOT PROVIDED"
    return pan[:2] + "X" * (len(pan) - 3) + pan[-1]
