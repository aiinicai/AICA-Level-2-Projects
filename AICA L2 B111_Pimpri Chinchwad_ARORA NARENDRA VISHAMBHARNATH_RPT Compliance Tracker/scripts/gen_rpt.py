"""
Related Party Transactions Compliance Tracker - sample data and answer key generator.

Creates:
  1. RPT_Sample_Upload.xlsx  - the file a user uploads to the app (fictitious company)
       Company          : company profile and the figures the limits are based on
       Transactions     : Tally day book layout (detailed), FY 2025-26
       Related_Parties  : related party list with relationship, basis and closing balance
       Approvals        : audit committee, board and shareholder approvals register
  2. RPT_Answer_Key.xlsx     - expected results for both modes, computed independently
  3. answer_key.json         - the same expected results, used by the app's acceptance test

Usage: python gen_rpt.py <output folder>
All names and figures are fictitious.
"""
import json
import os
import sys
from datetime import date

import numpy as np
import pandas as pd

OUT = sys.argv[1] if len(sys.argv) > 1 else "."
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(20261120)

# ---------------------------------------------------------------- company profile
COMPANY = {
    "Company name": "Sahyadri Precision Components Ltd",
    "Company type": "Public company with an audit committee (listing status chosen at upload)",
    "Financial year under review": "2025-26",
    "FY start": "2025-04-01",
    "FY end": "2026-03-31",
    "Standalone turnover, FY 2024-25 (Rs)": 4_800_000_000,      # Rs 480 crore
    "Net worth at 31-Mar-2025 (Rs)": 2_200_000_000,             # Rs 220 crore
    "Consolidated turnover, FY 2024-25 (Rs)": 5_200_000_000,    # Rs 520 crore
    "Paid-up share capital (Rs)": 250_000_000,                  # Rs 25 crore
}
TURNOVER = COMPANY["Standalone turnover, FY 2024-25 (Rs)"]
NETWORTH = COMPANY["Net worth at 31-Mar-2025 (Rs)"]
CONSOL = COMPANY["Consolidated turnover, FY 2024-25 (Rs)"]

# ---------------------------------------------------------------- limits (Rules and limits page)
ORDINARY_COURSE = {"Sale of goods", "Purchase of goods", "Availing of services", "Rendering of services"}
ARM_LENGTH_TOLERANCE = 0.10          # screening test, not a legal limit
RULE15_PCT = 0.10                    # Rule 15(3): goods, services, leasing -> turnover; property -> net worth
RULE15_OFFICE_MONTHLY = 250_000      # Rule 15(3)(f): office or place of profit, monthly remuneration


def sebi_material_threshold(consol_turnover):
    """SEBI LODR Schedule XII (effective 19 Dec 2025), amounts in Rs."""
    cr = 10_000_000
    t = consol_turnover
    if t <= 20_000 * cr:
        return 0.10 * t
    if t <= 40_000 * cr:
        return 2_000 * cr + 0.05 * (t - 20_000 * cr)
    return min(3_000 * cr + 0.025 * (t - 40_000 * cr), 5_000 * cr)


SEBI_THRESHOLD = sebi_material_threshold(CONSOL)

# ---------------------------------------------------------------- related parties
RP = [
    # party, relationship, recognised under, Ind AS 24 category, interested director/KMP, closing balance, balance nature
    ["Sahyadri Holdings Pvt Ltd", "Holding company (holds 52%)", "Companies Act, SEBI and Ind AS 24", "Holding company", "Mr Vikram Joshi (MD, common director)", 60_000_000, "Receivable"],
    ["Sahyadri Castings Pvt Ltd", "Subsidiary (74% held)", "Companies Act, SEBI and Ind AS 24", "Subsidiary", "", 92_000_000, "Payable"],
    ["Pune Precision Gears Pvt Ltd", "Associate (30% held)", "Companies Act, SEBI and Ind AS 24", "Associate", "", 21_000_000, "Receivable"],
    ["Deccan Tooling LLP", "LLP in which the MD is a partner", "Companies Act, SEBI and Ind AS 24", "Entity controlled by KMP", "Mr Vikram Joshi (MD)", 12_500_000, "Payable"],
    ["Westghat Realty Pvt Ltd", "Private company in which a director is a director and member", "Companies Act, SEBI and Ind AS 24", "Entity in which a director has significant influence", "Ms Anita Rao (Non-executive director)", 4_000_000, "Payable"],
    ["Kavya Joshi", "Daughter of the MD (relative)", "Companies Act, SEBI and Ind AS 24", "Close member of the family of KMP", "Mr Vikram Joshi (MD)", 300_000, "Payable"],
    ["Konkan Logistics Ltd", "Promoter group entity", "SEBI only", "Not a related party under Ind AS 24", "", 7_500_000, "Payable"],
    ["Nilgiri Capital Advisors LLP", "Shareholder holding 12%", "SEBI only", "Not a related party under Ind AS 24", "", 1_000_000, "Payable"],
]
rp_df = pd.DataFrame(RP, columns=["Party", "Relationship", "Recognised under", "Ind AS 24 category",
                                  "Interested director or KMP", "Closing balance 31-Mar-2026 (Rs)", "Balance nature"])
