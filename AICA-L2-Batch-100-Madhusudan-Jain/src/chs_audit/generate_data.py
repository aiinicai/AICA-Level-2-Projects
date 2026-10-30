"""Generate a realistic synthetic data set for a 64-flat housing society.

The data is fully synthetic. Names, mobile numbers and PANs are invented and
PANs are stored masked, mirroring how a firm should hold member data under the
DPDP Act 2023. A number of control failures are deliberately seeded so the
audit modules have something to find; they are listed in SEEDED_ISSUES.
"""
from __future__ import annotations

import calendar
import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from .config import FLAT_TYPES, MONTHS, RATES, SOCIETY, month_label

SEED = 20250401
rng = random.Random(SEED)

FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Rohan", "Kunal", "Siddharth", "Nikhil", "Rahul",
    "Priya", "Sneha", "Anjali", "Pooja", "Neha", "Kavita", "Meera", "Shruti",
    "Rajesh", "Suresh", "Mahesh", "Ganesh", "Prakash", "Dinesh", "Ramesh", "Sanjay",
    "Sunita", "Anita", "Vandana", "Rekha", "Smita", "Lata", "Asha", "Usha",
    "Farhan", "Imran", "Zoya", "Sameer", "Joseph", "Anthony", "Rosy", "Gurpreet",
]
LAST_NAMES = [
    "Sharma", "Patil", "Deshmukh", "Joshi", "Kulkarni", "Shah", "Mehta", "Iyer",
    "Nair", "Reddy", "Gupta", "Agarwal", "Verma", "Singh", "Khan", "Shaikh",
    "D'Souza", "Fernandes", "Jain", "Bhatt", "Chavan", "More", "Pawar", "Jadhav",
]

PROFILES = {
    # name: (pay_day_offset_range, pays_full_due, pay_fraction, stop_month_index)
    "punctual": ((3, 13), True, 1.0, None),
    "late": ((20, 45), False, 1.0, None),
    "partial": ((5, 25), False, 0.6, None),
    "defaulter_oct": ((5, 13), True, 1.0, 6),       # stops paying from Oct-2025
    "chronic": ((0, 0), False, 0.0, 0),              # pays nothing all year
}

SEEDED_ISSUES = [
    "A-402 (Secretary): interest on arrears never charged although bills paid 20-45 days late",
    "B-101 and B-502: interest charged at 18% instead of the 21% adopted by the General Body",
    "GST charged on 3BHK bills including the property tax component (over-charge)",
    "B-604 (3BHK, above Rs 7,500): GST not charged for Jun-Aug 2025 (under-charge)",
    "A-201 (2BHK, below Rs 7,500): GST wrongly charged for the whole year",
    "Receipt R-0233 cheque bounced in bank; reversal never recorded in books",
    "Unidentified NEFT credit of Rs 6,770 on 12-Nov-2025 not recorded in receipts register",
    "Housekeeping invoice SRV/2025/08-14 paid twice (duplicate payment)",
    "Terrace waterproofing Rs 1,45,000 split into three invoices below the Rs 50,000 committee limit",
    "Patil Plumbing Works shares address with Treasurer's flat B-203 (related party, no disclosure)",
    "No TDS on accountant fees of Rs 96,000 (s.194J threshold Rs 50,000)",
    "TDS on security agency (partnership firm) deducted at 1% instead of 2% u/s 194C",
    "Cash payments above Rs 10,000 to painter and electrician",
    "Sinking fund collections Rs 5.3 lakh but only Rs 4.8 lakh transferred to sinking fund",
    "Sinking fund Rs 43.8 lakh vs FDs of Rs 32 lakh: fund not fully invested (bye-law 15 / s.70)",
    "MC meeting of 12-Oct-2025 lacked quorum (4 of 11) yet approved expenditure",
    "AGM 2025 notice issued 10 days before meeting (bye-law requires 14 clear days)",
    "Structural audit overdue (last 20-Mar-2021, 5-year cycle); lift licence expires 15-Sep-2026 with no renewal filed",
    "No advance tax paid although liability exceeds Rs 10,000 (s.234B/234C exposure)",
]


def _name(i: int) -> str:
    return f"{FIRST_NAMES[i % len(FIRST_NAMES)]} {LAST_NAMES[(i * 7) % len(LAST_NAMES)]}"


def _masked_pan(i: int) -> str:
    return f"{chr(65 + i % 26)}{chr(65 + (i * 3) % 26)}{chr(65 + (i * 5) % 26)}P{chr(65 + (i * 11) % 26)}****{chr(65 + (i * 13) % 26)}"


def _mobile() -> str:
    return f"9{rng.randint(10_000, 99_999)}XXXXX"


