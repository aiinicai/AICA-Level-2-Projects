"""One-line verdict per invoice for the queue: is it ready to post, and if not, what's the single
most important thing to fix."""
from __future__ import annotations

from dataclasses import dataclass

from ..extract.schema import Invoice
from . import rules
from .masters import Masters

ORDER = {"blocked": 0, "attention": 1, "ready": 2, "posted": 3, "exception": 4}


@dataclass
class Verdict:
    state: str            # ready | attention | blocked | posted | exception
    reason: str           # short, shown on the chip
    detail: str = ""


def invoice_of(row) -> Invoice:
    e = row.extraction or {}
    inv = Invoice.from_json({k: v for k, v in e.items() if not k.startswith("_")})
    inv.raw_text = e.get("_text", "")
    return inv


def assess(session, company, m: Masters, row) -> tuple[Verdict, "rules.Suggestion | None"]:
    if row.status == "posted":
        return Verdict("posted", "Posted"), None
    if row.status == "exception":
        return Verdict("exception", "Set aside"), None
    v = row.validation or {}
    errors = [i for i in v.get("issues", []) if i["level"] == "error"]
    if not (row.extraction or {}).get("invoice_no") and not (row.extraction or {}).get("grand_total"):
        return Verdict("blocked", "Couldn't read", errors[0]["message"] if errors else ""), None
    inv = invoice_of(row)
    sug = rules.suggest(session, company, m, inv)
    dup = next((f for f in sug.flags if f.startswith("DUPLICATE?")), "")
    if dup:
        return Verdict("blocked", "Possible duplicate", dup), sug
    if errors:
        e = errors[0]
        short = {"grand_total": "Total doesn't add up", "taxable_total": "Check taxable value",
                 "buyer_gstin": "Billed to another GSTIN", "supplier_gstin": "Supplier GSTIN invalid",
                 "invoice_no": "Invoice no. missing", "invoice_date": "Check date", "igst_total": "IGST vs CGST/SGST",
                 "cgst_total": "IGST vs CGST/SGST", "sgst_total": "CGST ≠ SGST", "round_off": "Round-off too big",
                 "file": "Couldn't read"}.get(e["field"], "Needs checking")
        return Verdict("blocked", short, e["message"]), sug
    missing = [l for l in sug.voucher.lines if not l.ledger or l.ledger not in m.ledgers]
    if missing:
        what = "party ledger" if any(l.kind == "party" for l in missing) else "ledger"
        return Verdict("attention", f"Pick {what}", "; ".join(sug.flags)), sug
    if not sug.voucher.balanced:
        return Verdict("attention", "Dr ≠ Cr", ""), sug
    amber = [l for l in sug.voucher.lines if l.confidence != "green"]
    warns = [i for i in v.get("issues", []) if i["level"] == "warn"]
    if warns:
        return Verdict("attention", "Check: " + warns[0]["field"].replace("_", " "), warns[0]["message"]), sug
    if amber:
        return Verdict("attention", "Confirm ledger", amber[0].note), sug
    return Verdict("ready", "Ready"), sug