SEBI_ONLY = set(rp_df.loc[rp_df["Recognised under"] == "SEBI only", "Party"])
ALL_RP = set(rp_df["Party"])

# ---------------------------------------------------------------- approvals register
A = [
    # id, party, nature, body, type, approval date, valid from, valid to, limit, interested director(s), recused, reference
    ["A01", "Sahyadri Castings Pvt Ltd", "Purchase of goods", "Audit Committee", "Omnibus", "2025-03-27", "2025-04-01", "2026-03-31", 600_000_000, "", "Not applicable", "AC/2024-25/14"],
    ["A02", "Deccan Tooling LLP", "Purchase of goods", "Audit Committee", "Omnibus", "2025-03-27", "2025-04-01", "2026-03-31", 60_000_000, "Mr Vikram Joshi", "Not applicable", "AC/2024-25/15"],
    ["A03", "Pune Precision Gears Pvt Ltd", "Sale of goods", "Audit Committee", "Omnibus", "2025-03-27", "2025-04-01", "2025-09-30", 150_000_000, "", "Not applicable", "AC/2024-25/16"],
    ["A04", "Westghat Realty Pvt Ltd", "Leasing of property", "Audit Committee", "Specific", "2025-03-27", "2025-04-01", "2026-03-31", 48_000_000, "Ms Anita Rao", "Not applicable", "AC/2024-25/17"],
    ["A05", "Westghat Realty Pvt Ltd", "Leasing of property", "Board", "Specific", "2025-03-28", "2025-04-01", "2026-03-31", 48_000_000, "Ms Anita Rao", "No", "BM/2024-25/22"],
    ["A06", "Kavya Joshi", "Office or place of profit", "Audit Committee", "Specific", "2025-03-27", "2025-04-01", "2026-03-31", 3_600_000, "Mr Vikram Joshi", "Not applicable", "AC/2024-25/18"],
    ["A07", "Kavya Joshi", "Office or place of profit", "Board", "Specific", "2025-03-28", "2025-04-01", "2026-03-31", 3_600_000, "Mr Vikram Joshi", "Yes", "BM/2024-25/23"],
    ["A08", "Sahyadri Holdings Pvt Ltd", "Sale of property", "Audit Committee", "Specific", "2025-10-20", "2025-10-20", "2026-03-31", 260_000_000, "Mr Vikram Joshi", "Not applicable", "AC/2025-26/09"],
    ["A09", "Sahyadri Holdings Pvt Ltd", "Sale of property", "Board", "Specific", "2025-10-22", "2025-10-22", "2026-03-31", 260_000_000, "Mr Vikram Joshi", "Yes", "BM/2025-26/11"],
    ["A10", "Sahyadri Holdings Pvt Ltd", "Sale of property", "Shareholders", "Specific", "2025-11-25", "2025-11-25", "2026-03-31", 260_000_000, "Related parties did not vote", "Yes", "EGM/2025-26/01"],
    ["A11", "Nilgiri Capital Advisors LLP", "Availing of services", "Audit Committee", "Specific", "2025-03-27", "2025-04-01", "2026-03-31", 15_000_000, "", "Not applicable", "AC/2024-25/19"],
]
ap_df = pd.DataFrame(A, columns=["Approval ID", "Party", "Nature", "Approving body", "Approval type", "Approval date",
                                 "Valid from", "Valid to", "Limit (Rs)", "Interested director(s)",
                                 "Interested director stayed out", "Reference"])

