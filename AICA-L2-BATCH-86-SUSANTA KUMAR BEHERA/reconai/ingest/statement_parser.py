import io
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import pandas as pd
import pdfplumber

from reconai.models.transaction import StatementTransaction, TransactionType
from reconai.ingest.base_parser import (
    parse_flexible_date,
    clean_monetary_amount,
    detect_statement_columns,
    read_file_bytes_safely,
)
from reconai.ai.client import AIClient
from reconai.ingest.document_parser import DocumentParser, IMAGE_EXTENSIONS, DOCX_EXTENSIONS

logger = logging.getLogger(__name__)


class StatementParser:
    """Parses Bank Statements from CSV, Excel, PDF, Word (.docx), and Scanned Images into normalized StatementTransaction objects."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        ai_client: Optional[AIClient] = None,
        anthropic_api_key: Optional[str] = None,
    ):
        effective_key = api_key or anthropic_api_key
        self.ai_client = ai_client or AIClient(api_key=effective_key)
        self.document_parser = DocumentParser(ai_client=self.ai_client)

    def parse(
        self,
        file_path_or_bytes: Union[str, Path, bytes],
        file_name: Optional[str] = None,
        custom_mapping: Optional[Dict[str, str]] = None,
    ) -> List[StatementTransaction]:
        """Entry point for parsing bank statements."""
        ext = ""
        if isinstance(file_path_or_bytes, (str, Path)):
            path = Path(file_path_or_bytes)
            ext = path.suffix.lower()
            file_name = file_name or path.name
        elif file_name:
            ext = Path(file_name).suffix.lower()

        if ext in IMAGE_EXTENSIONS:
            return self.document_parser.extract_statement_from_image(file_path_or_bytes, file_name)
        elif ext in DOCX_EXTENSIONS:
            df = self.document_parser.parse_docx_to_dataframe(file_path_or_bytes)
            return self._dataframe_to_transactions(df, custom_mapping)
        elif ext == ".csv":
            return self._parse_csv(file_path_or_bytes, custom_mapping)
        elif ext in [".xlsx", ".xls"]:
            return self._parse_excel(file_path_or_bytes, custom_mapping)
        elif ext == ".pdf":
            return self._parse_pdf(file_path_or_bytes, custom_mapping, file_name)
        else:
            try:
                return self._parse_csv(file_path_or_bytes, custom_mapping)
            except Exception:
                return self._parse_excel(file_path_or_bytes, custom_mapping)

    def _parse_csv(
        self,
        source: Union[str, Path, bytes],
        custom_mapping: Optional[Dict[str, str]] = None,
    ) -> List[StatementTransaction]:
        data = read_file_bytes_safely(source)
        df = pd.read_csv(io.BytesIO(data))
        return self._dataframe_to_transactions(df, custom_mapping)

    def _parse_excel(
        self,
        source: Union[str, Path, bytes],
        custom_mapping: Optional[Dict[str, str]] = None,
    ) -> List[StatementTransaction]:
        data = read_file_bytes_safely(source)
        df = pd.read_excel(io.BytesIO(data))
        return self._dataframe_to_transactions(df, custom_mapping)

    def _dataframe_to_transactions(
        self,
        df: pd.DataFrame,
        custom_mapping: Optional[Dict[str, str]] = None,
    ) -> List[StatementTransaction]:
        df = df.dropna(how="all").copy()

        if any(str(c).startswith("Unnamed:") for c in df.columns) or len([c for c in df.columns if isinstance(c, int)]) > len(df.columns) / 2:
            for idx, row in df.head(15).iterrows():
                row_str = " ".join([str(v).lower() for v in row.values if pd.notna(v)])
                if ("date" in row_str and ("narration" in row_str or "description" in row_str or "particulars" in row_str)) or ("withdrawal" in row_str and "deposit" in row_str) or ("debit" in row_str and "credit" in row_str):
                    df.columns = [str(val).strip() for val in row.values]
                    df = df.iloc[idx + 1:].reset_index(drop=True)
                    break

        columns = [str(c) for c in df.columns]
        mapping = custom_mapping or detect_statement_columns(columns)

        date_col = mapping.get("date")
        desc_col = mapping.get("description")
        debit_col = mapping.get("debit")
        credit_col = mapping.get("credit")
        amt_col = mapping.get("amount")
        type_col = mapping.get("type")
        bal_col = mapping.get("balance")
        ref_col = mapping.get("ref_no")

        if not date_col or not desc_col:
            raise ValueError(f"Unable to auto-detect essential columns (Date, Description) from {columns}")

        transactions: List[StatementTransaction] = []

        for idx, row in df.iterrows():
            row_dict = {str(k): (None if pd.isna(v) else v) for k, v in row.items()}

            dt = parse_flexible_date(row.get(date_col))
            if not dt:
                continue

            desc = str(row.get(desc_col, "") or "").strip()
            if not desc:
                desc = "No narration"

            if ref_col and row.get(ref_col) and str(row.get(ref_col)) not in desc:
                ref_val = str(row.get(ref_col)).strip()
                if ref_val and ref_val.lower() != "nan" and ref_val != "-":
                    desc = f"{desc} [Ref: {ref_val}]"

            bal = clean_monetary_amount(row.get(bal_col)) if bal_col else None

            tx_type: Optional[TransactionType] = None
            amount = None

            if debit_col and credit_col:
                dr_amt = clean_monetary_amount(row.get(debit_col))
                cr_amt = clean_monetary_amount(row.get(credit_col))

                if dr_amt is not None and dr_amt > 0:
                    amount = dr_amt
                    tx_type = TransactionType.DEBIT
                elif cr_amt is not None and cr_amt > 0:
                    amount = cr_amt
                    tx_type = TransactionType.CREDIT
            elif amt_col:
                amount = clean_monetary_amount(row.get(amt_col))
                if type_col and row.get(type_col):
                    t_str = str(row.get(type_col)).strip().upper()
                    if "DR" in t_str or "DEBIT" in t_str or "PAYMENT" in t_str or "WDL" in t_str:
                        tx_type = TransactionType.DEBIT
                    elif "CR" in t_str or "CREDIT" in t_str or "DEP" in t_str:
                        tx_type = TransactionType.CREDIT
                elif str(row.get(amt_col)).strip().startswith("-"):
                    tx_type = TransactionType.DEBIT
                else:
                    if "DR" in desc.upper():
                        tx_type = TransactionType.DEBIT
                    else:
                        tx_type = TransactionType.CREDIT

            if amount is None or amount == 0 or tx_type is None:
                continue

            transactions.append(
                StatementTransaction(
                    source_row_ref=int(idx) + 2,
                    date=dt,
                    description=desc,
                    amount=amount,
                    type=tx_type,
                    balance=bal,
                    raw_data=row_dict,
                )
            )

        return transactions

    def _parse_pdf(
        self,
        source: Union[str, Path, bytes],
        custom_mapping: Optional[Dict[str, str]] = None,
        file_name: Optional[str] = None,
    ) -> List[StatementTransaction]:
        """Multi-strategy PDF Statement Parser with table detection and multimodal OCR fallback."""
        data = read_file_bytes_safely(source)
        pdf_file = pdfplumber.open(io.BytesIO(data))

        raw_text_pages: List[str] = []
        transactions: List[StatementTransaction] = []

        with pdf_file as pdf:
            header = None
            col_mapping = None
            detected_acct = None

            if pdf.pages:
                first_text = pdf.pages[0].extract_text() or ""
                m_acct = re.search(r"Account\s*(?:No|Number|#)?[\s:]*([0-9]{9,18})", first_text, re.IGNORECASE)
                if m_acct:
                    detected_acct = m_acct.group(1)

            for page_idx, page in enumerate(pdf.pages):
                page_text = page.extract_text() or ""
                raw_text_pages.append(page_text)
                tables = page.extract_tables()

                for table in tables:
                    for raw_row in table:
                        if not raw_row or not any(cell and str(cell).strip() for cell in raw_row):
                            continue
                        row = [str(c or "").strip() for c in raw_row]
                        row_str = " ".join(row).lower()

                        if "date" in row_str and ("particulars" in row_str or "narration" in row_str or "description" in row_str or "withdrawal" in row_str or "debit" in row_str):
                            header = row
                            col_mapping = custom_mapping or detect_statement_columns(header)
                            continue

                        if header and col_mapping:
                            date_col_name = col_mapping.get("date")
                            date_col_idx = None
                            for idx, h in enumerate(header):
                                if h == date_col_name:
                                    date_col_idx = idx
                                    break

                            if date_col_idx is not None and date_col_idx < len(row):
                                dt = parse_flexible_date(row[date_col_idx])
                                if dt:
                                    desc = ""
                                    debit_amt = None
                                    credit_amt = None
                                    bal = None
                                    ref = ""

                                    for idx, h in enumerate(header):
                                        if idx < len(row):
                                            val = row[idx]
                                            if h == col_mapping.get("description"):
                                                desc = val
                                            elif h == col_mapping.get("debit"):
                                                debit_amt = clean_monetary_amount(val)
                                            elif h == col_mapping.get("credit"):
                                                credit_amt = clean_monetary_amount(val)
                                            elif h == col_mapping.get("balance"):
                                                bal = clean_monetary_amount(val)
                                            elif h == col_mapping.get("ref_no"):
                                                ref = val

                                    tx_type = None
                                    amount = None
                                    if debit_amt is not None and debit_amt > 0:
                                        amount = debit_amt
                                        tx_type = TransactionType.DEBIT
                                    elif credit_amt is not None and credit_amt > 0:
                                        amount = credit_amt
                                        tx_type = TransactionType.CREDIT

                                    if amount and tx_type:
                                        if ref and ref != "-" and ref.lower() != "nan" and ref not in desc:
                                            desc = f"{desc} [Ref: {ref}]"
                                        transactions.append(
                                            StatementTransaction(
                                                source_row_ref=len(transactions) + 1,
                                                date=dt,
                                                description=desc or "Bank Transaction",
                                                amount=amount,
                                                type=tx_type,
                                                balance=bal,
                                                raw_data={"row": row, "page": page_idx + 1, "account_no": detected_acct},
                                            )
                                        )

        if transactions:
            return transactions

        # Fallback 1: Text-based LLM extraction
        ai_error = None
        has_text = any(t.strip() for t in raw_text_pages)
        if self.ai_client and self.ai_client.is_available and has_text:
            full_text = "\n\n--- PAGE BREAK ---\n\n".join(raw_text_pages[:10])
            try:
                ai_txs = self._ai_extract_statement_pdf(full_text)
                if ai_txs:
                    return ai_txs
            except Exception as e:
                ai_error = str(e)

        # Fallback 2: Multimodal Gemini Vision for Scanned PDF
        if self.ai_client and self.ai_client.is_available:
            try:
                return self.document_parser.extract_statement_from_image(source, file_name or "statement.pdf")
            except Exception as e:
                ai_error = str(e)

        error_msg = "Could not extract statement transactions from PDF. Try converting to CSV/Excel or enabling Gemini API key in Settings."
        if ai_error:
            error_msg = f"{error_msg}\n\nGemini API Error: {ai_error}"

        raise ValueError(error_msg)

    def _ai_extract_statement_pdf(self, pdf_text: str) -> List[StatementTransaction]:
        """Fallback extractor using Gemini AI API for irregular PDF text layouts."""
        prompt = (
            "Extract all bank transactions from the following raw bank statement text. "
            "Output ONLY a JSON list of objects with the exact schema:\n"
            '[{"source_row_ref": 1, "date": "YYYY-MM-DD", "description": "...", "amount": "1234.50", "type": "DEBIT"|"CREDIT", "balance": "5678.90"}]\n\n'
            f"Bank Statement Text:\n{pdf_text[:12000]}"
        )
        items = self.ai_client.generate_json(
            prompt=prompt,
            system_instruction="You are a financial document parser. Extract bank statement transactions accurately into the requested JSON schema."
        )
        if not isinstance(items, list):
            return []

        txs: List[StatementTransaction] = []
        for item in items:
            dt = parse_flexible_date(item.get("date"))
            amt = clean_monetary_amount(item.get("amount"))
            bal = clean_monetary_amount(item.get("balance")) if item.get("balance") else None
            t_str = str(item.get("type", "DEBIT")).upper()
            ttype = TransactionType.CREDIT if "CR" in t_str else TransactionType.DEBIT
            if dt and amt:
                txs.append(
                    StatementTransaction(
                        source_row_ref=item.get("source_row_ref", len(txs) + 1),
                        date=dt,
                        description=str(item.get("description", "Transaction")),
                        amount=amt,
                        type=ttype,
                        balance=bal,
                        raw_data=item,
                    )
                )
        return txs
