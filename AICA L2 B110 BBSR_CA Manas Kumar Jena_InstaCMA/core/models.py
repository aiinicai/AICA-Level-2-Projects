"""
Data model for InstaCMA.

The client's statements are kept as LINES with the client's own ledger names
(e.g. "Staff Salary", "Security Dep. - Telephone Authority").  Each line
carries a CMA head (for grouping and for the FORM-II / FORM-III links) and
one amount per statement year.  Years are typed by the user:
Audited / Provisional (from statements), Estimated / Projected (built by the
tool, or taken from the client's own projection figures).
"""
import datetime as dt
import json
import re
import uuid
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional

YEAR_KINDS = ["Audited", "Actual", "Provisional", "Estimated", "Projected"]
STATEMENT_KINDS = ("Audited", "Actual", "Provisional")
MAX_YEARS = 7


def fy_label(fy_end):
    return "%d-%02d" % (fy_end - 1, fy_end % 100)


def fy_end_of(date):
    return date.year + (1 if date.month >= 4 else 0)


def new_id():
    return uuid.uuid4().hex[:10]


@dataclass
class SourceLine:
    """A raw line as read from a file (before it is merged into a Line)."""
    year: int
    statement: str
    label: str
    amount: float
    head: str = ""
    confidence: int = 0
    source: str = ""
    note: str = ""
    section: str = ""             # "trading" / "pl" for P&L expense lines ("" = by head)
    year_kind: str = ""           # "Provisional" when the statement says so
    gross: float = 0.0            # fixed asset: value before depreciation (net line only)
    side: int = -1                # T-form side: 0 = Dr / liabilities, 1 = Cr / assets, -1 = not T-form


@dataclass
class Line:
    statement: str                      # PL / BS
    head: str                           # CMA head key
    label: str                          # client's own name
    values: Dict[str, float] = field(default_factory=dict)    # {"2026": amount}
    basis: str = ""                     # V/F (P&L) or S/H (BS); "" = default for the head
    rate: Optional[float] = None        # WDV rate for fixed-asset lines
    section: str = ""                   # P&L expense lines: "trading" or "pl" ("" = by head)
    sources: List[str] = field(default_factory=list)
    gross: Dict[str, float] = field(default_factory=dict)     # fixed assets: {"2025": value before depreciation}
    id: str = field(default_factory=new_id)

    def v(self, fy):
        return float(self.values.get(str(fy), 0.0) or 0.0)

    def set(self, fy, amount):
        self.values[str(fy)] = float(amount)


@dataclass
class YearDef:
    fy: int
    kind: str = "Audited"
    use_client_figures: bool = False    # only for Estimated / Projected

    @property
    def label(self):
        return fy_label(self.fy)

    @property
    def from_statement(self):
        return self.kind in STATEMENT_KINDS or self.use_client_figures


@dataclass
class YearInput:
    """Assumptions for a tool-built (estimated / projected) year. None = default."""
    fy: int
    growth: Optional[float] = None
    stock_days: Optional[float] = None
    debtor_days: Optional[float] = None
    creditor_days: Optional[float] = None
    cc_limit: Optional[float] = None
    drawings: Optional[float] = None
    capital_introduced: float = 0.0
    gp_pct: Optional[float] = None      # gross profit % for the year (None = previous year's); set by the DSCR fit
    line_override: Dict[str, float] = field(default_factory=dict)   # {line id: amount} set by the cash rule


@dataclass
class ExistingLoan:
    line_id: str
    lender: str = ""
    emi: float = 0.0                    # monthly EMI
    rate: float = 0.10
    end_date: str = ""                  # yyyy-mm-dd
    repay_override: Dict[str, float] = field(default_factory=dict)  # {"2027": principal}


