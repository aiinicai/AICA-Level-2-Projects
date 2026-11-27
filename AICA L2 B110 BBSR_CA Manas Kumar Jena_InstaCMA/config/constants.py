"""
InstaCMA - accounting constants and CMA head taxonomy.

Every line of a client's Profit & Loss and Balance Sheet is mapped to one of
the canonical CMA heads defined here.  The projection engine, the bank-test
engine and the Excel/Word generators all work on these keys.
"""

APP_NAME = "InstaCMA"
APP_VERSION = "1.0.0"
APP_TAGLINE = "Offline CMA data preparation, projections and bank-test assessment"

# --------------------------------------------------------------------------
# Constitutions and their default treatment
# --------------------------------------------------------------------------
CONSTITUTIONS = [
    "Proprietorship",
    "Partnership Firm",
    "LLP",
    "Private Limited Company",
    "Public Limited Company",
    "HUF",
    "Trust / Society",
]

# Default income-tax rate charged in the entity's own P&L (0 = taxed in the
# hands of the owner, so no provision is made in the business accounts).
DEFAULT_TAX_RATE = {
    "Proprietorship": 0.0,
    "Partnership Firm": 0.312,
    "LLP": 0.312,
    "Private Limited Company": 0.2517,
    "Public Limited Company": 0.2517,
    "HUF": 0.0,
    "Trust / Society": 0.0,
}

# Label used for owner withdrawals in each constitution
DRAWINGS_LABEL = {
    "Proprietorship": "Drawings",
    "Partnership Firm": "Partners' Withdrawals",
    "LLP": "Partners' Withdrawals",
    "Private Limited Company": "Dividend",
    "Public Limited Company": "Dividend",
    "HUF": "Karta / Member Withdrawals",
    "Trust / Society": "Application of Funds (Withdrawals)",
}

NATURES = ["Trading", "Manufacturing", "Service", "Contractor"]

FACILITIES = ["Both", "Cash Credit", "Term Loan"]
TL_METHODS = ["Equal EMI", "Equal Principal"]
TL_USES = ["Capex", "Working capital"]

# --------------------------------------------------------------------------
# Canonical CMA heads
#   key, label, statement, section, default basis
#   basis for P&L expenses : "V" variable with sales, "F" fixed (held)
#   basis for BS items      : "S" scales with sales, "H" held flat
#   "C" = computed by the engine (never a free input in projected years)
# --------------------------------------------------------------------------
PL_HEADS = [
    # key,             label,                                         section,      basis
    ("sales",          "Revenue from Operations (Net Sales)",          "income",     "C"),
    ("other_income",   "Other Income",                                 "income",     "F"),
    ("opening_stock",  "Opening Stock",                                "cogs",       "C"),
    ("purchases",      "Purchases / Raw Material Consumed",            "cogs",       "C"),
    ("wages",          "Direct Wages / Labour",                        "direct",     "V"),
    ("power_fuel",     "Power & Fuel",                                 "direct",     "V"),
    ("other_direct",   "Freight, Carriage & Other Direct Expenses",    "direct",     "V"),
    ("closing_stock",  "Closing Stock",                                "cogs",       "C"),
    ("salary",         "Salaries & Staff Welfare",                     "indirect",   "V"),
    ("rent",           "Rent",                                         "indirect",   "F"),
    ("admin_exp",      "Administrative & Office Expenses",             "indirect",   "V"),
    ("selling_exp",    "Selling & Distribution Expenses",              "indirect",   "V"),
    ("repairs",        "Repairs & Maintenance",                        "indirect",   "V"),
    ("audit_fee",      "Audit & Professional Fees",                    "indirect",   "F"),
    ("insurance",      "Insurance",                                    "indirect",   "F"),
    ("bank_charges",   "Bank Charges",                                 "indirect",   "V"),
    ("misc_exp",       "Miscellaneous Expenses",                       "indirect",   "V"),
    ("interest",       "Interest on Borrowings",                       "finance",    "C"),
    ("depreciation",   "Depreciation",                                 "finance",    "C"),
    ("tax",            "Provision for Income Tax",                     "tax",        "C"),
]

DIRECT_KEYS = ["wages", "power_fuel", "other_direct"]
INDIRECT_KEYS = ["salary", "rent", "admin_exp", "selling_exp", "repairs",
                 "audit_fee", "insurance", "bank_charges", "misc_exp"]

