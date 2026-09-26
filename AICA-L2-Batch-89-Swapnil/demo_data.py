"""FICTITIOUS demo data (brief §12). Names, CINs, DINs and PANs are made up and
only format-valid. Shared by the test-suite and `cli.py seed-demo`."""
from __future__ import annotations

from datetime import date

from engine.types import EntityIn, EventIn, FactsIn, PersonIn

CR, L = 10_000_000, 100_000


def entities() -> dict[str, dict]:
    """name -> {entity, facts, events, persons, flags, cin}"""
    d: dict[str, dict] = {}

    d["alpha"] = dict(
        cin="U62099DL2026PTC000101",
        entity=EntityIn(1, "Alpha Janak Pvt Ltd", "PRIVATE", date(2026, 1, 20),
                        nominal_capital=10 * L, paid_up_capital=1 * L),
        facts={"FY2026-27": FactsIn("FY2026-27", paid_up_capital=1 * L, turnover=40 * L,
                                    auditor_appointed_at_agm=True)},
        events=[],
        persons=[PersonIn(101, "Ravi Demo-Kumar", "10000101", date(2026, 1, 15),
                          detail_changes=[date(2026, 8, 5)]),
                 PersonIn(102, "Meera Sample", "10000102", date(2026, 1, 15))],
        flags={"FY2025-26": {"deposits_outstanding": True}},
    )
    d["beta"] = dict(
        cin="U74999DL2025OPC000202",
        entity=EntityIn(2, "Beta Solo (OPC) Pvt Ltd", "OPC", date(2025, 5, 10),
                        nominal_capital=1 * L, paid_up_capital=1 * L, single_director=True),
        facts={"FY2025-26": FactsIn("FY2025-26", paid_up_capital=1 * L, turnover=18 * L)},
        events=[], persons=[PersonIn(201, "Kiran Example", "10000201", date(2019, 7, 1),
                                     last_annual_kyc_fy="FY2024-25")],
        flags={},
    )
    d["gamma"] = dict(
        cin="U25999DL2012PTC000303",
        entity=EntityIn(3, "Gamma Industries Pvt Ltd", "PRIVATE", date(2012, 6, 15),
                        nominal_capital=15 * CR, paid_up_capital=12 * CR, engagement_start=date(2024, 4, 1)),
        facts={
            "FY2024-25": FactsIn("FY2024-25", paid_up_capital=12 * CR, turnover=140 * CR, net_worth=60 * CR,
                                 net_profit=4 * CR, agm_date=date(2025, 9, 20), isin_obtained_date=date(2024, 9, 10)),
            "FY2025-26": FactsIn("FY2025-26", paid_up_capital=12 * CR, turnover=150 * CR, net_worth=65 * CR,
                                 net_profit=4.5 * CR, agm_date=date(2026, 9, 26), auditor_appointed_at_agm=True),
        },
        events=[], persons=[PersonIn(301, "Anil Placeholder", "10000301", date(2014, 5, 2),
                                     last_annual_kyc_fy="FY2024-25")],
        flags={},
    )
    d["delta"] = dict(
        cin="U51909DL2016PTC000404",
        entity=EntityIn(4, "Delta Traders Pvt Ltd", "PRIVATE", date(2016, 8, 1),
                        nominal_capital=10 * CR, paid_up_capital=8 * CR, engagement_start=date(2025, 4, 1)),
        facts={
            "FY2023-24": FactsIn("FY2023-24", paid_up_capital=8 * CR, turnover=70 * CR),
            "FY2024-25": FactsIn("FY2024-25", paid_up_capital=8 * CR, turnover=75 * CR),
            "FY2025-26": FactsIn("FY2025-26", paid_up_capital=8 * CR, turnover=80 * CR),
        },
        events=[], persons=[], flags={},
    )
    d["epsilon"] = dict(
        cin="U45200DL2020PLC000505",
        entity=EntityIn(5, "Epsilon Infra Ltd", "PUBLIC_UNLISTED", date(2020, 7, 1),
                        nominal_capital=5 * CR, paid_up_capital=2 * CR, engagement_start=date(2026, 4, 1)),
        facts={"FY2025-26": FactsIn("FY2025-26", paid_up_capital=2 * CR, turnover=30 * CR)},
        events=[EventIn(501, "ALLOTMENT", date(2026, 10, 1), {"kind": "PRIVATE_PLACEMENT", "amount": 50 * L}),
                EventIn(502, "ALLOTMENT", date(2026, 10, 1), {"kind": "RIGHTS", "amount": 20 * L}),
                EventIn(503, "CHARGE_CREATED", date(2026, 10, 3), {"amount": 5 * CR}),
                EventIn(504, "SPECIAL_RESOLUTION", date(2026, 10, 5), {"subject": "Alteration of articles"}),
                EventIn(505, "DIRECTOR_APPOINTED", date(2026, 10, 10), {"din": "10000301"})],
        persons=[], flags={},
    )
    d["zeta"] = dict(
        cin="ABC-1234",
        entity=EntityIn(6, "Zeta Advisors LLP", "LLP", date(2021, 6, 1), has_share_capital=False,
                        llp_contribution=8 * L),
        facts={"FY2024-25": FactsIn("FY2024-25", turnover=28 * L, llp_contribution=8 * L),
               "FY2025-26": FactsIn("FY2025-26", turnover=30 * L, llp_contribution=8 * L)},
        events=[], persons=[], flags={},
    )
    d["eta"] = dict(
        cin="ABD-5678",
        entity=EntityIn(7, "Eta Consulting LLP", "LLP", date(2025, 11, 15), has_share_capital=False,
                        llp_contribution=2 * L, llp_elect_longer_first_fy=True),
        facts={}, events=[], persons=[], flags={},
    )
    d["theta"] = dict(
        cin="U10799DL2018PTC000808",
        entity=EntityIn(8, "Theta Foods Pvt Ltd", "PRIVATE", date(2018, 4, 10),
                        nominal_capital=5 * L, paid_up_capital=5 * L, engagement_start=date(2026, 6, 1)),
        facts={"FY2022-23": FactsIn("FY2022-23", paid_up_capital=5 * L, turnover=1.5 * CR,
                                    agm_date=date(2023, 9, 25)),
               "FY2023-24": FactsIn("FY2023-24", paid_up_capital=5 * L, turnover=1.8 * CR)},
        events=[], persons=[], flags={},
    )
    return d
