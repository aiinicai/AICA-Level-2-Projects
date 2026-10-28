"""Additional regulatory information and other statutory disclosures (Schedule III Division I, Companies Act 2013, AS).

A Tally trial balance holds some of the facts these disclosures need and not others. Each section therefore fills
in what the books show, says where it came from, and leaves the rest as "[Management to provide]". Nothing is
presented as nil or as complied with unless the books show it; a declaration only management can give is left for
management. The statements carry these sections after the notes (Word: its own part; Excel: the Disclosures sheet).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .format import dmy

TBD = "[Management to provide]"
CONFIRM = "[Management to confirm]"
NOT_LOADED = "Not loaded"      # a previous-year profit and loss figure: only one year was loaded

RELATED = re.compile(r"director|\bkmp\b|key managerial|promoter|relative|holding co|subsidiar|associate|partner|proprietor|"
                     r"shareholder|\bmd\b|managing", re.I)
CSR_RULE = {"net_worth": 500e7, "turnover": 1000e7, "profit": 5e7}      # Sec 135(1): Rs 500 cr, Rs 1,000 cr, Rs 5 cr


@dataclass
class Disclosure:
    no: str
    title: str
    ref: str
    header: list
    rows: list                                  # lists of strings
    comment: str = ""
    widths: list = field(default_factory=list)  # relative column widths


def _ledgers(m, pattern=None, lines=None, exclude=None):
    d = m.mapping
    if lines:
        d = d[d["line"].str.startswith(tuple(lines))]
    if pattern:
        d = d[d["ledger"].str.contains(pattern, case=False, regex=True)]
    if exclude:
        d = d[~d["ledger"].str.contains(exclude, case=False, regex=True)]
    return d


def disclosure_sections(m) -> list:
    u = m.unit

    def money(x):
        return u.fmt(abs(x)) if x else "-"

    def total(d, col="closing"):
        return float(d[col].abs().sum()) if len(d) else 0.0

    fig, pl, fprev = m.figures["cur"], m.figures["pl"], m.figures["prev"]
    out: list[Disclosure] = []

    def pair(cur):
        """[current, previous] for a figure of the year: the previous year's profit and loss was not loaded."""
        return [cur, TBD if cur == TBD else NOT_LOADED]

    ratio_no = next((n.no for n in m.notes if n.title == "Analytical ratios"), None)

    # ---- D1 payment to auditors (Sec 143, Sch III: other expenses)
    exp = _ledgers(m, r"audit|auditor", ["EXP."], r"outstanding")
    tax_audit = _ledgers(m, r"tax audit|3CD", ["EXP."])
    stat = total(exp) - total(tax_audit)
    payable = _ledgers(m, r"audit", ["CL."])
    rows = [["Statutory audit fee"] + pair(money(stat) if len(exp) else TBD),
            ["Tax audit fee"] + pair(money(total(tax_audit)) if len(tax_audit) else TBD),
            ["Other services (certification, limited review)"] + pair(TBD), ["Reimbursement of out-of-pocket expenses"] + pair(TBD),
            ["Total charged to the statement of profit and loss"] + pair(money(total(exp)) if len(exp) else TBD)]
    comment = "Source: expense ledgers with 'audit' in the name."
    if len(payable) and not total(exp):
        comment = (f"Audit fee payable of {u.fmt(total(payable))} is outstanding at the year end, but no audit fee is charged to "
                   "profit and loss. Confirm the charge for the year; the payment to auditors is disclosed under other expenses.")
    out.append(Disclosure("D1", "Payment to auditors", "Schedule III, Division I (other expenses); Sec 143", ["Particulars", "Current year", "Previous year"],
                          rows, comment, [4, 2, 2]))

    # ---- D2 managerial remuneration
    rem = _ledgers(m, r"director.*remuneration|remuneration.*director|managing director|whole.?time|managerial", ["EXP."])
    pbt = pl["pbt"]
    limit = 0.11 * pbt if pbt > 0 else 0
    rows = [["Remuneration to directors booked in the year"] + pair(money(total(rem)) if len(rem) else TBD),
            ["Net profit before tax (approximation of net profit under Sec 198)"] + pair(money(pbt)),
            ["11% of that profit (overall ceiling, Sec 197(1))"] + pair(money(limit)),
            ["Booked remuneration within the ceiling?"] + pair(
                ("Yes" if total(rem) <= limit else "No: exceeds the ceiling") if len(rem) and pbt > 0 else "Cannot be tested")]
    out.append(Disclosure("D2", "Managerial remuneration (Sec 197)", "Companies Act 2013, Sec 197 and Schedule V",
                          ["Particulars", "Current year", "Previous year"], rows,
                          "The ceiling applies to a public company; a private company is outside Sec 197. Sec 198 adjusts profit in ways Tally "
                          "does not hold, so the ceiling shown is indicative. Company type is not in the books. Remuneration to each director "
                          "and KMP is also a related-party disclosure (D3).", [4, 2, 2]))

    # ---- D3 related parties (AS 18)
    rel = m.mapping[m.mapping["ledger"].str.contains(RELATED) & (m.mapping["closing"].abs() > 0.5)]
    rows = []
    for r in rel.itertuples(index=False):
        what = "Remuneration" if r.line.startswith("EXP.") else ("Loan received" if r.closing < 0 and r.line.startswith(("NCL", "CL.")) else
                                                                  "Loan or advance given" if r.closing > 0 and r.line.startswith(("NCA", "CA.")) else "Balance")
        prev = NOT_LOADED if r.line.startswith("EXP.") else money(r.opening)      # a balance has an opening figure; a year's expense does not
        rows.append([r.ledger, "Director / KMP / related party (from the ledger name)", what, money(r.closing), prev])
    rows.append([TBD, "Holding, subsidiary, associate, relatives, enterprises under common control", TBD, TBD, TBD])
    out.append(Disclosure("D3", "Related-party disclosures (AS 18)", "AS 18; Companies Act 2013, Sec 188",
                          ["Name", "Relationship", "Nature", "Current year", "Previous year"], rows,
                          "Rows above come from ledger names that suggest a related party and the balance shown in Tally; the relationship "
                          "has to be confirmed. AS 18 also needs transactions in the year and balances outstanding for each party, which only "
                          "the party-wise ledgers can supply. Transactions with related parties not named in a ledger are not visible.",
                          [3, 3.2, 1.8, 1.6, 1.6]))

    # ---- D4 earnings per share (AS 20)
    out.append(Disclosure("D4", "Earnings per share (AS 20)", "AS 20",
                          ["Particulars", "Current year", "Previous year"],
                          [["Profit after tax available to equity shareholders"] + pair(money(m.profit)),
                           ["Weighted average number of equity shares"] + pair(TBD), ["Nominal value per share"] + pair(TBD),
                           ["Basic and diluted earnings per share (Rs)"] + pair("[Profit after tax / weighted average shares]")],
                          f"Paid-up share capital is {u.fmt(fig['share_capital'])}; the number of shares is not held in Tally.", [4, 2, 2]))

    # ---- D5 CSR applicability (Sec 135)
    nw, turnover = fig["equity"], pl["revenue"]
    met = [nw >= CSR_RULE["net_worth"], turnover >= CSR_RULE["turnover"], pbt >= CSR_RULE["profit"]]
    csr = _ledgers(m, r"\bcsr\b|corporate social", ["EXP."])
    pnw = fprev["equity"]
    rows = [["Net worth of Rs 500 crore or more", money(nw), "Yes" if met[0] else "No", money(pnw), "Yes" if pnw >= CSR_RULE["net_worth"] else "No"],
            ["Turnover of Rs 1,000 crore or more", money(turnover), "Yes" if met[1] else "No", NOT_LOADED, "-"],
            ["Net profit (before tax, approximation) of Rs 5 crore or more", money(pbt), "Yes" if met[2] else "No", NOT_LOADED, "-"],
            ["CSR expenditure booked in the year", money(total(csr)) if len(csr) else "No CSR ledger found", "", NOT_LOADED, ""]]
    out.append(Disclosure("D5", "Corporate social responsibility (Sec 135)", "Companies Act 2013, Sec 135; CSR Rules 2014",
                          ["Threshold", "Current year", "Met, current year", "Previous year", "Met, previous year"], rows,
                          ("None of the three thresholds is met on current-year figures, so CSR does not appear to apply."
                           if not any(met) else "At least one threshold is met: constitute the CSR committee, compute 2% of average net profit "
                           "of the three preceding years and disclose the spend and any shortfall.") +
                          " The test is made on the immediately preceding financial year's figures, which is the previous-year column; only its "
                          "net worth can be taken from the books (the opening balances), because its profit and loss was not loaded.", [4, 2, 1, 2, 1]))

    # ---- D6 contingent liabilities and commitments (AS 29)
    items = ["Claims against the company not acknowledged as debt", "Guarantees given (including by banks on the company's behalf)",
             "Bills discounted and not matured", "Disputed statutory dues: income tax, GST, other",
             "Other money for which the company is contingently liable", "Estimated capital commitments (net of advances)", "Other commitments"]
    out.append(Disclosure("D6", "Contingent liabilities and commitments (AS 29)", "AS 29; Schedule III, Division I",
                          ["Particulars", "Current year", "Previous year"], [[i, TBD, TBD] for i in items],
                          "Tally does not record contingent items. If there are none, management should say so; the tool does not assume it.",
                          [4, 2, 2]))

    # ---- D7 MSME (Sec 22 MSMED Act)
    rows = [["Total trade payables per the books", money(fig["tp"]), money(fprev["tp"])],
            ["Principal amount remaining unpaid to micro and small enterprises at the year end", TBD, TBD],
            ["Interest due and remaining unpaid on that principal", TBD, TBD],
            ["Interest paid under Sec 16, with payments made beyond the appointed day", TBD, TBD],
            ["Interest due and payable for delay in payment (without the interest specified)", TBD, TBD],
            ["Interest accrued and remaining unpaid at the year end", TBD, TBD],
            ["Further interest remaining due until the actual payment", TBD, TBD]]
    out.append(Disclosure("D7", "Dues to micro and small enterprises", "MSMED Act 2006, Sec 22; Schedule III, Division I",
                          ["Particulars", "Current year", "Previous year"], rows,
                          "Needs each supplier's MSME registration (Udyam) and the payment dates. The Day Book audit flags payments to suppliers "
                          "whose narration mentions MSME.", [5, 2, 2]))

    # ---- D8 trade receivables ageing, D9 trade payables ageing
    tr, ptr, tp = fig["tr"], fprev["tr"], fig["tp"]
    cur_lab, prev_lab = f"As at {dmy(m.as_at)}", f"As at {dmy(m.prev_as_at)}"

    def aged(labels, width, cur_total, prev_total):
        blank = [""] * (width - 2)
        rows = [[cur_lab] + [""] * (width - 1)] + [[x] + blank + [""] for x in labels]
        rows.append(["Total per the trial balance"] + blank + [money(cur_total)])
        rows.append([prev_lab] + [""] * (width - 1))
        rows += [[x] + blank + [""] for x in labels]
        rows.append(["Total per the opening balances"] + blank + [money(prev_total)])
        return rows

    out.append(Disclosure("D8", "Trade receivables ageing schedule", "Schedule III, Division I, Note on trade receivables",
                          ["Particulars", "Not due", "Under 6 months", "6 months to 1 year", "1 to 2 years", "2 to 3 years", "Over 3 years", "Total"],
                          aged(["Undisputed, considered good", "Undisputed, credit impaired", "Disputed, considered good", "Disputed, credit impaired"],
                               8, tr, ptr),
                          "Shown for both years as Schedule III requires. Ageing runs from the due date of payment, or the date of the transaction "
                          "where no due date is set. The totals agree to the balance sheet; the buckets need Tally's bill-wise outstanding ageing "
                          "(Receivables), and the previous year's buckets need the previous year's bills.", [3.2, 1, 1.2, 1.3, 1, 1, 1.1, 1.3]))
    out.append(Disclosure("D9", "Trade payables ageing schedule", "Schedule III, Division I, Note on trade payables",
                          ["Particulars", "Not due", "Under 1 year", "1 to 2 years", "2 to 3 years", "Over 3 years", "Total"],
                          aged(["MSME", "Others", "Disputed dues, MSME", "Disputed dues, others"], 7, tp, fprev["tp"]),
                          "Shown for both years as Schedule III requires. Ageing runs from the due date of payment; the buckets need Tally's "
                          "bill-wise outstanding ageing (Payables).", [3.2, 1, 1.2, 1.2, 1.2, 1.2, 1.3]))

    # ---- D10 additional regulatory information
    land = _ledgers(m, r"\bland\b|building|freehold|premises", ["NCA.PPE"], r"rent|lease")
    reval = _ledgers(m, r"revaluation")
    cwip = _ledgers(m, r"work.in.progress|cwip|capital wip", None)
    borrow = m.mapping[m.mapping["line"].isin(["NCL.LTB", "CL.STB"]) & (m.mapping["closing"].abs() > 0.5)]
    related_loans_out = rel[(rel["closing"] > 0.5) & rel["line"].str.startswith(("NCA", "CA."))]
    crypto = _ledgers(m, r"crypto|bitcoin|virtual currency")
    n_parties = len(_ledgers(m, None, ["CA.TR", "CL.TP"]))
    premium = _ledgers(m, r"securities premium|share premium")
    dash = lambda cond, yes, no: yes if cond else no          # noqa: E731
    rows = [
        ["Title deeds of immovable property not held in the company's name", "Sch III (Asset side), PPE",
         dash(len(land), f"Ledger(s) that look like land or building: {', '.join(land['ledger'])}", "No land or building ledger found (property may be rented)"), CONFIRM],
        ["Revaluation of property, plant and equipment or intangible assets", "Sch III, additional regulatory information",
         dash(len(reval), f"Revaluation ledger found: {', '.join(reval['ledger'])}", "No revaluation ledger found"), CONFIRM],
        ["Loans or advances to promoters, directors, KMP and related parties", "Sch III, additional regulatory information",
         dash(len(related_loans_out), f"Found: {', '.join(related_loans_out['ledger'])}", "None identified from ledger names"), CONFIRM],
        ["Capital work-in-progress: ageing and projects overdue or over cost", "Sch III, additional regulatory information",
         dash(len(cwip), f"Ledger found: {', '.join(cwip['ledger'])}", "No capital work-in-progress ledger found"), CONFIRM],
        ["Intangible assets under development: ageing and completion schedule", "Sch III, additional regulatory information",
         dash(fig["intang"], f"Intangible assets of {money(fig['intang'])} in the books", "No intangible assets in the books"), CONFIRM],
        ["Proceedings for benami property under the Prohibition of Benami Property Transactions Act 1988", "Sch III, additional regulatory information",
         "Not visible in the books", CONFIRM],
        ["Borrowings from banks or financial institutions on the security of current assets: quarterly returns agree with the books", "GN 8.9.7",
         dash(len(borrow), f"Borrowings of {money(total(borrow))} in the books ({', '.join(borrow['ledger'])}); security is not recorded in Tally",
              "No borrowings in the books"), CONFIRM],
        ["Wilful defaulter declared by a bank, financial institution or other lender", "Sch III, additional regulatory information",
         dash(len(borrow), "Lenders exist; the status is not in the books", "No borrowings in the books"), CONFIRM],
        ["Transactions with companies struck off under Sec 248 of the Companies Act", "Sch III, additional regulatory information",
         f"{n_parties} customer and supplier ledgers to be checked against the MCA list", CONFIRM],
        ["Registration of charges or satisfaction of charges with the Registrar of Companies", "Sch III, additional regulatory information",
         dash(len(borrow), "Charges on secured borrowings to be matched with MCA records", "No borrowings in the books"), CONFIRM],
        ["Compliance with the number of layers of companies", "GN 8.9.11", "Group structure is not in the books", CONFIRM],
        ["Compliance with an approved scheme of arrangement (Sec 230 to 237)", "GN 8.9.13", "Not visible in the books", CONFIRM],
        ["Utilisation of borrowed funds and share premium: funds advanced or received through intermediaries", "Sch III, additional regulatory information",
         dash(len(borrow) or len(premium), f"Borrowings {money(total(borrow))}" + (f"; share premium ledger found" if len(premium) else ""), "No borrowings or share premium in the books"), CONFIRM],
        ["Undisclosed income surrendered or disclosed in tax assessments", "Sch III, additional regulatory information", "Not visible in the books", CONFIRM],
        ["Corporate social responsibility: amount required to be spent, spent, and shortfall", "Sec 135; Sch III",
         "See D5: " + ("not applicable on the thresholds" if not any(met) else "applicable on at least one threshold"), CONFIRM],
        ["Trade or investment in crypto currency or virtual currency", "Sch III, additional regulatory information",
         dash(len(crypto), f"Ledger found: {', '.join(crypto['ledger'])}", "No such ledger found"), CONFIRM],
        ["Analytical ratios, with reasons for a change of more than 25%", "GN 8.9.12; Annexure B",
         f"Computed from the books: Note {ratio_no}" if ratio_no else "Computed from the books", "Explain each flagged ratio"],
    ]
    out.append(Disclosure("D10", "Additional regulatory information", "Schedule III, Division I, General Instructions; ICAI Guidance Note (Revised 2022) para 8.9",
                          ["Disclosure required", "Reference", "What the books show", "Management"], rows,
                          "A disclosure is made only where there is something to report; where the books show nothing, the statement 'Nil' or "
                          "'complied' is a declaration only management can give, so it is left as [Management to confirm].", [4.2, 2, 3.6, 1.8]))

    # ---- D11 other statutory matters the books point to
    dirloan = _ledgers(m, r"director|promoter", ["NCL.", "CL."])
    fx = _ledgers(m, r"import|export|foreign|forex|exchange (?:gain|loss)")
    gratuity = _ledgers(m, r"gratuity|leave encash|provident|\bpf\b|\besi\b", None)
    rows = [
        ["Loans received from directors or their relatives", "Companies (Acceptance of Deposits) Rules 2014, Rule 2(1)(c)(viii)",
         dash(len(dirloan), f"{', '.join(dirloan['ledger'])}: {money(total(dirloan))} (previous year {money(total(dirloan, 'opening'))})", "None identified"),
         "Written declaration from the director that the amount is not borrowed from others; disclose in the notes"
         if len(dirloan) else CONFIRM],
        ["Value of imports (CIF), expenditure and earnings in foreign currency", "Companies (Accounts) Rules 2014, Rule 8(3) and Sch III (Gen. Instr.)",
         dash(len(fx), f"Foreign-currency ledgers: {', '.join(fx['ledger'])}", "No foreign-currency ledger found"), TBD],
        ["Employee benefits: gratuity, leave encashment, provident fund and ESI", "AS 15",
         dash(len(gratuity), f"Ledgers found: {', '.join(gratuity['ledger'])}", "No gratuity, leave or provident fund ledger found; the liability may be unrecorded"),
         "Actuarial valuation or a management estimate of the gratuity liability"],
        ["Dividend proposed or declared, and transfer to reserves", "Schedule III, Division I (Reserves and surplus)", "Not in the books", TBD],
        ["Statutory dues (PF, ESI, TDS, GST) payable, and any overdue at the year end", "Various",
         dash(len(_ledgers(m, r"tds payable|gst|pf|esi", ["CL."])), "Statutory dues payable appear under other current liabilities (Note on other current liabilities)",
              "No statutory dues ledger found"), "Confirm none is overdue at the year end"],
    ]
    out.append(Disclosure("D11", "Other statutory disclosures the books point to", "Companies Act 2013 and Rules; AS 15",
                          ["Matter", "Reference", "What the books show", "Needed"], rows,
                          "These are matters visible from ledger names. The list is not exhaustive and does not replace the Companies Act checklist.",
                          [3.6, 2.8, 3.2, 2.6]))
    return out