FA_CLASSES = [
    # key,            label,                          default WDV rate
    ("fa_building",  "Land & Building (WDV)",          0.10),
    ("fa_plant",     "Plant & Machinery (WDV)",        0.15),
    ("fa_furniture", "Furniture & Fixtures (WDV)",     0.10),
    ("fa_vehicle",   "Vehicles (WDV)",                 0.15),
    ("fa_computer",  "Computers (WDV)",                0.40),
    ("fa_other",     "Other Fixed Assets (WDV)",       0.15),
]
FA_KEYS = [k for k, _, _ in FA_CLASSES]
FA_RATE_DEFAULT = {k: r for k, _, r in FA_CLASSES}

BS_LIAB_HEADS = [
    ("capital",          "Capital / Share Capital",                    "owners",    "C"),
    ("reserves",         "Reserves & Surplus / Retained Profit",       "owners",    "C"),
    ("unsecured_loans",  "Unsecured Loans (Promoters / Relatives)",    "long",      "H"),
    ("term_loans",       "Term Loans - Existing",                      "long",      "C"),
    ("new_term_loan",    "Term Loan - Proposed",                       "long",      "C"),
    ("cc",               "Cash Credit / Overdraft (Bank)",             "bank",      "C"),
    ("creditors",        "Sundry Creditors (Trade)",                   "current",   "C"),
    ("statutory_dues",   "Statutory Dues (GST / TDS Payable)",         "current",   "S"),
    ("other_cl",         "Other Current Liabilities & Provisions",     "current",   "S"),
]

BS_ASSET_HEADS = [(k, l, "fixed", "C") for k, l, _ in FA_CLASSES] + [
    ("investments",      "Investments",                                "noncurrent", "H"),
    ("loans_advances",   "Loans, Advances & Deposits",                 "noncurrent", "H"),
    ("stock",            "Inventory / Stock-in-Trade",                 "current",    "C"),
    ("debtors",          "Sundry Debtors (Trade Receivables)",         "current",    "C"),
    ("other_ca",         "Other Current Assets (GST / TDS Receivable)", "current",   "S"),
    ("cash_in_hand",     "Cash in Hand",                               "current",    "S"),
    ("bank_balance",     "Balance with Banks",                         "current",    "C"),
]

# Extra items read from the capital account (not balance-sheet totals)
CAPITAL_MOVEMENT_HEADS = [
    ("drawings",           "Drawings / Dividend / Withdrawals"),
    ("capital_introduced", "Capital Introduced during the year"),
]

ALL_HEADS = ([(k, l) for k, l, _, _ in PL_HEADS] +
             [(k, l) for k, l, _, _ in BS_LIAB_HEADS] +
             [(k, l) for k, l, _, _ in BS_ASSET_HEADS] +
             CAPITAL_MOVEMENT_HEADS)
HEAD_LABEL = dict(ALL_HEADS)

LIAB_KEYS = [k for k, _, _, _ in BS_LIAB_HEADS]
ASSET_KEYS = [k for k, _, _, _ in BS_ASSET_HEADS]
PL_KEYS = [k for k, _, _, _ in PL_HEADS]

DEFAULT_BASIS = {k: b for k, _, _, b in PL_HEADS}
DEFAULT_BASIS.update({k: b for k, _, _, b in BS_LIAB_HEADS})
DEFAULT_BASIS.update({k: b for k, _, _, b in BS_ASSET_HEADS})

# Items whose projection basis the user may switch (V/F or S/H)
SWITCHABLE_PL = ["other_income"] + DIRECT_KEYS + INDIRECT_KEYS
SWITCHABLE_BS = ["unsecured_loans", "statutory_dues", "other_cl",
                 "investments", "loans_advances", "other_ca", "cash_in_hand"]

