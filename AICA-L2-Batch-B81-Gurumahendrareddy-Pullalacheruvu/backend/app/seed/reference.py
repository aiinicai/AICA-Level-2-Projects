"""Reference data: chart of accounts, glossary definitions, alert rules.

Kept separate from the transaction generator because this part is real
configuration — it ships with the product regardless of which dataset is
loaded.
"""
from __future__ import annotations

from app.models import BurnCategory, CostNature

# --------------------------------------------------------------------------
# Chart of accounts — (name, parent_group, classification, sub_type,
#                      burn_category, cost_nature, is_cash)
# --------------------------------------------------------------------------
CHART_OF_ACCOUNTS: list[tuple] = [
    # Cash & bank
    ("HDFC Bank - Operating",        "Bank Accounts",      "asset", "bank",       None, None, True),
    ("ICICI Bank - Collections",     "Bank Accounts",      "asset", "bank",       None, None, True),
    ("Axis Bank - Payroll",          "Bank Accounts",      "asset", "bank",       None, None, True),
    ("HDFC Fixed Deposit (Lien)",    "Deposits",           "asset", "bank",       None, None, True),
    ("Petty Cash",                   "Cash-in-Hand",       "asset", "cash",       None, None, True),
    # Receivables / payables
    ("Sundry Debtors",               "Current Assets",     "asset", "receivable", None, None, False),
    ("Sundry Creditors",             "Current Liabilities","liability", "payable", None, None, False),
    # Statutory
    ("GST Payable",                  "Duties & Taxes",     "liability", "statutory", BurnCategory.STATUTORY, CostNature.VARIABLE, False),
    ("TDS Payable",                  "Duties & Taxes",     "liability", "statutory", BurnCategory.STATUTORY, CostNature.VARIABLE, False),
    ("PF Payable",                   "Duties & Taxes",     "liability", "statutory", BurnCategory.STATUTORY, CostNature.FIXED, False),
    ("ESI Payable",                  "Duties & Taxes",     "liability", "statutory", BurnCategory.STATUTORY, CostNature.FIXED, False),
    ("Professional Tax Payable",     "Duties & Taxes",     "liability", "statutory", BurnCategory.STATUTORY, CostNature.FIXED, False),
    ("Advance Tax",                  "Duties & Taxes",     "asset", "statutory",  BurnCategory.STATUTORY, CostNature.VARIABLE, False),
    # Borrowings
    ("Venture Debt - Alteria",       "Loans (Liability)",  "liability", "loan",   BurnCategory.FINANCE_COST, CostNature.FIXED, False),
    ("Working Capital OD - HDFC",    "Loans (Liability)",  "liability", "loan",   BurnCategory.FINANCE_COST, CostNature.FIXED, False),
    # Equity
    ("Share Capital",                "Capital Account",    "equity", "other",     None, None, False),
    ("Securities Premium",           "Capital Account",    "equity", "other",     None, None, False),
    # Income
    ("Product Subscription Revenue", "Sales Accounts",     "income", "other",     None, None, False),
    ("Implementation & Services",    "Sales Accounts",     "income", "other",     None, None, False),
    ("AMC & Support Revenue",        "Sales Accounts",     "income", "other",     None, None, False),
    ("Interest Income",              "Indirect Income",    "income", "other",     None, None, False),
    # People
    ("Salaries - Engineering",       "Employee Cost",      "expense", "other", BurnCategory.PEOPLE, CostNature.FIXED, False),
    ("Salaries - Sales & Marketing", "Employee Cost",      "expense", "other", BurnCategory.PEOPLE, CostNature.FIXED, False),
    ("Salaries - Operations",        "Employee Cost",      "expense", "other", BurnCategory.PEOPLE, CostNature.FIXED, False),
    ("Salaries - G&A",               "Employee Cost",      "expense", "other", BurnCategory.PEOPLE, CostNature.FIXED, False),
    ("Employer PF & ESI",            "Employee Cost",      "expense", "other", BurnCategory.PEOPLE, CostNature.FIXED, False),
    ("Staff Welfare",                "Employee Cost",      "expense", "other", BurnCategory.PEOPLE, CostNature.DISCRETIONARY, False),
    ("Recruitment Fees",             "Employee Cost",      "expense", "other", BurnCategory.PEOPLE, CostNature.DISCRETIONARY, False),
    ("Gratuity & Leave Provision",   "Employee Cost",      "expense", "other", BurnCategory.PEOPLE, CostNature.FIXED, False),
    # Technology
    ("AWS Cloud Hosting",            "Technology Cost",    "expense", "other", BurnCategory.TECH, CostNature.VARIABLE, False),
    ("Software Subscriptions",       "Technology Cost",    "expense", "other", BurnCategory.TECH, CostNature.FIXED, False),
    ("Data & API Licences",          "Technology Cost",    "expense", "other", BurnCategory.TECH, CostNature.VARIABLE, False),
    ("Security & Compliance Tools",  "Technology Cost",    "expense", "other", BurnCategory.TECH, CostNature.FIXED, False),
    # Delivery / COGS
    ("Contractor & Freelance Cost",  "Direct Expenses",    "expense", "other", BurnCategory.DELIVERY, CostNature.VARIABLE, False),
    ("Hardware & Sensor Purchases",  "Direct Expenses",    "expense", "other", BurnCategory.DELIVERY, CostNature.VARIABLE, False),
    ("Field Installation Cost",      "Direct Expenses",    "expense", "other", BurnCategory.DELIVERY, CostNature.VARIABLE, False),
    ("Travel - Client Delivery",     "Direct Expenses",    "expense", "other", BurnCategory.DELIVERY, CostNature.VARIABLE, False),
    # Facilities
    ("Office Rent",                  "Administrative",     "expense", "other", BurnCategory.FACILITIES, CostNature.FIXED, False),
    ("Electricity & Utilities",      "Administrative",     "expense", "other", BurnCategory.FACILITIES, CostNature.FIXED, False),
    ("Housekeeping & Security",      "Administrative",     "expense", "other", BurnCategory.FACILITIES, CostNature.FIXED, False),
    ("Repairs & Maintenance",        "Administrative",     "expense", "other", BurnCategory.FACILITIES, CostNature.VARIABLE, False),
    # Marketing
    ("Digital Marketing",            "Selling Expenses",   "expense", "other", BurnCategory.MARKETING, CostNature.DISCRETIONARY, False),
    ("Events & Conferences",         "Selling Expenses",   "expense", "other", BurnCategory.MARKETING, CostNature.DISCRETIONARY, False),
    ("Content & Brand",              "Selling Expenses",   "expense", "other", BurnCategory.MARKETING, CostNature.DISCRETIONARY, False),
    # Professional
    ("Legal & Secretarial",          "Professional Fees",  "expense", "other", BurnCategory.PROFESSIONAL, CostNature.VARIABLE, False),
    ("Audit & Tax Fees",             "Professional Fees",  "expense", "other", BurnCategory.PROFESSIONAL, CostNature.FIXED, False),
    ("Consultancy Charges",          "Professional Fees",  "expense", "other", BurnCategory.PROFESSIONAL, CostNature.DISCRETIONARY, False),
    # Finance
    ("Interest on Venture Debt",     "Finance Cost",       "expense", "other", BurnCategory.FINANCE_COST, CostNature.FIXED, False),
    ("Bank Charges",                 "Finance Cost",       "expense", "other", BurnCategory.FINANCE_COST, CostNature.FIXED, False),
    ("Processing & Facility Fees",   "Finance Cost",       "expense", "other", BurnCategory.FINANCE_COST, CostNature.VARIABLE, False),
    # Other
    ("Insurance",                    "Administrative",     "expense", "other", BurnCategory.OTHER, CostNature.FIXED, False),
    ("Miscellaneous Expenses",       "Administrative",     "expense", "other", BurnCategory.OTHER, CostNature.DISCRETIONARY, False),
]