def build_members() -> pd.DataFrame:
    rows = []
    i = 0
    tenanted = {"A-201", "A-304", "A-504", "A-703", "B-102", "B-304", "B-404", "B-601", "B-604", "B-803", "A-602", "B-203"}
    # B-203 is treasurer's flat; a tenanted committee member is itself a point to flag
    profile_map = {}
    chronic = ["A-303", "B-703", "A-103"]
    defaulter_oct = ["B-201", "A-504", "B-803"]
    partial = ["A-601", "B-301", "A-203", "B-404"]
    late = ["A-402", "B-101", "B-502", "A-704", "B-602", "A-801", "B-702", "A-202", "B-104", "A-401"]
    for f in chronic:
        profile_map[f] = "chronic"
    for f in defaulter_oct:
        profile_map[f] = "defaulter_oct"
    for f in partial:
        profile_map[f] = "partial"
    for f in late:
        profile_map[f] = "late"
    opening_arrears = {"A-303": 148_600.0, "B-703": 96_400.0, "A-103": 61_250.0, "A-601": 18_300.0, "B-301": 12_800.0}
    for wing in SOCIETY.wings:
        for floor in range(1, SOCIETY.floors + 1):
            for unit in range(1, SOCIETY.flats_per_floor + 1):
                flat = f"{wing}-{floor}{unit:02d}"
                ftype, area, parking = FLAT_TYPES[unit]
                rows.append({
                    "flat_no": flat,
                    "wing": wing,
                    "floor": floor,
                    "flat_type": ftype,
                    "carpet_area_sqft": area,
                    "member_name": _name(i),
                    "mobile": _mobile(),
                    "pan_masked": _masked_pan(i),
                    "share_certificate_no": f"SC-{i + 1:03d}",
                    "member_since": date(2009 + (i % 12), 1 + (i % 12), 1 + (i % 27)),
                    "occupancy": "Tenant" if flat in tenanted else "Self",
                    "car_parking": parking,
                    "committee_member": flat in SOCIETY.committee_flats,
                    "payment_profile": profile_map.get(flat, "punctual"),
                    "opening_arrears": opening_arrears.get(flat, 0.0),
                })
                i += 1
    return pd.DataFrame(rows)


def bill_components(m: pd.Series) -> dict:
    cost = m.carpet_area_sqft * RATES.construction_cost_per_sqft
    service = RATES.service_charges_per_flat
    comp = {
        "property_tax": round(m.carpet_area_sqft * RATES.property_tax_per_sqft_month, 2),
        "water_charges": RATES.water_charges_per_flat,
        "sinking_fund": round(cost * RATES.sinking_fund_rate / 12, 2),
        "repair_fund": round(cost * RATES.repair_fund_rate / 12, 2),
        "service_charges": service,
        "non_occupancy_charges": round(service * RATES.non_occupancy_pct, 2) if m.occupancy == "Tenant" else 0.0,
        "parking_charges": RATES.car_parking_per_month if m.car_parking else 0.0,
    }
    return comp


def _last_day(y: int, m: int) -> date:
    return date(y, m, calendar.monthrange(y, m)[1])


def build_bills_and_receipts(members: pd.DataFrame):
    """Bills are raised on the 1st; interest is charged on the amount actually outstanding
    on the bill date (date-based), so a member paying 20-45 days late carries arrears into
    the next bill and attracts interest under bye-law 72."""
    bills, receipts = [], []
    rno = 1
    for _, m in members.iterrows():
        prof = PROFILES[m.payment_profile]
        billed_so_far = float(m.opening_arrears)
        my_receipts: list[tuple[date, float]] = []
        for idx, (y, mo) in enumerate(MONTHS):
            bill_date = date(y, mo, 1)
            due_date = date(y, mo, RATES.bill_due_day)
            received_before = sum(a for (dt, a) in my_receipts if dt < bill_date)
            arrears = round(billed_so_far - received_before, 2)
            comp = bill_components(m)
            base_total = round(sum(comp.values()), 2)
            correct_interest = round(arrears * RATES.arrears_interest_rate / 12, 2) if arrears > 0 else 0.0
            soc_interest = correct_interest
            if m.flat_no == SOCIETY.secretary_flat:
                soc_interest = 0.0                       # seeded: secretary never charged
            elif m.flat_no in ("B-101", "B-502"):
                soc_interest = round(arrears * 0.18 / 12, 2) if arrears > 0 else 0.0
            # GST as charged by the society (flawed logic)
            soc_gst = 0.0
            if m.flat_type == "3BHK":
                if not (m.flat_no == "B-604" and idx in (2, 3, 4)):
                    soc_gst = round(base_total * RATES.gst_rate, 2)   # includes property tax: error
            if m.flat_no == "A-201":
                soc_gst = round(base_total * RATES.gst_rate, 2)       # wrongly charged
            bill_total = round(base_total + soc_interest + soc_gst, 2)
            bills.append({
                "bill_no": f"MB/{y}{mo:02d}/{m.flat_no}",
                "flat_no": m.flat_no,
                "bill_month": month_label(y, mo),
                "bill_date": bill_date,
                "due_date": due_date,
                **comp,
                "interest_on_arrears": soc_interest,
                "gst_charged": soc_gst,
                "bill_total": bill_total,
                "arrears_bf": arrears,
            })
            billed_so_far = round(billed_so_far + bill_total, 2)
            # payment behaviour for this bill
            if m.payment_profile == "chronic":
                paid = 0.0
            elif m.payment_profile == "defaulter_oct" and idx >= prof[3]:
                paid = 0.0
            else:
                lo, hi = prof[0]
                pay_date = bill_date + timedelta(days=rng.randint(lo, hi))
                outstanding_at_pay = billed_so_far - sum(a for (dt, a) in my_receipts if dt <= pay_date)
                due_amount = outstanding_at_pay if prof[1] else bill_total
                paid = round(max(due_amount, 0) * prof[2], 2)
                if paid > 0:
                    mode = rng.choices(["UPI", "NEFT", "Cheque"], weights=[55, 30, 15])[0]
                    my_receipts.append((pay_date, paid))
                    receipts.append({
                        "receipt_no": f"R-{rno:04d}",
                        "flat_no": m.flat_no,
                        "receipt_date": pay_date,
                        "amount": paid,
                        "mode": mode,
                        "reference": f"{mode[:3].upper()}{rng.randint(100000, 999999)}",
                        "against_bill": f"MB/{y}{mo:02d}/{m.flat_no}",
                    })
                    rno += 1
    bills_df = pd.DataFrame(bills)
    rec_df = pd.DataFrame(receipts).sort_values("receipt_date").reset_index(drop=True)
    rec_df["receipt_no"] = [f"R-{i + 1:04d}" for i in range(len(rec_df))]
    return bills_df, rec_df


