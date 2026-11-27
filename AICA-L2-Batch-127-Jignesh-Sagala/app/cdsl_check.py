"""CDSL CAS check. Runs on this laptop only. Prints and saves counts and PASS/FAIL, never figures or names.

What it does
  1. Asks for the PDF password (typed, not shown, not saved).
  2. Reads the statement by page position and runs the self-checks (cdsl.py).
  3. Prints counts and PASS/FAIL. For a FAIL it shows only the size of the difference.
  4. Saves the same text as a file under probe_out, next to the PDF. Counts and differences are real numbers.
     Any statement row shown is masked: digits become 9, words become x's.
     Optional: pages given on the command line also save the rows as the reader sees them, masked the same way.
Nothing is sent anywhere. The PDF is not changed.

Use:  py cdsl_check.py "C:\\path\\to\\cas.pdf" [first page] [how many pages] [--ask]
      Without --ask it uses the password saved by set_password.py (label: cas).
"""
import getpass
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cdsl  # noqa: E402

KEEP = {w.lower() for w in """
consolidated account statement mutual fund funds folio folios no number name isin ucc scheme schemes
opening closing balance unit units nav date dates transaction transactions description amount amounts
purchase purchases redemption switch in out sip systematic investment plan direct regular growth
idcw dividend payout reinvestment cost value market total summary holding holdings period from to
page of portfolio demat account securities security quantity price stamp duty tax stt registrar
equity debt hybrid cap mid large small flexi index liquid nominee kyc pan mode joint first holder
bank rs inr dr cr jan feb mar apr may jun jul aug sep oct nov dec
bo dp id client depository participant beneficiary details commission advisor arn
load redemptions gain loss net valuation as on for and the by with at is are new
cumulative invested bonds corporate etf etfs average type status exit grand
current free lent safekeep pledged face month change allocation asset class
""".split()}


def mask(t):
    t = re.sub(r"\d", "9", t)
    return re.sub(r"[A-Za-z]+", lambda m: m.group(0) if m.group(0).lower() in KEEP
                  else "".join("X" if c.isupper() else "x" for c in m.group(0)), t)


def self_check(masked):
    if re.search(r"[0-8]", masked):
        return "a digit other than 9 is left"
    for w in re.findall(r"[A-Za-z]+", masked):
        if w.lower() in KEEP:
            continue
        if re.fullmatch(r"[Xx]+", w) is None:
            return "an unmasked word is left"
    return None


def main(argv):
    ask = "--ask" in argv
    argv = [a for a in argv if a != "--ask"]
    if len(argv) not in (2, 3, 4):
        print(__doc__)
        return 1
    pdf = Path(argv[1].strip('"'))
    if not pdf.exists():
        print("File not found:", pdf)
        return 1
    first = int(argv[2]) if len(argv) > 2 else None
    count = int(argv[3]) if len(argv) > 3 else 3
    import secrets_store
    pw = None if ask else secrets_store.get("cas")
    if pw:
        print("Using the saved CAS password (py set_password.py cas to change it).")
    else:
        pw = getpass.getpass("PDF password (typing is hidden): ")
    try:
        try:
            pages = cdsl.read_rows(pdf, pw)
        except cdsl.PasswordError:
            if not ask and secrets_store.get("cas") == pw:
                print("The saved password did not open the file.")
                pw = getpass.getpass("PDF password (typing is hidden): ")
                pages = cdsl.read_rows(pdf, pw)
            else:
                raise
    except cdsl.PasswordError:
        print("The password did not open the file. Nothing saved.")
        return 1
    except cdsl.NeedsPackageError as e:
        print(f"A package is missing. Type:  pip install pdfminer.six cryptography    ({e})")
        return 1
    d = cdsl.parse(pages)

    lines = []
    out = lines.append
    pc, pl = cdsl.LAST_READER["pieces"]
    out(f"READER USED: {cdsl.LAST_READER['used']}   rows found by each reader: {cdsl.LAST_READER['rows']}   "
        f"pypdf text pieces: {pc}, average length {pl / pc:.1f} characters" if pc else
        f"READER USED: {cdsl.LAST_READER['used']}   rows found by each reader: {cdsl.LAST_READER['rows']}")
    out(f"PAGES: {len(pages)}   ROWS READ: {d['rows_seen']}")
    out(f"PERIOD FOUND: {'yes' if d['period'] else 'NO'}")
    out(f"MONTHS IN 12-MONTH TABLE: {len(d['months'])}   ASSET CLASSES: {len(d['asset_split'])}")
    out(f"MUTUAL FUND FOLIO ROWS: {len(d['mf_holdings'])}   (zero-unit rows: {sum(1 for x in d['mf_holdings'] if x['units'] == 0)})")
    ntx = sum(len(b['txns']) for b in d['mf_txn'].values())
    out(f"MF TRANSACTION SCHEMES: {len(d['mf_txn'])}   TRANSACTIONS: {ntx}   "
        f"(purchases {sum(1 for b in d['mf_txn'].values() for x in b['txns'] if x['units'] is not None and x['units'] > 0)}, "
        f"redemptions {sum(1 for b in d['mf_txn'].values() for x in b['txns'] if x['units'] is not None and x['units'] < 0)}, "
        f"unread {sum(1 for b in d['mf_txn'].values() for x in b['txns'] if x['units'] is None)})")
    out(f"DEMAT HOLDING ROWS: {len(d['demat'])}   (zero-quantity rows: {sum(1 for x in d['demat'] if x['qty'] == 0)})")
    out("")
    out("CHECKS")
    nfail = 0
    for name, st, det in cdsl.run_checks(d):
        out(f"  {st:4}  {name}  ->  {det}")
        nfail += st == "FAIL"
    out("")
    out(f"RESULT: {'ALL CHECKS PASS' if nfail == 0 else str(nfail) + ' CHECK(S) FAIL'}")
    un = d["unplaced"]["mf_holdings"]
    withnum = [r for r in un if re.search(r"\d[\d,]*\.\d", r)]
    out("")
    out(f"ROWS INSIDE THE FOLIO TABLE NOT READ AS A FOLIO ROW: {len(un)} (wrapped scheme-name lines are normal); of these with decimal numbers: {len(withnum)}")
    for r in withnum[:12]:
        out("  " + mask(r))
    body = "\n".join(lines)
    m = mask(body)
    err = self_check(m)
    print(body)
    folder = pdf.parent / "probe_out"
    folder.mkdir(exist_ok=True)
    if err:
        print("\nNot saved: self-check failed (" + err + ").")
        return 1
    f1 = folder / f"{pdf.stem}_cdsl_check.txt"
    f1.write_text(body, encoding="utf-8")
    print("\nSaved (counts and checks only):", f1)

    if first:
        rows = []
        for pno in range(first, min(first + count, len(pages) + 1)):
            rows.append("===== NEW PAGE =====")
            rows.extend(mask(r) for r in pages[pno - 1] if not re.search(r"[^\x00-\x7f]", r))
        text = "\n".join(rows)
        err = self_check(text)
        if err:
            print("Row file not saved: self-check failed (" + err + ").")
            return 1
        f2 = folder / f"{pdf.stem}_cdsl_rows_p{first}-{first + count - 1}.txt"
        f2.write_text(text, encoding="utf-8")
        print("Saved (masked rows as the reader sees them):", f2)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
