"""
AIS Broker Reconciliation - Report Format Upgrade v2

Prerequisites:
    1. ais_broker_reco_final.py
    2. ais_broker_reco_modified.py

Keep all three files in the same folder, then run:

    python ais_broker_reco_report_v2.py
"""

import re
from difflib import SequenceMatcher

import ais_broker_reco_modified as mod

base = mod.base
_LAST_RECONCILIATION = {}


# =====================================================================
# 1. STT STATUS FROM SOURCE SHEET
# =====================================================================
def infer_stt_status_from_sheet(sheet_name):
    """
    Examples treated as STT paid:
        Gain arising of STT Paid
        Gains - STT Paid

    Examples treated as STT not paid:
        Gain arising without STT
        STT Not Paid
        No STT
    """
    name = base.normalize_header_text(sheet_name)

    negative_phrases = (
        "without stt",
        "stt not paid",
        "stt unpaid",
        "no stt",
        "non stt",
    )
    if any(phrase in name for phrase in negative_phrases):
        return False, "STT Paid: No (inferred from source-sheet name)"

    if "stt paid" in name or "with stt" in name:
        return True, "STT Paid: Yes (inferred from source-sheet name)"

    return None, "STT Paid: Not determinable from source-sheet name"


_previous_loader = base.load_and_normalize_workbook


def load_with_sheet_based_stt(file_path, file_label, log_callback):
    transactions = _previous_loader(file_path, file_label, log_callback)

    for txn in transactions:
        status, status_remark = infer_stt_status_from_sheet(
            txn.source_sheet
        )
        txn.stt_paid_status = status
        txn.stt_status_remark = status_remark

        # Internal indicator only. No STT amount is displayed in the report.
        # A very small positive value allows the tax engine to recognise the
        # transaction as STT-paid without representing a monetary amount.
        if status is True:
            txn.stt = 0.01
        elif status is False:
            txn.stt = 0.0

    return transactions


base.load_and_normalize_workbook = load_with_sheet_based_stt
mod.base.load_and_normalize_workbook = load_with_sheet_based_stt


# =====================================================================
# 2. COMPANY-NAME, TRADING-CODE AND ACRONYM MATCHING
# =====================================================================
LEGAL_AND_COMMON_WORDS = {
    "LIMITED", "LTD", "PRIVATE", "PVT", "COMPANY", "CO",
    "INDIA", "INDIAN", "THE", "OF", "AND", "CORPORATION",
    "CORP", "INDUSTRIES", "INDUSTRY", "ENTERPRISES",
    "ENTERPRISE", "HOLDINGS", "HOLDING"
}


def name_tokens(value):
    name = base.clean_security_name(value)
    return re.findall(r"[A-Z0-9]+", name)


def meaningful_tokens(value):
    return [
        token for token in name_tokens(value)
        if token not in LEGAL_AND_COMMON_WORDS
    ]


def ordered_subsequence(short_value, long_value):
    iterator = iter(long_value)
    return all(character in iterator for character in short_value)


def generated_codes(value):
    """
    Generates likely broker/trading abbreviations.

    RELIANCE INDUSTRIES LIMITED produces, among others:
        RELIANCE, RI, REI, RELIANCEI
    """
    all_tokens = name_tokens(value)
    useful = meaningful_tokens(value) or all_tokens

    if not useful:
        return set()

    codes = set()
    compact = "".join(useful)
    codes.add(compact)

    for token in useful:
        if len(token) >= 3:
            codes.add(token)

    initials_all = "".join(token[0] for token in all_tokens if token)
    initials_useful = "".join(token[0] for token in useful if token)
    if len(initials_all) >= 2:
        codes.add(initials_all)
    if len(initials_useful) >= 2:
        codes.add(initials_useful)

    first = useful[0]
    later_initials = "".join(
        token[0] for token in all_tokens[1:] if token
    )
    if later_initials:
        codes.add(first[:2] + later_initials)
        codes.add(first[:3] + later_initials)
        codes.add(first + later_initials)

    return {code for code in codes if len(code) >= 2}


