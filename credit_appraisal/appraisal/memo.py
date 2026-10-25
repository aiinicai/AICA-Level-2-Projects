"""
memo.py
=======
Recommendation engine and automated credit-appraisal memo.

Decision logic (deterministic and auditable)
--------------------------------------------
DECLINE                     grade E, or any critical breach (DSCR < 1.0x / negative TNW),
                            or grade D with two or more hard-guardrail breaches
APPROVE WITH COVENANTS      no hard breaches and grade A or B
REFER TO CREDIT COMMITTEE   everything else (grade C, single hard breach, or soft-guardrail breaches on grade D)

Covenant tightness scales with the risk grade (config in TIERS below).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .config import RATIO_META, fmt_value
from .ingestion import ApplicantData
from .ratios import RatioBundle
from .scoring import Scorecard

DECISION_STYLE = {
    "APPROVE": ("Recommend Approval with Covenants", "#15803D"),
    "REFER": ("Refer to Credit Committee", "#B45309"),
    "DECLINE": ("Decline", "#B42318"),
}

# Tightness of structure by risk grade
TIERS = {
    "A": dict(dsra_months=3, sec_cover=1.25, de_cut=0.0, lev_cut=0.0, dscr_add=0.00, sweep=0.0, escrow=False, div_cap="No dividend if DSCR would fall below 1.50x post-payout"),
    "B": dict(dsra_months=3, sec_cover=1.40, de_cut=0.0, lev_cut=0.0, dscr_add=0.00, sweep=0.0, escrow=False, div_cap="No dividend if DSCR would fall below 1.50x post-payout"),
    "C": dict(dsra_months=6, sec_cover=1.60, de_cut=0.25, lev_cut=0.5, dscr_add=0.10, sweep=0.25, escrow=True, div_cap="Dividend capped at 20% of PAT, only if no covenant breach"),
    "D": dict(dsra_months=6, sec_cover=1.75, de_cut=0.50, lev_cut=1.0, dscr_add=0.15, sweep=0.50, escrow=True, div_cap="No dividend / promoter withdrawals until DSCR >= 1.50x for two consecutive years"),
    "E": dict(dsra_months=6, sec_cover=2.00, de_cut=0.50, lev_cut=1.0, dscr_add=0.20, sweep=0.50, escrow=True, div_cap="No dividend / promoter withdrawals"),
}


@dataclass
class Recommendation:
    decision: str                      # APPROVE | REFER | DECLINE
    label: str
    color: str
    headline: str
    rationale: list
    strengths: list
    risks: list
    financial_covenants: list
    structural_terms: list
    monitoring: list
    conditions_precedent: list
    key_numbers: dict = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Strengths and risks from the numbers
# --------------------------------------------------------------------------- #
def _strengths_and_risks(data, bundle, pf, exposure, stress, policy_df, limits):
    r, f = bundle.ratios, bundle.fin
    S, R = [], []
    last = lambda k: bundle.latest(k)  # noqa: E731

    # Growth & margins
    cagr = bundle.revenue_cagr
    if not np.isnan(cagr):
        if cagr >= 0.10:
            S.append(f"Revenue has compounded at {cagr * 100:.1f}% p.a. over the audited period, reaching ₹{f['revenue'].iloc[-1]:,.0f} Cr.")
        elif cagr < 0:
            R.append(f"Revenue has contracted at {abs(cagr) * 100:.1f}% p.a. over the audited period; top-line momentum is negative.")
    em, em_chg = last("ebitda_margin"), bundle.change("ebitda_margin")
    if em >= 0.15:
        S.append(f"Healthy EBITDA margin of {em * 100:.1f}% ({em_chg * 10000:+.0f} bps vs {bundle.years[0]}).")
    elif em < 0.08:
        R.append(f"Thin EBITDA margin of {em * 100:.1f}% leaves limited cushion against input-cost or pricing shocks.")
    if em_chg <= -0.02:
        R.append(f"EBITDA margin has compressed by {abs(em_chg) * 10000:.0f} bps over three years.")
    elif em_chg >= 0.01 and em >= 0.10:
        S.append("Margins are expanding, indicating pricing power or operating leverage.")

    # Returns vs cost of debt
    rate = float(data.proposed["rate_pct"]) / 100
    roce = last("roce")
    if roce >= rate + 0.04:
        S.append(f"ROCE of {roce * 100:.1f}% comfortably exceeds the proposed {rate * 100:.2f}% cost of debt (positive leverage).")
    elif roce < rate:
        R.append(f"ROCE of {roce * 100:.1f}% is below the proposed cost of debt of {rate * 100:.2f}% - incremental borrowing is dilutive.")
    if last("npm") <= 0:
        R.append("Company reported a net loss in the latest year; debt is being serviced from reserves/borrowings.")

    # Liquidity
    cr = last("current_ratio")
    if cr >= 1.33:
        S.append(f"Current ratio of {cr:.2f}x meets the 1.33x lending norm.")
    elif cr < 1.0:
        R.append(f"Current ratio of {cr:.2f}x is below 1.0x - working capital is funded from short-term sources.")
    elif cr < 1.33:
        R.append(f"Current ratio of {cr:.2f}x is below the 1.33x norm.")
    ccc_chg = bundle.change("ccc")
    if ccc_chg >= 15:
        R.append(f"Cash conversion cycle has lengthened by {ccc_chg:.0f} days to {last('ccc'):.0f} days - cash is getting trapped in working capital.")
    elif ccc_chg <= -10:
        S.append(f"Cash conversion cycle improved by {abs(ccc_chg):.0f} days to {last('ccc'):.0f} days.")
    if last("dso") > 90:
        R.append(f"Debtor days of {last('dso'):.0f} indicate elevated collection / counter-party risk.")

    # Leverage & coverage (pro-forma)
    def headroom(actual, limit, higher_better):
        return (actual / limit - 1) if higher_better else (1 - actual / limit)
    if not np.isnan(pf["dscr"]):
        h = headroom(pf["dscr"], limits.min_dscr, True)
        msg = f"Pro-forma DSCR of {pf['dscr']:.2f}x vs policy minimum {limits.min_dscr:.2f}x ({h * 100:+.0f}% headroom)."
        if h >= 0.20:
            S.append(msg)
        elif h < 0:
            R.append(msg)
    if np.isfinite(pf["debt_ebitda"]):
        h = headroom(pf["debt_ebitda"], limits.max_debt_ebitda, False)
        if h >= 0.30:
            S.append(f"Post-loan Debt/EBITDA of {pf['debt_ebitda']:.2f}x is well inside the {limits.max_debt_ebitda:.1f}x ceiling.")
        elif h < 0:
            R.append(f"Post-loan Debt/EBITDA of {pf['debt_ebitda']:.2f}x breaches the {limits.max_debt_ebitda:.1f}x ceiling.")
    else:
        R.append("EBITDA is not positive - leverage multiples are not meaningful.")
    if np.isfinite(pf["de"]):
        if pf["de"] <= limits.max_de * 0.6:
            S.append(f"Conservative gearing: post-loan Debt/TNW of {pf['de']:.2f}x.")
        elif pf["de"] > limits.max_de:
            R.append(f"Post-loan Debt/TNW of {pf['de']:.2f}x exceeds the {limits.max_de:.1f}x limit; equity infusion may be needed.")
    else:
        R.append("Tangible net worth is negative.")
    if not np.isnan(pf["icr"]) and pf["icr"] < limits.min_icr:
        R.append(f"Post-loan interest cover of {pf['icr']:.2f}x is below the {limits.min_icr:.2f}x minimum.")
    de_trend = bundle.change("de")
    if np.isfinite(de_trend) and de_trend > 0.25:
        R.append(f"Gearing has been rising (Debt/TNW +{de_trend:.2f}x over the period).")

    # Stress
    if not stress["DSCR >= 1.0x (can service)"].all():
        failing = ", ".join(stress.index[~stress["DSCR >= 1.0x (can service)"]])
        R.append(f"Debt service is not covered from cash flows under stress ({failing}).")
    elif stress["DSCR >= policy"].all():
        S.append("DSCR stays above policy minimum even under the harshest stress scenario tested.")

    # Existing lender profile
    if exposure["n_lenders"] >= 3 and exposure["top_lender_share"] <= 0.5:
        S.append(f"Diversified lender base ({exposure['n_lenders']} lenders; largest {exposure['top_lender_share'] * 100:.0f}% of debt).")
    elif exposure["top_lender_share"] > 0.6:
        R.append(f"Debt concentrated with one lender ({exposure['top_lender_share'] * 100:.0f}%) - refinancing / cross-default risk.")
    cu = exposure["cc_utilisation"]
    if not np.isnan(cu) and cu >= 0.85:
        R.append(f"Working-capital limits are {cu * 100:.0f}% utilised - little undrawn liquidity buffer.")
    if abs(exposure["recon_gap_pct"]) > 0.05:
        R.append(f"Lender-wise debt schedule differs from audited balance-sheet debt by {exposure['recon_gap_pct'] * 100:+.1f}% - reconcile via CA certificate / CIBIL-CRILC check.")

    # Promoter, vintage, rating
    ph = data.profile.get("promoter_holding_pct")
    if ph is not None and not pd.isna(ph):
        if ph >= 51:
            S.append(f"Promoter holding of {ph:.1f}% indicates strong control and alignment.")
        elif ph < 40:
            R.append(f"Low promoter holding ({ph:.1f}%) weakens commitment / support potential.")
    if data.vintage_years >= 10:
        S.append(f"Established operating track record of {data.vintage_years:.0f} years.")
    elif data.vintage_years < 5:
        R.append(f"Limited vintage ({data.vintage_years:.0f} years) - through-cycle performance not yet demonstrated.")
    if data.profile.get("rating"):
        S.append(f"External rating on record: {data.profile['rating']}.")

    # Credit bureau score
    bureau = data.profile.get("bureau_score")
    if bureau is not None and not pd.isna(bureau):
        if bureau >= max(limits.min_bureau_score, 750):
            S.append(f"Strong credit bureau score of {bureau:.0f}, indicating a clean repayment record with existing lenders.")
        elif bureau < limits.min_bureau_score:
            R.append(f"Credit bureau score of {bureau:.0f} is below the {limits.min_bureau_score:.0f} policy minimum - review repayment history, SMA/DPD tags and enquiries.")

    # Security
    sc = pf["security_cover"]
    if not np.isnan(sc):
        if sc >= limits.min_security_cover * 1.2:
            S.append(f"Collateral cover of {sc:.2f}x on the proposed facility exceeds the {limits.min_security_cover:.2f}x policy minimum.")
        elif sc < limits.min_security_cover:
            R.append(f"Offered collateral cover of {sc:.2f}x is below the {limits.min_security_cover:.2f}x policy minimum.")

    return [s for s in S if s], [x for x in R if x]


# --------------------------------------------------------------------------- #
# Covenants & monitoring
# --------------------------------------------------------------------------- #
def _covenants(data, bundle, pf, exposure, grade, limits):
    t = TIERS[grade]
    amount = float(data.proposed["amount"])
    fcov, struct = [], []

    dscr_cov = round(limits.min_dscr + t["dscr_add"], 2)
    de_cov = round(limits.max_de - t["de_cut"], 2)
    lev_cov = round(limits.max_debt_ebitda - t["lev_cut"], 2)
    fcov += [
        f"Minimum DSCR of {dscr_cov:.2f}x, tested annually on audited financials.",
        f"Maximum Total Debt / TNW of {de_cov:.2f}x.",
        f"Maximum Total Debt / EBITDA of {lev_cov:.2f}x.",
        f"Minimum ICR of {limits.min_icr:.2f}x.",
        "Current ratio to be maintained at or above 1.10x.",
    ]

    # DSRA = n months of peak debt service on the proposed facility
    ds_prop = pf["prop_principal"] + pf["prop_interest"]
    dsra = t["dsra_months"] * ds_prop / 12
    struct.append(f"DSRA: {t['dsra_months']} months of debt service on this facility (≈ ₹{dsra:,.2f} Cr) in an escrow-linked account with the NBFC, to be funded before first disbursement or from the first drawdown.")

    # Collateral
    req_cover = max(t["sec_cover"], limits.min_security_cover)
    req_value = req_cover * amount
    offered = float(data.proposed.get("collateral_value", 0.0))
    if offered >= req_value:
        struct.append(f"Security: first-ranking charge on collateral of ₹{offered:,.1f} Cr ({offered / amount:.2f}x) - meets the {req_cover:.2f}x requirement for Grade {grade}.")
    else:
        struct.append(f"Security: minimum {req_cover:.2f}x cover (₹{req_value:,.1f} Cr) required for Grade {grade}; offered ₹{offered:,.1f} Cr - additional collateral of ₹{req_value - offered:,.1f} Cr or equivalent cash margin / corporate guarantee to be obtained.")
    struct.append("Personal guarantee of promoter-directors and pledge of at least 30% of promoter shareholding (non-disposal undertaking for the balance).")

    # Drawing power - applicable to working-capital limits
    f = bundle.fin.iloc[-1]
    dp = max(0.75 * (f["inventory"] + f["receivables"]) - f["payables"], 0.0)
    wc_total = exposure["wc_limits"] + (amount if "working" in str(data.proposed["facility_type"]).lower() else 0.0)
    if wc_total > 0:
        flag = "adequate" if dp >= wc_total else f"SHORT by ₹{wc_total - dp:,.1f} Cr - limits to be restricted to DP"
        struct.append(f"Drawing power: 75% of eligible inventory + receivables (< 90 days) less trade creditors, via monthly stock & debtor statements. Indicative DP on latest balance sheet ₹{dp:,.1f} Cr vs working-capital limits ₹{wc_total:,.1f} Cr - {flag}.")
    else:
        struct.append("Drawing power: not applicable to this term facility; existing CC/OD lines to remain DP-controlled by respective lenders.")

    struct.append(t["div_cap"] + ".")
    struct.append("Negative lien on all assets financed / unencumbered; no additional borrowing or change in ownership/control without NBFC's prior written consent.")
    if t["sweep"]:
        struct.append(f"Cash sweep: {t['sweep'] * 100:.0f}% of excess cash flow after scheduled debt service applied to prepayment.")
    if t["escrow"]:
        struct.append("Escrow / trust-and-retention account (TRA) for top customer receivables with first charge to this facility's debt service.")
    struct.append("Utilisation strictly for the stated purpose; end-use certificate from statutory auditor within 60 days of drawdown.")

    # Conditions precedent
    cps = [
        "Receipt and review of latest provisional financials and GST/bank-statement reconciliation to audited turnover.",
        "No-dues / NOC from existing lenders and ROC charge-search confirming no conflicting charges.",
        "Independent valuation (≤ 6 months old) and legal title search of collateral; insurance assigned to NBFC.",
        "CIBIL Commercial / CRILC and negative-list checks on company and promoters; KYC and sanctions screening.",
    ]
    if offered < req_value:
        cps.append("Additional security / structural enhancement to bring cover to the required level.")
    return fcov, struct, cps


def _monitoring(data, bundle, pf, limits):
    f, r = bundle.fin.iloc[-1], bundle.ratios.iloc[-1]
    dscr_ew = round(limits.min_dscr + 0.15, 2)
    return [
        f"Early-warning: DSCR (rolling 12M) below {dscr_ew:.2f}x or ICR below {limits.min_icr + 0.25:.2f}x.",
        f"Early-warning: EBITDA margin falls more than 200 bps below the latest audited level of {r['ebitda_margin'] * 100:.1f}%.",
        f"Early-warning: debtor days rise above {r['dso'] + 15:.0f} (latest {r['dso']:.0f}) or inventory days above {r['dio'] + 15:.0f}.",
        f"Early-warning: Total Debt / EBITDA above {limits.max_debt_ebitda - 0.5:.1f}x or any new borrowing not pre-approved.",
        "Early-warning: CC/OD utilisation above 90% for three consecutive months, cheque returns or any DPD > 30 days with any lender.",
        "Trigger events: rating downgrade, auditor qualification, promoter share pledge invocation, adverse CRILC/SMA tagging, key-customer loss.",
        "Reporting: quarterly unaudited results within 45 days, monthly stock/debtor statements, annual audited accounts within 180 days, annual site visit.",
    ]


# --------------------------------------------------------------------------- #
# Decision
# --------------------------------------------------------------------------- #
def build_recommendation(data: ApplicantData, bundle: RatioBundle, pf: dict, exposure: dict, stress: pd.DataFrame,
                         scorecard: Scorecard, policy_df: pd.DataFrame, limits) -> Recommendation:
    grade = scorecard.grade
    hard_fails = policy_df[(policy_df["Severity"] == "Hard") & (~policy_df["Passed"])]
    soft_fails = policy_df[(policy_df["Severity"] == "Soft") & (~policy_df["Passed"])]
    critical = bool(policy_df["Critical"].any())

    if grade == "E" or critical or (grade == "D" and len(hard_fails) >= 2):
        decision = "DECLINE"
    elif len(hard_fails) == 0 and grade in ("A", "B"):
        decision = "APPROVE"
    else:
        decision = "REFER"
    label, color = DECISION_STYLE[decision]

    name, amount = data.profile["name"], float(data.proposed["amount"])
    why = [f"Internal risk grade **{grade}** ({scorecard.grade_label.lower()}), composite score {scorecard.composite:.1f}/100."]
    if len(hard_fails):
        why.append("Hard guardrail breaches: " + "; ".join(
            f"{r.Check} {fmt_value(r.Actual, r.Unit)} vs {r.Rule}" for r in hard_fails.itertuples()) + ".")
    else:
        why.append("All hard policy guardrails (DSCR, Debt/TNW, ICR, Debt/EBITDA, ticket size) are met on a pro-forma basis.")
    if len(soft_fails):
        why.append("Soft guardrail exceptions: " + "; ".join(
            f"{r.Check} {fmt_value(r.Actual, r.Unit)} vs {r.Rule}" for r in soft_fails.itertuples()) + ".")
    if critical:
        why.append("Critical breach: debt service cannot be met from cash flows or tangible net worth is eroded.")
    why.extend(scorecard.notes)

    headline = {
        "APPROVE": f"{name} meets all quantitative guardrails post-loan; sanction of ₹{amount:,.1f} Cr is recommended subject to the covenants and security below.",
        "REFER": f"{name} presents a mixed profile; the proposal for ₹{amount:,.1f} Cr should be placed before the Credit Committee with the mitigants and tightened structure below.",
        "DECLINE": f"The proposal for ₹{amount:,.1f} Cr does not meet the NBFC's risk appetite on current financials; decline is recommended. Re-submission is possible if the weaknesses below are cured (e.g. equity infusion, lower quantum, stronger security).",
    }[decision]

    strengths, risks = _strengths_and_risks(data, bundle, pf, exposure, stress, policy_df, limits)
    fcov, struct, cps = _covenants(data, bundle, pf, exposure, grade, limits)
    if decision == "DECLINE":
        fcov, struct, cps = [], [], []     # terms are not offered on a decline
    monitoring = _monitoring(data, bundle, pf, limits) if decision != "DECLINE" else []

    return Recommendation(decision, label, color, headline, why, strengths, risks, fcov, struct, monitoring, cps,
                          key_numbers=dict(grade=grade, score=scorecard.composite))


# --------------------------------------------------------------------------- #
# Markdown memo
# --------------------------------------------------------------------------- #
def _md_table(df: pd.DataFrame) -> str:
    cols = [str(df.index.name or "")] + [str(c) for c in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
    for idx, row in df.iterrows():
        lines.append("| " + " | ".join([str(idx)] + [str(v) for v in row.values]) + " |")
    return "\n".join(lines)


def render_memo_markdown(data: ApplicantData, bundle: RatioBundle, pf: dict, pf_now: dict, exposure: dict,
                         stress: pd.DataFrame, scorecard: Scorecard, policy_df: pd.DataFrame,
                         rec: Recommendation, limits) -> str:
    p, prop = data.profile, data.proposed
    f, r = bundle.fin, bundle.ratios

    def bullets(items):
        return "\n".join(f"- {i}" for i in items) if items else "- None."

    # Key ratio trend table
    keys = ["ebitda_margin", "npm", "roe", "roce", "current_ratio", "ccc", "de", "debt_ebitda", "icr", "dscr"]
    trend = pd.DataFrame({RATIO_META[k]["label"]: [fmt_value(r[k].iloc[i], RATIO_META[k]["unit"]) for i in range(len(r))]
                          for k in keys}, index=bundle.years).T
    trend.index.name = "Ratio"
    fin_tbl = pd.DataFrame({
        "Revenue": [f"{v:,.1f}" for v in f["revenue"]], "EBITDA": [f"{v:,.1f}" for v in f["ebitda"]],
        "PAT": [f"{v:,.1f}" for v in f["pat"]], "TNW": [f"{v:,.1f}" for v in f["tnw"]],
        "Total debt": [f"{v:,.1f}" for v in f["total_debt"]],
    }, index=bundle.years).T
    fin_tbl.index.name = "₹ Cr"

    pf_tbl = pd.DataFrame({
        "Current": [f"{pf_now['total_debt']:,.1f}", fmt_value(pf_now["de"], "x"), fmt_value(pf_now["debt_ebitda"], "x"),
                    fmt_value(pf_now["icr"], "x"), fmt_value(pf_now["dscr"], "x")],
        "Pro-forma": [f"{pf['total_debt']:,.1f}", fmt_value(pf["de"], "x"), fmt_value(pf["debt_ebitda"], "x"),
                      fmt_value(pf["icr"], "x"), fmt_value(pf["dscr"], "x")],
    }, index=["Total debt (₹ Cr)", "Debt / TNW", "Debt / EBITDA", "ICR", "DSCR"])
    pf_tbl.index.name = "Metric"

    sc_tbl = pd.DataFrame({"Score": [f"{v:.0f}" for v in scorecard.pillar_scores.values()]},
                          index=list(scorecard.pillar_scores.keys()))
    sc_tbl.index.name = "Pillar"

    pol = policy_df.copy()
    pol_tbl = pd.DataFrame({
        "Basis": pol["Basis"].values, "Rule": pol["Rule"].values,
        "Actual": [fmt_value(a, u) for a, u in zip(pol["Actual"], pol["Unit"])],
        "Result": ["Pass" if ok else "BREACH" for ok in pol["Passed"]],
    }, index=pol["Check"].values)
    pol_tbl.index.name = "Guardrail"

    st = stress.copy()
    st_tbl = pd.DataFrame({
        "DSCR": [fmt_value(v, "x") for v in st["DSCR"]], "ICR": [fmt_value(v, "x") for v in st["ICR"]],
        "Debt/EBITDA": [fmt_value(v, "x") for v in st["Debt / EBITDA"]],
        "Meets policy DSCR": ["Yes" if v else "No" for v in st["DSCR >= policy"]],
    }, index=st.index)

    md = f"""# Credit Appraisal Memo

