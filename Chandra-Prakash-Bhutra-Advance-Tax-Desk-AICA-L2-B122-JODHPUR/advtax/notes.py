"""Client-facing outputs: WhatsApp text and a one-page Word note."""
from __future__ import annotations

import io
from datetime import date

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

from .engine import ClientInputs, fmt_inr


def _dmy(d: date) -> str:
    return d.strftime("%d %b %Y")


def headline(result: dict) -> str:
    nd = result["schedule"]["next_due"]
    if not result["liable"]:
        return "No advance tax is payable on the present estimate."
    if nd is None:
        return "All instalment dates for the year have passed."
    if nd["pay_now"] <= 0:
        return f"Nothing more to pay for the {_dmy(nd['date'])} instalment."
    return f"Pay Rs {fmt_inr(nd['pay_now'])} by {_dmy(nd['date'])}."


def closing_line(result: dict) -> str:
    nd = result["schedule"]["next_due"]
    if result["liable"] and nd and nd["pay_now"] > 0:
        return "Please pay through e-Pay Tax on the income-tax portal and share the challan with us."
    if not result["liable"] and result["net_liability"] > 0:
        return (f"The estimated tax of Rs {fmt_inr(result['net_liability'])} is payable as self-assessment tax "
                "before the return is filed.")
    return "No payment is needed now. We will review the estimate again before the next due date."


def plain_explanation(inp: ClientInputs, result: dict) -> str:
    """Template explanation used when no AI key is supplied."""
    c, s = result["chosen"], result["schedule"]
    lines = [
        f"Your estimated total income for tax year {result['tax_year']} is Rs {fmt_inr(c['total_income'])}.",
        f"Estimated tax for the year ({c['regime']}) is Rs {fmt_inr(c['total_tax'])}.",
    ]
    if result["tds_tcs"]:
        lines.append(f"TDS/TCS of Rs {fmt_inr(result['tds_tcs'])} is already deducted, leaving "
                     f"Rs {fmt_inr(result['net_liability'])} to be paid as advance tax.")
    if not result["liable"]:
        lines.append(result["not_liable_reason"])
        return " ".join(lines)
    lines.append(f"You have paid Rs {fmt_inr(s['paid_to_date'])} so far.")
    nd = s["next_due"]
    if nd and nd["pay_now"] > 0:
        lines.append(f"By {_dmy(nd['date'])}, {int(nd['cumulative_pct'] * 100)}% of the year's tax must be paid, "
                     f"so Rs {fmt_inr(nd['pay_now'])} is due now.")
    if s["interest_incurred"]:
        lines.append(f"Interest of about Rs {fmt_inr(s['interest_incurred'])} has already arisen on earlier instalments.")
    if (result.get("regime_saving") or 0) > 0:
        other = "old" if result["chosen_key"] == "new" else "new"
        lines.append(f"This regime saves about Rs {fmt_inr(result['regime_saving'])} compared with the {other} regime.")
    return " ".join(lines)


