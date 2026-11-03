"""
BOI Account Opening Audit & Document Scrutiny System
Data & Session State Manager for Synthetic Banking Datasets
"""

import copy
from datetime import datetime
from typing import Dict, List, Any
from checklists import SAVING_ACCOUNT_CHECKS, CURRENT_ACCOUNT_CHECKS, get_checklist_for_type

# Status Constants
STATUS_PASSED = "Passed"
STATUS_DISCREPANCY = "Discrepancy Found"
STATUS_RECTIFICATION_PENDING = "Rectification Pending"
STATUS_RECTIFIED = "Rectified"
STATUS_RECHECK_COMPLETED = "Re-check Completed"

CHECK_STATUSES = [
    STATUS_PASSED,
    STATUS_DISCREPANCY,
    STATUS_RECTIFICATION_PENDING,
    STATUS_RECTIFIED,
    STATUS_RECHECK_COMPLETED
]

# Account Overall Statuses
ACCOUNT_STATUS_APPROVED = "Approved"
ACCOUNT_STATUS_READY = "Ready for Approval"
ACCOUNT_STATUS_DISCREPANCY = "Discrepancy Found"
ACCOUNT_STATUS_RECTIFICATION = "Rectification Pending"
ACCOUNT_STATUS_UNDER_SCRUTINY = "Under Scrutiny"