**Applicant:** {p['name']}  |  **CIN:** {p.get('cin') or 'n.a.'}  |  **Industry:** {p.get('industry') or 'n.a.'}
**Facility requested:** ₹{prop['amount']:,.1f} Cr {prop['facility_type']}, {prop['tenure_years']:.0f} years, {prop['rate_pct']:.2f}% p.a., {prop['moratorium_months']:.0f}-month moratorium
**Purpose:** {prop['purpose'] or 'n.a.'}
**Internal risk grade:** {scorecard.grade} ({scorecard.grade_label}), score {scorecard.composite:.1f}/100  |  **Credit bureau score:** {fmt_value(p.get('bureau_score'), 'score')}

## 1. Recommendation: {rec.label}
{rec.headline}

{bullets(rec.rationale)}

## 2. Financial snapshot (₹ Cr)
{_md_table(fin_tbl)}

{_md_table(trend)}

## 3. Existing and pro-forma exposure
Existing lender-wise debt: ₹{exposure['outstanding']:,.1f} Cr across {exposure['n_lenders']} lenders (weighted average cost {exposure['wavg_rate']:.2f}%). Sanctioned fund-based exposure after this facility: ₹{pf['sanctioned_exposure']:,.1f} Cr.

{_md_table(pf_tbl)}

**Stress test (pro-forma):**

{_md_table(st_tbl)}

## 4. Risk scorecard
{_md_table(sc_tbl)}

## 5. Policy compliance
{_md_table(pol_tbl)}

## 6. Key strengths
{bullets(rec.strengths)}

## 7. Key risks
{bullets(rec.risks)}
"""
    if rec.decision != "DECLINE":
        md += f"""
## 8. Proposed financial covenants
{bullets(rec.financial_covenants)}

## 9. Security and structural terms (DSRA, drawing power, collateral)
{bullets(rec.structural_terms)}

## 10. Conditions precedent to disbursement
{bullets(rec.conditions_precedent)}

## 11. Monitoring framework and early-warning triggers
{bullets(rec.monitoring)}
"""
    md += "\n---\n*System-generated draft based on the supplied financials and the NBFC credit-policy parameters in force. It supports, and does not replace, the credit officer's independent judgement, site visit, KYC/CIBIL checks and legal due diligence.*\n"
    return md
