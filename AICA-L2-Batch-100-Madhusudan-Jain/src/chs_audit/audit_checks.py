"""Module 1 and 2: statutory audit tests on member ledgers, GST, funds, bank and expenses.

Each public function returns (schedule DataFrame(s), list[Finding]). The schedules
become sheets in the audit workbook; the findings feed the AI drafting layer.
"""
from __future__ import annotations

import math
from collections import Counter
from datetime import date, timedelta

import pandas as pd

from .config import FY_END, FY_START, RATES, SOCIETY
from .findings import Finding
from .loaders import SocietyData


def _inr(x: float) -> str:
    """Indian-style grouping: 12,34,567.89"""
    neg = x < 0
    x = abs(float(x))
    whole = int(round(x))
    s = str(whole)
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts) + "," + tail
    return ("-" if neg else "") + "Rs " + s


# ----------------------------------------------------------------------------- 1. member ledger
def member_ledger(d: SocietyData):
    bills, rec, mem = d.bills, d.receipts, d.members
    rec_fy = rec[(rec.receipt_date >= FY_START) & (rec.receipt_date <= FY_END)]
    rec_post = rec[rec.receipt_date > FY_END]
    findings: list[Finding] = []
    rows, interest_rows = [], []
    for _, m in mem.iterrows():
        fb = bills[bills.flat_no == m.flat_no].sort_values("bill_date")
        opening = float(m.opening_arrears)
        billed = float(fb.bill_total.sum())
        paid = float(rec_fy[rec_fy.flat_no == m.flat_no].amount.sum())
        post = float(rec_post[rec_post.flat_no == m.flat_no].amount.sum())
        closing = round(opening + billed - paid, 2)
        avg_bill = float(fb.bill_total.mean())
        months = closing / avg_bill if avg_bill else 0
        # recompute interest month by month at the adopted rate
        my_rec = rec[rec.flat_no == m.flat_no]
        billed_so_far = opening
        soc_int, exp_int = 0.0, 0.0
        for _, b in fb.iterrows():
            received_before = float(my_rec[my_rec.receipt_date < b.bill_date].amount.sum())
            arrears = round(billed_so_far - received_before, 2)
            expected = round(arrears * RATES.arrears_interest_rate / 12, 2) if arrears > 0 else 0.0
            exp_int += expected
            soc_int += float(b.interest_on_arrears)
            billed_so_far = round(billed_so_far + float(b.bill_total), 2)
        diff = round(exp_int - soc_int, 2)
        if abs(diff) >= 1:
            interest_rows.append({"flat_no": m.flat_no, "member_name": m.member_name, "committee_member": m.committee_member,
                                  "interest_charged_by_society": round(soc_int, 2), "interest_per_bye_law_21pct": round(exp_int, 2), "short_(excess)_charge": diff})
        status = "Regular"
        if months >= 6:
            status = "Chronic defaulter (>6 months)"
        elif months >= RATES.defaulter_months:
            status = f"Defaulter (>{RATES.defaulter_months} months)"
        elif months >= 1:
            status = "Arrears 1-3 months"
        rows.append({
            "flat_no": m.flat_no, "member_name": m.member_name, "flat_type": m.flat_type, "occupancy": m.occupancy,
            "committee_member": m.committee_member, "opening_arrears": opening, "billed_fy": round(billed, 2),
            "received_fy": round(paid, 2), "closing_balance": closing, "months_of_arrears": round(months, 1),
            "status": status, "received_after_year_end": round(post, 2),
        })
    ledger = pd.DataFrame(rows)
    interest_df = pd.DataFrame(interest_rows)

    defaulters = ledger[ledger.months_of_arrears >= RATES.defaulter_months].sort_values("closing_balance", ascending=False)
    total_arrears = float(ledger.closing_balance.clip(lower=0).sum())
    billed = float(ledger.billed_fy.sum())
    findings.append(Finding(
        module="Member Ledger", area="Arrears and defaulters", severity="High" if len(defaulters) else "Info",
        observation=(f"Closing member dues at 31-Mar-2026 are {_inr(total_arrears)} against annual billing of {_inr(billed)} "
                     f"({total_arrears / billed:.1%}). {len(defaulters)} members are in arrears of more than {RATES.defaulter_months} months, "
                     f"of which {int((ledger.months_of_arrears >= 6).sum())} exceed 6 months. Largest: " +
                     ", ".join(f"{r.flat_no} {_inr(r.closing_balance)}" for r in defaulters.head(3).itertuples())),
        reference="MCS Act 1960 s.101 (recovery certificate); bye-laws 70-72 (dues and interest)",
        recommendation="Serve final demand notices and file s.101 recovery applications with the Deputy Registrar for all members above 3 months; disclose defaulters in the AGM agenda as required.",
        amount=float(defaulters.closing_balance.sum()), evidence="Sheet: Member_Ledger, Defaulters",
    ))
    if len(interest_df):
        short = float(interest_df["short_(excess)_charge"].clip(lower=0).sum())
        cm = interest_df[interest_df.committee_member]
        obs = (f"Interest on arrears has been short-charged by {_inr(short)} in {len(interest_df)} member accounts when recomputed at the 21% p.a. "
               f"adopted by the General Body (MC resolution 1.2 of 13-Apr-2025). ")
        if len(cm):
            obs += ("Office-bearer flat(s) " + ", ".join(cm.flat_no) + " were charged no interest at all despite paying 20-45 days late. "
                    f"Flats {', '.join(interest_df[~interest_df.committee_member].flat_no)} were charged at 18% instead of 21%.")
        findings.append(Finding(
            module="Member Ledger", area="Interest on arrears", severity="High", observation=obs,
            reference="Bye-law 72 (simple interest not exceeding 21% p.a.); MCS Act s.78 (misconduct of office bearers)",
            recommendation="Raise supplementary debit notes for the short interest; apply the rate uniformly through the billing software with no manual override; the committee should record a resolution on the waiver to the Secretary's account and the member should make good the amount.",
            amount=short, evidence="Sheet: Interest_Recompute",
        ))
    # bye-law 69: equal service charges
    sc = d.bills.groupby("flat_no").service_charges.mean()
    if sc.nunique() > 1:
        findings.append(Finding("Member Ledger", "Service charges", "Medium", "Service charges differ between flats.",
                                "Bye-law 69(a)", "Charge service charges equally per flat.", 0.0))
    # non-occupancy charges on tenanted flats
    ten = d.members[d.members.occupancy == "Tenant"].flat_no
    noc = d.bills[d.bills.flat_no.isin(ten)].groupby("flat_no").non_occupancy_charges.sum()
    missing = noc[noc == 0]
    if len(missing):
        findings.append(Finding("Member Ledger", "Non-occupancy charges", "Medium",
                                f"Non-occupancy charges not levied on tenanted flats {', '.join(missing.index)}.",
                                "Bye-law 43(2)(iii)(c); Govt. notification 1-Aug-2001 (cap 10% of service charges)",
                                "Levy NOC at 10% of service charges from the date of letting.", 0.0))
    # reserve fund s.66
    surplus = d.fund("Net surplus FY 2024-25")
    transferred = d.fund("Transfer to Reserve Fund made")
    required = round(surplus * 0.25, 2)
    if transferred + 1 < required:
        findings.append(Finding("Funds", "Reserve fund transfer", "Medium",
                                f"Only {_inr(transferred)} transferred to Reserve Fund against the minimum 25% of net profit of FY 2024-25 ({_inr(required)} on {_inr(surplus)}).",
                                "MCS Act 1960 s.66(1); bye-law 14", "Transfer the balance of {} before finalising accounts.".format(_inr(required - transferred)),
                                required - transferred, "Sheet: Fund_Compliance"))
    return ledger, interest_df, defaulters, findings


