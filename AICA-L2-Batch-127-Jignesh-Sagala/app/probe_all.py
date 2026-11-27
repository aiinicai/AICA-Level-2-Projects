"""Layout probe for ALL statement PDFs in one run. Runs on this laptop only.

What it does
  1. Looks through the statement folders under C:\\AICA_private (the 'Inbox' copies are skipped).
  2. Works out the statement type from the folder name: cas, bank_a, bank_b, zerodha, zerodha_cn, fund_a, fund_b.
  3. Opens each PDF with the password saved by set_password.py. If a type has none saved and the file is locked,
     it asks ONCE (hidden), opens the file, and saves the password for next time.
  4. Reads each file by position, masks it (digits become 9, words become x's, except plain heading words),
     checks its own output, and writes ONE text file: probe_all_masked.txt
  5. You attach that one file. Nothing else leaves your laptop. No PDF is changed.

Use:  py probe_all.py              (looks in C:\\AICA_private)
      py probe_all.py "D:\\other\\folder"
      py probe_all.py --only zerodha_cn   (one type only, first 2 files, own output file)
"""
import getpass
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cdsl            # noqa: E402
import cdsl_check      # noqa: E402
import secrets_store   # noqa: E402

cdsl_check.KEEP.update("""
upi neft imps rtgs cheque chq deposit withdrawal withdrawals debit credit debits credits interest charges particulars narration
ref reference txn tran branch ifsc micr customer cust crn address period brought forward carried
statement summary tds tax gst fee fees sweep nro nre savings current account a/c acct
ledger funds securities equity margin segment weekly pledge holdings quantity rate net amount settlement
dp isin scrip symbol exchange nse bse buy sell
""".split())

# (text found in the folder name, label). Labels here are generic. On a real run the owner edits the
# first text of the bank and fund lines to match his own folder names; the label is also the name the
# password is saved under in Windows Credential Manager.
RULES = [
    ("cdsl", "cas"), ("consolidated account statement", "cas"),
    ("bank a", "bank_a"),
    ("weekly account statement", "zerodha"),
    ("contract notes", "zerodha_cn"),
    ("fund house a", "fund_a"), ("fund house b", "fund_b"),
    ("bank b", "bank_b"),
]
FIRST_PAGES, LAST_PAGES, MAX_ROWS = 4, 2, 150


def label_for(pdf):
    name = pdf.parent.name.lower()
    for key, label in RULES:
        if key in name:
            return label
    return None


def is_locked(pdf):
    from pypdf import PdfReader
    r = PdfReader(str(pdf))
    return r.is_encrypted and not r.decrypt("")


def open_with_saved_or_ask(pdf, label, n):
    """Returns (pages, how) or raises. Tries label:n, then label, then asks once and saves."""
    if not is_locked(pdf):
        return cdsl.read_rows(pdf, ""), "no password needed"
    tried = set()
    for key in (f"{label}:{n}", label):
        pw = secrets_store.get(key)
        if pw and pw not in tried:
            tried.add(pw)
            try:
                return cdsl.read_rows(pdf, pw), f"saved password ({key})"
            except cdsl.PasswordError:
                pass
    pw = getpass.getpass(f"  Password for {label} file {n} (hidden): ")
    pages = cdsl.read_rows(pdf, pw)                     # raises PasswordError if wrong
    key = label if not secrets_store.get(label) else f"{label}:{n}"
    try:
        secrets_store.put(key, pw)
        return pages, f"typed, now saved as '{key}'"
    except RuntimeError:
        return pages, "typed (not saved: keyring missing)"


def masked_pages(pages):
    keep = list(range(1, min(FIRST_PAGES, len(pages)) + 1))
    for p in range(max(len(pages) - LAST_PAGES + 1, 1), len(pages) + 1):
        if p not in keep:
            keep.append(p)
    out = []
    for p in keep:
        out.append("--- page " + ("FIRST" if p <= FIRST_PAGES else "LAST") + " ---")
        rows = [r for r in pages[p - 1] if not re.search(r"[^\x00-\x7f]", r)][:MAX_ROWS]
        out.extend(cdsl_check.mask(r) for r in rows)
    return out


def main(argv):
    argv = list(argv)
    only = None
    if "--only" in argv:                      # py probe_all.py --only zerodha_cn  -> first 2 files of that type
        i = argv.index("--only")
        only = argv[i + 1]
        del argv[i:i + 2]
    base = Path(argv[1].strip('"')) if len(argv) > 1 else Path(r"C:\AICA_private")
    pdfs = []
    for pdf in sorted(base.rglob("*.pdf")):
        if "probe_out" in pdf.parts or "probe_all_out" in pdf.parts or "Inbox" in pdf.parts:
            continue
        lab = label_for(pdf)
        if lab and (only is None or lab == only):
            if only is None or sum(1 for p in pdfs if label_for(p) == only) < 2:
                pdfs.append(pdf)
    if not pdfs:
        print("No statement PDFs found under", base)
        return 1
    counts, blocks, report = {}, [], []
    for pdf in pdfs:
        label = label_for(pdf)
        counts[label] = counts.get(label, 0) + 1
        n = counts[label]
        tag = f"{label}_{n}"
        try:
            pages, how = open_with_saved_or_ask(pdf, label, n)
        except cdsl.PasswordError:
            print(f"  {tag}: password did not open the file - skipped")
            report.append(f"{tag}: NOT OPENED (wrong password)")
            continue
        except cdsl.NeedsPackageError as e:
            print(f"A package is missing. Type:  pip install pdfminer.six cryptography    ({e})")
            return 1
        rows = sum(len(p) for p in pages)
        body = masked_pages(pages)
        text = "\n".join(body)
        err = cdsl_check.self_check(text.replace("--- page FIRST ---", "").replace("--- page LAST ---", ""))
        if err:
            print(f"  {tag}: NOT saved, self-check failed ({err})")
            report.append(f"{tag}: NOT SAVED (self-check: {err})")
            continue
        head = f"##### FILE {tag}   type={label}   pages={len(pages)}   rows read={rows}   reader={cdsl.LAST_READER['used']}"
        blocks.append(head + "\n" + text)
        print(f"  {tag}: {len(pages)} pages, {rows} rows read ({how})")
        report.append(f"{tag}: ok, {len(pages)} pages, {rows} rows")
    out_dir = base / "probe_all_out"
    out_dir.mkdir(exist_ok=True)
    f = out_dir / (f"probe_all_masked_{only}.txt" if only else "probe_all_masked.txt")
    f.write_text("\n\n".join(["FILES: " + "; ".join(report)] + blocks), encoding="utf-8")
    print("\nSaved ONE file:", f)
    print("Open it, read it. If you see anything personal, do not share it. Then attach it here.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
