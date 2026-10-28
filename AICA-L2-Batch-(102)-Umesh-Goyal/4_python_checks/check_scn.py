r"""
check_scn.py - one script for any SCN.  AI reads, code counts, human decides.

How to use (IDLE or double-click, nothing to type):
  1. In Google AI Studio run the SCN with system_instruction.txt and copy the JSON it returns.
  2. Save it as  scn_output.json  in THIS folder (Notepad, paste, save).
  3. Open this file in IDLE and press F5.

It reads the JSON and
  A. works out the limitation dates for every financial year (section 73 / 74 / 74A) and the reply due date;
  B. re-does the arithmetic of the year-wise table (quantity x rate, tax on value, column sums against the
     Total row, issue amounts against the column sums);
  C. if the SCN PDF (or its OCR text) is in this folder, checks that every figure the AI reported really
     appears in the notice - this catches a misread or invented number;
  D. saves everything in  check_result_<scn no>.txt.

Optional:  py check_scn.py other.json  [notice.pdf]
It never sends anything anywhere.  Limitation uses the standard GSTR-9 due dates in scn_common.py;
extensions under section 168A must still be verified by you.
"""
import os
import re
import sys
from datetime import date

import scn_common as C

HERE = os.path.dirname(os.path.abspath(__file__))


def pick_json():
    if len(sys.argv) > 1 and sys.argv[1].lower().endswith(".json"):
        return sys.argv[1]
    default = os.path.join(HERE, "scn_output.json")
    if os.path.exists(default):
        return default
    try:
        import tkinter
        from tkinter import filedialog
        root = tkinter.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        path = filedialog.askopenfilename(title="Choose the JSON from AI Studio", filetypes=[("JSON", "*.json *.txt")])
        root.destroy()
        if path:
            return path
    except Exception:
        pass
    sys.exit("scn_output.json not found in %s. Save the AI Studio JSON there and run again." % HERE)


def pick_notice_text():
    """Text of the notice for the source check: PDF given on the command line, else the only PDF / *_ocr.txt in
    this folder. Returns (text, name) or (None, reason)."""
    paths = [a for a in sys.argv[1:] if a.lower().endswith((".pdf", ".txt"))]
    if not paths:
        pdfs = [f for f in os.listdir(HERE) if f.lower().endswith(".pdf")]
        ocrs = [f for f in os.listdir(HERE) if f.lower().endswith("_ocr.txt")]
        found = pdfs + ocrs
        if len(found) != 1:
            return None, ("no notice file in the folder" if not found else
                          "more than one notice file in the folder; give the one you want: py check_scn.py x.json y.pdf")
        paths = [os.path.join(HERE, found[0])]
    path = paths[0]
    try:
        text = open(path, encoding="utf-8", errors="ignore").read() if path.lower().endswith(".txt") else C.pdf_text(path)[0]
    except Exception as e:
        return None, "could not read %s (%s)" % (os.path.basename(path), e)
    if len(text.strip()) < 200:
        return None, "%s has no text layer (scanned). Run ocr_scanned_pdf.py first and keep the _ocr.txt here" % os.path.basename(path)
    return text, os.path.basename(path)


def main():
    path = pick_json()
    data = C.load_json_file(path)
    out = ["CHECK OF AI STUDIO JSON  (%s)" % os.path.basename(path),
           "Generated %s. AI reads, code counts, human decides - verify every line against the notice." % date.today().strftime("%d-%m-%Y"),
           "",
           "Notice  : %s | %s" % (data.get("scn_number"), data.get("act_and_section")),
           "Noticee : %s | GSTIN %s" % (data.get("noticee_name"), data.get("gstin")),
           "DIN     : %s" % data.get("din_status"),
           ""]
    problems = 0

    # ---------- A. limitation ----------
    out.append("A. LIMITATION AND REPLY DATE")
    scn = C.find_date(data.get("scn_date"))
    years = C.years_from_text(data.get("financial_years"))
    if not scn:
        out.append("   scn_date in the JSON is %r - cannot be read as dd-mm-yyyy. Check the notice." % data.get("scn_date"))
        problems += 1
    elif not years:
        out.append("   financial_years in the JSON is %r - no year like 2021-22 found. Check the notice." % data.get("financial_years"))
        problems += 1
    else:
        reply = C.find_date(data.get("reply_period_stated")) if re.search(r"\d{4}", str(data.get("reply_period_stated") or "")) else None
        lim = C.limitation_lines(scn, years, reply)
        out += ["   " + l if l else "" for l in lim]
        # a BARRED line matters only for the section the notice actually invokes
        sec = str(data.get("act_and_section") or "")
        invoked = "s.74A" if "74A" in sec.upper() else ("s.74" if "74" in sec else ("s.73" if "73" in sec else None))
        problems += sum(1 for l in lim if "skipped" in l or ("BARRED" in l and invoked and l.strip().startswith(invoked + ":")))
        out.append("   (Section invoked in the notice: %s - only its window is counted as a problem.)" % (invoked or "not recognised"))
        if not reply:
            out.append("   reply_period_stated = %r (no date printed in it): 30 days from the SCN date is assumed." % data.get("reply_period_stated"))
        hearing = data.get("personal_hearing_date")
        out.append("   Personal hearing (as printed): %s" % hearing)
    out.append("")

    # ---------- B. arithmetic ----------
    out.append("B. ARITHMETIC OF THE YEAR-WISE TABLE")
    rate_fwd = C.rate_from_text(data.get("issue_1_description"))
    rate_rcm = C.rate_from_text(data.get("issue_2_description"))
    out.append("   Rate taken from the issue description: issue 1 = %s, issue 2 = %s%s" % (
        "%g%%" % rate_fwd if rate_fwd is not None else "not found",
        "%g%%" % rate_rcm if rate_rcm is not None else "not found",
        "" if (rate_fwd is not None and rate_rcm is not None) else "  (where not found, only the implied rate is shown)"))
    lines, p = C.table_checks(data, rate_fwd, rate_rcm)
    out += ["   " + l if l else "" for l in lines]
    problems += p
    tax_total = sum(C.parse_num(data.get(k)) or 0 for k in ("issue_1_tax_amount", "issue_2_tax_amount"))
    pen = C.parse_num(data.get("penalty_amount"))
    if pen is not None:
        out.append("   Penalty printed %s | tax of both issues %s | %s" % (
            C.inr(pen), C.inr(tax_total), "equal" if abs(pen - tax_total) <= 1 else "different - note how the notice explains it"))
    out.append("")

    # ---------- C. figures against the notice ----------
    out.append("C. EVERY FIGURE OF THE JSON FOUND IN THE NOTICE?")
    text, name = pick_notice_text()
    if text is None:
        out.append("   Skipped: %s." % name)
    else:
        out.append("   Notice file used: %s" % name)
        lines, p = C.source_check(data, text)
        out += lines
        problems += p
    out.append("")

    out.append("RESULT: %s" % ("no mismatch found by this script - still verify against the notice."
                               if problems == 0 else "%d point(s) need attention - see MISMATCH / BARRED / NOT FOUND above." % problems))
    report = "\n".join(out)
    print(report)

    safe = re.sub(r"[^A-Za-z0-9]+", "_", str(data.get("scn_number") or "scn")).strip("_")[:40]
    target = os.path.join(HERE, "check_result_%s.txt" % safe)
    with open(target, "w", encoding="utf-8") as f:
        f.write(report + "\n")
    print("\nSaved: " + target)


if __name__ == "__main__":
    main()
