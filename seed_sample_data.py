import datetime
import database as db
import auth
import reports

def seed():
    db.init_db()
    auth.create_default_users()
    
    # Check if assignments already exist
    existing = db.get_all_assignments("Partner")
    if existing:
        print(f"Database already contains {len(existing)} assignments.")
        return
        
    today = datetime.date.today()
    
    sample_records = [
        {
            "borrower_name": "Apex Precision Engineering Ltd",
            "bank_name": "State Bank of India",
            "allotment_date": (today - datetime.timedelta(days=22)).strftime("%Y-%m-%d"),
            "acceptance_date": (today - datetime.timedelta(days=21)).strftime("%Y-%m-%d"),
            "data_req_bank_date": (today - datetime.timedelta(days=20)).strftime("%Y-%m-%d"),
            "data_req_borrower_date": (today - datetime.timedelta(days=20)).strftime("%Y-%m-%d"),
            "pending_details": "None (All documents reconciled)",
            "team_person_name": "Priya Verma",
            "team_person_number": "+91 98111 22334",
            "target_visit_date": (today - datetime.timedelta(days=15)).strftime("%Y-%m-%d"),
            "actual_visit_date": (today - datetime.timedelta(days=15)).strftime("%Y-%m-%d"),
            "audit_status": "Report Submitted",
            "review_partner_date": (today - datetime.timedelta(days=8)).strftime("%Y-%m-%d"),
            "report_target_date": (today - datetime.timedelta(days=5)).strftime("%Y-%m-%d"),
            "report_submission_date": (today - datetime.timedelta(days=6)).strftime("%Y-%m-%d"),
            "remarks": "Submitted final signed stock audit report to SBI SME Branch."
        },
        {
            "borrower_name": "Zenith Pharma Chemicals Pvt Ltd",
            "bank_name": "Punjab National Bank",
            "allotment_date": (today - datetime.timedelta(days=14)).strftime("%Y-%m-%d"),
            "acceptance_date": (today - datetime.timedelta(days=13)).strftime("%Y-%m-%d"),
            "data_req_bank_date": (today - datetime.timedelta(days=12)).strftime("%Y-%m-%d"),
            "data_req_borrower_date": (today - datetime.timedelta(days=12)).strftime("%Y-%m-%d"),
            "pending_details": "Ageing of stock > 180 days awaited from CFO",
            "team_person_name": "Amit Gupta",
            "team_person_number": "+91 98222 33445",
            "target_visit_date": (today - datetime.timedelta(days=5)).strftime("%Y-%m-%d"),
            "actual_visit_date": (today - datetime.timedelta(days=5)).strftime("%Y-%m-%d"),
            "audit_status": "Report Preparation",
            "review_partner_date": (today + datetime.timedelta(days=1)).strftime("%Y-%m-%d"),
            "report_target_date": (today + datetime.timedelta(days=2)).strftime("%Y-%m-%d"),
            "report_submission_date": "",
            "remarks": "Drafting observation on slow moving raw materials."
        },
        {
            "borrower_name": "Surya Agro Commodities & Mills",
            "bank_name": "Bank of Baroda",
            "allotment_date": (today - datetime.timedelta(days=30)).strftime("%Y-%m-%d"),
            "acceptance_date": (today - datetime.timedelta(days=29)).strftime("%Y-%m-%d"),
            "data_req_bank_date": (today - datetime.timedelta(days=28)).strftime("%Y-%m-%d"),
            "data_req_borrower_date": (today - datetime.timedelta(days=28)).strftime("%Y-%m-%d"),
            "pending_details": "Warehouse godown receipts and insurance policy copy",
            "team_person_name": "Sneha Patel",
            "team_person_number": "+91 98333 44556",
            "target_visit_date": (today - datetime.timedelta(days=18)).strftime("%Y-%m-%d"),
            "actual_visit_date": "",
            "audit_status": "Delayed",
            "review_partner_date": "",
            "report_target_date": (today - datetime.timedelta(days=4)).strftime("%Y-%m-%d"),
            "report_submission_date": "",
            "remarks": "Borrower postponed physical inspection due to factory maintenance. Escalation sent to Bank Branch Manager."
        },
        {
            "borrower_name": "Metro Logistics & Warehousing Corp",
            "bank_name": "HDFC Bank",
            "allotment_date": (today - datetime.timedelta(days=10)).strftime("%Y-%m-%d"),
            "acceptance_date": (today - datetime.timedelta(days=9)).strftime("%Y-%m-%d"),
            "data_req_bank_date": (today - datetime.timedelta(days=8)).strftime("%Y-%m-%d"),
            "data_req_borrower_date": (today - datetime.timedelta(days=8)).strftime("%Y-%m-%d"),
            "pending_details": "Sanction letter and Drawing Power working from Bank",
            "team_person_name": "Priya Verma",
            "team_person_number": "+91 98111 22334",
            "target_visit_date": (today + datetime.timedelta(days=2)).strftime("%Y-%m-%d"),
            "actual_visit_date": "",
            "audit_status": "Visit Planned",
            "review_partner_date": "",
            "report_target_date": (today + datetime.timedelta(days=6)).strftime("%Y-%m-%d"),
            "report_submission_date": "",
            "remarks": "Physical verification of fleet & inventory scheduled for day after tomorrow."
        },
        {
            "borrower_name": "Kaveri Spinning Mills Ltd",
            "bank_name": "Canara Bank",
            "allotment_date": (today - datetime.timedelta(days=7)).strftime("%Y-%m-%d"),
            "acceptance_date": (today - datetime.timedelta(days=6)).strftime("%Y-%m-%d"),
            "data_req_bank_date": (today - datetime.timedelta(days=5)).strftime("%Y-%m-%d"),
            "data_req_borrower_date": (today - datetime.timedelta(days=5)).strftime("%Y-%m-%d"),
            "pending_details": "Yarn stock register and GST returns (GSTR 3B)",
            "team_person_name": "Amit Gupta",
            "team_person_number": "+91 98222 33445",
            "target_visit_date": (today + datetime.timedelta(days=4)).strftime("%Y-%m-%d"),
            "actual_visit_date": "",
            "audit_status": "Data Awaited from Borrower",
            "review_partner_date": "",
            "report_target_date": (today + datetime.timedelta(days=10)).strftime("%Y-%m-%d"),
            "report_submission_date": "",
            "remarks": "Follow-up email sent to finance manager."
        },
        {
            "borrower_name": "Orbit Solar Renewable Energy Ltd",
            "bank_name": "ICICI Bank",
            "allotment_date": (today - datetime.timedelta(days=16)).strftime("%Y-%m-%d"),
            "acceptance_date": (today - datetime.timedelta(days=15)).strftime("%Y-%m-%d"),
            "data_req_bank_date": (today - datetime.timedelta(days=14)).strftime("%Y-%m-%d"),
            "data_req_borrower_date": (today - datetime.timedelta(days=14)).strftime("%Y-%m-%d"),
            "pending_details": "None",
            "team_person_name": "Sneha Patel",
            "team_person_number": "+91 98333 44556",
            "target_visit_date": (today - datetime.timedelta(days=7)).strftime("%Y-%m-%d"),
            "actual_visit_date": (today - datetime.timedelta(days=7)).strftime("%Y-%m-%d"),
            "audit_status": "Partner Review Completed",
            "review_partner_date": (today - datetime.timedelta(days=1)).strftime("%Y-%m-%d"),
            "report_target_date": (today + datetime.timedelta(days=1)).strftime("%Y-%m-%d"),
            "report_submission_date": "",
            "remarks": "Final printout prepared for signing by Partner."
        },
        {
            "borrower_name": "Galaxy Consumer Electronics",
            "bank_name": "Union Bank of India",
            "allotment_date": (today - datetime.timedelta(days=3)).strftime("%Y-%m-%d"),
            "acceptance_date": (today - datetime.timedelta(days=2)).strftime("%Y-%m-%d"),
            "data_req_bank_date": (today - datetime.timedelta(days=1)).strftime("%Y-%m-%d"),
            "data_req_borrower_date": (today - datetime.timedelta(days=1)).strftime("%Y-%m-%d"),
            "pending_details": "Sanction terms & account statement",
            "team_person_name": "Priya Verma",
            "team_person_number": "+91 98111 22334",
            "target_visit_date": (today + datetime.timedelta(days=5)).strftime("%Y-%m-%d"),
            "actual_visit_date": "",
            "audit_status": "Data Awaited from Bank",
            "review_partner_date": "",
            "report_target_date": (today + datetime.timedelta(days=12)).strftime("%Y-%m-%d"),
            "report_submission_date": "",
            "remarks": "Initial contact made with credit officer."
        },
        {
            "borrower_name": "Royal Ceramic & Granites LLP",
            "bank_name": "State Bank of India",
            "allotment_date": (today - datetime.timedelta(days=25)).strftime("%Y-%m-%d"),
            "acceptance_date": (today - datetime.timedelta(days=24)).strftime("%Y-%m-%d"),
            "data_req_bank_date": (today - datetime.timedelta(days=23)).strftime("%Y-%m-%d"),
            "data_req_borrower_date": (today - datetime.timedelta(days=23)).strftime("%Y-%m-%d"),
            "pending_details": "None",
            "team_person_name": "Amit Gupta",
            "team_person_number": "+91 98222 33445",
            "target_visit_date": (today - datetime.timedelta(days=17)).strftime("%Y-%m-%d"),
            "actual_visit_date": (today - datetime.timedelta(days=17)).strftime("%Y-%m-%d"),
            "audit_status": "Closed",
            "review_partner_date": (today - datetime.timedelta(days=10)).strftime("%Y-%m-%d"),
            "report_target_date": (today - datetime.timedelta(days=8)).strftime("%Y-%m-%d"),
            "report_submission_date": (today - datetime.timedelta(days=9)).strftime("%Y-%m-%d"),
            "remarks": "Completed successfully. Bank acknowledged receipt of report."
        }
    ]
    
    for rec in sample_records:
        db.create_assignment(rec, user_name="Seed Script")
        
    print(f"Successfully seeded {len(sample_records)} realistic stock audit assignments.")
    
    # Also write out sample template excel file
    tpl_bytes = reports.generate_sample_excel_template()
    with open("sample_stock_audit_import_template.xlsx", "wb") as f:
        f.write(tpl_bytes)
    print("Generated sample_stock_audit_import_template.xlsx")

if __name__ == "__main__":
    seed()
