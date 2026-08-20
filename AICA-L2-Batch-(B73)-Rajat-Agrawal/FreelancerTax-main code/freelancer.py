from datetime import datetime
from html import escape
from pathlib import Path
from textwrap import dedent
from typing import Optional
import json

import pandas as pd
import streamlit as st


st.set_page_config(
    page_title="Export Freelancer Tax Calculator — India",
    page_icon="🌍",
    layout="wide",
)


# ─── Constants ────────────────────────────────────────────────────────────────

NEW_REGIME_SLABS = [
    {"label": "Up to ₹4,00,000", "start": 0, "end": 400000, "rate": 0.00},
    {"label": "₹4,00,001 – ₹8,00,000", "start": 400000, "end": 800000, "rate": 0.05},
    {"label": "₹8,00,001 – ₹12,00,000", "start": 800000, "end": 1200000, "rate": 0.10},
    {"label": "₹12,00,001 – ₹16,00,000", "start": 1200000, "end": 1600000, "rate": 0.15},
    {"label": "₹16,00,001 – ₹20,00,000", "start": 1600000, "end": 2000000, "rate": 0.20},
    {"label": "₹20,00,001 – ₹24,00,000", "start": 2000000, "end": 2400000, "rate": 0.25},
    {"label": "Above ₹24,00,000", "start": 2400000, "end": float("inf"), "rate": 0.30},
]

REBATE_LIMIT = 1200000
REBATE_MAX = 60000
CESS_RATE = 0.04
GST_EXPORT_THRESHOLD = 2000000  # ₹20L for services
ADVANCE_TAX_TRIGGER = 10000

GOOGLE_SHEETS_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
GOOGLE_SHEET_ID = st.secrets.get("google_sheets", {}).get("sheet_id", "")
GOOGLE_SHEET_RANGE = st.secrets.get("google_sheets", {}).get("range", "Sheet1!A:Z")
SERVICE_ACCOUNT_JSON = st.secrets.get("google_sheets", {}).get("service_account_json", "")

FOREX_DEFAULTS = {
    "USD": 85.50,
    "EUR": 93.20,
    "GBP": 108.00,
    "AUD": 55.80,
    "CAD": 62.50,
    "SGD": 64.00,
    "AED": 23.30,
    "Other": 1.0,
}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def money(value: float) -> str:
    """Format an amount in Indian numbering style."""
    rounded = int(round(value))
    sign = "-" if rounded < 0 else ""
    number = str(abs(rounded))

    if len(number) <= 3:
        return f"₹{sign}{number}"

    last_three = number[-3:]
    rest = number[:-3]
    groups = []

    while len(rest) > 2:
        groups.insert(0, rest[-2:])
        rest = rest[:-2]

    if rest:
        groups.insert(0, rest)

    return f"₹{sign}{','.join(groups + [last_three])}"


def money_fc(value: float, currency: str) -> str:
    """Format foreign currency amount."""
    symbols = {"USD": "$", "EUR": "€", "GBP": "£", "AUD": "A$", "CAD": "C$", "SGD": "S$", "AED": "AED "}
    sym = symbols.get(currency, "")
    return f"{sym}{value:,.0f}"


def percent(value: float) -> str:
    return f"{value:.2f}%"


def calculate_freelancer_income(
    receipts: float,
    use_44ada: bool,
    expense_percent: float,
) -> tuple[float, float]:
    if use_44ada:
        expenses = receipts * 0.50
        income = receipts * 0.50
    else:
        expenses = receipts * expense_percent / 100
        income = receipts - expenses

    return income, expenses


def slab_breakup(income: float) -> pd.DataFrame:
    rows = []

    for slab in NEW_REGIME_SLABS:
        slab_start = slab["start"]
        slab_end = slab["end"]

        if income <= slab_start:
            taxable_amount = 0
        else:
            taxable_amount = min(income, slab_end) - slab_start

        taxable_amount = max(taxable_amount, 0)
        tax = taxable_amount * slab["rate"]

        rows.append(
            {
                "Slab": slab["label"],
                "Rate": f"{int(slab['rate'] * 100)}%",
                "Taxable Amount": taxable_amount,
                "Tax": tax,
            }
        )

    return pd.DataFrame(rows)


def calculate_tax_details(income: float) -> dict:
    breakup = slab_breakup(income)
    gross_tax = float(breakup["Tax"].sum())
    rebate = 0.0
    marginal_relief = 0.0

    if income <= REBATE_LIMIT:
        rebate = min(gross_tax, REBATE_MAX)
    else:
        excess_over_rebate_limit = income - REBATE_LIMIT
        marginal_relief = max(gross_tax - excess_over_rebate_limit, 0)

    tax_after_relief = max(gross_tax - rebate - marginal_relief, 0)
    cess = tax_after_relief * CESS_RATE
    total_tax = tax_after_relief + cess

    return {
        "breakup": breakup,
        "gross_tax": gross_tax,
        "rebate": rebate,
        "marginal_relief": marginal_relief,
        "tax_after_relief": tax_after_relief,
        "cess": cess,
        "total_tax": total_tax,
    }


def advance_tax_schedule(net_tax: float, use_44ada: bool) -> pd.DataFrame:
    if net_tax <= ADVANCE_TAX_TRIGGER:
        return pd.DataFrame(
            [
                {
                    "Due Date": "Not required",
                    "Cumulative Target": "Tax payable ≤ ₹10,000",
                    "Suggested Payment": 0,
                }
            ]
        )

    if use_44ada:
        return pd.DataFrame(
            [
                {
                    "Due Date": "On or before 15 March",
                    "Cumulative Target": "100% (presumptive — single instalment)",
                    "Suggested Payment": net_tax,
                }
            ]
        )

    milestones = [
        ("15 June", 0.15),
        ("15 September", 0.45),
        ("15 December", 0.75),
        ("15 March", 1.00),
    ]

    rows = []
    previously_due = 0

    for due_date, cumulative_percent in milestones:
        cumulative_due = net_tax * cumulative_percent
        rows.append(
            {
                "Due Date": due_date,
                "Cumulative Target": f"{int(cumulative_percent * 100)}%",
                "Suggested Payment": max(cumulative_due - previously_due, 0),
            }
        )
        previously_due = cumulative_due

    return pd.DataFrame(rows)


