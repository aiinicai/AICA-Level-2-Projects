"""Day Book tests that read what was written (narrations) and how amounts are shaped.

Narration themes flag words an auditor would want explained. They are leads, not conclusions: a match
means "look at this voucher", and the wording of each theme says why. A simple negation check stops
"no penalty levied" from being flagged.

Statutory references are to the Income-tax Act, 1961 and the CGST Act as understood for FY 2025-26.
From FY 2026-27 the Income-tax Act, 2025 renumbers sections; verify before relying on a section number.
"""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass

import pandas as pd

R_NARR_PREFIX = "Narration: "
R_NEAR = "999 test: amount just below a threshold"
R_REPEAT = "Repeated identical amounts"
R_BENFORD = "Benford first-digit test"


@dataclass(frozen=True)
class Theme:
    id: str
    label: str
    severity: str
    pattern: re.Pattern
    reference: str


def _t(id, label, sev, pattern, ref):
    return Theme(id, label, sev, re.compile(pattern, re.I), ref)


THEMES = [
    _t("fraud", "Fraud or misappropriation wording", "High",
       r"\b(fraud\w*|embezzl\w*|misappropriat\w*|defalcat\w*|forg(?:ed|ery)|siphon\w*|cheat\w*|dishonest\w*|"
       r"stolen|theft|pilfer\w*|scam\w*|fictitious|bogus|fake)\b",
       "SA 240: indicator of possible fraud. Escalate to management and those charged with governance; "
       "Sec 143(12) Companies Act reporting may apply."),
    _t("bribe", "Bribe or illegal payment wording", "High",
       r"\b(bribe\w*|kick.?backs?|illegal gratification|speed money|facilitation (?:fee|payment|charges?)|"
       r"under the table|hush money|pay.?off|(?:to|for) (?:influence|oblige)|consideration for (?:approval|clearance|licen[cs]e|"
       r"passing)|chai.?pani|sweetener)\b",
       "Sec 37(1) Explanation 1: expenditure that is an offence or prohibited by law is not deductible. "
       "Prevention of Corruption Act; Companies Act Sec 447."),
    _t("gift", "Gift or hospitality", "Medium",
       r"\b(gifts?|gifting|gift hamper|hampers?|freebies?|hospitality|entertainment|souvenirs?|mementos?|"
       r"sweets|dry fruits?|liquor|wine|diwali (?:gift|box)|festival (?:gift|expenses))\b",
       "Gifts are generally not a business expense (Sec 37) and GST input credit is blocked (Sec 17(5)(h) CGST). "
       "Sec 194R may require TDS on benefits above Rs 20,000 to a business associate."),
    _t("penalty", "Penalty, fine or late fee", "Medium",
       r"\b(penalt(?:y|ies)|fines?|late fees?|late filing|late payment (?:charges?|interest)|interest on late|"
       r"delay(?:ed)? (?:payment )?(?:charges?|interest)|compounding|show.?cause|demand notice|liquidated damages|"
       r"damages)\b",
       "Sec 37(1) Explanation 1: a penalty for infringement of law is not deductible. Late TDS interest is also "
       "not deductible (Sec 201(1A)); check Sec 40(a)(ia)."),
    _t("donation", "Donation, charity, CSR or political contribution", "Medium",
       r"\b(donat\w*|charit\w*|csr|corporate social responsibility|contribution to (?:trust|ngo|party|temple)|"
       r"political (?:party|contribution)|electoral bonds?|temple|mandir|gurudwara|church|mosque)\b",
       "Not a business expense: CSR is not deductible (Sec 37 Explanation 2); donations are claimed only under Sec 80G; "
       "political contributions fall under Sec 80GGB/80GGC and Sec 182 of the Companies Act, which also requires them to be disclosed in the profit and loss account with the name of the party (Sec 182(3))."),
    _t("instructed", "Entry made on instruction", "Medium",
       r"\b(as (?:per )?(?!standing )(?:(?:verbal|oral|written|telephonic)\s+)?(?:instruction|direction)s?|as instructed|"
       r"as directed|on (?:the )?(?:instruction|direction|orders?) of|at the (?:request|behest) of (?:the )?"
       r"(?:director|md|ceo|chairman|owner|boss|promoter)|as desired by|as told by|per (?:md|director|owner|boss)'?s? "
       r"(?:instruction|direction|request|wish))\b",
       "SA 240: management override of controls and missing supporting evidence. Obtain written authorisation "
       "and the underlying document."),
    _t("suspense", "Suspense, plug or unexplained difference", "Medium",
       r"\b(suspense|unreconciled|reconciliation difference|difference in (?:books|bank|balance|stock)|balancing figure|"
       r"plug(?:ged)?|adjustment entry|rounding off|round(?:ed)? off|unexplained|unidentified|unknown|"
       r"not known|clearing)\b",
       "Suspense and plug entries must be cleared, explained and supported before the accounts are finalised."),
    _t("writeoff", "Write-off or waiver", "Medium",
       r"\b(written?.?off|write.?offs?|waive\w*|waiver|forgone|forgiven|bad debts? (?:written|provided))\b",
       "Write-offs need approval and evidence that recovery was attempted (Sec 36(1)(vii) bad debts); "
       "waivers of amounts owed by related parties are also a Sec 185/AS 18 matter."),
    _t("personal", "Personal or family spend", "High",
       r"\b(personal|family|spouse|wife|husband|children|daughter|holiday|vacation|trip to|honeymoon|wedding|marriage|"
       r"birthday|domestic|residence|home loan|paid to self|cash to self|self cheque|"
       r"director'?s? (?:family|personal|vehicle|car|house|flat|travel))\b",
       "Not wholly for business: Sec 37(1). May be a perquisite to the director, and a related-party transaction (AS 18)."),
    _t("director_loan", "Loan or advance to a director or relative", "Medium",
       r"\b((?:loan|advance)s? (?:to|for) (?:the )?(?:director|md|promoter|relative|shareholder)|director'?s? "
       r"(?:loan|advance|drawings?)|drawings)\b",
       "Companies Act Sec 185 (loans to directors) and Sec 186; Sec 2(22)(e) deemed dividend for a closely held company."),
    _t("unsupported", "No supporting document", "Medium",
       r"\b(without (?:bill|invoice|voucher|receipt|supporting)|no (?:bill|invoice|voucher|receipt)|bills? not (?:available|"
       r"received)|invoice awaited|bills? to follow|to be regularis\w*|will be regularis\w*|pending regularisation|"
       r"estimated|on estimate|provisional entry)\b",
       "Expenditure without supporting documents may be disallowed and cannot support GST input credit. Request evidence."),
    _t("msme", "MSME supplier", "Medium",
       r"\b(udyam|msme|micro enterprise|small enterprise|msmed|micro and small|micro \& small)\b",
       "Payments to micro and small enterprises must be made within 45 days (MSMED Act Sec 15/16). Beyond that, Sec 43B(h) "
       "disallows the expense until paid and compound interest is due. Check invoice and payment dates."),
    _t("no_tds", "TDS probably not deducted", "Medium",
       r"\b(full amount (?:remitted|paid|released|transferred)|paid in full|without (?:deducting )?tds|no tds|"
       r"tds not (?:deducted|applicable)|gross amount paid)\b",
       "If tax was due, non-deduction attracts disallowance of 30% of the expense (Sec 40(a)(ia)), interest (Sec 201(1A)) "
       "and penalty (Sec 271C). Confirm whether the payee is below the threshold or holds a lower-deduction certificate."),
    _t("cash_settle", "Cash settlement wording", "Low",
       r"\b(settled in cash|paid in cash|cash payment|cash paid|cash received|in cash)\b",
       "Cash limits: Sec 40A(3) for payments, Sec 269ST for receipts and Sec 269SS/269T for loans and deposits."),
    _t("correction", "Correction, reversal or back-dating", "Low",
       r"\b(back.?dated?|ante.?dated?|reversal|reversed|cancelled (?:invoice|bill)|re.?booked|rectif\w*|"
       r"correction entry|wrongly (?:posted|booked|debited|credited|passed)|posted in error|error)\b",
       "Entries that undo earlier postings need approval and a trace to the original voucher."),
]
THEME_BY_ID = {t.id: t for t in THEMES}