# Synthetic Initial Data
INITIAL_DEMO_ACCOUNTS: List[Dict[str, Any]] = [
    {
        "account_id": "SB-BOI-2026-001",
        "customer_name": "Rahul Ramesh Sharma (Synthetic)",
        "account_type": "Saving Account",
        "cif_number": "SYN-CIF-8821430",
        "dummy_account_no": "BOI-SB-9918237401",
        "branch_name": "BOI Nariman Point Branch (Code: 0012)",
        "submission_date": "2026-08-14",
        "risk_category": "Low",
        "auditor_pf": "PF-849201",
        "is_approved": True,
        "approval_date": "2026-08-15 11:30 AM",
        "approval_remarks": "All 8 mandatory KYC and AOF checks verified thoroughly against Finacle. Compliant for account opening.",
        "checks": {
            "SB_CHK_01": {"status": STATUS_PASSED, "remarks": "Masked Aadhaar copy verified against UIDAI QR code. Demographic details match.", "rectification_notes": ""},
            "SB_CHK_02": {"status": STATUS_PASSED, "remarks": "PAN verified on ITD portal via Finacle flag (Status: Active).", "rectification_notes": ""},
            "SB_CHK_03": {"status": STATUS_PASSED, "remarks": "CKYC 14-digit identifier SYN-CKYC-99281 linked in Finacle.", "rectification_notes": ""},
            "SB_CHK_04": {"status": STATUS_PASSED, "remarks": "Clear passport photograph affixed and cross-signed by applicant.", "rectification_notes": ""},
            "SB_CHK_05": {"status": STATUS_PASSED, "remarks": "Officer signature with PF 772109 present on all copies with OSV stamp.", "rectification_notes": ""},
            "SB_CHK_06": {"status": STATUS_PASSED, "remarks": "CPS completely filled. Salaried IT professional, Low AML risk grading.", "rectification_notes": ""},
            "SB_CHK_07": {"status": STATUS_PASSED, "remarks": "Maker & Checker dual verification signatures legible with branch stamp.", "rectification_notes": ""},
            "SB_CHK_08": {"status": STATUS_PASSED, "remarks": "Specimen signature captured in ink and uploaded to Finacle Signature Viewer.", "rectification_notes": ""}
        }
    },
    {
        "account_id": "SB-BOI-2026-002",
        "customer_name": "Sunita Devi Patel (Synthetic)",
        "account_type": "Saving Account",
        "cif_number": "SYN-CIF-8839912",
        "dummy_account_no": "BOI-SB-9918237402",
        "branch_name": "BOI Andheri West Branch (Code: 0045)",
        "submission_date": "2026-08-18",
        "risk_category": "Medium",
        "auditor_pf": "PF-849201",
        "is_approved": False,
        "approval_date": "",
        "approval_remarks": "",
        "checks": {
            "SB_CHK_01": {"status": STATUS_PASSED, "remarks": "Masked Aadhaar copy verified and legible.", "rectification_notes": ""},
            "SB_CHK_02": {"status": STATUS_PASSED, "remarks": "PAN card verified on ITD portal.", "rectification_notes": ""},
            "SB_CHK_03": {"status": STATUS_DISCREPANCY, "remarks": "CKYC record not found in CERSAI portal; upload pending from branch.", "rectification_notes": "Branch notified to upload CKYC data template immediately."},
            "SB_CHK_04": {"status": STATUS_PASSED, "remarks": "Passport photo affixed and verified.", "rectification_notes": ""},
            "SB_CHK_05": {"status": STATUS_DISCREPANCY, "remarks": "Officer signature on AOF page 2 lacks PF Employee Number.", "rectification_notes": "Awaiting verifying officer PF number stamp."},
            "SB_CHK_06": {"status": STATUS_PASSED, "remarks": "CPS filled with Medium risk classification (Retail Trader).", "rectification_notes": ""},
            "SB_CHK_07": {"status": STATUS_PASSED, "remarks": "Dual verification signed by Maker and Checker.", "rectification_notes": ""},
            "SB_CHK_08": {"status": STATUS_PASSED, "remarks": "Specimen signature scanned and uploaded.", "rectification_notes": ""}
        }
    },
    {
        "account_id": "CA-BOI-2026-101",
        "customer_name": "Apex Star Logistics Pvt Ltd (Synthetic)",
        "account_type": "Current Account",
        "cif_number": "SYN-CIF-9901452",
        "dummy_account_no": "BOI-CA-7718902311",
        "branch_name": "BOI Fort Commercial Branch (Code: 0008)",
        "submission_date": "2026-08-12",
        "risk_category": "Medium",
        "auditor_pf": "PF-663219",
        "is_approved": True,
        "approval_date": "2026-08-13 04:15 PM",
        "approval_remarks": "All 11 mandatory current account checks completed. MCA verified, Site inspection report satisfactory.",
        "checks": {
            "CA_CHK_01": {"status": STATUS_PASSED, "remarks": "Certificate of Incorporation verified on MCA21 portal (CIN: SYN-U63090MH2022PTC8991).", "rectification_notes": ""},
            "CA_CHK_02": {"status": STATUS_PASSED, "remarks": "Entity PAN card verified on ITD portal (Status: Active).", "rectification_notes": ""},
            "CA_CHK_03": {"status": STATUS_PASSED, "remarks": "GSTIN and Udhyam Registration verified as 2 independent business proofs.", "rectification_notes": ""},
            "CA_CHK_04": {"status": STATUS_PASSED, "remarks": "Beneficial Ownership declaration obtained for 2 shareholders >10% holding.", "rectification_notes": ""},
            "CA_CHK_05": {"status": STATUS_PASSED, "remarks": "Board Resolution dated 05/08/2026 authorizing Director Rajesh Varma to operate account.", "rectification_notes": ""},
            "CA_CHK_06": {"status": STATUS_PASSED, "remarks": "KYC of both directors verified with OSV stamp.", "rectification_notes": ""},
            "CA_CHK_07": {"status": STATUS_PASSED, "remarks": "CKYC-LE identifier SYN-CKYC-LE-5521 created and linked.", "rectification_notes": ""},
            "CA_CHK_08": {"status": STATUS_PASSED, "remarks": "Pre-opening site inspection report attached with geo-tagged photos of warehouse.", "rectification_notes": ""},
            "CA_CHK_09": {"status": STATUS_PASSED, "remarks": "Declaration obtained regarding non-availment of credit facilities from any bank.", "rectification_notes": ""},
            "CA_CHK_10": {"status": STATUS_PASSED, "remarks": "CPS completed. Projected turnover INR 4.5 Cr. Medium AML risk categorized.", "rectification_notes": ""},
            "CA_CHK_11": {"status": STATUS_PASSED, "remarks": "Dual officer verification completed by Maker (PF-55120) & Checker (PF-44109).", "rectification_notes": ""}
        }
    },
    {
        "account_id": "CA-BOI-2026-102",
        "customer_name": "GreenLeaf Agro Traders LLP (Synthetic)",
        "account_type": "Current Account",
        "cif_number": "SYN-CIF-9903381",
        "dummy_account_no": "BOI-CA-7718902312",
        "branch_name": "BOI Pune Camp Branch (Code: 0102)",
        "submission_date": "2026-08-17",
        "risk_category": "High",
        "auditor_pf": "PF-849201",
        "is_approved": False,
        "approval_date": "",
        "approval_remarks": "",
        "checks": {
            "CA_CHK_01": {"status": STATUS_PASSED, "remarks": "LLP Agreement and MCA Registration Certificate verified.", "rectification_notes": ""},
            "CA_CHK_02": {"status": STATUS_PASSED, "remarks": "Entity PAN card verified.", "rectification_notes": ""},
            "CA_CHK_03": {"status": STATUS_PASSED, "remarks": "GSTIN Certificate and APMC Trade License verified.", "rectification_notes": ""},
            "CA_CHK_04": {"status": STATUS_PASSED, "remarks": "BO declaration signed by designated partners.", "rectification_notes": ""},
            "CA_CHK_05": {"status": STATUS_PASSED, "remarks": "LLP Partner Resolution for account operation verified.", "rectification_notes": ""},
            "CA_CHK_06": {"status": STATUS_PASSED, "remarks": "KYC of 2 designated partners verified.", "rectification_notes": ""},
            "CA_CHK_07": {"status": STATUS_PASSED, "remarks": "CKYC records available for both partners.", "rectification_notes": ""},
            "CA_CHK_08": {"status": STATUS_DISCREPANCY, "remarks": "Pre-opening site inspection report is missing from the audit docket.", "rectification_notes": "Branch manager instructed to carry out physical site inspection and submit report."},
            "CA_CHK_09": {"status": STATUS_RECTIFICATION_PENDING, "remarks": "Credit facility undertaking not submitted on standard BOI format.", "rectification_notes": "Standard undertaking format sent to customer on 18/08/2026."},
            "CA_CHK_10": {"status": STATUS_PASSED, "remarks": "CPS completed with High AML risk grading due to agricultural commodity cash turnover.", "rectification_notes": ""},
            "CA_CHK_11": {"status": STATUS_PASSED, "remarks": "Dual officer signatures verified.", "rectification_notes": ""}
        }
    },
    {
        "account_id": "SB-BOI-2026-003",
        "customer_name": "Priya Ananya Deshmukh (Synthetic)",
        "account_type": "Saving Account",
        "cif_number": "SYN-CIF-8841029",
        "dummy_account_no": "BOI-SB-9918237403",
        "branch_name": "BOI Thane Branch (Code: 0088)",
        "submission_date": "2026-08-19",
        "risk_category": "Low",
        "auditor_pf": "PF-849201",
        "is_approved": False,
        "approval_date": "",
        "approval_remarks": "",
        "checks": {
            "SB_CHK_01": {"status": STATUS_PASSED, "remarks": "Masked Aadhaar copy verified.", "rectification_notes": ""},
            "SB_CHK_02": {"status": STATUS_PASSED, "remarks": "PAN verified against ITD database.", "rectification_notes": ""},
            "SB_CHK_03": {"status": STATUS_PASSED, "remarks": "CKYC search confirmed.", "rectification_notes": ""},
            "SB_CHK_04": {"status": STATUS_PASSED, "remarks": "Customer photograph affixed and verified.", "rectification_notes": ""},
            "SB_CHK_05": {"status": STATUS_RECTIFIED, "remarks": "OSV stamp initially missing PF number; now rectified with PF-771902.", "rectification_notes": "Verifying officer affixed fresh stamp with PF code."},
            "SB_CHK_06": {"status": STATUS_PASSED, "remarks": "CPS completed.", "rectification_notes": ""},
            "SB_CHK_07": {"status": STATUS_PASSED, "remarks": "Dual verification signed by Maker and Checker.", "rectification_notes": ""},
            "SB_CHK_08": {"status": STATUS_RECHECK_COMPLETED, "remarks": "Customer signature specimen re-scanned in high resolution.", "rectification_notes": "Signature re-upload completed in Finacle signature viewer."}
        }
    },
    {
        "account_id": "CA-BOI-2026-103",
        "customer_name": "Nexus Cyber Solutions Pvt Ltd (Synthetic)",
        "account_type": "Current Account",
        "cif_number": "SYN-CIF-9905510",
        "dummy_account_no": "BOI-CA-7718902313",
        "branch_name": "BOI BKC Branch (Code: 0019)",
        "submission_date": "2026-08-20",
        "risk_category": "Medium",
        "auditor_pf": "PF-849201",
        "is_approved": False,
        "approval_date": "",
        "approval_remarks": "",
        "checks": {
            "CA_CHK_01": {"status": STATUS_PASSED, "remarks": "Certificate of Incorporation verified on MCA.", "rectification_notes": ""},
            "CA_CHK_02": {"status": STATUS_PASSED, "remarks": "Entity PAN card verified.", "rectification_notes": ""},
            "CA_CHK_03": {"status": STATUS_DISCREPANCY, "remarks": "Only GSTIN submitted; second independent business proof is required under RBI norms.", "rectification_notes": "Branch advised to collect Udhyam Registration or Shops & Est License."},
            "CA_CHK_04": {"status": STATUS_DISCREPANCY, "remarks": "Beneficial Ownership declaration format not signed by Managing Director.", "rectification_notes": "Fresh BO declaration requested."},
            "CA_CHK_05": {"status": STATUS_PASSED, "remarks": "Board Resolution verified.", "rectification_notes": ""},
            "CA_CHK_06": {"status": STATUS_PASSED, "remarks": "KYC of directors verified.", "rectification_notes": ""},
            "CA_CHK_07": {"status": STATUS_PASSED, "remarks": "CKYC completed.", "rectification_notes": ""},
            "CA_CHK_08": {"status": STATUS_PASSED, "remarks": "Site inspection report satisfactory.", "rectification_notes": ""},
            "CA_CHK_09": {"status": STATUS_PASSED, "remarks": "No credit facility declaration verified.", "rectification_notes": ""},
            "CA_CHK_10": {"status": STATUS_PASSED, "remarks": "CPS completed.", "rectification_notes": ""},
            "CA_CHK_11": {"status": STATUS_PASSED, "remarks": "Dual verification signed.", "rectification_notes": ""}
        }
    }
]