def build_comparison(receipts: float, expense_percent: float, other_income: float, tds: float) -> pd.DataFrame:
    rows = []

    for mode, income, expenses in [
        ("44ADA presumptive", receipts * 0.50, receipts * 0.50),
        ("Actual expenses", receipts * (1 - expense_percent / 100), receipts * expense_percent / 100),
    ]:
        total_income = income + other_income
        tax_details = calculate_tax_details(total_income)
        total_tax = tax_details["total_tax"]
        net_tax = max(total_tax - tds, 0)
        refund = max(tds - total_tax, 0)

        rows.append(
            {
                "Method": mode,
                "Allowed Expenses": expenses,
                "Professional Income": income,
                "Taxable Income": total_income,
                "Total Tax": total_tax,
                "Payable After TDS": net_tax,
                "Refund Estimate": refund,
            }
        )

    return pd.DataFrame(rows)


def explain_44ada_eligibility(receipts: float, cash_receipt_percent: float) -> tuple[str, str]:
    threshold = 7500000 if cash_receipt_percent <= 5 else 5000000

    if receipts <= threshold:
        status = "✅ Within the 44ADA gross-receipts threshold."
        tone = "success"
    else:
        status = "⚠️ Receipts exceed the basic 44ADA threshold; review books/audit position."
        tone = "warning"

    detail = (
        f"Threshold used: {money(threshold)} because cash receipts are "
        f"{cash_receipt_percent:.1f}% of total receipts."
    )

    return tone, f"{status} {detail}"


