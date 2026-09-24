"""A worked example of the set-up workbook.

Static on purpose. The moment someone most wants to see a filled-in sheet is
the moment the database is empty, so this cannot be an export of seeded data —
it has to stand on its own.

The figures are Northwind Robotics as at 31-Aug-2026, the same company the
demonstration dataset describes, so the example and the demo tell one story
rather than two. They are internally consistent: the bank balances add to the
cash position, three months of movement produce the burn, and the open items
are the ones the screens talk about.
"""
from __future__ import annotations

from datetime import date, timedelta

from app.models import BurnCategory, CommitmentType, CostNature, StatutoryHead

AS_ON = date(2026, 8, 31)


# ---------------------------------------------------------------------------
def _banks() -> list[dict]:
    return [
        {"institution": "HDFC Bank", "account_name": "Northwind Robotics — Current",
         "account_masked": "4471", "purpose": "Operating", "balance": 21_450_000,
         "as_on": AS_ON, "is_restricted": False, "restriction_reason": None},
        {"institution": "ICICI Bank", "account_name": "Northwind Robotics — Collections",
         "account_masked": "8802", "purpose": "Collections", "balance": 12_180_000,
         "as_on": AS_ON, "is_restricted": False, "restriction_reason": None},
        {"institution": "Axis Bank", "account_name": "Payroll account",
         "account_masked": "1156", "purpose": "Payroll", "balance": 6_320_000,
         "as_on": AS_ON, "is_restricted": False, "restriction_reason": None},
        {"institution": "HDFC Bank", "account_name": "Fixed deposit — BG margin",
         "account_masked": "9014", "purpose": "Deposit", "balance": 4_500_000,
         "as_on": AS_ON, "is_restricted": True,
         "restriction_reason": "Lien-marked against the bank guarantee issued to "
                               "Bharat Metro Rail. Releases on 14-Mar-2027."},
        {"institution": "Kotak Mahindra Bank", "account_name": "Tax account",
         "account_masked": "6620", "purpose": "Tax", "balance": 1_750_000,
         "as_on": AS_ON, "is_restricted": False, "restriction_reason": None},
    ]


# ---------------------------------------------------------------------------
# Three months of movement. Written out as a repeating monthly shape plus the
# named one-offs, because that is how a finance team actually fills this in.
# ---------------------------------------------------------------------------
_MONTHLY_OUT = [
    ("Payroll — June salaries", BurnCategory.PEOPLE, CostNature.FIXED, 9_850_000, 1),
    ("Provident fund and ESI", BurnCategory.PEOPLE, CostNature.FIXED, 1_120_000, 14),
    ("AWS India", BurnCategory.TECH, CostNature.VARIABLE, 1_640_000, 8),
    ("Atlassian / Figma / GitHub", BurnCategory.TECH, CostNature.VARIABLE, 285_000, 8),
    ("Embedded components — Sensedge", BurnCategory.DELIVERY, CostNature.VARIABLE, 2_310_000, 12),
    ("Site commissioning contractors", BurnCategory.DELIVERY, CostNature.VARIABLE, 1_480_000, 20),
    ("Office rent — Whitefield", BurnCategory.FACILITIES, CostNature.FIXED, 620_000, 5),
    ("Electricity and facilities", BurnCategory.FACILITIES, CostNature.FIXED, 178_000, 10),
    ("Digital campaigns", BurnCategory.MARKETING, CostNature.DISCRETIONARY, 540_000, 18),
    ("Statutory audit and CS retainer", BurnCategory.PROFESSIONAL, CostNature.VARIABLE, 310_000, 22),
    ("Term loan interest — HDFC", BurnCategory.FINANCE_COST, CostNature.FIXED, 268_000, 7),
    ("Insurance, travel and sundries", BurnCategory.OTHER, CostNature.VARIABLE, 395_000, 25),
    ("GST payment", BurnCategory.STATUTORY, CostNature.VARIABLE, 2_180_000, 20),
    ("TDS payment", BurnCategory.STATUTORY, CostNature.VARIABLE, 940_000, 7),
]