def get_default_accounts() -> List[Dict[str, Any]]:
    """Returns a deep copy of initial synthetic demo accounts."""
    return copy.deepcopy(INITIAL_DEMO_ACCOUNTS)


def calculate_account_metrics(account: Dict[str, Any]) -> Dict[str, Any]:
    """
    Computes audit metrics for a single dummy account:
    - total_checks: Number of mandatory checklist items (8 for SB, 11 for CA)
    - passed_checks: Checks with status 'Passed' or 'Re-check Completed'
    - discrepancy_checks: Checks with status 'Discrepancy Found'
    - rectification_pending: Checks with status 'Rectification Pending'
    - rectified_checks: Checks with status 'Rectified'
    - rechecked_checks: Checks with status 'Re-check Completed'
    - compliance_pct: Percentage of compliant checks (0-100%)
    - is_ready_for_approval: True ONLY when all checks are Passed or Re-check Completed
    - overall_status: 'Approved', 'Ready for Approval', 'Discrepancy Found', 'Rectification Pending', 'Under Scrutiny'
    """
    checks_def = get_checklist_for_type(account.get("account_type", "Saving Account"))
    total_checks = len(checks_def)
    account_checks = account.get("checks", {})

    passed_count = 0
    discrepancy_count = 0
    rectification_pending_count = 0
    rectified_count = 0
    rechecked_count = 0

    discrepant_items = []

    for item in checks_def:
        cid = item["id"]
        check_data = account_checks.get(cid, {"status": STATUS_DISCREPANCY, "remarks": "Pending verification", "rectification_notes": ""})
        status = check_data.get("status", STATUS_DISCREPANCY)

        if status in [STATUS_PASSED, STATUS_RECHECK_COMPLETED]:
            passed_count += 1
            if status == STATUS_RECHECK_COMPLETED:
                rechecked_count += 1
        elif status == STATUS_DISCREPANCY:
            discrepancy_count += 1
            discrepant_items.append({
                "id": cid,
                "title": item["title"],
                "category": item["category"],
                "severity": item["severity"],
                "status": status,
                "remarks": check_data.get("remarks", ""),
                "rectification_notes": check_data.get("rectification_notes", "")
            })
        elif status == STATUS_RECTIFICATION_PENDING:
            rectification_pending_count += 1
            discrepant_items.append({
                "id": cid,
                "title": item["title"],
                "category": item["category"],
                "severity": item["severity"],
                "status": status,
                "remarks": check_data.get("remarks", ""),
                "rectification_notes": check_data.get("rectification_notes", "")
            })
        elif status == STATUS_RECTIFIED:
            rectified_count += 1
            discrepant_items.append({
                "id": cid,
                "title": item["title"],
                "category": item["category"],
                "severity": item["severity"],
                "status": status,
                "remarks": check_data.get("remarks", ""),
                "rectification_notes": check_data.get("rectification_notes", "")
            })

    compliance_pct = round((passed_count / total_checks) * 100, 1) if total_checks > 0 else 0.0
    is_ready = (passed_count == total_checks)

    # Determine overall status
    if account.get("is_approved", False):
        overall_status = ACCOUNT_STATUS_APPROVED
    elif is_ready:
        overall_status = ACCOUNT_STATUS_READY
    elif discrepancy_count > 0:
        overall_status = ACCOUNT_STATUS_DISCREPANCY
    elif rectification_pending_count > 0:
        overall_status = ACCOUNT_STATUS_RECTIFICATION
    else:
        overall_status = ACCOUNT_STATUS_UNDER_SCRUTINY

    return {
        "total_checks": total_checks,
        "passed_checks": passed_count,
        "discrepancy_checks": discrepancy_count,
        "rectification_pending": rectification_pending_count,
        "rectified_checks": rectified_count,
        "rechecked_checks": rechecked_count,
        "pending_issues_count": total_checks - passed_count,
        "compliance_pct": compliance_pct,
        "is_ready_for_approval": is_ready,
        "is_approved": account.get("is_approved", False),
        "overall_status": overall_status,
        "discrepant_items": discrepant_items
    }


