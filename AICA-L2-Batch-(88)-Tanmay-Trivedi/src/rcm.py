"""
rcm.py
-------
A separate, independent alert layer for Reverse Charge Mechanism (RCM)
applicability - Section 9(3) and 9(4), CGST Act, 2017 (Section 5(3)/5(4),
IGST Act for inter-state/import cases), read with Notification No. 13/2017-
Central Tax (Rate), as amended.

This is deliberately kept separate from src/rules.py. Section 17(5) (blocked
credits) and Section 9(3)/9(4) (reverse charge) answer two different
questions about the same expense:

    - rules.py   -> "Can I claim ITC on this, once GST has been paid?"
    - rcm.py     -> "Who is liable to pay the GST on this in the first
                     place - the supplier, or me (the recipient)?"

An expense can be RCM-liable AND fully ITC-eligible at the same time (e.g.
legal fees paid to an advocate: you self-invoice and pay GST under RCM, and
that self-paid tax is itself eligible ITC, subject to Section 17(5) like any
other tax). So this module never overrides or blocks a Section 17(5)
verdict - it's shown as an independent heads-up alongside it, wherever a
description is checked (Quick Check, Bulk Check, Invoice Check).

Matching uses the same word-boundary keyword technique as rules.py, kept as
its own small copy here rather than a shared import, since the two rule
tables are conceptually independent and may evolve separately.

This list is a representative, NOT exhaustive, set of the more commonly
encountered RCM entries in day-to-day practice - see the "conditions" note
on each entry: RCM applicability frequently also depends on facts this
matcher can't see from a description alone (the recipient's own
registration/body-corporate status, whether the supplier has opted for
forward charge, etc.). Treat every alert here as "go verify the specific
conditions," not a determination - exactly like a Section 17(5) verdict.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class RCMCategory:
    id: str
    section: str  # e.g. "9(3), CGST Act" or "5(3), IGST Act"
    title: str
    keywords: list[str]
    note: str


RCM_CATEGORIES: list[RCMCategory] = [
    RCMCategory(
        id="gta_freight",
        section="9(3), CGST Act",
        title="Goods Transport Agency (GTA) Services",
        keywords=["goods transport agency", "gta", "freight paid", "lorry freight",
                   "transportation of goods by road", "truck freight", "transport charges for goods"],
        note="If the GTA has not opted to pay tax itself (forward charge @ 12%) and the recipient "
             "falls in a notified category (body corporate, registered person, factory, society, "
             "partnership firm, etc.), GST on this freight is payable by the recipient under RCM.",
    ),
    RCMCategory(
        id="legal_services",
        section="9(3), CGST Act",
        title="Legal Services from an Advocate / Firm of Advocates",
        keywords=["legal services", "advocate fee", "advocate fees", "lawyer fee", "lawyer fees",
                   "legal fees", "legal consultancy fee", "counsel fee", "counsel fees"],
        note="Legal services received by a business entity from an advocate or firm of advocates "
             "are taxable under RCM in the recipient's hands, regardless of the advocate's own "
             "GST registration status.",
    ),
    RCMCategory(
        id="arbitral_tribunal",
        section="9(3), CGST Act",
        title="Services of an Arbitral Tribunal",
        keywords=["arbitral tribunal", "arbitration fee", "arbitration fees"],
        note="Services of an arbitral tribunal to a business entity are taxable under RCM.",
    ),
    RCMCategory(
        id="sponsorship",
        section="9(3), CGST Act",
        title="Sponsorship Services",
        keywords=["sponsorship", "sponsorship fee", "sponsorship service"],
        note="Sponsorship services provided to a body corporate or partnership firm are taxable "
             "under RCM in the recipient's hands.",
    ),
    RCMCategory(
        id="director_services",
        section="9(3), CGST Act",
        title="Services by a Director to the Company",
        keywords=["director sitting fee", "director sitting fees", "director remuneration",
                   "directors fee", "directors fees", "commission to director", "director commission"],
        note="Services by a director to the company, other than in the capacity of an employee "
             "(e.g. sitting fees, commission), are taxable under RCM in the company's hands.",
    ),
    RCMCategory(
        id="import_of_service",
        section="5(3), IGST Act",
        title="Import of Services (Supplier Located Outside India)",
        keywords=["import of service", "import of services", "foreign consultancy fee",
                   "overseas service fee", "services from outside india", "payment to foreign vendor for service",
                   "cross-border service fee"],
        note="Import of services is taxable under RCM in the recipient's hands as IGST (Section "
             "5(3), IGST Act, mirroring Section 9(3) CGST) - applies even to a single one-off "
             "service, subject to the specified exceptions (e.g. certain OIDAR supplies).",
    ),
    RCMCategory(
        id="security_services",
        section="9(3), CGST Act",
        title="Security Services (Supply of Security Personnel)",
        keywords=["security services", "security guard service", "security guard services",
                   "security personnel service"],
        note="Security services (supply of security personnel) provided by anyone other than a "
             "body corporate, to a registered person, are taxable under RCM in the recipient's "
             "hands (subject to specified exclusions such as Government departments/PSUs already "
             "registered only for TDS).",
    ),
    RCMCategory(
        id="rent_a_cab",
        section="9(3), CGST Act",
        title="Renting of Motor Vehicle for Passenger Transport",
        keywords=["renting of motor vehicle", "rent-a-cab", "rent a cab", "cab rental service",
                   "car rental service for employees"],
        note="Renting of a motor vehicle designed to carry passengers, by a non-body-corporate "
             "supplier who is NOT charging GST at 12% (with full ITC) or 5%, to a body corporate, "
             "is taxable under RCM in the recipient's hands. Doesn't apply if the supplier already "
             "charges 12% GST on the invoice.",
    ),
    RCMCategory(
        id="residential_dwelling",
        section="9(3), CGST Act",
        title="Renting of Residential Dwelling to a Registered Person",
        keywords=["renting of residential dwelling", "residential property rent",
                   "residential rent to registered person", "rent for residential accommodation"],
        note="Renting of a residential dwelling to a registered person (for any purpose, including "
             "as an employee's accommodation booked in the company's name) is taxable under RCM in "
             "the recipient's hands, effective 18-07-2022.",
    ),
    RCMCategory(
        id="insurance_agent",
        section="9(3), CGST Act",
        title="Insurance Agent Services",
        keywords=["insurance agent commission", "insurance agent service", "commission to insurance agent"],
        note="Services by an insurance agent to an insurance company are taxable under RCM in the "
             "insurance company's hands.",
    ),
    RCMCategory(
        id="recovery_agent",
        section="9(3), CGST Act",
        title="Recovery Agent Services",
        keywords=["recovery agent", "recovery agent service", "recovery agent commission"],
        note="Services by a recovery agent to a banking company, financial institution or NBFC are "
             "taxable under RCM in the recipient's hands.",
    ),
    RCMCategory(
        id="unregistered_purchase_9_4",
        section="9(4), CGST Act",
        title="Purchases from Unregistered Suppliers (Notified Real-Estate Cases)",
        keywords=["purchase from unregistered dealer", "unregistered supplier purchase",
                   "cement purchase from unregistered", "promoter shortfall purchase"],
        note="Section 9(4) RCM today applies narrowly - mainly to a real-estate promoter's cement "
             "purchases, and the shortfall in inputs/input services procured from unregistered "
             "suppliers (taxed at year-end) under the real-estate scheme notifications. It is NOT "
             "a general 'any purchase from an unregistered dealer' RCM as it briefly was in 2017.",
    ),
]


def match_rcm(description: str) -> list[RCMCategory]:
    """Same word-boundary keyword technique as rules.match_categories(), so a
    short keyword can't false-match inside an unrelated word. Returns every
    matching category, most-specific keyword match first - this is an
    independent alert list, not a mutually-exclusive verdict, so more than
    one entry can legitimately apply to the same description."""
    text = description.lower()
    scored = []
    for cat in RCM_CATEGORIES:
        best_score = None
        for kw in cat.keywords:
            pattern = r"\b" + re.escape(kw.strip().lower()) + r"\b"
            if re.search(pattern, text):
                score = (len(kw.strip().split()), len(kw.strip()))
                if best_score is None or score > best_score:
                    best_score = score
        if best_score is not None:
            scored.append((best_score, cat))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [cat for _score, cat in scored]
