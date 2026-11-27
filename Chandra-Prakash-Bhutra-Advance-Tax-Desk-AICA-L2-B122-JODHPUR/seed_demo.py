"""Load the invented demo clients into the local database. Run: python seed_demo.py

Two sets are loaded: the 20 tax cases below, and the six fuller clients in demo_clients/, each of which
has its own folder of test files (trial balance, capital gains statement, Form 26AS).

Every name and figure is made up. The set covers individuals (below 60, senior,
super senior, non-resident, salaried, presumptive), HUFs, partnership firms and
LLPs, with different income mixes and payment histories. The expected tax for
each one is hand-worked in tests/test_demo_clients.py.
"""
from advtax import storage
from advtax.engine import ClientInputs

MODE_DIRECT = "Enter full-year figure directly"
MODE_PRESUMPTIVE = "Presumptive (% of turnover)"


def direct(inp: ClientInputs):
    return inp, {"mode": MODE_DIRECT, "f_direct_business": inp.business_income}


def presumptive(inp: ClientInputs, turnover_to_date: float, rate: float):
    # books up to 30 Sep 2026 = 183 of 365 days
    return inp, {"mode": MODE_PRESUMPTIVE, "f_turnover": turnover_to_date, "f_presumptive_rate": rate,
                 "f_books_date": "2026-09-30", "f_growth": 0.0}


def pay(*items):
    return [{"date": d, "amount": a} for d, a in items]


DEMO = [
    # ---------------- Individuals ----------------
    direct(ClientInputs(name="01 Demo Hardware Stores (Prop. R. Sharma)", business_income=1863000,
                        other_interest=42000, hp_let_out_rent=180000, hp_municipal_tax=6000, tds_tcs=18000,
                        payments=pay(("2026-06-12", 30000), ("2026-09-14", 60000)))),
    direct(ClientInputs(name="02 Mrs. K. Iyer - Salaried (Demo)", salary_gross=1500000,
                        hp_self_occupied_interest=200000, deductions_old=450000, other_interest=60000,
                        ltcg_equity=325000, tds_tcs=60000)),
    direct(ClientInputs(name="03 Shri G. Patel - Senior, Old Regime (Demo)", age_band="senior", regime="old",
                        business_income=900000, other_interest=120000, deductions_old=150000,
                        payments=pay(("2026-06-10", 15000)))),
    direct(ClientInputs(name="04 Smt. L. Desai - Senior, No Business (Demo)", age_band="senior",
                        other_interest=1400000, hp_let_out_rent=300000, hp_municipal_tax=10000)),
    direct(ClientInputs(name="05 Shri B. Rao - Super Senior (Demo)", age_band="super_senior",
                        business_income=1400000, other_interest=200000,
                        payments=pay(("2026-06-15", 20000), ("2026-09-15", 40000)))),
    presumptive(ClientInputs(name="06 Dr. A. Mehta - Presumptive Profession (Demo)", presumptive=True,
                             business_income=1898000, stcg_equity=150000, ltcg_equity=320000,
                             other_dividend=65000, deductions_old=250000, tds_tcs=190000), 1903200, 50.0),
    presumptive(ClientInputs(name="07 Demo Kirana Store - Presumptive Trader (Prop. M. Khan)", presumptive=True,
                             business_income=1423500, other_interest=30000), 11895000, 6.0),
    direct(ClientInputs(name="08 Demo Builders - Surcharge (Prop. V. Singh)", business_income=7200000,
                        other_interest=300000, tds_tcs=150000,
                        payments=pay(("2026-06-15", 300000), ("2026-09-20", 500000)))),
    direct(ClientInputs(name="09 Demo Exports - High Income with Gains (Prop. N. Shah)", business_income=18000000,
                        ltcg_other=9000000, stcg_equity=1000000, tds_tcs=200000,
                        payments=pay(("2026-06-15", 1100000), ("2026-09-15", 2200000)))),
    direct(ClientInputs(name="10 Ms. P. Nair - Just Above 12 Lakh (Demo)", salary_gross=1280000)),
    direct(ClientInputs(name="11 Mr. R. Kapoor - Non-Resident (Demo)", resident=False, hp_let_out_rent=960000,
                        hp_municipal_tax=20000, hp_let_out_interest=150000, ltcg_other=2000000,
                        other_interest=100000, tds_tcs=120000)),
    direct(ClientInputs(name="12 Mr. D. Joshi - Salary with Business Loss (Demo)", salary_gross=1800000,
                        business_income=-300000, other_interest=100000, tds_tcs=120000)),
    direct(ClientInputs(name="13 Demo Medical Store - Paid on Time (Prop. S. Gupta)", business_income=2400000,
                        payments=pay(("2026-06-10", 46800), ("2026-09-10", 93600), ("2026-11-20", 93600)))),
    # ---------------- HUFs ----------------
    direct(ClientInputs(name="14 S. Verma HUF (Demo)", constitution="HUF", business_income=720000,
                        hp_let_out_rent=360000, hp_municipal_tax=12000, hp_let_out_interest=90000,
                        other_interest=85000, deductions_old=150000)),
    direct(ClientInputs(name="15 A. Jain HUF - Old Regime (Demo)", constitution="HUF", regime="old",
                        business_income=1200000, ltcg_equity=200000, deductions_old=200000,
                        payments=pay(("2026-06-14", 20000), ("2026-09-15", 40000)))),
    # ---------------- Partnership firms ----------------
    direct(ClientInputs(name="16 Demo Traders (Partnership Firm)", constitution="Firm", business_income=2850000,
                        other_interest=50000, tds_tcs=40000,
                        payments=pay(("2026-06-15", 100000), ("2026-09-15", 250000)))),
    direct(ClientInputs(name="17 Demo Steel Industries - Above 1 Crore (Firm)", constitution="Firm",
                        business_income=10200000, tds_tcs=100000,
                        payments=pay(("2026-06-15", 485000), ("2026-09-15", 970000)))),
    presumptive(ClientInputs(name="18 Demo Transport Co - Presumptive (Firm)", constitution="Firm", presumptive=True,
                             business_income=1168000), 7320000, 8.0),
    # ---------------- LLPs ----------------
    direct(ClientInputs(name="19 Demo Textiles LLP", constitution="LLP", business_income=4250000,
                        other_interest=110000, ltcg_other=600000, tds_tcs=95000,
                        payments=pay(("2026-06-15", 200000)))),
    direct(ClientInputs(name="20 Demo Consultants LLP - Loss", constitution="LLP", business_income=-150000,
                        other_interest=80000)),
]

if __name__ == "__main__":
    con = storage.connect()
    for inp, working in DEMO:
        storage.save_client(con, inp.name, inp.to_dict(), working)
    from advtax import demo

    full = demo.load_demo_folder(con)
    print(f"{len(DEMO)} tax cases and {len(full)} clients from demo_clients/ saved to {storage.db_path()}")