def company_name_match(name_a, name_b):
    tokens_a = meaningful_tokens(name_a)
    tokens_b = meaningful_tokens(name_b)
    compact_a = "".join(tokens_a)
    compact_b = "".join(tokens_b)

    if not compact_a or not compact_b:
        return False

    if compact_a == compact_b:
        return True

    codes_a = generated_codes(name_a)
    codes_b = generated_codes(name_b)
    if compact_a in codes_b or compact_b in codes_a:
        return True
    if codes_a.intersection(codes_b):
        return True

    # Full first token is often the exchange/trading symbol.
    if tokens_a and tokens_b:
        if tokens_a[0] == tokens_b[0]:
            return True

    # Short broker codes such as REI for Reliance Industries.
    short_value, long_value = (
        (compact_a, compact_b)
        if len(compact_a) <= len(compact_b)
        else (compact_b, compact_a)
    )
    if 3 <= len(short_value) <= 10:
        if (
            short_value[0] == long_value[0]
            and ordered_subsequence(short_value, long_value)
        ):
            short_tokens = (
                tokens_a if short_value == compact_a else tokens_b
            )
            long_tokens = (
                tokens_b if short_value == compact_a else tokens_a
            )
            if long_tokens:
                expected = (
                    long_tokens[0][:2]
                    + "".join(token[0] for token in long_tokens[1:])
                )
                if short_value == expected:
                    return True

            # Require a strong similarity unless the generated-code rule
            # above already matched.
            similarity = SequenceMatcher(
                None, short_value, long_value[:max(len(short_value), 8)]
            ).ratio()
            if similarity >= 0.72:
                return True

    token_overlap = set(tokens_a).intersection(tokens_b)
    if token_overlap:
        longest_common = max(len(token) for token in token_overlap)
        if longest_common >= 5:
            return True

    return SequenceMatcher(None, compact_a, compact_b).ratio() >= 0.88


def enhanced_security_matches(ais_txn, broker_txn, soft=False):
    if (
        ais_txn.isin and broker_txn.isin
        and ais_txn.isin == broker_txn.isin
    ):
        return True

    exact_names = (
        base.clean_security_name(ais_txn.security_name)
        == base.clean_security_name(broker_txn.security_name)
    )
    if exact_names:
        return True

    return soft and company_name_match(
        ais_txn.security_name,
        broker_txn.security_name
    )


mod.security_matches = enhanced_security_matches


# =====================================================================
# 3. CAPTURE VALUE DASHBOARD DATA
# =====================================================================
_previous_matching_engine = mod.match_and_reconcile


def matching_with_dashboard_capture(
    ais_txns, broker_txns, tax_engine, log_callback
):
    result = _previous_matching_engine(
        ais_txns, broker_txns, tax_engine, log_callback
    )
    matched, unmatched_ais, unmatched_broker = result

    _LAST_RECONCILIATION.clear()
    _LAST_RECONCILIATION.update({
        "ais_rows": list(ais_txns),
        "broker_rows": list(broker_txns),
        "matched": list(matched),
        "unmatched_ais": list(unmatched_ais),
        "unmatched_broker": list(unmatched_broker),
    })
    return result


mod.match_and_reconcile = matching_with_dashboard_capture


def total_sale_value(transactions):
    return sum(
        base.clean_number(txn.sale_consideration)
        for txn in transactions
    )


def pair_totals(pairs):
    ais_value = sum(
        base.clean_number(ais.sale_consideration)
        for ais, _, _ in pairs
    )
    broker_value = sum(
        base.clean_number(broker.sale_consideration)
        for _, broker, _ in pairs
    )
    return ais_value, broker_value


def material_pairs(pairs):
    return [
        pair for pair in pairs
        if abs(
            pair[0].sale_consideration
            - pair[1].sale_consideration
        ) > mod.sale_cost_tolerance(
            pair[0].sale_consideration,
            pair[1].sale_consideration
        )
    ]


