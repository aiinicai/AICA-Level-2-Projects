"""Load the clients in demo_clients/ into the local database.

Each client folder has a client.json and its own test files. The files are put
through the same readers the screens use (trial balance import, capital gains
import, 26AS reader), so what is loaded is exactly what uploading the files by
hand would give.
"""
from __future__ import annotations

import json
import shutil
from datetime import date
from pathlib import Path

from advtax import cg_import, form26as_read, portal_26as, storage, tb_import
from advtax.engine import ClientInputs, load_rules
from advtax.projection import project_business, project_presumptive

DEMO_DIR = storage.ROOT / "demo_clients"
MODE_TB, MODE_DIRECT, MODE_PRESUMPTIVE = ("Upload trial balance", "Enter full-year figure directly",
                                          "Presumptive (% of turnover)")


def read_trial_balance(path: Path) -> dict:
    data = path.read_bytes()
    raw = tb_import.read_raw(data, path.name)
    header = tb_import.detect_header_row(raw)
    table = tb_import.build_table(raw, header)
    mapping = tb_import.guess_columns(table)
    ledgers = tb_import.classify(tb_import.normalise(table, mapping))
    return {"data": data, "meta": {"sheet": 0, "header_row": header + 1, "mapping": mapping},
            "ledgers": ledgers, "totals": tb_import.summarise(ledgers)}


def read_capital_gains(path: Path) -> dict:
    data = path.read_bytes()
    raw = cg_import.read_raw(data, path.name)
    table = cg_import.build_table(raw, cg_import.detect_header_row(raw))
    rows = cg_import.normalise(table, cg_import.guess_columns(table))
    total = cg_import.summarise(rows)
    return {"rows": rows, "statement": total, "after": cg_import.set_off(total["buckets"])}


def build(folder: Path) -> dict:
    """Everything needed to save one demo client: inputs, working, and the trial balance if it has one."""
    p = json.loads((folder / "client.json").read_text(encoding="utf-8"))
    rules = load_rules()
    start, end = date.fromisoformat(rules["start"]), date.fromisoformat(rules["end"])
    b = p.get("business", {"mode": "none"})
    mode, tb, presumptive = b.get("mode", "none"), None, False
    if mode == "trial_balance":
        tb = read_trial_balance(folder / b["file"])
        tb["filename"] = b["file"]
        t, books = tb["totals"], date.fromisoformat(b["books_date"])
        proj = project_business(t["recurring_income"], t["recurring_expense"], t["one_off_income"], t["one_off_expense"],
                                t["opening_stock"], b.get("closing_stock", 0), start, books, end,
                                b.get("add_backs", 0), b.get("less_deductions", 0), b.get("growth", 0))
        business = proj["projected_business_income"]
        working = {"mode": MODE_TB, "f_books_date": books.isoformat(), "f_growth": float(b.get("growth", 0)),
                   "f_rec_income": t["recurring_income"], "f_rec_expense": t["recurring_expense"],
                   "f_oneoff_income": t["one_off_income"], "f_oneoff_expense": t["one_off_expense"],
                   "f_opening_stock": t["opening_stock"], "f_closing_stock": float(b.get("closing_stock", 0)),
                   "f_add_backs": float(b.get("add_backs", 0)), "f_less_deductions": float(b.get("less_deductions", 0))}
    elif mode == "presumptive":
        books, presumptive = date.fromisoformat(b["books_date"]), True
        business = project_presumptive(b["turnover"], b["rate"], start, books, end, b.get("growth", 0))["projected_business_income"]
        working = {"mode": MODE_PRESUMPTIVE, "f_turnover": float(b["turnover"]), "f_presumptive_rate": float(b["rate"]),
                   "f_books_date": books.isoformat(), "f_growth": float(b.get("growth", 0))}
    else:
        business = float(b.get("amount", 0))
        working = {"mode": MODE_DIRECT, "f_direct_business": business}
    working["mobile"] = p.get("mobile", "")

    gains = {k: 0 for k in cg_import.BUCKETS}
    if p.get("capital_gains_file"):
        gains = read_capital_gains(folder / p["capital_gains_file"])["after"]["buckets"]
    tds = 0
    if p.get("form_26as_file"):
        tds = form26as_read.read((folder / p["form_26as_file"]).read_bytes(), p["form_26as_file"])["total_deposited"]

    inp = ClientInputs(
        name=p["name"], constitution=p["constitution"], age_band=p.get("age_band", "below60"),
        resident=p.get("resident", True), regime=p.get("regime", "auto"), presumptive=presumptive,
        business_income=float(business), salary_gross=float(p.get("salary", 0)),
        hp_let_out_rent=float(p.get("hp_let_out_rent", 0)), hp_municipal_tax=float(p.get("hp_municipal_tax", 0)),
        hp_let_out_interest=float(p.get("hp_let_out_interest", 0)),
        hp_self_occupied_interest=float(p.get("hp_self_occupied_interest", 0)),
        stcg_equity=float(gains["stcg_equity"]), ltcg_equity=float(gains["ltcg_equity"]),
        ltcg_other=float(gains["ltcg_other"]), stcg_other=float(gains["stcg_other"]),
        other_interest=float(p.get("other_interest", 0)), other_dividend=float(p.get("other_dividend", 0)),
        other_misc=float(p.get("other_misc", 0)), deductions_old=float(p.get("deductions_old", 0)),
        tds_tcs=float(tds + p.get("extra_tds_expected", 0)), payments=p.get("payments", []))
    return {"profile": p, "inputs": inp, "working": working, "trial_balance": tb}


def client_folders(root: Path | None = None) -> list[Path]:
    root = root or DEMO_DIR
    if not root.exists():
        return []
    return sorted(d for d in root.iterdir() if d.is_dir() and (d / "client.json").exists())


def load_demo_folder(con, root: Path | None = None) -> list[str]:
    """Save every client in the folder (replacing a demo client of the same name). Returns the names loaded."""
    names = []
    for folder in client_folders(root):
        item = build(folder)
        inp, p = item["inputs"], item["profile"]
        storage.save_client(con, inp.name, inp.to_dict(), item["working"])
        tb = item["trial_balance"]
        if tb:
            cols = ["ledger", "group", "net", "type", "review", "one_off"]
            storage.save_trial_balance(con, inp.name, tb["filename"], tb["data"], tb["meta"],
                                       tb["ledgers"][cols].to_dict("records"))
        if p.get("form_26as_file"):
            target = storage.data_dir() / "26AS" / portal_26as.safe_folder_name(inp.name)
            target.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(folder / p["form_26as_file"], target / "26AS (demo).txt")
        names.append(inp.name)
    return names