# (limit in rupees, what it triggers). Amounts that sit just under these are a classic avoidance pattern.
THRESHOLDS = [
    (10_000, "Sec 40A(3) cash payment limit"),
    (20_000, "Sec 269SS/269T cash loan and deposit limit; Sec 194H commission limit"),
    (30_000, "Sec 194C single-payment limit for contractors"),
    (50_000, "PAN quoting limit (Rule 114B) and Sec 194J professional fees limit"),
    (100_000, "Sec 194C annual limit and the Rs 1 lakh item-disclosure threshold"),
    (200_000, "Sec 269ST cash receipt limit"),
    (500_000, "a common internal approval limit (confirm the company's own)"),
]
NEGATION = re.compile(r"\b(no|not|nil|without|never|zero|nor)\s+(?:any\s+|a\s+|the\s+)?(?:\w+\s+){0,2}$", re.I)
ANALYSED_TYPES = ("payment", "journal", "receipt", "purchase")


def _negated(text: str, start: int) -> bool:
    window = text[max(0, start - 30):start]
    window = re.split(r"[.;,:]", window)[-1]
    return bool(NEGATION.search(window))


def scan_narration(text: str) -> list[tuple[Theme, str]]:
    """Themes found in a narration, each with the words that matched. Negated mentions are ignored."""
    found = []
    for theme in THEMES:
        for m in theme.pattern.finditer(text or ""):
            if not _negated(text, m.start()):
                found.append((theme, m.group(0)))
                break
    return found


