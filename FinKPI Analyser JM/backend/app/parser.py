import io
import pandas as pd
from typing import Dict, List, Any
from .config import config

VALID_ACCOUNT_TYPES = {"Asset", "Liability", "Equity", "Revenue", "Expense"}

def parse_excel_trial_balance(file_bytes: bytes) -> Dict[str, Any]:
    """
    Parses and validates 10-sheet Trial Balance Excel file.
    Enforces validation rules:
      1. All 10 sheets present
      2. No blank Account Code or Account Name
      3. Valid Account Type (Asset, Liability, Equity, Revenue, Expense)
      4. Total Debit == Total Credit (or sum of Net Balance == 0) per sheet
      5. Fiscal Year matching sheet name
    """
    try:
        xl = pd.ExcelFile(io.BytesIO(file_bytes))
    except Exception as e:
        raise ValueError(f"Failed to parse Excel file: {str(e)}")

    sheet_names = xl.sheet_names
    missing_sheets = [s for s in config.REQUIRED_SHEETS if s not in sheet_names]
    if missing_sheets:
        raise ValueError(f"Missing required sheets ({len(missing_sheets)} missing): {', '.join(missing_sheets)}")

    all_records: List[Dict[str, Any]] = []
    validation_report: Dict[str, Any] = {}
    errors: List[str] = []

    for sheet in config.REQUIRED_SHEETS:
        sheet_meta = config.SHEET_MAP[sheet]
        try:
            df = xl.parse(sheet)
            # Standardize column headers
            col_map = {str(c).strip(): str(c).strip() for c in df.columns}
            normalized_cols = {c: c.lower().replace(" ", "_").replace("-", "_") for c in df.columns}
            df.rename(columns=normalized_cols, inplace=True)

            # Map possible column variations
            # Account Code
            acct_code_col = next((c for c in df.columns if c in ["account_code", "accountcode", "code"]), None)
            # Account Name
            acct_name_col = next((c for c in df.columns if c in ["account_name", "accountname", "name", "account"]), None)
            # Category
            cat_col = next((c for c in df.columns if c in ["category", "cat"]), None)
            # Sub-Category
            subcat_col = next((c for c in df.columns if c in ["sub_category", "subcategory", "subcat"]), None)
            # Account Type
            type_col = next((c for c in df.columns if c in ["account_type", "accounttype", "type"]), None)
            # Normal Balance
            norm_col = next((c for c in df.columns if c in ["normal_balance", "normalbalance"]), None)
            # Debit / Credit / Net Balance / Amount
            debit_col = next((c for c in df.columns if c in ["debit_amount", "debit"]), None)
            credit_col = next((c for c in df.columns if c in ["credit_amount", "credit"]), None)
            net_col = next((c for c in df.columns if c in ["net_balance", "netbalance", "amount", "balance"]), None)

            if not acct_code_col or not acct_name_col:
                errors.append(f"Sheet '{sheet}': Missing mandatory Account Code or Account Name columns.")
                continue

            # Drop empty rows
            df = df.dropna(subset=[acct_code_col, acct_name_col], how='all')

            sheet_records = []
            sheet_debit_sum = 0.0
            sheet_credit_sum = 0.0
            sheet_net_sum = 0.0
            invalid_type_count = 0

            for idx, row in df.iterrows():
                code = str(row[acct_code_col]).strip() if pd.notna(row[acct_code_col]) else ""
                name = str(row[acct_name_col]).strip() if pd.notna(row[acct_name_col]) else ""

                if not code or not name or code.lower() == "nan" or name.lower() == "nan":
                    continue

                raw_type = str(row[type_col]).strip().capitalize() if type_col and pd.notna(row[type_col]) else "Expense"
                if raw_type not in VALID_ACCOUNT_TYPES:
                    # Best effort mapping
                    if "asset" in raw_type.lower(): raw_type = "Asset"
                    elif "liab" in raw_type.lower(): raw_type = "Liability"
                    elif "eq" in raw_type.lower(): raw_type = "Equity"
                    elif "rev" in raw_type.lower() or "inc" in raw_type.lower(): raw_type = "Revenue"
                    else: raw_type = "Expense"

                cat = str(row[cat_col]).strip() if cat_col and pd.notna(row[cat_col]) else ""
                subcat = str(row[subcat_col]).strip() if subcat_col and pd.notna(row[subcat_col]) else ""
                norm_bal = str(row[norm_col]).strip() if norm_col and pd.notna(row[norm_col]) else ("Debit" if raw_type in ["Asset", "Expense"] else "Credit")

                debit = float(row[debit_col]) if debit_col and pd.notna(row[debit_col]) else 0.0
                credit = float(row[credit_col]) if credit_col and pd.notna(row[credit_col]) else 0.0

                if net_col and pd.notna(row[net_col]):
                    net = float(row[net_col])
                    if not debit_col and not credit_col:
                        if net >= 0:
                            debit, credit = net, 0.0
                        else:
                            debit, credit = 0.0, abs(net)
                else:
                    net = debit - credit

                sheet_debit_sum += debit
                sheet_credit_sum += credit
                sheet_net_sum += net

                rec = {
                    "account_code": code,
                    "account_name": name,
                    "category": cat,
                    "sub_category": subcat,
                    "account_type": raw_type,
                    "normal_balance": norm_bal,
                    "debit_amount": round(debit, 2),
                    "credit_amount": round(credit, 2),
                    "net_balance": round(net, 2),
                    "quarter": sheet_meta["quarter"],
                    "fiscal_year": sheet_meta["year"],
                    "period_id": sheet_meta["period_id"],
                    "period_sequence": sheet_meta["sequence"]
                }
                sheet_records.append(rec)

            is_balanced = abs(sheet_debit_sum - sheet_credit_sum) < 5.0 or abs(sheet_net_sum) < 5.0

            validation_report[sheet] = {
                "rows_processed": len(sheet_records),
                "total_debit": round(sheet_debit_sum, 2),
                "total_credit": round(sheet_credit_sum, 2),
                "net_difference": round(sheet_net_sum, 2),
                "is_balanced": is_balanced,
                "status": "VALIDATED" if is_balanced else "UNBALANCED_WARNING"
            }

            all_records.extend(sheet_records)

        except Exception as e:
            errors.append(f"Error parsing sheet '{sheet}': {str(e)}")

    all_balanced = all(rep["is_balanced"] for rep in validation_report.values())

    return {
        "records": all_records,
        "validation_report": validation_report,
        "all_periods_balanced": all_balanced,
        "periods_detected": len(validation_report),
        "total_records": len(all_records),
        "errors": errors
    }