# --------------------------------------------------------------------------
# Glossary (SPEC 12D). Every argument about a number traces back to here.
# --------------------------------------------------------------------------
DEFINITIONS: list[dict] = [
    dict(term="Gross Burn", category="Burn",
         plain_english="Every rupee that left the bank in the month, before counting anything that came in.",
         formula="Sum of all cash outflows in the month",
         basis_help="Excludes non-cash charges such as depreciation and provisions."),
    dict(term="Net Burn", category="Burn",
         plain_english="What the month actually cost us after customers paid. This is the number runway is built on.",
         formula="Gross Burn − Cash Collections received in the month",
         basis_help="Reported as a 3-month average by default, so one heavy month does not distort it. One-off items are excluded when 'normalised' is shown."),
    dict(term="Normalised Net Burn", category="Burn",
         plain_english="Net burn with one-off items stripped out, so it reflects what a typical month costs.",
         formula="Net Burn − one-off outflows + one-off inflows, over the same period",
         basis_help="An item is one-off only when someone has explicitly classified it, and that person's name is shown against it."),
    dict(term="Runway", category="Runway",
         plain_english="How many months the unrestricted cash lasts at the burn rate assumed.",
         formula="Cash Available ÷ Net Burn per month",
         basis_help="Cash Available excludes restricted balances. Undrawn credit is NOT included unless the scenario says so."),
    dict(term="Cash-Out Date", category="Runway",
         plain_english="The date the unrestricted cash reaches zero if nothing changes.",
         formula="As-on date + Runway months",
         basis_help="Calculated on the current run-rate scenario unless another scenario is selected."),
    dict(term="Fundraise Trigger Date", category="Runway",
         plain_english="The date by which we must start raising, given how long a round takes to close.",
         formula="Cash-Out Date − fundraise lead time (default 6 months)",
         basis_help="Lead time is configurable in Setup."),
    dict(term="Cash Available", category="Liquidity",
         plain_english="Money we can actually spend today.",
         formula="Total bank and cash balances − restricted or encumbered balances",
         basis_help="Restricted includes lien-marked deposits, margin money and balances earmarked under a facility."),
    dict(term="Restricted Cash", category="Liquidity",
         plain_english="Cash on the balance sheet that we are not free to use.",
         formula="Sum of balances flagged restricted, with the reason recorded against each",
         basis_help="Every restricted balance must carry a reason. A balance with no reason is treated as available."),
    dict(term="Days Cash on Hand", category="Liquidity",
         plain_english="How many days of normal operating spend the available cash covers.",
         formula="Cash Available ÷ (Gross Burn ÷ 30)",
         basis_help="Uses the 3-month average gross burn."),
    dict(term="Cash Conversion Cycle", category="Liquidity",
         plain_english="How long our money is tied up between paying for something and being paid for it.",
         formula="DSO + Inventory Days − DPO",
         basis_help="A negative number means suppliers fund us."),
    dict(term="DSO", category="Receivables",
         plain_english="On average, how many days customers take to pay us.",
         formula="(Receivables ÷ Credit Sales for the period) × days in period",
         basis_help="Disputed invoices are included in receivables but reported separately."),
    dict(term="Weighted Collectible", category="Receivables",
         plain_english="What we actually expect to receive, not what is billed — each invoice discounted by how likely it is to arrive.",
         formula="Σ (Invoice outstanding × collection probability)",
         basis_help="Probability comes from the customer's own payment history unless a person has overridden it."),
    dict(term="Statutory Dues Cover", category="Payables",
         plain_english="Whether we have the cash set aside for taxes falling due.",
         formula="Cash earmarked for statutory ÷ Statutory dues in the next 30 days",
         basis_help="Below 1.00 means a funding gap. Statutory dues are first-charge and carry penal interest."),
    dict(term="Committed but Not Yet Billed", category="Payables",
         plain_english="Money we have already promised to spend that has not reached the books because no invoice has arrived.",
         formula="Σ (Commitment total value − consumed to date)",
         basis_help="Maintained manually. Cancellable and non-cancellable are reported separately."),
    dict(term="Liquidity Health Score", category="Liquidity",
         plain_english="A single 0–100 read on whether the cash position is structurally sound, built from five components.",
         formula="Weighted: Runway 30 · Days Cash on Hand 20 · Statutory Cover 20 · Receivables Quality 15 · Concentration & Structure 15",
         basis_help="Strong 80+ · Adequate 65–79 · Tight 45–64 · Critical below 45. Each component's contribution is always shown."),
    dict(term="Minimum Cash Floor", category="Runway",
         plain_english="The balance below which we do not let cash fall — one payroll plus statutory dues plus a buffer.",
         formula="Set manually in Setup",
         basis_help="Breaching the floor is a red condition, not an amber one."),
    dict(term="Timing Variance", category="Plan vs Actual",
         plain_english="A difference that reverses — the money still arrives or still leaves, just in a different month.",
         formula="Classified manually when explaining a variance",
         basis_help="Shown in a distinct shade on the waterfall because it does not change the full-year position."),
    dict(term="Forecast Accuracy", category="Forecast",
         plain_english="How wrong our weekly cash forecast has been recently. It tells you how much to trust the grid.",
         formula="Mean absolute % difference between forecast closing cash and actual closing cash over the last 8 weeks",
         basis_help="Computed from forecasts as they stood at the time, never re-forecast with hindsight."),
]


