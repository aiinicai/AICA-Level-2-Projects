"""Demo of the INPUT and PROCESS steps on MADE-UP statements. No real data.

  1. Makes small locked statements for "BusyMe" in the folder  samples/  (password  Demo@2026 ):
       cdsl_made_up.pdf        consolidated fund and demat statement (CAMS / CDSL style)
       contract_note_*.pdf     broker contract notes (Zerodha style), two trade days
       kotak_a.pdf, indus_a.pdf   two bank statement layouts
       funds_ledger.pdf        broker funds ledger
  2. Opens each one with its reader, using the password, and runs the reader's own checks.
  3. Prints only counts and PASS / FAIL, the same way the real run on the owner's laptop reports.
  4. Shows that a wrong password is refused.

Use:  py tools\\demo_readers.py          (needs  pip install -r requirements-extra.txt )
The made-up PAN is ABCDE1234F. The real run uses the same readers on real statements, only on the owner's laptop.
"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))
sys.path.insert(0, str(ROOT / "tools"))
import bank                      # noqa: E402
import cdsl                      # noqa: E402
import make_dummy_bank as g_bank       # noqa: E402
import make_dummy_cdsl as g_cdsl       # noqa: E402
import make_dummy_zcn as g_zcn         # noqa: E402
import make_dummy_zledger as g_led     # noqa: E402
import zcn                       # noqa: E402
import zledger                   # noqa: E402

PW = "Demo@2026"
SAMPLES = ROOT / "samples"
FAILS = []


def report(title, results):
    print(f"\n{title}")
    for name, st, detail in results:
        print(f"  {st:4}  {name}" + (f"  ->  {detail}" if detail and st != "PASS" else ""))
        if st == "FAIL":
            FAILS.append(name)


def make():
    SAMPLES.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        g_cdsl.main(["x", str(t), "1"])
        g_zcn.main(["x", str(t), "1", "2"])
        g_bank.main(["x", str(t), "1"])
        g_led.build(t, 1, "credit")
        for src, dst in [("cdsl_made_up.pdf", "cdsl_made_up.pdf"), ("kotak_a.pdf", "kotak_a.pdf"), ("indus_a.pdf", "indus_a.pdf"),
                         ("ledger.pdf", "funds_ledger.pdf")]:
            shutil.copy(t / src, SAMPLES / dst)
        for i, p in enumerate(sorted(t.glob("*contract-notes*.pdf")), 1):
            shutil.copy(p, SAMPLES / f"contract_note_{i}.pdf")


def main():
    make()
    print(f"Made-up statements are in: {SAMPLES}   (password {PW})")
    pages = cdsl.read_rows(SAMPLES / "cdsl_made_up.pdf", PW)
    d = cdsl.parse(pages)
    print(f"\nFund and demat statement: {len(d['mf_holdings'])} folio rows, {len(d['demat'])} demat rows, "
          f"{sum(len(b['txns']) for b in d['mf_txn'].values())} fund transactions")
    report("Fund and demat statement checks", cdsl.run_checks(d))
    for p in sorted(SAMPLES.glob("contract_note_*.pdf")):
        dd = zcn.parse(cdsl.read_rows(p, PW))
        report(f"Contract note {p.name}: {len(dd['trades'])} trades", zcn.run_checks(dd))
    kd = bank.kotak_parse(cdsl.read_rows(SAMPLES / "kotak_a.pdf", PW))
    report(f"Bank statement kotak_a.pdf: {len(kd['rows'])} rows", bank.kotak_checks(kd))
    idd = bank.indus_parse(cdsl.read_rows(SAMPLES / "indus_a.pdf", PW))
    report("Bank statement indus_a.pdf", bank.indus_checks(idd))
    ld = zledger.parse(cdsl.read_rows(SAMPLES / "funds_ledger.pdf", PW))
    report(f"Funds ledger funds_ledger.pdf: {len(ld['rows'])} rows", zledger.checks(ld))
    try:
        cdsl.read_rows(SAMPLES / "cdsl_made_up.pdf", "wrong password")
        print("\nWrong password: NOT refused (FAIL)")
        FAILS.append("wrong password")
    except cdsl.PasswordError:
        print("\nWrong password: refused (PASS)")
    print("\nRESULT:", "ALL PASS" if not FAILS else f"{len(FAILS)} FAIL")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