VENDORS = [
    # code, name, category, entity_type, pan_masked, address, tds_section
    ("V01", "SecureGuard Facility Services", "Security", "Firm", "AAAFS****Q", "Wagle Estate, Thane", "194C"),
    ("V02", "Swachh Housekeeping Services", "Housekeeping", "Individual", "BXYPS****K", "Majiwada, Thane", "194C"),
    ("V03", "Maharashtra State Electricity Distribution Co. Ltd", "Electricity", "Govt", "-", "Thane", None),
    ("V04", "Thane Municipal Corporation", "Municipal", "Govt", "-", "Thane", None),
    ("V05", "Otis Elevator Co. (India) Ltd", "Lift AMC", "Company", "AAACO****P", "Mumbai", "194C"),
    ("V06", "New India Assurance Co. Ltd", "Insurance", "Company", "AAACN****L", "Mumbai", None),
    ("V07", "R. K. Kadam & Associates", "Accounting fees", "Firm", "AAIFR****M", "Naupada, Thane", "194J"),
    ("V08", "M/s Desai Legal LLP", "Legal fees", "Firm", "AAJFD****R", "Fort, Mumbai", "194J"),
    ("V09", "Patil Plumbing Works", "Repairs - plumbing", "Individual", "AKLPP****H", "Flat B-203, Sunrise Heights, Ghodbunder Road, Thane (W)", "194C"),
    ("V10", "Shree Waterproofing Contractors", "Repairs - civil", "Individual", "BBCPS****D", "Kalwa, Thane", "194C"),
    ("V11", "GreenLeaf Garden Services", "Garden", "Individual", "CDEPG****F", "Kasarvadavali, Thane", "194C"),
    ("V12", "PestFree Solutions", "Pest control", "Firm", "AAEFP****W", "Mulund, Mumbai", "194C"),
    ("V13", "Sai Painter (cash)", "Repairs - painting", "Individual", "-", "Thane", "194C"),
    ("V14", "Vijay Electricals (cash)", "Repairs - electrical", "Individual", "-", "Thane", "194C"),
    ("V15", "SocietyHub Software Pvt Ltd", "Software subscription", "Company", "AAHCS****Z", "Pune", "194J"),
    ("V16", "Kalpana Printers", "Printing & stationery", "Individual", "-", "Thane", None),
    ("V17", "Statutory Auditor - Jain Jakhotiya & Associates", "Audit fees", "Firm", "AAOFS****J", "Thane", "194J"),
]


def build_vendors() -> pd.DataFrame:
    return pd.DataFrame(VENDORS, columns=["vendor_code", "vendor_name", "category", "entity_type", "pan_masked", "address", "tds_section"])


