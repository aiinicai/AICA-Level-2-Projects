"""Creates small SAP-style test files locally. Run: py generate_dummy_data.py"""
from pathlib import Path
import numpy as np
import pandas as pd

rng = np.random.default_rng(42)
out = Path("dummy_data"); out.mkdir(exist_ok=True)
ledgers = [("400000", "Sales - Domestic", "H"), ("500100", "Purchases - Raw Material", "S"), ("650100", "Travelling Expenses", "S"), ("113100", "HDFC Bank - Current A/c", "S")]
rows = []
for i in range(250):
    date = pd.Timestamp("2025-04-01") + pd.Timedelta(days=int(rng.integers(0, 365)))
    code, name, side = ledgers[i % len(ledgers)]
    amount = round(float(rng.integers(5_000, 500_000)), 2)
    rows.append({"Document Number": f"{100000000+i}", "Document Type": ["SA", "KR", "RV", "KZ"][i%4], "Posting Date": date,
                 "G/L Account": code, "G/L Account Name": name, "Customer/Vendor Name": f"Party {i%15+1}",
                 "Text": "Dummy entry for testing", "Amount in Local Currency": amount, "Debit/Credit Ind.": side})
daybook = pd.DataFrame(rows)
daybook.to_excel(out / "Dummy_Day_Book.xlsx", index=False)
tb = daybook.assign(Debit=lambda x: np.where(x["Debit/Credit Ind."]=="S", x["Amount in Local Currency"], 0), Credit=lambda x: np.where(x["Debit/Credit Ind."]=="H", x["Amount in Local Currency"], 0)).groupby(["G/L Account", "G/L Account Name"], as_index=False)[["Debit", "Credit"]].sum()
tb["Balance Carried Forward"] = 0; tb["Cumulative Balance"] = tb["Debit"] - tb["Credit"]
tb.rename(columns={"G/L Account": "G/L Account", "G/L Account Name": "G/L Account Name", "Debit": "Debit (Report Period)", "Credit": "Credit (Report Period)"}).to_excel(out / "Dummy_TB.xlsx", index=False)
print("Created dummy_data/Dummy_Day_Book.xlsx and dummy_data/Dummy_TB.xlsx")
