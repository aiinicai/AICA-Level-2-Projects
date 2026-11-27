"""Zerodha funds ledger check. Runs on this laptop only.

What it does
  1. Finds the Zerodha weekly account statement PDFs under C:\\AICA_private (same folder rule as probe_all.py).
  2. Opens each with the password saved under 'zerodha'. Asks once, hidden, if none is saved.
  3. Reads the files that are funds ledgers (the securities statement is skipped) and runs the checks in zledger.py.
     For a FAIL it names the check and counts only. No amounts, no names.
  4. Saves that text as C:\\AICA_private\\zerodha_ledger_out\\zledger_check.txt   (this is the file to attach).
  5. Writes zerodha_cash.csv (statement end date and closing cash balance) from the latest ledger that passed every check.
     That file holds a real balance. It STAYS on this laptop. Never attach it.
Nothing is sent anywhere. No PDF is changed.

Use:  py zledger_check.py                (looks in C:\\AICA_private)
      py zledger_check.py "D:\\other\\folder"
"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cdsl            # noqa: E402
import probe_all       # noqa: E402
import zledger         # noqa: E402


def main(argv):
    base = Path(argv[1].strip('"')) if len(argv) > 1 else Path(r"C:\AICA_private")
    files, counts = [], {}
    for pdf in sorted(base.rglob("*.pdf")):
        if any(x in pdf.parts for x in ("probe_out", "probe_all_out", "Inbox", "zerodha_cn_out", "bank_out", "zerodha_ledger_out")):
            continue
        lab = probe_all.label_for(pdf)
        if lab:
            counts[lab] = counts.get(lab, 0) + 1
            if lab == "zerodha":
                files.append((pdf, counts[lab]))
    if not files:
        print("No Zerodha weekly statements found under", base)
        return 1
    lines, good, nfail, nopen, nledger = [], [], 0, 0, 0
    for pdf, n in files:
        tag = f"zerodha file {n}"
        try:
            pages, how = probe_all.open_with_saved_or_ask(pdf, "zerodha", n)
        except cdsl.PasswordError:
            lines.append(f"{tag}: NOT OPENED (wrong password)")
            nopen += 1
            continue
        except cdsl.NeedsPackageError as e:
            print(f"A package is missing. Type:  pip install pdfminer.six cryptography    ({e})")
            return 1
        d = zledger.parse(pages)
        if not d["is_funds"]:
            lines.append(f"{tag}: not a funds ledger (securities statement), skipped. Pages {len(pages)}")
            continue
        nledger += 1
        res = zledger.checks(d)
        bad = [(x, det) for x, s, det in res if s == "FAIL"]
        lines.append(f"{tag}: funds ledger, rows {len(d['rows'])}, pages {len(pages)}   checks {len(res) - len(bad)} PASS, {len(bad)} FAIL")
        for x, det in bad:
            lines.append(f"    FAIL  {x}  ->  {det}")
        if bad:
            lines.extend(zledger.diag(d))
        else:
            good.append(d)
        nfail += bool(bad)
    lines.append("")
    lines.append(f"FILES: {len(files)}   FUNDS LEDGERS: {nledger}   NOT OPENED: {nopen}   WITH A FAIL: {nfail}")
    lines.append("RESULT: " + ("ALL LEDGERS PASS" if nfail == 0 and nopen == 0 and nledger > 0 else "CHECK THE LINES ABOVE"))
    body = "\n".join(lines)
    print(body)
    out = base / "zerodha_ledger_out"
    out.mkdir(exist_ok=True)
    (out / "zledger_check.txt").write_text(body, encoding="utf-8")
    if not good:
        print("\nzerodha_cash.csv NOT written: no ledger passed. An older file is left as it was.")
        print("Saved (counts and checks only, attach this):", out / "zledger_check.txt")
        return 1
    best = max(good, key=lambda d: d["to"])
    c = zledger.closing(best)
    with open(out / "zerodha_cash.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["as_of", "closing_cash_balance", "sign_convention"])
        w.writerow([c["as_of"], c["balance"], c["convention"]])
    print("\nSaved (counts and checks only, attach this):", out / "zledger_check.txt")
    print("Saved (real cash balance, stays on this laptop, do NOT attach):", out / "zerodha_cash.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