# --------------------------------------------------------------------------
# Keyword taxonomy used by the mapper (lower-case; first match wins in order)
# --------------------------------------------------------------------------
KEYWORD_RULES = [
    # capital account movements first (they sit inside the capital block)
    ("drawings",           ["drawing", "withdrawal", "dividend paid", "dividend"]),
    ("capital_introduced", ["introduced", "capital introduced", "addition to capital", "capital added", "fresh capital"]),
    # P&L
    ("opening_stock",  ["opening stock", "opening inventory", "stock at the beginning", "op. stock", "op stock"]),
    ("closing_stock",  ["closing stock", "closing inventory", "stock at the end", "cl. stock", "cl stock"]),
    ("sales",          ["sales", "turnover", "revenue from operation", "receipts from contract",
                        "contract receipt", "service income", "income from services", "gross receipts",
                        "job work income", "fees received", "revenue"]),
    ("other_income",   ["other income", "interest received", "interest income", "discount received",
                        "commission received", "rent received", "misc income", "miscellaneous income",
                        "dividend received", "profit on sale"]),
    ("purchases",      ["purchase", "raw material", "material consumed", "cost of material",
                        "consumption"]),
    ("salary",         ["salary and wages", "salaries and wages", "salary & wages", "salaries & wages"]),
    ("wages",          ["wages", "labour", "labor", "direct salary", "contract labour"]),
    ("power_fuel",     ["power", "fuel", "electricity charges factory", "diesel"]),
    ("other_direct",   ["carriage inward", "freight inward", "freight", "carriage", "cartage",
                        "loading", "unloading", "transport", "packing", "job work", "manufacturing",
                        "factory", "direct expense", "consumable", "stores", "sub-contract",
                        "subcontract"]),
    ("interest",       ["interest", "finance cost", "finance charges"]),
    ("bank_charges",   ["bank charge", "bank commission", "processing fee", "bg commission"]),
    ("depreciation",   ["depreciation", "amortisation", "amortization"]),
    ("tax",            ["provision for tax", "income tax", "current tax", "deferred tax", "tax expense"]),
    ("audit_fee",      ["audit fee", "audit", "auditor", "auditors", "professional fee", "legal",
                        "consultancy", "accounting charges", "professional charges"]),
    ("salary",         ["salary", "salaries", "staff", "bonus", "remuneration", "employee",
                        "esi", "epf", "provident fund", "gratuity"]),
    ("rent",           ["rent", "lease rent", "godown rent", "shop rent"]),
        ("insurance",      ["insurance"]),
    ("selling_exp",    ["advertisement", "advertising", "selling", "sales promotion", "commission paid",
                        "discount allowed", "freight outward", "carriage outward", "business promotion",
                        "distribution"]),
    ("repairs",        ["repair", "maintenance"]),
    ("admin_exp",      ["telephone", "mobile", "internet", "printing", "stationery", "postage",
                        "courier", "travelling", "travel", "conveyance", "electricity", "office",
                        "vehicle running", "vehicle expense", "fuel for vehicle", "rates and taxes",
                        "rates & taxes", "licence", "license", "fees and subscription", "subscription",
                        "newspaper", "general expense", "administrative", "computer expense",
                        "software", "donation", "charity", "development", "hire charges"]),
    ("misc_exp",       ["miscellaneous", "misc", "sundry expense", "other expense",
                        "preliminary", "written off", "round off"]),
    # Balance sheet - priority phrases that contain words of other heads
    ("bank_balance",   ["cash at bank", "cash with bank", "balance with bank", "balances with bank",
                        "bank balance", "current account with"]),
    ("loans_advances", ["security dep", "sec. dep", "loans and advances", "loans & advances", "long-term loans & advances",
                        "short-term loans & advances", "long term loans and advances"]),
    ("other_cl",       ["creditors for expenses", "creditors for expense", "creditors for capital goods"]),
    # Balance sheet - liabilities
    ("capital",        ["capital account", "proprietor", "proprietor's capital", "partners capital",
                        "partners' capital", "share capital", "capital", "owners fund", "corpus"]),
    ("reserves",       ["reserve", "surplus", "retained earning", "profit and loss account",
                        "p & l account", "p&l a/c", "general reserve"]),
    ("cc",             ["cash credit", "overdraft", "o/d", "od account", "cc account", "cc limit",
                        "working capital loan", "wcdl", "packing credit", "bank borrowing",
                        "secured loan from bank - cc"]),
    ("term_loans",     ["term loan", "vehicle loan", "car loan", "machinery loan", "secured loan",
                        "secured", "mudra", "gecl", "ecgls", "loan from bank", "loan from nbfc", "hypothecation loan"]),
    ("unsecured_loans",["unsecured loan", "unsecured", "loan from directors", "loans from directors", "loan from director", "loan from relative", "loan from partner",
                        "loan from family", "loans from friends", "inter corporate deposit", "deposits from"]),
    ("creditors",      ["sundry creditor", "creditors", "trade payable", "payable for goods",
                        "creditors for goods", "accounts payable"]),
    ("statutory_dues", ["gst payable", "tds payable", "duties and taxes", "duties & taxes",
                        "statutory", "pf payable", "esi payable", "professional tax payable",
                        "output gst", "output cgst", "output sgst", "output igst"]),
    ("other_cl",       ["outstanding", "expenses payable", "provision", "advance from customer",
                        "advance received", "other current liabilities", "other liabilities", "other payable",
                        "salary payable", "audit fee payable", "creditors for expenses"]),
    # Balance sheet - assets
    ("fa_building",    ["land", "building", "shed", "premises"]),
    ("fa_plant",       ["plant", "machinery", "machine", "equipment", "tools"]),
    ("fa_furniture",   ["furniture", "fixture", "fittings", "interior"]),
    ("fa_vehicle",     ["vehicle", "car", "motor", "two wheeler", "two-wheeler", "scooter",
                        "truck", "tractor", "bike"]),
    ("fa_computer",    ["computer", "laptop", "printer", "server", "software"]),
    ("fa_other",       ["fixed asset", "net block", "air conditioner", "mobile phone", "electrical",
                        "inverter", "cctv", "other asset"]),
    ("investments",    ["investment", "fixed deposit", "fdr", "mutual fund", "shares in", "nsc",
                        "lic policy", "kvp"]),
    ("stock",          ["stock", "inventory", "inventories", "stock-in-trade", "work in progress",
                        "finished goods"]),
    ("debtors",        ["sundry debtor", "debtors", "trade receivable", "receivable from customers",
                        "book debts", "accounts receivable"]),
    ("loans_advances", ["security deposit", "deposit", "loans and advances", "loans & advances",
                        "advance to", "advance paid", "advance for", "prepaid", "earnest money", "emd"]),
    ("other_ca",       ["gst receivable", "input tax credit", "itc", "tds receivable", "tcs receivable",
                        "advance tax", "income tax refund", "gst input", "input cgst", "input sgst",
                        "input igst", "other current asset", "receivable"]),
    ("cash_in_hand",   ["cash in hand", "cash on hand", "cash balance", "petty cash", "cash"]),
    ("bank_balance",   ["bank", "current account", "savings account", "balance with"]),
]