def build_expenses() -> pd.DataFrame:
    rows = []
    n = 1

    def add(vcode, inv_date, amount, desc, mode="NEFT", tds_rate=None, approved_by="MC", inv_no=None, pay_lag=None, gst=0.18):
        nonlocal n
        v = next(x for x in VENDORS if x[0] == vcode)
        lag = pay_lag if pay_lag is not None else rng.randint(2, 12)
        pay_date = inv_date + timedelta(days=lag)
        taxable = amount
        gst_amt = round(taxable * gst, 2) if gst else 0.0
        gross = round(taxable + gst_amt, 2)
        tds = round(taxable * tds_rate, 2) if tds_rate else 0.0
        rows.append({
            "voucher_no": f"PV-{n:04d}",
            "vendor_code": vcode,
            "vendor_name": v[1],
            "category": v[2],
            "invoice_no": inv_no or f"{vcode}/{inv_date:%y%m}/{rng.randint(10, 99)}",
            "invoice_date": inv_date,
            "payment_date": pay_date,
            "description": desc,
            "taxable_value": taxable,
            "gst_on_invoice": gst_amt,
            "gross_amount": gross,
            "tds_deducted": tds,
            "net_paid": round(gross - tds, 2),
            "payment_mode": mode,
            "approved_by": approved_by,
        })
        n += 1

    for (y, mo) in MONTHS:
        d = date(y, mo, 3)
        add("V01", d, 110_000, f"Security services {month_label(y, mo)}", tds_rate=0.01)      # seeded: 1% instead of 2%
        add("V02", d + timedelta(days=2), 45_000, f"Housekeeping {month_label(y, mo)}", tds_rate=0.01,
            inv_no=f"SRV/{y}/{mo:02d}-14")
        add("V03", date(y, mo, 10), rng.randint(34_000, 42_000), f"Common area electricity {month_label(y, mo)}", gst=0)
        add("V07", date(y, mo, 7), 8_000, f"Accounting & book-keeping {month_label(y, mo)}", tds_rate=None)  # seeded: no TDS
        add("V15", date(y, mo, 1), 2_500, "Society management software subscription", tds_rate=None)
        add("V11", date(y, mo, 15), 6_500, "Garden maintenance", tds_rate=None, gst=0)
        if mo in (5, 7, 9, 11, 1, 3):
            add("V04", date(y, mo, 20), 28_000, "Municipal water charges (bi-monthly)", gst=0)
        if mo in (4, 7, 10, 1):
            add("V05", date(y, mo, 12), 22_500, "Lift AMC quarterly", tds_rate=0.02)
            add("V12", date(y, mo, 18), 5_500, "Pest control quarterly", tds_rate=None)
    # duplicate payment of housekeeping Aug-2025 invoice
    add("V02", date(2025, 8, 5), 45_000, "Housekeeping Aug-2025", tds_rate=0.01, inv_no="SRV/2025/08-14", pay_lag=19)
    # property tax half-yearly
    add("V04", date(2025, 6, 25), 585_000, "Property tax H1 2025-26 paid to TMC", gst=0, approved_by="MC")
    add("V04", date(2025, 12, 22), 585_000, "Property tax H2 2025-26 paid to TMC", gst=0, approved_by="MC")
    # insurance
    add("V06", date(2025, 11, 10), 68_000, "Building insurance renewal 15-Nov-2025 to 14-Nov-2026", gst=0.18)
    # audit and legal
    add("V17", date(2025, 9, 20), 35_000, "Statutory audit fees FY 2024-25", tds_rate=None)  # 35k < 50k threshold: OK
    add("V08", date(2025, 8, 28), 60_000, "Legal opinion on deemed conveyance", tds_rate=0.10)
    # waterproofing split invoices (seeded) - total 1,45,000 approved only by MC
    add("V10", date(2025, 6, 9), 49_000, "Terrace waterproofing - Phase 1", tds_rate=0.01, inv_no="SWC/25/031", pay_lag=3)
    add("V10", date(2025, 6, 10), 48_000, "Terrace waterproofing - Phase 2", tds_rate=0.01, inv_no="SWC/25/032", pay_lag=3)
    add("V10", date(2025, 6, 11), 48_000, "Terrace waterproofing - Phase 3", tds_rate=0.01, inv_no="SWC/25/033", pay_lag=3)
    # related-party plumber: frequent bills
    for d, amt in [(date(2025, 4, 22), 18_500), (date(2025, 6, 2), 24_000), (date(2025, 7, 19), 15_750),
                   (date(2025, 9, 8), 22_000), (date(2025, 11, 30), 19_800), (date(2026, 2, 14), 21_500)]:
        add("V09", d, amt, "Plumbing repairs - common lines", tds_rate=None, gst=0, approved_by="Treasurer")
    # cash payments above limit (seeded)
    add("V13", date(2025, 10, 12), 28_000, "Painting of staircase (Diwali)", mode="Cash", gst=0, approved_by="Secretary")
    add("V14", date(2025, 12, 7), 14_500, "Replacement of lobby lights", mode="Cash", gst=0, approved_by="Secretary")
    # misc
    add("V16", date(2025, 9, 2), 6_200, "AGM notice & annual report printing", gst=0.05)
    add("V16", date(2026, 3, 18), 3_100, "Stationery", gst=0.05)
    df = pd.DataFrame(rows).sort_values(["payment_date", "voucher_no"]).reset_index(drop=True)
    df["voucher_no"] = [f"PV-{i + 1:04d}" for i in range(len(df))]
    return df