def calculate_global_summary(accounts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes global audit metrics across all accounts.
    """
    total_accounts = len(accounts)
    saving_count = 0
    current_count = 0
    total_discrepancies = 0
    pending_discrepancies = 0
    rectified_count = 0
    ready_for_approval_count = 0
    approved_count = 0

    category_discrepancies: Dict[str, int] = {}

    for acc in accounts:
        acc_type = acc.get("account_type", "")
        if "Saving" in acc_type:
            saving_count += 1
        else:
            current_count += 1

        metrics = calculate_account_metrics(acc)

        if metrics["is_approved"]:
            approved_count += 1
        elif metrics["is_ready_for_approval"]:
            ready_for_approval_count += 1

        # Track active and historical discrepancies
        total_discrepancies += metrics["discrepancy_checks"] + metrics["rectification_pending"] + metrics["rectified_checks"]
        pending_discrepancies += metrics["discrepancy_checks"] + metrics["rectification_pending"]
        rectified_count += metrics["rectified_checks"] + metrics["rechecked_checks"]

        # Track discrepancy counts by checklist category
        for disc in metrics["discrepant_items"]:
            cat = disc.get("category", "General")
            category_discrepancies[cat] = category_discrepancies.get(cat, 0) + 1

    return {
        "total_accounts": total_accounts,
        "saving_count": saving_count,
        "current_count": current_count,
        "total_discrepancies": total_discrepancies,
        "pending_discrepancies": pending_discrepancies,
        "rectified_count": rectified_count,
        "ready_for_approval_count": ready_for_approval_count,
        "approved_count": approved_count,
        "category_discrepancies": category_discrepancies
    }


def create_new_dummy_account(
    account_type: str,
    customer_name: str,
    branch_name: str,
    risk_category: str,
    auditor_pf: str
) -> Dict[str, Any]:
    """Creates a new synthetic dummy account for audit training."""
    timestamp_id = datetime.now().strftime("%y%m%d%H%M%S")
    prefix = "SB" if "Saving" in account_type else "CA"
    account_id = f"{prefix}-BOI-2026-{timestamp_id[-4:]}"
    cif_number = f"SYN-CIF-{timestamp_id[-7:]}"
    dummy_acc_no = f"BOI-{prefix}-{timestamp_id}"

    # Initialize all checks to Discrepancy Found / Pending scrutiny
    checks_def = get_checklist_for_type(account_type)
    checks: Dict[str, Dict[str, str]] = {}
    for item in checks_def:
        checks[item["id"]] = {
            "status": STATUS_DISCREPANCY,
            "remarks": "Newly created dummy case – Document scrutiny pending",
            "rectification_notes": ""
        }

    return {
        "account_id": account_id,
        "customer_name": f"{customer_name} (Synthetic)",
        "account_type": account_type,
        "cif_number": cif_number,
        "dummy_account_no": dummy_acc_no,
        "branch_name": branch_name,
        "submission_date": datetime.now().strftime("%Y-%m-%d"),
        "risk_category": risk_category,
        "auditor_pf": auditor_pf,
        "is_approved": False,
        "approval_date": "",
        "approval_remarks": "",
        "checks": checks
    }