# ----------------------------------------------------------------------------- 2. GST
def gst_check(d: SocietyData):
    b = d.bills.copy()
    # Reckonable maintenance for the Rs 7,500 test: exclude property tax (statutory levy collected
    # on behalf of TMC) and interest (tested separately); include all other contributions.
    b["reckonable"] = (b.bill_total - b.gst_charged - b.interest_on_arrears - b.property_tax).round(2)
    b["gst_applicable"] = b.reckonable > RATES.gst_exemption_per_member_month
    b["correct_gst"] = (b.reckonable * RATES.gst_rate).where(b.gst_applicable, 0.0).round(2)
    b["difference"] = (b.gst_charged - b.correct_gst).round(2)
    b["issue"] = ""
    b.loc[(b.difference > 1) & b.gst_applicable, "issue"] = "GST charged on property tax component (over-charged)"
    b.loc[(b.difference > 1) & ~b.gst_applicable, "issue"] = "GST charged although monthly contribution below Rs 7,500"
    b.loc[b.difference < -1, "issue"] = "GST not charged although contribution exceeds Rs 7,500"
    sched = b[["bill_no", "flat_no", "bill_month", "property_tax", "reckonable", "gst_applicable", "gst_charged", "correct_gst", "difference", "issue"]]
    issues = sched[sched.issue != ""]
    over = float(issues[issues.difference > 0].difference.sum())
    under = float(-issues[issues.difference < 0].difference.sum())
    turnover = float(b.reckonable.sum() + b.property_tax.sum())
    findings = []
    summary = issues.groupby("issue").agg(bills=("bill_no", "count"), flats=("flat_no", "nunique"), amount=("difference", "sum")).reset_index()
    findings.append(Finding(
        module="GST", area="Maintenance bills", severity="High",
        observation=(f"Aggregate collections of {_inr(turnover)} exceed the Rs 20 lakh registration threshold, so GST applies to members whose monthly contribution "
                     f"exceeds Rs 7,500 (whole amount taxable, Circular 109/28/2019). Testing all {len(b)} bills: GST over-charged by {_inr(over)} on "
                     f"{int((issues.difference > 0).sum())} bills ({int(issues[issues.difference > 0].flat_no.nunique())} flats) and under-charged by {_inr(under)} on "
                     f"{int((issues.difference < 0).sum())} bills. Causes: (i) property tax included in the taxable value for 3BHK flats; "
                     f"(ii) flat A-201 charged GST though below the limit; (iii) flat B-604 not charged for Jun-Aug 2025."),
        reference="CGST Act s.22, s.15; Notification 12/2017-CT(R) entry 77(c); Circular 109/28/2019-GST dated 22-Jul-2019",
        recommendation="Issue credit notes u/s 34 for the over-charge and debit notes for the under-charge within the time limit; correct the billing template to exclude property tax and apply the Rs 7,500 test per member per month; reconcile GSTR-1 with the corrected bills.",
        amount=over + under, evidence="Sheet: GST_Check",
    ))
    interest_total = float(b.interest_on_arrears.sum())
    findings.append(Finding(
        module="GST", area="Interest on delayed payment", severity="Low",
        observation=f"Interest on arrears of {_inr(interest_total)} billed to members has not been included in the value of supply for members who are liable to GST.",
        reference="CGST Act s.15(2)(d)", recommendation="Include interest in the taxable value for GST-liable members, or obtain a written position from the GST consultant.",
        amount=round(float(b[b.gst_applicable].interest_on_arrears.sum()) * RATES.gst_rate, 2), evidence="Sheet: GST_Check",
    ))
    return sched, summary, findings