# ---------------------------------------------------------------- transactions (Tally day book, detailed)
months = [(2025, m) for m in range(4, 13)] + [(2026, m) for m in range(1, 4)]
rows = []
vno = {"Sales": 0, "Purchase": 0, "Journal": 0}


def add(d, party, vtype, item, qty, unit, rate, nature, side):
    vno[vtype] += 1
    amt = int(round(qty * rate))
    rows.append({
        "Date": d, "Particulars": party, "Vch Type": vtype,
        "Vch No.": f"{vtype[:2].upper()}/{vno[vtype]:04d}",
        "Item": item, "Quantity": qty, "Unit": unit, "Rate": rate,
        "Debit Amount": amt if side == "Dr" else None,
        "Credit Amount": amt if side == "Cr" else None,
        "Nature": nature,
    })


for (y, m) in months:
    d1, d2 = date(y, m, 8), date(y, m, 22)
    # castings: related subsidiary at market rate, two unrelated foundries
    for d in (d1, d2):
        add(d, "Sahyadri Castings Pvt Ltd", "Purchase", "MS castings", int(round(23_000_000 / 147)), "kg", 147.0, "Purchase of goods", "Cr")
        for v in ("Bharat Foundry Works", "Malwa Castings Ltd"):
            r = float(round(rng.uniform(141, 149), 2))
            add(d, v, "Purchase", "MS castings", int(round(rng.uniform(6.5e6, 8.5e6) / r)), "kg", r, "Purchase of goods", "Cr")
    # carbide inserts: related LLP at about 18% above market
    for d in (d1, d2):
        add(d, "Deccan Tooling LLP", "Purchase", "Carbide inserts", int(round(3_000_000 / 1003)), "pcs", 1003.0, "Purchase of goods", "Cr")
        for v in ("Precision Tools India", "Toolcraft Engineers"):
            r = float(round(rng.uniform(830, 870), 2))
            add(d, v, "Purchase", "Carbide inserts", int(round(rng.uniform(1.8e6, 2.2e6) / r)), "pcs", r, "Purchase of goods", "Cr")
    # gear assemblies: sales to associate and five unrelated customers
    for d in (d1, d2):
        add(d, "Pune Precision Gears Pvt Ltd", "Sales", "Gear assembly GA-200", int(round(5_000_000 / 4150)), "nos", 4150.0, "Sale of goods", "Dr")
        for c in ("Ashoka Motors Ltd", "Narmada Tractors Ltd", "Coromandel Auto Parts Ltd", "Satpura Engineering Ltd", "Indus Earthmovers Ltd"):
            r = float(round(rng.uniform(4080, 4320), 2))
            add(d, c, "Sales", "Gear assembly GA-200", int(round(rng.uniform(1.5e7, 3.0e7) / r)), "nos", r, "Sale of goods", "Dr")
    # freight: promoter group transporter and two unrelated transporters
    add(date(y, m, 28), "Konkan Logistics Ltd", "Purchase", "Freight", 195, "trips", 38461.5, "Availing of services", "Cr")
    for v in ("Shree Ganesh Roadways", "Western Cargo Movers"):
        r = float(round(rng.uniform(37000, 39500), 0))
        add(date(y, m, 28), v, "Purchase", "Freight", int(rng.integers(80, 121)), "trips", r, "Availing of services", "Cr")
    # monthly items with no market comparable
    add(date(y, m, 28), "Nilgiri Capital Advisors LLP", "Purchase", "Advisory retainer", 1, "month", 1_000_000.0, "Availing of services", "Cr")
    add(date(y, m, 1), "Westghat Realty Pvt Ltd", "Journal", "Office rent", 1, "month", 4_000_000.0, "Leasing of property", "Cr")
    add(date(y, m, 28) if m != 2 else date(y, m, 27), "Kavya Joshi", "Journal", "Salary", 1, "month", 300_000.0, "Office or place of profit", "Cr")