@dataclass
class Intake:
    # client
    client_name: str = ""
    signatory_name: str = ""
    signatory_title: str = "Proprietor"
    constitution: str = "Proprietorship"
    nature: str = "Trading"
    address: str = ""
    pan: str = ""
    gstin: str = ""
    bank_name: str = ""
    branch: str = ""
    case_type: str = "Fresh"            # Fresh / Renewal / Enhancement
    place: str = ""
    preparation_date: str = field(default_factory=lambda: dt.date.today().isoformat())
    # cash credit
    has_cc: bool = True
    cc_existing_limit: float = 0.0
    cc_limit: float = 0.0
    cc_rate: Optional[float] = None
    stock_margin: Optional[float] = None
    debtor_margin: Optional[float] = None
    deduct_creditors: bool = True
    exclude_over90: bool = False
    debtors_over_90_pct: float = 0.0
    # term loan
    has_tl: bool = False
    tl_amount: float = 0.0
    tl_rate: Optional[float] = None
    tl_tenure_months: int = 60
    tl_moratorium_months: int = 0
    tl_method: str = "Equal EMI"
    tl_purpose: str = ""
    tl_use: str = "Capex"
    tl_capex_class: str = "fa_plant"
    # norms (None = default from settings)
    dscr_min: Optional[float] = None
    dscr_max: Optional[float] = None
    dscr_deduct_drawings: bool = False
    turnover_fail_below: Optional[float] = None
    turnover_pass_from: Optional[float] = None
    dp_buffer: float = 0.02
    debtor_days_cap: float = 90
    auto_raise_stock: bool = True       # raise stock days when the debtor-days cap is not enough for DP
    stock_days_cap: float = 120
    default_growth: Optional[float] = None
    tax_rate: Optional[float] = None
    unsecured_loan_rate: float = 0.0
    unit: str = "Actual"
    gst_turnover: Dict[str, float] = field(default_factory=dict)

    @property
    def prep_date(self):
        return dt.date.fromisoformat(str(self.preparation_date)[:10])

    @property
    def facility_start(self):
        d = self.prep_date
        y, m = (d.year + 1, 1) if d.month == 12 else (d.year, d.month + 1)
        return dt.date(y, m, 1)

    @property
    def is_company(self):
        return "Company" in self.constitution


NORM_DEFAULTS = {"dscr_min": 1.5, "dscr_max": 2.5, "turnover_fail_below": 4.0, "turnover_pass_from": 5.0,
                 "stock_margin": 0.25, "debtor_margin": 0.25, "default_growth": 0.20, "cc_rate": 0.10,
                 "tl_rate": 0.105}

TAX_DEFAULT = {"Proprietorship": 0.0, "HUF": 0.0, "Trust / Society": 0.0, "Partnership Firm": 0.312,
               "LLP": 0.312, "Private Limited Company": 0.2517, "Public Limited Company": 0.2517}


def norm(intake, key, settings_defaults=None):
    v = getattr(intake, key, None)
    if v is not None:
        return v
    if settings_defaults and key in settings_defaults and settings_defaults[key] is not None:
        return settings_defaults[key]
    return NORM_DEFAULTS[key]


def tax_rate(intake):
    if intake.tax_rate is not None:
        return intake.tax_rate
    return TAX_DEFAULT.get(intake.constitution, 0.0)