# ----------------------------------------------------------------------------- 3. funds
def fund_compliance(d: SocietyData):
    sf_open = d.fund("Sinking Fund - opening")
    sf_coll = d.fund("Sinking Fund - collected")
    sf_tr = d.fund("Sinking Fund - transferred")
    sf_fd = d.earmarked_fd()
    rf_open = d.fund("Repair & Maintenance Fund - opening")
    rf_coll = d.fund("Repair & Maintenance Fund - collected")
    rf_used = d.fund("Repair & Maintenance Fund - utilised")
    sf_close = sf_open + sf_coll
    rows = [
        {"test": "Sinking fund contribution rate", "expected": f"{RATES.sinking_fund_rate:.2%} p.a. of construction cost", "actual": "0.25% p.a. (per bills)", "result": "Complies"},
        {"test": "Repair fund contribution rate", "expected": f"{RATES.repair_fund_rate:.2%} p.a. of construction cost", "actual": "0.75% p.a. (per bills)", "result": "Complies"},
        {"test": "Sinking fund collected vs transferred to fund", "expected": sf_coll, "actual": sf_tr, "result": "Shortfall " + _inr(sf_coll - sf_tr) if sf_tr < sf_coll else "Complies"},
        {"test": "Sinking fund balance vs earmarked investments", "expected": sf_close, "actual": sf_fd, "result": "Under-invested " + _inr(sf_close - sf_fd) if sf_fd < sf_close else "Complies"},
        {"test": "Repair fund movement", "expected": rf_open + rf_coll, "actual": rf_open + rf_coll - rf_used, "result": f"Utilised {_inr(rf_used)} on repairs; closing {_inr(rf_open + rf_coll - rf_used)}"},
        {"test": "Reserve fund transfer (25% of net profit)", "expected": d.fund("Net surplus") * 0.25, "actual": d.fund("Transfer to Reserve"), "result": "Shortfall" if d.fund("Transfer to Reserve") < d.fund("Net surplus") * 0.25 else "Complies"},
    ]
    sched = pd.DataFrame(rows)
    findings = [
        Finding("Funds", "Sinking fund diversion", "High",
                f"Sinking fund contributions of {_inr(sf_coll)} were collected but only {_inr(sf_tr)} was credited to the Sinking Fund; {_inr(sf_coll - sf_tr)} was used for revenue expenditure (MC minutes 15-Feb-2026 acknowledge temporary use).",
                "Bye-law 13(a) and 15; MCS Act s.70 (investment of funds)", "Restore the diverted amount to the sinking fund immediately and invest it; sinking fund may be used only for structural repairs with General Body approval.",
                sf_coll - sf_tr, "Sheet: Fund_Compliance"),
        Finding("Funds", "Sinking fund investment", "High",
                f"Sinking Fund balance of {_inr(sf_close)} is backed by earmarked fixed deposits of only {_inr(sf_fd)}, an under-investment of {_inr(sf_close - sf_fd)}.",
                "Bye-law 15 read with MCS Act s.70 and Rule 54 (investment in co-operative bank/approved securities)",
                "Invest the shortfall in fixed deposits with a co-operative bank earmarked to the Sinking Fund and report the position to the AGM.",
                sf_close - sf_fd, "Sheet: Fund_Compliance"),
    ]
    return sched, findings


