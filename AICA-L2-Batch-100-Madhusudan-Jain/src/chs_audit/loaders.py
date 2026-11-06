"""Load the society workbook and minutes into a single dataclass."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

DATE_COLS = {
    "Members": ["member_since"],
    "Maintenance_Bills": ["bill_date", "due_date"],
    "Receipts": ["receipt_date"],
    "Bank_Statement": ["txn_date"],
    "Expenses": ["invoice_date", "payment_date"],
    "Other_Income": ["date"],
}


@dataclass
class SocietyData:
    members: pd.DataFrame
    bills: pd.DataFrame
    receipts: pd.DataFrame
    bank: pd.DataFrame
    vendors: pd.DataFrame
    expenses: pd.DataFrame
    other_income: pd.DataFrame
    funds: pd.DataFrame
    compliance_master: pd.DataFrame
    minutes: dict[str, str] = field(default_factory=dict)

    def fund(self, item_prefix: str) -> float:
        row = self.funds[self.funds["item"].str.startswith(item_prefix)]
        return float(row["amount"].iloc[0]) if len(row) else 0.0

    def earmarked_fd(self) -> float:
        """Fixed deposits earmarked for the sinking fund, whichever bank holds them."""
        it = self.funds["item"].astype(str).str.lower()
        rows = self.funds[it.str.startswith("fixed deposit") & it.str.contains("sinking")]
        return float(rows["amount"].sum()) if len(rows) else 0.0

    def master(self, item_prefix: str):
        row = self.compliance_master[self.compliance_master["item"].str.startswith(item_prefix)]
        return row["value"].iloc[0] if len(row) else None


def load(data_dir: Path) -> SocietyData:
    xl = pd.read_excel(data_dir / "society_data.xlsx", sheet_name=None)
    if "Other_Income" not in xl:   # optional sheet
        xl["Other_Income"] = pd.DataFrame(columns=["date", "head", "nature", "gross_amount", "tds", "mutual", "section_hint"])
    for sheet, cols in DATE_COLS.items():
        for c in cols:
            xl[sheet][c] = pd.to_datetime(xl[sheet][c]).dt.date
    minutes = {}
    mdir = data_dir / "minutes"
    if mdir.exists():
        for p in sorted(mdir.glob("*.txt")):
            minutes[p.name] = p.read_text(encoding="utf-8")
    return SocietyData(
        members=xl["Members"], bills=xl["Maintenance_Bills"], receipts=xl["Receipts"],
        bank=xl["Bank_Statement"], vendors=xl["Vendors"], expenses=xl["Expenses"],
        other_income=xl["Other_Income"], funds=xl["Fund_Balances"],
        compliance_master=xl["Compliance_Master"], minutes=minutes,
    )