def narration_findings(recs, cfg, ledger_level, mk):
    out = []
    for r in recs:
        for theme, words in scan_narration(str(r["narration"] or "")):
            if theme.id == "cash_settle" and ledger_level:
                continue          # the ledger-level cash tests are authoritative; the wording only matters without ledger lines
            sev = theme.severity
            detail = f"The narration says '{words}': \"{' '.join(str(r['narration']).split())[:140]}\""
            if (theme.id == "cash_settle" and r["vch_type"].lower() == "payment" and r["total"] > cfg.cash_payment_limit
                    and not ledger_level):
                sev = "Medium"
                detail += (f". A cash payment of Rs {r['total']:,.0f} exceeds the Rs {cfg.cash_payment_limit:,.0f} limit "
                           "(this export has no ledger lines, so the payee is taken from the narration).")
            out.append(mk(R_NARR_PREFIX + theme.label, sev, r, detail, "", None, theme.reference))
    return out


def threshold_findings(recs, cfg, mk):
    """The '999' test: amounts ending in 999, or just under a statutory threshold."""
    out = []
    pct = cfg.near_threshold_pct / 100
    for r in recs:
        if r["vch_type"].lower() not in ANALYSED_TYPES:
            continue
        t = float(r["total"])
        reasons, near = [], None
        if t >= 9_999 and int(t) % 1000 == 999:
            reasons.append(f"ends in 999 (Rs {t:,.2f})")
        for limit, why in THRESHOLDS:
            if limit * (1 - pct) <= t < limit:
                near = (limit, why)
                reasons.append(f"is just under Rs {limit:,.0f} ({why})")
                break
        if reasons:
            out.append(mk(R_NEAR, "Medium" if near else "Low", r,
                          f"The amount " + " and ".join(reasons) + ". Check whether it was set to stay under a limit, "
                          "or split from a larger payment.", "", None,
                          "Amounts hugging a threshold are a standard avoidance indicator (SA 240, journal entry and "
                          "transaction testing)."))
    return out


def _party(r) -> str:
    skip = re.compile(r"bank|\bcash\b|hdfc|icici|\bsbi\b|axis|kotak|\b(cgst|sgst|igst|tds|gst)\b", re.I)
    lines = sorted(r["dr_lines"] + r["cr_lines"], key=lambda x: -x[1])
    for ledger, _ in lines:
        if not skip.search(ledger):
            return ledger
    return lines[0][0] if lines else ""


def repeated_findings(recs, cfg, mk):
    """The same amount to the same party three or more times within a month: splitting or a repeated payment."""
    groups = defaultdict(list)
    for r in recs:
        if r["vch_type"].lower() in ANALYSED_TYPES and r["total"] >= cfg.duplicate_min and pd.notna(r["date"]):
            groups[(_party(r), round(float(r["total"]), 2))].append(r)
    out = []
    for (party, amount), rs_ in groups.items():
        rs_ = sorted(rs_, key=lambda x: x["date"])
        i = 0
        while i < len(rs_):
            window = [x for x in rs_[i:] if (x["date"] - rs_[i]["date"]).days <= cfg.repeat_days]
            if len(window) >= cfg.repeat_min:
                nos = ", ".join(str(x["vch_no"]) for x in window)
                out.append(mk(R_REPEAT, "Medium", window[0],
                              f"Rs {amount:,.2f} appears {len(window)} times for {party or 'the same party'} within "
                              f"{cfg.repeat_days} days (vouchers {nos}).", party, amount,
                              "Repeated identical amounts can indicate payment splitting or duplicate processing."))
                i += len(window)
            else:
                i += 1
    return out


BENFORD = [math.log10(1 + 1 / d) for d in range(1, 10)]


def benford_findings(recs, cfg, mk):
    """First-digit screen. Only a screening indicator: auto-generated, rounded or capped data also trips it."""
    amounts = [float(r["total"]) for r in recs if r["vch_type"].lower() != "contra" and r["total"] >= 10]
    n = len(amounts)
    if n < cfg.benford_min:
        return []
    counts = Counter(int(str(int(a))[0]) for a in amounts)
    chi = sum((counts.get(d, 0) - n * BENFORD[d - 1]) ** 2 / (n * BENFORD[d - 1]) for d in range(1, 10))
    if chi < 15.51:      # 5% critical value, 8 degrees of freedom
        return []
    sev = "Medium" if chi >= 20.09 else "Low"           # 1% critical value
    dev = sorted(range(1, 10), key=lambda d: -(counts.get(d, 0) / n - BENFORD[d - 1]))
    top = ", ".join(f"{d} ({counts.get(d, 0) / n:.0%} against {BENFORD[d - 1]:.0%} expected)" for d in dev[:2])
    return [mk(R_BENFORD, sev, recs[0],
               f"Across {n:,} voucher amounts the first digits differ from Benford's law (chi-square {chi:.1f}, "
               f"critical value 15.5 at 5%). Most over-represented: {top}. Screening indicator only.", "", 0.0,
               "Benford's law: in natural financial data about 30% of amounts begin with 1. Large departures can "
               "point to invented, capped or manipulated amounts.")]
