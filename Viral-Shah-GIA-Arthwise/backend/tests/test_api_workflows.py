import os
import uuid
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_api_root():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "preliminary estimates" in data["regulatory_notice"]

def test_auth_login_success_and_failure():
    # Valid analyst login
    res = client.post("/api/v1/auth/login", json={"email": "analyst@giaarthwise.com", "password": "Analyst@123"})
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["user"]["role"] == "analyst"
    
    # Invalid password
    res_bad = client.post("/api/v1/auth/login", json={"email": "analyst@giaarthwise.com", "password": "WrongPassword"})
    assert res_bad.status_code == 401

def test_end_to_end_proposal_and_checklist_workflow():
    # 1. Login as Analyst
    login_res = client.post("/api/v1/auth/login", json={"email": "analyst@giaarthwise.com", "password": "Analyst@123"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Create Client
    cli_res = client.post("/api/v1/clients", headers=headers, json={
        "primary_contact_name": "Sample Borrower",
        "phone": "+1 202 555 0102",
        "email": "borrower@example.com",
        "constitution": "pvt_ltd",
        "address": "123 Example Street",
        "city": "Vadodara",
        "state": "Gujarat",
        "pin_code": "390023"
    })
    assert cli_res.status_code == 200
    client_id = cli_res.json()["id"]
    
    # 3. Create Entity
    ent_res = client.post(f"/api/v1/clients/{client_id}/entities", headers=headers, json={
        "legal_name": "GIA Tech Solutions Private Limited",
        "trade_name": "GIA Tech",
        "constitution": "pvt_ltd",
        "pan": "AAACX0000M",
        "cin": "U00000GJ2000PTC000000",
        "udyam_reg": "UDYAM-GJ-24-0012345",
        "date_of_incorporation": "2020-08-15",
        "business_activity": "Enterprise Cybersecurity & Managed Threat Detection"
    })
    assert ent_res.status_code == 200
    entity_id = ent_res.json()["id"]
    assert ent_res.json()["pan_masked"] == "AA*****M"
    
    # 4. Add Promoter
    prom_res = client.post(f"/api/v1/clients/entities/{entity_id}/promoters", headers=headers, json={
        "name": "Sample Borrower",
        "role": "director",
        "pan": "ACAPX0000P",
        "ownership_pct": 51.0,
        "cibil_score": 745,
        "mobile": "+1 202 555 0102",
        "email": "director@example.com"
    })
    assert prom_res.status_code == 200
    assert prom_res.json()["pan_masked"] == "AC*****P"
    
    # 5. Create Proposal
    prop_res = client.post("/api/v1/proposals", headers=headers, json={
        "client_id": client_id,
        "entity_id": entity_id,
        "product_type": "cash_credit_od",
        "requested_amount": 10000000.00, # 1 Crore
        "tenure_months": 12,
        "purpose": "Working capital limits against debtors & enterprise contracts",
        "target_rate": 9.25
    })
    assert prop_res.status_code == 200
    proposal_id = prop_res.json()["id"]
    
    # 6. Verify 7-column checklist was auto-populated
    chk_res = client.get(f"/api/v1/proposals/{proposal_id}/checklist", headers=headers)
    assert chk_res.status_code == 200
    items = chk_res.json()
    assert len(items) >= 10
    first_item = items[0]
    
    # 7. Test Checklist Validation: Marking Not Applicable requires na_reason
    fail_res = client.patch(
        f"/api/v1/proposals/{proposal_id}/checklist/{first_item['id']}",
        headers=headers,
        json={"is_applicable": False, "na_reason": ""}
    )
    assert fail_res.status_code == 400
    assert "justification reason must be specified" in fail_res.json()["detail"]
    
    # Succeeds when na_reason is provided
    succ_res = client.patch(
        f"/api/v1/proposals/{proposal_id}/checklist/{first_item['id']}",
        headers=headers,
        json={"is_applicable": False, "na_reason": "Entity was incorporated in 2024; FY 2023-24 not applicable"}
    )
    assert succ_res.status_code == 200
    assert succ_res.json()["is_applicable"] is False
    assert succ_res.json()["na_reason"] != ""
    
    # 8. Test Financial Evaluation Endpoint
    eval_res = client.post(f"/api/v1/proposals/{proposal_id}/evaluation", headers=headers, json={
        "proposal_id": proposal_id,
        "monthly_income_or_cash_accrual": 650000.0,
        "total_existing_emi": 50000.0,
        "interest_rate": 9.25,
        "tenure_months": 60,
        "assessed_collateral_value": 18000000.0, # 1.8 Cr
        "max_foir_pct": 60.0,
        "max_ltv_pct": 75.0,
        "min_dscr_target": 1.35,
        "pat": 3500000.0,
        "depreciation": 1200000.0,
        "finance_costs": 800000.0,
        "existing_term_debt_repayment": 1000000.0,
        "ebitda": 5500000.0,
        "current_assets": 22000000.0,
        "current_liabilities": 14000000.0,
        "inventory": 2000000.0,
        "tangible_net_worth": 15000000.0,
        "total_outside_liabilities": 18000000.0,
        "turnover": 48000000.0,
        "sundry_debtors": 8500000.0,
        "sundry_creditors": 4200000.0,
        "cogs": 26000000.0,
        "total_purchases": 24000000.0
    })
    assert eval_res.status_code == 200
    eval_data = eval_res.json()
    assert float(eval_data["preliminary_eligible_amount"]) > 0
    assert "preliminary estimates" in eval_data["disclaimer"]
    
    # 9. Test Lender Comparison
    lend_res = client.get(f"/api/v1/lenders/compare/{proposal_id}", headers=headers)
    assert lend_res.status_code == 200
    lenders_fit = lend_res.json()
    assert len(lenders_fit) > 0
    
    # 10. Test Reports (Excel, Word, PDF)
    xlsx_res = client.get(f"/api/v1/proposals/{proposal_id}/reports/cma-excel", headers=headers)
    assert xlsx_res.status_code == 200
    assert len(xlsx_res.content) > 1000
    
    docx_res = client.get(f"/api/v1/proposals/{proposal_id}/reports/dpr-word", headers=headers)
    assert docx_res.status_code == 200
    assert len(docx_res.content) > 1000

    pdf_res = client.get(f"/api/v1/proposals/{proposal_id}/reports/bank-pdf", headers=headers)
    assert pdf_res.status_code == 200
    assert len(pdf_res.content) > 1000

    # 11. Test Proposal Closed Won / Closed Lost Status Lifecycle
    won_res = client.patch(
        f"/api/v1/proposals/{proposal_id}/status",
        headers=headers,
        json={"status": "closed_won", "review_notes": "Sanction received from State Bank of India"}
    )
    assert won_res.status_code == 200
    assert won_res.json()["status"] == "closed_won"

    lost_res = client.patch(
        f"/api/v1/proposals/{proposal_id}/status",
        headers=headers,
        json={"status": "closed_lost", "review_notes": "Borrower postponed expansion"}
    )
    assert lost_res.status_code == 200
    assert lost_res.json()["status"] == "closed_lost"

    # 12. Test Proposal Deletion & Cascading Cleanup
    del_res = client.delete(f"/api/v1/proposals/{proposal_id}", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "success"

    # 13. Verify proposal is deleted and returns 404
    get_del_res = client.get(f"/api/v1/proposals/{proposal_id}", headers=headers)
    assert get_del_res.status_code == 404

    # 14. Clean up test client
    client.delete(f"/api/v1/clients/{client_id}", headers=headers)


def test_admin_only_user_creation_and_password_reset():
    # 1. Login as Analyst (Non-Admin)
    analyst_login = client.post("/api/v1/auth/login", json={"email": "analyst@giaarthwise.com", "password": "Analyst@123"})
    analyst_token = analyst_login.json()["access_token"]
    analyst_headers = {"Authorization": f"Bearer {analyst_token}"}

    # 2. Login as Admin
    admin_login = client.post("/api/v1/auth/login", json={"email": "admin@giaarthwise.com", "password": "Admin@123"})
    admin_token = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 3. Non-admin attempting to create a user should be rejected with 403 Forbidden
    non_admin_create = client.post("/api/v1/admin/users", headers=analyst_headers, json={
        "email": "hacker@giaarthwise.com",
        "password": "Password@123",
        "full_name": "Unauthorized User",
        "role": "analyst"
    })
    assert non_admin_create.status_code == 403

    # Public registration without admin token should also be rejected with 403 or 401
    public_register = client.post("/api/v1/auth/register", json={
        "email": "public@giaarthwise.com",
        "password": "Password@123",
        "full_name": "Public Registrant",
        "role": "analyst"
    })
    assert public_register.status_code in [401, 403]

    # 4. Administrator creating a new user should succeed with 200 OK
    test_user_email = f"testops_{os.urandom(3).hex()}@giaarthwise.com"
    admin_create = client.post("/api/v1/admin/users", headers=admin_headers, json={
        "email": test_user_email,
        "password": "InitialPassword@123",
        "full_name": "Test Operations Lead",
        "role": "analyst"
    })
    assert admin_create.status_code == 200
    created_user = admin_create.json()
    assert created_user["email"] == test_user_email
    assert created_user["role"] == "analyst"
    user_id = created_user["id"]

    # 5. Verify the new user can log in with initial password
    login_new = client.post("/api/v1/auth/login", json={"email": test_user_email, "password": "InitialPassword@123"})
    assert login_new.status_code == 200

    # 6. Non-admin attempting to reset password should be rejected with 403 Forbidden
    non_admin_reset = client.post(f"/api/v1/admin/users/{user_id}/reset-password", headers=analyst_headers, json={
        "new_password": "HackedPassword@123"
    })
    assert non_admin_reset.status_code == 403

    # 7. Administrator resetting password should succeed
    admin_reset = client.post(f"/api/v1/admin/users/{user_id}/reset-password", headers=admin_headers, json={
        "new_password": "NewResetPassword@999"
    })
    assert admin_reset.status_code == 200
    assert admin_reset.json()["status"] == "success"

    # 8. Verify old password no longer works
    login_old = client.post("/api/v1/auth/login", json={"email": test_user_email, "password": "InitialPassword@123"})
    assert login_old.status_code == 401

    # 9. Verify new reset password works
    login_reset = client.post("/api/v1/auth/login", json={"email": test_user_email, "password": "NewResetPassword@999"})
    assert login_reset.status_code == 200
    assert login_reset.json()["user"]["email"] == test_user_email


def test_pan_validation_api():
    # 1. Valid Company PAN
    res = client.post("/api/v1/master/pan/validate", json={
        "pan": "AAACX0000M",
        "entity_name": "GIA Tech Solutions",
        "constitution": "pvt_ltd"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["is_valid"] is True
    assert data["status"] == "VALID"
    assert data["constitution_match"] is True
    assert data["entity_type_code"] == "C"

    # 2. Constitution Mismatch: Individual PAN for Pvt Ltd Company
    res_mismatch = client.post("/api/v1/master/pan/validate", json={
        "pan": "ABCPV1234F",
        "entity_name": "Apex Enterprise Ltd",
        "constitution": "pvt_ltd"
    })
    assert res_mismatch.status_code == 200
    data_mismatch = res_mismatch.json()
    assert data_mismatch["is_valid"] is True
    assert data_mismatch["constitution_match"] is False
    assert "Expected 4th character 'C'" in data_mismatch["message"]

    # 3. Invalid Syntactic Format
    res_bad = client.post("/api/v1/master/pan/validate", json={"pan": "INVALID123"})
    assert res_bad.status_code == 200
    data_bad = res_bad.json()
    assert data_bad["is_valid"] is False
    assert data_bad["status"] == "INVALID"


def test_city_and_state_lov_and_custom_addition():
    # 1. Fetch Indian States list
    res_states = client.get("/api/v1/master/states")
    assert res_states.status_code == 200
    states = res_states.json()
    assert "Gujarat" in states
    assert "Maharashtra" in states
    assert len(states) >= 36

    # 2. Search Cities
    res_cities = client.get("/api/v1/master/cities?query=Vadodara")
    assert res_cities.status_code == 200
    cities = res_cities.json()
    assert any(c["city"] == "Vadodara" and c["state"] == "Gujarat" for c in cities)

    # 3. Add Custom City (User can type any new city without restriction)
    custom_city_name = f"CustomTown_{os.urandom(2).hex()}"
    res_add = client.post("/api/v1/master/cities", json={
        "city": custom_city_name,
        "state": "Gujarat",
        "tier": "tier3"
    })
    assert res_add.status_code == 200
    assert res_add.json()["city"] == custom_city_name


def test_white_label_company_creation_and_switching():
    # 1. Login as Admin
    admin_login = client.post("/api/v1/auth/login", json={"email": "admin@giaarthwise.com", "password": "Admin@123"})
    admin_token = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. Get active company
    res_active = client.get("/api/v1/companies/active")
    assert res_active.status_code == 200
    assert "brand_name" in res_active.json()

    # 3. Create a new white-label company
    code = f"APX{os.urandom(2).hex().upper()}"
    res_create = client.post("/api/v1/companies", headers=admin_headers, json={
        "company_code": code,
        "company_name": f"Apex Capital Advisory {code} Private Limited",
        "brand_name": f"ApexCapital_{code}",
        "tagline": "Enterprise Syndication Suite",
        "primary_color": "#0d2b45",
        "secondary_color": "#d97736",
        "city": "Mumbai",
        "state": "Maharashtra",
        "pan": "AABCA9999M",
        "gstin": "27AABCA9999M1Z5"
    })
    assert res_create.status_code == 200
    new_comp = res_create.json()
    new_comp_id = new_comp["id"]

    # 4. Switch active white-label company
    res_switch = client.post(f"/api/v1/companies/{new_comp_id}/set-active", headers=admin_headers)
    assert res_switch.status_code == 200
    assert res_switch.json()["is_active"] is True

    # 5. Verify /companies/active now reflects new company
    res_new_active = client.get("/api/v1/companies/active")
    assert res_new_active.status_code == 200
    assert res_new_active.json()["brand_name"] == f"ApexCapital_{code}"

    # 6. Switch back to default GIA_Arthwise
    companies = client.get("/api/v1/companies", headers=admin_headers).json()
    gia_comp = [c for c in companies if c["company_code"] == "GIA"][0]
    client.post(f"/api/v1/companies/{gia_comp['id']}/set-active", headers=admin_headers)

def test_deleted_customer_not_shown_in_proposals_or_client_list():
    # 1. Login as Analyst
    login_res = client.post("/api/v1/auth/login", json={"email": "analyst@giaarthwise.com", "password": "Analyst@123"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Onboard customer with proposal
    suffix = os.urandom(3).hex().upper()
    onboard_res = client.post("/api/v1/clients/onboard", headers=headers, json={
        "customer_name": f"Test Customer {suffix} Pvt Ltd",
        "primary_contact": f"Test Contact {suffix}",
        "phone": "+91 99887 66554",
        "email": f"test_{suffix.lower()}@customer.com",
        "constitution": "pvt_ltd",
        "address": "402 Corporate Park",
        "city": "Ahmedabad",
        "state": "Gujarat",
        "pin_code": "380015",
        "pan": "AABCT1234F",
        "create_proposal": True,
        "product_type": "cash_credit_od",
        "requested_amount": 5000000,
        "tenure_months": 36
    })
    assert onboard_res.status_code == 200
    data = onboard_res.json()
    client_id = data["client_id"]
    proposal_id = data["proposal_id"]
    assert client_id is not None
    assert proposal_id is not None

    # 3. Client appears in active clients list
    clients_res = client.get("/api/v1/clients", headers=headers)
    assert clients_res.status_code == 200
    active_client_ids = [c["id"] for c in clients_res.json()]
    assert client_id in active_client_ids

    # 4. Delete the proposal
    del_res = client.delete(f"/api/v1/proposals/{proposal_id}", headers=headers)
    assert del_res.status_code == 200

    # 5. Customer must NO LONGER appear in active clients list
    clients_res_after = client.get("/api/v1/clients", headers=headers)
    assert clients_res_after.status_code == 200
    active_client_ids_after = [c["id"] for c in clients_res_after.json()]
    assert client_id not in active_client_ids_after, "Deleted customer must not appear in clients list!"

    # 6. Attempting to create proposal for deleted customer must fail
    bad_prop_res = client.post("/api/v1/proposals", headers=headers, json={
        "client_id": client_id,
        "entity_id": data["entity_id"],
        "product_type": "working_capital",
        "requested_amount": 1000000,
        "tenure_months": 12,
        "purpose": "Test deleted client protection",
        "target_rate": 9.5
    })
    assert bad_prop_res.status_code == 400
    assert "deleted" in bad_prop_res.json()["detail"].lower()

    # 7. Test direct client deletion endpoint with a separate client
    cli2_res = client.post("/api/v1/clients", headers=headers, json={
        "primary_contact_name": f"Direct Del {suffix}",
        "phone": "+91 99887 00000",
        "email": f"direct_del_{suffix.lower()}@test.com",
        "constitution": "proprietorship",
        "address": "Shop 12",
        "city": "Surat",
        "state": "Gujarat",
        "pin_code": "395001"
    })
    assert cli2_res.status_code == 200
    cli2_id = cli2_res.json()["id"]

    del_cli2_res = client.delete(f"/api/v1/clients/{cli2_id}", headers=headers)
    assert del_cli2_res.status_code == 200
    assert del_cli2_res.json()["status"] == "success"

    # Confirm it cannot be fetched
    get_cli2 = client.get(f"/api/v1/clients/{cli2_id}", headers=headers)
    assert get_cli2.status_code == 404


def test_client_naming_and_requirements_update_and_isolated_dossier():
    """
    Test suite for:
    1. Client code format: CLI-{CLEAN_PREFIX}-{00001}
    2. Proposal code format: PROP-{CLEAN_PREFIX}-{00001}
    3. Isolated case document library: Empty case returns 0 files, no leak of sample reference files
    4. Loan requirements modification endpoint: Updates facility amount, tenure, etc. with audit tracking
    """
    suffix = uuid.uuid4().hex[:6].upper()
    admin_login = client.post("/api/v1/auth/login", json={"email": "admin@giaarthwise.com", "password": "Admin@123"})
    admin_token = admin_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Onboard client with corporate name "Aditya Logistics ... Pvt Ltd"
    client_name = f"Aditya Logistics {suffix} Pvt Ltd"
    onboard_res = client.post("/api/v1/clients/onboard", headers=headers, json={
        "customer_name": client_name,
        "primary_contact": f"Aditya Birla {suffix}",
        "phone": "+91 98765 00000",
        "email": f"aditya_{suffix.lower()}@testcorp.com",
        "constitution": "pvt_ltd",
        "address": "401 Corporate Park",
        "city": "Mumbai",
        "state": "Maharashtra",
        "pin_code": "400001",
        "pan": "AAACA1234D",
        "create_proposal": True,
        "product_type": "term_loan",
        "requested_amount": 7500000.0,
        "tenure_months": 60,
        "purpose": "Warehouse expansion"
    })
    assert onboard_res.status_code == 200, onboard_res.text
    data = onboard_res.json()
    proposal_id = data["proposal_id"]
    proposal_code = data["proposal_code"]

    # Verify naming formats
    assert proposal_code.startswith("PROP-ADITYA-")
    # Suffix should be 5 digits
    seq_part = proposal_code.split("-")[-1]
    assert len(seq_part) == 5 and seq_part.isdigit()

    # 2. Check dossier library isolation: must NOT leak reference docs (0 files for a clean case)
    dossier_res = client.get(f"/api/v1/proposals/{proposal_id}/documents/dossier-library", headers=headers)
    assert dossier_res.status_code == 200
    dossier_data = dossier_res.json()
    assert isinstance(dossier_data, list)
    assert len(dossier_data) == 0, f"Expected 0 isolated files, got {len(dossier_data)}"

    # 3. Modify loan requirements
    update_res = client.patch(f"/api/v1/proposals/{proposal_id}/requirements", headers=headers, json={
        "product_type": "working_capital",
        "requested_amount": 12000000.0,
        "tenure_months": 36,
        "target_rate": 8.75,
        "purpose": "Updated working capital and raw material procurement"
    })
    assert update_res.status_code == 200
    upd_data = update_res.json()
    assert float(upd_data["requested_amount"]) == 12000000.0
    assert upd_data["product_type"] == "working_capital"
    assert upd_data["tenure_months"] == 36
    assert float(upd_data["target_rate"]) == 8.75
    assert "working capital" in upd_data["purpose"]

    # Verify persisted proposal reflects changes
    get_prop = client.get(f"/api/v1/proposals/{proposal_id}", headers=headers)
    assert get_prop.status_code == 200
    prop = get_prop.json()
    assert float(prop["requested_amount"]) == 12000000.0
    assert prop["product_type"] == "working_capital"
    assert prop["tenure_months"] == 36

    # Clean up test proposal and client so test runs never pollute production DB
    del_res = client.delete(f"/api/v1/proposals/{proposal_id}", headers=headers)
    assert del_res.status_code == 200
    client.delete(f"/api/v1/clients/{data['client_id']}", headers=headers)

