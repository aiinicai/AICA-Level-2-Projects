"""
rules_engine.py
----------------
The offline, rule-based "intelligence" of LC Analyser. No external AI/API
calls are made - every summary and verdict below is produced by explicit
field-mapping tables and UCP 600 derived checklist logic.

Public entry point: build_clause_points(fields, lc_type) -> List[ClausePoint]
"""

from __future__ import annotations

import datetime
import re
from typing import Dict, List, Optional, Tuple

from models import (
    ClausePoint,
    SECTION_MAIN_SUMMARY,
    SECTION_GOODS,
    SECTION_DOCUMENTS,
    SECTION_CHARGES,
    SUB_LR_BL,
    SUB_COO,
    SUB_INVOICE_PACKING,
    SUB_BOE,
    SUB_CERT_INSPECTION,
    SUB_INSURANCE,
    SUB_INTIMATION,
    SUB_OTHER,
    VERDICT_OPTIONS,
)
from lc_parser import RawField, split_into_items

CORRECT, AMEND, CLARIFY, INFO = VERDICT_OPTIONS


# ---------------------------------------------------------------------------
# SWIFT tag -> (header, section, subsection) map
# ---------------------------------------------------------------------------

FIELD_MAP: Dict[str, Tuple[str, str, Optional[str]]] = {
    "20": ("Documentary Credit Number", SECTION_MAIN_SUMMARY, None),
    "21": ("Related Reference", SECTION_MAIN_SUMMARY, None),
    "23": ("Reference to Pre-Advice", SECTION_MAIN_SUMMARY, None),
    "27": ("Sequence of Total", SECTION_MAIN_SUMMARY, None),
    "31C": ("Date of Issue", SECTION_MAIN_SUMMARY, None),
    "31D": ("Date and Place of Expiry", SECTION_MAIN_SUMMARY, None),
    "32B": ("Currency Code, Amount", SECTION_MAIN_SUMMARY, None),
    "39A": ("Percentage Credit Amount Tolerance", SECTION_MAIN_SUMMARY, None),
    "39B": ("Maximum Credit Amount", SECTION_MAIN_SUMMARY, None),
    "39C": ("Additional Amounts Covered", SECTION_MAIN_SUMMARY, None),
    "40A": ("Form of Documentary Credit", SECTION_MAIN_SUMMARY, None),
    "40E": ("Applicable Rules", SECTION_MAIN_SUMMARY, None),
    "41A": ("Available With...By...", SECTION_MAIN_SUMMARY, None),
    "41D": ("Available With...By...", SECTION_MAIN_SUMMARY, None),
    "42A": ("Drawee", SECTION_MAIN_SUMMARY, None),
    "42C": ("Drafts at...", SECTION_MAIN_SUMMARY, None),
    "42M": ("Mixed Payment Details", SECTION_MAIN_SUMMARY, None),
    "42P": ("Deferred Payment Details", SECTION_MAIN_SUMMARY, None),
    "43P": ("Partial Shipments", SECTION_MAIN_SUMMARY, None),
    "43T": ("Transshipment", SECTION_MAIN_SUMMARY, None),
    "44A": ("Place of Taking in Charge / Dispatch", SECTION_MAIN_SUMMARY, None),
    "44B": ("Place of Final Destination", SECTION_MAIN_SUMMARY, None),
    "44C": ("Latest Date of Shipment", SECTION_MAIN_SUMMARY, None),
    "44D": ("Shipment Period", SECTION_MAIN_SUMMARY, None),
    "44E": ("Port of Loading / Airport of Departure", SECTION_MAIN_SUMMARY, None),
    "44F": ("Port of Discharge / Airport of Destination", SECTION_MAIN_SUMMARY, None),
    "45A": ("Description of Goods and/or Services", SECTION_GOODS, None),
    "45B": ("Description of Goods and/or Services", SECTION_GOODS, None),
    "46A": ("Documents Required", SECTION_DOCUMENTS, None),  # split into items
    "46B": ("Documents Required", SECTION_DOCUMENTS, None),
    "47A": ("Additional Conditions", SECTION_DOCUMENTS, None),  # split into items
    "47B": ("Additional Conditions", SECTION_DOCUMENTS, None),
    "48": ("Period for Presentation", SECTION_MAIN_SUMMARY, None),
    "49": ("Confirmation Instructions", SECTION_CHARGES, None),
    "50": ("Applicant", SECTION_MAIN_SUMMARY, None),
    "51A": ("Applicant Bank", SECTION_MAIN_SUMMARY, None),
    "51D": ("Applicant Bank", SECTION_MAIN_SUMMARY, None),
    "52A": ("Issuing Bank", SECTION_MAIN_SUMMARY, None),
    "52D": ("Issuing Bank", SECTION_MAIN_SUMMARY, None),
    "53A": ("Reimbursing Bank", SECTION_CHARGES, None),
    "53D": ("Reimbursing Bank", SECTION_CHARGES, None),
    "56A": ("Intermediary Bank", SECTION_CHARGES, None),
    "56D": ("Intermediary Bank", SECTION_CHARGES, None),
    "57A": ("Advise Through Bank", SECTION_CHARGES, None),
    "57D": ("Advise Through Bank", SECTION_CHARGES, None),
    "58A": ("Beneficiary's Bank", SECTION_CHARGES, None),
    "58D": ("Beneficiary's Bank", SECTION_CHARGES, None),
    "59": ("Beneficiary", SECTION_MAIN_SUMMARY, None),
    "71B": ("Charges", SECTION_CHARGES, None),
    "71D": ("Charges", SECTION_CHARGES, None),
    "72": ("Sender to Receiver Information", SECTION_CHARGES, None),
    "72Z": ("Sender to Receiver Information", SECTION_CHARGES, None),
    "73": ("Sender to Receiver Information", SECTION_CHARGES, None),
    "77J": ("Additional Conditions", SECTION_DOCUMENTS, None),
    "78": ("Instructions to Paying/Accepting/Negotiating Bank", SECTION_CHARGES, None),
}


