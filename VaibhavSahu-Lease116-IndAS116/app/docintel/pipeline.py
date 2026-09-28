"""Agreement-reader pipeline: file -> pages -> CV/OCR -> rules (+ LLM) -> verified fields,
judgment flags and a proposed lease draft for human review.

Nothing produced here is booked automatically. The output is a proposal; the user
confirms each field (and answers the judgment questions) before a lease is created.
"""
from __future__ import annotations

import hashlib
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Optional

from ..engine.calendar_utils import add_months, prev_day
from .ingest import LoadedDocument, load_document
from .rules import extract_rules
from .schema import ESSENTIAL, FIELDS, FIELD_MAP
from .textnum import normalise
from .verify import FieldResult, merge_field


@dataclass
class ExtractionResult:
    document: dict
    fields: dict
    flags: list
    missing_essentials: list
    questions: list
    draft: dict
    engine: dict
    warnings: list
    timings: dict

    def to_dict(self) -> dict:
        return asdict(self)


def _boxes_for_quote(page, quote: str) -> list:
    """Normalised bounding boxes of the page lines that make up the quote."""
    if not quote or page is None or not page.lines:
        return []
    qn = normalise(quote)
    q_tokens = set(re.findall(r"[a-z0-9]+", qn))
    out = []
    for ln in page.lines:
        tn = normalise(ln["text"])
        if len(tn) < 4:
            continue
        if tn in qn:
            out.append(ln["bbox"])
            continue
        toks = set(re.findall(r"[a-z0-9]+", tn))
        if toks and len(toks & q_tokens) / len(toks) >= 0.8 and len(toks) >= 3:
            out.append(ln["bbox"])
    return out[:20]