_MONTHLY_IN = [
    ("Bharat Metro Rail Corporation", 6_400_000, 6),
    ("Sterling Cement Ltd", 3_850_000, 11),
    ("Aurora Pharma Pvt Ltd", 2_950_000, 17),
    ("Vidyut Grid Solutions", 2_240_000, 23),
    ("Coastal Logistics Park", 1_780_000, 27),
]

# Things that happened once. Excluded from normalised burn — with the reason
# written down, because "normalised burn" is only trustworthy if you can see
# what was taken out.
_ONE_OFFS = [
    (date(2026, 6, 18), "Payment", "Kanoria & Associates", BurnCategory.PROFESSIONAL,
     CostNature.DISCRETIONARY, 1_450_000,
     "Series B diligence — legal and financial vendor due diligence. One-off."),
    (date(2026, 7, 9), "Payment", "Sensedge Instruments", BurnCategory.DELIVERY,
     CostNature.VARIABLE, 2_100_000,
     "Bulk sensor purchase for the metro rollout, ordered ahead of a price "
     "revision. One-off, not a monthly rate."),
    (date(2026, 8, 12), "Receipt", "Karnataka State — MSME incentive", None, None,
     1_250_000, "Capital incentive under the state electronics policy. One-off."),
]


def _movement() -> list[dict]:
    rows: list[dict] = []
    for month in (6, 7, 8):
        label = date(2026, month, 1).strftime("%b-%y")
        for name, cat, nature, amount, day in _MONTHLY_OUT:
            base = name.split(" — ")[0]
            rows.append({
                "txn_date": date(2026, month, min(day, 28)),
                "kind": "Payment",
                "party": base,
                "burn_category": cat,
                "amount": amount,
                "cost_nature": nature,
                "is_one_off": False,
                "narration": f"{base} — {label}",
            })
        for party, amount, day in _MONTHLY_IN:
            rows.append({
                "txn_date": date(2026, month, min(day, 28)),
                "kind": "Receipt",
                "party": party,
                "burn_category": None,
                "amount": amount,
                "cost_nature": None,
                "is_one_off": False,
                "narration": f"Collection against invoices — {label}",
            })

    for d, kind, party, cat, nature, amount, note in _ONE_OFFS:
        rows.append({"txn_date": d, "kind": kind, "party": party,
                     "burn_category": cat, "amount": amount, "cost_nature": nature,
                     "is_one_off": True, "narration": note})

    rows.sort(key=lambda r: r["txn_date"])
    return rows


# ---------------------------------------------------------------------------
def _invoices() -> list[dict]:
    d = date
    raw = [
        ("Bharat Metro Rail Corporation", "NW/26-27/0181", d(2026, 6, 30), 45, 18_400_000, 8_400_000, 70, False, None),
        ("Bharat Metro Rail Corporation", "NW/26-27/0206", d(2026, 7, 28), 45, 9_600_000, 9_600_000, 80, False, None),
        ("Sterling Cement Ltd", "NW/26-27/0192", d(2026, 7, 12), 30, 5_200_000, 5_200_000, 90, False, None),
        ("Sterling Cement Ltd", "NW/26-27/0224", d(2026, 8, 14), 30, 3_950_000, 3_950_000, 95, False, None),
        ("Aurora Pharma Pvt Ltd", "NW/26-27/0177", d(2026, 6, 22), 30, 4_100_000, 1_600_000, 85, False, None),
        ("Aurora Pharma Pvt Ltd", "NW/26-27/0231", d(2026, 8, 20), 30, 3_300_000, 3_300_000, 90, False, None),
        ("Vidyut Grid Solutions", "NW/26-27/0165", d(2026, 5, 29), 45, 6_750_000, 2_750_000, 60, True,
         "Disputed scope — two commissioning milestones contested. Meeting held 21-Aug."),
        ("Vidyut Grid Solutions", "NW/26-27/0217", d(2026, 8, 4), 45, 2_900_000, 2_900_000, 75, False, None),
        ("Coastal Logistics Park", "NW/26-27/0158", d(2026, 5, 18), 30, 2_400_000, 2_400_000, 40, False, None),
        ("Coastal Logistics Park", "NW/26-27/0229", d(2026, 8, 18), 30, 1_850_000, 1_850_000, 85, False, None),
        ("Nandi Infra Projects", "NW/26-27/0149", d(2026, 4, 30), 45, 3_600_000, 3_600_000, 35, True,
         "Client insolvency proceedings admitted 12-Jul. Claim filed."),
        ("Peninsula Ports Authority", "NW/26-27/0235", d(2026, 8, 26), 60, 5_400_000, 5_400_000, 88, False, None),
    ]
    out = []
    for cust, no, idate, terms, amount, outstanding, prob, disputed, reason in raw:
        out.append({
            "customer": cust, "invoice_no": no, "invoice_date": idate,
            "due_date": idate + timedelta(days=terms),
            "amount": amount, "outstanding": outstanding,
            "credit_terms_days": terms, "collection_probability": prob,
            "is_disputed": disputed, "dispute_reason": reason,
        })
    return out