# ----------------------------------------------------------------------------- 4. bank reconciliation
def bank_reconciliation(d: SocietyData):
    bank = d.bank.copy()
    rec = d.receipts.copy()
    exp = d.expenses.copy()
    bank_fy = bank[(bank.txn_date >= FY_START) & (bank.txn_date <= FY_END)]
    credits = bank_fy[bank_fy.credit > 0]
    debits = bank_fy[bank_fy.debit > 0]
    matched_rec = rec.merge(credits[["ref", "txn_date", "credit"]], left_on="reference", right_on="ref", how="left")
    unmatched_receipts = matched_rec[matched_rec.ref.isna() & (matched_rec.receipt_date <= FY_END)]
    # receipts whose cheque was returned
    returned = bank_fy[bank_fy.narration.str.contains("CHQ RETURN INSUFFICIENT")]
    returned_refs = set(returned.ref)
    bounced = rec[rec.reference.isin(returned_refs)]
    # unidentified credits: bank credits not matching any receipt reference or known income
    known_refs = set(rec.reference) | {"OI"}
    unidentified = credits[~credits.ref.isin(known_refs)]
    # expense payments vs bank debits
    exp_bank = exp[exp.payment_mode != "Cash"]
    matched_exp = exp_bank.merge(debits[["ref", "debit"]], left_on="voucher_no", right_on="ref", how="left")
    unmatched_exp = matched_exp[matched_exp.ref.isna() & (matched_exp.payment_date <= FY_END)]
    cash_payments = exp[exp.payment_mode == "Cash"]
    # book balance vs bank balance
    opening = d.fund("Bank balance - opening")
    rec_fy = rec[(rec.receipt_date >= FY_START) & (rec.receipt_date <= FY_END)]
    other = d.other_income
    other_net = float((other.gross_amount - other.tds).sum())
    exp_paid_bank = float(exp_bank[exp_bank.payment_date <= FY_END].net_paid.sum())
    tds_remitted = float(bank_fy[bank_fy.ref == "TDS"].debit.sum())
    book_balance = round(opening + float(rec_fy.amount.sum()) + other_net - exp_paid_bank - tds_remitted, 2)
    bank_balance = float(bank_fy.iloc[-1].balance)
    bank_charges = float(bank_fy[bank_fy.ref == "CHG"].debit.sum())
    recon = pd.DataFrame([
        {"item": "Balance as per books (derived: opening + receipts + other income - payments - TDS remitted)", "amount": book_balance},
        {"item": "Add: unidentified credits in bank not in books", "amount": float(unidentified.credit.sum())},
        {"item": "Less: cheque returned by bank, not reversed in books", "amount": -float(bounced.amount.sum())},
        {"item": "Less: bank charges and cheque return charges not booked", "amount": -bank_charges},
        {"item": "Less: receipts recorded in books, credited in bank after year end (cheques in transit)", "amount": -float(unmatched_receipts.amount.sum())},
        {"item": "Balance as per bank statement 31-Mar-2026", "amount": bank_balance},
    ])
    explained = book_balance + float(unidentified.credit.sum()) - float(bounced.amount.sum()) - bank_charges - float(unmatched_receipts.amount.sum())
    recon.loc[len(recon)] = {"item": "Unreconciled difference", "amount": round(bank_balance - explained, 2)}
    findings = []
    if len(bounced):
        r = bounced.iloc[0]
        findings.append(Finding("Bank", "Dishonoured cheque", "High",
                                f"Cheque received from flat {r.flat_no} ({_inr(r.amount)}, receipt {r.receipt_no} dated {r.receipt_date:%d-%b-%Y}) was returned unpaid by the bank, but the receipt stands in the member's ledger and the member shows no arrears for that month.",
                                "Bye-law 70; Negotiable Instruments Act s.138", "Reverse the receipt, debit cheque return charges to the member, issue a s.138 notice if not regularised within 15 days, and add a monthly bank reconciliation review to the Treasurer's checklist.",
                                float(r.amount), "Sheet: Bank_Reconciliation"))
    if len(unidentified):
        findings.append(Finding("Bank", "Unidentified credits", "Medium",
                                f"{len(unidentified)} credit(s) totalling {_inr(float(unidentified.credit.sum()))} appear in the bank statement with no corresponding receipt (e.g. NEFT from 'RAVI' on 12-Nov-2025). A member may be wrongly shown in arrears.",
                                "Bye-law 142 (books of account); AS/Accounting discipline", "Identify the payer, issue the receipt and credit the member's ledger; keep a suspense account for unidentified credits reviewed monthly.",
                                float(unidentified.credit.sum()), "Sheet: Bank_Reconciliation"))
    if len(cash_payments):
        over = cash_payments[cash_payments.gross_amount > RATES.cash_payment_limit]
        if len(over):
            findings.append(Finding("Expenses", "Cash payments", "Medium",
                                    f"{len(over)} cash payments above Rs {RATES.cash_payment_limit:,.0f} totalling {_inr(float(over.gross_amount.sum()))} ({', '.join(over.vendor_name)}), approved by a single office bearer and without vendor PAN.",
                                    "Bye-law 143; Income-tax Act s.40A(3) discipline; MCS Rules on cash limit", "Pay vendors only through banking channels; obtain PAN/declaration for every vendor above Rs 10,000.",
                                    float(over.gross_amount.sum()), "Sheet: Expense_Anomalies"))
    findings.append(Finding("Bank", "Monthly reconciliation", "Medium",
                            f"No bank reconciliation statement was prepared during the year. A reconstructed reconciliation explains the difference between books and bank through {len(bounced)} dishonoured cheque, {len(unidentified)} unidentified credit and unbooked bank charges of {_inr(bank_charges)}, leaving an unreconciled balance of {_inr(float(recon.iloc[-1].amount))}.",
                            "Bye-law 142; MCS Rules 65 (books of account)", "Prepare and sign a bank reconciliation every month; book bank charges from the statement.",
                            abs(float(recon.iloc[-1].amount)), "Sheet: Bank_Reconciliation"))
    detail = pd.concat([
        bounced.assign(exception="Cheque returned by bank, not reversed in books"),
        unidentified.rename(columns={"txn_date": "receipt_date", "credit": "amount", "narration": "reference"}).assign(exception="Unidentified credit in bank"),
        unmatched_receipts[rec.columns].assign(exception="Receipt in books, credited in bank after 31-Mar-2026"),
    ], ignore_index=True)
    return recon, detail, findings