def _judgment_flags(f: dict, doc: LoadedDocument) -> tuple[list, list]:
    flags, questions = [], []
    v = lambda k: f[k].value if k in f and f[k].value not in (None, "") else None  # noqa: E731
    tenure = v("tenure_months")
    lock = v("lock_in_months")
    if tenure is not None and int(tenure) <= 12:
        flags.append({"code": "SHORT_TERM_CANDIDATE", "title": "Term of 12 months or less",
                      "detail": "Possible short-term lease. For renewable 11-month leave-and-licence arrangements, determine the "
                                "enforceable period considering renewal history and broader economics (B34; IFRIC agenda decision "
                                "Nov 2019) before applying the exemption.", "ref": "Ind AS 116.5–8, B34"})
    if lock and tenure and int(lock) < int(tenure):
        flags.append({"code": "LOCK_IN_TERM", "title": "Lock-in shorter than contractual term",
                      "detail": f"Lessee may exit after {lock} months. Lease term = lock-in + periods the lessee is reasonably "
                                "certain not to terminate (18(b)).", "ref": "Ind AS 116.18–19, B37"})
        questions.append({"key": "rc_continue_after_lock_in", "question": f"Is the lessee reasonably certain NOT to terminate after "
                          f"the {lock}-month lock-in (i.e. to continue for the full {tenure} months)?",
                          "guidance": "Consider significant leasehold improvements, relocation costs, importance of the location, "
                                      "termination penalties and past practice (B37).", "ref": "Ind AS 116.18(b), B37"})
    who = v("renewal_at_option_of")
    if v("renewal_option"):
        if who == "MUTUAL":
            flags.append({"code": "RENEWAL_MUTUAL", "title": "Renewal by mutual consent",
                          "detail": "Renewal requires lessor agreement — not a unilateral lessee option; generally excluded from the "
                                    "lease term unless the renewal period is enforceable (B34).", "ref": "Ind AS 116.18, B34"})
        else:
            flags.append({"code": "RENEWAL_OPTION", "title": "Lessee renewal / extension option",
                          "detail": "Assess whether the lessee is reasonably certain to exercise the renewal option.",
                          "ref": "Ind AS 116.18(a), B37"})
            questions.append({"key": "rc_renewal", "question": "Is the lessee reasonably certain to exercise the renewal option?",
                              "guidance": "Economic incentive: leasehold improvements, below-market renewal rent, relocation cost (B37).",
                              "ref": "Ind AS 116.18(a)"})
    if v("lessor_can_terminate_without_cause"):
        flags.append({"code": "BOTH_CAN_TERMINATE", "title": "Lessor may also terminate without cause",
                      "detail": "If both parties can terminate without more than an insignificant penalty, the lease is not "
                                "enforceable beyond that point (B34) — consider broader economics.", "ref": "Ind AS 116.B34"})
    if v("deposit_amount"):
        if v("deposit_interest_free") in (True, None):
            flags.append({"code": "DEPOSIT_IND_AS_109", "title": "Interest-free security deposit",
                          "detail": "Measure the deposit at fair value (Ind AS 109); the difference from cash paid is ordinarily "
                                    "treated as prepaid rent and added to the ROU asset. A market interest rate is required.",
                          "ref": "Ind AS 109; Ind AS 116.24(b)"})
            questions.append({"key": "deposit_market_rate", "question": "Market interest rate for fair-valuing the security deposit (% p.a.)?",
                              "guidance": "Typically the lessee's borrowing rate for a similar tenor.", "ref": "Ind AS 109.B5.1.1"})
    if v("rent_free_days"):
        flags.append({"code": "RENT_FREE", "title": "Rent-free / fit-out period",
                      "detail": "Include nil payments in the schedule; ROU depreciation and interest start at commencement "
                                "(when the premises are made available), not at rent commencement.", "ref": "Ind AS 116 App. A; 22"})
    if v("escalation_pct"):
        flags.append({"code": "ESCALATION", "title": "Fixed escalations",
                      "detail": "Contractual fixed escalations are fixed lease payments and included in the liability.",
                      "ref": "Ind AS 116.27(a)"})
    if v("cam_amount"):
        flags.append({"code": "NON_LEASE", "title": "Maintenance / CAM charges",
                      "detail": "Non-lease component — separate from the lease liability unless the practical expedient is "
                                "elected for the class (para 15).", "ref": "Ind AS 116.12–15"})
    if v("variable_rent"):
        flags.append({"code": "VARIABLE_RENT", "title": "Variable (revenue-share) rent",
                      "detail": "Sales-based payments are excluded from the liability and expensed when incurred; any minimum "
                                "guaranteed rent is fixed (in-substance fixed) and included.", "ref": "Ind AS 116.27–28, 38(b), B42"})
    if v("restoration_obligation"):
        flags.append({"code": "RESTORATION", "title": "Restoration / reinstatement clause",
                      "detail": "Estimate the cost of removing fit-outs / reinstating the premises and recognise a provision if "
                                "material (Ind AS 37); the PV is added to the ROU asset (24(d)).", "ref": "Ind AS 116.24(d)"})
        questions.append({"key": "restoration_estimate", "question": "Estimated restoration cost at the end of the lease (if material)?",
                          "guidance": "Obtain an engineer's / facility estimate; 'reasonable wear and tear excepted' may reduce it.",
                          "ref": "Ind AS 37.36"})
    if v("purchase_option_price"):
        flags.append({"code": "PURCHASE_OPTION", "title": "Purchase option",
                      "detail": "Include the exercise price only if reasonably certain; if so, depreciate the ROU asset over the "
                                "asset's useful life (32).", "ref": "Ind AS 116.27(d), 32"})
        questions.append({"key": "rc_purchase", "question": "Is the lessee reasonably certain to exercise the purchase option?",
                          "guidance": "Compare the option price with the expected fair value at the exercise date.", "ref": "Ind AS 116.27(d)"})
    if v("substitution_right"):
        flags.append({"code": "SUBSTITUTION", "title": "Lessor substitution right",
                      "detail": "A substitution right is substantive only if the supplier has the practical ability and would "
                                "benefit economically (B14–B19). If substantive, the contract may not contain a lease.",
                      "ref": "Ind AS 116.B14–B19"})
    if v("stamp_duty_borne_by") == "LESSEE" or v("brokerage_amount"):
        flags.append({"code": "IDC", "title": "Initial direct costs",
                      "detail": "Stamp duty / registration and brokerage borne by the lessee are incremental costs of obtaining the "
                                "lease — capitalise in the ROU asset.", "ref": "Ind AS 116.24(c)"})
    if f.get("commencement_date") and f["commencement_date"].status == "DERIVED":
        flags.append({"code": "COMMENCEMENT_DERIVED", "title": "Commencement date not explicit",
                      "detail": "The commencement date is the date the lessor makes the asset available for use (App. A). "
                                "Confirm the handover date.", "ref": "Ind AS 116 App. A"})
    cur = v("currency")
    if cur and cur != "INR":
        flags.append({"code": "FOREIGN_CURRENCY", "title": f"Lease denominated in {cur}",
                      "detail": "Liability is a monetary item retranslated at closing rates; ROU asset stays at historical rate.",
                      "ref": "Ind AS 21.23"})
    if v("gst_treatment"):
        flags.append({"code": "GST", "title": "GST on rent",
                      "detail": "Creditable GST is excluded from lease payments; non-creditable GST requires a policy decision "
                                "(IFRS IC 2021 discussion — no blanket conclusion).", "ref": "Entity policy"})
    for p in doc.pages:
        if p.vision and p.vision.stamps:
            flags.append({"code": "STAMP_DETECTED", "title": f"Stamp / seal detected on page {p.number}",
                          "detail": "Computer vision found coloured seal/stamp marks — indicative of an executed copy (verify).",
                          "ref": "Audit evidence", "severity": "INFO"})
        if p.vision and p.vision.blurry:
            flags.append({"code": "LOW_QUALITY", "title": f"Page {p.number} is blurred",
                          "detail": "Obtain a clearer scan; OCR-derived values on this page need closer review.", "ref": "",
                          "severity": "INFO"})
        if p.page_type == "ESTAMP":
            flags.append({"code": "ESTAMP_PAGE", "title": f"e-Stamp certificate on page {p.number}",
                          "detail": "Stamp duty details read from the e-stamp certificate.", "ref": "", "severity": "INFO"})
    questions.append({"key": "discount_rate", "question": "Incremental borrowing rate (IBR) for this lease (% p.a.) and its source?",
                      "guidance": "Reflect the lease term, currency, security and the lessee's credit; document methodology and approval.",
                      "ref": "Ind AS 116.26"})
    questions.append({"key": "related_party", "question": "Is the lessor a related party (Ind AS 24)?", "guidance": "", "ref": "Ind AS 24"})
    return flags, questions