def whatsapp_text(inp: ClientInputs, result: dict, firm_name: str = "", explanation: str | None = None) -> str:
    c, s = result["chosen"], result["schedule"]
    nd = s["next_due"]
    out = [f"*Advance Tax Reminder - Tax Year {result['tax_year']}*", f"Dear {inp.name},", ""]
    out.append(f"*{headline(result)}*")
    out.append("")
    out.append(f"Estimated income: Rs {fmt_inr(c['total_income'])}")
    out.append(f"Estimated tax ({c['regime']}): Rs {fmt_inr(c['total_tax'])}")
    if result["tds_tcs"]:
        out.append(f"Less TDS/TCS: Rs {fmt_inr(result['tds_tcs'])}")
    out.append(f"Advance tax paid so far: Rs {fmt_inr(s['paid_to_date'])}")
    if result["liable"] and nd and nd["pay_now"] > 0:
        out.append(f"Due by {_dmy(nd['date'])}: Rs {fmt_inr(nd['pay_now'])} ({nd['days_left']} days left)")
        saved = round(nd["pay_now"] // 100 * 100 * 0.01 * (1 if nd["cumulative_pct"] >= 1 else 3))
        if saved:
            out.append(f"Late payment will cost about Rs {fmt_inr(saved)} as interest.")
    out.append("")
    out.append(explanation or "This is an estimate based on your books to date and may change with your actual results.")
    out.append("")
    out.append(closing_line(result))
    if firm_name:
        out.append(f"- {firm_name}")
    return "\n".join(out)


def docx_note(inp: ClientInputs, result: dict, firm_name: str = "", explanation: str | None = None) -> bytes:
    c, s = result["chosen"], result["schedule"]
    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)

    if firm_name:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(firm_name)
        r.bold = True
        r.font.size = Pt(14)
    h = doc.add_paragraph()
    h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = h.add_run(f"Advance Tax Estimate - Tax Year {result['tax_year']}")
    r.bold = True
    r.font.size = Pt(13)
    doc.add_paragraph(f"Client: {inp.name} ({inp.constitution})        As on: {_dmy(result['as_on'])}")

    p = doc.add_paragraph()
    r = p.add_run(headline(result))
    r.bold = True
    r.font.size = Pt(13)

    doc.add_paragraph(explanation or plain_explanation(inp, result))

    doc.add_paragraph().add_run("Estimated income and tax").bold = True
    rows = [("Salary", c["salary_income"]), ("House property", c["house_property_income"]),
            ("Business or profession", c["business_income"]), ("Other sources", c["other_sources_income"]),
            ("Short-term capital gains (slab rate)", c["stcg_other"]),
            ("Short-term capital gains (equity)", c["stcg_equity"]),
            ("Long-term capital gains (equity)", c["ltcg_equity"]),
            ("Long-term capital gains (other)", c["ltcg_other"]),
            ("Less: deductions", -c["deductions"])]
    rows = [(k, v) for k, v in rows if v]
    rows += [("Total income", c["total_income"]), ("Tax on normal income", c["tax_on_normal_income"])]
    if c["tax_on_capital_gains"]:
        rows.append(("Tax on capital gains", c["tax_on_capital_gains"]))
    if c["rebate"]:
        rows.append(("Less: rebate / marginal relief", -c["rebate"]))
    if c["surcharge"]:
        rows.append(("Surcharge", c["surcharge"]))
    rows += [("Health and education cess", c["cess"]), (f"Total tax ({c['regime']})", c["total_tax"]),
             ("Less: TDS / TCS", -result["tds_tcs"]), ("Advance tax liability for the year", result["net_liability"])]
    t = doc.add_table(rows=0, cols=2)
    t.style = "Table Grid"
    for k, v in rows:
        cells = t.add_row().cells
        cells[0].text = k
        cells[1].text = fmt_inr(v)
        cells[1].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
        if k.startswith(("Total", "Advance tax liability")):
            for cell in cells:
                for run in cell.paragraphs[0].runs:
                    run.bold = True

    if result["liable"]:
        doc.add_paragraph()
        doc.add_paragraph().add_run("Instalment position").bold = True
        t2 = doc.add_table(rows=1, cols=5)
        t2.style = "Light Grid Accent 1"
        for i, head in enumerate(["Due date", "Cumulative %", "Required (Rs)", "Paid by date (Rs)", "Shortfall (Rs)"]):
            t2.rows[0].cells[i].text = head
        for row in s["rows"]:
            cells = t2.add_row().cells
            cells[0].text = _dmy(row["due_date"])
            cells[1].text = f"{int(row['cumulative_pct'] * 100)}%"
            cells[2].text = fmt_inr(row["required_cumulative"])
            cells[3].text = fmt_inr(row["paid_by_due_date"])
            cells[4].text = fmt_inr(row["shortfall"])
        if s["interest_incurred"]:
            doc.add_paragraph(f"Interest for deferment already arisen: Rs {fmt_inr(s['interest_incurred'])}.")

    doc.add_paragraph()
    note = doc.add_paragraph("This is an estimate prepared from books and information available on the above date. "
                             "Actual tax will depend on final accounts. " + closing_line(result))
    note.runs[0].italic = True
    note.runs[0].font.size = Pt(9)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
