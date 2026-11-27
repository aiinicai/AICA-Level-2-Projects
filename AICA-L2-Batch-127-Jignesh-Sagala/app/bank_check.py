"""Bank statement check. Runs on this laptop only. Reads two bank statement layouts in one go: bank_a (savings statement, one table with a running balance) and bank_b (customer statement with term deposits).

What it does
  1. Finds the statement PDFs under C:\\AICA_private (same folder-name rules as probe_all.py): bank_a and bank_b.
  2. Opens each with the password saved under its label (bank_a, bank_b). Asks once, hidden, if none is saved.
  3. Reads each file and runs the checks in bank.py. Prints one line per file, then PASS or FAIL lines.
     For a FAIL it names the check and the SIZE of the difference only. No names, no account numbers, no amounts.
  4. Saves that text as C:\\AICA_private\\bank_out\\bank_check.txt   (this is the file to attach).
  5. Writes bank_balances.csv and fixed_deposits.csv in the same folder from files that passed every check.
     Those two files hold real balances. They STAY on this laptop. Never attach them.
Nothing is sent anywhere. No PDF is changed.

Use:  py bank_check.py                (looks in C:\\AICA_private)
      py bank_check.py "D:\\other\\folder"
"""
import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bank            # noqa: E402
import cdsl            # noqa: E402
import probe_all       # noqa: E402


def collect(base):
    """(pdf, label, n) for every labelled statement, numbered per label exactly as probe_all.py numbers them."""
    out, counts = [], {}
    for pdf in sorted(base.rglob("*.pdf")):
        if any(x in pdf.parts for x in ("probe_out", "probe_all_out", "Inbox", "zerodha_cn_out", "bank_out")):
            continue
        lab = probe_all.label_for(pdf)
        if lab:
            counts[lab] = counts.get(lab, 0) + 1
            if lab in ("bank_a", "bank_b"):
                out.append((pdf, lab, counts[lab]))
    return out


def masked_dump(pages):
    """Masked rows of every page that has transaction lines (digits -> 9, words -> x). Safe to attach."""
    out = ["    --- masked transaction pages of this file (digits 9, words x) ---"]
    for n, pg in enumerate(pages, 1):
        if not any(bank.I_TXN.match(r) or "Brought Forward" in r or "Carried Forward" in r for r in pg):
            continue
        text = "\n".join(probe_all.cdsl_check.mask(r) for r in pg[:80] if not re.search(r"[^\x00-\x7f]", r))
        err = probe_all.cdsl_check.self_check(text)
        out.append(f"    --- page {n} ---" if not err else f"    --- page {n} not shown (self-check: {err}) ---")
        if not err:
            out.extend("    " + x for x in text.split("\n"))
    return out