def _bills() -> list[dict]:
    d = date
    raw = [
        ("Sensedge Instruments", "SI/2026/1188", d(2026, 8, 6), 30, 3_180_000, 3_180_000,
         BurnCategory.DELIVERY, True, 0, "Sensor modules — metro phase 2"),
        ("Amazon Web Services India", "AWS-IN-0826", d(2026, 8, 31), 15, 1_640_000, 1_640_000,
         BurnCategory.TECH, False, 0, "August cloud usage — service suspends on non-payment"),
        ("Prestige Office Ventures", "POV/AUG/26", d(2026, 8, 25), 7, 620_000, 620_000,
         BurnCategory.FACILITIES, False, 62_000, "Whitefield office rent — September"),
        ("Kanoria & Associates", "KA/26-27/077", d(2026, 7, 31), 30, 480_000, 480_000,
         BurnCategory.PROFESSIONAL, True, 0, "Statutory audit — first instalment"),
        ("Trilok Contracting", "TC/1042", d(2026, 8, 12), 45, 1_480_000, 1_480_000,
         BurnCategory.DELIVERY, True, 0, "Site commissioning — Hubli"),
        ("Meridian Media", "MM/2608", d(2026, 8, 20), 30, 540_000, 540_000,
         BurnCategory.MARKETING, True, 0, "Q2 digital campaign"),
        ("Bharat Electric Utility", "BEU/0826", d(2026, 8, 28), 10, 178_000, 178_000,
         BurnCategory.FACILITIES, False, 8_900, "Electricity — August"),
        ("Sundaram Insurance Brokers", "SIB/26/311", d(2026, 8, 18), 30, 395_000, 395_000,
         BurnCategory.OTHER, True, 0, "D&O and asset insurance renewal"),
        ("Talent Bridge Consulting", "TB/26/094", d(2026, 7, 22), 45, 720_000, 720_000,
         BurnCategory.PEOPLE, True, 0, "Recruitment fees — three engineering hires"),
        ("HDFC Bank — term loan", "TL/INT/0826", d(2026, 8, 31), 7, 268_000, 268_000,
         BurnCategory.FINANCE_COST, False, 26_800, "Interest instalment — September"),
    ]
    out = []
    for vendor, no, bdate, terms, amount, outstanding, cat, deferrable, cost, desc in raw:
        out.append({
            "vendor": vendor, "bill_no": no, "bill_date": bdate,
            "due_date": bdate + timedelta(days=terms), "amount": amount,
            "outstanding": outstanding, "burn_category": cat,
            "deferrable": deferrable, "deferral_cost": cost, "description": desc,
        })
    return out


