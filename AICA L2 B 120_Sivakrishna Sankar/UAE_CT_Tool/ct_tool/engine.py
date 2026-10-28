"""Tax computation engine.

Principles (see project brief s.12):
 * The engine PROPOSES adjustments from the data and the questionnaire. It never confirms one.
 * Only adjustments with status 'Confirmed' enter the computation. Proposed items are reported
   separately together with their potential impact.
 * Elections, reliefs and exemptions are applied only where the questionnaire says so AND the
   evidence checks pass; otherwise the adjustment is 'blocked' (it can be confirmed only with an
   explicit, recorded override).
 * Every parameter comes from config/rules.json; nothing is hard-coded to a tax year.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from typing import Optional

from .fx import TranslationResult
from .mapping import fs_lines
from .models import load_json
from .questionnaire import ans, RB_OPTIONS, RB_CODE, YES, NO, UNK

# --------------------------------------------------------------------------------------------
# Computation rows (labels / template row numbers of the supplied template)
# --------------------------------------------------------------------------------------------
ROWS = {
    "d_unrealised_capital": (14, "B", "Unrealised gains on capital items (Options 1 & 2)"),
    "d_unrealised_revenue": (15, "B", "Unrealised gains on revenue items (Option 1)"),
    "d_qual_activity": (16, "B", "Income from Qualifying Activity (Holding of shares for investment purposes)"),
    "d_dividends_resident": (17, "B", "Dividends & profit distributions received from resident juridical person"),
    "d_participating": (18, "B", "Income from Participating Interest (Dividend / Capital Gains)"),
    "d_foreign_pe": (19, "B", "Income from foreign Permanent Establishment (subject to election)"),
    "d_shipping": (20, "B", "Income from operating aircraft/ships in international transportation"),
    "d_qgr": (21, "B", "Gain from transfers within a qualifying group"),
    "d_restructuring": (22, "B", "Gain from qualified business restructuring"),
    "d_other_md134": (23, "B", "Other adjustments to accounting income specified in MD No. 134 (deduction)"),
    "a_unreal_loss_capital": (28, "C", "Unrealised loss on capital items (Options 1 & 2)"),
    "a_unreal_loss_revenue": (29, "C", "Unrealised loss on revenue items (Option 1)"),
    "a_qual_loss": (30, "C", "Loss from Qualifying Activity (Holding of shares for investment purposes)"),
    "a_capital_exp": (31, "C", "Expenses of capital nature"),
    "a_exempt_exp": (32, "C", "Expenses incurred in deriving Exempt Income"),
    "a_non_business": (33, "C", "Expenses not incurred for the purposes of the Taxable Person's Business"),
    "a_losses_non_business": (34, "C", "Losses not connected with or arising out of the Taxable Person's Business"),
    "a_interest_excess": (35, "C", "Interest charged in excess of allowable limit"),
    "a_nondeduct_interest": (36, "C", "Non-deductible interest"),
    "a_entertainment": (37, "C", "50% of entertainment, amusement or recreation expenses"),
    "a_donations": (38, "C", "Donations, grants or gifts made to a non-Qualifying Public Benefit Entity"),
    "a_fines": (39, "C", "Fines and penalties, other than amounts awarded as compensation"),
    "a_no_docs": (40, "C", "Expenses without Supporting Documents"),
    "a_dividends_owner": (41, "C", "Dividends, profit distributions or benefits of a similar nature paid to an owner"),
    "a_withdrawals": (42, "C", "Amounts withdrawn from the business by a natural person who is a Taxable Person or partner"),
    "a_ct": (43, "C", "Corporate Tax imposed on a Taxable Person as per the applicable Law"),
    "a_vat": (44, "C", "Input Value Added Tax incurred that is recoverable as per the applicable Law"),
    "a_foreign_tax": (45, "C", "Tax on income imposed on the Taxable Person outside UAE"),
    "a_rp_non_arm": (46, "C", "Adjustments for Related Party / Connected Person transactions not at arm's length"),
    "a_other_md134": (47, "C", "Other adjustments to accounting income specified in MD No. 134 (addition)"),
    "a_cd": (48, "C", "Any other expenses that may be specified in a Cabinet Decision"),
    "o_prev_gain": (53, "O+", "Amount of previously unrealised gains which have been realised in the current Tax Period"),
    "o_prev_loss": (54, "O-", "Amount of previously unrealised losses which have been realised in the current Tax Period"),
}
DISALLOWED_SHEET_ROWS = ["a_entertainment", "a_donations", "a_fines", "a_non_business", "a_no_docs", "a_capital_exp", "a_rp_non_arm",
                         "a_other_md134", "a_withdrawals", "a_vat", "a_cd", "a_losses_non_business"]


def params() -> dict:
    return load_json("rules.json")["params"]


# --------------------------------------------------------------------------------------------
@dataclass
class Adjustment:
    adj_id: str
    row: str
    description: str
    amount: float
    accounts: list = field(default_factory=list)       # [[code, name], ...]
    reason: str = ""
    rule_ref: str = ""
    status: str = "Proposed"                            # Proposed | Confirmed | Rejected
    blocking: str = ""
    support_ref: str = ""
    mgmt_response: str = ""
    reviewer: str = ""
    override_note: str = ""
    origin: str = "auto"
    gl_refs: list = field(default_factory=list)
    category: str = ""
    docs_needed: list = field(default_factory=list)
    auto_amount: float = 0.0                            # amount as generated, before any user override

    def __post_init__(self):
        self.auto_amount = self.amount

    @property
    def section(self) -> str:
        return ROWS[self.row][1]

    @property
    def report_status(self) -> str:
        if self.status == "Confirmed":
            return "Confirmed"
        if self.status == "Rejected":
            return "Rejected"
        return "Information required" if self.blocking else "Potential adjustment"


@dataclass
class Computation:
    rows: dict
    A: float
    B: float
    C: float
    o_gain: float
    o_loss: float
    D: float
    relief_cf: float
    relief_group: float
    E: float
    basis: str                      # ordinary | QFZP | SBR
    tax_0: float
    tax_9: float
    credit: float
    payable: float
    etr: Optional[float]
    q_taxable: Optional[float] = None
    nq_taxable: Optional[float] = None
    loss_opening: float = 0.0
    loss_closing: float = 0.0
    notes: list = field(default_factory=list)
    qfzp: dict = field(default_factory=dict)
    sbr: dict = field(default_factory=dict)
    interest_test: dict = field(default_factory=dict)
    nil_band_applied: float = 0.0


# --------------------------------------------------------------------------------------------
# Context for the questionnaire
# --------------------------------------------------------------------------------------------
def questionnaire_context(tr: TranslationResult, st, tb=None, gl=None, fx=None, answers: Optional[dict] = None) -> dict:
    lines = fs_lines()
    by_line = {}
    for a in tr.accounts:
        by_line.setdefault(a.line, []).append(a)

    def accts(*keys):
        return [a for k in keys for a in by_line.get(k, [])]

    ctx = {
        "fv_accounts": [(a.account.code or a.account.name, a.account.name, -a.net_aed) for a in accts("P_FV")],
        "fx_accounts": [a.account.name for a in accts("P_FX")],
        "dividend_accounts": [(a.account.code or a.account.name, a.account.name, -a.net_aed) for a in accts("P_DIV")],
        "disposal_accounts": [(a.account.code or a.account.name, a.account.name, -a.net_aed) for a in accts("P_GAIN_REAL")],
        "income_accounts": [(a.account.code or a.account.name, a.account.name, -a.net_aed) for a in tr.accounts
                            if lines[a.line]["statement"] == "PL" and a.net_aed < 0],
        "has_interest": bool(accts("P_FIN", "P_INT_INC", "L_ACCR_INT", "L_BORR", "A_LOANS")),
        "has_entertainment": bool([a for a in accts("P_ENT") if a.net_aed > 0]),
        "has_donations": bool(accts("P_DON")),
        "has_fines": bool(accts("P_FINES")),
        "has_provisions": bool(accts("P_PROV", "L_PROV")),
        "revenue_aed": st.revenue,
    }
    if tb is not None:
        from .extract import entity_guess
        ctx["entity_guess"] = entity_guess(tb)
    dates = []
    if gl and gl.lines:
        dates = sorted(l.date for l in gl.lines if l.date)
    if fx and fx.period_start and fx.period_end:
        ctx["period_start"], ctx["period_end"] = fx.period_start, fx.period_end
        ctx["period_note"] = "From the currency step - confirm"
    elif dates:
        ctx["period_start"], ctx["period_end"] = dates[0], dates[-1]
        ctx["period_note"] = "Inferred from the first and last GL dates - confirm"
    a = answers or {}
    ctx["sbr_potential"] = sbr_assessment(a, st, ctx)["potential"]
    return ctx


# --------------------------------------------------------------------------------------------
# Small Business Relief
# --------------------------------------------------------------------------------------------
def sbr_assessment(answers: dict, st, ctx: Optional[dict] = None) -> dict:
    p = params()
    rev_cur = ans(answers, "revenue_current", st.revenue if st else 0.0) or 0.0
    rev_prev = ans(answers, "revenue_previous", 0.0) or 0.0
    reasons, fail = [], []
    thr = p["sbr_revenue_threshold"]
    # the relief is tested on the revenue of the current and each previous relevant period (confirm against the MD text)
    if rev_cur > thr:
        fail.append(f"Current-period revenue AED {rev_cur:,.0f} exceeds AED {thr:,.0f}.")
    if rev_prev > thr:
        fail.append(f"Revenue of a previous relevant period (AED {rev_prev:,.0f}) exceeds AED {thr:,.0f}; eligibility is lost once the threshold is breached.")
    if ans(answers, "qfzp_claimed") == YES:
        fail.append("A Qualifying Free Zone Person cannot elect Small Business Relief.")
    if ans(answers, "entity_status") == "Branch of a foreign company":
        fail.append("A branch of a foreign company is not a Resident Person - eligibility is doubtful.")
    if ans(answers, "mne_group") == YES:
        gr = ans(answers, "group_revenue", 0.0) or 0.0
        if gr >= p["sbr_mne_revenue_threshold"]:
            fail.append("Member of an MNE group with consolidated revenue at or above the threshold.")
        elif not gr:
            reasons.append("MNE group revenue not provided.")
    elif ans(answers, "mne_group") in (None, UNK):
        reasons.append("MNE group status not confirmed.")
    pe = ans(answers, "period_end")
    if pe and pe > p["sbr_last_period_end"]:
        fail.append(f"Relief is configured only for periods ending on or before {p['sbr_last_period_end']}.")
    potential = not fail
    other_inc = 0.0
    if st is not None:
        other_inc = sum(r.amount for r in st.pl_rows if r.kind == "line" and r.amount and r.line_key not in ("P_REV", "P_COS") and r.amount > 0
                        and r.line_key in ("P_DIV", "P_INT_INC", "P_GAIN_REAL", "P_FV", "P_OTHER_INC"))
    if other_inc > 0:
        reasons.append(f"Revenue is taken from the 'Revenue' lines only; other income of AED {other_inc:,.0f} (dividends, interest, gains) is excluded - confirm what counts as revenue for this test.")
    return {"potential": potential, "failures": fail, "open": reasons, "revenue_current": rev_cur, "revenue_previous": rev_prev}


# --------------------------------------------------------------------------------------------
# Adjustment generation
# --------------------------------------------------------------------------------------------
def _rb(answers) -> str:
    return RB_CODE.get(ans(answers, "realisation_basis", RB_OPTIONS[3]), "unknown")


def _table(answers, qid) -> list:
    v = answers.get(qid)
    if isinstance(v, dict) and "value" in v:
        v = v["value"]
    return [r for r in (v or []) if isinstance(r, dict)]


def _num(x, d=0.0):
    try:
        if x in (None, ""):
            return d
        return float(x)
    except (TypeError, ValueError):
        return d


def build_adjustments(tr: TranslationResult, review, answers: dict, option: Optional[str] = None) -> tuple:
    """Return (adjustments, open_items). `option` overrides the realisation-basis code for scenario analysis."""
    P = params()
    lines = fs_lines()
    adjs, open_items = [], []
    rb = option or _rb(answers)
    by_line = {}
    for a in tr.accounts:
        by_line.setdefault(a.line, []).append(a)

    def add(row, desc, amt, accts, reason, rule, blocking="", docs=None, cat="", gl_refs=None, key=None):
        amt = round(amt, 2)
        if abs(amt) < 0.005:
            return
        aid = f"{row}:{key or (accts[0][0] or accts[0][1] if accts else desc)}"
        adjs.append(Adjustment(aid, row, desc, amt, [list(x) for x in accts], reason, rule, blocking=blocking,
                               docs_needed=docs or [], category=cat, gl_refs=gl_refs or []))

    def oi(topic, text, status="Information required", docs=None):
        open_items.append({"topic": topic, "item": text, "status": status, "documents": docs or []})

    # ------------------------------------------------------------ realisation basis
    election_ok = True
    block_rb = ""
    if rb == "unknown":
        oi("Realisation basis", "Election status not confirmed - the computation is shown on the current basis (no election) until it is confirmed.",
           "Information required", ["First-period return / election evidence"])
    if rb in ("A", "B") and option is None:
        ev = ans(answers, "realisation_evidence", UNK)
        if ev != YES:
            block_rb = "Election evidence (made in the first tax period) is not confirmed."
            oi("Realisation basis", "Evidence that the election was made in the first tax period is required before the deduction can be confirmed.",
               "Information required", ["First-period return showing the election"])
        if ans(answers, "accounting_basis") == "Cash":
            block_rb = "The election is available only to accrual-basis businesses."
        if ans(answers, "first_period") == "Subsequent tax period" and ev != YES:
            pass
    fv_rows = {r.get("account"): r for r in _table(answers, "fv_classification")}
    if rb in ("A", "B"):
        for a in by_line.get("P_FV", []):
            code = a.account.code or a.account.name
            cls = (fv_rows.get(code) or fv_rows.get(a.account.name) or {}).get("class", UNK)
            is_cap = cls == "Capital account"
            is_rev = cls == "Revenue account"
            gain = -a.net_aed
            if rb == "B" and not is_cap:
                if cls == UNK or cls is None:
                    oi("Realisation basis (scope B)", f"'{a.account.name}': capital or revenue classification required - under scope B only capital-account items are covered.",
                       "Information required", ["Investment classification memo"])
                continue
            row = None
            if gain > 0:
                row = "d_unrealised_capital" if is_cap else "d_unrealised_revenue"
            else:
                row = "a_unreal_loss_capital" if is_cap else "a_unreal_loss_revenue"
            blocking = block_rb
            if cls == UNK:
                blocking = (blocking + " " if blocking else "") + "Capital/revenue classification not provided."
            add(row, f"{'Unrealised gain' if gain > 0 else 'Unrealised loss'} - {a.account.name}", abs(gain), [(a.account.code, a.account.name)],
                f"Realisation basis (scope {rb}): unrealised {'gain deducted' if gain > 0 else 'loss added back'}; "
                f"classified {cls}. Amount per P&L account (AED).", "RB-01", blocking, ["Fair value statements", "Election evidence"], "Realisation basis")
        # FX
        ufx = _num(ans(answers, "unrealised_fx", 0.0))
        if rb == "A" and abs(ufx) > 0.005:
            if ufx > 0:
                add("d_unrealised_revenue", "Unrealised FX gain", ufx, [("", "Exchange differences")], "Unrealised FX gain removed under scope A.", "RB-01", block_rb, cat="Realisation basis", key="fx")
            else:
                add("a_unreal_loss_revenue", "Unrealised FX loss", -ufx, [("", "Exchange differences")], "Unrealised FX loss added back under scope A.", "RB-01", block_rb, cat="Realisation basis", key="fx")
        elif rb == "A" and by_line.get("P_FX"):
            oi("Foreign exchange", "Split of FX differences into realised and unrealised is needed under scope A.", "Information required", ["FX analysis"])
        # provisions (scope A only: impairment items subject to fair value/impairment accounting)
        provs = _table(answers, "provisions")
        if rb == "A":
            total_disallow = 0.0
            for r in provs:
                nm = str(r.get("name", "")).lower()
                if any(w in nm for w in ("indemn", "end of service", "gratuity", "eosb")):
                    continue
                total_disallow += _num(r.get("made")) - _num(r.get("adjustments"))
            if total_disallow > 0:
                add("a_unreal_loss_revenue", "Provisions / impairments charged in the year", total_disallow, [("", "Provision schedule")],
                    "Under scope A impairments of revenue items are unrealised losses; amount = provisions made less adjustments "
                    "(end-of-service/indemnity provisions excluded), as in the supplied template.", "RB-01", block_rb, ["Provision schedule"], "Realisation basis", key="prov")
            elif by_line.get("P_PROV") and not provs:
                for a in by_line["P_PROV"]:
                    if a.net_aed > 0:
                        add("a_unreal_loss_revenue", f"Provision / impairment charge - {a.account.name}", a.net_aed, [(a.account.code, a.account.name)],
                            "Charge per P&L account; confirm against the provision schedule.", "RB-01", block_rb or "Provision schedule not provided.", ["Provision schedule"], "Realisation basis")
        # prior-period unrealised gains/losses realised now
        for i, r in enumerate(_table(answers, "prev_unrealised")):
            g, l = _num(r.get("gain")), _num(r.get("loss"))
            if g > 0:
                add("o_prev_gain", f"Previously deferred gain realised - {r.get('asset', '')}", g, [("", r.get("asset", ""))],
                    "A gain deferred in an earlier period was realised in this period.", "RB-01", "" if r.get("through_pl") == YES else "Confirm the gain was previously recognised in the income statement.",
                    ["Prior-period computation"], "Realisation basis", key=f"prev{i}")
            if l > 0:
                add("o_prev_loss", f"Previously deferred loss realised - {r.get('asset', '')}", l, [("", r.get("asset", ""))],
                    "A loss deferred in an earlier period was realised in this period.", "RB-01", "" if r.get("through_pl") == YES else "Confirm the loss was previously recognised in the income statement.",
                    ["Prior-period computation"], "Realisation basis", key=f"prevl{i}")
    elif rb in ("none", "unknown") and by_line.get("P_FV"):
        oi("Realisation basis", "Fair value movements are included in taxable income on the current basis. Consider whether an election was made in the first tax period.",
           "Technical review required")

    # ------------------------------------------------------------ dividends and share gains (exempt income)
    p_min_own, p_min_cost, p_months = P["participation_min_ownership_pct"], P["participation_min_cost_aed"], P["participation_min_holding_months"]

    def exempt_rows(line, qid, kind):
        rows = {r.get("account"): r for r in _table(answers, qid)}
        for a in by_line.get(line, []):
            code = a.account.code or a.account.name
            r = rows.get(code) or rows.get(a.account.name) or {}
            amt = -a.net_aed
            jur = r.get("jurisdiction", UNK)
            if not r:
                oi("Exempt income", f"'{a.account.name}': payer/investee details required to assess exemption.", "Information required",
                   ["Share register", "Investee tax status"])
                continue
            if kind == "div" and jur == "UAE resident juridical person" and amt > 0:
                add("d_dividends_resident", f"Dividend from UAE resident juridical person - {a.account.name}", amt, [(a.account.code, a.account.name)],
                    f"Payer: {r.get('payer', '')} (UAE resident juridical person).", "PE-01", "", ["Dividend voucher"], "Exempt income")
                continue
            own, cost, mon, sub = _num(r.get("ownership")) / 100.0, _num(r.get("cost")), _num(r.get("months")), r.get("subject_tax", UNK)
            missing = []
            if not (own >= p_min_own or cost >= p_min_cost):
                missing.append(f"ownership {own:.1%} / cost AED {cost:,.0f} below the minimum")
            if mon < p_months:
                missing.append(f"holding period {mon:.0f} months (minimum {p_months})")
            if sub != YES:
                missing.append("subject-to-tax condition not confirmed")
            if jur == UNK:
                missing.append("payer type unknown")
            label = "Dividend" if kind == "div" else ("Gain on disposal" if amt > 0 else "Loss on disposal")
            if not missing:
                if amt > 0:
                    add("d_participating", f"{label} - participating interest - {a.account.name}", amt, [(a.account.code, a.account.name)],
                        "All participation-exemption conditions answered 'yes'.", "PE-01", "", ["Share register", "Acquisition documents"], "Exempt income")
                elif amt < 0:
                    add("a_other_md134", f"{label} - participating interest - {a.account.name}", -amt, [(a.account.code, a.account.name)],
                        "Loss on a Participating Interest is not deductible where the exemption applies.", "PE-01", "", ["Share register"], "Exempt income", key="loss")
            else:
                oi("Exempt income", f"'{a.account.name}': exemption not applied - " + "; ".join(missing) + ".", "Information required" if "unknown" in " ".join(missing) or "not confirmed" in " ".join(missing) else "Technical review required",
                   ["Share register", "Investee tax status", "Acquisition documents"])

    exempt_rows("P_DIV", "dividends", "div")
    exempt_rows("P_GAIN_REAL", "disposals", "disp")
    if any(a.row in ("d_dividends_resident", "d_participating") for a in adjs):
        oi("Exempt income", "Expenses incurred in deriving exempt income (e.g. interest on funding) are non-deductible - quantify and enter under 'Additional adjustments'.",
           "Information required", ["Funding and cost analysis"])

    # ------------------------------------------------------------ risk-flag driven adjustments
    staff_pct = _num(ans(answers, "entertainment_staff_pct", 0.0)) / 100.0
    fines_comp = _num(ans(answers, "fines_compensation", 0.0))
    for f in review.flags:
        if not f.adj_key or not f.proposed_adjustment or f.proposed_adjustment <= 0:
            continue
        amt = f.proposed_adjustment
        blocking = ""
        if f.adj_key == "a_entertainment":
            amt = f.amount_aed * (1 - staff_pct) * (f.adj_pct or P["entertainment_disallow_pct"])
            reason = "50% of entertainment (net of any staff-only share) proposed - restriction applies to customers, shareholders, suppliers and business partners."
        elif f.adj_key == "a_donations":
            if ans(answers, "donations_qpbe") == "All to qualifying entities":
                continue
            blocking = "Qualifying Public Benefit Entity status of recipients not confirmed." if ans(answers, "donations_qpbe") != "Not all / none" else ""
            reason = "Donations proposed as non-deductible unless the recipient is a Qualifying Public Benefit Entity."
        elif f.adj_key == "a_fines":
            amt = max(0.0, f.amount_aed - fines_comp)
            reason = "Fines and penalties proposed as non-deductible except amounts that are compensation for damages or breach of contract."
        elif f.adj_key == "a_ct":
            reason = "Corporate Tax expense is non-deductible; added back."
        elif f.adj_key == "a_foreign_tax":
            if any(_num(r.get("expensed")) > 0 for r in _table(answers, "foreign_taxes")):
                continue                      # amounts are taken from the foreign-tax table instead (avoids double counting)
            reason = "Foreign/withholding tax expensed is non-deductible; any credit needs the foreign-taxes table completed with proof of payment."
            oi("Foreign tax credit", f"'{f.name}': complete the foreign-taxes table (country, tax paid, proof of payment) to assess a credit.",
               "Information required", ["Foreign tax certificates"])
        else:
            blocking = "Business purpose to be confirmed."
            reason = f"Proposed from the account name ('{f.category_label}') - not confirmed."
        add(f.adj_key, f"{f.category_label} - {f.name}", amt, [(f.code, f.name)], reason, f.rule_ref, blocking, f.documents, f.category_label, f.gl_refs)

    # ------------------------------------------------------------ interest limitation
    it = interest_test(tr, answers)
    if it["excess"] > 0:
        add("a_interest_excess", "Net interest above the allowable limit", it["excess"], [("", "Finance costs / interest income")],
            f"Net interest AED {it['net_interest']:,.0f} exceeds the limit of AED {it['threshold']:,.0f}.", "INT-01",
            "Tax EBITDA is approximated - confirm.", ["Interest and EBITDA workings"], "Interest limitation", key="limit")

    # ------------------------------------------------------------ foreign taxes
    for i, r in enumerate(_table(answers, "foreign_taxes")):
        ex = _num(r.get("expensed"))
        if ex > 0:
            add("a_foreign_tax", f"Foreign tax expensed - {r.get('country', '')} {r.get('nature', '')}", ex, [("", r.get("country", ""))],
                "Tax on income imposed outside the UAE is non-deductible (a credit may be claimed instead).", "NDE-01", "", ["Tax certificate"], "Foreign tax", key=f"ft{i}")
        if _num(r.get("paid")) > 0 and r.get("proof") != YES:
            oi("Foreign tax credit", f"{r.get('country', '')}: proof of payment is required before a credit can be claimed.", "Information required", ["Tax payment proof"])
        elif _num(r.get("paid")) > 0 and r.get("exempt_income") != NO:
            oi("Foreign tax credit", f"{r.get('country', '')}: no credit is given until it is confirmed that the related income is NOT exempt in the UAE "
               "(a credit is limited to UAE tax on the same income).", "Information required" if r.get("exempt_income", UNK) == UNK else "Technical review required", ["Income analysis"])

    # ------------------------------------------------------------ provisions outside scope A
    if rb != "A" and (by_line.get("P_PROV") or _table(answers, "provisions")):
        oi("Provisions", "Provisions/impairments: confirm deductibility under the elected basis; no adjustment has been proposed.", "Technical review required", ["Provision schedule"])

    # ------------------------------------------------------------ related parties
    if ans(answers, "conf_arms_length") != YES and (by_line.get("A_RP") or by_line.get("L_RP") or _table(answers, "related_parties") or by_line.get("A_LOANS")):
        oi("Related parties", "Management confirmation that related-party and connected-person transactions are at arm's length is not on file.",
           "Information required", ["Related-party list", "Pricing support"])
    if ans(answers, "conf_exempt_income") != YES and (by_line.get("P_DIV") or by_line.get("P_GAIN_REAL")):
        oi("Exempt income", "Management has not confirmed the exempt-income position (dividends and share gains exist in the TB).", "Information required")
    if ans(answers, "conf_disallowed") != YES:
        oi("Disallowed expenses", "Management has not confirmed that no other expenses of a disallowable nature are recorded.", "Information required")

    # ------------------------------------------------------------ manual adjustments
    for i, r in enumerate(_table(answers, "manual_adjustments")):
        row, amt = r.get("row"), _num(r.get("amount"))
        if row in ROWS and amt > 0:
            adjs.append(Adjustment(f"manual:{i}", row, r.get("description") or ROWS[row][2], round(amt, 2), [["", "Manual"]],
                                   r.get("reason", ""), "", origin="manual", support_ref=r.get("support", ""), category="Manual"))
    # de-duplicate ids
    seen = {}
    for a in adjs:
        if a.adj_id in seen:
            seen[a.adj_id] += 1
            a.adj_id += f"#{seen[a.adj_id]}"
        else:
            seen[a.adj_id] = 1
    return adjs, open_items


def apply_decisions(adjs: list, decisions: dict) -> list:
    """Apply stored user decisions. Returns a list of warnings (e.g. confirmation blocked)."""
    warns = []
    for a in adjs:
        d = decisions.get(a.adj_id)
        if not d:
            continue
        a.mgmt_response = d.get("mgmt_response", a.mgmt_response)
        a.reviewer = d.get("reviewer", a.reviewer)
        a.support_ref = d.get("support_ref", a.support_ref)
        a.override_note = d.get("override_note", "")
        if d.get("amount") not in (None, ""):
            a.amount = round(float(d["amount"]), 2)
        st = d.get("status", "Proposed")
        if st == "Confirmed" and a.blocking and not a.override_note.strip():
            warns.append(f"{a.description}: cannot be confirmed - {a.blocking} (enter an override note to confirm anyway).")
            a.status = "Proposed"
        else:
            a.status = st
    return warns


# --------------------------------------------------------------------------------------------
# Tests: interest, QFZP
# --------------------------------------------------------------------------------------------
def interest_test(tr: TranslationResult, answers: dict) -> dict:
    P = params()
    exp = sum(a.net_aed for a in tr.accounts if a.line == "P_FIN" and a.net_aed > 0)
    inc = -sum(a.net_aed for a in tr.accounts if a.line == "P_INT_INC")
    dep = sum(a.net_aed for a in tr.accounts if a.line == "P_DEP")
    profit = -sum(a.net_aed for a in tr.accounts if fs_lines()[a.line]["statement"] == "PL")
    net_int = exp - inc
    ebitda = profit + exp - inc + dep       # approximation - the legislated tax EBITDA differs
    thr = max(P["interest_threshold_amount"], P["interest_ebitda_pct"] * max(ebitda, 0.0))
    return {"interest_expense": exp, "interest_income": inc, "net_interest": net_int, "approx_tax_ebitda": ebitda,
            "threshold": thr, "excess": max(0.0, net_int - thr), "within": net_int <= thr}


def qfzp_status(answers: dict) -> dict:
    claimed = ans(answers, "qfzp_claimed") == YES
    missing = []
    if claimed:
        if ans(answers, "qfzp_substance") != YES:
            missing.append("adequate substance not evidenced")
        if ans(answers, "qfzp_audited") != YES:
            missing.append("audited financial statements not confirmed")
        if ans(answers, "qfzp_domestic_pe") == YES:
            missing.append("domestic permanent establishment / natural-person income to be reviewed")
        if ans(answers, "qfzp_domestic_pe") in (None, UNK):
            missing.append("domestic permanent establishment status unknown")
    return {"claimed": claimed, "missing": missing, "ok": claimed and not missing}


# --------------------------------------------------------------------------------------------
# Computation
# --------------------------------------------------------------------------------------------
def _round0(x: float) -> float:
    return float(math.floor(x + 0.5))


def compute(tr: TranslationResult, st, adjs: list, answers: dict, include_status=("Confirmed",)) -> Computation:
    P = params()
    rows = {k: 0.0 for k in ROWS}
    for a in adjs:
        if a.status in include_status:
            rows[a.row] += a.amount
    A = st.profit_for_year
    B = sum(rows[k] for k, v in ROWS.items() if v[1] == "B")
    C = sum(rows[k] for k, v in ROWS.items() if v[1] == "C")
    og, ol = rows["o_prev_gain"], rows["o_prev_loss"]
    D = A - B + C + og - ol
    L0 = _num(ans(answers, "opening_losses", 0.0))
    G = _num(ans(answers, "loss_transfer_in", 0.0))
    notes = []

    # ---------------- QFZP split
    q = qfzp_status(answers)
    qinfo = {}
    qtaxable = nqtaxable = None
    sbr = sbr_assessment(answers, st)
    sbr_applied = ans(answers, "sbr_elect") == YES and sbr["potential"]
    if ans(answers, "sbr_elect") == YES and not sbr["potential"]:
        notes.append("Small Business Relief was elected but the conditions are not met (" + " ".join(sbr["failures"]) + ") - relief NOT applied.")

    if q["claimed"]:
        cls = {r.get("account"): r.get("class", UNK) for r in _table(answers, "income_classification")}
        by_acct_ded = {}
        for a in adjs:
            if a.status in include_status and ROWS[a.row][1] == "B":
                for code, name in a.accounts:
                    by_acct_ded[code or name] = by_acct_ded.get(code or name, 0.0) + a.amount / max(len(a.accounts), 1)
        qi = nqi = exempt = unknown = 0.0
        for a in tr.accounts:
            if fs_lines()[a.line]["statement"] == "PL" and a.net_aed < 0:
                key = a.account.code or a.account.name
                inc = -a.net_aed - by_acct_ded.get(key, 0.0) - by_acct_ded.get(a.account.name, 0.0)
                c = cls.get(key) or cls.get(a.account.name) or UNK
                if c == "Qualifying income":
                    qi += inc
                elif c == "Exempt income":
                    exempt += inc
                elif c == UNK:
                    unknown += inc
                    nqi += inc
                else:
                    nqi += inc
        gross_rev = qi + nqi + exempt
        nq_rev_for_test = nqi
        thr = min(P["qfzp_de_minimis_amount"], P["qfzp_de_minimis_pct"] * st.revenue) if st.revenue > 0 else P["qfzp_de_minimis_amount"]
        # de minimis: non-qualifying revenue must not exceed the lower of the amount and the % of total revenue
        total_rev_for_test = max(st.revenue, gross_rev)
        thr = min(P["qfzp_de_minimis_amount"], P["qfzp_de_minimis_pct"] * total_rev_for_test)
        de_min_ok = nq_rev_for_test <= thr
        # expense allocation
        nq_alloc_income = nqi + exempt          # exempt income not removed by a confirmed adjustment is still taxable
        expenses_net = (qi + nq_alloc_income) - D
        dq, dnq = _num(ans(answers, "qfzp_direct_q", 0.0)), _num(ans(answers, "qfzp_direct_nq", 0.0))
        indirect = expenses_net - dq - dnq
        ratio = (qi / (qi + nq_alloc_income)) if (qi + nq_alloc_income) > 0 else 0.0
        qtaxable = qi - dq - indirect * ratio
        nqtaxable = nq_alloc_income - dnq - indirect * (1 - ratio)
        qinfo = {"qualifying_income_gross": qi, "non_qualifying_income_gross": nqi, "exempt_income": exempt, "unknown_income": unknown,
                 "de_minimis_threshold": thr, "de_minimis_ok": de_min_ok, "direct_q": dq, "direct_nq": dnq, "indirect_allocated": indirect,
                 "q_ratio": ratio, "missing_conditions": q["missing"] + ([] if de_min_ok else ["non-qualifying revenue exceeds the de minimis limit"]),
                 "status_ok": q["ok"] and de_min_ok}
        if unknown > 0:
            notes.append(f"AED {unknown:,.0f} of income is unclassified and was treated as non-qualifying for the QFZP split.")
    # ---------------- losses
    use_qfzp = bool(q["claimed"] and qinfo.get("status_ok"))
    base_for_cap = (nqtaxable if use_qfzp else D)
    cap = P["loss_utilisation_cap"] * max(base_for_cap or 0.0, 0.0)
    if sbr_applied:
        relief_cf = relief_g = 0.0
    else:
        relief_cf = min(L0, cap)
        relief_g = min(G, max(cap - relief_cf, 0.0))
    E = D - relief_cf - relief_g
    nq_after = (nqtaxable - relief_cf - relief_g) if use_qfzp else None

    # ---------------- tax
    basis, tax0, tax9, nil_applied = "ordinary", 0.0, 0.0, 0.0
    if sbr_applied:
        basis = "SBR"
        notes.append("Small Business Relief applied on election: taxable income is treated as nil; tax losses of the period are not carried forward.")
    elif use_qfzp:
        basis = "QFZP"
        tax9 = _round0(P["standard_rate"] * max(nq_after, 0.0))
        tax0 = 0.0
        if qtaxable is not None and qtaxable < 0 or (nq_after is not None and nq_after < 0):
            notes.append("A loss arises on one side of the QFZP split - technical review of loss treatment required.")
    else:
        taxable = max(E, 0.0)
        nil_applied = min(taxable, P["nil_rate_band"])
        tax9 = _round0(P["standard_rate"] * max(taxable - P["nil_rate_band"], 0.0))
        if q["claimed"]:
            notes.append("QFZP was claimed but is not supported (" + "; ".join(qinfo.get("missing_conditions", [])) +
                         ") - the computation uses the ordinary rates. The QFZP result is shown as an alternative.")
    # foreign tax credit (capped at CT payable)
    creditable = 0.0
    for r in _table(answers, "foreign_taxes"):
        if r.get("proof") != YES or r.get("exempt_income") != NO:
            continue          # no credit without proof of payment AND confirmation that the income is not exempt in the UAE
        inc = _num(r.get("income"))
        creditable += min(_num(r.get("paid")), P["standard_rate"] * inc) if inc > 0 else _num(r.get("paid"))
    credit = min(creditable, tax9) if basis != "SBR" else 0.0
    payable = tax9 - credit
    etr = (payable / A) if abs(A) > 0.5 else None

    # alternative QFZP result when claimed but unsupported
    if q["claimed"] and not use_qfzp and qinfo:
        qt = _round0(P["standard_rate"] * max(nqtaxable - relief_cf - relief_g, 0.0))
        qinfo["alternative_tax_if_qfzp"] = qt
    loss_closing = 0.0
    if not sbr_applied:
        loss_closing = L0 - relief_cf + max(-(E if not use_qfzp else min(E, 0.0)), 0.0)
    else:
        loss_closing = L0
    it = interest_test(tr, answers)
    return Computation(rows, A, B, C, og, ol, D, relief_cf, relief_g, E, basis, tax0, tax9, credit, payable, etr,
                       qtaxable, nq_after, L0, loss_closing, notes, qinfo, sbr, it, nil_applied)


def scenarios(tr, st, review, answers) -> list:
    """What-if comparison of the three realisation-basis options, treating all generated adjustments as confirmed."""
    out = []
    for code, label in (("A", "Option 1 - scope A"), ("B", "Option 2 - scope B"), ("none", "Option 3 - current basis")):
        adjs, _ = build_adjustments(tr, review, answers, option=code)
        # only the realisation-basis items differ between scenarios; keep other proposed items out of the comparison
        rb_adjs = [a for a in adjs if a.category == "Realisation basis"]
        for a in rb_adjs:
            a.status = "Confirmed"
        c = compute(tr, st, rb_adjs, answers)
        out.append({"option": label, "taxable_income": c.E, "tax_payable": c.payable, "deductions": c.B, "additions": c.C})
    return out


# --------------------------------------------------------------------------------------------
# Sheet applicability (user requirement: a sheet that is not applicable is not produced)
# --------------------------------------------------------------------------------------------
def applicability(tr: TranslationResult, st, adjs: list, comp: Computation, answers: dict, include_dta: bool = False) -> dict:
    """Ordered dict: sheet -> (included: bool, reason: str). Evaluated on CONFIRMED adjustments for the client workbook."""
    conf = [a for a in adjs if a.status == "Confirmed"]
    lines = {a.line for a in tr.accounts}
    rb = _rb(answers)
    res = {}
    res["Assumptions"] = (True, "Always produced")
    res["Calculation of CT"] = (True, "Always produced")
    res["Profit and Loss"] = (True, "Always produced - AED")
    res["Balance Sheet"] = (True, "Always produced - AED")
    foreign = not tr.method_record.get("method") == "none"
    res["FX Rates"] = (foreign, "TB currency is not AED - conversion record required" if foreign else "TB is already in AED - no conversion sheet needed")
    res["TB (AED)"] = (True, "Source of the P&L and balance sheet")
    res["Adjustments"] = (bool(conf), "Confirmed adjustments feed the computation" if conf else "No confirmed adjustments")
    cur_def = [a for a in conf if a.category == "Realisation basis" and a.row in ("d_unrealised_capital", "d_unrealised_revenue", "a_unreal_loss_capital", "a_unreal_loss_revenue")]
    prev = _table(answers, "prev_unrealised")
    ugul = rb in ("A", "B") and (bool(prev) or bool(cur_def))
    res["UGUL"] = (ugul, "Realisation basis elected and unrealised amounts exist" if ugul else
                   ("No realisation-basis election confirmed" if rb not in ("A", "B") else "No unrealised amounts to schedule"))
    prov = bool(_table(answers, "provisions")) or bool(lines & {"P_PROV", "L_PROV"})
    res["Provision"] = (prov, "Provision accounts or movements exist" if prov else "No provisions in the TB or questionnaire")
    res["DTA & DTL Working"] = (include_dta, "Requested (accounting deferred-tax working)" if include_dta else "Optional accounting working - not requested")
    loss = (comp.loss_opening > 0) or comp.E < 0 or _num(ans(answers, "loss_transfer_in", 0.0)) > 0
    res["Tax Loss Carried Forward"] = (loss, "Opening losses, a current-period loss or loss transfers exist" if loss else "No tax losses involved")
    dis = [a for a in conf if a.row in DISALLOWED_SHEET_ROWS]
    res["Disallowed Expenses"] = (bool(dis), "Confirmed non-deductible expenses exist" if dis else "No confirmed disallowed expenses")
    fz = ans(answers, "qfzp_claimed") == YES
    res["Freezone"] = (fz, "QFZP status is claimed" if fz else "QFZP not claimed")
    ft = any(_num(r.get("paid")) > 0 for r in _table(answers, "foreign_taxes"))
    res["Taxes Paid Abroad"] = (ft, "Foreign tax / withholding tax reported" if ft else "No foreign tax reported")
    return res


def open_items_from_state(answers: dict, ctx: dict, extra: list, comp: Computation, st, tr) -> list:
    """Merge questionnaire gaps, engine open items and structural flags into one list."""
    from .questionnaire import unanswered
    items = list(extra)
    for q in unanswered(answers, ctx):
        items.append({"topic": "Questionnaire", "item": q.text, "status": "Information required", "documents": [q.evidence] if q.evidence else []})
    sbr = comp.sbr or sbr_assessment(answers, st)
    if sbr.get("potential"):
        items.append({"topic": "Small Business Relief",
                      "item": "Potential Small Business Relief eligibility identified. Confirm the statutory conditions and the company's election before applying the relief. "
                              "Electing forfeits carry-forward of tax losses of the period.",
                      "status": "Technical review required", "documents": ["Revenue records for all periods"]})
    q = qfzp_status(answers)
    if q["claimed"] and not q["ok"]:
        items.append({"topic": "QFZP", "item": "QFZP conditions not fully evidenced: " + "; ".join(q["missing"]) + ".", "status": "Technical review required", "documents": ["Substance evidence", "Audited FS"]})
    if comp.qfzp and not comp.qfzp.get("de_minimis_ok", True):
        items.append({"topic": "QFZP", "item": "Non-qualifying revenue exceeds the de minimis limit - QFZP status may be lost for this and following periods.", "status": "Technical review required", "documents": []})
    if tr.diff_applicable:
        items.append({"topic": "Currency translation", "item": f"Approve the derived translation difference of AED {tr.translation_diff:,.2f}.", "status": "Information required", "documents": []})
    return items