# Words that mark a line as a total / heading (ignored by the mapper)
TOTAL_MARKERS = ["as certified", "certified by", "(as certified", "total", "grand total", "sub total", "subtotal", "gross profit",
                 "net profit", "net loss", "balance c/d", "balance b/d", "particulars",
                 "liabilities", "assets", "income", "expenditure", "c/f", "b/f",
                 "profit before", "profit after", "excess of"]

# Sheet / page classifiers
PL_MARKERS = ["profit and loss", "profit & loss", "trading account", "income and expenditure",
              "income & expenditure", "statement of profit", "p&l", "p & l", "sales", "purchases",
              "gross profit", "net profit"]
BS_MARKERS = ["balance sheet", "liabilities", "assets", "capital account", "sundry debtors",
              "sundry creditors", "fixed assets", "current assets", "current liabilities"]

# --------------------------------------------------------------------------
# Defaults for intake (all overridable on the Intake page and in Settings)
# --------------------------------------------------------------------------
DEFAULTS = {
    "n_estimated": 1,
    "n_projected": 2,
    "sales_growth": 0.20,             # 120% of previous year
    "cc_rate": 0.10,
    "tl_rate": 0.105,
    "tl_tenure_months": 60,
    "tl_moratorium_months": 6,
    "existing_tl_rate": 0.10,
    "unsecured_loan_rate": 0.0,
    "dscr_min": 1.50,
    "dscr_max": 2.50,
    "turnover_fail_below": 4.0,
    "turnover_pass_from": 5.0,
    "stock_margin": 0.25,
    "debtor_margin": 0.25,
    "deduct_creditors": True,
    "debtors_over_90_pct": 0.0,
    "dp_buffer": 0.02,
    "debtor_days_cap": 90,
    "stock_days_trading": 45,
    "stock_days_mfg": 60,
    "creditor_days": 30,
    "creditor_days_service": 20,
    "debtor_days_default": 45,
}

STATUS_PASS = "PASS"
STATUS_AMBER = "AMBER"
STATUS_FAIL = "FAIL"

DISCLAIMER = (
    "DISCLAIMER & LIMITATIONS: The estimated and projected figures in this CMA data are prepared "
    "by InstaCMA from the actual / audited financial statements and the assumptions entered by "
    "the preparer. Projections are forward-looking estimates; actual results will differ and the "
    "differences may be material. The bank tests (drawing power, turnover method, DSCR) are computed "
    "on the basis stated in the workbook; the lending bank's own policy prevails. The preparer must "
    "verify the source figures and the reasonableness of every assumption before submission."
)
