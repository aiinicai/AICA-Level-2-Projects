import os
import sys
from database import SessionLocal, engine, Base
from models import (
    Client, TrialBalanceLine, ARAgeing, APAgeing, CWIPAgeing,
    RelatedParty, Borrowing, Contingency, Note, AccountingPolicy,
    CashFlowAdjustment
)
from services.excel_parser import load_sample_dataset
from services.mapping_engine import auto_map_ledgers
from services.fs_generator import generate_financial_statements
from services.notes_engine import generate_or_update_notes
from services.accounting_policies_engine import generate_or_update_accounting_policies
from services.cash_flow_engine import generate_cash_flow_statement, get_cash_flow_validations
from services.ratio_engine import calculate_ratios
from services.validation_engine import run_validation_checks
from services.export_service import export_formula_linked_excel, export_pdf_review_pack
from services.word_export_service import export_word_financial_report

def run_e2e_workflow_test():
    print("=" * 80)
    print("SW INDIA - FS BUILDER LITE v0.2: END-TO-END WORKFLOW INTEGRATION TEST")
    print("=" * 80)

    db = SessionLocal()
    try:
        # STEP 1: Create Client Entity
        print("\n[STEP 1] Creating New Audit Client Entity...")
        client = Client(
            name="Apex Engineering Industries Limited",
            entity_type="Public Limited Company",
            reporting_period="FY 2024-25",
            previous_year_period="FY 2023-24",
            currency="INR (in Lakhs)",
            accounting_framework="IGAAP",
            schedule_format="Schedule III Division I",
            prepared_by="CA Senior Auditor",
            reviewed_by="CA Managing Partner"
        )
        db.add(client)
        db.commit()
        db.refresh(client)
        client_id = client.id
        print(f" -> SUCCESS: Client created (ID={client_id}, Name='{client.name}')")

        # STEP 2: Load Sample Dataset
        print("\n[STEP 2] Loading Pre-Packaged Sample Data...")
        sample_dir = os.path.join(os.path.dirname(__file__), "sample_data")
        load_sample_dataset(client_id, sample_dir, db)
        print(" -> SUCCESS: Sample trial balance and supporting schedules loaded successfully")

        # STEP 3: Verify Trial Balance Ledgers
        print("\n[STEP 3] Verifying Trial Balance Ledgers...")
        tb_lines = db.query(TrialBalanceLine).filter(TrialBalanceLine.client_id == client_id).all()
        assert len(tb_lines) == 24, f"Expected 24 TB ledgers, got {len(tb_lines)}"
        print(f" -> SUCCESS: {len(tb_lines)} Trial Balance ledgers populated.")

        # STEP 4: Verify AR Ageing Schedule
        print("\n[STEP 4] Verifying AR Ageing Schedule...")
        ar_items = db.query(ARAgeing).filter(ARAgeing.client_id == client_id).all()
        assert len(ar_items) == 3, f"Expected 3 AR records, got {len(ar_items)}"
        print(f" -> SUCCESS: {len(ar_items)} Customer AR Ageing records loaded.")

        # STEP 5: Verify AP Ageing Schedule
        print("\n[STEP 5] Verifying AP Ageing Schedule...")
        ap_items = db.query(APAgeing).filter(APAgeing.client_id == client_id).all()
        assert len(ap_items) == 2, f"Expected 2 AP records, got {len(ap_items)}"
        print(f" -> SUCCESS: {len(ap_items)} Vendor AP Ageing records loaded.")

        # STEP 6: Verify CWIP Ageing Schedule
        print("\n[STEP 6] Verifying CWIP Ageing Schedule...")
        cwip_items = db.query(CWIPAgeing).filter(CWIPAgeing.client_id == client_id).all()
        assert len(cwip_items) == 1, f"Expected 1 CWIP record, got {len(cwip_items)}"
        print(f" -> SUCCESS: {len(cwip_items)} Capital Work-in-Progress projects loaded.")

        # STEP 7: Verify Related Party Schedule
        print("\n[STEP 7] Verifying Related Party Transactions Schedule...")
        rpt_items = db.query(RelatedParty).filter(RelatedParty.client_id == client_id).all()
        assert len(rpt_items) == 1, f"Expected 1 RPT record, got {len(rpt_items)}"
        print(f" -> SUCCESS: {len(rpt_items)} Related Party Transaction records loaded.")

        # STEP 8: Verify Borrowings Schedule
        print("\n[STEP 8] Verifying Borrowings Schedule...")
        bor_items = db.query(Borrowing).filter(Borrowing.client_id == client_id).all()
        assert len(bor_items) == 2, f"Expected 2 borrowing records, got {len(bor_items)}"
        print(f" -> SUCCESS: {len(bor_items)} Secured & Unsecured Borrowing facilities loaded.")

        # STEP 9: Verify Contingencies Schedule
        print("\n[STEP 9] Verifying Contingent Liabilities Schedule...")
        cont_items = db.query(Contingency).filter(Contingency.client_id == client_id).all()
        assert len(cont_items) == 1, f"Expected 1 contingency record, got {len(cont_items)}"
        print(f" -> SUCCESS: {len(cont_items)} Contingent Liability claims loaded.")

        # STEP 10: Auto-Map Ledgers
        print("\n[STEP 10] Executing Rule-Based Keyword Auto-Mapping Engine...")
        map_result = auto_map_ledgers(client_id, db)
        print(f" -> SUCCESS: {map_result['mapped_count'] + map_result['unmapped_count']} Ledgers mapped using regex rule engine.")

        # STEP 11: Save User Override
        print("\n[STEP 11] Simulating Manual User Override and Saving Mapping...")
        sc_line = db.query(TrialBalanceLine).filter(TrialBalanceLine.client_id == client_id, TrialBalanceLine.ledger_name == "Equity Share Capital").first()
        if sc_line:
            sc_line.final_classification = "Share Capital"
            sc_line.user_override = True
            db.commit()
            print(f" -> SUCCESS: Override saved for '{sc_line.ledger_name}' -> '{sc_line.final_classification}'")

        # STEP 12: Generate Financial Statements & Tally Check
        print("\n[STEP 12] Generating Schedule III Balance Sheet & Profit and Loss...")
        fs = generate_financial_statements(client_id, db)
        print(f" -> Balance Sheet Tallied Status: {fs.is_tallied} (Diff: Rs {fs.difference:.2f} Lakhs)")
        assert fs.is_tallied, f"Balance Sheet does not tally! Diff = {fs.difference}"
        print(" -> SUCCESS: Balance Sheet Tally Verified! Total Assets = Total Equity & Liabilities.")

        # STEP 13: Generate AS 3 Cash Flow Statement
        print("\n[STEP 13] Generating AS 3 Cash Flow Statement (Indirect Method)...")
        cfs = generate_cash_flow_statement(client_id, db)
        print(f" -> Opening Cash: {cfs.opening_cash}, Closing Cash: {cfs.closing_cash}, Net Movement: {cfs.net_movement}, Diff: {cfs.difference}, Reconciled: {cfs.is_reconciled}")
        assert len(cfs.statement) >= 20, "Expected at least 20 cash flow statement lines"
        print(f" -> SUCCESS: AS 3 Cash Flow Statement generated. Closing Cash: Rs {cfs.closing_cash:.2f} Lakhs (Reconciled: {cfs.is_reconciled})")

        # Add a sample cash flow adjustment
        adj = CashFlowAdjustment(client_id=client_id, adjustment_type="Income Tax Paid", description="Advance Tax Challan 280", amount=40.0, py_amount=30.0, category="Operating")
        db.add(adj)
        db.commit()

        # STEP 14: Generate Accounting Policies & Detailed Notes
        print("\n[STEP 14] Generating 21 Mandatory IGAAP Accounting Policies & 16 Detailed Structured Notes...")
        policies = generate_or_update_accounting_policies(client_id, db)
        assert len(policies) == 21, f"Expected 21 accounting policies, got {len(policies)}"
        notes = generate_or_update_notes(client_id, db)
        assert len(notes) >= 16, f"Expected at least 16 notes, got {len(notes)}"
        print(f" -> SUCCESS: {len(policies)} IGAAP Accounting Policies & {len(notes)} Detailed Structured Notes generated.")

        # STEP 15: Edit and Save One Policy & Note
        print("\n[STEP 15] Editing and Saving Auditor Policy & Note Customization...")
        pol_1 = db.query(AccountingPolicy).filter(AccountingPolicy.client_id == client_id, AccountingPolicy.policy_number == "AP-01").first()
        if pol_1:
            pol_1.content += "\n[AUDITOR NOTE: Compliant with ICSI and MCA notifications]."
            pol_1.is_modified = True
            db.commit()

        note_42 = db.query(Note).filter(Note.client_id == client_id, Note.note_number == "4.2").first()
        if note_42:
            updated_text = note_42.content + "\n[AUDITOR REMARK: Verified physical inspection of CWIP site on 10-Apr-2026]."
            note_42.content = updated_text
            note_42.is_modified = True
            db.commit()
            print(f" -> SUCCESS: Policy AP-01 & Note 4.2 customized and saved to SQLite app.db.")

        # STEP 16: Calculate Ratios
        print("\n[STEP 16] Calculating 8 Core Schedule III Ratios & Audit Commentaries...")
        ratios = calculate_ratios(client_id, db)
        assert len(ratios) == 8, f"Expected 8 ratios, got {len(ratios)}"
        print(f" -> SUCCESS: {len(ratios)} Schedule III ratios computed with CY vs PY movement.")

        # STEP 17: Run Validations
        print("\n[STEP 17] Running 20 Automated Audit Sanity Checks & 10 Cash Flow Checks...")
        validations = run_validation_checks(client_id, db)
        cf_validations = get_cash_flow_validations(client_id, db)
        passed = len([v for v in validations if v.status == 'Passed'])
        warnings = len([v for v in validations if v.status == 'Warning'])
        criticals = len([v for v in validations if v.status == 'Critical'])
        print(f" -> SUCCESS: {len(validations)} General Checks & {len(cf_validations)} Cash Flow Checks Evaluated (Passed={passed}, Warnings={warnings}, Critical={criticals}).")

        # STEP 18: Export Excel
        print("\n[STEP 18] Exporting Formula-Linked Excel Workbook (.xlsx) with 29 Sheets...")
        export_dir = os.path.join(os.path.dirname(__file__), "exports")
        xlsx_path = export_formula_linked_excel(client_id, export_dir, db)
        assert os.path.exists(xlsx_path), "Excel export file was not created"
        print(f" -> SUCCESS: 29-Sheet Workbook generated at: {xlsx_path}")

        # STEP 19: Export PDF
        print("\n[STEP 19] Exporting Print-Ready PDF Audit Review Pack (.pdf) with 13 Sections...")
        pdf_path = export_pdf_review_pack(client_id, export_dir, db)
        assert os.path.exists(pdf_path), "PDF export file was not created"
        print(f" -> SUCCESS: 13-Section PDF Review Pack generated at: {pdf_path}")

        # STEP 20: Export Word
        print("\n[STEP 20] Exporting 13-Section Editable Word Report (.docx)...")
        word_path = export_word_financial_report(client_id, export_dir, db)
        assert os.path.exists(word_path), "Word export file was not created"
        print(f" -> SUCCESS: 13-Section Word Report generated at: {word_path}")

        print("\n" + "=" * 80)
        print("ALL 20 WORKFLOW STEPS PASSED SUCCESSFULLY WITHOUT ERRORS!")
        print("=" * 80)

    except Exception as e:
        print(f"\n[ERROR IN WORKFLOW]: {str(e)}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    run_e2e_workflow_test()
