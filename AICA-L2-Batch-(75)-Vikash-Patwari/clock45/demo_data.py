"""
clock45.demo_data
=================
Deterministic synthetic ledger for the ICAI demonstration.

NEVER demo on real client data. Not redacted, not "just this once".

Every case below is planted because it is a beat in the demo story. The seed is
fixed, so the run is byte-identical every time you present. Rehearsed
unpredictability is not a feature.

Planted cases:
  A. 23 genuine micro/small suppliers unpaid past the limit  -> the headline
  B.  4 traders, NIC 46/47, unpaid                           -> the credibility moment
  C.  2 medium enterprises the client's ERP flagged as MSME  -> the ERP-is-wrong diff
  D.  1 vendor registered on Udyam AFTER the supply          -> gate 4
  E.  1 written agreement stating 60 days                    -> the 45-day ceiling
  F.  1 vendor with 4 ledger spellings                       -> fuzzy matching
  G.  1 payment landing exactly on day 45                    -> boundary handling
  H.  3 vendors paid late but within the year                -> interest-only exposure
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from decimal import Decimal

from .classify import (
    UdyamRecord, MICRO, SMALL, MEDIUM,
    SRC_CERTIFICATE, SRC_DECLARATION, SRC_CLIENT_FLAG,
)
from .engine import PurchaseLine, PaymentLine

SEED = 45045
FY = "2025-26"
FY_START, FY_END = date(2025, 4, 1), date(2026, 3, 31)

_FIRST = ["Sharma", "Verma", "Patel", "Reddy", "Iyer", "Nair", "Bose", "Gupta",
          "Joshi", "Mehta", "Kulkarni", "Rao", "Shah", "Desai", "Bhatt",
          "Chauhan", "Pillai", "Sinha", "Malhotra", "Kapoor"]
_KIND = ["Industries", "Engineering", "Precision Works", "Auto Components",
         "Polymers", "Fabrication", "Castings", "Tooling", "Springs",
         "Fasteners", "Rubber Products", "Electricals"]
_SVC = ["Consultancy Services", "Logistics Services", "Design Studio",
        "Technical Services", "Calibration Labs"]
_TRADE = ["Trading Co", "Enterprises", "Agencies", "Distributors"]


def _amt(rng, lo, hi) -> Decimal:
    return Decimal(rng.randrange(lo, hi, 500))


def build_demo_dataset():
    rng = random.Random(SEED)
    vendors: dict[str, dict] = {}
    udyam: dict[str, UdyamRecord] = {}
    purchases: list[PurchaseLine] = []
    payments: list[PaymentLine] = []
    inv_no = 1000

    used_names: set[str] = set()
    _LOC = ["Pune", "Nashik", "Aurangabad", "Satara", "Kolhapur", "Sangli",
            "Solapur", "Latur", "Nagpur", "Thane", "Vasai", "Ratnagiri"]

    def unique(name):
        if name not in used_names:
            used_names.add(name)
            return name
        for loc in _LOC:
            cand = f"{loc} {name}"
            if cand not in used_names:
                used_names.add(cand)
                return cand
        i = 2
        while f"{name} {i}" in used_names:
            i += 1
        used_names.add(f"{name} {i}")
        return f"{name} {i}"

    def add_vendor(vid, name, cls, nic, activity, reg, source):
        vendors[vid] = {"name": name}
        udyam[vid] = UdyamRecord(
            vendor_id=vid, udyam_no=f"UDYAM-MH-26-{vid[-6:]}" if cls else None,
            enterprise_class=cls, nic_code=nic, activity_label=activity,
            registration_date=reg, source=source,
            evidence_file_hash=f"sha256:{rng.getrandbits(64):016x}" if source == SRC_CERTIFICATE else None,
        )

    def add_invoice(vid, name, d, amount, agreement_days=None, pay_offset=None, grn=None):
        nonlocal inv_no
        inv_no += 1
        iid = f"PI/{inv_no}"
        purchases.append(PurchaseLine(
            invoice_id=iid, vendor_id=vid, vendor_name_as_written=name,
            invoice_date=d, amount=Decimal(amount), grn_date=grn,
            agreement_days=agreement_days,
        ))
        if pay_offset is not None:
            payments.append(PaymentLine(iid, d + timedelta(days=pay_offset), Decimal(amount)))
        return iid

    # ---------------------------------------------------------------- A
    # 23 covered MSE vendors, unpaid at year end, past the limit.
    # Amounts chosen to total ~Rs 18.4 lakh.
    target = 1840000
    amounts = []
    remaining, n = target, 23
    for i in range(n - 1):
        avg = remaining // (n - i)
        a = rng.randrange(int(avg * 0.45), int(avg * 1.55), 500)
        amounts.append(a)
        remaining -= a
    amounts.append(remaining - (remaining % 500))
    amounts[0] += target - sum(amounts)

    for i, amount in enumerate(amounts):
        vid = f"V{2000+i:06d}"
        name = f"{_FIRST[i % len(_FIRST)]} {_KIND[i % len(_KIND)]}"
        if i % 7 == 0:
            name = f"{_FIRST[i % len(_FIRST)]} {_SVC[i % len(_SVC)]}"
        name = unique(name)
        add_vendor(vid, name, SMALL if i % 3 else MICRO,
                   f"{rng.choice(['25','28','29','22','13','62','52'])}{rng.randrange(100,999)}",
                   "Manufacture / services", date(2021, 7, 1) + timedelta(days=i * 11),
                   SRC_CERTIFICATE if i % 4 else SRC_DECLARATION)
        d = FY_END - timedelta(days=rng.randrange(50, 300))
        add_invoice(vid, name, d, amount,
                    agreement_days=45 if i % 2 else None, pay_offset=None)
        for _ in range(rng.randrange(1, 4)):  # noise: paid-on-time invoices
            off = rng.randrange(5, 40)
            d2 = FY_START + timedelta(days=rng.randrange(0, 300 - off))
            add_invoice(vid, name, d2, _amt(rng, 20000, 180000),
                        agreement_days=45, pay_offset=off)

    # ---------------------------------------------------------------- B
    # 4 traders, NIC 46/47, unpaid ~Rs 6 lakh. THE credibility moment.
    trader_amounts = [212500, 168000, 131500, 88000]
    for i, amount in enumerate(trader_amounts):
        vid = f"T{3000+i:06d}"
        name = unique(f"{_FIRST[(i*3) % len(_FIRST)]} {_TRADE[i % len(_TRADE)]}")
        add_vendor(vid, name, SMALL if i % 2 else MICRO,
                   f"{rng.choice(['46','47','46','45'])}{rng.randrange(100,999)}",
                   "Wholesale / retail trade", date(2022, 3, 14) + timedelta(days=i * 40),
                   SRC_CERTIFICATE)
        add_invoice(vid, name, FY_END - timedelta(days=rng.randrange(60, 200)), amount)

    # ---------------------------------------------------------------- C
    # 2 MEDIUM enterprises the client's own ERP flagged as MSME.
    for i, amount in enumerate([340000, 275000]):
        vid = f"M{4000+i:06d}"
        name = unique(f"{_FIRST[(i*5) % len(_FIRST)]} Alloys Pvt Ltd")
        add_vendor(vid, name, MEDIUM, f"25{rng.randrange(100,999)}",
                   "Manufacture", date(2021, 9, 2), SRC_CLIENT_FLAG)
        add_invoice(vid, name, FY_END - timedelta(days=rng.randrange(70, 180)), amount)

    # ---------------------------------------------------------------- D
    vid = "V500001"
    name = unique("Krishna Precision Works")
    add_vendor(vid, name, SMALL, "28104", "Manufacture", date(2026, 1, 20), SRC_CERTIFICATE)
    add_invoice(vid, name, date(2025, 11, 12), 155000)

    # ---------------------------------------------------------------- E
    vid = "V500002"
    name = unique("Deccan Rubber Products")
    add_vendor(vid, name, SMALL, "22192", "Manufacture", date(2020, 8, 1), SRC_CERTIFICATE)
    add_invoice(vid, name, date(2026, 1, 5), 285000, agreement_days=60)

    # ---------------------------------------------------------------- F
    # One vendor, four ledger spellings, one PAN.
    vid = "V500003"
    spellings = ["Sharma Ind.", "Sharma Industries",
                 "M/s Sharma Inds Pvt Ltd", "SHARMA INDUSTRIES PVT LTD"]
    add_vendor(vid, unique(spellings[1]), MICRO, "25931", "Manufacture",
               date(2021, 2, 18), SRC_CERTIFICATE)
    for i, sp in enumerate(spellings):
        add_invoice(vid, sp, date(2025, 6, 1) + timedelta(days=i * 47),
                    [92000, 64500, 118000, 73500][i],
                    agreement_days=45,
                    pay_offset=None if i in (1, 3) else 30)

    # ---------------------------------------------------------------- G
    vid = "V500004"
    name = unique("Bharat Fasteners")
    add_vendor(vid, name, SMALL, "25931", "Manufacture", date(2019, 5, 5), SRC_CERTIFICATE)
    add_invoice(vid, name, date(2025, 12, 1), 196000, agreement_days=45, pay_offset=45)

    # ---------------------------------------------------------------- H
    # Paid late but within the year: no disallowance, but s.16 interest.
    for i, (amount, late) in enumerate([(420000, 96), (310000, 132), (255000, 78)]):
        vid = f"V6000{i:02d}"
        name = unique(f"{_FIRST[(i*7) % len(_FIRST)]} Engineering Works")
        add_vendor(vid, name, SMALL, "25990", "Manufacture",
                   date(2020, 11, 3), SRC_CERTIFICATE)
        add_invoice(vid, name, date(2025, 5, 10) + timedelta(days=i * 20),
                    amount, agreement_days=45, pay_offset=late)

    # ---------------------------------------------------- background noise
    for i in range(170):
        vid = f"N{7000+i:06d}"
        name = unique(f"{_FIRST[i % len(_FIRST)]} {(_KIND + _SVC + _TRADE)[i % 21]}")
        is_trader = i % 9 == 0
        cls = rng.choice([MICRO, SMALL, SMALL, MEDIUM])
        nic = f"{rng.choice(['46','47'])}{rng.randrange(100,999)}" if is_trader \
            else f"{rng.choice(['25','28','13','62','22','29'])}{rng.randrange(100,999)}"
        add_vendor(vid, name, cls, nic,
                   "Wholesale / retail trade" if is_trader else "Manufacture / services",
                   date(2021, 1, 1) + timedelta(days=rng.randrange(0, 1400)),
                   rng.choice([SRC_CERTIFICATE, SRC_CERTIFICATE, SRC_DECLARATION, SRC_CLIENT_FLAG]))
        for _ in range(rng.randrange(20, 45)):
            offset = rng.randrange(3, 44)
            # Keep noise fully settled within the year so the headline number
            # is driven only by the planted cases. Demos must be predictable.
            d = FY_START + timedelta(days=rng.randrange(0, 364 - offset - 2))
            add_invoice(vid, name, d, _amt(rng, 8000, 260000),
                        agreement_days=rng.choice([45, 45, 30, None]),
                        pay_offset=offset)

    return {
        "entity_name": "Sample Auto Components Pvt Ltd",
        "fy": FY, "vendors": vendors, "udyam": udyam,
        "purchases": purchases, "payments": payments,
    }
