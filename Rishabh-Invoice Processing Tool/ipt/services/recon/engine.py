"""Reconciliation engine (docs/RECON_RULES.md). Pure functions: no database, no Qt.

Sources: 'ipt' (processed invoices), 'pr' (purchase register / Tally books), '2b' (GSTR-2B).
Matching is per supplier GSTIN in stages; a record is paired only when exactly ONE candidate qualifies
(and it is the only record that qualifies for that candidate). Two or more candidates -> no automatic
match; the row says so and the user links it manually.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from difflib import SequenceMatcher

from ipt.core.textnorm import normalize_invoice_no

SOURCES = ("ipt", "pr", "2b")
SOURCE_LABEL = {"ipt": "IPT", "pr": "Tally books", "2b": "GSTR-2B"}
MISSING_STATUS = {"2b": "NOT_IN_2B", "pr": "NOT_IN_BOOKS", "ipt": "NOT_IN_IPT"}
# NOT_IN_IPT comes after the books-vs-2B statuses: an invoice booked straight in Tally must not hide a
# statutory difference between Tally and GSTR-2B (the reason list still says it is not in IPT).
STATUS_ORDER = ["DUPLICATE", "AMENDED", "GSTIN_MISMATCH", "CDN_DIFFERENCE", "NOT_IN_2B", "NOT_IN_BOOKS",
                "AMOUNT_MISMATCH", "PARTIALLY_MATCHED", "NOT_IN_IPT", "MATCHED"]
STAGE_CONF = {"exact": Decimal("1.00"), "normalised": Decimal("0.95"), "financial": Decimal("0.85"),
              "fuzzy": Decimal("0.70"), "gstin": Decimal("0.60"), "doc_type": Decimal("0.60"),
              "manual": Decimal("1.00")}
SUGGESTED_ACTION = {
    "NOT_IN_2B": "Check supplier's GSTR-1/IFF filing; confirm the invoice was reported; follow up; consider deferring ITC",
    "NOT_IN_BOOKS": "Check if received but not booked; verify purchase entry; check other party/period",
    "AMOUNT_MISMATCH": "Verify taxable value and rate; check credit/debit notes; check rounding; ask supplier to amend if wrong",
    "GSTIN_MISMATCH": "Verify GSTIN on invoice; correct Tally party ledger GSTIN; check multiple registrations",
    "PARTIALLY_MATCHED": "Verify invoice number, series and date on the original document",
    "DUPLICATE": "Confirm double booking; cancel duplicate voucher after review",
    "AMENDED": "Use amended values; check books reflect the amendment",
    "CDN_DIFFERENCE": "Match note to original invoice; check note type and sign in books",
    "NOT_IN_IPT": "Upload the source invoice for document support",
    "MATCHED": "",
}
AMOUNT_HEADS = ("taxable", "igst", "cgst", "sgst", "cess")
MODES = {"ipt_tally": ("ipt", "pr"), "ipt_2b": ("ipt", "2b"), "tally_2b": ("pr", "2b"), "three_way": ("ipt", "pr", "2b")}
MODE_LABEL = {"three_way": "Three-way (IPT + Tally + GSTR-2B)", "tally_2b": "Tally books vs GSTR-2B",
              "ipt_2b": "IPT invoices vs GSTR-2B", "ipt_tally": "IPT invoices vs Tally books"}


@dataclass
class Settings:
    taxable_tol: Decimal = Decimal("1.00")
    tax_tol: Decimal = Decimal("1.00")
    total_tol: Decimal = Decimal("1.00")
    date_tol_days: int = 0
    similarity: int = 90


@dataclass
class Rec:
    src: str
    id: int
    gstin: str
    doc_no: str
    doc_date: date | None
    taxable: Decimal | None = None
    igst: Decimal | None = None
    cgst: Decimal | None = None
    sgst: Decimal | None = None
    cess: Decimal | None = None
    total: Decimal | None = None
    doc_type: str = "INV"
    name: str = ""
    section: str = ""
    original_no: str = ""
    itc_available: str = ""
    norm: str = ""
    orig_norm: str = ""
    notes: list[str] = field(default_factory=list)
    duplicate_of: "Rec | None" = None
    duplicates: int = 0                 # >0: this record is booked more than once in its source
    amends: str = ""

    def __post_init__(self):
        self.gstin = (self.gstin or "").upper()
        self.norm = self.norm or (normalize_invoice_no(self.doc_no) or "")
        self.orig_norm = normalize_invoice_no(self.original_no) or "" if self.original_no else ""

    @property
    def key(self) -> tuple[str, int]:
        return (self.src, self.id)

    def tax(self) -> Decimal:
        return sum((x or Decimal("0")) for x in (self.igst, self.cgst, self.sgst, self.cess))


@dataclass
class Row:
    recs: dict[str, Rec] = field(default_factory=dict)       # source -> record
    stage: str = ""
    confidence: Decimal | None = None
    status: str = ""
    reasons: list[str] = field(default_factory=list)
    differences: dict = field(default_factory=dict)
    is_manual: bool = False

    @property
    def gstin(self) -> str:
        for s in ("2b", "pr", "ipt"):
            if s in self.recs:
                return self.recs[s].gstin
        return ""

    def first(self, attr: str):
        for s in ("2b", "pr", "ipt"):
            if s in self.recs and getattr(self.recs[s], attr):
                return getattr(self.recs[s], attr)
        return None

    @property
    def suggested_action(self) -> str:
        return SUGGESTED_ACTION.get(self.status, "")


# ----------------------------------------------------------------------------- comparisons
def _d(v) -> Decimal:
    return v if v is not None else Decimal("0")


def amounts_within(a: Rec, b: Rec, st: Settings) -> bool:
    if a.taxable is not None and b.taxable is not None and abs(a.taxable - b.taxable) > st.taxable_tol:
        return False
    if a.taxable is None and b.taxable is None and a.total is not None and b.total is not None:
        if abs(a.total - b.total) > st.total_tol:
            return False
    return all(abs(_d(getattr(a, h)) - _d(getattr(b, h))) <= st.tax_tol for h in ("igst", "cgst", "sgst", "cess"))


def dates_within(a: Rec, b: Rec, st: Settings) -> bool:
    if a.doc_date is None or b.doc_date is None:
        return False
    return abs((a.doc_date - b.doc_date).days) <= st.date_tol_days


def similarity(a: str, b: str) -> int:
    if not a or not b:
        return 0
    return int(round(SequenceMatcher(None, a, b).ratio() * 100))


def _nums(r: Rec) -> set[str]:
    return {r.norm} | ({r.orig_norm} if r.orig_norm else set())


STAGES = [
    ("exact", lambda a, b, st: a.doc_type == b.doc_type and a.doc_no.strip().upper() == b.doc_no.strip().upper()),
    ("normalised", lambda a, b, st: a.doc_type == b.doc_type and bool(_nums(a) & _nums(b) - {""})),
    ("financial", lambda a, b, st: a.doc_type == b.doc_type and dates_within(a, b, st) and amounts_within(a, b, st)
     and (a.taxable is not None or a.total is not None)),
    ("fuzzy", lambda a, b, st: a.doc_type == b.doc_type and similarity(a.norm, b.norm) >= st.similarity
     and amounts_within(a, b, st)),
]


# ----------------------------------------------------------------------------- pre-processing
def mark_duplicates(recs: list[Rec]) -> tuple[list[Rec], list[Rec]]:
    """Same GSTIN + normalised no + doc type twice within one source: the first (lowest id) stays in matching,
    the others become DUPLICATE rows."""
    groups: dict[tuple, list[Rec]] = {}
    for r in recs:
        if r.norm:
            groups.setdefault((r.gstin, r.norm, r.doc_type), []).append(r)
    dups = []
    for g in groups.values():
        if len(g) > 1:
            g.sort(key=lambda r: r.id)
            for extra in g[1:]:
                extra.duplicate_of = g[0]
                dups.append(extra)
            g[0].duplicates = len(g)
            g[0].notes.append(f"Appears {len(g)} times in {SOURCE_LABEL[g[0].src]}")
    dup_keys = {d.key for d in dups}
    return [r for r in recs if r.key not in dup_keys], dups


def apply_amendments(recs_2b: list[Rec]) -> list[Rec]:
    """An amendment (B2BA / CDNRA) supersedes the original document in 2B: the original is dropped from
    matching and the amendment is matched under both its new and original number."""
    amended = [r for r in recs_2b if r.section in ("B2BA", "CDNRA") and r.orig_norm]
    drop = set()
    for a in amended:
        a.amends = a.original_no
        for r in recs_2b:
            if r is not a and r.section in ("B2B", "CDNR") and r.gstin == a.gstin and r.norm == a.orig_norm:
                drop.add(r.key)
                a.notes.append(f"Supersedes the original {r.section} entry {r.doc_no}")
    return [r for r in recs_2b if r.key not in drop]


# ----------------------------------------------------------------------------- pairing
def pair(left: list[Rec], right: list[Rec], st: Settings) -> tuple[list[tuple[Rec, Rec, str]], list[Rec], list[Rec]]:
    """Pair records of two sources. Returns (pairs, unpaired left, unpaired right)."""
    free_l = {r.key: r for r in left}
    free_r = {r.key: r for r in right}
    blocked: set[tuple] = set()            # ambiguous: stop automatic matching for these
    pairs: list[tuple[Rec, Rec, str]] = []
    for stage, test in STAGES:
        by_gstin: dict[str, list[Rec]] = {}
        for r in free_r.values():
            by_gstin.setdefault(r.gstin, []).append(r)
        proposals: dict[tuple, list[Rec]] = {}
        for a in list(free_l.values()):
            if a.key in blocked or not a.gstin:
                continue
            proposals[a.key] = [b for b in by_gstin.get(a.gstin, []) if b.key not in blocked and test(a, b, st)]
        reverse: dict[tuple, list[tuple]] = {}
        for ak, cands in proposals.items():
            for b in cands:
                reverse.setdefault(b.key, []).append(ak)
        for ak, cands in proposals.items():
            if not cands:
                continue
            a = free_l[ak]
            if len(cands) > 1:
                a.notes.append(f"{len(cands)} possible matches in {SOURCE_LABEL[cands[0].src]} "
                               f"({', '.join(c.doc_no for c in cands[:3])}) – link manually")
                blocked.add(ak)
                continue
            b = cands[0]
            if len(reverse[b.key]) > 1:
                b.notes.append(f"{len(reverse[b.key])} possible matches in {SOURCE_LABEL[a.src]} – link manually")
                blocked.add(b.key)
                for other in reverse[b.key]:
                    blocked.add(other)
                continue
            pairs.append((a, b, stage))
            del free_l[ak], free_r[b.key]
    # leftovers: the same document under a different GSTIN, or a different note / document type
    for stage, test in (("gstin", lambda a, b: a.gstin != b.gstin and a.doc_type == b.doc_type and a.norm == b.norm
                         and dates_within(a, b, st) and amounts_within(a, b, st)),
                        ("doc_type", lambda a, b: a.gstin == b.gstin and a.doc_type != b.doc_type and a.norm == b.norm)):
        for a in list(free_l.values()):
            if a.key in blocked or not a.norm:
                continue
            cands = [b for b in free_r.values() if b.key not in blocked and test(a, b)]
            back = [x for x in free_l.values() if cands and test(x, cands[0])] if len(cands) == 1 else []
            if len(cands) == 1 and len(back) == 1:
                pairs.append((a, cands[0], stage))
                del free_l[a.key], free_r[cands[0].key]
    return pairs, list(free_l.values()), list(free_r.values())


# ----------------------------------------------------------------------------- classification
def _compare(a: Rec, b: Rec, st: Settings) -> tuple[list[str], list[str]]:
    """(statuses that apply, reasons) for one paired couple of records."""
    la, lb = SOURCE_LABEL[a.src], SOURCE_LABEL[b.src]
    statuses, reasons = [], []
    if a.gstin != b.gstin:
        statuses.append("GSTIN_MISMATCH")
        reasons.append(f"GSTIN differs: {la} {a.gstin or '-'} / {lb} {b.gstin or '-'}")
    if a.doc_type != b.doc_type:
        statuses.append("CDN_DIFFERENCE")
        reasons.append(f"Document type differs: {la} {a.doc_type} / {lb} {b.doc_type}")
    amount_bad = False
    for h, tol in (("taxable", st.taxable_tol), ("igst", st.tax_tol), ("cgst", st.tax_tol), ("sgst", st.tax_tol),
                   ("cess", st.tax_tol)):
        x, y = getattr(a, h), getattr(b, h)
        if h == "taxable" and (x is None or y is None):
            continue
        if abs(_d(x) - _d(y)) > tol:
            amount_bad = True
            reasons.append(f"{h.upper() if h != 'taxable' else 'Taxable value'} differs by "
                           f"{abs(_d(x) - _d(y)):,.2f} ({la} {_d(x):,.2f} / {lb} {_d(y):,.2f})")
    if a.total is not None and b.total is not None and abs(a.total - b.total) > st.total_tol:
        amount_bad = True
        reasons.append(f"Invoice total differs by {abs(a.total - b.total):,.2f}")
    if amount_bad:
        statuses.append("AMOUNT_MISMATCH")
    partial = False
    if not (_nums(a) & _nums(b) - {""}):
        partial = True
        reasons.append(f"Invoice no. differs: {la} {a.doc_no} / {lb} {b.doc_no}")
    if a.doc_date and b.doc_date and abs((a.doc_date - b.doc_date).days) > st.date_tol_days:
        partial = True
        reasons.append(f"Date differs: {la} {a.doc_date:%d-%m-%Y} / {lb} {b.doc_date:%d-%m-%Y}")
    elif not (a.doc_date and b.doc_date):
        partial = True
        reasons.append("Date missing in one source")
    if partial:
        statuses.append("PARTIALLY_MATCHED")
    return statuses, reasons


def classify(row: Row, sources: tuple[str, ...], st: Settings) -> Row:
    statuses: list[str] = []
    reasons: list[str] = []
    recs = row.recs
    for r in recs.values():
        reasons += r.notes
        if r.duplicates:
            statuses.append("DUPLICATE")
        if r.duplicate_of is not None:
            statuses.append("DUPLICATE")
            reasons.append(f"Same invoice already in {SOURCE_LABEL[r.src]} (record {r.duplicate_of.id})")
        if r.src == "2b" and r.amends:
            statuses.append("AMENDED")
            reasons.append(f"Amended in GSTR-2B ({r.section}) – original no. {r.amends}")
    for s in sources:
        if s not in recs:
            statuses.append(MISSING_STATUS[s])
            reasons.append(f"Not found in {SOURCE_LABEL[s]}")
    present = [s for s in ("pr", "2b", "ipt") if s in recs]
    # statutory pair first (books vs 2B), then the IPT invoice against books (else against 2B)
    couples = []
    if "pr" in recs and "2b" in recs:
        couples.append(("pr", "2b"))
    if "ipt" in recs and "pr" in recs:
        couples.append(("ipt", "pr"))
    elif "ipt" in recs and "2b" in recs:
        couples.append(("ipt", "2b"))
    for x, y in couples:
        st_, rs = _compare(recs[x], recs[y], st)
        statuses += st_
        reasons += rs
    if not statuses and len(present) >= 2:
        statuses.append("MATCHED")
    if not statuses:
        statuses.append(MISSING_STATUS[next(s for s in sources if s not in recs)] if len(present) < len(sources)
                        else "MATCHED")
    row.status = next(s for s in STATUS_ORDER if s in statuses)
    seen, uniq = set(), []
    for r in reasons:
        if r not in seen:
            seen.add(r)
            uniq.append(r)
    row.reasons = uniq
    row.differences = {h: {s: (str(getattr(recs[s], h)) if getattr(recs[s], h) is not None else None)
                           for s in recs} for h in AMOUNT_HEADS + ("total",)}
    row.differences["doc_no"] = {s: recs[s].doc_no for s in recs}
    row.differences["doc_date"] = {s: (recs[s].doc_date.isoformat() if recs[s].doc_date else None) for s in recs}
    return row


# ----------------------------------------------------------------------------- run
def reconcile(data: dict[str, list[Rec]], mode: str, st: Settings,
              manual_links: list[dict[str, int]] | None = None) -> list[Row]:
    """data: source -> records. manual_links: earlier user links {source: record id} kept across runs."""
    sources = MODES[mode]
    pools: dict[str, list[Rec]] = {}
    dup_rows: list[Row] = []
    for s in sources:
        recs = list(data.get(s, []))
        if s == "2b":
            recs = apply_amendments(recs)
        recs, dups = mark_duplicates(recs)
        pools[s] = recs
        dup_rows += [Row(recs={s: d}) for d in dups]
    rows: list[Row] = []
    # 1. links the user made by hand
    for link in manual_links or []:
        picked = {}
        for s, rid in link.items():
            r = next((x for x in pools.get(s, []) if x.id == rid), None)
            if r is not None:
                picked[s] = r
        if len(picked) >= 2:
            for s, r in picked.items():
                pools[s].remove(r)
            rows.append(Row(recs=picked, stage="manual", confidence=STAGE_CONF["manual"], is_manual=True))
    # 2. automatic pairing
    if mode == "three_way":
        pairs, pr_left, b_left = pair(pools["pr"], pools["2b"], st)
        trio = [Row(recs={"pr": a, "2b": b}, stage=stg, confidence=STAGE_CONF[stg]) for a, b, stg in pairs]
        trio += [Row(recs={"pr": a}) for a in pr_left] + [Row(recs={"2b": b}) for b in b_left]
        # attach IPT invoices to books records, then to 2B-only rows
        book_rows = {row.recs["pr"].key: row for row in trio if "pr" in row.recs}
        p2, ipt_left, _ = pair(pools["ipt"], [r.recs["pr"] for r in book_rows.values()], st)
        for a, b, stg in p2:
            row = book_rows[b.key]
            row.recs["ipt"] = a
            row.confidence = min(row.confidence or STAGE_CONF[stg], STAGE_CONF[stg])
            row.stage = row.stage or stg
        only_2b = {row.recs["2b"].key: row for row in trio if set(row.recs) == {"2b"}}
        p3, ipt_left, _ = pair(ipt_left, [r.recs["2b"] for r in only_2b.values()], st)
        for a, b, stg in p3:
            row = only_2b[b.key]
            row.recs["ipt"] = a
            row.stage, row.confidence = stg, STAGE_CONF[stg]
        trio += [Row(recs={"ipt": a}) for a in ipt_left]
        rows += trio
    else:
        x, y = sources
        pairs, lx, ly = pair(pools[x], pools[y], st)
        rows += [Row(recs={x: a, y: b}, stage=stg, confidence=STAGE_CONF[stg]) for a, b, stg in pairs]
        rows += [Row(recs={x: a}) for a in lx] + [Row(recs={y: b}) for b in ly]
    rows += dup_rows
    for row in rows:
        classify(row, sources, st)
    rows.sort(key=lambda r: (STATUS_ORDER.index(r.status), r.gstin, str(r.first("doc_no") or "")))
    return rows