def build_draft(f: dict) -> dict:
    """Map confirmed/proposed fields to the lease-creation structure (all values remain editable)."""
    g = lambda k: f[k].value if k in f and f[k].value not in (None, "") else None  # noqa: E731
    draft: dict[str, Any] = {"assumptions": []}
    comm = g("commencement_date")
    tenure = g("tenure_months")
    expiry = g("expiry_date")
    if comm and not expiry and tenure:
        expiry = prev_day(add_months(date.fromisoformat(comm), int(tenure))).isoformat()
    draft.update({
        "lessor_name": g("lessor_name"), "lessee_name": g("lessee_name"), "contract_date": g("agreement_date"),
        "description": (g("asset_description") or "")[:250], "asset_class": g("asset_category") or "Buildings",
        "location": (g("asset_address") or "")[:200], "commencement_date": comm, "contract_end": expiry,
        "currency": g("currency") or "INR", "area_sqft": g("area_sqft"),
    })
    freq = {"MONTHLY": 1, "QUARTERLY": 3, "HALF_YEARLY": 6, "ANNUAL": 12}.get(g("rent_frequency") or "MONTHLY", 1)
    due = g("payment_due_day")
    pt = {"amount": g("rent_amount"), "frequency_months": freq, "timing": g("payment_timing") or "ADVANCE",
          "due_day": due, "alignment": "CALENDAR" if (due and freq == 1) else "ANNIVERSARY",
          "start_date": comm, "end_date": expiry, "escalations": [], "rent_free": [], "non_lease_amount": g("cam_amount") or "0"}
    if not g("payment_timing"):
        draft["assumptions"].append("Payment timing not stated — assumed in advance; confirm.")
    if g("escalation_pct"):
        pt["escalations"].append({"value": g("escalation_pct"), "every_months": g("escalation_every_months") or 12,
                                  "compounding": (g("escalation_basis") or "COMPOUND") == "COMPOUND"})
        if not g("escalation_basis"):
            draft["assumptions"].append("Escalation basis not stated — assumed on last paid rent (compounding); confirm.")
        if not g("escalation_every_months"):
            draft["assumptions"].append("Escalation interval not stated — assumed every 12 months; confirm.")
    rf = g("rent_free_days")
    if rf and comm:
        start = date.fromisoformat(comm)
        end = start + timedelta(days=int(rf) - 1)
        pt["rent_free"].append({"start": start.isoformat(), "end": end.isoformat()})
    draft["payment_terms"] = pt
    options = []
    lock = g("lock_in_months")
    if lock and comm and tenure and int(lock) < int(tenure):
        options.append({"kind": "TERMINATION", "holder": "LESSEE",
                        "exercise_date": prev_day(add_months(date.fromisoformat(comm), int(lock))).isoformat(),
                        "reasonably_certain": None, "description": f"Lessee may terminate after the {lock}-month lock-in"
                        + (f" with {g('lessee_termination_notice_months')} months' notice" if g("lessee_termination_notice_months") else ""),
                        "price": f.get("termination_penalty").value if f.get("termination_penalty") else None})
    if g("renewal_option") and expiry:
        months = g("renewal_months") or tenure
        if months:
            options.append({"kind": "EXTENSION", "holder": "LESSEE" if g("renewal_at_option_of") == "LESSEE" else "LESSOR",
                            "exercise_date": (date.fromisoformat(expiry) + timedelta(days=1)).isoformat(),
                            "extension_end_date": prev_day(add_months(date.fromisoformat(expiry) + timedelta(days=1), int(months))).isoformat(),
                            "reasonably_certain": None if g("renewal_at_option_of") == "LESSEE" else False,
                            "renewal_escalation_pct": g("renewal_escalation_pct"),
                            "description": "Renewal " + ("at lessee's option" if g("renewal_at_option_of") == "LESSEE" else
                                                         "by mutual consent (not a lessee option)")})
    if g("purchase_option_price") and expiry:
        options.append({"kind": "PURCHASE", "holder": "LESSEE", "exercise_date": expiry, "price": g("purchase_option_price"),
                        "reasonably_certain": None, "description": "Purchase option"})
    draft["options"] = options
    if g("deposit_amount") and comm:
        draft["deposit"] = {"amount": g("deposit_amount"), "payment_date": comm,
                            "refund_date": (date.fromisoformat(expiry) + timedelta(days=1)).isoformat() if expiry else None,
                            "interest_free": g("deposit_interest_free") is not False, "market_rate_pct": None}
    idc = []
    if g("stamp_duty_amount") and g("stamp_duty_borne_by") in ("LESSEE", None):
        idc.append({"description": "Stamp duty (e-stamp)", "amount": g("stamp_duty_amount"), "date": comm})
    if g("brokerage_amount"):
        idc.append({"description": "Brokerage", "amount": g("brokerage_amount"), "date": comm})
    draft["idc"] = idc
    draft["restoration_obligation"] = bool(g("restoration_obligation"))
    draft["variable_rent"] = g("variable_rent")
    draft["purchase_option_price"] = g("purchase_option_price")
    draft["residual_value_guarantee"] = g("residual_value_guarantee")
    return draft


