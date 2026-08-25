import csv
import io
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from sqlalchemy.orm import Session

from app.models.gst_report import GstReportInput
from app.services.daybook_service import get_consolidated_daybook
from app.services.pdf_header import pdf_document
from app.services.report_service import NumberedCanvas, _export_period_label, _inr, _INR_FONT, _INR_FONT_BOLD

CHANNELS = ("cash", "card_qr", "dineout", "zomato", "swiggy")
OWN_CHANNELS = ("cash", "card_qr", "dineout")
PACKING_CHANNELS = ("zomato", "swiggy")
GST_RATE_NUM = 5.0
GST_RATE_DEN = 105.0

RULES = {
    "days": "Take the data from All Branches Day Book for the selected period.",
    "total": "TOTAL",
    "adjustment": "Manual row to add or less any channel amount.",
    "net": "Total − Adjustment, or Total + Adjustment.",
    "tax": "Net × 5 ÷ 105  (GST inclusive @ 5%)",
    "basic": "Net − Tax",
    "deposit": "Sum of all Tax @ 5% columns",
    "balance": "Enter GST cash ledger balance.",
    "requirement": "Tax to be deposited − Available Balance",
}


def _num(val: Any) -> float:
    try:
        return float(val or 0.0)
    except (TypeError, ValueError):
        return 0.0


def gst_inclusive_tax(amount: float) -> float:
    return _num(amount) * GST_RATE_NUM / GST_RATE_DEN


def apply_adjustment(total: float, adj: float, mode: str) -> float:
    amount = abs(_num(adj))
    if (mode or "less").lower() == "add":
        return _num(total) + amount
    return _num(total) - amount


def _empty_amounts() -> Dict[str, float]:
    return {key: 0.0 for key in CHANNELS}


def _channel_map(row: Dict[str, Any]) -> Dict[str, float]:
    return {
        "cash": _num(row.get("cash")),
        "card_qr": _num(row.get("card_qr")),
        "dineout": _num(row.get("dineout")),
        "zomato": _num(row.get("zomato")),
        "swiggy": _num(row.get("swiggy")),
    }


def _find_input(db: Session, branch_id: Optional[int], start: date, end: date) -> Optional[GstReportInput]:
    query = db.query(GstReportInput).filter(
        GstReportInput.start_date == start,
        GstReportInput.end_date == end,
    )
    if branch_id:
        query = query.filter(GstReportInput.branch_id == branch_id)
    else:
        query = query.filter(GstReportInput.branch_id.is_(None))
    return query.first()


def _input_payload(row: Optional[GstReportInput]) -> Dict[str, Any]:
    if not row:
        return {
            "mode": "less",
            "cash": 0.0,
            "card_qr": 0.0,
            "dineout": 0.0,
            "zomato": 0.0,
            "swiggy": 0.0,
            "available_balance": 0.0,
        }
    return {
        "mode": (row.adj_mode or "less").lower(),
        "cash": _num(row.adj_cash),
        "card_qr": _num(row.adj_card_qr),
        "dineout": _num(row.adj_dineout),
        "zomato": _num(row.adj_zomato),
        "swiggy": _num(row.adj_swiggy),
        "available_balance": _num(row.available_balance),
    }


def _aggregator_channel_key(batch) -> Optional[str]:
    code = ((batch.aggregator.code if batch.aggregator else "") or "").upper()
    name = ((batch.aggregator.name if batch.aggregator else "") or "").lower()
    if code == "ZOMATO" or "zomato" in name:
        return "zomato"
    if code == "SWIGGY" or "swiggy" in name:
        return "swiggy"
    return None