def nominal_variance_pairs(pairs):
    result = []
    for pair in pairs:
        ais, broker, _ = pair
        difference = abs(
            ais.sale_consideration - broker.sale_consideration
        )
        if (
            difference > base.TOLERANCE_AMOUNT
            and difference <= mod.sale_cost_tolerance(
                ais.sale_consideration,
                broker.sale_consideration
            )
        ):
            result.append(pair)
    return result


# =====================================================================
# 4. SUMMARY DASHBOARD AND CONSISTENT SHEET NAMES
# =====================================================================
_previous_summary_writer = (
    base.RecoReportGenerator.write_summary_sheet
)


def summary_with_value_dashboard(self, summary_data):
    _previous_summary_writer(self, summary_data)
    ws = self.wb["Summary"]

    # Make link text and target sheet name identical.
    for row in ws.iter_rows():
        for cell in row:
            if isinstance(cell.value, str):
                cell.value = cell.value.replace(
                    "Other Differences",
                    "Other Financial Differences"
                )
            if cell.hyperlink and cell.hyperlink.target:
                cell.hyperlink.target = cell.hyperlink.target.replace(
                    "Other Differences",
                    "Other Financial Differences"
                )

    data = _LAST_RECONCILIATION
    ais_rows = data.get("ais_rows", [])
    broker_rows = data.get("broker_rows", [])
    matched = data.get("matched", [])
    unmatched_ais = data.get("unmatched_ais", [])
    unmatched_broker = data.get("unmatched_broker", [])

    material = material_pairs(matched)
    nominal = nominal_variance_pairs(matched)

    total_ais = total_sale_value(ais_rows)
    total_broker = total_sale_value(broker_rows)
    matched_ais, matched_broker = pair_totals(matched)
    material_ais, material_broker = pair_totals(material)
    nominal_ais, nominal_broker = pair_totals(nominal)
    missing_ais_value = total_sale_value(unmatched_ais)
    missing_broker_value = total_sale_value(unmatched_broker)

    dashboard_rows = [
        (
            "Total sale consideration loaded",
            total_ais, total_broker
        ),
        (
            "Matched/reconciled sale consideration",
            matched_ais, matched_broker
        ),
        (
            "Material sale-consideration differences",
            material_ais, material_broker
        ),
        (
            "Ignored nominal transaction-cost variances",
            nominal_ais, nominal_broker
        ),
        (
            "Unmatched/missing transaction values",
            missing_ais_value, missing_broker_value
        ),
    ]

    start_row = ws.max_row + 3
    ws.cell(
        row=start_row, column=1,
        value="RECONCILIATION VALUE DASHBOARD"
    ).font = Font(
        name="Segoe UI", size=12, bold=True, color="1E3A8A"
    )

    headers = [
        "Reconciliation Category",
        "Value as per AIS",
        "Value as per Broker Report",
        "Actual Difference"
    ]
    for column, heading in enumerate(headers, 1):
        cell = ws.cell(
            row=start_row + 1, column=column, value=heading
        )
        cell.font = self.FONT_HEADER
        cell.fill = PatternFill(
            start_color=self.COLOR_INDIGO_HEADER,
            end_color=self.COLOR_INDIGO_HEADER,
            fill_type="solid"
        )
        cell.alignment = self.ALIGN_CENTER
        cell.border = self.BORDER_THIN

    for offset, (label, ais_value, broker_value) in enumerate(
        dashboard_rows, 2
    ):
        row_number = start_row + offset
        difference = ais_value - broker_value
        values = [label, ais_value, broker_value, difference]

        for column, value in enumerate(values, 1):
            cell = ws.cell(
                row=row_number, column=column, value=value
            )
            cell.border = self.BORDER_THIN
            cell.font = self.FONT_BODY

            if column > 1:
                cell.number_format = '₹#,##0.00;[Red]-₹#,##0.00'
                cell.alignment = self.ALIGN_RIGHT

        if abs(difference) > base.TOLERANCE_AMOUNT:
            ws.cell(
                row=row_number, column=4
            ).fill = PatternFill(
                start_color=self.COLOR_RED_DIFF,
                end_color=self.COLOR_RED_DIFF,
                fill_type="solid"
            )
        else:
            ws.cell(
                row=row_number, column=4
            ).fill = PatternFill(
                start_color=self.COLOR_GREEN_MATCH,
                end_color=self.COLOR_GREEN_MATCH,
                fill_type="solid"
            )

    ws.column_dimensions["A"].width = 48
    ws.column_dimensions["B"].width = 24
    ws.column_dimensions["C"].width = 28
    ws.column_dimensions["D"].width = 22