# --------------------------------------------------------------------------
# The ten alert rules the CFO asked for (SPEC 12C)
# --------------------------------------------------------------------------
ALERT_RULES: list[dict] = [
    dict(code="runway_below_months", name="Runway below threshold",
         description="Fires when runway on the current run-rate falls below the set number of months.",
         threshold=9.0, threshold_unit="months", severity="Red", channels="sms,email",
         cooldown_hours=24, escalate_after_hours=12),
    dict(code="cash_below_amount", name="Cash below floor",
         description="Fires when freely available cash falls below the amount set.",
         threshold=20000000.0, threshold_unit="inr", severity="Red", channels="sms,email",
         cooldown_hours=12, escalate_after_hours=6),
    dict(code="statutory_unfunded_within_days", name="Statutory dues unfunded",
         description="Fires when a statutory due falling within the window has no cash earmarked against it.",
         threshold=10.0, threshold_unit="days", severity="Red", channels="sms",
         cooldown_hours=24, escalate_after_hours=24),
    dict(code="payables_exceed_receivables_due", name="Payables exceed receivables due",
         description="Fires when payables due in the next 30 days exceed weighted collectible in the same window.",
         threshold=1.0, threshold_unit="ratio", severity="Amber", channels="sms",
         cooldown_hours=72, escalate_after_hours=0),
    dict(code="plan_variance_above_pct", name="Plan variance breach",
         description="Fires when month-to-date cash variance against the active plan exceeds the set percentage.",
         threshold=10.0, threshold_unit="pct", severity="Amber", channels="sms,email",
         cooldown_hours=168, escalate_after_hours=0),
    dict(code="client_above_pct_of_receivables", name="Client concentration",
         description="Fires when a single client accounts for more than the set share of total receivables.",
         threshold=25.0, threshold_unit="pct", severity="Amber", channels="sms",
         cooldown_hours=168, escalate_after_hours=0),
    dict(code="covenant_headroom_below_pct", name="Covenant headroom thin",
         description="Fires before a covenant breaches, when headroom drops below the set percentage.",
         threshold=15.0, threshold_unit="pct", severity="Amber", channels="sms,email",
         cooldown_hours=72, escalate_after_hours=24),
    dict(code="books_bank_difference_above", name="Books vs bank difference",
         description="Fires when the unreconciled difference between books and bank exceeds the amount set.",
         threshold=500000.0, threshold_unit="inr", severity="Amber", channels="email",
         cooldown_hours=24, escalate_after_hours=0),
    dict(code="data_not_updated_for_hours", name="Data stale",
         description="Fires when the accounting sync has not succeeded within the set number of hours.",
         threshold=48.0, threshold_unit="hours", severity="Grey", channels="email",
         cooldown_hours=24, escalate_after_hours=0),
    dict(code="cashout_moved_more_than_days", name="Cash-out date moved",
         description="Fires when the cash-out date shifts by more than the set number of days within one week.",
         threshold=14.0, threshold_unit="days", severity="Red", channels="sms,email",
         cooldown_hours=168, escalate_after_hours=12),
]