# one-off sale of land to the holding company
add(date(2025, 12, 15), "Sahyadri Holdings Pvt Ltd", "Journal", "Land at Chakan, Plot 14", 1, "plot", 260_000_000.0, "Sale of property", "Dr")

tx = pd.DataFrame(rows).sort_values(["Date", "Vch Type", "Vch No."]).reset_index(drop=True)
tx["Amount"] = tx["Debit Amount"].fillna(0) + tx["Credit Amount"].fillna(0)
tx["Direction"] = np.where(tx["Debit Amount"].notna(), "Dr", "Cr")

# ================================================================= ANSWER KEY (independent of the app)
FY_START, FY_END = pd.Timestamp("2025-04-01"), pd.Timestamp("2026-03-31")
tx["DateTS"] = pd.to_datetime(tx["Date"])
ap = ap_df.copy()
for c in ("Approval date", "Valid from", "Valid to"):
    ap[c] = pd.to_datetime(ap[c])


def covered(party, nature, body, d):
    a = ap[(ap.Party == party) & (ap.Nature == nature) & (ap["Approving body"] == body)
           & (ap["Approval date"] <= d) & (ap["Valid from"] <= d) & (ap["Valid to"] >= d)]
    return a


def market_test():
    """C4: weighted average rate with related party vs unrelated parties, same item, same direction."""
    res = {}
    unrel = tx[~tx.Particulars.isin(ALL_RP)]
    for (party, item), g in tx[tx.Particulars.isin(ALL_RP)].groupby(["Particulars", "Item"]):
        u = unrel[(unrel.Item == item) & (unrel.Direction == g.Direction.iloc[0])]
        if u.empty:
            res[(party, item)] = {"tested": False}
            continue
        rp_rate = g.Amount.sum() / g.Quantity.sum()
        mkt_rate = u.Amount.sum() / u.Quantity.sum()
        dev = rp_rate / mkt_rate - 1
        unfavourable = dev > ARM_LENGTH_TOLERANCE if g.Direction.iloc[0] == "Cr" else dev < -ARM_LENGTH_TOLERANCE
        cost = (rp_rate - mkt_rate) * g.Quantity.sum() if g.Direction.iloc[0] == "Cr" else (mkt_rate - rp_rate) * g.Quantity.sum()
        res[(party, item)] = {"tested": True, "rp_rate": rp_rate, "mkt_rate": mkt_rate, "deviation": dev,
                              "flag": bool(unfavourable), "excess_cost": cost if unfavourable else 0.0}
    return res


MT = market_test()