base.RecoReportGenerator.write_summary_sheet = (
    summary_with_value_dashboard
)


# =====================================================================
# 5. REMOVE STT AMOUNT AND HOLDING-PERIOD COLUMNS FROM OUTPUT
# =====================================================================
def write_tax_output_without_stt_amount_or_holding(self, transactions):
    ws = self.wb.create_sheet(title="Tax Software Output")
    headers = [
        "Source Row", "Source Sheet", "Security", "ISIN",
        "Type of Asset", "Sale Date", "Purchase Date",
        "Quantity", "Sale Consideration", "Purchase Cost",
        "STT Paid?", "Original Classification",
        "Calculated Classification", "Is it LTCG?",
        "Tax Rule Remarks"
    ]
    self.style_header(ws, headers)

    row_number = 2
    for txn in transactions:
        stt_status = getattr(txn, "stt_paid_status", None)
        stt_display = (
            "Yes" if stt_status is True
            else "No" if stt_status is False
            else "Not Determinable"
        )
        status_remark = getattr(
            txn, "stt_status_remark",
            "STT Paid: Not determinable from source-sheet name"
        )
        remarks = txn.remarks
        if status_remark not in remarks:
            remarks = f"{remarks}; {status_remark}".strip("; ")

        ws.append([
            txn.source_row, txn.source_sheet, txn.security_name,
            txn.isin, txn.calculated_asset_type, txn.sale_date,
            txn.purchase_date, txn.quantity,
            txn.sale_consideration, txn.purchase_cost,
            stt_display, txn.original_classification,
            txn.calculated_classification, txn.is_ltcg,
            remarks
        ])

        ws.cell(
            row=row_number, column=6
        ).number_format = "yyyy-mm-dd"
        ws.cell(
            row=row_number, column=7
        ).number_format = "yyyy-mm-dd"
        ws.cell(
            row=row_number, column=8
        ).number_format = "#,##0.0000"
        for column in (9, 10):
            ws.cell(
                row=row_number, column=column
            ).number_format = "#,##0.00"
        row_number += 1

    if row_number > 2:
        self.format_rows(
            ws, 2, row_number - 1, len(headers)
        )
    self.autofit_columns(ws)


def write_difference_without_stt_or_holding(
    self, title, difference_rows
):
    if title == "Other Differences":
        title = "Other Financial Differences"

    ws = self.wb.create_sheet(title=title)
    headers = [
        "Match ID", "Security", "ISIN", "Transaction Date",
        "Purchase Date", "Quantity",
        "AIS Class", "Broker Class", "Calculated Class",
        "Is it LTCG?", "AIS Sale Value", "Broker Sale Value",
        "Difference in Sale Value", "Allowed Nominal Variance",
        "AIS Cost", "Broker Cost", "Difference in Cost",
        "Difference Type", "Remarks", "Source Sheet", "Source Row"
    ]
    self.style_header(ws, headers)

    row_number = 2
    for ais, broker, difference_type, remarks in difference_rows:
        sale_difference = (
            ais.sale_consideration - broker.sale_consideration
        )
        cost_difference = ais.purchase_cost - broker.purchase_cost
        allowed_variance = mod.sale_cost_tolerance(
            ais.sale_consideration,
            broker.sale_consideration
        )

        ws.append([
            ais.match_id, ais.security_name, ais.isin,
            ais.sale_date, broker.purchase_date or ais.purchase_date,
            ais.quantity, ais.original_classification,
            broker.original_classification,
            ais.calculated_classification, ais.is_ltcg,
            ais.sale_consideration, broker.sale_consideration,
            sale_difference, allowed_variance,
            ais.purchase_cost, broker.purchase_cost,
            cost_difference, difference_type, remarks,
            ais.source_sheet, ais.source_row
        ])

        ws.cell(
            row=row_number, column=4
        ).number_format = "yyyy-mm-dd"
        ws.cell(
            row=row_number, column=5
        ).number_format = "yyyy-mm-dd"
        ws.cell(
            row=row_number, column=6
        ).number_format = "#,##0.0000"
        for column in range(11, 18):
            ws.cell(
                row=row_number, column=column
            ).number_format = "#,##0.00"
        row_number += 1

    if row_number > 2:
        self.format_rows(
            ws, 2, row_number - 1, len(headers)
        )
    self.autofit_columns(ws)