def _aggregator_deduction_totals(
    db: Session,
    deduction_type: str,
    branch_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> Dict[str, float]:
    from app.models.aggregator import Aggregator
    from app.models.settlement import SettlementBatch

    query = db.query(SettlementBatch).join(Aggregator, SettlementBatch.aggregator_id == Aggregator.id)
    if branch_id:
        query = query.filter(SettlementBatch.branch_id == branch_id)
    if start_date:
        query = query.filter(SettlementBatch.period_start_date >= start_date)
    if end_date:
        query = query.filter(SettlementBatch.period_end_date <= end_date)

    wanted = (deduction_type or "").upper()
    totals = {"zomato": 0.0, "swiggy": 0.0}
    for batch in query.all():
        key = _aggregator_channel_key(batch)
        if not key:
            continue
        for deduction in batch.deductions:
            if (deduction.deduction_type or "").upper() == wanted:
                totals[key] += abs(_num(deduction.amount))
    return totals


def get_packing_charges(
    db: Session,
    branch_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> Dict[str, float]:
    return _aggregator_deduction_totals(db, "PACKING_CHARGES", branch_id, start_date, end_date)


def get_section_9_5_tax(
    db: Session,
    branch_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> Dict[str, float]:
    return _aggregator_deduction_totals(db, "GST_9_5", branch_id, start_date, end_date)


def compute_gst_payable(
    day_rows: List[Dict[str, Any]],
    adjustment: Optional[Dict[str, Any]] = None,
    packing: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    adj = _input_payload(None)
    if adjustment:
        adj.update({
            "mode": str(adjustment.get("mode") or "less").lower(),
            "cash": _num(adjustment.get("cash")),
            "card_qr": _num(adjustment.get("card_qr")),
            "dineout": _num(adjustment.get("dineout")),
            "available_balance": _num(adjustment.get("available_balance")),
        })
        if adj["mode"] not in ("add", "less"):
            adj["mode"] = "less"

    packing = packing or {}
    adj["zomato"] = abs(_num(packing.get("zomato")))
    adj["swiggy"] = abs(_num(packing.get("swiggy")))
    adj["source"] = {
        "zomato": "packing_charges",
        "swiggy": "packing_charges",
    }

    rows: List[Dict[str, Any]] = []
    totals = _empty_amounts()
    for raw in day_rows:
        raw_date = raw.get("date")
        if hasattr(raw_date, "isoformat"):
            date_key = raw_date.isoformat()
        else:
            date_key = str(raw_date or "")[:10]
        amounts = _channel_map(raw)
        if not any(amounts.values()):
            continue
        rows.append({"date": date_key, **amounts})
        for key in CHANNELS:
            totals[key] += amounts[key]
    rows.sort(key=lambda item: item["date"])

    net = _empty_amounts()
    tax = _empty_amounts()
    basic = _empty_amounts()
    for key in OWN_CHANNELS:
        net[key] = apply_adjustment(totals[key], adj[key], adj["mode"])
        tax[key] = gst_inclusive_tax(net[key])
        basic[key] = net[key] - tax[key]
    for key in PACKING_CHANNELS:
        net[key] = adj[key]
        tax[key] = gst_inclusive_tax(net[key])
        basic[key] = net[key] - tax[key]

    tax_to_deposit = (
        tax["cash"] + tax["card_qr"] + tax["dineout"] + tax["zomato"] + tax["swiggy"]
    )
    basic_total = sum(basic[key] for key in CHANNELS)
    available = adj["available_balance"]
    return {
        "rows": rows,
        "totals": totals,
        "adjustment": adj,
        "net": net,
        "tax": tax,
        "basic": basic,
        "basic_total": basic_total,
        "tax_to_deposit": tax_to_deposit,
        "available_balance": available,
        "additional_requirement": tax_to_deposit - available,
        "rules": RULES,
    }


HSN_RESTAURANT = "996331"
HSN_DESCRIPTION = (
    "Services provided by restaurants, cafes and similar eating facilities "
    "including takeaway services, room services and door delivery of food"
)
PLACE_OF_SUPPLY_UP = "09-Uttar Pradesh"


def gst_offline_figures(data: Dict[str, Any]) -> Dict[str, float]:
    basic_total = round(_num(data.get("basic_total")), 2)
    if not basic_total and data.get("basic"):
        basic_total = round(sum(_num(data["basic"].get(key)) for key in CHANNELS), 2)
    tax = round(_num(data.get("tax_to_deposit")), 2)
    cgst = round(tax / 2.0, 2)
    sgst = round(tax - cgst, 2)
    return {
        "basic_total": basic_total,
        "tax_to_deposit": tax,
        "cgst": cgst,
        "sgst": sgst,
        "total_value": round(basic_total + cgst + sgst, 2),
    }


def _csv_bytes(headers: List[str], rows: List[List[Any]]) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\r\n")
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)
    return ("\ufeff" + buf.getvalue()).encode("utf-8")


TABLE14_NATURE = "Liable to pay tax u/s 9(5)"
TABLE14_OPERATORS = (
    {"key": "zomato", "gstin": "09AADCD4946L1Z8", "name": "ETERNAL LIMITED"},
    {"key": "swiggy", "gstin": "09AAFCB7707D1ZS", "name": "Swiggy"},
)


def table14_row_from_tax(tax_amount: float) -> Dict[str, float]:
    tax = round(_num(tax_amount), 2)
    net = round(tax * 100.0 / GST_RATE_NUM, 2)
    cgst = round(tax / 2.0, 2)
    sgst = round(tax - cgst, 2)
    return {"tax": tax, "net": net, "cgst": cgst, "sgst": sgst, "igst": 0.0, "cess": 0.0}


def generate_b2cs_csv(
    db: Session,
    branch_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> Tuple[bytes, str]:
    data = get_gst_payable_report(db, branch_id, start_date, end_date)
    figures = gst_offline_figures(data)
    payload = _csv_bytes(
        ["Type", "Place Of Supply", "Applicable % of Tax Rate", "Taxable Value", "Cess Amount", "E-Commerce GSTIN", "Rate"],
        [["OE", PLACE_OF_SUPPLY_UP, "", f"{figures['basic_total']:.2f}", "0", "", "5"]],
    )
    label = (data.get("period_label") or "GST").replace(" ", "_")
    return payload, f"GST_B2CS_{label}.csv"


def generate_hsn_b2cs_csv(
    db: Session,
    branch_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> Tuple[bytes, str]:
    data = get_gst_payable_report(db, branch_id, start_date, end_date)
    figures = gst_offline_figures(data)
    payload = _csv_bytes(
        [
            "HSN",
            "Description",
            "UQC",
            "Total Quantity",
            "Total Value",
            "Taxable Value",
            "Integrated Tax Amount",
            "Central Tax Amount",
            "State/UT Tax Amount",
            "Cess Amount",
            "Rate",
        ],
        [[
            HSN_RESTAURANT,
            HSN_DESCRIPTION,
            "NA",
            "0",
            f"{figures['total_value']:.2f}",
            f"{figures['basic_total']:.2f}",
            "0",
            f"{figures['cgst']:.2f}",
            f"{figures['sgst']:.2f}",
            "0",
            "5",
        ]],
    )
    label = (data.get("period_label") or "GST").replace(" ", "_")
    return payload, f"GST_HSN_B2C_{label}.csv"


def generate_table14_eco_csv(
    db: Session,
    branch_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> Tuple[bytes, str]:
    data = get_gst_payable_report(db, branch_id, start_date, end_date)
    taxes = get_section_9_5_tax(db, branch_id, start_date, end_date)
    rows = []
    for operator in TABLE14_OPERATORS:
        figures = table14_row_from_tax(taxes.get(operator["key"], 0.0))
        rows.append([
            TABLE14_NATURE,
            operator["gstin"],
            operator["name"],
            f"{figures['net']:.2f}",
            f"{figures['igst']:.2f}",
            f"{figures['cgst']:.2f}",
            f"{figures['sgst']:.2f}",
            f"{figures['cess']:.2f}",
        ])
    payload = _csv_bytes(
        [
            "Nature of Supply",
            "GSTIN of E-Commerce Operator",
            "E-Commerce Operator Name",
            "Net value of supplies",
            "Integrated tax",
            "Central tax",
            "State/UT tax",
            "Cess",
        ],
        rows,
    )
    label = (data.get("period_label") or "GST").replace(" ", "_")
    return payload, f"GST_TABLE14_ECO_9_5_{label}.csv"


def get_gst_payable_report(
    db: Session,
    branch_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> Dict[str, Any]:
    today = date.today()
    start = start_date or today.replace(day=1)
    end = end_date or today
    daybook = get_consolidated_daybook(db, branch_id, start, end)
    stored = _find_input(db, branch_id, start, end)
    packing = get_packing_charges(db, branch_id, start, end)
    computed = compute_gst_payable(daybook, _input_payload(stored), packing)
    branch_name = "All Branches"
    if branch_id and daybook:
        branch_name = daybook[0].get("branch_name") or branch_name
    elif branch_id:
        from app.models.branch import Branch
        branch = db.query(Branch).filter(Branch.id == branch_id).first()
        if branch:
            branch_name = branch.name
    return {
        "branch_id": branch_id,
        "branch_name": branch_name,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "period_label": _export_period_label(start, end),
        **computed,
    }


def save_gst_adjustments(
    db: Session,
    branch_id: Optional[int],
    start_date: date,
    end_date: date,
    mode: str,
    cash: float,
    card_qr: float,
    dineout: float,
    zomato: float,
    swiggy: float,
    available_balance: float,
) -> Dict[str, Any]:
    row = _find_input(db, branch_id, start_date, end_date)
    if not row:
        row = GstReportInput(branch_id=branch_id, start_date=start_date, end_date=end_date)
        db.add(row)
    row.adj_mode = "add" if str(mode or "").lower() == "add" else "less"
    row.adj_cash = abs(_num(cash))
    row.adj_card_qr = abs(_num(card_qr))
    row.adj_dineout = abs(_num(dineout))
    row.available_balance = _num(available_balance)
    db.commit()
    return get_gst_payable_report(db, branch_id, start_date, end_date)


def generate_pdf_gst_report(
    db: Session,
    branch_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> bytes:
    data = get_gst_payable_report(db, branch_id, start_date, end_date)
    buf = io.BytesIO()
    doc = pdf_document(buf, landscape(A4), left=18, right=18, bottom=28, title="GST Payable Report")
    styles = getSampleStyleSheet()
    title = ParagraphStyle("GstTitle", parent=styles["Heading1"], fontName=_INR_FONT_BOLD, fontSize=14, textColor=colors.HexColor("#166534"), spaceAfter=2)
    sub = ParagraphStyle("GstSub", parent=styles["Normal"], fontName=_INR_FONT, fontSize=8, textColor=colors.HexColor("#64748B"), spaceAfter=8)
    th = ParagraphStyle("GstTH", fontName=_INR_FONT_BOLD, fontSize=7, textColor=colors.HexColor("#4B6354"), alignment=1, leading=9)
    td = ParagraphStyle("GstTD", fontName=_INR_FONT, fontSize=7, textColor=colors.HexColor("#0F172A"), leading=9)
    tn = ParagraphStyle("GstTN", fontName=_INR_FONT, fontSize=7, textColor=colors.HexColor("#0F172A"), alignment=2, leading=9)
    tb = ParagraphStyle("GstTB", fontName=_INR_FONT_BOLD, fontSize=7, textColor=colors.HexColor("#166534"), alignment=2, leading=9)
    total_style = ParagraphStyle("GstTotal", fontName=_INR_FONT_BOLD, fontSize=8, textColor=colors.HexColor("#166534"), alignment=0, leading=10)

    def money(val: float, bold=False):
        return Paragraph(_inr(val), tb if bold else tn)

    header = [
        [
            Paragraph("Date", th),
            Paragraph("Cash", th),
            Paragraph("Card / QR Code", th),
            Paragraph("Dineout", th),
            Paragraph("Zomato", th),
            Paragraph("Swiggy", th),
        ]
    ]
    group = [[
        Paragraph("", th),
        Paragraph("Normal sales — GST payable by restaurant", th),
        "",
        "",
        Paragraph("Section 9(5) — GST paid by aggregator", th),
        "",
    ]]
    day_rows = []
    for item in data["rows"]:
        day_rows.append([
            Paragraph(item["date"], td),
            money(item["cash"]),
            money(item["card_qr"]),
            money(item["dineout"]),
            money(item["zomato"]),
            money(item["swiggy"]),
        ])

    def summary(label, amounts):
        return [
            Paragraph(label, tb),
            money(amounts["cash"], True),
            money(amounts["card_qr"], True),
            money(amounts["dineout"], True),
            money(amounts["zomato"], True),
            money(amounts["swiggy"], True),
        ]

    summaries = [
        summary("Total", data["totals"]),
        summary(
            f"Adjustment ({'Add' if data['adjustment']['mode'] == 'add' else 'Less'}) / Packing",
            data["adjustment"],
        ),
        summary("Net Sales", data["net"]),
        summary("Tax @ 5%", data["tax"]),
        summary("Basic", data["basic"]),
        [
            Paragraph("Tax to be deposited", tb),
            Paragraph(_inr(data["tax_to_deposit"]), total_style),
            "",
            "",
            "",
            "",
        ],
        [
            Paragraph("Available Balance", tb),
            Paragraph(_inr(data["available_balance"]), total_style),
            "",
            "",
            "",
            "",
        ],
        [
            Paragraph("Additional Requirement", tb),
            Paragraph(_inr(data["additional_requirement"]), total_style),
            "",
            "",
            "",
            "",
        ],
    ]
    table_data = group + header + day_rows + summaries
    day_count = len(day_rows)
    deposit_row = 2 + day_count + 5
    balance_row = deposit_row + 1
    need_row = deposit_row + 2
    tax_row = 2 + day_count + 3
    total_row = 2 + day_count

    table = Table(table_data, colWidths=[100, 105, 115, 105, 105, 105])
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 1), colors.HexColor("#F6FAF7")),
        ("SPAN", (1, 0), (3, 0)),
        ("SPAN", (4, 0), (5, 0)),
        ("BACKGROUND", (0, total_row), (-1, total_row), colors.HexColor("#F6FAF7")),
        ("BACKGROUND", (0, tax_row), (-1, tax_row), colors.HexColor("#DCFCE7")),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D5DDD7")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("SPAN", (1, deposit_row), (5, deposit_row)),
        ("SPAN", (1, balance_row), (5, balance_row)),
        ("SPAN", (1, need_row), (5, need_row)),
        ("BACKGROUND", (0, deposit_row), (-1, deposit_row), colors.HexColor("#ECFDF5")),
        ("BACKGROUND", (0, need_row), (-1, need_row), colors.HexColor("#FEF2F2")),
        ("ALIGN", (1, deposit_row), (1, need_row), "LEFT"),
    ]
    table.setStyle(TableStyle(style_cmds))

    story = [
        Paragraph("GST Payable Report", title),
        Paragraph(f"{data['branch_name']}  ·  {data['period_label']}", sub),
        table,
        Spacer(1, 8),
        Paragraph("Software property of Harsh Singhal & Associates", sub),
    ]
    doc.build(story, canvasmaker=NumberedCanvas)
    return buf.getvalue()