def run(mode):
    listed = mode == "Listed"
    rps = ALL_RP if listed else ALL_RP - SEBI_ONLY
    r = tx[tx.Particulars.isin(rps) & (tx.DateTS >= FY_START) & (tx.DateTS <= FY_END)].copy()
    exc = []

    # C2: no valid audit committee approval covering the transaction
    r["ac_ok"] = [not covered(p, n, "Audit Committee", d).empty for p, n, d in zip(r.Particulars, r.Nature, r.DateTS)]
    for (p, n), g in r[~r.ac_ok].groupby(["Particulars", "Nature"]):
        why = "No audit committee approval on record" if covered(p, n, "Audit Committee", FY_END).empty and ap[(ap.Party == p) & (ap["Approving body"] == "Audit Committee")].empty \
            else "Audit committee approval had lapsed for these transactions"
        exc.append({"Check": "C2", "Party": p, "Nature": n, "Amount (Rs)": int(g.Amount.sum()),
                    "Finding": f"{why} ({len(g)} vouchers, {g.DateTS.min():%d-%b-%Y} to {g.DateTS.max():%d-%b-%Y})",
                    "Law": "Sec 177(4)(iv) Companies Act" + ("; Reg 23(2) SEBI LODR" if listed else "")})

    # C3: approved limit exceeded (audit committee approvals)
    for _, a in ap[ap["Approving body"] == "Audit Committee"].iterrows():
        g = r[(r.Particulars == a.Party) & (r.Nature == a.Nature) & (r.DateTS >= a["Valid from"]) & (r.DateTS <= a["Valid to"])]
        if g.empty:
            continue
        used = g.Amount.sum()
        if used > a["Limit (Rs)"]:
            exc.append({"Check": "C3", "Party": a.Party, "Nature": a.Nature, "Amount (Rs)": int(used - a["Limit (Rs)"]),
                        "Finding": f"Transactions of Rs {used:,.0f} against approved limit of Rs {a['Limit (Rs)']:,.0f} ({a['Approval ID']})",
                        "Law": "Sec 177(4)(iv), Rule 6A"})

    # C4: price away from market
    for (p, item), t in MT.items():
        if p in rps and t["tested"] and t["flag"]:
            n = r[(r.Particulars == p) & (r.Item == item)].Nature.iloc[0]
            exc.append({"Check": "C4", "Party": p, "Nature": n, "Amount (Rs)": int(round(t["excess_cost"])),
                        "Finding": f"{item}: average rate Rs {t['rp_rate']:,.2f} vs Rs {t['mkt_rate']:,.2f} with unrelated parties ({t['deviation']:+.1%}); estimated excess cost shown",
                        "Law": "Sec 188(1) arm's length test (screening at 10%)"})

    # C5 / C6: Section 188 board and shareholder approval
    for (p, n), g in r.groupby(["Particulars", "Nature"]):
        items = g.Item.unique()
        not_arm = any(MT.get((p, i), {}).get("flag", False) for i in items)
        if n in ORDINARY_COURSE and not not_arm:
            continue  # Section 188 does not apply
        reason = "not in the ordinary course of business" if n not in ORDINARY_COURSE else "not at arm's length (C4)"
        total = g.Amount.sum()
        if not all(not covered(p, n, "Board", d).empty for d in g.DateTS):
            exc.append({"Check": "C5", "Party": p, "Nature": n, "Amount (Rs)": int(total),
                        "Finding": f"Section 188 applies ({reason}); no board approval on record",
                        "Law": "Sec 188(1) Companies Act"})
        if n == "Office or place of profit":
            monthly = g.Amount.max()
            crosses, limit_txt = monthly > RULE15_OFFICE_MONTHLY, f"monthly remuneration Rs {monthly:,.0f} exceeds Rs {RULE15_OFFICE_MONTHLY:,.0f}"
        elif n == "Sale of property" or n == "Purchase of property":
            crosses, limit_txt = total >= RULE15_PCT * NETWORTH, f"Rs {total:,.0f} is at or above 10% of net worth (Rs {RULE15_PCT*NETWORTH:,.0f})"
        else:
            crosses, limit_txt = total >= RULE15_PCT * TURNOVER, f"Rs {total:,.0f} is at or above 10% of turnover (Rs {RULE15_PCT*TURNOVER:,.0f})"
        if crosses and not all(not covered(p, n, "Shareholders", d).empty for d in g.DateTS):
            exc.append({"Check": "C6", "Party": p, "Nature": n, "Amount (Rs)": int(total),
                        "Finding": f"Shareholder approval needed: {limit_txt}; no resolution on record",
                        "Law": "Sec 188(1), Rule 15(3)"})

    # C7: interested director did not stay out of the board decision
    for _, a in ap[(ap["Approving body"] == "Board") & (ap["Interested director stayed out"] == "No")].iterrows():
        g = r[(r.Particulars == a.Party) & (r.Nature == a.Nature)]
        if not g.empty:
            exc.append({"Check": "C7", "Party": a.Party, "Nature": a.Nature, "Amount (Rs)": int(g.Amount.sum()),
                        "Finding": f"{a['Interested director(s)']} did not stay out of the board decision ({a['Reference']})",
                        "Law": "Sec 184(2) Companies Act"})

    # L2: material related party transaction (listed only)
    if listed:
        for p, g in r.groupby("Particulars"):
            total = g.Amount.sum()
            if total > SEBI_THRESHOLD:
                ok = all(not ap[(ap.Party == p) & (ap["Approving body"] == "Shareholders") & (ap["Approval date"] <= d)
                                & (ap["Valid from"] <= d) & (ap["Valid to"] >= d)].empty for d in g.DateTS)
                if not ok:
                    exc.append({"Check": "L2", "Party": p, "Nature": ", ".join(sorted(g.Nature.unique())), "Amount (Rs)": int(total),
                                "Finding": f"Material transaction: Rs {total:,.0f} with this party exceeds Rs {SEBI_THRESHOLD:,.0f} (10% of consolidated turnover); no prior shareholder approval",
                                "Law": "Reg 23(4) and Schedule XII, SEBI LODR"})

    order = {"C2": 2, "C3": 3, "C4": 4, "C5": 5, "C6": 6, "C7": 7, "L2": 9}
    exc = sorted(exc, key=lambda e: (order[e["Check"]], e["Party"]))
    summary = (r.groupby(["Particulars", "Nature"]).Amount.sum().reset_index()
               .rename(columns={"Particulars": "Party", "Amount": "FY 2025-26 (Rs)"}))
    return pd.DataFrame(exc), summary, r


