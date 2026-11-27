"""Contract-note check. Runs on this laptop only. Reads ALL Zerodha contract notes in one go.

What it does
  1. Finds every PDF in folders under C:\\AICA_private whose folder name has 'contract notes'.
  2. Opens each with the password saved under the label zerodha_cn (asks once, hidden, if none is saved).
  3. Reads and runs the checks in zcn.py. Prints one line per note: trade date, counts, PASS or FAIL.
     For a FAIL it names the check and the SIZE of the difference only. No names, no prices, no amounts.
  4. Saves that text as C:\\AICA_private\\zerodha_cn_out\\zcn_check.txt (this is the file to attach).
  5. Writes C:\\AICA_private\\zerodha_cn_out\\buys.csv, sells.csv and charges.csv with the real buy rows (date, ISIN, name, quantity, value before and after brokerage, average price).
     That file STAYS on this laptop. Never attach it. It is the share-cost source for the private dashboard.
Nothing is sent anywhere. No PDF is changed.

Use:  py zcn_check.py                (looks in C:\\AICA_private)
      py zcn_check.py "D:\\other\\folder"
"""
import csv
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cdsl            # noqa: E402
import secrets_store   # noqa: E402
import zcn             # noqa: E402

LABEL = "zerodha_cn"


def find_pdfs(base):
    out = []
    for pdf in sorted(base.rglob("*.pdf")):
        if "contract notes" in pdf.parent.name.lower() and "zerodha_cn_out" not in pdf.parts and "Inbox" not in pdf.parts:
            out.append(pdf)
    return out


def open_note(pdf, state):
    """Returns pages. Uses the saved password; asks once if there is none or it is wrong."""
    pw = state.get("pw") or secrets_store.get(LABEL)
    for attempt in range(2):
        if pw:
            try:
                pages = cdsl.read_rows(pdf, pw)
                state["pw"] = pw
                return pages
            except cdsl.PasswordError:
                pw = None
        if attempt == 0:
            pw = getpass.getpass("  Contract note password (hidden): ")
            try:
                pages = cdsl.read_rows(pdf, pw)
                try:
                    secrets_store.put(LABEL, pw)
                    print("  Saved as 'zerodha_cn'.")
                except RuntimeError:
                    print("  Not saved (keyring missing).")
                state["pw"] = pw
                return pages
            except cdsl.PasswordError:
                pw = None
    raise cdsl.PasswordError()


def main(argv):
    base = Path(argv[1].strip('"')) if len(argv) > 1 else Path(r"C:\AICA_private")
    pdfs = find_pdfs(base)
    if not pdfs:
        print("No contract notes found under", base)
        return 1
    lines, buys, sells, charges, state = [], [], [], [], {}
    nfail = nopen = 0
    for i, pdf in enumerate(pdfs, 1):
        try:
            pages = open_note(pdf, state)
        except cdsl.PasswordError:
            lines.append(f"note {i}: NOT OPENED (wrong password)")
            nopen += 1
            continue
        except cdsl.NeedsPackageError as e:
            print(f"A package is missing. Type:  pip install pdfminer.six cryptography    ({e})")
            return 1
        d = zcn.parse(pages)
        res = zcn.run_checks(d)
        bad = [(n, det) for n, st, det in res if st == "FAIL"]
        td = d["trade_date"].isoformat() if d["trade_date"] else "no date"
        lines.append(f"note {i}: trade date {td}   securities {len(d['summary'])}   trades {len(d['trades'])}   "
                     f"checks {len(res) - len(bad)} PASS, {len(bad)} FAIL")
        for n, det in bad:
            lines.append(f"    FAIL  {n}  ->  {det}")
        if bad:
            lines.extend(zcn.diagnose(d))
        nfail += bool(bad)
        if not bad:                                   # only notes that passed every check feed the cost file
            buys.extend(zcn.buys(d))
            sells.extend(zcn.sells(d))
            charges.extend({"trade_date": d["trade_date"], "label": x["label"], "value": x["value"]} for x in d["charges"])
    lines.append("")
    lines.append(f"NOTES: {len(pdfs)}   NOT OPENED: {nopen}   WITH A FAIL: {nfail}")
    lines.append("RESULT: " + ("ALL NOTES PASS" if nfail == 0 and nopen == 0 else "CHECK THE FAIL LINES ABOVE"))
    body = "\n".join(lines)
    print(body)
    out = base / "zerodha_cn_out"
    out.mkdir(exist_ok=True)
    (out / "zcn_check.txt").write_text(body, encoding="utf-8")
    if not buys and (nopen or nfail):
        print("\nbuys.csv NOT written: no note passed. Any older buys.csv is left as it was.")
        print("Saved (counts and checks only, attach this):", out / "zcn_check.txt")
        return 1
    with open(out / "buys.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["trade_date", "isin", "name", "buy_qty", "gross_value", "brokerage", "value_incl_brokerage", "avg_price_incl_brokerage"])
        for b in sorted(buys, key=lambda x: (x["trade_date"] or 0, x["isin"])):
            w.writerow([b["trade_date"], b["isin"], b["name"], b["buy_qty"], b["gross_value"], b["brokerage"], b["value_incl_brokerage"], b["avg_price_incl_brokerage"]])
    with open(out / "sells.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["trade_date", "isin", "name", "sell_qty", "gross_value", "brokerage", "value_after_brokerage", "avg_price_after_brokerage"])
        for b in sorted(sells, key=lambda x: (x["trade_date"] or 0, x["isin"])):
            w.writerow([b["trade_date"], b["isin"], b["name"], b["sell_qty"], b["gross_value"], b["brokerage"], b["value_after_brokerage"], b["avg_price_after_brokerage"]])
    with open(out / "charges.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["trade_date", "label", "value"])
        for b in sorted(charges, key=lambda x: (x["trade_date"] or 0, x["label"])):
            w.writerow([b["trade_date"], b["label"], b["value"]])
    if nopen or nfail:
        print(f"\nNote: buys.csv holds only the {len(pdfs) - nopen - nfail} notes that passed every check.")
    print("\nSaved (counts and checks only, attach this):", out / "zcn_check.txt")
    print("Saved (real buy rows, stays on this laptop, do NOT attach):", out / "buys.csv")
    print("Saved (real sell rows, stays on this laptop, do NOT attach):", out / "sells.csv")
    print("Saved (real charges, stays on this laptop, do NOT attach):", out / "charges.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
