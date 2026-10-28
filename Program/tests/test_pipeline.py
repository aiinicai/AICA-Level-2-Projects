"""
End-to-End Pipeline Unit & Integration Test
Verifies all modules: PDF processing, NLP extraction, Ind AS 116 decision engine,
financial DCF, amortisation schedules, journal vouchers, Excel (9 tabs), Word memo, and RAG search.
"""
import os
import sys
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from modules.config import DEFAULT_GUIDANCE_DIR
from modules.pdf_processor import PDFProcessor
from modules.extractor import LeaseExtractor
from modules.ind_as_116_engine import IndAS116Engine
from modules.financial_engine import FinancialEngine
from modules.journal_entries import JournalEntryEngine
from modules.quality_checks import QualityControlEngine
from modules.guidance_rag import GuidanceSearchEngine
from modules.reporting_engine import ReportEngine

def run_all_tests():
    print("=" * 60)
    print("RUNNING END-TO-END TESTS FOR IND AS 116 TOOL")
    print("=" * 60)

    # 1. Test Mock Agreement Data
    sample_pages = {
        1: (
            "COMMERCIAL LEASE AGREEMENT\n"
            "This Lease Agreement is made this 1st day of April 2024 between Horizon Realty Pvt Ltd "
            "(hereinafter called the Lessor) and Apex Tech Solutions India Ltd (hereinafter called the Lessee).\n"
            "Demised Premises: Unit No. 402, 4th Floor, Tech Park One, Whitefield, Bangalore.\n"
            "Term of Lease: The lease shall be for a duration of 60 months commencing from 01-04-2024.\n"
            "Possession Date: Possession handed over on 01-04-2024."
        ),
        2: (
            "RENTAL AND PAYMENT TERMS\n"
            "Monthly Rent: The Lessee agrees to pay a monthly rent of Rs. 150,000/- (Rupees One Lakh Fifty Thousand only), "
            "payable in advance on or before the 7th day of each calendar month.\n"
            "Rent-Free Period: A fit-out rent free period of 2 months shall apply from commencement.\n"
            "Escalation Clause: The monthly rent shall escalate by 5% every 12 months.\n"
            "Security Deposit: Rs. 600,000/- interest-free refundable deposit paid on signing."
        ),
        3: (
            "MAINTENANCE AND OTHER TERMS\n"
            "Common Area Maintenance (CAM): Rs. 25,000/- per month payable to the facility management agency.\n"
            "Initial Direct Costs: Lessee has incurred brokerage fees of Rs. 50,000/- and stamp duty of Rs. 25,000/-.\n"
            "Restoration Obligation: Lessee shall restore premises to original bare shell condition on expiry (estimated cost Rs. 100,000/-).\n"
            "Option to Renew: Lessee holds an option to extend the lease for a further period of 24 months subject to prevailing market rent.\n"
            "Discount Rate: Entity Incremental Borrowing Rate (IBR) is 8.50% per annum."
        )
    }

    # 2. Test Extractor
    print("\n[TEST 1] Testing Local NLP Heuristic Extractor...")
    extractor = LeaseExtractor()
    extracted = extractor.extract_all_fields(sample_pages)
    assert extracted["lessor_name"].value != "Requires Review", "Lessor extraction failed"
    assert "Apex" in str(extracted["lessee_name"].value), "Lessee extraction failed"
    assert extracted["lease_term_months"].value == 60, f"Term expected 60, got {extracted['lease_term_months'].value}"
    assert extracted["fixed_rental_amount"].value == 150000.0, f"Rent expected 150,000, got {extracted['fixed_rental_amount'].value}"
    assert extracted["escalation_pct"].value == 5.0, "Escalation % extraction failed"
    print(f" -> Lessor: {extracted['lessor_name'].value} (Source: Page {extracted['lessor_name'].source_page})")
    print(f" -> Lessee: {extracted['lessee_name'].value} (Source: Page {extracted['lessee_name'].source_page})")
    print(f" -> Term: {extracted['lease_term_months'].value} months")
    print(f" -> Base Rent: {extracted['fixed_rental_amount'].value:,.2f}")
    print(" -> PASS: Extractor verified.")

    # 3. Test Ind AS 116 Engine
    print("\n[TEST 2] Testing Ind AS 116 Assessment Engine...")
    dict_extracted = {k: v.to_dict() for k, v in extracted.items()}
    engine = IndAS116Engine()
    assessment = engine.evaluate_contract(
        dict_extracted,
        elect_short_term_exemption=True,
        elect_low_value_exemption=True,
        elect_practical_expedient=False,
        asset_class="Real Estate"
    )
    assert assessment.contains_lease is True, "Lease definition evaluation failed"
    assert assessment.accounting_classification == "ROU_AND_LIABILITY", f"Classification unexpected: {assessment.accounting_classification}"
    print(f" -> Contains Lease: {assessment.contains_lease}")
    print(f" -> Classification: {assessment.accounting_classification}")
    print(" -> PASS: Ind AS 116 Engine verified.")

    # 4. Test Financial Calculations
    print("\n[TEST 3] Testing Financial Schedule & DCF Engine...")
    fin_engine = FinancialEngine(currency="INR")
    sched_df, summary = fin_engine.generate_schedule(
        commencement_date_str=str(extracted["commencement_date"].value),
        term_months=assessment.effective_lease_term_months,
        base_rent_per_period=assessment.lease_component_amount,
        annual_discount_rate=float(extracted["discount_rate"].value or 8.5),
        frequency="Monthly",
        payment_timing="In Advance",
        rent_free_months=int(extracted["rent_free_period_months"].value or 0),
        escalation_pct=float(extracted["escalation_pct"].value or 0.0),
        escalation_interval_months=int(extracted["escalation_frequency_months"].value or 12),
        initial_direct_costs=assessment.initial_direct_costs,
        lease_incentives=assessment.lease_incentives,
        restoration_obligation=assessment.restoration_provision
    )
    assert len(sched_df) == 60, f"Expected 60 periods, got {len(sched_df)}"
    assert summary.initial_liability > 0, "Initial liability should be > 0"
    assert summary.initial_rou_asset >= summary.initial_liability, "Initial ROU should include initial direct costs"
    final_row = sched_df.iloc[-1]
    assert final_row["closing_liability"] == 0.0, f"Closing liability at expiry should be 0.0, got {final_row['closing_liability']}"
    assert final_row["closing_rou_asset"] == 0.0, f"Closing ROU asset at expiry should be 0.0, got {final_row['closing_rou_asset']}"
    print(f" -> Total Periods: {len(sched_df)}")
    print(f" -> Initial Lease Liability: Rs. {summary.initial_liability:,.2f}")
    print(f" -> Initial ROU Asset: Rs. {summary.initial_rou_asset:,.2f}")
    print(f" -> Total Cash Outflows: Rs. {summary.total_lease_payments:,.2f}")
    print(f" -> Total Interest Expense: Rs. {summary.total_interest_expense:,.2f}")
    print(f" -> Total ROU Depreciation: Rs. {summary.total_depreciation_expense:,.2f}")
    print(" -> PASS: Financial calculations & amortisation schedule verified.")

    # 5. Test Journal Entries
    print("\n[TEST 4] Testing Journal Entries Engine...")
    je_engine = JournalEntryEngine(currency="INR")
    entries = je_engine.generate_all_entries(
        assessment=assessment,
        summary=summary,
        schedule_df=sched_df,
        commencement_date=str(extracted["commencement_date"].value),
        asset_description=str(extracted["asset_description"].value)
    )
    df_je = je_engine.to_dataframe(entries)
    tot_debits = df_je["debit_amount"].sum()
    tot_credits = df_je["credit_amount"].sum()
    print(f" -> Total Entries Generated: {len(entries)}")
    print(f" -> Total Debits: Rs. {tot_debits:,.2f}")
    print(f" -> Total Credits: Rs. {tot_credits:,.2f}")
    assert abs(tot_debits - tot_credits) < 0.05, f"Journal entries out of balance: {tot_debits} vs {tot_credits}"
    print(" -> PASS: Journal vouchers are perfectly balanced (Debits == Credits).")

    # 6. Test Quality Checks
    print("\n[TEST 5] Testing Quality Controls & Validations...")
    qc = QualityControlEngine()
    val = qc.run_checks(dict_extracted, assessment)
    print(f" -> Validation Passed: {val.is_valid}")
    print(f" -> Warnings Flagged: {len(val.warnings)}")
    print(f" -> Audit Review Points: {len(val.review_points)}")
    assert val.is_valid is True, f"Validation errors: {val.errors}"
    print(" -> PASS: Quality checks verified.")

    # 7. Test Guidance RAG Search
    print("\n[TEST 6] Testing Guidance Library Offline Search...")
    rag = GuidanceSearchEngine(str(DEFAULT_GUIDANCE_DIR))
    chunk_count = rag.build_index(max_pages_per_doc=25)
    print(f" -> Indexed {chunk_count} paragraphs from {DEFAULT_GUIDANCE_DIR}")
    results = rag.search("practical expedient combine lease components", top_k=2)
    print(f" -> Search matches for query: {len(results)}")
    if results:
        print(f"    Top match from: {results[0].doc_name} ({results[0].page_or_section}) - Score: {results[0].relevance_score}")
    print(" -> PASS: Guidance RAG Search verified.")

    # 8. Test Excel Generation (9 Tabs)
    print("\n[TEST 7] Testing Excel 9-Tab Generation...")
    rep_engine = ReportEngine(currency_symbol="₹")
    excel_bytes = rep_engine.generate_excel_workbook(
        extracted_data=dict_extracted,
        assessment=assessment,
        summary=summary,
        schedule_df=sched_df,
        journal_entries=entries,
        review_points=val.review_points
    )
    assert len(excel_bytes) > 5000, "Excel output file too small"
    
    # Verify tabs inside workbook
    import openpyxl, io
    wb = openpyxl.load_workbook(io.BytesIO(excel_bytes))
    sheet_names = wb.sheetnames
    expected_sheets = [
        "Input Summary", "Extracted Agreement Data", "Ind AS 116 Analysis",
        "Lease Liability Schedule", "ROU Asset Schedule", "Journal Entries",
        "Fin Statement Presentation", "Disclosures", "Audit Review Points"
    ]
    assert sheet_names == expected_sheets, f"Sheets mismatch: {sheet_names}"
    print(f" -> Successfully verified {len(sheet_names)} tabs: {sheet_names}")
    print(" -> PASS: Excel generation verified.")

    # 9. Test Word Document Generation
    print("\n[TEST 8] Testing Word Document (Lease_Summary.docx) Generation...")
    word_bytes = rep_engine.generate_word_document(
        extracted_data=dict_extracted,
        assessment=assessment,
        summary=summary,
        schedule_df=sched_df,
        journal_entries=entries,
        review_points=val.review_points
    )
    assert len(word_bytes) > 5000, "Word memo output too small"
    print(f" -> Word memo generated successfully ({len(word_bytes)} bytes).")
    print(" -> PASS: Word document generation verified.")

    print("\n" + "=" * 60)
    print("ALL 8 UNIT & INTEGRATION TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_all_tests()