results = {m: run(m) for m in ("Unlisted", "Listed")}

# Ind AS 24 summary (same in both modes: Ind AS 24 parties only)
ind = results["Unlisted"][2].merge(rp_df[["Party", "Ind AS 24 category"]], left_on="Particulars", right_on="Party")
ind24 = (ind.groupby(["Ind AS 24 category", "Party", "Nature"]).Amount.sum().reset_index()
         .rename(columns={"Amount": "FY 2025-26 (Rs)"}))
bal = rp_df[~rp_df.Party.isin(SEBI_ONLY)][["Party", "Closing balance 31-Mar-2026 (Rs)", "Balance nature"]]
ind24 = ind24.merge(bal, on="Party", how="left")

# AOC-2
aoc_rows = []
for (p, item), t in MT.items():
    if t["tested"] and t["flag"]:
        g = tx[(tx.Particulars == p) & (tx.Item == item)]
        aoc_rows.append({"Part": "1. Not at arm's length", "Party": p, "Relationship": rp_df.set_index("Party").loc[p, "Relationship"],
                         "Nature": g.Nature.iloc[0], "Duration": "FY 2025-26", "Value (Rs)": int(g.Amount.sum()),
                         "Board approval date": "Not obtained", "Shareholder approval date": "Not applicable"})
for (p, n), g in results["Unlisted"][2].groupby(["Particulars", "Nature"]):
    if any(MT.get((p, i), {}).get("flag", False) for i in g.Item.unique()):
        continue
    total = g.Amount.sum()
    if n == "Office or place of profit":
        material = g.Amount.max() > RULE15_OFFICE_MONTHLY
    elif n in ("Sale of property", "Purchase of property"):
        material = total >= RULE15_PCT * NETWORTH
    else:
        material = total >= RULE15_PCT * TURNOVER
    if material:
        b = ap[(ap.Party == p) & (ap.Nature == n) & (ap["Approving body"] == "Board")]
        s = ap[(ap.Party == p) & (ap.Nature == n) & (ap["Approving body"] == "Shareholders")]
        aoc_rows.append({"Part": "2. Material, at arm's length", "Party": p, "Relationship": rp_df.set_index("Party").loc[p, "Relationship"],
                         "Nature": n, "Duration": "FY 2025-26", "Value (Rs)": int(total),
                         "Board approval date": b["Approval date"].min().strftime("%d-%b-%Y") if not b.empty else "Not applicable (ordinary course, arm's length)",
                         "Shareholder approval date": s["Approval date"].min().strftime("%d-%b-%Y") if not s.empty else "Not obtained"})
aoc2 = pd.DataFrame(aoc_rows)

# market test table
mt_rows = []
for (p, item), t in MT.items():
    mt_rows.append({"Party": p, "Item": item, "Tested": "Yes" if t["tested"] else "No comparable",
                    "Related party rate (Rs)": round(t.get("rp_rate", 0), 2) if t["tested"] else None,
                    "Unrelated party rate (Rs)": round(t.get("mkt_rate", 0), 2) if t["tested"] else None,
                    "Deviation": round(t.get("deviation", 0), 4) if t["tested"] else None,
                    "Flag": "Yes" if t.get("flag") else "No"})
mt_df = pd.DataFrame(mt_rows)

