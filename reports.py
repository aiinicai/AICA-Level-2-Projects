"""Payslips, statutory returns (KRA P10, NSSF, SHIF, AHL, NITA), bank file, P9A, journal."""
from __future__ import annotations

import calendar
import csv
import html
import os
from datetime import date

from config import APP_NAME

MONTHS = list(calendar.month_name)


def money(v) -> str:
    return f"{float(v or 0):,.2f}"


def full_name(e) -> str:
    return f"{e['first_name']} {e['last_name']}".strip()


def period_label(period: str) -> str:
    y, m = period.split("-")
    return f"{MONTHS[int(m)]} {y}"


def out_dir(base: str, period: str) -> str:
    path = os.path.join(base, period)
    os.makedirs(path, exist_ok=True)
    return path


def write_csv(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    return path


def due_date(period: str) -> str:
    """PAYE, NSSF, SHIF, AHL and NITA are due by the 9th of the following month."""
    y, m = map(int, period.split("-"))
    y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return date(y, m, 9).strftime("%d %b %Y")


# ---------------------------------------------------------------------------
CSS = """
body{font-family:Segoe UI,Arial,sans-serif;color:#1d2433;margin:0;background:#eef1f5}
.slip{background:#fff;width:190mm;margin:10mm auto;padding:10mm 12mm;box-sizing:border-box;
 page-break-after:always;border-top:6px solid #0b3d6e}
h1{font-size:20px;margin:0;color:#0b3d6e}.sub{color:#5a6372;font-size:12px}
.head{display:flex;justify-content:space-between;align-items:flex-start;border-bottom:1px solid #d6dbe3;padding-bottom:8px}
.title{font-size:15px;font-weight:600;text-align:right}
table{width:100%;border-collapse:collapse;font-size:12px;margin-top:8px}
td,th{padding:4px 6px;border-bottom:1px solid #edf0f4;text-align:left}
th{background:#f3f6fa;color:#0b3d6e;font-weight:600}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.info td{border:none;padding:2px 6px}.info td:first-child{color:#5a6372;width:40%}
.tot td{font-weight:600;border-top:1px solid #aab3c0}
.net{margin-top:10px;background:#0b3d6e;color:#fff;padding:10px 14px;display:flex;justify-content:space-between;font-size:16px;font-weight:600}
.foot{font-size:10px;color:#7a8291;margin-top:10px}
.warn{color:#a33}
@media print{body{background:#fff}.slip{margin:0;border-top-width:4px}}
"""


def _rows(items):
    return "".join(f"<tr><td>{html.escape(k)}</td><td class='n'>{money(v)}</td></tr>"
                   for k, v in items if v)


def payslip_html(line: dict, company: dict, ytd: dict) -> str:
    e = line["employee"]
    earnings = [("Basic Salary", line["basic"])]
    earnings += list(line["allowances"].items())
    earnings += [("Overtime", line["overtime"]), ("Bonus", line["bonus"]),
                 ("Arrears", line["arrears"]), ("Leave Pay", line["leave_pay"]),
                 ("Other Earnings", line["other_earnings"])]
    if line["absence"]:
        earnings.append(("Less: Absence", -line["absence"]))
    deds = [("PAYE", line["paye"]), ("NSSF Tier I", line["nssf_tier1"]),
            ("NSSF Tier II", line["nssf_tier2"]), ("SHIF", line["shif"]),
            ("Housing Levy", line["ahl_employee"]), ("Withholding Tax (5%)", line["wht"]),
            ("Pension (Voluntary)", line["voluntary_pension"])]
    deds += list(line["other_deductions"].items())
    tax = [("Taxable Benefits", line["taxable_benefits"]),
           ("Allowable Pension", line["pension_allowed"]),
           ("Mortgage Interest", line["mortgage_allowed"]),
           ("Post-Retirement Medical", line["prmf_allowed"]),
           ("Disability Exemption", line["disability_exempt"]),
           ("Taxable Pay", line["taxable_pay"]), ("Tax Charged", line["tax_charged"]),
           ("Personal Relief", line["personal_relief"]),
           ("Insurance Relief", line["insurance_relief"])]
    employer = [("NSSF (Employer)", line["nssf_employer"]),
                ("Housing Levy (Employer)", line["ahl_employer"]),
                ("NITA Levy", line["nita"])]
    pay_to = e["payment_mode"] or "Bank"
    if pay_to == "Bank":
        pay_to = f"{e['bank_name'] or ''} {e['bank_branch'] or ''} - {e['account_no'] or ''}"
    elif pay_to == "M-Pesa":
        pay_to = f"M-Pesa {e['phone'] or ''}"
    prorate = f" (pro-rated {line['proration']*100:.0f}%)" if line.get("proration", 1) < 1 else ""
    esc = lambda s: html.escape(str(s or ""))
    return f"""
<div class="slip">
 <div class="head">
  <div><h1>{esc(company['name'])}</h1>
   <div class="sub">{esc(company['address'])} {esc(company['phone'])} {esc(company['email'])}<br>
   KRA PIN: {esc(company['kra_pin'])}</div></div>
  <div class="title">PAYSLIP<br><span class="sub">{period_label(line['period'])}</span></div>
 </div>
 <div class="grid">
  <table class="info">
   <tr><td>Employee</td><td><b>{esc(full_name(e))}</b></td></tr>
   <tr><td>Staff No.</td><td>{esc(e['staff_no'])}</td></tr>
   <tr><td>Department</td><td>{esc(e['department'])}</td></tr>
   <tr><td>Designation</td><td>{esc(e['designation'])}</td></tr>
   <tr><td>Employment</td><td>{esc(e['employment_type'])}{prorate}</td></tr>
  </table>
  <table class="info">
   <tr><td>ID No.</td><td>{esc(e['id_no'])}</td></tr>
   <tr><td>KRA PIN</td><td>{esc(e['kra_pin'])}</td></tr>
   <tr><td>NSSF No.</td><td>{esc(e['nssf_no'])}</td></tr>
   <tr><td>SHIF No.</td><td>{esc(e['shif_no'])}</td></tr>
   <tr><td>Pay To</td><td>{esc(pay_to)}</td></tr>
  </table>
 </div>
 <div class="grid">
  <table><tr><th>Earnings</th><th class="n">KES</th></tr>{_rows(earnings)}
   <tr class="tot"><td>Gross Pay</td><td class="n">{money(line['gross_pay'])}</td></tr></table>
  <table><tr><th>Deductions</th><th class="n">KES</th></tr>{_rows(deds)}
   <tr class="tot"><td>Total Deductions</td><td class="n">{money(line['total_deductions'])}</td></tr></table>
 </div>
 <div class="net"><span>NET PAY</span><span>KES {money(line['net_pay'])}</span></div>
 <div class="grid">
  <table><tr><th>Tax Computation</th><th class="n">KES</th></tr>{_rows(tax)}</table>
  <div>
   <table><tr><th>Employer Contributions</th><th class="n">KES</th></tr>{_rows(employer)}</table>
   <table><tr><th>Year to Date</th><th class="n">KES</th></tr>
    <tr><td>Gross Pay</td><td class="n">{money(ytd['gross'])}</td></tr>
    <tr><td>PAYE</td><td class="n">{money(ytd['paye'])}</td></tr>
    <tr><td>NSSF</td><td class="n">{money(ytd['nssf'])}</td></tr>
    <tr><td>Net Pay</td><td class="n">{money(ytd['net'])}</td></tr></table>
  </div>
 </div>
 <div class="foot">Computer-generated payslip - {esc(APP_NAME)}. Statutory deductions per Income Tax Act (Cap 470),
 NSSF Act 2013, Social Health Insurance Act 2023 and Affordable Housing Act 2024.</div>
</div>"""


def ytd_totals(db, line) -> dict:
    year, _ = line["period"].split("-")
    t = {"gross": 0.0, "paye": 0.0, "nssf": 0.0, "net": 0.0}
    for l in db.lines_for_year(int(year), line["employee"]["id"]):
        if l["period"] <= line["period"]:
            t["gross"] += l["gross_pay"]
            t["paye"] += l["paye"]
            t["nssf"] += l["nssf_employee"]
            t["net"] += l["net_pay"]
    return t


def payslips(db, period, base, emp_id=None) -> str:
    company = db.company()
    lines = [l for l in db.run_lines(period) if emp_id is None or l["employee"]["id"] == emp_id]
    body = "".join(payslip_html(l, company, ytd_totals(db, l)) for l in lines)
    name = "Payslips.html" if emp_id is None else f"Payslip_{lines[0]['employee']['staff_no']}.html"
    path = os.path.join(out_dir(base, period), name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"<!doctype html><html><head><meta charset='utf-8'><title>Payslips {period}</title>"
                f"<style>{CSS}</style></head><body>{body}</body></html>")
    return path


# ---------------------------------------------------------------------------
def payroll_register(db, period, base) -> str:
    lines = db.run_lines(period)
    allowance_names = sorted({k for l in lines for k in l["allowances"]})
    ded_names = sorted({k for l in lines for k in l["other_deductions"]})
    header = (["Staff No", "Name", "Department", "KRA PIN", "Basic"] + allowance_names +
              ["Overtime", "Bonus", "Arrears", "Leave Pay", "Other Earnings", "Absence", "Gross Pay",
               "Taxable Benefits", "NSSF Tier I", "NSSF Tier II", "SHIF", "Housing Levy",
               "Pension Allowed", "Taxable Pay", "Tax Charged", "Personal Relief",
               "Insurance Relief", "PAYE", "WHT", "Voluntary Pension"] + ded_names +
              ["Total Deductions", "Net Pay", "NSSF Employer", "AHL Employer", "NITA", "Employer Cost"])
    rows, totals = [], None
    for l in lines:
        e = l["employee"]
        r = ([e["staff_no"], full_name(e), e["department"], e["kra_pin"], l["basic"]] +
             [l["allowances"].get(a, 0) for a in allowance_names] +
             [l["overtime"], l["bonus"], l["arrears"], l["leave_pay"], l["other_earnings"], l["absence"],
              l["gross_pay"], l["taxable_benefits"], l["nssf_tier1"], l["nssf_tier2"], l["shif"],
              l["ahl_employee"], l["pension_allowed"], l["taxable_pay"], l["tax_charged"],
              l["personal_relief"], l["insurance_relief"], l["paye"], l["wht"], l["voluntary_pension"]] +
             [l["other_deductions"].get(d, 0) for d in ded_names] +
             [l["total_deductions"], l["net_pay"], l["nssf_employer"], l["ahl_employer"], l["nita"],
              l["employer_cost"]])
        rows.append(r)
        nums = r[4:]
        totals = nums if totals is None else [round(a + b, 2) for a, b in zip(totals, nums)]
    if totals:
        rows.append(["TOTAL", f"{len(lines)} employees", "", ""] + totals)
    return write_csv(os.path.join(out_dir(base, period), "Payroll_Register.csv"), header, rows)


def kra_p10(db, period, base) -> str:
    """Rows laid out in the order of the iTax P10 'Employee Details' sheet (resident employees)."""
    header = ["PIN of Employee", "Name of Employee", "Residential Status", "Type of Employee",
              "Basic Salary", "Housing Allowance", "Transport Allowance", "Leave Pay",
              "Overtime Allowance", "Directors Fee", "Lump Sum Payment", "Other Allowance",
              "Total Cash Pay", "Value of Car Benefit", "Other Non Cash Benefit",
              "Total Non Cash Pay", "Global Income", "Type of Housing", "Value of Housing",
              "Total Gross Pay", "30% of Cash Pay", "Actual Contribution", "Permissible Limit",
              "Mortgage Interest", "Deposit on Home Ownership Saving Plan", "Amount of Benefit",
              "Affordable Housing Levy", "Social Health Insurance Fund", "Post Retirement Medical Fund",
              "Taxable Pay", "Tax Payable", "Monthly Personal Relief", "Amount of Insurance Relief",
              "PAYE Tax"]
    rows = []
    for l in db.run_lines(period):
        e = l["employee"]
        if e["employment_type"] == "Consultant (WHT)":
            continue
        a = l["allowances"]
        other = a.get("Other Allowance", 0) + l["bonus"] + l["arrears"] + l["other_earnings"] - l["absence"]
        non_cash = round(l["taxable_benefits"] - (e["car_benefit"] or 0) - (e["housing_benefit"] or 0), 2)
        rows.append([
            e["kra_pin"], full_name(e), "Resident",
            "Primary Employee" if e["employment_type"] == "Primary" else "Secondary Employee",
            l["basic"], a.get("House Allowance", 0), a.get("Transport Allowance", 0), l["leave_pay"],
            l["overtime"], 0, 0, round(other, 2), l["gross_pay"], e["car_benefit"] or 0, non_cash,
            l["taxable_benefits"], 0, "Benefit not given" if not e["housing_benefit"] else "Employer's Owned House",
            e["housing_benefit"] or 0, round(l["gross_pay"] + l["taxable_benefits"], 2),
            round(l["gross_pay"] * 0.3, 2), round(l["nssf_employee"] + l["voluntary_pension"], 2),
            db.rates()["pension_deduction_cap"], l["mortgage_allowed"], 0, l["pension_allowed"],
            l["ahl_employee"], l["shif"], l["prmf_allowed"], l["taxable_pay"], l["tax_charged"],
            l["personal_relief"], l["insurance_relief"], l["paye"]])
    return write_csv(os.path.join(out_dir(base, period), "KRA_P10_PAYE.csv"), header, rows)


def nssf_return(db, period, base) -> str:
    header = ["Payroll Number", "Surname", "Other Names", "ID No", "KRA PIN", "NSSF No",
              "Gross Pay", "Tier I Employee", "Tier I Employer", "Tier II Employee",
              "Tier II Employer", "Total"]
    rows = []
    for l in db.run_lines(period):
        e = l["employee"]
        if not l["nssf_employee"]:
            continue
        rows.append([e["staff_no"], e["last_name"], e["first_name"], e["id_no"], e["kra_pin"],
                     e["nssf_no"], l["gross_pay"], l["nssf_tier1"], l["nssf_employer_tier1"],
                     l["nssf_tier2"], l["nssf_employer_tier2"],
                     round(l["nssf_employee"] + l["nssf_employer"], 2)])
    return write_csv(os.path.join(out_dir(base, period), "NSSF_Return.csv"), header, rows)


def shif_return(db, period, base) -> str:
    header = ["Payroll Number", "First Name", "Last Name", "ID No", "KRA PIN", "SHIF No",
              "Phone", "Gross Pay", "Amount"]
    rows = [[l["employee"]["staff_no"], l["employee"]["first_name"], l["employee"]["last_name"],
             l["employee"]["id_no"], l["employee"]["kra_pin"], l["employee"]["shif_no"],
             l["employee"]["phone"], l["gross_pay"], l["shif"]]
            for l in db.run_lines(period) if l["shif"]]
    return write_csv(os.path.join(out_dir(base, period), "SHIF_Return.csv"), header, rows)


def ahl_return(db, period, base) -> str:
    header = ["ID No", "Full Name", "KRA PIN", "Gross Pay", "Employee Levy", "Employer Levy", "Total"]
    rows = [[l["employee"]["id_no"], full_name(l["employee"]), l["employee"]["kra_pin"], l["gross_pay"],
             l["ahl_employee"], l["ahl_employer"], round(l["ahl_employee"] + l["ahl_employer"], 2)]
            for l in db.run_lines(period) if l["ahl_employee"]]
    return write_csv(os.path.join(out_dir(base, period), "Housing_Levy_Return.csv"), header, rows)


def bank_file(db, period, base) -> str:
    header = ["Staff No", "Beneficiary Name", "Payment Mode", "Bank", "Branch", "Account / Phone",
              "Amount", "Narration"]
    rows = []
    for l in db.run_lines(period):
        e = l["employee"]
        if l["net_pay"] <= 0:
            continue
        acct = e["phone"] if e["payment_mode"] == "M-Pesa" else e["account_no"]
        rows.append([e["staff_no"], full_name(e).upper(), e["payment_mode"], e["bank_name"],
                     e["bank_branch"], acct, l["net_pay"], f"SALARY {period_label(period).upper()}"])
    return write_csv(os.path.join(out_dir(base, period), "Bank_Transfer.csv"), header, rows)


def summary(db, period) -> dict:
    lines = db.run_lines(period)
    s = lambda k: round(sum(l[k] for l in lines), 2)
    other = round(sum(sum(l["other_deductions"].values()) for l in lines), 2)
    return {
        "employees": len(lines), "gross": s("gross_pay"), "net": s("net_pay"),
        "paye": s("paye"), "wht": s("wht"),
        "nssf_ee": s("nssf_employee"), "nssf_er": s("nssf_employer"),
        "shif": s("shif"), "ahl_ee": s("ahl_employee"), "ahl_er": s("ahl_employer"),
        "nita": s("nita"), "pension": s("voluntary_pension"), "other": other,
        "employer_cost": s("employer_cost"), "due": due_date(period),
    }


def journal(db, period, base) -> str:
    t = summary(db, period)
    rows = [
        ["Salaries & Wages Expense", t["gross"], ""],
        ["Employer NSSF Expense", t["nssf_er"], ""],
        ["Employer Housing Levy Expense", t["ahl_er"], ""],
        ["NITA Levy Expense", t["nita"], ""],
        ["PAYE Payable (KRA)", "", t["paye"]],
        ["Withholding Tax Payable (KRA)", "", t["wht"]],
        ["NSSF Payable", "", round(t["nssf_ee"] + t["nssf_er"], 2)],
        ["SHIF Payable (SHA)", "", t["shif"]],
        ["Housing Levy Payable (KRA)", "", round(t["ahl_ee"] + t["ahl_er"], 2)],
        ["NITA Payable", "", t["nita"]],
        ["Pension Scheme Payable", "", t["pension"]],
        ["Loans / Other Deductions Payable", "", t["other"]],
        ["Net Salaries Payable", "", t["net"]],
    ]
    dr = round(sum(r[1] for r in rows if r[1] != ""), 2)
    cr = round(sum(r[2] for r in rows if r[2] != ""), 2)
    rows.append(["TOTAL", dr, cr])
    return write_csv(os.path.join(out_dir(base, period), "Payroll_Journal.csv"),
                     ["Account", "Debit", "Credit"], rows)


def statutory_summary(db, period, base) -> str:
    t = summary(db, period)
    rows = [
        ["PAYE", "KRA iTax (P10)", t["paye"], t["due"]],
        ["Withholding Tax (consultants)", "KRA iTax", t["wht"], "Within 5 working days of payment"],
        ["Affordable Housing Levy", "KRA iTax", round(t["ahl_ee"] + t["ahl_er"], 2), t["due"]],
        ["NSSF", "NSSF eReturn", round(t["nssf_ee"] + t["nssf_er"], 2), t["due"]],
        ["SHIF", "SHA Portal", t["shif"], t["due"]],
        ["NITA Levy", "NITA Portal", t["nita"], t["due"]],
    ]
    return write_csv(os.path.join(out_dir(base, period), "Statutory_Summary.csv"),
                     ["Statutory Item", "Remit Via", "Amount (KES)", "Due Date"], rows)


def p9a(db, year: int, base: str, emp_id=None) -> str:
    """P9A Tax Deduction Card for one employee or all employees for a year."""
    company = db.company()
    lines = db.lines_for_year(year, emp_id)
    by_emp: dict = {}
    for l in lines:
        by_emp.setdefault(l["employee"]["id"], []).append(l)
    cards = []
    cols = ["Month", "A Basic", "B Benefits", "C Quarters", "D Gross Pay", "E1 30% of A",
            "E2 Actual", "E3 Fixed", "F Mortgage Int.", "G Allowable Pension", "SHIF", "AHL",
            "H Chargeable Pay", "J Tax Charged", "K Personal Relief", "Insurance Relief", "L PAYE"]
    cap = db.rates()["pension_deduction_cap"]
    for emp_lines in by_emp.values():
        e = emp_lines[-1]["employee"]
        body, tot = [], [0.0] * (len(cols) - 1)
        for l in emp_lines:
            vals = [l["gross_pay"], l["taxable_benefits"] - (e["housing_benefit"] or 0),
                    e["housing_benefit"] or 0, l["gross_pay"] + l["taxable_benefits"],
                    l["gross_pay"] * 0.3, l["nssf_employee"] + l["voluntary_pension"], cap,
                    l["mortgage_allowed"], l["pension_allowed"], l["shif"], l["ahl_employee"],
                    l["taxable_pay"], l["tax_charged"], l["personal_relief"], l["insurance_relief"],
                    l["paye"]]
            tot = [a + b for a, b in zip(tot, vals)]
            m = MONTHS[int(l["period"].split("-")[1])]
            body.append("<tr><td>" + m + "</td>" + "".join(f"<td class='n'>{money(v)}</td>" for v in vals) + "</tr>")
        body.append("<tr class='tot'><td>TOTAL</td>" + "".join(f"<td class='n'>{money(v)}</td>" for v in tot) + "</tr>")
        esc = lambda s: html.escape(str(s or ""))
        cards.append(f"""<div class="slip" style="width:287mm">
 <div class="head"><div><h1>{esc(company['name'])}</h1><div class="sub">Employer PIN: {esc(company['kra_pin'])}</div></div>
 <div class="title">KENYA REVENUE AUTHORITY<br>TAX DEDUCTION CARD (P9A) - {year}</div></div>
 <table class="info"><tr><td>Employee</td><td><b>{esc(full_name(e))}</b> ({esc(e['staff_no'])})</td>
 <td>Employee PIN</td><td>{esc(e['kra_pin'])}</td></tr></table>
 <table style="font-size:10px"><tr>{''.join(f'<th class="n">{c}</th>' for c in cols)}</tr>{''.join(body)}</table>
 <div class="foot">Total PAYE for the year: KES {money(tot[-1])}. Generated by {esc(APP_NAME)}.</div></div>""")
    path = os.path.join(base, f"P9A_{year}" + (f"_{lines[0]['employee']['staff_no']}" if emp_id and lines else "") + ".html")
    os.makedirs(base, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"<!doctype html><html><head><meta charset='utf-8'><title>P9A {year}</title>"
                f"<style>{CSS}@page{{size:A4 landscape}}</style></head><body>{''.join(cards)}</body></html>")
    return path


ALL_PERIOD_REPORTS = [
    ("Payslips (all employees)", payslips),
    ("Payroll Register", payroll_register),
    ("KRA P10 (PAYE)", kra_p10),
    ("NSSF Return", nssf_return),
    ("SHIF Return", shif_return),
    ("Housing Levy Return", ahl_return),
    ("Bank / M-Pesa Transfer File", bank_file),
    ("Payroll Journal", journal),
    ("Statutory Summary & Due Dates", statutory_summary),
]
