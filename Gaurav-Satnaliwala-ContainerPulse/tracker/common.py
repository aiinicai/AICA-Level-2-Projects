from __future__ import annotations
import re
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

@dataclass
class TrackingResult:
    container_number: str
    shipping_line: str
    success: bool
    carrier_website_opened: bool = False
    tracking_search_accepted: bool = False
    access_restriction: str | None = None
    latest_eta: str | None = None
    status: str | None = None
    current_location: str | None = None
    vessel: str | None = None
    last_tracking_event: str | None = None
    source_url: str | None = None
    checked_at: str = ""
    raw_excerpt: str | None = None
    error: str | None = None

    def to_dict(self):
        if not self.checked_at:
            self.checked_at = datetime.now().isoformat(timespec="seconds")
        return asdict(self)

DATE_PATTERNS = [
    r"\b(?:ETA|Estimated(?: date and time of)? arrival|Estimated arrival)\s*[:\-]?\s*([0-3]?\d[\s\-/](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s\-/]\d{2,4})",
    r"\b(?:ETA|Estimated(?: date and time of)? arrival|Estimated arrival)\s*[:\-]?\s*((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+[0-3]?\d,?\s+\d{4})",
    r"\b(?:ETA|Estimated(?: date and time of)? arrival|Estimated arrival)\s*[:\-]?\s*(\d{4}-\d{2}-\d{2})",
]

def extract_eta(text: str) -> str | None:
    flat = re.sub(r"\s+", " ", text or " ")
    for p in DATE_PATTERNS:
        m = re.search(p, flat, flags=re.I)
        if m:
            return m.group(1).strip()
    return None

def extract_labeled_value(text: str, labels: list[str]) -> str | None:
    lines = [re.sub(r"\s+", " ", x).strip() for x in (text or "").splitlines() if x.strip()]
    for i, line in enumerate(lines):
        low = line.lower()
        for label in labels:
            ll = label.lower()
            if low == ll and i + 1 < len(lines):
                return lines[i+1][:180]
            if low.startswith(ll + ":"):
                return line.split(":",1)[1].strip()[:180]
    return None

def debug_save(container: str, carrier: str, text: str) -> None:
    d = Path("tracking_debug")
    d.mkdir(exist_ok=True)
    (d / f"{carrier.lower()}_{container}.txt").write_text(text or "", encoding="utf-8")

def logger_for(carrier: str) -> logging.Logger:
    return logging.getLogger(f"containerpulse.{carrier.lower()}")

def detect_access_block(text: str) -> str | None:
    low = (text or "").lower()
    markers = {
        "captcha": "CAPTCHA challenge displayed",
        "verify you are human": "human-verification challenge displayed",
        "access denied": "access denied by carrier website",
        "temporarily blocked": "request temporarily blocked by carrier website",
    }
    return next((reason for marker, reason in markers.items() if marker in low), None)