def run_pipeline(data: bytes, filename: str, llm=None, provider_name: str = "", ocr_pref: str = "auto",
                 force_ocr: bool = False, ocr_llm=None) -> tuple[ExtractionResult, LoadedDocument]:
    t0 = time.time()
    doc = load_document(data, filename, llm=ocr_llm, ocr_pref=ocr_pref, force_ocr=force_ocr)
    t1 = time.time()
    pages = [(p.number, p.text) for p in doc.pages]
    rule_c = extract_rules(pages)
    t2 = time.time()
    llm_out: dict = {}
    warnings = list(doc.warnings)
    llm_error = ""
    if llm is not None:
        try:
            llm_out = llm.extract(pages) or {}
        except Exception as exc:
            llm_error = f"{type(exc).__name__}: {exc}"
            warnings.append(f"AI reader ({provider_name}) failed — rules-only result shown. {llm_error}")
    t3 = time.time()
    fields = {}
    page_map = {p.number: p for p in doc.pages}
    for fd in FIELDS:
        fr = merge_field(fd.key, rule_c.get(fd.key, []), llm_out.get(fd.key), pages, provider_name)
        if fr.page and fr.quote:
            fr.boxes = _boxes_for_quote(page_map.get(fr.page), fr.quote)
        fields[fd.key] = fr
    flags, questions = _judgment_flags(fields, doc)
    missing = [k for k in ESSENTIAL if fields[k].value in (None, "")]
    draft = build_draft(fields)
    sha = hashlib.sha256(data).hexdigest()
    res = ExtractionResult(
        document={"filename": filename, "kind": doc.kind, "pages": len(doc.pages), "sha256": sha,
                  "ocr_used": doc.ocr_used, "ocr_engine": doc.ocr_engine,
                  "page_info": [{"number": p.number, "source": p.source, "page_type": p.page_type, "ocr_engine": p.ocr_engine,
                                 "has_preview": p.preview_png is not None, "chars": len(p.text or ""),
                                 "vision": (asdict(p.vision) if p.vision else None)} for p in doc.pages]},
        fields={k: asdict(v) for k, v in fields.items()},
        flags=flags, missing_essentials=missing, questions=questions, draft=draft,
        engine={"rules": True, "llm": provider_name or None, "llm_error": llm_error or None,
                "llm_model": getattr(llm, "model", None) if llm else None},
        warnings=warnings,
        timings={"load_ocr_s": round(t1 - t0, 2), "rules_s": round(t2 - t1, 2), "llm_s": round(t3 - t2, 2),
                 "total_s": round(time.time() - t0, 2)},
    )
    return res, doc
