"""
config.py  -  All audit thresholds and keywords in one place.
Change values here (or from the app sidebar) as per law / client / materiality.
Thresholds as per Income-tax Act, 1961 (FY 2025-26 position). Verify before use.
"""

DEFAULT_CONFIG = {
    # ---------- Tally connection ----------
    "tally_host": "http://localhost",
    "tally_port": 9000,

    # ---------- Cash rules ----------
    "cash_payment_limit_40A3": 10000,        # Sec 40A(3): cash payment to a person in a day > 10,000
    "cash_receipt_limit_269ST": 200000,      # Sec 269ST: cash receipt >= 2,00,000 from a person in a day
    "cash_loan_limit_269SS_T": 20000,        # Sec 269SS / 269T: cash loan/deposit taken or repaid >= 20,000

    # ---------- TDS (single / aggregate per party per FY) ----------
    "tds_rules": {
        "194C": {"label": "Contract / Job work / Freight", "single": 30000, "aggregate": 100000,
                 "keywords": ["contract", "job work", "jobwork", "labour", "labor", "freight",
                              "transport", "repair", "cartage", "carriage", "advertis", "catering", "printing"]},
        "194J": {"label": "Professional / Technical fees", "single": 50000, "aggregate": 50000,
                 "keywords": ["professional", "legal", "audit fee", "consult", "technical",
                              "retainer", "architect", "director sitting"]},
        "194I": {"label": "Rent", "single": 50000, "aggregate": 600000,   # 50,000 per month
                 "keywords": ["rent", "lease", "hire charges"]},
        "194H": {"label": "Commission / Brokerage", "single": 20000, "aggregate": 20000,
                 "keywords": ["commission", "brokerage"]},
    },

    # ---------- General scrutiny ----------
    "materiality_amount": 500000,            # entries above this are listed as 'material'
    "round_sum_min": 25000,                  # round-figure check applies at/above this amount
    "round_sum_multiple": 1000,              # amount exactly divisible by this = 'round sum'
    "duplicate_window_days": 7,              # same party + same amount within N days
    "min_narration_length": 5,
    "outlier_zscore": 3.0,                   # amount > mean + z*SD within the same ledger
    "ai_contamination": 0.02,                # Isolation Forest: expected share of anomalies
    "holidays": [],                          # list of "YYYY-MM-DD" (Sundays are checked automatically)

    # Words in ledger/narration that point to possible disallowance (Sec 37(1), 40(a), 43B etc.)
    "disallowance_keywords": [
        "penalty", "fine", "late fee", "interest on tds", "interest on gst", "interest on income tax",
        "donation", "personal", "gift", "bribe", "compounding", "income tax", "advance tax",
        "prior period", "household", "school fee", "club",
    ],
}

# Tally reserved / primary group names used for classification
GROUPS = {
    "cash": ["Cash-in-Hand", "Cash-in-hand"],
    "bank": ["Bank Accounts", "Bank OD A/c", "Bank OCC A/c"],
    "debtor": ["Sundry Debtors"],
    "creditor": ["Sundry Creditors"],
    "loan_liability": ["Loans (Liability)", "Unsecured Loans", "Secured Loans"],
    "loan_asset": ["Loans & Advances (Asset)"],
    "expense": ["Indirect Expenses", "Direct Expenses", "Purchase Accounts"],
    "income": ["Sales Accounts", "Direct Incomes", "Indirect Incomes"],
    "duties": ["Duties & Taxes"],
    "capital": ["Capital Account"],
    "fixed_asset": ["Fixed Assets"],
}
