"""GST validation engine and reconciliation."""
import datetime as dt
import re
from collections import defaultdict
from dataclasses import dataclass, asdict
from decimal import Decimal
from typing import Dict, List

from .classifier import is_implemented
from .config import SECTIONS
from .gstin import validate_gstin, is_valid_structure
from .models import (Line, DocSeries, group_invoices, invoice_value, computed_value,
                     STATUS_DUP, STATUS_APPROVED)
from .utils import D, q2, parse_rates, ZERO

ERROR, WARNING, INFO = "Error", "Warning", "Information"


@dataclass
class Issue:
    severity: str
    code: str
    message: str
    source_file: str = ""
    invoice_no: str = ""
    action: str = ""
    line_id: int = 0
    ref: str = ""            # e.g. "B2B row 7" (sheet/row in a template) or "Sheet1!row 12"

    def to_dict(self):
        return asdict(self)


_INV_OK = re.compile(r"^[A-Za-z0-9/\-]{1,16}$")


def _split_no(no: str):
    from .series import split_no
    sp = split_no(no)
    # the financial-year suffix (if any) is kept inside the prefix part so that prefixes compare correctly
    return (sp[0] + "{" + sp[3] + "}", sp[1], sp[2]) if sp else None


def validate_all(lines: List[Line], client: dict, docs: List[DocSeries], settings: dict,
                 period=None) -> List[Issue]:
    """period = (month, year) of the return, used for date checks."""
    issues: List[Issue] = []
    tol = D(settings.get("rounding_tolerance", "1.00"))
    rates = parse_rates(settings.get("valid_rates", ""))
    own_state = client["gstin"][:2]

    def add(sev, code, msg, l, action):
        issues.append(Issue(sev, code, msg, l.source_file, l.invoice_no, action, l.id))

    for l in lines:
        if l.review_status == "Rejected":
            continue
        if not l.invoice_no.strip():
            add(ERROR, "NO_INV_NO", "Invoice number is missing", l, "Enter the invoice number")
        elif not _INV_OK.match(l.invoice_no.strip()):
            add(ERROR, "INV_NO_FORMAT",
                "Invoice number must be max 16 characters using letters, digits, '/' and '-' only",
                l, "Correct the invoice number as issued (check original)")
        if not l.invoice_date:
            add(ERROR, "NO_DATE", "Invoice date missing or not readable", l, "Enter date as DD/MM/YYYY")
        elif period:
            try:
                d = dt.date.fromisoformat(l.invoice_date)
                if (d.month, d.year) != tuple(period):
                    add(WARNING, "DATE_PERIOD",
                        f"Invoice date {l.invoice_date} is outside return period {period[0]:02d}/{period[1]}",
                        l, "Confirm the invoice belongs to this return period")
            except ValueError:
                add(ERROR, "BAD_DATE", "Invalid invoice date", l, "Correct the date")
        if l.recipient_gstin:
            lvl, msg = validate_gstin(l.recipient_gstin)
            if lvl == "error":
                add(ERROR, "GSTIN_INVALID", f"Recipient GSTIN: {msg}", l,
                    "Correct the GSTIN, or clear it if the recipient is unregistered")
            elif lvl == "warn":
                add(WARNING, "GSTIN_CHECKDIGIT", f"Recipient GSTIN: {msg}", l, "Verify GSTIN on GST portal")
            if l.recipient_gstin == l.supplier_gstin:
                add(ERROR, "GSTIN_SELF", "Recipient GSTIN equals supplier GSTIN", l, "Correct recipient")
        if min(l.taxable, l.igst, l.cgst, l.sgst, l.cess) < 0 and l.note_type == "":
            add(WARNING, "NEGATIVE", "Negative values on a normal invoice", l,
                "If this is a credit note, set Note Type to Credit; otherwise correct the values")
        if not l.pos:
            add(ERROR, "NO_POS", "Place of supply missing", l, "Select the place of supply state")
        elif l.recipient_gstin and l.pos != "96" and l.pos != l.recipient_gstin[:2] and \
                l.invoice_type == "Regular":
            add(INFO, "POS_NE_GSTIN", f"Place of supply {l.pos} differs from the recipient GSTIN state "
                f"{l.recipient_gstin[:2]}", l, "Correct only if goods are really delivered to the GSTIN's state; "
                "use 'Place of supply = GSTIN state' to reset")
        # inter / intra state
        if l.igst and (l.cgst or l.sgst):
            add(ERROR, "IGST_CGST_CONFLICT", "IGST and CGST/SGST both present", l,
                "A supply is either inter-state (IGST) or intra-state (CGST+SGST)")
        elif l.pos:
            inter = l.pos != own_state and l.pos != "96"
            if inter and (l.cgst or l.sgst) and not l.igst:
                add(ERROR, "INTER_NEEDS_IGST", "Place of supply differs from supplier state but CGST/SGST charged",
                    l, "Check place of supply or tax heads (IGST expected)")
            if not inter and l.pos == own_state and l.igst and l.invoice_type == "Regular":
                add(ERROR, "INTRA_NEEDS_CGST", "Place of supply equals supplier state but IGST charged", l,
                    "Check place of supply or tax heads (CGST+SGST expected)")
        if l.cgst != l.sgst and not l.igst:
            add(WARNING, "CGST_SGST_DIFF", "CGST and SGST amounts differ", l, "Verify tax split")
        # tax amount vs rate
        if l.taxable:
            expected = q2(l.taxable * l.rate / 100)
            actual = l.tax_total
            if abs(expected - actual) > tol and l.reverse_charge != "Y":
                add(ERROR, "TAX_MISMATCH",
                    f"Tax {actual} differs from taxable x rate ({l.rate}%) = {expected}", l,
                    "Verify taxable value, rate and tax amounts")
            if rates and l.rate not in rates:
                add(WARNING, "RATE_UNUSUAL", f"Rate {l.rate}% is not a configured GST slab", l,
                    "Confirm rate (Settings > valid rates)")
        # HSN / UQC
        if not l.hsn:
            add(WARNING, "NO_HSN", "HSN/SAC missing - cannot be included in HSN summary", l,
                "Provide HSN/SAC from the invoice/item master")
        elif not (l.hsn.isdigit() and len(l.hsn) in (2, 4, 6, 8)):
            add(ERROR, "HSN_INVALID", f"HSN/SAC '{l.hsn}' must be 2, 4, 6 or 8 digits", l, "Correct HSN/SAC")
        elif l.hsn[:2] == "00":
            add(WARNING, "HSN_PLACEHOLDER", f"HSN '{l.hsn}' is not a real HSN/SAC code (chapter 00 does not exist) - "
                "it looks like a placeholder in the billing software", l,
                "Get the correct HSN from the client / item master and correct it here")
        elif not l.hsn.startswith("99") and not l.uqc:
            add(WARNING, "NO_UQC", "Unit of measure missing for goods HSN (default OTH-OTHERS will be used)",
                l, "Enter UQC (e.g. NOS, KGS)")
        if l.confidence < 0.6:
            add(WARNING, "LOW_CONF", f"Low extraction confidence ({l.confidence})", l, "Verify against source")
        if l.review_status == STATUS_DUP:
            add(WARNING, "DUP_SUSPECT", "Possible duplicate of a line from another file", l,
                "Approve one copy and reject the other")
        if l.section and not is_implemented(l.section):
            add(WARNING, "MANUAL_SECTION",
                f"Section {l.section} ({SECTIONS.get(l.section, ('',))[0]}) is not generated by this version",
                l, "Report this transaction manually in the Offline Tool / portal")
        if l.section == "NIL":
            add(INFO, "NIL_CLASS", "Nil-rated / exempt / non-GST needs staff classification", l,
                "Decide nil / exempt / non-GST and inter/intra-state, report in Table 8")
        if l.note_type in ("C", "D") and not l.orig_invoice_no:
            add(WARNING, "NOTE_NO_ORIG", "Credit/debit note without original invoice reference", l,
                "Enter original invoice number and date")
        if l.reverse_charge == "Y":
            add(INFO, "RCM", "Reverse charge flagged - confirm reporting", l, "Confirm applicability")

    live = [l for l in lines if l.review_status != "Rejected"]
    groups = group_invoices(live)
    # invoice level checks
    by_no: Dict[str, set] = defaultdict(set)
    files_by_key = defaultdict(set)
    for key, grp in groups.items():
        first = grp[0]
        by_no[key[1]].add(key[2])
        for l in grp:
            files_by_key[key].add(l.source_file)
        total = invoice_value(grp)
        comp = computed_value(grp)
        if abs(total - comp) > tol:
            add(ERROR, "TOTAL_MISMATCH",
                f"Invoice total {q2(total)} differs from taxable + taxes + cess = {q2(comp)}", first,
                "Check invoice total / missing lines (all items of the invoice must be present)")
        recips = {l.recipient_gstin for l in grp}
        if len(recips) > 1:
            add(ERROR, "MIXED_RECIPIENT", "Lines of one invoice carry different recipient GSTINs", first,
                "Correct recipient GSTIN on all lines")
        secs = {l.section for l in grp}
        if len(secs) > 1:
            add(WARNING, "MIXED_SECTION", f"Lines of one invoice are in different sections: {sorted(secs)}",
                first, "Check classification of each line")
    for no, dates in by_no.items():
        if no and len(dates) > 1:
            l = next(x for x in live if x.key()[1] == no)
            add(ERROR, "DUP_NO_DIFF_DATE", f"Invoice number used on different dates: {sorted(dates)}", l,
                "Invoice numbers must be unique in a financial year - correct")
    for key, files in files_by_key.items():
        if len(files) > 1:
            l = groups[key][0]
            add(WARNING, "DUP_ACROSS_FILES", f"Invoice appears in multiple files: {sorted(files)}", l,
                "Keep only one copy (reject the others)")

    # numbering gaps (per series; per customer when customers have their own runs of numbers)
    from .series import entries_from_lines, build_runs, gap_report
    for text in gap_report(build_runs(entries_from_lines(live), "auto"), docs):
        issues.append(Issue(INFO, "SEQ_GAP", text, "", "",
                            "Confirm they are cancelled/unused and add them as cancelled in the Documents tab"))

    # documents register
    if not docs:
        issues.append(Issue(WARNING, "DOCS_MISSING",
                            "No document-series register entered - documents.csv cannot be generated reliably", "", "",
                            "Upload/enter the invoice register with issued and cancelled documents (Documents tab)"))
    for d in docs:
        if d.origin == "derived":
            issues.append(Issue(WARNING, "DOCS_DERIVED",
                                f"Series {d.from_no}-{d.to_no} was derived from received invoices only; "
                                "issued/cancelled counts are unverified", d.source_file, "",
                                "Confirm against the client's invoice register and edit counts"))
        fs, ts = _split_no(d.from_no), _split_no(d.to_no)
        if not d.from_no or not d.to_no:
            issues.append(Issue(ERROR, "DOCS_RANGE", "Document series missing From/To number", "", "", "Fix register"))
        elif fs and ts and fs[0] == ts[0] and ts[1] >= fs[1]:
            span = ts[1] - fs[1] + 1
            if d.total != span:
                issues.append(Issue(WARNING, "DOCS_TOTAL",
                                    f"Series {d.from_no}-{d.to_no}: total {d.total} differs from range size {span}",
                                    "", "", "Verify total issued"))
        if d.cancelled > d.total:
            issues.append(Issue(ERROR, "DOCS_CANCEL", "Cancelled documents exceed total issued", "", "", "Fix register"))
    # invoices not covered by any register range (only invoice-nature docs)
    inv_ranges = []
    for d in docs:
        fs, ts = _split_no(d.from_no), _split_no(d.to_no)
        if fs and ts and fs[0] == ts[0]:
            inv_ranges.append((fs[0].upper(), fs[1], ts[1]))
    if docs and inv_ranges:
        for key, grp in groups.items():
            if key[0]:
                continue
            sp = _split_no(grp[0].invoice_no)
            if not sp or not any(sp[0].upper() == p and a <= sp[1] <= b for p, a, b in inv_ranges):
                add(WARNING, "NOT_IN_REGISTER", "Invoice number is outside every document-register range",
                    grp[0], "Extend the register range or correct the invoice number")
    return issues


def blocking_errors(issues: List[Issue], lines: List[Line]) -> List[Issue]:
    """Errors on approved lines (or register-level errors) that block export."""
    approved = {l.id for l in lines if l.review_status == STATUS_APPROVED}
    return [i for i in issues if i.severity == ERROR and (i.line_id == 0 or i.line_id in approved)]
