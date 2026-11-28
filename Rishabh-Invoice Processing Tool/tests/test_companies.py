import pytest

from ipt.core.gstin import check_char
from ipt.core.permissions import PermissionDenied
from ipt.services.auth_service import AuthService
from ipt.services.company_service import CompanyInput, ValidationError


def gst(prefix14):
    return prefix14 + check_char(prefix14)


def test_create_company_and_fys(companies, admin, tmp_path):
    c = companies.create_company(CompanyInput(name="ABC Enterprises", state_code="08",
                                              gstin=gst("08ABCDE1234F1Z")), admin)
    fy1 = companies.create_fy(c.id, 2025, admin)
    fy2 = companies.create_fy(c.id, 2026, admin)
    assert fy1.label == "2025-26" and fy2.label == "2026-27"
    assert [f.label for f in companies.list_fys(c.id)] == ["2026-27", "2025-26"]
    base = tmp_path / "data" / "Companies" / c.folder_name / "FY_2025_26"
    for sub in ("Invoices", "GSTR2B", "Purchase_Register", "XML", "Reports"):
        assert (base / sub).is_dir()


def test_duplicate_fy_rejected(companies, admin):
    c = companies.create_company(CompanyInput(name="A", state_code="08"), admin)
    companies.create_fy(c.id, 2025, admin)
    with pytest.raises(ValidationError):
        companies.create_fy(c.id, 2025, admin)


def test_same_fy_label_allowed_for_different_companies(companies, admin):
    a = companies.create_company(CompanyInput(name="A", state_code="08"), admin)
    b = companies.create_company(CompanyInput(name="B", state_code="27"), admin)
    companies.create_fy(a.id, 2025, admin)
    companies.create_fy(b.id, 2025, admin)
    assert len(companies.list_fys(a.id)) == 1 and len(companies.list_fys(b.id)) == 1


def test_gstin_state_mismatch(companies, admin):
    with pytest.raises(ValidationError) as e:
        companies.create_company(CompanyInput(name="A", state_code="27", gstin=gst("08ABCDE1234F1Z")), admin)
    assert "gstin" in e.value.errors


def test_invalid_and_duplicate_gstin(companies, admin):
    with pytest.raises(ValidationError):
        companies.create_company(CompanyInput(name="A", state_code="08", gstin="08ABCDE1234F1ZX"), admin)
    g = gst("08ABCDE1234F1Z")
    companies.create_company(CompanyInput(name="A", state_code="08", gstin=g), admin)
    with pytest.raises(ValidationError):
        companies.create_company(CompanyInput(name="B", state_code="08", gstin=g), admin)


def test_books_begin_outside_fy(companies, admin):
    from datetime import date
    c = companies.create_company(CompanyInput(name="A", state_code="08"), admin)
    with pytest.raises(ValidationError):
        companies.create_fy(c.id, 2025, admin, books_begin=date(2027, 1, 1))


def test_accountant_cannot_manage_companies(db, companies, admin):
    acc = AuthService(db).create_user("acc", "password123", "accountant", actor=admin)
    with pytest.raises(PermissionDenied):
        companies.create_company(CompanyInput(name="A", state_code="08"), acc)


def test_update_keeps_folder(companies, admin):
    c = companies.create_company(CompanyInput(name="Old Name", state_code="08"), admin)
    u = companies.update_company(c.id, CompanyInput(name="New Name", state_code="08"), admin)
    assert u.name == "New Name" and u.folder_name == c.folder_name
