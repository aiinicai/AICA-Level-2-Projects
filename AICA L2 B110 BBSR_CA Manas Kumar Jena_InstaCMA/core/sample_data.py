"""
Sample clients used by the demo buttons and the automated tests.

1. M/S Sample Publication House - proprietorship, trading; the figures follow the
   layout of the firm's CMA format file (names changed for the demo).
2. Kalinga Agro Foods Private Limited - fictional manufacturing company.
"""
from core.models import CMAProject, Intake, SourceLine, YearDef, YearInput, ExistingLoan

# (statement, label, head, section, {fy: amount})
TRADING_LINES = [
    ("PL", "Opening Stock", "opening_stock", "", {2024: 41003, 2025: 65280, 2026: 112560}),
    ("PL", "Purchases", "purchases", "", {2024: 5323599, 2025: 835941, 2026: 17984153}),
    ("PL", "Carriage Inward", "other_direct", "trading", {2024: 32480, 2025: 15460, 2026: 56840}),
    ("PL", "Sales", "sales", "", {2024: 6857464, 2025: 1772005, 2026: 18885385}),
    ("PL", "Closing Stock", "closing_stock", "", {2024: 65280, 2025: 112560, 2026: 1062681}),
    ("PL", "Staff Salary", "salary", "pl", {2024: 760000, 2025: 421600, 2026: 460000}),
    ("PL", "Labour Expenses", "wages", "pl", {2024: 110600, 2025: 65210, 2026: 86520}),
    ("PL", "House Rent", "rent", "pl", {2024: 132000, 2025: 132000, 2026: 132000}),
    ("PL", "Telephone Expenses", "admin_exp", "pl", {2024: 8620, 2025: 7420, 2026: 12560}),
    ("PL", "Travelling & Conveyance", "admin_exp", "pl", {2024: 6140, 2025: 6240, 2026: 9860}),
    ("PL", "Electricity Charges", "admin_exp", "pl", {2024: 10680, 2025: 11260, 2026: 12410}),
    ("PL", "Bank Interest", "interest", "", {2024: 0, 2025: 0, 2026: 0}),
    ("PL", "Bank Charges", "bank_charges", "pl", {2024: 2140, 2025: 2240, 2026: 3560}),
    ("PL", "Legal Expenses", "audit_fee", "pl", {2024: 8000, 2025: 8000, 2026: 8000}),
    ("PL", "Audit Fees", "audit_fee", "pl", {2024: 2000, 2025: 2000, 2026: 6000}),
    ("PL", "Newspaper & Periodicals", "admin_exp", "pl", {2024: 1460, 2025: 1320, 2026: 1420}),
    ("PL", "Printing & Stationery", "admin_exp", "pl", {2024: 2140, 2025: 1620, 2026: 2140}),
    ("PL", "Development Expenses", "admin_exp", "pl", {2024: 5260, 2025: 4860, 2026: 12640}),
    ("PL", "Repair & Maintenance", "repairs", "pl", {2024: 4260, 2025: 3110, 2026: 8620}),
    ("PL", "Depreciation", "depreciation", "", {2024: 15192, 2025: 12914, 2026: 11063}),
    ("PL", "Misc. Expenses", "misc_exp", "pl", {2024: 3120, 2025: 2450, 2026: 3140}),
    ("BS", "Capital Account", "capital", "", {2024: 1939300, 2025: 2004940, 2026: 2669520}),
    ("BS", "Less: Drawings", "drawings", "", {2024: 280000, 2025: 220000, 2026: 360000}),
    ("BS", "Cash Credit Loan", "cc", "", {2024: 0, 2025: 0, 2026: 0}),
    ("BS", "Sundry Creditors", "creditors", "", {2024: 3448888, 2025: 1692786, 2026: 347880}),
    ("BS", "Audit Fees Payable", "other_cl", "", {2024: 2000, 2025: 2000, 2026: 6000}),
    ("BS", "GST Payable", "statutory_dues", "", {2024: 0, 2025: 0, 2026: 0}),
    ("BS", "Furniture & Fixture", "fa_furniture", "", {2024: 18146, 2025: 16431, 2026: 14888}),
    ("BS", "Machinery", "fa_plant", "", {2024: 40633, 2025: 34538, 2026: 29357}),
    ("BS", "Two Wheeler", "fa_vehicle", "", {2024: 34030, 2025: 28926, 2026: 24587}),
    ("BS", "Sundry Debtors", "debtors", "", {2024: 51210, 2025: 62480, 2026: 78520}),
    ("BS", "Security Dep. - Telephone Authority", "loans_advances", "", {2024: 3000, 2025: 3000, 2026: 3000}),
    ("BS", "Security Dep. - Sales Tax Authority", "loans_advances", "", {2024: 2000, 2025: 2000, 2026: 2000}),
    ("BS", "GST Receivable", "other_ca", "", {2024: 112640, 2025: 86520, 2026: 183774}),
    ("BS", "TDS Receivable", "other_ca", "", {2024: 107826, 2025: 40389, 2026: 355241}),
    ("BS", "Cash at Bank", "bank_balance", "", {2024: 4928583, 2025: 3281662, 2026: 1224092}),
    ("BS", "Cash in Hand", "cash_in_hand", "", {2024: 26840, 2025: 31220, 2026: 45260}),
]
TRADING_NP = {2024: 454050, 2025: 285640, 2026: 1024580}

