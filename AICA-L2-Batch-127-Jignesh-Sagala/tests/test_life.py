"""Life test. Calendar, premium counts and SIP/rent figures are worked out twice: in JavaScript (life.js, what the
browser uses) and in Python (life.py). This test makes the JavaScript code answer many questions and compares each
answer with Python. It also checks small cases that can be done by hand.
Needs Node.js (any version from 14).
"""
import json
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app import build_dashboard, life as L  # noqa: E402

DB = ROOT / "db_dummy"
JS = r"""
const Life = require(process.argv[2]);
const data = JSON.parse(require('fs').readFileSync(process.argv[3], 'utf8'));
const dates = JSON.parse(require('fs').readFileSync(process.argv[4], 'utf8'));
const lf = new Life(data);
console.log(JSON.stringify(dates.map(on => ({
  on, cal: lf.calendar(on, 12).map(e => [e.date, e.kind, e.label, e.amount]),
  paid: lf.ins.map(p => lf.paid(p, on)), next: lf.ins.map(p => lf.nextDue(p, on)),
  year: lf.yearPremiums(on), pay: lf.ins.map(p => lf.payments(p)) }))));
"""
DATES = ["2024-01-01", "2024-12-31", "2025-06-15", "2026-01-14", "2026-01-15", "2026-02-28", "2026-11-25", "2026-12-31", "2027-04-30",
         "2033-06-09", "2034-01-15", "2035-06-10", "2035-12-31"]


def main():
    data = build_dashboard.data_for(DB)
    lf = L.load(DB)
    names = {i["key"]: i["name"].replace(" - Direct Growth", "") for i in data["instruments"]}
    d = Path(tempfile.mkdtemp())
    (d / "data.json").write_text(json.dumps(data))
    (d / "dates.json").write_text(json.dumps(DATES))
    (d / "run.js").write_text(JS)
    r = subprocess.run(["node", str(d / "run.js"), str(ROOT / "app/web/life.js"), str(d / "data.json"), str(d / "dates.json")], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    got = json.loads(r.stdout)
    n = 0
    for g in got:
        on = date.fromisoformat(g["on"])
        py = [[e[0].isoformat(), e[1], e[2], e[3]] for e in L.calendar(lf, on, 12, names)]
        assert g["cal"] == py, (g["on"], "calendar differs")
        assert g["paid"] == [L.premiums_paid(p, on) for p in lf["ins"]], (g["on"], "premiums paid")
        nxt = []
        for p in lf["ins"]:
            ds = L.premium_dates(p, on, L.add_months(on, 36))
            nxt.append(ds[0].isoformat() if ds else None)
        assert g["next"] == nxt, (g["on"], "next due")
        y = on.year
        assert g["year"] == sum(len(L.premium_dates(p, date(y - 1, 12, 31), date(y, 12, 31))) * p["premium"] for p in lf["ins"]), (g["on"], "year premiums")
        n += len(py)
    # hand cases (dummy data: SIP 5 x 40,000 on the 5th; term 5,00,000 on 15 Jan 2024-2033; medical 75,000 on 1 Aug;
    # retirement 25,000 on 10 Jun 2015-2035; house tax and maintenance 1,40,000 on 30 Apr)
    on = date(2026, 11, 25)
    cal = L.calendar(lf, on, 12, names)
    kinds = {}
    for e in cal:
        kinds[e[1]] = kinds.get(e[1], 0) + e[3]
    assert kinds == {"SIP": 2400000, "Insurance": 600000, "House tax and maintenance": 140000}, kinds
    assert sum(kinds.values()) == 3140000
    assert len([e for e in cal if e[1] == "SIP"]) == 60, "12 months x 5 funds"
    assert [e[0] for e in cal if e[1] == "Insurance"] == [date(2027, 1, 15), date(2027, 6, 10), date(2027, 8, 1)]
    term, med, ret = lf["ins"]
    assert L.premiums_paid(term, on) == 3 and L.premiums_total(term) == 10, "term: 2024, 2025, 2026 paid of 10"
    assert L.premiums_paid(ret, on) == 12 and L.premiums_total(ret) == 21, "retirement: 2015 to 2026 paid of 21"
    assert L.premiums_paid(med, on) is None
    assert ret["payout"] * 300 == 3000000, "income 10,000 x 300 months (Jul 2035 to Jun 2060)"
    assert L.add_months(date(2026, 1, 31), 1) == date(2026, 2, 28), "month end"
    print(f"  life test: calendar, paid counts, next dues and year premiums = Python for {len(DATES)} dates ({n} calendar lines); hand cases ok")
    print("ALL PASS")


if __name__ == "__main__":
    main()
