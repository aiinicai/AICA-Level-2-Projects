#!/usr/bin/env python3
"""Bank Statement Analyzer for CA/ITR Practice.
Dharmjeet & Associates, Chartered Accountants.

Offline desktop pipeline to ingest bank statements (PDF, Scanned, Excel, Word, Images),
normalize transactions, classify nature-wise/party-wise, flag scrutiny risks, and export
Excel, Word, and PDF reports.
"""

import os
import sys
import argparse
import pandas as pd
from typing import List, Optional

from ingestion import ingest_multiple_statements, ingest_statement
from classification import classify_transactions, load_client_profile, save_client_profile, add_party_mapping
from analysis import (
    generate_executive_summary, generate_month_wise_summary,
    generate_nature_wise_summary, generate_party_wise_summary,
    generate_cash_summary, detect_red_flags, analyze_presumptive_tax,
    validate_running_balances
)
from reports import export_excel_report, export_word_report, export_pdf_report

def analyze_and_generate_reports(
    file_paths: List[str],
    client_name: str = "Client",
    output_dir: str = "output",
    password: Optional[str] = None,
    formats: List[str] = ["excel", "word", "pdf"]
) -> dict:
    """
    Run complete bank statement analysis pipeline and generate requested report formats.
    """
    os.makedirs(output_dir, exist_ok=True)
    print(f"\n=======================================================")
    print(f" DHARMJEET & ASSOCIATES — BANK STATEMENT ANALYZER")
    print(f" Client: {client_name}")
    print(f" Processing {len(file_paths)} file(s)...")
    print(f"=======================================================\n")

    # 1. Ingestion
    file_inputs = [{"file": fp, "filename": os.path.basename(fp), "password": password} for fp in file_paths]
    df_raw = ingest_multiple_statements(file_inputs)
    
    if df_raw.empty:
        print("[!] No transaction rows could be extracted from provided files.")
        return {"status": "EMPTY", "df": pd.DataFrame()}

    print(f"[+] Ingested {len(df_raw)} raw transaction entries.")

    # 2. Classification
    df_classified = classify_transactions(df_raw, client_name=client_name)
    print(f"[+] Nature and party classification completed.")

    # 3. Reconciliation Validation
    df_recon, recon_summary = validate_running_balances(df_classified)
    print(f"[+] Running balance validation: {recon_summary['status']} ({recon_summary['discrepancies_found']} discrepancy flags).")

    # 4. Red Flag & Scrutiny Detection
    df_analyzed, red_flag_summary = detect_red_flags(df_recon, client_name=client_name)
    print(f"[+] Scrutiny scan: {red_flag_summary['total_flagged_transactions']} anomalies flagged (Total Volume: INR {red_flag_summary['total_flagged_amount']:,.2f}).")

    # 5. Presumptive Taxation Assessment
    presump_summary = analyze_presumptive_tax(df_analyzed)
    print(f"[+] Presumptive Tax Check: Gross Turnover INR {presump_summary['total_turnover']:,.2f} ({presump_summary['digital_percentage']:.1f}% digital).")

    # 6. Summaries
    exec_summary = generate_executive_summary(df_analyzed)
    print(f"\n--- EXECUTIVE SUMMARY ---")
    print(f"  Total Credits (Receipts): INR {exec_summary['total_credits']:,.2f} ({exec_summary['credit_count']} entries)")
    print(f"  Total Debits (Payments):  INR {exec_summary['total_debits']:,.2f} ({exec_summary['debit_count']} entries)")
    print(f"  Net Movement:             INR {exec_summary['net_movement']:,.2f}")
    print(f"  Period:                   {exec_summary['start_date']} to {exec_summary['end_date']}")

    # 7. Generate Reports
    safe_client = "".join(c for c in client_name if c.isalnum() or c in (' ', '_', '-')).strip().replace(' ', '_')
    report_paths = {}

    if "excel" in formats or "xlsx" in formats:
        excel_path = os.path.join(output_dir, f"{safe_client}_Bank_Statement_Summary.xlsx")
        export_excel_report(df_analyzed, excel_path, client_name=client_name)
        report_paths["excel"] = excel_path
        print(f"[OK] Excel Report generated: {excel_path}")

    if "word" in formats or "docx" in formats:
        word_path = os.path.join(output_dir, f"{safe_client}_Bank_Statement_Report.docx")
        export_word_report(df_analyzed, word_path, client_name=client_name)
        report_paths["word"] = word_path
        print(f"[OK] Word Report generated: {word_path}")

    if "pdf" in formats:
        pdf_path = os.path.join(output_dir, f"{safe_client}_Bank_Statement_Report.pdf")
        export_pdf_report(df_analyzed, pdf_path, client_name=client_name)
        report_paths["pdf"] = pdf_path
        print(f"[OK] PDF Report generated: {pdf_path}")

    print(f"\n[OK] All requested reports generated successfully in '{output_dir}'.\n")

    return {
        "status": "SUCCESS",
        "df": df_analyzed,
        "exec_summary": exec_summary,
        "red_flag_summary": red_flag_summary,
        "presump_summary": presump_summary,
        "recon_summary": recon_summary,
        "report_paths": report_paths
    }

def main():
    parser = argparse.ArgumentParser(
        description="Offline Bank Statement Analyzer for CA/ITR Practice — Dharmjeet & Associates"
    )
    parser.add_argument("--files", "-f", nargs="+", help="Path to bank statement file(s) (PDF, Excel, Word, Image, CSV)")
    parser.add_argument("--client", "-c", default="Client", help="Client name (for profile and letterhead branding)")
    parser.add_argument("--output", "-o", default="output", help="Output directory for reports")
    parser.add_argument("--password", "-p", default=None, help="Password for encrypted PDFs")
    parser.add_argument("--formats", nargs="+", default=["excel", "word", "pdf"], help="Report formats to generate (excel, word, pdf)")

    args = parser.parse_args()

    if not args.files:
        print("Usage: python bank_statement_analyzer.py --files statement1.pdf statement2.xlsx --client 'M/s XYZ Traders'")
        print("Or launch the interactive web dashboard with: streamlit run app.py")
        sys.exit(1)

    analyze_and_generate_reports(
        file_paths=args.files,
        client_name=args.client,
        output_dir=args.output,
        password=args.password,
        formats=args.formats
    )

if __name__ == "__main__":
    main()