limits = pd.DataFrame([
    ["Rule 15(3): goods, services, leasing", "10% of standalone turnover of the preceding year", RULE15_PCT * TURNOVER],
    ["Rule 15(3): sale or purchase of property", "10% of net worth of the preceding year", RULE15_PCT * NETWORTH],
    ["Rule 15(3)(f): office or place of profit", "Monthly remuneration above Rs 2.5 lakh", RULE15_OFFICE_MONTHLY],
    ["SEBI Schedule XII: material transaction", "10% of consolidated turnover (turnover up to Rs 20,000 crore)", SEBI_THRESHOLD],
    ["Market price screening (C4)", "Unfavourable deviation of more than 10% (our test parameter)", ARM_LENGTH_TOLERANCE],
], columns=["Limit", "Basis", "Value"])

# ================================================================= write files
upload_path = os.path.join(OUT, "RPT_Sample_Upload.xlsx")
key_path = os.path.join(OUT, "RPT_Answer_Key.xlsx")
tx_out = tx[["Date", "Particulars", "Vch Type", "Vch No.", "Item", "Quantity", "Unit", "Rate", "Debit Amount", "Credit Amount", "Nature"]]
comp_df = pd.DataFrame(list(COMPANY.items()), columns=["Field", "Value"])
with pd.ExcelWriter(upload_path, engine="openpyxl") as w:
    comp_df.to_excel(w, "Company", index=False)
    tx_out.to_excel(w, "Transactions", index=False)
    rp_df.to_excel(w, "Related_Parties", index=False)
    ap_out = ap_df.copy()
    for c in ("Approval date", "Valid from", "Valid to"):
        ap_out[c] = pd.to_datetime(ap_out[c]).dt.date
    ap_out.to_excel(w, "Approvals", index=False)

with pd.ExcelWriter(key_path, engine="openpyxl") as w:
    s = pd.DataFrame([
        ["Mode", "Unlisted", "Listed"],
        ["Related party transactions identified (Rs)", int(results["Unlisted"][2].Amount.sum()), int(results["Listed"][2].Amount.sum())],
        ["Related parties with transactions", results["Unlisted"][2].Particulars.nunique(), results["Listed"][2].Particulars.nunique()],
        ["Exceptions", len(results["Unlisted"][0]), len(results["Listed"][0])],
    ])
    s.to_excel(w, "Summary", index=False, header=False)
    results["Unlisted"][0].to_excel(w, "Unlisted_Exceptions", index=False)
    results["Listed"][0].to_excel(w, "Listed_Exceptions", index=False)
    results["Listed"][1].to_excel(w, "RPT_by_Party", index=False)
    mt_df.to_excel(w, "Market_Price_Test", index=False)
    ind24.to_excel(w, "IndAS24_Summary", index=False)
    aoc2.to_excel(w, "AOC2", index=False)
    limits.to_excel(w, "Limits", index=False)

key = {m: {"exceptions": [{k: (int(v) if isinstance(v, (np.integer,)) else v) for k, v in e.items()}
                          for e in results[m][0].to_dict("records")],
           "rpt_total": int(results[m][2].Amount.sum()),
           "rpt_parties": int(results[m][2].Particulars.nunique())}
       for m in results}
key["limits"] = {"rule15_turnover": RULE15_PCT * TURNOVER, "rule15_networth": RULE15_PCT * NETWORTH,
                 "rule15_office_monthly": RULE15_OFFICE_MONTHLY, "sebi_material": SEBI_THRESHOLD}
with open(os.path.join(OUT, "answer_key.json"), "w") as f:
    json.dump(key, f, indent=2, default=str)

# console summary
print("Vouchers:", len(tx), "| FY total value:", f"{tx.Amount.sum():,.0f}")
for m in results:
    e, sm, r = results[m]
    print(f"\n=== {m}: {len(e)} exceptions | RPT value {r.Amount.sum():,.0f} across {r.Particulars.nunique()} parties")
    for _, x in e.iterrows():
        print(f"  {x.Check} | {x.Party} | {x.Nature} | {x['Amount (Rs)']:,} | {x.Finding}")
print("\nMarket test:")
print(mt_df.to_string(index=False))
print("\nAOC-2:")
print(aoc2[["Part", "Party", "Nature", "Value (Rs)"]].to_string(index=False))
print("\nSEBI threshold:", f"{SEBI_THRESHOLD:,.0f}")
