"""CARO 2020 applicability and the paragraph 3 clause checklist."""

from __future__ import annotations

from auditlens.caro import CLAUSES, build_checklist, check_applicability


# --------------------------------------------------------------------------
# Applicability - paragraph 1(2)
# --------------------------------------------------------------------------

def test_one_person_company_is_exempt():
    r = check_applicability(company_class="private", is_one_person_company=True)
    assert not r.applies
    assert "One person company" in r.reasons[0]


def test_banking_and_insurance_companies_are_exempt():
    r = check_applicability(company_class="public", is_banking_or_insurance=True)
    assert not r.applies


def test_section_8_company_is_exempt():
    r = check_applicability(company_class="public", is_section_8=True)
    assert not r.applies


def test_small_private_company_within_all_three_limits_is_exempt():
    r = check_applicability(
        company_class="private",
        paid_up_capital=50_00_000,
        reserves_and_surplus=40_00_000,      # capital + reserves = 90 lakh, within 1 crore
        total_borrowings=80_00_000,          # within 1 crore
        total_revenue=8_00_00_000,           # within 10 crore
        turnover=8_00_00_000,
    )
    assert not r.applies
    assert "within all three limits" in r.reasons[-1]


def test_breaching_any_one_limit_brings_the_order_back():
    r = check_applicability(
        company_class="private",
        paid_up_capital=50_00_000,
        reserves_and_surplus=40_00_000,
        total_borrowings=80_00_000,
        total_revenue=12_00_00_000,          # revenue exceeds 10 crore
        turnover=12_00_00_000,
    )
    assert r.applies


def test_public_company_is_covered_regardless_of_size():
    r = check_applicability(
        company_class="public",
        paid_up_capital=10_00_000,
        reserves_and_surplus=5_00_000,
        total_borrowings=0,
        total_revenue=50_00_000,
    )
    assert r.applies


def test_subsidiary_of_a_public_company_loses_the_private_exemption():
    r = check_applicability(
        company_class="private",
        paid_up_capital=50_00_000,
        reserves_and_surplus=40_00_000,
        total_borrowings=80_00_000,
        total_revenue=8_00_00_000,
        is_holding_or_subsidiary_of_public=True,
    )
    assert r.applies


# --------------------------------------------------------------------------
# The clause checklist
# --------------------------------------------------------------------------

def test_all_twenty_one_clauses_are_present():
    checklist = build_checklist(check_applicability(company_class="public"))
    assert len(CLAUSES) == 21
    assert len(checklist.clauses) == 21
    numbers = [c.number for c in checklist.clauses]
    assert numbers[0] == "(i)"
    assert numbers[-1] == "(xxi)"
    assert len(set(numbers)) == 21


def test_every_clause_carries_its_requirement():
    checklist = build_checklist(check_applicability(company_class="public"))
    for clause in checklist.clauses:
        assert clause.title
        assert len(clause.requirement) > 40


def test_nothing_is_prefilled_without_facts():
    checklist = build_checklist(check_applicability(company_class="public"))
    assert checklist.prefilled_count == 0
    assert all(c.suggested_status == "Auditor input required" for c in checklist.clauses)


def test_facts_prefill_the_clauses_they_evidence():
    checklist = build_checklist(
        check_applicability(company_class="public"),
        facts={
            "has_ppe": True, "ppe_value": 5_00_00_000,
            "has_inventory": True, "inventory_value": 2_00_00_000,
            "working_capital_limit": 6_00_00_000,
            "has_borrowings": True, "borrowings_value": 3_00_00_000,
            "current_ratio": 0.85,
            "cash_loss_current": -20_00_000, "cash_loss_prior": 15_00_000,
        },
    )
    by_number = {c.number: c for c in checklist.clauses}

    # Amounts are grouped in the Indian lakh/crore convention.
    assert by_number["(i)"].data_available
    assert "5,00,00,000.00" in by_number["(i)"].evidence

    # Working capital limits above Rs 5 crore trigger the quarterly returns point.
    assert "quarterly returns" in by_number["(ii)"].suggested_status

    # A current ratio below 1 must raise the clause (xix) question.
    assert "material uncertainty" in by_number["(xix)"].suggested_status

    # A cash loss must be reported under clause (xvii).
    assert "Report the cash loss" in by_number["(xvii)"].suggested_status
    assert "loss" in by_number["(xvii)"].evidence


def test_a_cash_profit_is_not_reported_as_a_loss():
    checklist = build_checklist(
        check_applicability(company_class="public"),
        facts={"cash_loss_current": 45_00_000, "cash_loss_prior": 30_00_000},
    )
    clause = next(c for c in checklist.clauses if c.number == "(xvii)")
    assert "no cash loss" in clause.suggested_status


def test_a_healthy_current_ratio_does_not_raise_clause_xix():
    checklist = build_checklist(
        check_applicability(company_class="public"), facts={"current_ratio": 1.8}
    )
    clause = next(c for c in checklist.clauses if c.number == "(xix)")
    assert "material uncertainty" not in clause.suggested_status


def test_no_clause_is_ever_concluded_for_the_auditor():
    """Every clause must be returned blank for the auditor to complete."""
    checklist = build_checklist(
        check_applicability(company_class="public"),
        facts={"has_ppe": True, "ppe_value": 1_00_00_000, "current_ratio": 2.0},
    )
    assert all(c.auditor_response == "" for c in checklist.clauses)


def test_checklist_rows_are_export_ready(engagement):
    rows = engagement.caro.as_rows()
    assert len(rows) == 21
    assert set(rows[0]) == {
        "Clause", "Subject", "Requirement", "Data available",
        "Evidence from the books", "Status", "Auditor response",
    }


def test_sample_client_is_covered_and_partly_prefilled(engagement):
    assert engagement.caro.applicability.applies
    assert engagement.caro.prefilled_count >= 7