def build_other_income() -> pd.DataFrame:
    rows = []
    for d, amt in [(date(2025, 6, 30), 61_250), (date(2025, 9, 30), 61_250), (date(2025, 12, 31), 61_250), (date(2026, 3, 31), 61_250)]:
        rows.append({"date": d, "head": "FD interest - Thane District Central Co-op Bank", "nature": "Interest from co-operative bank", "gross_amount": amt, "tds": 0.0, "mutual": False, "section_hint": "80P(2)(d)"})
    for d, amt in [(date(2025, 9, 30), 46_000), (date(2026, 3, 31), 46_000)]:
        rows.append({"date": d, "head": "FD interest - HDFC Bank", "nature": "Interest from scheduled bank", "gross_amount": amt, "tds": round(amt * 0.10, 2), "mutual": False, "section_hint": "Taxable - IFOS"})
    for (y, mo) in MONTHS:
        rows.append({"date": _last_day(y, mo), "head": "Mobile tower rent - Reliance Jio Infocomm", "nature": "Rent from non-member", "gross_amount": 30_000, "tds": 3_000, "mutual": False, "section_hint": "House property / IFOS"})
    for d in [date(2025, 7, 14), date(2025, 11, 3), date(2026, 2, 20)]:
        rows.append({"date": d, "head": "Transfer premium", "nature": "Receipt from members on transfer", "gross_amount": 25_000, "tds": 0.0, "mutual": True, "section_hint": "Mutuality"})
    rows.append({"date": date(2026, 1, 9), "head": "Sale of scrap", "nature": "Misc receipt", "gross_amount": 8_000, "tds": 0.0, "mutual": False, "section_hint": "Taxable - IFOS"})
    return pd.DataFrame(rows)