def write_missing_without_stt(self, title, transactions):
    ws = self.wb.create_sheet(title=title)
    headers = [
        "Source Row", "Source Sheet", "Security", "ISIN",
        "Transaction Date", "Quantity", "Sale Consideration",
        "Purchase Date", "Purchase Cost",
        "Reported Classification", "Calculated Classification",
        "Is it LTCG?", "Remarks"
    ]
    self.style_header(ws, headers)

    row_number = 2
    for txn in transactions:
        ws.append([
            txn.source_row, txn.source_sheet, txn.security_name,
            txn.isin, txn.sale_date, txn.quantity,
            txn.sale_consideration, txn.purchase_date,
            txn.purchase_cost, txn.original_classification,
            txn.calculated_classification, txn.is_ltcg,
            txn.remarks
        ])
        ws.cell(
            row=row_number, column=5
        ).number_format = "yyyy-mm-dd"
        ws.cell(
            row=row_number, column=6
        ).number_format = "#,##0.0000"
        ws.cell(
            row=row_number, column=7
        ).number_format = "#,##0.00"
        ws.cell(
            row=row_number, column=8
        ).number_format = "yyyy-mm-dd"
        ws.cell(
            row=row_number, column=9
        ).number_format = "#,##0.00"
        row_number += 1

    if row_number > 2:
        self.format_rows(
            ws, 2, row_number - 1, len(headers)
        )
    self.autofit_columns(ws)


def write_matched_without_stt(self, matched_pairs):
    ws = self.wb.create_sheet(title="Matched Transactions")
    headers = [
        "Match ID", "Security", "ISIN", "Transaction Date",
        "Quantity", "AIS Sale Value", "Broker Sale Value",
        "Difference in Sale Value", "AIS Cost", "Broker Cost",
        "AIS Class", "Broker Class", "Calculated Class",
        "Is it LTCG?", "Match Mode"
    ]
    self.style_header(ws, headers)

    row_number = 2
    for ais, broker, match_mode in matched_pairs:
        ws.append([
            ais.match_id, ais.security_name, ais.isin,
            ais.sale_date, ais.quantity,
            ais.sale_consideration, broker.sale_consideration,
            ais.sale_consideration - broker.sale_consideration,
            ais.purchase_cost, broker.purchase_cost,
            ais.original_classification,
            broker.original_classification,
            ais.calculated_classification, ais.is_ltcg,
            match_mode
        ])
        ws.cell(
            row=row_number, column=4
        ).number_format = "yyyy-mm-dd"
        ws.cell(
            row=row_number, column=5
        ).number_format = "#,##0.0000"
        for column in range(6, 11):
            ws.cell(
                row=row_number, column=column
            ).number_format = "#,##0.00"
        row_number += 1

    if row_number > 2:
        self.format_rows(
            ws, 2, row_number - 1, len(headers)
        )
    self.autofit_columns(ws)


base.RecoReportGenerator.write_tax_software_output = (
    write_tax_output_without_stt_amount_or_holding
)
base.RecoReportGenerator.write_difference_sheet = (
    write_difference_without_stt_or_holding
)
base.RecoReportGenerator.write_missing_sheet = (
    write_missing_without_stt
)
base.RecoReportGenerator.write_matched_sheet = (
    write_matched_without_stt
)


if __name__ == "__main__":
    app = base.AISBrokerRecoApp()
    app.mainloop()