def _statutory() -> list[dict]:
    return [
        {"head": StatutoryHead.GST, "period": "Aug-26", "due_date": date(2026, 9, 20),
         "amount": 2_205_000, "earmarked_amount": 1_750_000, "reference": "GSTR-3B",
         "notes": "Net of input credit. Thin credit — the company is people-heavy."},
        {"head": StatutoryHead.TDS, "period": "Aug-26", "due_date": date(2026, 9, 7),
         "amount": 940_000, "earmarked_amount": 940_000, "reference": "194J / 192",
         "notes": None},
        {"head": StatutoryHead.PF, "period": "Aug-26", "due_date": date(2026, 9, 15),
         "amount": 705_000, "earmarked_amount": 705_000, "reference": "ECR", "notes": None},
        {"head": StatutoryHead.ESI, "period": "Aug-26", "due_date": date(2026, 9, 15),
         "amount": 118_000, "earmarked_amount": 118_000, "reference": None, "notes": None},
        {"head": StatutoryHead.PT, "period": "Aug-26", "due_date": date(2026, 9, 20),
         "amount": 37_000, "earmarked_amount": 37_000, "reference": "Karnataka PT",
         "notes": None},
    ]


def _commitments() -> list[dict]:
    return [
        {"commitment_type": CommitmentType.PO, "counterparty": "Sensedge Instruments",
         "description": "Sensor modules for the metro rollout, phases 2 and 3",
         "total_value": 12_600_000, "consumed_to_date": 4_200_000, "cancellable": False,
         "notice_period_days": 0, "exit_cost": 2_500_000,
         "starts_on": date(2026, 6, 1), "ends_on": date(2027, 3, 31),
         "monthly_runrate": 1_050_000, "burn_category": BurnCategory.DELIVERY},
        {"commitment_type": CommitmentType.CLOUD, "counterparty": "Amazon Web Services India",
         "description": "Committed spend agreement, 24 months",
         "total_value": 9_600_000, "consumed_to_date": 3_280_000, "cancellable": False,
         "notice_period_days": 90, "exit_cost": 1_200_000,
         "starts_on": date(2026, 2, 1), "ends_on": date(2028, 1, 31),
         "monthly_runrate": 400_000, "burn_category": BurnCategory.TECH},
        {"commitment_type": CommitmentType.OFFER, "counterparty": "Four engineering hires",
         "description": "Offers issued, joining October and November",
         "total_value": 4_320_000, "consumed_to_date": 0, "cancellable": True,
         "notice_period_days": 30, "exit_cost": 0,
         "starts_on": date(2026, 10, 1), "ends_on": date(2027, 9, 30),
         "monthly_runrate": 360_000, "burn_category": BurnCategory.PEOPLE},
        {"commitment_type": CommitmentType.LEASE, "counterparty": "Prestige Office Ventures",
         "description": "Whitefield office — lock-in to Mar-2028",
         "total_value": 11_160_000, "consumed_to_date": 3_720_000, "cancellable": False,
         "notice_period_days": 180, "exit_cost": 1_860_000,
         "starts_on": date(2025, 4, 1), "ends_on": date(2028, 3, 31),
         "monthly_runrate": 620_000, "burn_category": BurnCategory.FACILITIES},
        {"commitment_type": CommitmentType.RETAINER, "counterparty": "Kanoria & Associates",
         "description": "Statutory audit and secretarial retainer, FY26-27",
         "total_value": 1_440_000, "consumed_to_date": 480_000, "cancellable": True,
         "notice_period_days": 60, "exit_cost": 0,
         "starts_on": date(2026, 4, 1), "ends_on": date(2027, 3, 31),
         "monthly_runrate": 120_000, "burn_category": BurnCategory.PROFESSIONAL},
        {"commitment_type": CommitmentType.PO, "counterparty": "Trilok Contracting",
         "description": "Commissioning work order — Hubli and Belgaum sites",
         "total_value": 5_200_000, "consumed_to_date": 1_480_000, "cancellable": True,
         "notice_period_days": 30, "exit_cost": 260_000,
         "starts_on": date(2026, 7, 1), "ends_on": date(2027, 1, 31),
         "monthly_runrate": 520_000, "burn_category": BurnCategory.DELIVERY},
    ]


def example_rows() -> dict[str, list[dict]]:
    """Keyed by sheet name, matching `setupimport.SHEETS`."""
    return {
        "Bank Accounts": _banks(),
        "Receipts & Payments": _movement(),
        "Open Invoices": _invoices(),
        "Open Bills": _bills(),
        "Statutory Dues": _statutory(),
        "Committed Not Billed": _commitments(),
    }