def resolve_field(tag: str, header_hint: str) -> Tuple[str, str, Optional[str]]:
    if tag in FIELD_MAP:
        return FIELD_MAP[tag]
    if header_hint:
        return (header_hint, _classify_freeform(header_hint), None)
    return (f"Field {tag}", SECTION_MAIN_SUMMARY, None)


# ---------------------------------------------------------------------------
# Keyword classification for document / condition items and free-form
# (non-SWIFT) draft-LC paragraphs
# ---------------------------------------------------------------------------

_SUB_KEYWORDS = [
    # Order matters: more specific/exclusive categories are checked first so
    # a generic word like "invoice" appearing inside e.g. an insurance
    # clause ("...110% of CIF invoice value...") doesn't steal the match.
    (SUB_LR_BL, [
        "bills? of lading", "b/l", "airway bill", "air waybill", "awb",
        "lorry receipt", "l/r", "transport document", "multimodal",
        "combined transport", "cmr", "truck receipt", "on board",
    ]),
    (SUB_COO, [
        "certificate of origin", "gsp certificate", "form a", "\\bcoo\\b",
        "chamber of commerce",
    ]),
    (SUB_BOE, [
        "bill of exchange", "draft drawn", "draft at", "drafts at",
        "drawn on", "usance bill",
    ]),
    (SUB_CERT_INSPECTION, [
        "inspection certificate", "inspection report", "survey report",
        "fumigation", "phytosanitary", "health certificate",
        "quality certificate", "analysis certificate", "test certificate",
        "\\bsgs\\b", "quality inspection", "pre-shipment inspection",
    ]),
    (SUB_INSURANCE, [
        "insurance polic", "insurance certificate", "insurance covering",
        "insurance to be covered", "insurance covered", "\\bcif\\b", "\\bcip\\b",
        "marine insurance", "marine cover", "\\binsurance\\b",
    ]),
    (SUB_INTIMATION, [
        "notify", "intimation", "courier", "by fax", "by e-mail", "by email",
        "to be sent to (the )?applicant", "advis(e|ed) (the )?applicant",
        "within.*days of shipment", "copy of.*to be sent",
    ]),
    (SUB_INVOICE_PACKING, [
        "commercial invoice", "invoice in", "packing list", "weight list",
        "weight note", "\\binvoice\\b",
    ]),
]


