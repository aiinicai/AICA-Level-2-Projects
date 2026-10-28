"""
Generates sample_data/sample_financials.xlsx — a realistic 3-year dataset for
"ABC Manufacturing Pvt Ltd" (₹ in Lakhs), designed to trip several variance
flags and produce an interesting demo (grey-zone Z-score, elevated receivables).
Run once:  python make_sample_data.py
"""

import pandas as pd

# key: (CY, PY, PY2)  — ₹ in Lakhs
FIG = {
    "Revenue from Operations":            (4820, 4150, 3900),
    "Other Income":                       (95,   40,   35),
    "Cost of Materials / Purchases":      (3160, 2620, 2470),
    "Employee Benefit Expenses":          (610,  540,  505),
    "Finance Costs":                      (185,  120,  110),
    "Depreciation & Amortisation":        (140,  150,  145),
    "Other / SG&A Expenses":              (520,  430,  400),
    "Profit Before Tax":                  (300,  330,  305),
    "Tax Expense":                        (78,   86,   80),
    "Profit After Tax":                   (222,  244,  225),
    "Share Capital":                      (250,  250,  250),
    "Reserves & Surplus":                 (1445, 1268, 1069),
    "Long-term Borrowings":               (620,  450,  480),
    "Short-term Borrowings":              (410,  260,  240),
    "Trade Payables":                     (560,  505,  470),
    "Other Current Liabilities":          (160,  140,  130),
    "Provisions":                         (75,   70,   65),
    "Property, Plant & Equipment (Net)":  (1310, 1220, 1195),
    "Non-current Investments":            (110,  105,  100),
    "Other Non-current Assets":           (95,   80,   75),
    "Inventories":                        (640,  520,  495),
    "Trade Receivables":                  (1180, 755,  640),
    "Cash & Bank Balances":               (85,   178,  119),
    "Short-term Loans & Advances":        (65,   55,   50),
    "Other Current Assets":               (35,   30,   30),
}

STMT = {k: ("P&L" if i < 10 else "BS") for i, k in enumerate(FIG)}

rows = [{"Statement": STMT[k], "Line Item": k,
         "Current Year": v[0], "Previous Year": v[1],
         "Year Before Previous (optional)": v[2]} for k, v in FIG.items()]

pd.DataFrame(rows).to_excel("sample_data/sample_financials.xlsx",
                            sheet_name="Financials", index=False)
print("sample_data/sample_financials.xlsx written.")