def main(argv):
    base = Path(argv[1].strip('"')) if len(argv) > 1 else Path(r"C:\AICA_private")
    files = collect(base)
    if not files:
        print("No bank_a or bank_b statements found under", base)
        return 1
    lines, nfail, nopen = [], 0, 0
    dumped = False
    kotak_ok, indus_ok = [], []                      # parsed files that passed every check
    for pdf, lab, n in files:
        tag = f"{lab} file {n}"
        try:
            pages, how = probe_all.open_with_saved_or_ask(pdf, lab, n)
        except cdsl.PasswordError:
            lines.append(f"{tag}: NOT OPENED (wrong password)")
            nopen += 1
            continue
        except cdsl.NeedsPackageError as e:
            print(f"A package is missing. Type:  pip install pdfminer.six cryptography    ({e})")
            return 1
        if lab == "bank_a":
            d = bank.kotak_parse(pages)
            res = bank.kotak_checks(d)
            head = f"{tag}: rows {len(d['rows'])}, summary lines {len(d['summary'])}, pages {len(pages)}"
        else:
            d = bank.indus_parse(pages)
            res = bank.indus_checks(d)
            head = (f"{tag}: accounts {len(d['summary'])}, term deposits {len(d['fds'])}, transaction blocks {len(d['blocks'])}, "
                    f"rows {sum(len(b['rows']) for b in d['blocks'])}, pages {len(pages)}")
        bad = [(x, det) for x, s, det in res if s == "FAIL"]
        lines.append(f"{head}   checks {len(res) - len(bad)} PASS, {len(bad)} FAIL")
        for x, det in bad:
            lines.append(f"    FAIL  {x}  ->  {det}")
        if bad:
            lines.extend(bank.kotak_diag(d) if lab == "bank_a" else bank.indus_diag(d))
            if lab == "bank_b" and not dumped:          # layout of the transaction pages, masked like probe_all.py
                dumped = True
                lines.extend(masked_dump(pages))
        else:
            (kotak_ok if lab == "bank_a" else indus_ok).append(d)
        nfail += bool(bad)
    # bank_b: two copies of the same statement may sit in the folder. Compare them, keep the one made last.
    keep_indus = []
    if indus_ok:
        indus_ok.sort(key=lambda d: d["generated"] or d["period"][1])
        keep_indus = [indus_ok[-1]]
        if len(indus_ok) > 1:
            sig = lambda d: sorted((r["account"][-4:], str(r["balance"])) for r in d["summary"]) + sorted((r["account"][-4:], str(r["value"])) for r in d["fds"])
            same = all(sig(x) == sig(indus_ok[-1]) for x in indus_ok[:-1])
            lines.append(f"bank_b: {len(indus_ok)} files read OK. Same balances and term deposits in all of them: {'PASS' if same else 'FAIL'}. Latest one is used.")
            nfail += not same
    seen, keep_kotak = set(), []
    for d in kotak_ok:
        if d["account"] not in seen:
            seen.add(d["account"])
            keep_kotak.append(d)
    if len(keep_kotak) < len(kotak_ok):
        lines.append(f"bank_a: {len(kotak_ok) - len(keep_kotak)} file(s) repeat an account already read and are ignored.")
    lines.append("")
    lines.append(f"FILES: {len(files)}   NOT OPENED: {nopen}   WITH A FAIL: {nfail}")
    lines.append("RESULT: " + ("ALL FILES PASS" if nfail == 0 and nopen == 0 else "CHECK THE FAIL LINES ABOVE"))
    body = "\n".join(lines)
    print(body)
    out = base / "bank_out"
    out.mkdir(exist_ok=True)
    (out / "bank_check.txt").write_text(body, encoding="utf-8")
    bal = [r for d in keep_kotak for r in bank.kotak_balances(d)] + [r for d in keep_indus for r in bank.indus_balances(d)]
    fds = [r for d in keep_indus for r in bank.indus_fds(d)]
    if not bal and not fds:
        print("\nbank_balances.csv NOT written: no file passed. Older files are left as they were.")
        print("Saved (counts and checks only, attach this):", out / "bank_check.txt")
        return 1
    with open(out / "bank_balances.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["bank", "account_last4", "kind", "currency", "as_of", "balance"])
        for r in bal:
            w.writerow([r["bank"], r["account_last4"], r["kind"], r["currency"], r["as_of"], r["balance"]])
    with open(out / "fixed_deposits.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["bank", "account_last4", "kind", "start", "maturity", "currency", "rate_pct", "lien", "current_value"])
        for r in fds:
            w.writerow([r["bank"], r["account_last4"], r["kind"], r["start"], r["maturity"], r["currency"], r["rate_pct"], r["lien"], r["current_value"]])
    if nfail or nopen:
        print("\nNote: the CSV files hold only the files that passed every check.")
    print("\nSaved (counts and checks only, attach this):", out / "bank_check.txt")
    print("Saved (real balances, stay on this laptop, do NOT attach):", out / "bank_balances.csv", "and", out / "fixed_deposits.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