@dataclass
class CMAProject:
    intake: Intake = field(default_factory=Intake)
    years: List[YearDef] = field(default_factory=list)
    lines: List[Line] = field(default_factory=list)
    inputs: List[YearInput] = field(default_factory=list)
    loans: List[ExistingLoan] = field(default_factory=list)
    source_lines: List[SourceLine] = field(default_factory=list)
    locked: bool = False
    history: Dict[str, Dict] = field(default_factory=dict)   # earlier projections {fy: {key: value}}

    # ---------------------------------------------------------- years
    def year_list(self):
        return sorted(self.years, key=lambda y: y.fy)

    def statement_years(self):
        return [y for y in self.year_list() if y.from_statement]

    def tool_years(self):
        return [y for y in self.year_list() if not y.from_statement]

    def year_input(self, fy):
        for yi in self.inputs:
            if yi.fy == fy:
                return yi
        yi = YearInput(fy=fy)
        self.inputs.append(yi)
        return yi

    def line(self, lid):
        for ln in self.lines:
            if ln.id == lid:
                return ln
        return None

    def lines_of(self, *heads, statement=None):
        return [ln for ln in self.lines if ln.head in heads and (statement is None or ln.statement == statement)]

    # ---------------------------------------------------------- build lines
    def build_lines_from_sources(self, single_heads):
        """Merge raw source lines into client lines (same head + same name -> one line)."""
        old = {(ln.statement, ln.head, _key(ln.label)): ln for ln in self.lines}
        out, index = [], {}
        for s in self.source_lines:
            if not s.head or s.head in ("ignore", "_reported_net_profit"):
                continue
            k = (s.statement if s.head not in ("drawings", "capital_introduced") else "BS", s.head,
                 "_single_" if s.head in single_heads else _key(s.label))
            ln = index.get(k)
            if ln is None:
                prev = old.get((k[0], k[1], _key(s.label)))
                ln = Line(statement=k[0], head=s.head, label=s.label,
                          basis=prev.basis if prev else "", rate=prev.rate if prev else None,
                          section=(prev.section if prev and prev.section else s.section))
                if prev:
                    ln.id = prev.id
                index[k] = ln
                out.append(ln)
            ln.values[str(s.year)] = ln.values.get(str(s.year), 0.0) + float(s.amount)
            if getattr(s, "gross", 0):
                ln.gross[str(s.year)] = ln.gross.get(str(s.year), 0.0) + float(s.gross)
            src = "%s: %s" % (s.year, s.source or s.label)
            if src not in ln.sources:
                ln.sources.append(src)
        self.lines = _merge_renamed(out)
        return self.lines

    def reported_net_profit(self, fy):
        tot = None
        for s in self.source_lines:
            if s.year == fy and s.head == "_reported_net_profit":
                tot = (tot or 0) + s.amount
        return tot

    # ---------------------------------------------------------- persistence
    def to_dict(self):
        return {"app": "InstaCMA", "intake": asdict(self.intake),
                "years": [asdict(y) for y in self.years], "lines": [asdict(l) for l in self.lines],
                "inputs": [asdict(i) for i in self.inputs], "loans": [asdict(l) for l in self.loans],
                "source_lines": [asdict(s) for s in self.source_lines], "locked": self.locked,
                "history": self.history}

    @classmethod
    def from_dict(cls, d):
        p = cls()
        p.intake = Intake(**d.get("intake", {}))
        p.years = [YearDef(**y) for y in d.get("years", [])]
        p.lines = [Line(**l) for l in d.get("lines", [])]
        p.inputs = [YearInput(**i) for i in d.get("inputs", [])]
        p.loans = [ExistingLoan(**l) for l in d.get("loans", [])]
        p.source_lines = [SourceLine(**s) for s in d.get("source_lines", [])]
        p.locked = d.get("locked", False)
        p.history = d.get("history", {})
        return p

    def save(self, path):
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, indent=1, default=str)

    @classmethod
    def load(cls, path):
        with open(path, "r", encoding="utf-8") as fh:
            return cls.from_dict(json.load(fh))


_STOP = {"expenses", "expense", "exp", "expneses", "charges", "charge", "and", "of", "received", "a", "c", "to",
         "by", "account", "less", "add", "the", "for", "paid", "on"}


def _words(label):
    return {w for w in re.findall(r"[a-z]+", str(label).lower()) if len(w) > 2 and w not in _STOP}


def _merge_renamed(lines):
    """The same head under a different name in another year (Rent / Shop Rent, Interest / Interest Received)
    is one line: merge lines of one head whose years do not overlap. The latest year's name is kept."""
    out = []
    for ln in lines:
        for o in out:
            if (o.statement, o.head, o.section) == (ln.statement, ln.head, ln.section) and \
                    _words(o.label) & _words(ln.label) and \
                    not (set(k for k, v in o.values.items() if v) & set(k for k, v in ln.values.items() if v)):
                late_ln = max([int(k) for k, v in ln.values.items() if v] or [0])
                late_o = max([int(k) for k, v in o.values.items() if v] or [0])
                for k, v in ln.values.items():
                    if v:
                        o.values[k] = v
                for k, v in ln.gross.items():
                    o.gross[k] = v
                o.sources += [x for x in ln.sources if x not in o.sources]
                if late_ln > late_o:
                    o.label = ln.label
                break
        else:
            out.append(ln)
    return out


def _key(label):
    return re.sub(r"[^a-z0-9]", "", str(label).lower())