def _classify_doc_item(item_text: str) -> str:
    lower = item_text.lower()
    for subsection, keywords in _SUB_KEYWORDS:
        for kw in keywords:
            if re.search(kw, lower):
                return subsection
    return SUB_OTHER


def _classify_freeform(text: str) -> str:
    """Used only for the fallback (non-SWIFT-tag) draft-LC parser to decide
    which of the four main sections a whole paragraph belongs to."""
    lower = text.lower()
    doc_kw = ["document", "invoice", "bill of lading", "certificate", "packing list",
              "bill of exchange", "insurance", "inspection"]
    goods_kw = ["description of goods", "goods", "merchandise", "commodity", "services"]
    charge_kw = ["charge", "commission", "reimbursement", "confirmation"]
    if any(k in lower for k in charge_kw):
        return SECTION_CHARGES
    if any(k in lower for k in doc_kw):
        return SECTION_DOCUMENTS
    if any(k in lower for k in goods_kw):
        return SECTION_GOODS
    return SECTION_MAIN_SUMMARY


# ---------------------------------------------------------------------------
# Date / numeric helpers
# ---------------------------------------------------------------------------

def _parse_date(text: str):
    """Best-effort date extraction. Returns a datetime.date or None."""
    if not text:
        return None
    try:
        from dateutil import parser as dtparser
    except ImportError:
        return None

    # Try a few common explicit patterns first (fast, unambiguous)
    patterns = [
        r"\b(\d{4}-\d{2}-\d{2})\b",
        r"\b(\d{1,2}[-/ ][A-Za-z]{3,9}[-/ ]\d{2,4})\b",
        r"\b(\d{2}[/-]\d{2}[/-]\d{2,4})\b",
        r"\b(\d{6})\b",  # YYMMDD, common raw SWIFT format
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            candidate = m.group(1)
            try:
                if re.fullmatch(r"\d{6}", candidate):
                    yy, mm, dd = candidate[0:2], candidate[2:4], candidate[4:6]
                    year = 2000 + int(yy) if int(yy) < 80 else 1900 + int(yy)
                    return dtparser.parse(f"{year}-{mm}-{dd}").date()
                return dtparser.parse(candidate, dayfirst=True, fuzzy=True).date()
            except Exception:
                continue
    try:
        return dtparser.parse(text, dayfirst=True, fuzzy=True).date()
    except Exception:
        return None


def _extract_presentation_days(field48_value: str) -> int:
    if field48_value:
        # Common labelled form: "Days:           21" (bank SWIFT reprints
        # print field 48 as a "Days:" / "Narrative:" pair, so the number
        # isn't immediately followed by the word "DAY").
        m = re.search(r"DAYS?\s*:\s*(\d{1,3})", field48_value, re.I)
        if m:
            return int(m.group(1))
        # Prose form: "21 DAYS AFTER THE DATE OF SHIPMENT..."
        m = re.search(r"(\d{1,3})\s*DAY", field48_value.upper())
        if m:
            return int(m.group(1))
    return 21  # UCP 600 Article 14(c) default


def _fmt_ddmmyyyy(d: datetime.date) -> str:
    """The user requires every date shown in the summary to be DD/MM/YYYY."""
    return d.strftime("%d/%m/%Y")


def _yymmdd_to_date(digits: str):
    yy, mm, dd = digits[0:2], digits[2:4], digits[4:6]
    year = 2000 + int(yy) if int(yy) < 80 else 1900 + int(yy)
    try:
        return datetime.date(year, int(mm), int(dd))
    except ValueError:
        return None


# Bank SWIFT-message reprints print date fields twice: the raw 6-digit
# SWIFT date immediately followed by a spelled-out form, e.g.
# "250903          2025 Sep 03" (both mean 3 September 2025). This
# collapses that redundant pair down to a single DD/MM/YYYY date.
_SWIFT_DUAL_DATE_RE = re.compile(r"\b(\d{6})\s+(\d{4})\s+([A-Za-z]{3})\s+(\d{1,2})\b")

# Dates written DD.MM.YYYY in free-flowing clause text (e.g. an invoice or
# contract date quoted inside "Documents Required"/"Additional Conditions")
# just need their separator swapped to DD/MM/YYYY.
_DOT_DATE_RE = re.compile(r"\b(\d{2})\.(\d{2})\.(\d{4})\b")


def normalize_dates_in_text(text: str) -> str:
    """Rewrites every date pattern this tool recognises in free text to
    DD/MM/YYYY, per the requirement that dates in the summary always use
    that format. Only touches substrings that unambiguously look like a
    date - reference numbers etc. are left untouched."""
    if not text:
        return text

    # A value that is *entirely* a bare 6-digit SWIFT date (e.g. a field
    # like "Date of Issue" whose bank didn't also print the spelled-out
    # companion date) - safe to convert because it requires the WHOLE
    # (trimmed) value to be exactly 6 digits, not just a substring, so an
    # unrelated 6-digit reference/amount elsewhere in a sentence is left
    # alone.
    # A bare 6-digit SWIFT date at the very START of the (trimmed) value -
    # either alone (e.g. a "Date of Issue" field with no spelled-out
    # companion date) or followed by trailing descriptive text (e.g. a
    # "Date and Place of Expiry" field printed as "261130 IN INDIA"). Only
    # the leading date token is touched, so unrelated trailing text and any
    # unrelated 6-digit number elsewhere in a longer sentence are left alone.
    stripped = text.strip()
    lead = re.match(r"^(\d{6})(\s+.*)?$", stripped, re.S)
    if lead:
        d = _yymmdd_to_date(lead.group(1))
        if d:
            rest = lead.group(2) or ""
            return _fmt_ddmmyyyy(d) + rest

    def _dual_repl(m: "re.Match") -> str:
        d = _yymmdd_to_date(m.group(1))
        return _fmt_ddmmyyyy(d) if d else m.group(0)

    text = _SWIFT_DUAL_DATE_RE.sub(_dual_repl, text)

    def _dot_repl(m: "re.Match") -> str:
        dd, mm, yyyy = m.group(1), m.group(2), m.group(3)
        try:
            datetime.date(int(yyyy), int(mm), int(dd))
        except ValueError:
            return m.group(0)
        return f"{dd}/{mm}/{yyyy}"

    text = _DOT_DATE_RE.sub(_dot_repl, text)
    return text


# ---------------------------------------------------------------------------
# Per-field rule-based analysis
# ---------------------------------------------------------------------------

def _analyze_field(tag: str, value: str, field_by_tag: Dict[str, RawField]) -> Tuple[str, str]:
    raw_v = (value or "").strip()
    upper = raw_v.upper()  # keyword checks below run against the untouched text
    v = normalize_dates_in_text(raw_v)  # display copy used in messages, with dates as DD/MM/YYYY

    if tag == "20":
        if not v:
            return AMEND, "Documentary Credit Number is missing; the LC cannot be treated as complete without this reference."
        return CORRECT, f"Documentary Credit Number is stated as '{v}'."

    if tag == "40A":
        if "REVOCABLE" in upper and "IRREVOCABLE" not in upper:
            return AMEND, ("Credit is stated as REVOCABLE. Under UCP 600 Article 3, a credit is "
                            "irrevocable even if there is no indication to that effect, but an "
                            "explicitly revocable credit gives the beneficiary very weak protection "
                            "and should normally be amended to IRREVOCABLE.")
        if "IRREVOCABLE" in upper:
            return CORRECT, "Credit is correctly stated as Irrevocable."
        return CLARIFY, "Form of documentary credit is not clearly stated; confirm it is Irrevocable."

    if tag == "40E":
        if "UCP" not in upper:
            return CLARIFY, "Applicable rules are not clearly stated; confirm the credit is subject to UCP 600 (ICC Publication No. 600) or the applicable revision."
        return CORRECT, f"Applicable rules stated: {v}."

    if tag == "31D":
        return INFO, f"Expiry date/place stated as: {v}. Cross-checked against shipment/presentation timelines separately below."

    if tag == "32B":
        if not v or re.search(r"\b0(\.0+)?\b", v.replace(",", "")) and not re.search(r"[1-9]", v):
            return AMEND, "Credit amount appears to be missing or zero; this is a mandatory field."
        return CORRECT, f"Currency and amount stated as: {v}."

    if tag in ("39A", "39B", "39C"):
        return INFO, f"Tolerance / additional amount clause: {v}."

    if tag in ("41A", "41D"):
        if not v:
            return CLARIFY, "Availability (with which bank, by what method - payment/acceptance/negotiation/deferred payment) is not clearly stated."
        return CORRECT, f"Credit is available as: {v}."

    if tag == "42C":
        drafts_required = bool(v)
        avail = (field_by_tag.get("41A") or field_by_tag.get("41D"))
        avail_value = (avail.value.upper() if avail else "")
        if drafts_required and avail_value and "NEGOTIATION" not in avail_value and "ACCEPTANCE" not in avail_value and "MIXED" not in avail_value:
            return CLARIFY, f"Drafts at '{v}' are called for; confirm this is consistent with the stated availability ({avail_value or 'not stated'})."
        if v:
            return INFO, f"Draft tenor: {v}."
        return INFO, "No drafts called for."

    if tag == "43P":
        if "NOT ALLOWED" in upper or "PROHIBITED" in upper:
            return INFO, "Partial shipments are NOT allowed - each shipment must fully match the LC quantity/value in one lot."
        if "ALLOWED" in upper:
            return INFO, "Partial shipments are allowed."
        return CLARIFY, "Partial shipment permissibility is not clearly stated (UCP 600 Art. 31 treats silence as 'allowed')."

    if tag == "43T":
        if "NOT ALLOWED" in upper or "PROHIBITED" in upper:
            return INFO, "Transshipment is NOT allowed."
        if "ALLOWED" in upper:
            return INFO, "Transshipment is allowed."
        return CLARIFY, "Transshipment permissibility is not clearly stated (UCP 600 Art. 19-21 treats silence as 'allowed' for combined/multimodal, sea, and air transport documents)."

    if tag in ("44C", "44D"):
        if not v:
            return AMEND, "Latest date of shipment / shipment period is not specified. This is a mandatory field and must be included."
        return CORRECT, f"Shipment timeline stated as: {v}."

    if tag == "45A" or tag == "45B":
        if len(v) < 15:
            return CLARIFY, "Description of goods/services appears very brief; ensure it aligns with the commercial invoice/underlying contract, without adding excessive extra detail that could itself cause discrepancies (UCP 600 Art. 18(c))."
        return CORRECT, "Description of goods/services is stated; verify it matches the commercial invoice exactly (UCP 600 Art. 18(c))."

    if tag == "48":
        days = _extract_presentation_days(v)
        return INFO, f"Period for presentation: {days} day(s) after shipment date{' (UCP 600 Art. 14(c) default, field not stated)' if not v else ''}."

    if tag == "49":
        if "CONFIRM" in upper and "WITHOUT" not in upper and "MAY ADD" not in upper:
            return INFO, "Credit calls for confirmation by the advising/another bank."
        if "WITHOUT" in upper:
            return INFO, "Credit is issued without confirmation instructions."
        if "MAY ADD" in upper:
            return INFO, "Advising bank may add its confirmation at beneficiary's request."
        return CLARIFY, "Confirmation instructions are not clearly stated."

    if tag in ("50", "59"):
        who = "Applicant" if tag == "50" else "Beneficiary"
        if len(v) < 10:
            return CLARIFY, f"{who} details appear incomplete; confirm full name and address are correctly captured."
        return CORRECT, f"{who} details are stated."

    if tag in ("71B", "71D"):
        if not v:
            return CLARIFY, "Charges clause is not specified; confirm how banking charges are allocated between applicant and beneficiary (UCP 600 Art. 37(c))."
        if "BENEFICIARY" in upper and ("OUTSIDE" in upper or "ISSUING BANK" in upper):
            return CORRECT, f"Charges clause: {v}."
        return INFO, f"Charges clause: {v}."

    if tag in ("52A", "52D"):
        if v:
            return CORRECT, f"Issuing Bank: {v}."
        return CLARIFY, "Issuing Bank details not clearly stated."

    if not v:
        return INFO, "Field present but no value could be extracted; please verify manually against the original LC."

    return INFO, f"{v}"


def _analyze_doc_item(item_text: str, subsection: str) -> Tuple[str, str]:
    lower = item_text.lower()

    if subsection == SUB_LR_BL:
        if "lading" in lower or "b/l" in lower:
            if "clean" not in lower and "on board" not in lower:
                return CLARIFY, "Bill of Lading requirement does not explicitly call for a 'Clean On Board' transport document; recommend this be made explicit to avoid a discrepancy at negotiation."
            return CORRECT, "Bill of Lading / transport document requirement appears complete."
        return INFO, "Transport document condition noted."

    if subsection == SUB_COO:
        authority_named = "issued by" in lower or "chamber" in lower
        if authority_named:
            return CORRECT, "Certificate of Origin requirement noted; issuing authority is specified."
        return CLARIFY, "Certificate of Origin is required but the issuing authority (e.g. Chamber of Commerce) is not clearly specified."

    if subsection == SUB_INVOICE_PACKING:
        return INFO, "Invoice / packing list requirement noted; ensure the number of copies and any legalisation/attestation requirement is complied with."

    if subsection == SUB_BOE:
        return INFO, "Bill of Exchange (draft) requirement noted; confirm tenor matches field 42C and drawee matches field 42A/D."

    if subsection == SUB_CERT_INSPECTION:
        return CLARIFY, "Inspection/certification document required; confirm the issuing agency is named and acceptable to the beneficiary, as unnamed 'independent inspection agency' clauses are a frequent source of discrepancy/dispute."

    if subsection == SUB_INSURANCE:
        covered_by_buyer = (
            "covered by the applicant" in lower or "covered by applicant" in lower
            or ("insurance" in lower and "applicant" in lower and "cover" in lower)
        )
        if covered_by_buyer:
            return INFO, "Insurance is stated to be arranged/covered by the applicant (buyer), not the beneficiary - typical under CPT/FOB/CFR-type Incoterms; confirm this matches the agreed sales terms."
        if "110%" in lower or "110 %" in lower or "110 per cent" in lower:
            return CORRECT, "Insurance coverage of 110% of CIF/CIP value is called for, consistent with UCP 600 Art. 28(f)(ii) market practice."
        return CLARIFY, "Insurance requirement noted; confirm coverage percentage (market norm is 110% of CIF/CIP value, where insurance is the beneficiary's responsibility) and risks covered are acceptable."

    if subsection == SUB_INTIMATION:
        return INFO, "Intimation / communication requirement noted; ensure the beneficiary can comply within the stated timeline (e.g. days from shipment)."

    return INFO, "Additional condition noted; review for practical compliance."


# ---------------------------------------------------------------------------
# Cross-field checks (need the whole set of fields at once)
# ---------------------------------------------------------------------------

def _cross_field_checks(field_by_tag: Dict[str, RawField], next_sl: int) -> List[ClausePoint]:
    results: List[ClausePoint] = []

    expiry_field = field_by_tag.get("31D")
    shipment_field = field_by_tag.get("44C") or field_by_tag.get("44D")
    presentation_field = field_by_tag.get("48")

    expiry_date = _parse_date(expiry_field.value) if expiry_field else None
    shipment_date = _parse_date(shipment_field.value) if shipment_field else None
    presentation_days = _extract_presentation_days(presentation_field.value if presentation_field else "")

    if expiry_date and shipment_date:
        if expiry_date < shipment_date:
            verdict, note = AMEND, (
                f"Expiry date ({_fmt_ddmmyyyy(expiry_date)}) is earlier than the latest date of "
                f"shipment ({_fmt_ddmmyyyy(shipment_date)}). Documents could never be presented "
                f"within the credit's validity; the expiry date and/or shipment date needs to "
                f"be amended (UCP 600 Art. 6(d))."
            )
        else:
            from datetime import timedelta
            latest_presentation = shipment_date + timedelta(days=presentation_days)
            if latest_presentation > expiry_date:
                verdict, note = AMEND, (
                    f"Presentation period ({presentation_days} days from shipment = "
                    f"{_fmt_ddmmyyyy(latest_presentation)}) runs beyond the credit's expiry date "
                    f"({_fmt_ddmmyyyy(expiry_date)}). The period for presentation and/or expiry "
                    f"date needs to be reconciled per UCP 600 Art. 14(c)."
                )
            else:
                verdict, note = CORRECT, (
                    f"Shipment date ({_fmt_ddmmyyyy(shipment_date)}), presentation period "
                    f"({presentation_days} days) and expiry date ({_fmt_ddmmyyyy(expiry_date)}) "
                    f"are consistent with each other."
                )
    else:
        verdict, note = CLARIFY, (
            "Could not automatically reconcile expiry date, latest shipment date and "
            "presentation period from the extracted text - please verify these three "
            "dates manually against UCP 600 Art. 6(d) and Art. 14(c)."
        )

    results.append(ClausePoint(
        sl_no=next_sl,
        point_no="Cross-check",
        header="Shipment / Presentation / Expiry Date Consistency",
        summary="Automated consistency check across the latest shipment date, period for presentation and credit expiry date.",
        raw_text="\n".join(
            f"{t}: {field_by_tag[t].value}" for t in ("44C", "44D", "48", "31D") if t in field_by_tag
        ),
        section=SECTION_MAIN_SUMMARY,
        subsection=None,
        suggested_verdict=verdict,
        analysis_note=note,
    ))
    return results


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def build_clause_points(fields: List[RawField], lc_type: str) -> List[ClausePoint]:
    clauses: List[ClausePoint] = []
    field_by_tag: Dict[str, RawField] = {f.tag: f for f in fields if not f.tag.startswith("Para")}
    sl = 1

    for f in fields:
        is_swift_tag = f.tag in FIELD_MAP

        if is_swift_tag and f.tag in ("46A", "46B", "47A", "47B", "77J"):
            items = split_into_items(f.value)
            if not items:
                continue
            for item in items:
                subsection = _classify_doc_item(item)
                verdict, note = _analyze_doc_item(item, subsection)
                header = subsection
                clauses.append(ClausePoint(
                    sl_no=sl,
                    point_no=f.tag,
                    header=header,
                    summary=_clean_summary(item),
                    raw_text=item,
                    section=SECTION_DOCUMENTS,
                    subsection=subsection,
                    suggested_verdict=verdict,
                    analysis_note=note,
                ))
                sl += 1
            continue

        if is_swift_tag:
            header, section, subsection = resolve_field(f.tag, f.header_hint)
            verdict, note = _analyze_field(f.tag, f.value, field_by_tag)
        else:
            # fallback free-form paragraph mode
            header = f.header_hint or f"Clause {f.order + 1}"
            section = _classify_freeform(f.value)
            subsection = _classify_doc_item(f.value) if section == SECTION_DOCUMENTS else None
            verdict, note = (
                _analyze_doc_item(f.value, subsection) if subsection
                else (INFO, "Reviewed under general LC checklist; verify manually for completeness.")
            )

        clauses.append(ClausePoint(
            sl_no=sl,
            point_no=f.tag,
            header=header,
            summary=_clean_summary(f.value) or "(no value extracted)",
            raw_text=f.value,
            section=section,
            subsection=subsection,
            suggested_verdict=verdict,
            analysis_note=note,
        ))
        sl += 1

    if field_by_tag:  # only meaningful in SWIFT-tag mode
        clauses.extend(_cross_field_checks(field_by_tag, sl))

    return clauses


def _clean_summary(text: str, max_len: int = 260) -> str:
    cleaned = re.sub(r"\s+", " ", (text or "")).strip()
    cleaned = normalize_dates_in_text(cleaned)  # every date shown in the summary is DD/MM/YYYY
    if len(cleaned) > max_len:
        cleaned = cleaned[: max_len - 1].rstrip() + "…"
    return cleaned