KALINGA_LINES = [
    ("PL", "Revenue from Operations", "sales", "", {2025: 41000000, 2026: 46500000}),
    ("PL", "Other Income", "other_income", "", {2025: 120000, 2026: 140000}),
    ("PL", "Opening Stock", "opening_stock", "", {2025: 4200000, 2026: 4800000}),
    ("PL", "Raw Material Purchased", "purchases", "", {2025: 29000000, 2026: 33000000}),
    ("PL", "Factory Wages", "wages", "trading", {2025: 1800000, 2026: 2050000}),
    ("PL", "Power & Fuel", "power_fuel", "trading", {2025: 950000, 2026: 1080000}),
    ("PL", "Freight Inward & Packing", "other_direct", "trading", {2025: 650000, 2026: 720000}),
    ("PL", "Closing Stock", "closing_stock", "", {2025: 4800000, 2026: 5500000}),
    ("PL", "Salaries, Bonus & Staff Welfare", "salary", "pl", {2025: 2400000, 2026: 2650000}),
    ("PL", "Rent", "rent", "pl", {2025: 360000, 2026: 360000}),
    ("PL", "Office & Administrative Expenses", "admin_exp", "pl", {2025: 640000, 2026: 710000}),
    ("PL", "Selling & Distribution Expenses", "selling_exp", "pl", {2025: 1200000, 2026: 1380000}),
    ("PL", "Repairs & Maintenance", "repairs", "pl", {2025: 280000, 2026: 310000}),
    ("PL", "Auditor's Remuneration", "audit_fee", "pl", {2025: 120000, 2026: 130000}),
    ("PL", "Insurance", "insurance", "pl", {2025: 110000, 2026: 120000}),
    ("PL", "Bank Charges & Commission", "bank_charges", "pl", {2025: 60000, 2026: 70000}),
    ("PL", "Miscellaneous Expenses", "misc_exp", "pl", {2025: 130000, 2026: 140000}),
    ("PL", "Finance Costs", "interest", "", {2025: 1150000, 2026: 1100000}),
    ("PL", "Depreciation & Amortisation", "depreciation", "", {2025: 1240000, 2026: 1130000}),
    ("PL", "Current Tax", "tax", "", {2025: 410000, 2026: 602000}),
    ("BS", "Equity Share Capital", "capital", "", {2025: 5000000, 2026: 5000000}),
    ("BS", "Reserves & Surplus", "reserves", "", {2025: 3820000, 2026: 5608000}),
    ("BS", "Loan from Directors (Unsecured)", "unsecured_loans", "", {2025: 1200000, 2026: 1200000}),
    ("BS", "Term Loan from Bank of India", "term_loans", "", {2025: 4600000, 2026: 3800000}),
    ("BS", "Cash Credit from Bank of India", "cc", "", {2025: 6000000, 2026: 7000000}),
    ("BS", "Trade Payables", "creditors", "", {2025: 2800000, 2026: 3100000}),
    ("BS", "Duties & Taxes Payable", "statutory_dues", "", {2025: 340000, 2026: 390000}),
    ("BS", "Other Current Liabilities & Provisions", "other_cl", "", {2025: 460000, 2026: 510000}),
    ("BS", "Factory Land & Building", "fa_building", "", {2025: 4800000, 2026: 4560000}),
    ("BS", "Plant & Machinery", "fa_plant", "", {2025: 7200000, 2026: 6520000}),
    ("BS", "Furniture & Fixtures", "fa_furniture", "", {2025: 420000, 2026: 380000}),
    ("BS", "Vehicles", "fa_vehicle", "", {2025: 900000, 2026: 765000}),
    ("BS", "Computers", "fa_computer", "", {2025: 110000, 2026: 75000}),
    ("BS", "Long-term Loans & Advances / Deposits", "loans_advances", "", {2025: 650000, 2026: 720000}),
    ("BS", "Trade Receivables", "debtors", "", {2025: 4400000, 2026: 6100000}),
    ("BS", "GST & TDS Receivable", "other_ca", "", {2025: 520000, 2026: 580000}),
    ("BS", "Cash on Hand", "cash_in_hand", "", {2025: 130000, 2026: 140000}),
    ("BS", "Balances with Banks", "bank_balance", "", {2025: 290000, 2026: 1268000}),
]
KALINGA_NP = {2025: 1220000, 2026: 1788000}