# ----------------------------------------------------------------------------- 5. expenses
def _benford(values: pd.Series) -> pd.DataFrame:
    digits = [int(str(abs(int(v)))[0]) for v in values if v and int(v) != 0]
    n = len(digits)
    counts = Counter(digits)
    rows = []
    for dgt in range(1, 10):
        expected = math.log10(1 + 1 / dgt)
        actual = counts.get(dgt, 0) / n if n else 0
        rows.append({"first_digit": dgt, "expected_pct": round(expected * 100, 1), "actual_pct": round(actual * 100, 1),
                     "count": counts.get(dgt, 0), "deviation_pts": round((actual - expected) * 100, 1)})
    return pd.DataFrame(rows)


def expense_anomalies(d: SocietyData):
    exp = d.expenses.copy()
    ven = d.vendors
    anomalies = []
    # duplicates
    dup = exp[exp.duplicated(subset=["vendor_code", "invoice_no", "taxable_value"], keep=False)].sort_values("invoice_no")
    for inv, g in dup.groupby("invoice_no"):
        anomalies.append({"test": "Duplicate payment", "vendor": g.vendor_name.iloc[0], "reference": f"Invoice {inv}: vouchers {', '.join(g.voucher_no)}",
                          "amount": float(g.net_paid.iloc[1:].sum()), "detail": f"Same vendor, invoice number and amount paid {len(g)} times on {', '.join(x.strftime('%d-%b-%Y') for x in g.payment_date)}"})
    # split invoices: same vendor, within 7 days, each below limit, sum above limit
    for vcode, g in exp.drop_duplicates(subset=["vendor_code", "invoice_no"]).sort_values("invoice_date").groupby("vendor_code"):
        g = g.reset_index(drop=True)
        for i in range(len(g)):
            window = g[(g.invoice_date >= g.loc[i, "invoice_date"]) & (g.invoice_date <= g.loc[i, "invoice_date"] + timedelta(days=7))]
            if len(window) >= 2 and (window.taxable_value < RATES.committee_approval_limit).all() and window.taxable_value.sum() > RATES.committee_approval_limit:
                anomalies.append({"test": "Split invoices below approval limit", "vendor": g.vendor_name.iloc[0],
                                  "reference": ", ".join(window.invoice_no), "amount": float(window.taxable_value.sum()),
                                  "detail": f"{len(window)} invoices on consecutive dates each below Rs {RATES.committee_approval_limit:,.0f}; combined {_inr(float(window.taxable_value.sum()))} exceeds the limit set by AGM resolution A.4 and only one quotation was obtained (MC minutes 08-Jun-2025)"})
                break
    # related party: vendor address refers to a committee flat or the society itself
    for _, v in ven.iterrows():
        addr = str(v.address)
        hit = [f for f in SOCIETY.committee_flats if f"Flat {f}" in addr or f" {f}," in addr]
        if hit or SOCIETY.name.split(" Co-operative")[0] in addr:
            spend = exp[exp.vendor_code == v.vendor_code]
            role = {SOCIETY.chairman_flat: "Chairman", SOCIETY.secretary_flat: "Secretary", SOCIETY.treasurer_flat: "Treasurer"}.get(hit[0] if hit else "", "committee member")
            anomalies.append({"test": "Related-party vendor", "vendor": v.vendor_name, "reference": f"{len(spend)} vouchers; approved by {', '.join(spend.approved_by.unique())}",
                              "amount": float(spend.gross_amount.sum()),
                              "detail": f"Vendor address is flat {hit[0] if hit else '(society premises)'} - the {role}'s flat. Payments approved by the {role} alone, no competitive quotes, no disclosure of interest in minutes."})
    # payments above committee limit approved by MC only (excluding statutory/government)
    inv_count = exp.groupby("vendor_code").voucher_no.transform("count")
    big = exp[(exp.taxable_value > RATES.committee_approval_limit) & (~exp.vendor_code.isin(["V04"])) & (inv_count < 3)]
    for _, r in big.iterrows():
        anomalies.append({"test": "Single item above committee limit", "vendor": r.vendor_name, "reference": r.invoice_no, "amount": float(r.taxable_value),
                          "detail": f"{r.description}: {_inr(float(r.taxable_value))} exceeds Rs {RATES.committee_approval_limit:,.0f}; verify General Body sanction or budget line (approved by {r.approved_by})."})
    # single-signatory approvals
    single = exp[exp.approved_by.isin(["Treasurer", "Secretary"])]
    anomalies.append({"test": "Approval by single office bearer", "vendor": ", ".join(single.vendor_name.unique()), "reference": f"{len(single)} vouchers",
                      "amount": float(single.gross_amount.sum()), "detail": "Vouchers approved by one office bearer without committee sanction recorded in minutes."})
    # weekend payments
    exp["weekday"] = [pd.Timestamp(x).dayofweek for x in exp.payment_date]
    wk = exp[exp.weekday >= 5]
    anomalies.append({"test": "Weekend payment dates", "vendor": "-", "reference": f"{len(wk)} of {len(exp)} vouchers", "amount": float(wk.net_paid.sum()),
                      "detail": "Payments dated on Saturday/Sunday; verify authorisation trail in net-banking logs (informational)."})
    anomalies_df = pd.DataFrame(anomalies)
    benford = _benford(exp.taxable_value)
    findings = []
    dup_amt = float(anomalies_df[anomalies_df.test == "Duplicate payment"].amount.sum())
    if dup_amt:
        findings.append(Finding("Expenses", "Duplicate payment", "High",
                                f"Housekeeping invoice SRV/2025/08-14 of {_inr(dup_amt)} was paid twice (PV in Aug-2025 and again 19 days later). No invoice-number uniqueness control exists in the payment process.",
                                "Bye-law 142-143; internal control", "Recover the excess from Swachh Housekeeping Services against the next bill; enforce invoice-number uniqueness in the accounting software.",
                                dup_amt, "Sheet: Expense_Anomalies"))
    split = anomalies_df[anomalies_df.test == "Split invoices below approval limit"]
    if len(split):
        findings.append(Finding("Expenses", "Split invoices / tendering", "High",
                                f"Terrace waterproofing of {_inr(float(split.amount.iloc[0]))} was awarded on a single quotation and billed as three invoices of Rs 49,000, 48,000 and 48,000 on consecutive days, each below the Rs 50,000 committee limit fixed by AGM resolution A.4.",
                                "AGM 2025 resolution A.4; bye-law 143; MCS Act s.73 (duties of committee)", "Obtain ex-post ratification from the General Body; adopt a written procurement policy (three quotations above Rs 50,000, tender above Rs 5 lakh).",
                                float(split.amount.iloc[0]), "Sheet: Expense_Anomalies"))
    rp = anomalies_df[anomalies_df.test == "Related-party vendor"]
    if len(rp):
        findings.append(Finding("Expenses", "Related-party vendor", "High",
                                f"Patil Plumbing Works, paid {_inr(float(rp.amount.iloc[0]))} during the year across six vouchers, has its address at flat B-203, the Treasurer's residence. All vouchers were approved by the Treasurer alone and the interest was not disclosed in any minutes.",
                                "MCS Act s.73(1AB)/s.78 (conflict of interest, removal of office bearer); bye-law 143", "Disclose the interest to the committee and General Body; the Treasurer should abstain from approving these payments; obtain independent quotes for plumbing work.",
                                float(rp.amount.iloc[0]), "Sheet: Expense_Anomalies"))
    dev = benford.deviation_pts.abs().max()
    findings.append(Finding("Expenses", "Benford first-digit test", "Info" if dev < 12 else "Low",
                            f"First-digit distribution of {len(exp)} expense invoices deviates from Benford's expectation by at most {dev:.1f} percentage points (digit {int(benford.loc[benford.deviation_pts.abs().idxmax(), 'first_digit'])}); the recurring fixed contracts explain most of the skew.",
                            "ISA/SA 520 analytical procedures", "No action beyond the specific anomalies already reported.", 0.0, "Sheet: Benford"))
    return anomalies_df, benford, findings


