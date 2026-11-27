"""Builds ONE self-contained dashboard page from a database folder.

    py build_dashboard.py db_dummy out/dashboard_dummy.html "Dummy data"

The page holds the data and the code. No internet, no server: double-click it.
The same code builds the dashboard from the private real data folder on the laptop.
"""
import csv
import json
import sys
from datetime import date
from pathlib import Path

from . import life, portfolio

HERE = Path(__file__).resolve().parent
WEB = HERE / "web"


def rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def data_for(folder, label="Dummy data"):
    f = Path(folder)
    db = portfolio.load(f)
    lf = life.load(f)
    checks = [dict(name=n, ok=bool(ok), detail=d) for n, ok, d in portfolio.checks(db) + life.checks(lf, db)]
    return dict(
        meta=dict(label=label, latest=db["latest"].isoformat(), built=date.today().isoformat(),
                  open=min(t["date"] for t in db["tx"] if t["action"] == "OPENING").isoformat()),
        instruments=rows(f / "instruments.csv"),
        tx=rows(f / "transactions.csv"),
        prices=rows(f / "prices.csv"),
        bank=rows(f / "bank_balances.csv"),
        fd=rows(f / "fixed_deposits.csv"),
        cash=rows(f / "broker_cash.csv"),
        checks=checks,
        owner=(lf["owner"]["name"] if lf["owner"] else ""),
        pan=(lf["owner"]["pan"] if lf["owner"] else ""),
        birth=(lf["owner"]["birth"].isoformat() if lf["owner"] else ""),
        sip=rows(f / "sip_plan.csv") if (f / "sip_plan.csv").exists() else [],
        props=rows(f / "properties.csv") if (f / "properties.csv").exists() else [],
        rent=rows(f / "rent_receipts.csv") if (f / "rent_receipts.csv").exists() else [],
        ins=rows(f / "insurance.csv") if (f / "insurance.csv").exists() else [],
    )


def build(folder, out, label="Dummy data"):
    data = data_for(folder, label)
    tpl = (WEB / "template.html").read_text(encoding="utf-8")
    html = (tpl.replace("/*__CSS__*/", (WEB / "style.css").read_text(encoding="utf-8"))
               .replace("/*__ENGINE__*/", (WEB / "engine.js").read_text(encoding="utf-8"))
               .replace("/*__CHARTS__*/", (WEB / "charts.js").read_text(encoding="utf-8"))
               .replace("/*__LIFE__*/", (WEB / "life.js").read_text(encoding="utf-8"))
               .replace("/*__APP__*/", (WEB / "app.js").read_text(encoding="utf-8"))
               .replace("/*__DTAA__*/", json.dumps((WEB / "dtaa.html").read_text(encoding="utf-8")).replace("</", "<\\/"))
               .replace("/*__DATA__*/", json.dumps(data, separators=(",", ":")).replace("</", "<\\/")))
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return out, data


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        sys.exit(1)
    o, d = build(a[0], a[1] if len(a) > 1 else "dashboard.html", a[2] if len(a) > 2 else "Dummy data")
    print(f"written {o} ({o.stat().st_size // 1024} KB), {len(d['tx'])} transactions, {len(d['checks'])} build checks (5 more run in the page)")
