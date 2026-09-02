import io
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import pandas as pd

from reconai.models.transaction import LedgerEntry, TransactionType
from reconai.ingest.base_parser import (
    parse_flexible_date,
    clean_monetary_amount,
    detect_ledger_columns,
    read_file_bytes_safely,
)
from reconai.ai.client import AIClient
from reconai.ingest.document_parser import DocumentParser, IMAGE_EXTENSIONS, DOCX_EXTENSIONS

logger = logging.getLogger(__name__)


class LedgerParser:
    """Parses Client Ledger/Books (Tally, ERP, CSV, Excel, Word .docx, Scanned Images & Handwritten Vouchers) into normalized LedgerEntry objects."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        ai_client: Optional[AIClient] = None,
    ):
        self.ai_client = ai_client or AIClient(api_key=api_key)
        self.document_parser = DocumentParser(ai_client=self.ai_client)

    def parse(
        self,
        file_path_or_bytes: Union[str, Path, bytes],
        file_name: Optional[str] = None,
        custom_mapping: Optional[Dict[str, str]] = None,
        sheet_name: Optional[Union[str, int]] = None,
    ) -> List[LedgerEntry]:
        ext = ""
        if isinstance(file_path_or_bytes, (str, Path)):
            path = Path(file_path_or_bytes)
            ext = path.suffix.lower()
            file_name = file_name or path.name
        elif file_name:
            ext = Path(file_name).suffix.lower()

        if ext in IMAGE_EXTENSIONS:
            return self.document_parser.extract_ledger_from_image(file_path_or_bytes, file_name)
        elif ext in DOCX_EXTENSIONS:
            df = self.document_parser.parse_docx_to_dataframe(file_path_or_bytes)
            return self._dataframe_to_ledger_entries(df, custom_mapping)
        elif ext == ".csv":
            return self._parse_csv(file_path_or_bytes, custom_mapping)
        elif ext in [".xlsx", ".xls"]:
            return self._parse_excel(file_path_or_bytes, custom_mapping, sheet_name=sheet_name)
        else:
            try:
                return self._parse_csv(file_path_or_bytes, custom_mapping)
            except Exception:
                return self._parse_excel(file_path_or_bytes, custom_mapping, sheet_name=sheet_name)

    def _parse_csv(
        self,
        source: Union[str, Path, bytes],
        custom_mapping: Optional[Dict[str, str]] = None,
    ) -> List[LedgerEntry]:
        data = read_file_bytes_safely(source)
        df = pd.read_csv(io.BytesIO(data))
        return self._dataframe_to_ledger_entries(df, custom_mapping)

    def _parse_excel(
        self,
        source: Union[str, Path, bytes],
        custom_mapping: Optional[Dict[str, str]] = None,
        sheet_name: Optional[Union[str, int]] = None,
    ) -> List[LedgerEntry]:
        data = read_file_bytes_safely(source)
        excel_file = pd.ExcelFile(io.BytesIO(data))

        target_sheet = sheet_name
        if target_sheet is None:
            if len(excel_file.sheet_names) > 1:
                # Auto-select the sheet with the most rows / highest accounting relevance
                best_sheet = excel_file.sheet_names[0]
                max_rows = 0
                for s_name in excel_file.sheet_names:
                    try:
                        sample_df = excel_file.parse(s_name, nrows=30)
                        s_str = " ".join([str(c).lower() for c in sample_df.columns] + [str(v).lower() for v in sample_df.values.flatten() if pd.notna(v)])
                        if any(k in s_str for k in ["date", "particulars", "vch", "debit", "credit"]):
                            full_len = len(excel_file.parse(s_name))
                            if full_len > max_rows:
                                max_rows = full_len
                                best_sheet = s_name
                    except Exception:
                        pass
                target_sheet = best_sheet
            else:
                target_sheet = excel_file.sheet_names[0]

        df = excel_file.parse(target_sheet)
        return self._dataframe_to_ledger_entries(df, custom_mapping)

    def _dataframe_to_ledger_entries(
        self,
        df: pd.DataFrame,
        custom_mapping: Optional[Dict[str, str]] = None,
    ) -> List[LedgerEntry]:
        # Reset index immediately after dropping empty rows
        df = df.dropna(how="all").reset_index(drop=True).copy()

        # Handle nested headers or metadata header lines (common in Tally exports)
        for idx in range(min(15, len(df))):
            row = df.iloc[idx]
            row_str = " ".join([str(v).lower() for v in row.values if pd.notna(v)])
            if ("date" in row_str and ("particulars" in row_str or "vch" in row_str or "debit" in row_str or "ledger" in row_str)):
                clean_cols = []
                for c_idx, val in enumerate(row.values):
                    v_str = str(val).strip() if pd.notna(val) else f"Col_{c_idx}"
                    clean_cols.append(v_str)
                df.columns = clean_cols
                df = df.iloc[idx + 1:].reset_index(drop=True)
                break

        columns = [str(c) for c in df.columns]
        mapping = custom_mapping or detect_ledger_columns(columns)

        date_col = mapping.get("date")
        desc_col = mapping.get("description")
        acct_col = mapping.get("account_name")
        vch_type_col = mapping.get("voucher_type")
        vch_no_col = mapping.get("voucher_no")
        debit_col = mapping.get("debit")
        credit_col = mapping.get("credit")
        amt_col = mapping.get("amount")
        type_col = mapping.get("type")
        appr_col = mapping.get("approver")
        gstin_col = mapping.get("gstin")
        tds_col = mapping.get("tds_section")

        if not date_col:
            raise ValueError(f"Unable to auto-detect Date column from {columns}")

        if not desc_col and not acct_col:
            for c in columns:
                if c != date_col and not any(k in c.lower() for k in ["debit", "credit", "amount", "vch", "balance"]):
                    desc_col = c
                    break

        entries: List[LedgerEntry] = []

        for idx, row in df.iterrows():
            row_dict = {str(k): (None if pd.isna(v) else v) for k, v in row.items()}

            if any("opening balance" in str(v).lower() or "closing balance" in str(v).lower() for v in row.values if pd.notna(v)):
                continue

            dt = parse_flexible_date(row.get(date_col))
            if not dt:
                continue

            desc = str(row.get(desc_col, "") or "").strip() if desc_col else ""
            acct = str(row.get(acct_col, "") or "").strip() if acct_col else None

            if desc in ("To", "By", ""):
                candidate_party = None
                for c in columns:
                    if c not in (date_col, desc_col, vch_type_col, vch_no_col, debit_col, credit_col, amt_col):
                        val_str = str(row.get(c, "") or "").strip()
                        if val_str and val_str.lower() != "nan" and not clean_monetary_amount(val_str):
                            candidate_party = val_str
                            break
                if candidate_party:
                    desc = f"{desc} {candidate_party}".strip() if desc else candidate_party
                    acct = candidate_party

            if not desc and acct:
                desc = acct
            elif not desc:
                desc = "Ledger Entry"

            vch_type = str(row.get(vch_type_col, "") or "").strip() if vch_type_col else None
            vch_no = str(row.get(vch_no_col, "") or "").strip() if vch_no_col else None
            approver = str(row.get(appr_col, "") or "").strip() if appr_col else None
            gstin = str(row.get(gstin_col, "") or "").strip() if gstin_col else None
            tds = str(row.get(tds_col, "") or "").strip() if tds_col else None

            source_ref = vch_no if (vch_no and vch_no.lower() != "nan") else (int(idx) + 1)

            tx_type: Optional[TransactionType] = None
            amount = None

            dr_amt = clean_monetary_amount(row.get(debit_col)) if debit_col else None
            cr_amt = clean_monetary_amount(row.get(credit_col)) if credit_col else None

            if vch_type:
                vt = vch_type.lower()
                if "payment" in vt:
                    tx_type = TransactionType.DEBIT
                    amount = cr_amt or dr_amt
                elif "receipt" in vt:
                    tx_type = TransactionType.CREDIT
                    amount = dr_amt or cr_amt
                elif "contra" in vt:
                    if dr_amt is not None and dr_amt > 0:
                        tx_type = TransactionType.CREDIT
                        amount = dr_amt
                    elif cr_amt is not None and cr_amt > 0:
                        tx_type = TransactionType.DEBIT
                        amount = cr_amt

            if amount is None or tx_type is None:
                if debit_col and credit_col:
                    if dr_amt is not None and dr_amt > 0:
                        amount = dr_amt
                        tx_type = TransactionType.DEBIT if "payment" in desc.lower() else TransactionType.CREDIT
                    elif cr_amt is not None and cr_amt > 0:
                        amount = cr_amt
                        tx_type = TransactionType.DEBIT
                elif amt_col:
                    amount = clean_monetary_amount(row.get(amt_col))
                    if type_col and row.get(type_col):
                        t_str = str(row.get(type_col)).strip().upper()
                        if "DR" in t_str or "DEBIT" in t_str or "PAYMENT" in t_str:
                            tx_type = TransactionType.DEBIT
                        elif "CR" in t_str or "CREDIT" in t_str or "RECEIPT" in t_str:
                            tx_type = TransactionType.CREDIT
                    elif str(row.get(amt_col)).strip().startswith("-"):
                        tx_type = TransactionType.DEBIT
                    else:
                        tx_type = TransactionType.DEBIT

            if amount is None or amount == 0 or tx_type is None:
                continue

            entries.append(
                LedgerEntry(
                    source_row_ref=source_ref,
                    date=dt,
                    description=desc,
                    amount=amount,
                    type=tx_type,
                    account_name=acct if (acct and acct.lower() != "nan") else None,
                    voucher_type=vch_type if (vch_type and vch_type.lower() != "nan") else None,
                    approver_ref=approver if (approver and approver.lower() != "nan") else None,
                    gstin=gstin if (gstin and gstin.lower() != "nan") else None,
                    tds_section=tds if (tds and tds.lower() != "nan") else None,
                    raw_data=row_dict,
                )
            )

        return entries