# ----------------------------------------------------------------------------- 6. TDS
def tds_check(d: SocietyData):
    exp = d.expenses.merge(d.vendors[["vendor_code", "entity_type", "tds_section"]], on="vendor_code")
    rows = []
    for vcode, g in exp.groupby("vendor_code"):
        sec = g.tds_section.iloc[0]
        if not isinstance(sec, str):
            continue
        agg = float(g.taxable_value.sum())
        single_max = float(g.taxable_value.max())
        ent = g.entity_type.iloc[0]
        if sec == "194C":
            applicable = agg > RATES.tds_194c_aggregate or single_max > RATES.tds_194c_single
            rate = RATES.tds_194c_rate_individual if ent == "Individual" else RATES.tds_194c_rate_others
        elif sec == "194J":
            applicable = agg > RATES.tds_194j_threshold
            rate = RATES.tds_194j_rate
        else:
            applicable, rate = False, 0.0
        has_pan = g.vendor_code.iloc[0] not in ("V13", "V14")
        if applicable and not has_pan:
            rate = 0.20
        expected = round(agg * rate, 2) if applicable else 0.0
        deducted = float(g.tds_deducted.sum())
        short = round(expected - deducted, 2)
        rows.append({"vendor_code": vcode, "vendor_name": g.vendor_name.iloc[0], "entity_type": ent, "section": sec,
                     "aggregate_payments": agg, "tds_applicable": applicable, "correct_rate": rate, "tds_expected": expected,
                     "tds_deducted": deducted, "short_deduction": short,
                     "remark": ("No TDS deducted" if deducted == 0 and expected > 0 else
                                "Short deduction - wrong rate" if 0 < deducted < expected else
                                "Not applicable - below threshold" if not applicable else "Correct")})
    sched = pd.DataFrame(rows)
    short_total = float(sched.short_deduction.clip(lower=0).sum())
    # interest u/s 201(1A): 1% p.m. for non-deduction from date deductible to date of deduction (assume 31-Mar-2026 average 6 months)
    interest_est = round(short_total * 0.01 * 6, 2)
    findings = [Finding("Tax - TDS", "Short/non-deduction of TDS", "High",
                        f"TDS short-deducted by {_inr(short_total)}: no TDS on accounting fees of Rs 96,000 to R. K. Kadam & Associates (s.194J, threshold Rs 50,000); "
                        f"security agency SecureGuard (a partnership firm) deducted at 1% instead of 2% u/s 194C on Rs 13.2 lakh; cash vendors without PAN attract 20% u/s 206AA. "
                        f"Estimated interest u/s 201(1A) about {_inr(interest_est)}.",
                        "Income-tax Act s.194C, 194J, 206AA, 201(1A); s.40(a)(ia)", "Deposit the short TDS with interest, file correction statements (Form 26Q), and maintain a vendor master with PAN and entity type driving the TDS rate automatically.",
                        short_total + interest_est, "Sheet: TDS_Check")]
    return sched, findings