# --------------------------------------------------------------------------
# Pre-built scenarios always available (SPEC 8)
# --------------------------------------------------------------------------
PREBUILT_SCENARIOS: list[dict] = [
    dict(name="Base", sort_order=1,
         note="What we currently expect: collections at plan, hiring per plan, no new funding.",
         levers=dict(top_client_delay_days=0, collections_pct_of_plan=100, hiring="plan",
                     discretionary_cut_pct=0, funding_slip_months=0, new_funding_amount=0,
                     new_funding_date=None, revenue_pct_of_plan=100, price_increase_pct=0)),
    dict(name="Best", sort_order=2,
         note="Collections land early and in full, one price increase sticks, hiring stays on plan.",
         levers=dict(top_client_delay_days=-10, collections_pct_of_plan=110, hiring="plan",
                     discretionary_cut_pct=0, funding_slip_months=0, new_funding_amount=0,
                     new_funding_date=None, revenue_pct_of_plan=110, price_increase_pct=5)),
    dict(name="Worst", sort_order=3,
         note="Top client slips a full quarter, collections at 80% of plan, no cost action taken.",
         levers=dict(top_client_delay_days=90, collections_pct_of_plan=80, hiring="plan",
                     discretionary_cut_pct=0, funding_slip_months=6, new_funding_amount=0,
                     new_funding_date=None, revenue_pct_of_plan=85, price_increase_pct=0)),
    dict(name="Board Plan", sort_order=4,
         note="The plan as approved by the board in April 2026.",
         levers=dict(top_client_delay_days=0, collections_pct_of_plan=100, hiring="plan",
                     discretionary_cut_pct=0, funding_slip_months=0, new_funding_amount=0,
                     new_funding_date=None, revenue_pct_of_plan=100, price_increase_pct=0)),
    dict(name="Survival", sort_order=5,
         note="What it takes to reach 18 months: hiring frozen, discretionary spend halved, collections chased hard.",
         levers=dict(top_client_delay_days=0, collections_pct_of_plan=105, hiring="freeze",
                     discretionary_cut_pct=50, funding_slip_months=0, new_funding_amount=0,
                     new_funding_date=None, revenue_pct_of_plan=100, price_increase_pct=0)),
]