def build_bank_statement(receipts: pd.DataFrame, expenses: pd.DataFrame, other: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, r in receipts.iterrows():
        lag = 0 if r["mode"] in ("UPI", "NEFT") else rng.randint(1, 3)
        rows.append({"txn_date": r.receipt_date + timedelta(days=lag), "narration": f"{r['mode']} CR {r['reference']} {r.flat_no}", "debit": 0.0, "credit": r.amount, "ref": r["reference"]})
    # cheque bounce for R-0233: reversal 3 days later, never recorded in books
    r233 = receipts.loc[receipts.receipt_no == "R-0233"].iloc[0]
    rows.append({"txn_date": r233.receipt_date + timedelta(days=4), "narration": f"CHQ RETURN INSUFFICIENT FUNDS {r233['reference']}", "debit": r233.amount, "credit": 0.0, "ref": r233["reference"]})
    rows.append({"txn_date": r233.receipt_date + timedelta(days=4), "narration": "CHQ RETURN CHARGES", "debit": 295.0, "credit": 0.0, "ref": "CHG"})
    # unidentified credit
    rows.append({"txn_date": date(2025, 11, 12), "narration": "NEFT CR HDFC0000240 RAVI", "debit": 0.0, "credit": 6_770.0, "ref": "UNID001"})
    for _, e in expenses.iterrows():
        if e.payment_mode == "Cash":
            continue
        rows.append({"txn_date": e.payment_date, "narration": f"NEFT DR {e.vendor_name[:28].upper()} {e.voucher_no}", "debit": e.net_paid, "credit": 0.0, "ref": e.voucher_no})
    for _, o in other.iterrows():
        if o["head"].startswith("Transfer") or o["head"].startswith("Sale"):
            rows.append({"txn_date": o["date"], "narration": f"{o["head"].upper()} RECEIPT", "debit": 0.0, "credit": o["gross_amount"], "ref": "OI"})
        else:
            rows.append({"txn_date": o["date"], "narration": f"{o["head"].upper()}", "debit": 0.0, "credit": o["gross_amount"] - o["tds"], "ref": "OI"})
    # TDS remittances monthly (as actually deducted) and GST payments
    for (y, mo) in MONTHS:
        nxt = date(y + (mo // 12), (mo % 12) + 1, 7)
        rows.append({"txn_date": nxt, "narration": f"TDS PAYMENT CHALLAN {month_label(y, mo)}", "debit": 0.0, "credit": 0.0, "ref": "TDS"})  # filled below
        rows.append({"txn_date": date(y + (mo // 12), (mo % 12) + 1, 20), "narration": f"GSTR-3B PAYMENT {month_label(y, mo)}", "debit": 0.0, "credit": 0.0, "ref": "GST"})
    for (y, mo) in MONTHS:
        rows.append({"txn_date": _last_day(y, mo), "narration": "BANK CHARGES", "debit": 236.0, "credit": 0.0, "ref": "CHG"})
    df = pd.DataFrame(rows)
    # compute TDS challan amounts from expenses by payment month
    expenses = expenses.copy()
    expenses["pm"] = pd.to_datetime(expenses.payment_date).dt.to_period("M")
    tds_by_month = expenses.groupby("pm").tds_deducted.sum()
    for i, row in df[df.ref == "TDS"].iterrows():
        pm = (pd.Timestamp(row.txn_date) - pd.DateOffset(months=1)).to_period("M")
        df.at[i, "debit"] = float(round(tds_by_month.get(pm, 0.0), 2))
    df = df[~((df.ref == "TDS") & (df.debit == 0))]
    df = df[df.ref != "GST"]  # GST paid via cash ledger shown separately in books; keep statement simpler
    df = df.sort_values("txn_date").reset_index(drop=True)
    opening = 425_000.0
    bal = opening
    bals = []
    for _, r in df.iterrows():
        bal = round(bal + r.credit - r.debit, 2)
        bals.append(bal)
    df["balance"] = bals
    df.insert(0, "txn_date", df.pop("txn_date"))
    return df


def build_fund_balances(bills: pd.DataFrame) -> pd.DataFrame:
    sf_collected = round(bills.sinking_fund.sum(), 2)
    rf_collected = round(bills.repair_fund.sum(), 2)
    return pd.DataFrame([
        {"item": "Sinking Fund - opening balance", "amount": 3_850_000.0},
        {"item": "Sinking Fund - collected during year (per bills)", "amount": sf_collected},
        {"item": "Sinking Fund - transferred to fund account per books", "amount": 480_000.0},
        {"item": "Repair & Maintenance Fund - opening balance", "amount": 1_200_000.0},
        {"item": "Repair & Maintenance Fund - collected during year (per bills)", "amount": rf_collected},
        {"item": "Repair & Maintenance Fund - utilised for repairs during year", "amount": 745_750.0},
        {"item": "Fixed deposits - Thane District Central Co-op Bank (earmarked Sinking Fund)", "amount": 3_200_000.0},
        {"item": "Fixed deposits - HDFC Bank (general)", "amount": 1_250_000.0},
        {"item": "Bank balance - opening 01-Apr-2025", "amount": 425_000.0},
        {"item": "Reserve Fund (s.66) - opening", "amount": 310_000.0},
        {"item": "Net surplus FY 2024-25 (for 25% transfer u/s 66)", "amount": 412_000.0},
        {"item": "Transfer to Reserve Fund made in FY 2025-26", "amount": 50_000.0},
    ])


def build_compliance_master() -> pd.DataFrame:
    s = SOCIETY
    return pd.DataFrame([
        {"item": "Society name", "value": s.name},
        {"item": "Registration no.", "value": s.reg_no},
        {"item": "Society address", "value": s.address},
        {"item": "Building occupation certificate date", "value": s.occupation_certificate_date},
        {"item": "Last structural audit (bye-law 77)", "value": s.last_structural_audit},
        {"item": "Last managing committee election", "value": s.last_mc_election},
        {"item": "Lift licence expiry", "value": s.lift_licence_expiry},
        {"item": "Building insurance policy expiry", "value": s.insurance_policy_expiry},
        {"item": "Last fire safety Form B filed", "value": s.last_fire_audit_form_b},
        {"item": "Deemed conveyance status", "value": s.deemed_conveyance_status},
        {"item": "Statutory audit FY 2024-25 completed on", "value": date(2025, 8, 22)},
        {"item": "Audit rectification report (Form O) FY 2024-25 filed on", "value": "Not filed"},
        {"item": "AGM for FY 2024-25 held on", "value": date(2025, 9, 28)},
        {"item": "AGM notice for FY 2024-25 issued on", "value": date(2025, 9, 18)},
        {"item": "ITR for AY 2025-26 filed on", "value": date(2025, 11, 30)},
        {"item": "GSTR-9 FY 2024-25 filed on", "value": date(2025, 12, 28)},
        {"item": "Advance tax paid FY 2025-26", "value": 0},
        {"item": "Accounts FY 2025-26 finalised and placed before committee on", "value": date(2026, 5, 12)},
        {"item": "TDS return Q4 FY 2025-26 (26Q) filed on", "value": date(2026, 5, 28)},
        {"item": "GST registration status", "value": "Registered (regular)"},
    ])


# --------------------------------------------------------------------------- minutes
COMMITTEE = [
    ("Mr. Rajesh Deshmukh", "Chairman", "A-801"), ("Mrs. Sneha Kulkarni", "Hon. Secretary", "A-402"),
    ("Mr. Ganesh Patil", "Treasurer", "B-203"), ("Mr. Aditya Shah", "Member", "A-104"),
    ("Mrs. Pooja Iyer", "Member", "A-603"), ("Mr. Imran Shaikh", "Member", "B-401"),
    ("Mrs. Rosy Fernandes", "Member", "B-702"), ("Mr. Kunal Mehta", "Member", "A-302"),
    ("Mrs. Vandana Jadhav", "Member", "B-104"), ("Mr. Sameer Khan", "Member", "A-704"),
    ("Mrs. Lata More", "Member", "B-503"),
]

MC_MEETINGS = [
    # date, notice_date, present_count, resolutions(list), actions(list of (text, due))
    (date(2025, 4, 13), date(2025, 4, 6), 8,
     ["RESOLVED THAT the maintenance bill structure for FY 2025-26 be continued with service charges of Rs 3,200 per flat per month shared equally as per bye-law 69.",
      "RESOLVED THAT interest on arrears be charged at 21% p.a. simple interest as approved by the General Body."],
     [("Treasurer to circulate list of members in arrears above three months", date(2025, 4, 30))]),
    (date(2025, 5, 18), date(2025, 5, 11), 7,
     ["RESOLVED THAT the draft accounts for FY 2024-25 be approved and forwarded to the statutory auditor.",
      "RESOLVED THAT quotations be invited for terrace waterproofing before monsoon."],
     [("Secretary to obtain three quotations for terrace waterproofing", date(2025, 6, 1))]),
    (date(2025, 6, 8), date(2025, 6, 2), 6,
     ["RESOLVED THAT Shree Waterproofing Contractors be awarded terrace waterproofing work for Rs 1,45,000 to be billed in three phases.",
      "NOTED that only one quotation was received due to urgency of monsoon."],
     [("Treasurer to release payment on completion of each phase", date(2025, 6, 20))]),
    (date(2025, 7, 20), date(2025, 7, 13), 9,
     ["RESOLVED THAT the transfer of flat A-305 from Mr. Prakash Verma to Mr. Nikhil Jain be approved on receipt of transfer premium of Rs 25,000 and all dues.",
      "RESOLVED THAT M/s Desai Legal LLP be engaged for opinion on deemed conveyance at fees of Rs 60,000."],
     [("Secretary to issue share certificate endorsement for A-305", date(2025, 8, 15))]),
    (date(2025, 8, 17), date(2025, 8, 10), 7,
     ["RESOLVED THAT the Annual General Meeting for FY 2024-25 be held on 28 September 2025 at 10:30 am in the society hall.",
      "RESOLVED THAT the audited accounts, auditor's report and budget for FY 2025-26 be placed before the AGM."],
     [("Secretary to issue AGM notice to all members", date(2025, 9, 13)),
      ("Treasurer to prepare budget FY 2025-26", date(2025, 9, 5))]),
    (date(2025, 9, 14), date(2025, 9, 7), 8,
     ["RESOLVED THAT Jain Jakhotiya & Associates, Chartered Accountants, be recommended to the AGM for appointment as statutory auditor for FY 2025-26 at a fee of Rs 35,000.",
      "NOTED the legal notice received from member of flat A-303 disputing interest on arrears."],
     [("Secretary to reply to legal notice of A-303 through society advocate", date(2025, 9, 30))]),
    (date(2025, 10, 12), date(2025, 10, 10), 4,
     ["RESOLVED THAT staircase painting work for Diwali be awarded to Sai Painter for Rs 28,000 and paid in cash on completion.",
      "RESOLVED THAT Diwali bonus equal to one month salary be paid to security and housekeeping staff through the agencies."],
     [("Secretary to arrange payment to painter", date(2025, 10, 20))]),
    (date(2025, 11, 16), date(2025, 11, 9), 8,
     ["RESOLVED THAT the building insurance policy be renewed with New India Assurance for a sum insured of Rs 18 crore at a premium of Rs 68,000.",
      "RESOLVED THAT recovery proceedings under section 101 of the MCS Act be initiated against members of flats A-303, B-703 and A-103."],
     [("Secretary to file section 101 recovery applications", date(2025, 12, 31)),
      ("Treasurer to reconcile bank statement for Nov-2025", date(2025, 12, 10))]),
    (date(2025, 12, 14), date(2025, 12, 7), 7,
     ["RESOLVED THAT the second instalment of property tax of Rs 5,85,000 be paid to Thane Municipal Corporation before due date.",
      "NOTED that the structural audit due in March 2026 is to be planned."],
     [("Secretary to obtain quotations from empanelled structural engineers", date(2026, 1, 31))]),
    (date(2026, 1, 18), date(2026, 1, 11), 9,
     ["RESOLVED THAT fire safety Form B for the half year be filed with the Chief Fire Officer.",
      "RESOLVED THAT lobby light replacement be done by Vijay Electricals."],
     [("Secretary to file Form B", date(2026, 1, 31))]),
    (date(2026, 2, 15), date(2026, 2, 8), 8,
     ["RESOLVED THAT the transfer of flat B-506 be approved on receipt of transfer premium of Rs 25,000.",
      "NOTED that sinking fund collections are being used temporarily for revenue expenses and will be regularised."],
     [("Treasurer to transfer sinking fund collections to the earmarked FD", date(2026, 3, 31))]),
    (date(2026, 3, 15), date(2026, 3, 8), 7,
     ["RESOLVED THAT the lift licence renewal application be filed with the Lift Inspector before expiry in September 2026.",
      "RESOLVED THAT the accounts for FY 2025-26 be closed and the Treasurer be authorised to finalise the books by 15 May 2026."],
     [("Secretary to file lift licence renewal", date(2026, 8, 31)),
      ("Treasurer to finalise books of accounts", date(2026, 5, 15))]),
]


def write_minutes(folder: Path) -> list[Path]:
    folder.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, (d, notice, present, resolutions, actions) in enumerate(MC_MEETINGS, start=1):
        attendees = COMMITTEE[:present]
        txt = [
            f"{SOCIETY.name}",
            f"Regn. No. {SOCIETY.reg_no}",
            "",
            f"MINUTES OF THE MANAGING COMMITTEE MEETING NO. {i}/2025-26",
            f"Date of meeting: {d:%d-%m-%Y}",
            f"Notice issued on: {notice:%d-%m-%Y}",
            f"Venue: Society office, 7:30 pm",
            f"Members present: {present} of {SOCIETY.committee_size}",
            "Attendance: " + "; ".join(f"{n} ({r}, {f})" for n, r, f in attendees),
            "",
            "The Chairman welcomed the members. The minutes of the previous meeting were read and confirmed.",
            "",
            "RESOLUTIONS:",
        ]
        for k, r in enumerate(resolutions, start=1):
            txt.append(f"{i}.{k} {r}")
        txt += ["", "ACTION ITEMS:"]
        for (a, due) in actions:
            txt.append(f"- Action: {a} by {due:%d-%m-%Y}")
        txt += ["", "There being no other business, the meeting ended with a vote of thanks to the Chair.", "",
                "Sd/- Hon. Secretary                    Sd/- Chairman"]
        p = folder / f"MC_{i:02d}_{d:%Y-%m-%d}.txt"
        p.write_text("\n".join(txt), encoding="utf-8")
        paths.append(p)
    agm = [
        f"{SOCIETY.name}",
        f"Regn. No. {SOCIETY.reg_no}",
        "",
        "MINUTES OF THE 16TH ANNUAL GENERAL MEETING",
        "Date of meeting: 28-09-2025",
        "Notice issued on: 18-09-2025",
        "Venue: Society hall, 10:30 am",
        "Members present: 22 of 64 (quorum: one-fifth of members or 20, whichever is less, as per bye-law 100)",
        "",
        "RESOLUTIONS:",
        "A.1 RESOLVED THAT the audited statement of accounts and the statutory auditor's report for FY 2024-25 be adopted.",
        "A.2 RESOLVED THAT Jain Jakhotiya & Associates, Chartered Accountants (Panel No. 4521), be appointed statutory auditor for FY 2025-26 at a fee of Rs 35,000 plus taxes.",
        "A.3 RESOLVED THAT the budget for FY 2025-26 as presented by the Treasurer be approved.",
        "A.4 RESOLVED THAT the managing committee be authorised to incur expenditure up to Rs 50,000 per item without prior general body approval; any item above this limit shall require general body sanction and three quotations.",
        "A.5 RESOLVED THAT the appointment of a structural engineer for the five-yearly structural audit be approved with a budget of Rs 1,50,000.",
        "A.6 RESOLVED THAT the committee be directed to pursue deemed conveyance of the land and building.",
        "",
        "ACTION ITEMS:",
        "- Action: Secretary to file annual returns and auditor appointment with the Registrar by 31-10-2025",
        "- Action: Secretary to file audit rectification report (Form O) for FY 2024-25 by 22-11-2025",
        "- Action: Committee to appoint structural engineer by 31-01-2026",
        "",
        "Sd/- Hon. Secretary                    Sd/- Chairman",
    ]
    p = folder / "AGM_2025-09-28.txt"
    p.write_text("\n".join(agm), encoding="utf-8")
    paths.append(p)
    return paths


def generate(out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    members = build_members()
    bills, receipts = build_bills_and_receipts(members)
    vendors = build_vendors()
    expenses = build_expenses()
    other = build_other_income()
    bank = build_bank_statement(receipts, expenses, other)
    funds = build_fund_balances(bills)
    comp = build_compliance_master()
    path = out_dir / "society_data.xlsx"
    with pd.ExcelWriter(path, engine="openpyxl") as xw:
        members.to_excel(xw, sheet_name="Members", index=False)
        bills.to_excel(xw, sheet_name="Maintenance_Bills", index=False)
        receipts.to_excel(xw, sheet_name="Receipts", index=False)
        bank.to_excel(xw, sheet_name="Bank_Statement", index=False)
        vendors.to_excel(xw, sheet_name="Vendors", index=False)
        expenses.to_excel(xw, sheet_name="Expenses", index=False)
        other.to_excel(xw, sheet_name="Other_Income", index=False)
        funds.to_excel(xw, sheet_name="Fund_Balances", index=False)
        comp.to_excel(xw, sheet_name="Compliance_Master", index=False)
        pd.DataFrame({"seeded_issue": SEEDED_ISSUES}).to_excel(xw, sheet_name="Seeded_Issues_(answer_key)", index=False)
    write_minutes(out_dir / "minutes")
    return path


if __name__ == "__main__":
    import sys
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/raw")
    p = generate(target)
    print(f"written {p}")
