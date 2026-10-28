"""Dynamic corporate-tax questionnaire.

Questions are data (so the GUI can render them and tests can answer them). Only relevant questions
are shown; answers that can be reliably prefilled from the data are prefilled but marked 'unconfirmed'
until the user accepts them. A question left unanswered or answered 'Unknown' becomes an open item
('Information required') - it never silently becomes a tax fact.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

YES, NO, UNK = "Yes", "No", "Unknown"
YNU = [YES, NO, UNK]


@dataclass
class Question:
    id: str
    section: str                 # A..F
    text: str
    kind: str                    # text | number | date | choice | multi | table
    options: list = field(default_factory=list)
    columns: list = field(default_factory=list)       # for tables: dicts {id,label,kind,options}
    rows_from: str = ""                               # fixed rows generated from the data (e.g. 'fv_accounts')
    help: str = ""
    why: str = ""
    required: bool = True
    default: Any = None
    relevant: Optional[Callable] = None               # f(answers, ctx) -> bool
    evidence: str = ""                                # supporting document normally expected


SECTIONS = {
    "A": "Company and tax-period information",
    "B": "Accounting policies, elections and transitional rules",
    "C": "Small Business Relief",
    "D": "Qualifying Free Zone Person (QFZP)",
    "E": "Other tax adjustments and reliefs",
    "F": "Management confirmations",
}


def ans(answers: dict, qid: str, default=None):
    v = answers.get(qid)
    if isinstance(v, dict) and "value" in v:
        v = v["value"]
    return default if v in (None, "") else v


def _is(qid, *vals):
    return lambda a, c: ans(a, qid) in vals


def _fz(a, c):
    return ans(a, "entity_status") == "Free Zone"


RB_OPTIONS = [
    "Not elected - current basis (Option 3)",
    "Elected - scope A: all assets/liabilities subject to fair value or impairment (Option 1)",
    "Elected - scope B: assets and liabilities held on capital account only (Option 2)",
    "Unknown / not confirmed",
]
RB_CODE = {RB_OPTIONS[0]: "none", RB_OPTIONS[1]: "A", RB_OPTIONS[2]: "B", RB_OPTIONS[3]: "unknown"}


def build_questions() -> list:
    Q = Question
    qs = [
        # ------------------------------------------------------------------ A
        Q("entity_name", "A", "Legal name of the taxable person", "text", why="Used on every output.", evidence="Trade licence"),
        Q("entity_status", "A", "Registration status", "choice", ["Mainland", "Free Zone", "Branch of a foreign company", "Other"],
          why="Free-zone status opens the QFZP questions; branches are not eligible for Small Business Relief.", default="Mainland"),
        Q("free_zone_name", "A", "Name of the Free Zone", "text", relevant=_fz, required=False),
        Q("period_start", "A", "Tax period start", "date", why="Inferred from the GL/TB where possible - confirm.", evidence="Return / registration"),
        Q("period_end", "A", "Tax period end", "date"),
        Q("first_period", "A", "Is this the first Corporate Tax period?", "choice", ["First tax period", "Subsequent tax period", UNK],
          why="The realisation-basis election can only be made in the first tax period.", default="Subsequent tax period"),
        Q("first_period_start", "A", "Start date of the first Corporate Tax period", "date", required=False,
          relevant=_is("first_period", "Subsequent tax period")),
        Q("accounting_framework", "A", "Accounting framework", "choice", ["IFRS", "IFRS for SMEs", "Other"], default="IFRS"),
        Q("accounting_basis", "A", "Basis of accounting", "choice", ["Accrual", "Cash"], default="Accrual",
          why="The realisation-basis election is available to accrual-basis businesses only."),
        Q("tb_status", "A", "Status of the financial statements the TB supports", "choice", ["Draft / unaudited", "Audited", UNK], default="Draft / unaudited",
          why="Audited statements are required for QFZP claims and above a revenue threshold."),
        Q("revenue_current", "A", "Revenue for the current tax period (AED)", "number", why="Prefilled from the P&L; drives SBR and QFZP tests."),
        Q("revenue_previous", "A", "Revenue of the previous relevant tax period(s) (AED; highest single period if several)", "number", default=0.0,
          why="Small Business Relief is tested on the current and previous relevant periods.", evidence="Prior returns / FS"),
        Q("mne_group", "A", "Is the entity part of a Multinational Enterprise Group?", "choice", YNU, default=UNK),
        Q("group_revenue", "A", "Consolidated group revenue (AED)", "number", relevant=_is("mne_group", YES), required=False),
        Q("ct_registered", "A", "Registered for Corporate Tax (TRN)?", "choice", YNU, default=UNK, required=False),
        Q("filing_status", "A", "Filing status for this period", "choice", ["Not yet filed", "Filed", "Revision of a filed return", UNK], default=UNK,
          why="Returns are due nine months after period end; penalties are outside this tool."),
        Q("opening_losses", "A", "Tax losses brought forward (AED)", "number", default=0.0,
          why="Opening losses; utilisation is limited to 75% of taxable income.", evidence="Prior-year computation / return"),
        Q("related_parties", "A", "Related parties and connected persons", "table",
          columns=[{"id": "name", "label": "Name", "kind": "text"}, {"id": "relationship", "label": "Relationship", "kind": "text"},
                   {"id": "jurisdiction", "label": "Jurisdiction", "kind": "text"}, {"id": "nature", "label": "Nature of transactions", "kind": "text"}],
          required=False, why="Used to search the GL for related-party counterparties and to prepare the arm's-length statement."),
        # ------------------------------------------------------------------ B
        Q("realisation_basis", "B", "Realisation basis election", "choice", RB_OPTIONS, default=RB_OPTIONS[3],
          why="Decides whether unrealised gains/losses are taxed. Never applied unless confirmed.", evidence="First-period return showing the election"),
        Q("realisation_evidence", "B", "Is the election documented (made in the first tax period)?", "choice", YNU, default=UNK,
          relevant=lambda a, c: ans(a, "realisation_basis") in (RB_OPTIONS[1], RB_OPTIONS[2]),
          why="The election is irrevocable and must have been made in the first tax period."),
        Q("fv_classification", "B", "Fair value / unrealised accounts: capital or revenue?", "table", rows_from="fv_accounts",
          columns=[{"id": "account", "label": "Account", "kind": "fixed"}, {"id": "amount_aed", "label": "Amount (AED)", "kind": "fixed"},
                   {"id": "class", "label": "Classification", "kind": "choice", "options": ["Capital account", "Revenue account", UNK]}],
          relevant=lambda a, c: bool(c.get("fv_accounts")), why="Scope B only covers capital-account items; the template reports capital and revenue items on different rows."),
        Q("unrealised_fx", "B", "Unrealised part of FX differences in the period (AED; gain positive, loss negative)", "number", default=0.0, required=False,
          relevant=lambda a, c: bool(c.get("fx_accounts")) and ans(a, "realisation_basis") in (RB_OPTIONS[1],),
          why="Only the unrealised part is affected by the election."),
        Q("prev_unrealised", "B", "Prior-period unrealised gains/losses realised in this period", "table",
          columns=[{"id": "asset", "label": "Asset / liability", "kind": "text"}, {"id": "date", "label": "Realisation date", "kind": "date"},
                   {"id": "period", "label": "Tax period deferred", "kind": "text"},
                   {"id": "gain", "label": "Unrealised gain realised (AED)", "kind": "number"}, {"id": "loss", "label": "Unrealised loss realised (AED)", "kind": "number"},
                   {"id": "through_pl", "label": "Previously through income statement?", "kind": "choice", "options": YNU}],
          required=False, relevant=lambda a, c: ans(a, "realisation_basis") in (RB_OPTIONS[1], RB_OPTIONS[2]),
          why="Amounts deferred in an earlier period become taxable when realised.", evidence="Prior computation (UGUL schedule)"),
        Q("transitional", "B", "Does the entity claim transitional rules for pre-existing assets/liabilities?", "choice", YNU, default=UNK,
          why="Never claimed merely because an asset existed before the first tax period."),
        Q("transitional_assets", "B", "Transitional assets/liabilities", "table",
          columns=[{"id": "asset", "label": "Asset / liability", "kind": "text"},
                   {"id": "category", "label": "Category", "kind": "choice", "options": ["Qualifying immovable property", "Qualifying intangible asset", "Qualifying financial asset", "Qualifying financial liability", "Other"]},
                   {"id": "date", "label": "Acquisition date", "kind": "date"}, {"id": "cost", "label": "Historical cost (AED)", "kind": "number"},
                   {"id": "value", "label": "Pre-period valuation / carrying amount (AED)", "kind": "number"}, {"id": "support", "label": "Supporting document", "kind": "text"}],
          required=False, relevant=_is("transitional", YES), evidence="Valuation reports, agreements"),
        Q("other_elections", "B", "Other elections or reliefs that apply", "multi",
          ["Qualifying group relief", "Business restructuring relief", "Tax group", "Participation exemption", "Interest limitation election", "None"],
          required=False, why="Each can change the computation; the tool only flags them - it does not compute group relief or restructuring relief."),
        # ------------------------------------------------------------------ C
        Q("sbr_elect", "C", "Elect Small Business Relief for this period?", "choice", [YES, NO], default=NO,
          relevant=lambda a, c: bool(c.get("sbr_potential")), why="Potential eligibility was identified. Relief is applied only if you elect it and the statutory conditions are confirmed.",
          evidence="Revenue records for all periods"),
        # ------------------------------------------------------------------ D
        Q("qfzp_claimed", "D", "Is the entity claiming Qualifying Free Zone Person status?", "choice", YNU, default=UNK,
          relevant=_fz, why="A free-zone licence alone never gives the 0% rate."),
        Q("qfzp_activities", "D", "Qualifying activities performed", "multi",
          ["Holding of shares/securities for investment", "Treasury and financing to related parties", "Distribution in/from a Designated Zone",
           "Manufacturing / processing", "Qualifying intellectual property", "Commodities trading", "Other", "None"],
          relevant=_is("qfzp_claimed", YES), required=False),
        Q("qfzp_substance", "D", "Adequate substance (employees, premises, core income-generating activities) evidenced?", "choice", YNU, default=UNK,
          relevant=_is("qfzp_claimed", YES), evidence="Employment contracts, lease, org chart"),
        Q("qfzp_audited", "D", "Audited financial statements available for this period?", "choice", YNU, default=UNK, relevant=_is("qfzp_claimed", YES)),
        Q("qfzp_domestic_pe", "D", "Mainland or other domestic permanent establishment / income from natural persons?", "choice", YNU, default=UNK,
          relevant=_is("qfzp_claimed", YES)),
        Q("income_classification", "D", "Classify each income account", "table", rows_from="income_accounts",
          columns=[{"id": "account", "label": "Income account", "kind": "fixed"}, {"id": "amount_aed", "label": "Amount (AED)", "kind": "fixed"},
                   {"id": "class", "label": "Classification", "kind": "choice",
                    "options": ["Qualifying income", "Non-qualifying income", "Excluded activity", "Exempt income", UNK]}],
          relevant=_is("qfzp_claimed", YES), why="Unknown items are treated as non-qualifying in the tests."),
        Q("qfzp_direct_q", "D", "Operating expenses directly attributable to qualifying income (AED)", "number", default=0.0, required=False, relevant=_is("qfzp_claimed", YES)),
        Q("qfzp_direct_nq", "D", "Operating expenses directly attributable to non-qualifying income (AED)", "number", default=0.0, required=False, relevant=_is("qfzp_claimed", YES)),
        # ------------------------------------------------------------------ E
        Q("dividends", "E", "Dividend income: payer details", "table", rows_from="dividend_accounts",
          columns=[{"id": "account", "label": "Account", "kind": "fixed"}, {"id": "amount_aed", "label": "Amount (AED)", "kind": "fixed"},
                   {"id": "payer", "label": "Payer", "kind": "text"},
                   {"id": "jurisdiction", "label": "Payer type", "kind": "choice", "options": ["UAE resident juridical person", "Foreign company", UNK]},
                   {"id": "ownership", "label": "Ownership %", "kind": "number"}, {"id": "cost", "label": "Acquisition cost (AED)", "kind": "number"},
                   {"id": "months", "label": "Months held", "kind": "number"}, {"id": "subject_tax", "label": "Payer subject to ≥9% tax?", "kind": "choice", "options": YNU}],
          relevant=lambda a, c: bool(c.get("dividend_accounts")), evidence="Share certificates, dividend vouchers, investee tax status"),
        Q("disposals", "E", "Gains/losses on share disposals: investee details", "table", rows_from="disposal_accounts",
          columns=[{"id": "account", "label": "Account", "kind": "fixed"}, {"id": "amount_aed", "label": "Amount (AED)", "kind": "fixed"},
                   {"id": "payer", "label": "Investee", "kind": "text"},
                   {"id": "jurisdiction", "label": "Investee type", "kind": "choice", "options": ["UAE resident juridical person", "Foreign company", UNK]},
                   {"id": "ownership", "label": "Ownership %", "kind": "number"}, {"id": "cost", "label": "Acquisition cost (AED)", "kind": "number"},
                   {"id": "months", "label": "Months held", "kind": "number"}, {"id": "subject_tax", "label": "Investee subject to ≥9% tax?", "kind": "choice", "options": YNU}],
          relevant=lambda a, c: bool(c.get("disposal_accounts")), evidence="Sale agreements, share register"),
        Q("loans", "E", "Loans and interest: counterparties", "table",
          columns=[{"id": "counterparty", "label": "Counterparty", "kind": "text"},
                   {"id": "direction", "label": "Direction", "kind": "choice", "options": ["Loan given", "Loan received"]},
                   {"id": "related", "label": "Related party?", "kind": "choice", "options": YNU},
                   {"id": "rate", "label": "Interest rate %", "kind": "number"},
                   {"id": "agreement", "label": "Written agreement?", "kind": "choice", "options": YNU}],
          required=False, relevant=lambda a, c: bool(c.get("has_interest")), evidence="Loan agreements"),
        Q("entertainment_staff_pct", "E", "Share of entertainment spend that was for staff only (0-100%)", "number", default=0.0, required=False,
          relevant=lambda a, c: bool(c.get("has_entertainment")), why="Staff-only entertainment is treated differently from client entertainment."),
        Q("donations_qpbe", "E", "Were all donations made to Qualifying Public Benefit Entities?", "choice", ["All to qualifying entities", "Not all / none", UNK], default=UNK,
          relevant=lambda a, c: bool(c.get("has_donations")), evidence="QPBE listing / receipts"),
        Q("fines_compensation", "E", "Part of fines/penalties that is compensation for damages or breach of contract (AED)", "number", default=0.0, required=False,
          relevant=lambda a, c: bool(c.get("has_fines"))),
        Q("provisions", "E", "Provision movement", "table",
          columns=[{"id": "name", "label": "Provision", "kind": "text"}, {"id": "opening", "label": "Opening (AED)", "kind": "number"},
                   {"id": "made", "label": "Made in year (AED)", "kind": "number"}, {"id": "utilised", "label": "Utilised (AED)", "kind": "number"},
                   {"id": "adjustments", "label": "Adjustments / reversals (AED)", "kind": "number"}],
          required=False, relevant=lambda a, c: bool(c.get("has_provisions")), evidence="Provision schedule"),
        Q("foreign_taxes", "E", "Foreign taxes / withholding tax suffered", "table",
          columns=[{"id": "country", "label": "Country", "kind": "text"}, {"id": "nature", "label": "Nature of income", "kind": "text"},
                   {"id": "income", "label": "Income (AED)", "kind": "number"}, {"id": "rate", "label": "Rate %", "kind": "number"},
                   {"id": "paid", "label": "Tax paid (AED)", "kind": "number"},
                   {"id": "proof", "label": "Proof of payment?", "kind": "choice", "options": YNU},
                   {"id": "exempt_income", "label": "Is this income exempt in the UAE (e.g. participation exemption)?", "kind": "choice", "options": YNU},
                   {"id": "expensed", "label": "Expensed in P&L (AED)", "kind": "number"}],
          required=False, evidence="Tax certificates / withholding vouchers"),
        Q("loss_transfer_in", "E", "Tax losses received from a group company this period (AED)", "number", default=0.0, required=False,
          relevant=lambda a, c: "Qualifying group relief" in (ans(a, "other_elections") or []) or "Tax group" in (ans(a, "other_elections") or [])),
        Q("manual_adjustments", "E", "Additional adjustments identified by the reviewer", "table",
          columns=[{"id": "row", "label": "Computation row", "kind": "choice", "options": []},      # options filled by the engine
                   {"id": "description", "label": "Description", "kind": "text"}, {"id": "amount", "label": "Amount (AED)", "kind": "number"},
                   {"id": "reason", "label": "Reason", "kind": "text"}, {"id": "support", "label": "Supporting reference", "kind": "text"}],
          required=False, why="Anything the automated analysis cannot determine, e.g. capital expenditure expensed, expenses without documents."),
        # ------------------------------------------------------------------ F
        Q("conf_documentation", "F", "Management has been informed of the requirement to keep supporting documents for all expenses", "choice", YNU, default=UNK, required=False),
        Q("conf_business_purpose", "F", "Management confirms all expenses were incurred wholly and exclusively for business purposes", "choice", YNU, default=UNK, required=False),
        Q("conf_disallowed", "F", "Management confirms no expenses of a disallowable nature are recorded other than those already adjusted", "choice", YNU, default=UNK, required=False),
        Q("conf_exempt_income", "F", "Management confirms the exempt-income position stated in this computation", "choice", YNU, default=UNK, required=False),
        Q("conf_arms_length", "F", "Management confirms related-party transactions are at arm's length", "choice", YNU, default=UNK, required=False),
        Q("conf_subsidiaries", "F", "Management confirms the position on investments in subsidiaries (e.g. FS basis and Ministerial Decision 134 of 2023)", "choice", YNU, default=UNK, required=False),
    ]
    return qs


def visible(answers: dict, ctx: dict) -> list:
    return [q for q in build_questions() if q.relevant is None or q.relevant(answers, ctx)]


def question_map() -> dict:
    return {q.id: q for q in build_questions()}


def unanswered(answers: dict, ctx: dict) -> list:
    out = []
    for q in visible(answers, ctx):
        if not q.required:
            continue
        v = ans(answers, q.id)
        if v in (None, "", UNK, RB_OPTIONS[3]) or (isinstance(v, list) and not v):
            out.append(q)
    return out


def prefill(answers: dict, ctx: dict) -> dict:
    """Fill gaps from data without overwriting anything the user entered. Returns the updated copy."""
    a = dict(answers)
    a["_meta"] = meta = dict(a.get("_meta", {}))          # copy: never mutate the caller's metadata

    def put(qid, val, why):
        if qid not in a or a[qid] in (None, ""):
            a[qid] = val
            meta[qid] = {"source": "prefilled", "confirmed": False, "note": why}

    if ctx.get("entity_guess"):
        put("entity_name", ctx["entity_guess"], "Guessed from the title text in the TB file")
    if ctx.get("period_start"):
        put("period_start", ctx["period_start"], ctx.get("period_note", ""))
    if ctx.get("period_end"):
        put("period_end", ctx["period_end"], ctx.get("period_note", ""))
    if ctx.get("revenue_aed") is not None:
        put("revenue_current", round(ctx["revenue_aed"], 2), "Revenue accounts in the AED P&L")
    for q in build_questions():
        if q.default is not None and q.id not in a:
            a[q.id] = q.default
            meta[q.id] = {"source": "default", "confirmed": False, "note": "Default - not yet confirmed"}
    return a