def _build(lines, np_, intake, years, inputs=None):
    from analysis.layout import SINGLE_HEADS
    p = CMAProject()
    p.intake = intake
    p.years = years
    for st, label, head, section, amounts in lines:
        for fy, amt in amounts.items():
            p.source_lines.append(SourceLine(year=fy, statement=st, label=label, amount=float(amt), head=head,
                                             confidence=100, source="sample", section=section))
    for fy, v in np_.items():
        p.source_lines.append(SourceLine(year=fy, statement="PL", label="Net Profit", amount=float(v),
                                         head="_reported_net_profit", confidence=100, source="sample"))
    p.build_lines_from_sources(SINGLE_HEADS)
    for yi in inputs or []:
        p.inputs.append(yi)
    return p


def sample_trading():
    it = Intake(client_name="M/S SAMPLE PUBLICATION HOUSE", signatory_name="Mrs A. Sample",
                signatory_title="Proprietor", constitution="Proprietorship", nature="Trading",
                address="PLOT NO-1, SAMPLE NAGAR, BHUBANESWAR", bank_name="State Bank of India",
                branch="Sahid Nagar", case_type="Fresh", place="Bhubaneswar", preparation_date="2026-11-15",
                has_cc=True, cc_limit=5000000, cc_rate=0.10, stock_margin=0.25, debtor_margin=0.25,
                has_tl=True, tl_amount=500000, tl_rate=0.118, tl_tenure_months=60, tl_moratorium_months=0,
                tl_method="Equal EMI", tl_purpose="Purchase of furniture and fixtures", tl_use="Capex",
                tl_capex_class="fa_furniture", gst_turnover={"2024": 6857464, "2025": 1772005, "2026": 18885385})
    years = [YearDef(2024, "Audited"), YearDef(2025, "Audited"), YearDef(2026, "Provisional"),
             YearDef(2027, "Estimated"), YearDef(2028, "Projected"), YearDef(2029, "Projected"),
             YearDef(2030, "Projected")]
    inputs = [YearInput(2029, cc_limit=6000000), YearInput(2030, cc_limit=7000000)]
    return _build(TRADING_LINES, TRADING_NP, it, years, inputs)


def sample_company():
    it = Intake(client_name="KALINGA AGRO FOODS PRIVATE LIMITED", signatory_name="Director",
                signatory_title="Director", constitution="Private Limited Company", nature="Manufacturing",
                address="Industrial Estate, Khurda, Odisha", bank_name="Bank of India", branch="Khurda",
                case_type="Enhancement", place="Bhubaneswar", preparation_date="2026-11-27", has_cc=True,
                cc_existing_limit=7000000, cc_limit=9000000, cc_rate=0.095, has_tl=True, tl_amount=2500000,
                tl_rate=0.0975, tl_tenure_months=84, tl_moratorium_months=6, tl_method="Equal Principal",
                tl_purpose="Purchase of packing machinery", tl_use="Capex", tl_capex_class="fa_plant",
                gst_turnover={"2025": 41000000, "2026": 47950000})
    years = [YearDef(2025, "Audited"), YearDef(2026, "Audited"), YearDef(2027, "Estimated"),
             YearDef(2028, "Projected"), YearDef(2029, "Projected"), YearDef(2030, "Projected")]
    p = _build(KALINGA_LINES, KALINGA_NP, it, years)
    tl = p.lines_of("term_loans")[0]
    p.loans = [ExistingLoan(line_id=tl.id, lender="Bank of India", emi=90000, rate=0.095, end_date="2031-03-31")]
    return p