def format_money_columns(data: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    formatted = data.copy()

    for column in columns:
        formatted[column] = formatted[column].map(money)

    return formatted


def signed_money(value: float) -> str:
    if value < 0:
        return f"-{money(abs(value))}"

    return money(value)


def amount_tone(value: float) -> str:
    if value < 0:
        return "negative"
    if value > 0:
        return "positive"
    return "neutral"


def get_google_sheets_service() -> Optional[object]:
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ImportError:
        return None

    credentials = None
    if SERVICE_ACCOUNT_JSON:
        try:
            account_info = json.loads(SERVICE_ACCOUNT_JSON)
            credentials = service_account.Credentials.from_service_account_info(
                account_info, scopes=GOOGLE_SHEETS_SCOPES
            )
        except Exception:
            credentials = None

    if credentials is None:
        return None

    return build("sheets", "v4", credentials=credentials)


def append_row_to_google_sheet(row_values: list[object]) -> tuple[bool, str]:
    if not GOOGLE_SHEET_ID:
        return False, (
            "Google Sheet ID is not configured. Add `sheet_id` under `google_sheets` in Streamlit secrets."
        )

    service = get_google_sheets_service()
    if service is None:
        fallback_hint = (
            "Verify that `google-auth` and `google-api-python-client` are installed, "
            "and that the service account JSON file is in `SERVICE_ACCOUNT_JSON` in secrets."
        )
        return False, (
            "Google Sheets client could not be created. " + fallback_hint
        )

    try:
        service.spreadsheets().values().append(
            spreadsheetId=GOOGLE_SHEET_ID,
            range=GOOGLE_SHEET_RANGE,
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": [row_values]},
        ).execute()
        return True, "Row appended successfully."
    except Exception as exc:
        return False, f"Failed to save lead to Google Sheets: {exc}"


def render_horizontal_bar_chart(
    data: pd.DataFrame,
    label_col: str,
    value_col: str,
    note_col: Optional[str] = None,
) -> None:
    max_abs_value = max([abs(float(value)) for value in data[value_col]] + [1])
    rows_html = []

    for _, row in data.iterrows():
        label = escape(str(row[label_col]))
        note = escape(str(row[note_col])) if note_col and pd.notna(row[note_col]) else ""
        value = float(row[value_col])
        width = abs(value) / max_abs_value * 100
        width = max(width, 2) if value else 0
        tone = amount_tone(value)
        note_html = f'<div class="hbar-note">{note}</div>' if note else ""

        rows_html.append(
            f'<div class="hbar-row">'
            f'<div class="hbar-label"><strong>{label}</strong>{note_html}</div>'
            f'<div class="hbar-track">'
            f'<div class="hbar-fill {tone}" style="width: {width:.2f}%;"></div>'
            f'</div>'
            f'<div class="hbar-value {tone}">{signed_money(value)}</div>'
            f'</div>'
        )

    chart_html = f'<div class="hbar-card">{"".join(rows_html)}</div>'
    st.markdown(chart_html, unsafe_allow_html=True)


def render_dashboard_table(data: pd.DataFrame, money_columns: list[str]) -> None:
    header_html = "".join(f"<th>{escape(str(column))}</th>" for column in data.columns)
    body_rows = []

    for _, row in data.iterrows():
        cells = []

        for column in data.columns:
            value = row[column]

            if column in money_columns:
                amount = float(value)
                cells.append(
                    f'<td><span class="amount-pill {amount_tone(amount)}">{signed_money(amount)}</span></td>'
                )
            else:
                cells.append(f"<td>{escape(str(value))}</td>")

        body_rows.append(f"<tr>{''.join(cells)}</tr>")

    table_html = (
        '<div class="dash-table-wrap">'
        '<table class="dash-table">'
        f'<thead><tr>{header_html}</tr></thead>'
        f'<tbody>{"".join(body_rows)}</tbody>'
        '</table>'
        '</div>'
    )
    st.markdown(table_html, unsafe_allow_html=True)


# ─── Custom CSS ───────────────────────────────────────────────────────────────

st.markdown(
    dedent(
        """
    <style>
    .block-container {padding-top: 1.5rem;}

    /* Metric card styling */
    div[data-testid="stMetric"] {
        border: 1px solid #1a1a2e;
        border-radius: 12px;
        padding: 16px 18px;
        background: linear-gradient(135deg, #0f0f23 0%, #1a1a3e 100%);
        color: #e0e0ff;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(79, 70, 229, 0.3);
    }
    div[data-testid="stMetric"] label {
        font-weight: 700;
        color: #a5b4fc !important;
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: #ffffff !important;
        font-weight: 800;
    }

    /* Section headers */
    .export-header {
        background: linear-gradient(90deg, #4f46e5 0%, #7c3aed 50%, #06b6d4 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 1.1rem;
        margin-bottom: 0.5rem;
        letter-spacing: 0.3px;
    }

    /* Info card */
    .info-card {
        background: linear-gradient(135deg, #f0f4ff 0%, #e8ecff 100%);
        border-left: 4px solid #4f46e5;
        border-radius: 8px;
        padding: 16px 20px;
        margin: 10px 0;
        font-size: 0.92rem;
        line-height: 1.6;
        color: #1e1b4b;
    }

    /* Export badge */
    .export-badge {
        display: inline-block;
        background: linear-gradient(135deg, #4f46e5, #7c3aed);
        color: white;
        padding: 4px 14px;
        border-radius: 20px;
        font-size: 0.78rem;
        font-weight: 600;
        letter-spacing: 0.5px;
        margin-left: 8px;
        vertical-align: middle;
    }

    /* Flow step styling */
    .flow-step {
        background: #fafbff;
        border: 1px solid #e0e7ff;
        border-radius: 10px;
        padding: 14px 16px;
        text-align: center;
        margin: 4px;
        transition: all 0.2s ease;
    }
    .flow-step:hover {
        border-color: #4f46e5;
        box-shadow: 0 2px 12px rgba(79, 70, 229, 0.15);
    }
    .flow-step .step-num {
        background: #4f46e5;
        color: white;
        width: 28px;
        height: 28px;
        border-radius: 50%;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 0.85rem;
        margin-bottom: 6px;
    }
    .flow-step .step-label {
        font-size: 0.82rem;
        color: #64748b;
        font-weight: 500;
    }
    .flow-step .step-value {
        font-size: 1.05rem;
        font-weight: 700;
        color: #1e1b4b;
        margin-top: 2px;
    }

    /* Checklist styling */
    .checklist-item {
        display: flex;
        align-items: flex-start;
        gap: 10px;
        padding: 10px 14px;
        margin: 6px 0;
        background: #fafbff;
        border-radius: 8px;
        border-left: 3px solid #4f46e5;
        font-size: 0.9rem;
        line-height: 1.5;
    }

    /* GST info box */
    .gst-box {
        background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
        border: 1px solid #6ee7b7;
        border-radius: 10px;
        padding: 16px 20px;
        margin: 10px 0;
    }
    .gst-box-warning {
        background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%);
        border: 1px solid #fcd34d;
        border-radius: 10px;
        padding: 16px 20px;
        margin: 10px 0;
    }

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 8px 20px;
        font-weight: 600;
    }

    /* Dashboard horizontal bars */
    .hbar-card {
        background: #ffffff;
        border: 1px solid #e0e7ff;
        border-radius: 10px;
        padding: 12px 14px;
        margin: 8px 0 14px 0;
        box-shadow: 0 2px 10px rgba(30, 27, 75, 0.06);
    }
    .hbar-row {
        display: grid;
        grid-template-columns: minmax(150px, 31%) 1fr minmax(105px, 14%);
        align-items: center;
        gap: 12px;
        padding: 10px 0;
        border-bottom: 1px solid #eef2ff;
    }
    .hbar-row:last-child {
        border-bottom: 0;
    }
    .hbar-label {
        color: #1e1b4b;
        font-size: 0.88rem;
        line-height: 1.25;
    }
    .hbar-note {
        color: #64748b;
        font-size: 0.76rem;
        margin-top: 3px;
    }
    .hbar-track {
        height: 17px;
        background: #eef2ff;
        border-radius: 999px;
        overflow: hidden;
        border: 1px solid #dbe4ff;
    }
    .hbar-fill {
        height: 100%;
        border-radius: 999px;
    }
    .hbar-fill.positive {
        background: linear-gradient(90deg, #2563eb, #06b6d4);
    }
    .hbar-fill.negative {
        background: linear-gradient(90deg, #f97316, #ef4444);
    }
    .hbar-fill.neutral {
        background: #94a3b8;
    }
    .hbar-value {
        text-align: right;
        font-weight: 800;
        font-size: 0.88rem;
        white-space: nowrap;
    }
    .hbar-value.positive {
        color: #075985;
    }
    .hbar-value.negative {
        color: #b91c1c;
    }
    .hbar-value.neutral {
        color: #64748b;
    }

    /* Dashboard explanation tables */
    .dash-table-wrap {
        overflow-x: auto;
        border: 1px solid #dbe4ff;
        border-radius: 10px;
        margin: 8px 0 22px 0;
        box-shadow: 0 2px 10px rgba(30, 27, 75, 0.05);
    }
    table.dash-table {
        width: 100%;
        border-collapse: collapse;
        background: #ffffff;
        font-size: 0.88rem;
    }
    .dash-table th {
        background: #eef2ff;
        color: #312e81;
        text-align: left;
        padding: 11px 12px;
        font-weight: 800;
        border-bottom: 1px solid #dbe4ff;
        white-space: nowrap;
    }
    .dash-table td {
        padding: 11px 12px;
        border-bottom: 1px solid #eef2ff;
        color: #334155;
        vertical-align: top;
    }
    .dash-table tr:nth-child(even) td {
        background: #fbfdff;
    }
    .dash-table tr:last-child td {
        border-bottom: 0;
    }
    .amount-pill {
        display: inline-block;
        min-width: 96px;
        text-align: right;
        padding: 4px 9px;
        border-radius: 999px;
        font-weight: 800;
        font-variant-numeric: tabular-nums;
        white-space: nowrap;
    }
    .amount-pill.positive {
        background: #e0f2fe;
        color: #075985;
    }
    .amount-pill.negative {
        background: #fee2e2;
        color: #b91c1c;
    }
    .amount-pill.neutral {
        background: #f1f5f9;
        color: #475569;
    }

    .small-note {
        color: #5f6368;
        font-size: 0.88rem;
        line-height: 1.5;
    }
    </style>
        """
    ).strip(),
    unsafe_allow_html=True,
)


# ─── Title ────────────────────────────────────────────────────────────────────

st.markdown(
    """
    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 4px;">
        <h1 style="margin: 0; font-size: 1.8rem;">🌍 Export Freelancer Tax Calculator</h1>
        <span class="export-badge">EXPORT OF SERVICES</span>
    </div>
    """,
    unsafe_allow_html=True,
)
st.caption("For Indian freelancers earning from foreign clients · CA Rajat Agrawal")

# ─── Hero Section: Consultation ───────────────────────────────────────────────

st.markdown(
    """
    <div style="background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%); border-radius: 12px; padding: 24px 28px; margin: 20px 0; color: white;">
        <div style="display: flex; align-items: center; justify-content: space-between; gap: 20px;">
            <div>
                <h2 style="margin: 0 0 8px 0; font-size: 1.5rem; color: white;">💼 Need Personalized Tax Guidance?</h2>
                <p style="margin: 0 0 16px 0; font-size: 0.95rem; color: #e0e0ff; line-height: 1.5;">
                    Our Chartered Accountants will analyze your specific situation and help you optimize your tax position.
                    Book a consultation call with an expert.
                </p>
                <a href="https://prokhata.com/product/consultation-call-with-chartered-accountant/" target="_blank" style="display: inline-block; background: white; color: #4f46e5; padding: 10px 24px; border-radius: 6px; text-decoration: none; font-weight: 600; font-size: 0.95rem;">
                    📅 Book Consultation Call →
                </a>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


st.sidebar.markdown("## 📋 Your Details")

tax_year = st.sidebar.selectbox(
    "Assessment year",
    ["FY 2026-27 / Tax Year 2026-27", "FY 2025-26 / AY 2026-27"],
    help="Both options currently use the new-regime slab set.",
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 💱 Foreign Income")

billing_currency = st.sidebar.selectbox(
    "Currency you bill clients in",
    list(FOREX_DEFAULTS.keys()),
    index=0,
    help="Select the primary currency you invoice your foreign clients in.",
)

default_rate = FOREX_DEFAULTS[billing_currency]
forex_rate = st.sidebar.number_input(
    f"Average {billing_currency}/INR exchange rate",
    min_value=0.01,
    value=default_rate,
    step=0.50,
    help="Average conversion rate used when remittance was credited to your Indian bank account. Check your FIRC for actuals.",
)

foreign_receipts = st.sidebar.number_input(
    f"Total amount invoiced ({billing_currency})",
    min_value=0.0,
    value=12000.0 if billing_currency == "USD" else 10000.0,
    step=500.0,
    help="Total gross amount invoiced to all foreign clients during the financial year.",
)

receipts_inr = foreign_receipts * forex_rate

st.sidebar.info(f"**INR equivalent:** {money(receipts_inr)}")

additional_domestic_income = st.sidebar.number_input(
    "Domestic receipts (₹), if any",
    min_value=0.0,
    value=0.0,
    step=50000.0,
    help="Income from Indian clients, if any — billed directly in INR.",
)

receipts = receipts_inr + additional_domestic_income

st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 Tax Method")

use_44ada = st.sidebar.toggle(
    "Use 44ADA presumptive taxation",
    value=True,
    help="Under 44ADA, your taxable professional income is taken as 50% of gross receipts. No need to maintain books of accounts.",
)

expense_percent = st.sidebar.slider(
    "Actual expense % (if not using 44ADA)",
    min_value=0,
    max_value=90,
    value=30,
    help="Your actual business expenses as a percentage of gross receipts. Used when 44ADA is turned off and also for the comparison tab.",
)

cash_receipt_percent = st.sidebar.slider(
    "Cash receipt %",
    min_value=0,
    max_value=100,
    value=0,
    help="Export freelancers typically receive everything via bank (0% cash), which qualifies for the higher ₹75L threshold under 44ADA.",
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🔢 Other Inputs")

other_income = st.sidebar.number_input(
    "Other income (interest, capital gains, etc.)",
    min_value=0.0,
    value=0.0,
    step=10000.0,
)

tds = st.sidebar.number_input(
    "TDS / advance tax already paid",
    min_value=0.0,
    value=0.0,
    step=10000.0,
    help="Include TDS deducted by Indian clients, advance tax paid, and any self-assessment tax already deposited.",
)


# ─── Calculations ─────────────────────────────────────────────────────────────

freelancer_income, expenses = calculate_freelancer_income(receipts, use_44ada, expense_percent)
total_income = freelancer_income + other_income
tax_details = calculate_tax_details(total_income)
tax = tax_details["total_tax"]
net_tax = max(tax - tds, 0)
refund = max(tds - tax, 0)
effective_rate = (tax / total_income * 100) if total_income else 0
receipt_tax_rate = (tax / receipts * 100) if receipts else 0
take_home_after_tax = max(receipts + other_income - expenses - tax, 0)
gst_applicable = receipts > GST_EXPORT_THRESHOLD

comparison = build_comparison(receipts, expense_percent, other_income, tds)
selected_method = "44ADA presumptive" if use_44ada else "Actual expenses"
alternative_method = "Actual expenses" if use_44ada else "44ADA presumptive"
selected_tax = float(comparison.loc[comparison["Method"] == selected_method, "Total Tax"].iloc[0])
alternative_tax = float(comparison.loc[comparison["Method"] == alternative_method, "Total Tax"].iloc[0])
tax_difference = selected_tax - alternative_tax


# ─── Top Section: Money Flow Visual ──────────────────────────────────────────

st.markdown('<p class="export-header">💰 YOUR MONEY FLOW — FOREIGN CLIENT TO YOUR POCKET</p>', unsafe_allow_html=True)

flow_cols = st.columns(6)

flow_data = [
    ("1", "Foreign Invoice", money_fc(foreign_receipts, billing_currency)),
    ("2", f"× {billing_currency}/INR Rate", f"₹{forex_rate:,.2f}"),
    ("3", "Gross Receipts (INR)", money(receipts_inr)),
    ("4", f"+ Domestic Income", money(additional_domestic_income)),
    ("5", "Total Receipts", money(receipts)),
    ("6", "Your Tax", money(tax)),
]

for col, (num, label, value) in zip(flow_cols, flow_data):
    col.markdown(
        f"""
        <div class="flow-step">
            <div class="step-num">{num}</div><br>
            <span class="step-label">{label}</span><br>
            <span class="step-value">{value}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("")


# ─── Key Metrics ──────────────────────────────────────────────────────────────

st.markdown('<p class="export-header">📊 TAX SNAPSHOT</p>', unsafe_allow_html=True)

metric_cols = st.columns(5)
metric_cols[0].metric("Taxable Income", money(total_income))
metric_cols[1].metric("Estimated Tax", money(tax))
metric_cols[2].metric("Net Payable After TDS", money(net_tax))
metric_cols[3].metric("Refund Estimate", money(refund))
metric_cols[4].metric("Effective Tax Rate", percent(effective_rate))


# ─── Export GST Status ────────────────────────────────────────────────────────

st.markdown("")
gst_col1, gst_col2 = st.columns(2)

with gst_col1:
    st.markdown('<p class="export-header">🏷️ GST POSITION — EXPORT OF SERVICES</p>', unsafe_allow_html=True)
    if gst_applicable:
        st.markdown(
            f"""
            <div class="gst-box-warning">
                <strong>⚠️ GST Registration Required</strong><br>
                Your aggregate turnover of <strong>{money(receipts)}</strong> exceeds the ₹20L threshold.<br><br>
                <strong>As an export-of-service provider, you have two options:</strong>
                <ol style="margin: 8px 0 0 0; padding-left: 20px;">
                    <li><strong>LUT (Letter of Undertaking)</strong> — File LUT on GST portal → invoice at 0% GST → no GST to collect or pay. <em>Most freelancers prefer this.</em></li>
                    <li><strong>Pay IGST + claim refund</strong> — Charge 18% IGST on invoice → pay to govt → apply for refund. <em>Delays cash flow.</em></li>
                </ol>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        gst_gap = GST_EXPORT_THRESHOLD - receipts
        st.markdown(
            f"""
            <div class="gst-box">
                <strong>✅ GST Registration Not Yet Mandatory</strong><br>
                Your turnover is <strong>{money(gst_gap)}</strong> below the ₹20L threshold.<br><br>
                <em>Tip: Some export freelancers voluntarily register for GST to claim input tax credits on business expenses (laptop, software, coworking).</em>
            </div>
            """,
            unsafe_allow_html=True,
        )

with gst_col2:
    st.markdown('<p class="export-header">📑 44ADA ELIGIBILITY</p>', unsafe_allow_html=True)
    eligibility_tone, eligibility_message = explain_44ada_eligibility(receipts, cash_receipt_percent)

    if eligibility_tone == "success":
        st.success(eligibility_message)
    else:
        st.warning(eligibility_message)

    st.markdown(
        """
        <div class="info-card">
            <strong>Why 44ADA is popular with export freelancers:</strong><br>
            • Only 50% of receipts are taxed — the other 50% is deemed as expenses<br>
            • No need to maintain books of accounts<br>
            • No audit required if income declared ≥ 50%<br>
            • Export freelancers usually have low actual expenses → 44ADA saves time & money
        </div>
        """,
        unsafe_allow_html=True,
    )


# ─── Tabs ─────────────────────────────────────────────────────────────────────

lead_tab, dashboard_tab, explanation_tab, comparison_tab, planning_tab, compliance_tab = st.tabs(
    [
        "📞 Submit Details",
        "📊 Dashboard",
        "📖 Tax Explained",
        "⚖️ 44ADA vs Actual",
        "📅 Planning",
        "🌐 Export Compliance",
    ]
)


# ═══ SUBMIT DETAILS TAB ═══════════════════════════════════════════════════════

with lead_tab:
    st.markdown(
        """
        <div class="info-card">
            <strong>How this works:</strong><br>
            1️⃣ Share your tax details below<br>
            2️⃣ Our Chartered Accountant will analyze your specific situation<br>
            3️⃣ Book a consultation call to discuss optimization strategies<br><br>
            Your data helps us provide personalized advice during the consultation.
        </div>
        """,
        unsafe_allow_html=True,
    )

    lead_col1, lead_col2 = st.columns(2)
    name = lead_col1.text_input("Your name", key="lead_name")
    phone = lead_col2.text_input("Phone / WhatsApp number", key="lead_phone")

    service_type = st.selectbox(
        "Primary service type",
        [
            "IT / Software Development",
            "Design / Creative",
            "Consulting / Advisory",
            "Content / Writing",
            "Marketing / SEO",
            "Other Professional Services",
        ],
        key="lead_service_type",
    )

    notes = st.text_area(
        "What do you need help with?",
        placeholder="Example: I bill US clients in USD via Paypal. Need help with GST-LUT, advance tax, and ITR filing.",
        key="lead_notes",
    )

    if st.button("Submit Details to Chartered Accountant", key="lead_submit"):
        if not name or not phone:
            st.warning("Please enter both Name and Phone before submitting.")
        else:
            row_values = [
                datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
                name,
                phone,
                service_type,
                billing_currency,
                foreign_receipts,
                forex_rate,
                receipts_inr,
                additional_domestic_income,
                receipts,
                use_44ada,
                expense_percent,
                cash_receipt_percent,
                expenses,
                freelancer_income,
                other_income,
                total_income,
                tax,
                net_tax,
                refund,
                gst_applicable,
                notes or "",
            ]

            sheet_saved, sheet_message = append_row_to_google_sheet(row_values)
            st.caption(sheet_message)
            if sheet_saved:
                st.success("✅ Your details have been submitted to our Chartered Accountant for analysis!")
            else:
                st.warning(
                    "✅ Details submitted, but Google Sheets save encountered an issue."
                )

            st.markdown("**Your Tax Summary:**")

            summary_data = {
                "Detail": [
                    "Name",
                    "Phone",
                    "Service Type",
                    "Billing Currency",
                    "Foreign Receipts",
                    "INR Equivalent",
                    "Taxable Income",
                    "Estimated Tax",
                    "Net Payable",
                    "Refund Estimate",
                ],
                "Value": [
                    name,
                    phone,
                    service_type,
                    billing_currency,
                    money_fc(foreign_receipts, billing_currency),
                    money(receipts_inr),
                    money(total_income),
                    money(tax),
                    money(net_tax),
                    money(refund),
                ],
            }
            st.dataframe(pd.DataFrame(summary_data), hide_index=True, use_container_width=True)

            if notes:
                st.markdown(f"**Your Notes:** {notes}")

            st.markdown("---")
            st.markdown(
                """
                <div style="background: #f0f4ff; border-left: 4px solid #4f46e5; border-radius: 8px; padding: 16px 20px; margin: 16px 0;">
                    <strong>📅 Next Step: Book Your Consultation</strong><br>
                    Our CA will review your details and reach out with insights. You can also
                    <a href="https://prokhata.com/product/consultation-call-with-chartered-accountant/" target="_blank" style="color: #4f46e5; font-weight: 600; text-decoration: none;">
                        book a consultation call directly →
                    </a>
                </div>
                """,
                unsafe_allow_html=True,
            )


# ═══ DASHBOARD TAB ═════════════════════════════════════════════════════════════

with dashboard_tab:
    st.markdown('<p class="export-header">INCOME BREAKDOWN</p>', unsafe_allow_html=True)

    income_flow = pd.DataFrame(
        [
            {
                "Component": "Foreign receipts (INR)",
                "Amount": receipts_inr,
                "Meaning": f"{money_fc(foreign_receipts, billing_currency)} converted at ₹{forex_rate:,.2f}.",
            },
            {
                "Component": "Domestic receipts",
                "Amount": additional_domestic_income,
                "Meaning": "Income from Indian clients, if any.",
            },
            {
                "Component": "Total gross receipts",
                "Amount": receipts,
                "Meaning": "Base figure used for 44ADA, GST threshold, and receipt-level planning.",
            },
            {
                "Component": "Less: expenses / deemed",
                "Amount": -expenses,
                "Meaning": "Reduction from receipts before professional income is taxed.",
            },
            {
                "Component": "Professional income",
                "Amount": freelancer_income,
                "Meaning": "Taxable profit from freelancing before adding other income.",
            },
            {
                "Component": "Other income",
                "Amount": other_income,
                "Meaning": "Interest, rent, capital gains, or other income entered separately.",
            },
            {
                "Component": "Taxable income",
                "Amount": total_income,
                "Meaning": "Final amount on which the slab calculation starts.",
            },
        ]
    )

    st.markdown("**Horizontal view: how receipts become taxable income**")
    render_horizontal_bar_chart(income_flow, "Component", "Amount", "Meaning")
    render_dashboard_table(income_flow, ["Amount"])

    tax_waterfall = pd.DataFrame(
        [
            {
                "Component": "Slab tax",
                "Amount": tax_details["gross_tax"],
                "Meaning": "Tax before rebate, marginal relief, cess, and TDS.",
            },
            {
                "Component": "Less: 87A rebate",
                "Amount": -tax_details["rebate"],
                "Meaning": "Reduces tax when eligible income is within the rebate threshold.",
            },
            {
                "Component": "Less: marginal relief",
                "Amount": -tax_details["marginal_relief"],
                "Meaning": "Smooths tax when income is just above the rebate limit.",
            },
            {
                "Component": "Add: 4% cess",
                "Amount": tax_details["cess"],
                "Meaning": "Health and education cess added after rebate/relief.",
            },
            {
                "Component": "Less: TDS paid",
                "Amount": -tds,
                "Meaning": "Tax already paid or deducted; reduces final payable.",
            },
            {
                "Component": "Net payable",
                "Amount": net_tax,
                "Meaning": "Estimated amount still payable after TDS/advance tax.",
            },
        ]
    )

    st.markdown('<p class="export-header">TAX MOVEMENT</p>', unsafe_allow_html=True)
    st.markdown("**Horizontal view: what increases and reduces tax**")
    render_horizontal_bar_chart(tax_waterfall, "Component", "Amount", "Meaning")
    render_dashboard_table(tax_waterfall, ["Amount"])

    st.markdown('<p class="export-header">SLAB-WISE TAX CONTRIBUTION</p>', unsafe_allow_html=True)
    slab_chart = tax_details["breakup"].copy()
    slab_chart = slab_chart[slab_chart["Taxable Amount"] > 0]

    if slab_chart.empty:
        st.info("No taxable slab amount at this income level. Your income is within the tax-free limit.")
    else:
        slab_chart["Meaning"] = slab_chart.apply(
            lambda row: (
                f"{money(row['Taxable Amount'])} of your income falls in this slab "
                f"and is taxed at {row['Rate']}."
            ),
            axis=1,
        )
        st.markdown("**Horizontal view: which slab creates the tax**")
        render_horizontal_bar_chart(slab_chart, "Slab", "Tax", "Meaning")
        render_dashboard_table(slab_chart[["Slab", "Rate", "Taxable Amount", "Tax", "Meaning"]], ["Taxable Amount", "Tax"])


# ═══ EXPLANATION TAB ══════════════════════════════════════════════════════════

with explanation_tab:
    st.subheader("How This Calculation Works — For Export Freelancers")

    method_name = "44ADA presumptive" if use_44ada else "actual expense"

    st.markdown(
        f"""
        <div class="info-card">
            <strong>🔑 Key Point for Export Freelancers:</strong><br>
            Your foreign earnings (received in {billing_currency}) are fully taxable in India as a resident.
            The income is converted to INR at the exchange rate when received.
            Export of services is not exempt from income tax — it is only zero-rated for GST.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        **Step 1 · Convert foreign income to INR**

        - You invoiced: **{money_fc(foreign_receipts, billing_currency)}**
        - Exchange rate used: **₹{forex_rate:,.2f}** per {billing_currency}
        - INR equivalent: **{money(receipts_inr)}**
        - Domestic income added: **{money(additional_domestic_income)}**
        - Total gross receipts: **{money(receipts)}**
        """
    )

    st.markdown(
        f"""
        **Step 2 · Calculate professional income ({method_name} method)**

        - Gross receipts: **{money(receipts)}**
        - Expenses {"(50% deemed under 44ADA)" if use_44ada else f"({expense_percent}% actual)"}: **{money(expenses)}**
        - Professional income: **{money(freelancer_income)}**
        - Other income added: **{money(other_income)}**
        - **Taxable income: {money(total_income)}**
        """
    )

    st.markdown(
        f"""
        **Step 3 · Apply new regime slabs**

        Your slab tax before rebate, relief, and cess is **{money(tax_details["gross_tax"])}**.
        """
    )

    st.dataframe(
        format_money_columns(tax_details["breakup"], ["Taxable Amount", "Tax"]),
        hide_index=True,
        use_container_width=True,
    )

    st.markdown(
        f"""
        **Step 4 · Rebate, marginal relief, and cess**

        | Item | Amount |
        |------|--------|
        | Section 87A rebate | {money(tax_details["rebate"])} |
        | Marginal relief near ₹12L | {money(tax_details["marginal_relief"])} |
        | Tax after rebate/relief | {money(tax_details["tax_after_relief"])} |
        | Health & education cess (4%) | {money(tax_details["cess"])} |
        | **Total estimated tax** | **{money(tax)}** |
        """
    )

    st.info(
        "⚠️ This calculator handles normal slab income under the new regime. "
        "Special-rate income (capital gains), surcharge, DTAA treaty relief, foreign tax credit (FTC), "
        "and state-specific GST exceptions need separate review."
    )

    with st.expander("📚 Assumptions and references"):
        st.markdown(
            """
            - **New regime slabs:** Nil up to ₹4L → 5% → 10% → 15% → 20% → 25% → 30% above ₹24L
            - **Rebate:** Resident individual, normal income ≤ ₹12L → rebate up to ₹60,000
            - **44ADA:** Professional income = 50% of gross receipts
            - **44ADA threshold:** ₹50L normally, ₹75L if cash receipts ≤ 5% of total
            - **GST:** ₹20L aggregate turnover threshold; export of services is zero-rated
            - **Exchange rate:** Should match the rate on the date of receipt in your Indian bank (or FIRC rate)
            - **Advance tax:** Net liability > ₹10,000 → advance tax applies; presumptive payers → single instalment by 15 March
            """
        )


# ═══ COMPARISON TAB ═══════════════════════════════════════════════════════════

with comparison_tab:
    st.subheader("44ADA vs Actual Expense — Which Saves You More Tax?")

    st.markdown(
        """
        <div class="info-card">
            <strong>💡 Quick Rule of Thumb for Export Freelancers:</strong><br>
            Most export freelancers have <strong>low actual expenses</strong> (just a laptop, internet, and software subscriptions).
            If your actual expenses are below 50% of receipts, <strong>44ADA almost always saves more tax</strong> because it deems
            50% as expenses — giving you a higher deduction than your actual costs.
        </div>
        """,
        unsafe_allow_html=True,
    )

    comparison_display = format_money_columns(
        comparison,
        [
            "Allowed Expenses",
            "Professional Income",
            "Taxable Income",
            "Total Tax",
            "Payable After TDS",
            "Refund Estimate",
        ],
    )

    st.dataframe(comparison_display, hide_index=True, use_container_width=True)

    comparison_chart = comparison.melt(
        id_vars="Method",
        value_vars=["Professional Income", "Total Tax", "Payable After TDS"],
        var_name="Metric",
        value_name="Amount",
    )
    comparison_chart["Component"] = comparison_chart["Method"] + " - " + comparison_chart["Metric"]
    comparison_chart["Meaning"] = comparison_chart.apply(
        lambda row: f"{row['Metric']} using the {row['Method']} method.",
        axis=1,
    )
    render_horizontal_bar_chart(comparison_chart, "Component", "Amount", "Meaning")

    if tax_difference > 0:
        st.warning(
            f"💸 **{alternative_method}** saves you **{money(abs(tax_difference))}** compared to {selected_method} with current inputs."
        )
    elif tax_difference < 0:
        st.success(
            f"✅ **{selected_method}** is already saving you **{money(abs(tax_difference))}** compared to {alternative_method}."
        )
    else:
        st.info("Both methods produce the same estimated tax with the current inputs.")


# ═══ PLANNING TAB ═════════════════════════════════════════════════════════════

with planning_tab:
    st.subheader("Tax Planning — Export Freelancer Edition")

    plan_cols = st.columns(4)
    plan_cols[0].metric("Tax as % of Receipts", percent(receipt_tax_rate))
    plan_cols[1].metric("Take-Home After Tax", money(take_home_after_tax))
    plan_cols[2].metric("Expense Ratio Used", percent((expenses / receipts * 100) if receipts else 0))
    plan_cols[3].metric("TDS Coverage", percent((tds / tax * 100) if tax else 0))

    st.markdown("")
    st.markdown('<p class="export-header">📅 ADVANCE TAX SCHEDULE</p>', unsafe_allow_html=True)

    schedule = advance_tax_schedule(net_tax, use_44ada)
    st.dataframe(
        format_money_columns(schedule, ["Suggested Payment"]),
        hide_index=True,
        use_container_width=True,
    )

    if use_44ada:
        st.info("💡 Under 44ADA, you need to pay 100% advance tax in a **single instalment by 15 March**. Set a calendar reminder!")
    else:
        if net_tax > ADVANCE_TAX_TRIGGER:
            st.info("💡 Since you're not under 44ADA, advance tax is due in **4 quarterly instalments** (Jun, Sep, Dec, Mar).")

    st.markdown("")
    st.markdown('<p class="export-header">✅ ACTION CHECKLIST</p>', unsafe_allow_html=True)

    suggestions = []

    # Export-specific suggestions
    suggestions.append("🏦 **FIRC Tracking:** Collect Foreign Inward Remittance Certificates from your bank for every payment received.")
    suggestions.append("💱 **Exchange Rate:** Use the actual TT buying rate on the date of receipt for accurate income computation.")

    if gst_applicable:
        suggestions.append("📋 **GST-LUT:** File Letter of Undertaking (Form GST RFD-11) on the GST portal before April 1. Renew annually.")
        suggestions.append("🧾 **Export Invoices:** Issue GST invoices with '0% IGST — supply under LUT' for each foreign client payment.")
        suggestions.append("📤 **GSTR-1 Filing:** Report your export invoices in GSTR-1 with 'Exports — with LUT' category.")

    if not use_44ada and expense_percent < 50:
        suggestions.append("💡 **Consider 44ADA:** Your expense percentage is below 50% — 44ADA may give you a higher deduction automatically.")

    if use_44ada and receipts > 5000000 and cash_receipt_percent > 5:
        suggestions.append("⚠️ **44ADA Cap:** Cash receipts > 5% limits the threshold to ₹50L. Verify your eligibility.")

    if use_44ada and receipts > 7500000 and cash_receipt_percent <= 5:
        suggestions.append("⚠️ **High Receipts:** Above ₹75L — verify books and tax audit requirements even under 44ADA.")

    if net_tax > ADVANCE_TAX_TRIGGER:
        suggestions.append(f"📅 **Advance Tax Due:** Net tax of {money(net_tax)} exceeds ₹10,000 — plan your advance tax deposits.")

    if total_income > 5000000:
        suggestions.append("📈 **Surcharge Review:** Income above ₹50L — review surcharge and marginal relief (not computed in this calculator).")

    if tax_details["marginal_relief"] > 0:
        suggestions.append("🎯 **Marginal Relief Active:** Your income is near the ₹12L rebate cliff — marginal relief is reducing your tax.")

    if refund > 0:
        suggestions.append("💰 **TDS Refund Expected:** Check Form 26AS/AIS before filing your return to claim the refund.")

    suggestions.append("📁 **Record Keeping:** Keep contracts, invoices, bank statements, and FIRC copies for at least 6 years.")

    for suggestion in suggestions:
        st.markdown(suggestion)


# ═══ EXPORT COMPLIANCE TAB ════════════════════════════════════════════════════

with compliance_tab:
    st.subheader("🌐 Export of Services — Compliance Essentials")

    st.markdown(
        """
        <div class="info-card">
            <strong>What is "Export of Services" under GST?</strong><br>
            When you provide services (IT, design, consulting, writing, etc.) to clients located
            <strong>outside India</strong> and receive payment <strong>in foreign exchange</strong>,
            your supply qualifies as an <strong>export of services</strong> under IGST Act Section 2(6).<br><br>
            <strong>Important:</strong> Export of services is <strong>zero-rated</strong> (0% GST) — not exempt.
            This distinction matters because zero-rated lets you claim input tax credits.
        </div>
        """,
        unsafe_allow_html=True,
    )

    comp_col1, comp_col2 = st.columns(2)

    with comp_col1:
        st.markdown("#### 🏷️ GST — Your Options")
        st.markdown(
            """
            | Option | How It Works | Best For |
            |--------|-------------|----------|
            | **LUT (Most Common)** | File LUT annually → Invoice at 0% GST → No GST to pay | Freelancers with low domestic expenses |
            | **Pay IGST + Refund** | Charge 18% IGST → Pay to govt → Apply for refund | Freelancers with significant input credits |
            | **Not Registered** | No GST filing needed | Turnover below ₹20L |
            """
        )

        st.markdown("#### 📋 LUT Checklist")
        lut_items = [
            "File **Form GST RFD-11** on GST portal before 1 April each year",
            "Keep **FIRC / bank realization certificates** for each receipt",
            "Mention **LUT ARN number** on all export invoices",
            "Report export invoices in **GSTR-1** under 'Exports — with LUT'",
            "File **GSTR-3B** monthly/quarterly with zero tax on exports",
        ]
        for item in lut_items:
            st.markdown(f"- {item}")

    with comp_col2:
        st.markdown("#### 🏦 FEMA / RBI Compliance")
        st.markdown(
            """
            As a freelancer receiving foreign exchange, you must comply with FEMA:
            """
        )
        fema_items = [
            "**FIRC Collection:** Get Foreign Inward Remittance Certificate from your bank for every payment",
            "**Purpose Code:** Ensure bank credits use correct purpose code (P0802 for IT services, P0805 for consulting, etc.)",
            "**Repatriation Timeline:** Foreign exchange should be received within the timelines per RBI guidelines",
            "**No Form 15CA/CB:** These forms are for **outward** remittances — NOT needed for receiving money from abroad",
            "**Bank Account:** Maintain an EEFC (Exchange Earner's Foreign Currency) account if you want to retain some forex",
        ]
        for item in fema_items:
            st.markdown(f"- {item}")

        st.markdown("#### 🌍 Double Tax Avoidance (DTAA)")
        st.markdown(
            """
            - If your foreign client's country **deducts withholding tax**, you may be eligible for
              **Foreign Tax Credit (FTC)** under India's DTAA
            - File **Form 67** before the due date of your return to claim FTC
            - The credit is limited to the lower of: foreign tax paid or Indian tax on that income
            """
        )

    st.markdown("---")
    st.markdown("#### 📌 Common Mistakes by Export Freelancers")

    mistakes_col1, mistakes_col2 = st.columns(2)

    with mistakes_col1:
        st.markdown(
            """
            **❌ Thinking export income is tax-free**
            > Export income is fully taxable under income tax. Only GST is zero-rated.

            **❌ Not collecting FIRCs**
            > FIRCs are your proof of foreign exchange receipt — needed for GST, IT, and FEMA compliance.

            **❌ Missing LUT renewal**
            > LUT expires on 31 March. If not renewed, your exports may attract 18% IGST.
            """
        )

    with mistakes_col2:
        st.markdown(
            """
            **❌ Wrong exchange rate**
            > Use the TT buying rate on the date of receipt, not the date of invoice.

            **❌ Not filing advance tax**
            > No TDS on foreign income = full tax liability is on you. Plan advance tax.

            **❌ Ignoring Form 67 for FTC**
            > If foreign tax was withheld, you lose the credit without Form 67.
            """
        )






# ─── Footer ──────────────────────────────────────────────────────────────────

st.markdown("---")
st.markdown(
    f"""
    <div style="text-align: center; color: #64748b; font-size: 0.85rem; padding: 10px 0;">
        🌍 <strong>Export Freelancer Tax Calculator</strong> · Powered by CA Rajat Agrawal · {tax_year}<br>
        Educational estimate only — verify final return positions before filing<br>
        <span style="font-size: 0.78rem; color: #94a3b8;">Income Tax · GST · FEMA · 44ADA · Advance Tax</span>
    </div>
    """,
    unsafe_allow_html=True,
)
