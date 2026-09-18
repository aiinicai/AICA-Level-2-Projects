"""Tests for core.extraction_engine: schema validation, missing-field detection,
and Decimal-exact total verification."""
from __future__ import annotations

import json
from decimal import Decimal

import pytest

from core.ai_provider import AIProviderKind, AIResponse
from core.extraction_engine import ExtractionKind, extract_structured, verify_invoice_totals
from utils.validation import ValidationError


class StubProvider:
    def __init__(self, response_dict: dict):
        self.response_dict = response_dict

    def complete(self, request):
        return AIResponse(text=json.dumps(self.response_dict), provider=AIProviderKind.ANTHROPIC, model="stub-model")


def test_extract_invoice_parses_decimals_not_floats():
    stub = StubProvider(
        {
            "invoice_number": "INV-001",
            "invoice_date": "2026-01-10",
            "supplier_name": "ABC Traders",
            "supplier_gstin": "29ABCDE1234F1Z5",
            "customer_name": "Kishor Singh and Co.",
            "customer_gstin": None,
            "place_of_supply": "Karnataka",
            "taxable_value": "100000.00",
            "cgst": "9000.00",
            "sgst": "9000.00",
            "igst": None,
            "cess": None,
            "total_amount": "118000.00",
            "line_items": [],
        }
    )
    outcome = extract_structured("invoice text", ExtractionKind.INVOICE, stub)
    assert isinstance(outcome.model.total_amount, Decimal)
    assert outcome.model.total_amount == Decimal("118000.00")
    assert outcome.model.invoice_number == "INV-001"


def test_extract_invoice_reports_missing_fields():
    stub = StubProvider(
        {
            "invoice_number": "INV-002",
            "invoice_date": None,
            "supplier_name": None,
            "supplier_gstin": None,
            "customer_name": None,
            "customer_gstin": None,
            "place_of_supply": None,
            "taxable_value": None,
            "cgst": None,
            "sgst": None,
            "igst": None,
            "cess": None,
            "total_amount": None,
            "line_items": [],
        }
    )
    outcome = extract_structured("sparse text", ExtractionKind.INVOICE, stub)
    assert "supplier_name" in outcome.missing_fields
    assert "total_amount" in outcome.missing_fields
    assert "invoice_number" not in outcome.missing_fields


def test_extract_tolerates_markdown_fenced_json():
    class FencedStub:
        def complete(self, request):
            payload = {
                "invoice_number": "INV-003", "invoice_date": None, "supplier_name": None,
                "supplier_gstin": None, "customer_name": None, "customer_gstin": None,
                "place_of_supply": None, "taxable_value": None, "cgst": None, "sgst": None,
                "igst": None, "cess": None, "total_amount": None, "line_items": [],
            }
            return AIResponse(text=f"```json\n{json.dumps(payload)}\n```", provider=AIProviderKind.ANTHROPIC, model="stub")

    outcome = extract_structured("text", ExtractionKind.INVOICE, FencedStub())
    assert outcome.model.invoice_number == "INV-003"


def test_extract_raises_clear_error_on_schema_mismatch():
    class BadNumberStub:
        def complete(self, request):
            return AIResponse(
                text=json.dumps(
                    {
                        "invoice_number": "X", "invoice_date": None, "supplier_name": None,
                        "supplier_gstin": None, "customer_name": None, "customer_gstin": None,
                        "place_of_supply": None, "taxable_value": "not-a-decimal", "cgst": None,
                        "sgst": None, "igst": None, "cess": None, "total_amount": None, "line_items": [],
                    }
                ),
                provider=AIProviderKind.ANTHROPIC,
                model="stub",
            )

    with pytest.raises(ValidationError):
        extract_structured("text", ExtractionKind.INVOICE, BadNumberStub())


def test_extract_bank_statement_transactions():
    stub = StubProvider(
        {
            "account_number": "1234567890",
            "account_holder": "Kishor Singh and Co.",
            "bank_name": "Example Bank",
            "statement_period_from": "2026-01-01",
            "statement_period_to": "2026-01-31",
            "opening_balance": "50000.00",
            "closing_balance": "62000.00",
            "transactions": [
                {"date": "2026-01-05", "value_date": "2026-01-05", "narration": "Fee received", "reference_number": "TXN1",
                 "debit": None, "credit": "12000.00", "balance": "62000.00", "suggested_category": "Professional Fees"}
            ],
        }
    )
    outcome = extract_structured("bank text", ExtractionKind.BANK_STATEMENT, stub)
    assert len(outcome.model.transactions) == 1
    assert outcome.model.transactions[0].credit == Decimal("12000.00")


def test_extract_gst_notice():
    stub = StubProvider(
        {
            "notice_type": "DRC-01",
            "section_reference": "Section 74",
            "gstin": "29ABCDE1234F1Z5",
            "tax_period": "FY 2023-24",
            "demand_amount": "50000.00",
            "reply_due_date": "2026-02-01",
            "issuing_authority": "State GST Department",
            "summary": "Mismatch in ITC claimed vs GSTR-2A",
        }
    )
    outcome = extract_structured("notice text", ExtractionKind.GST_NOTICE, stub)
    assert outcome.model.notice_type == "DRC-01"
    assert outcome.model.demand_amount == Decimal("50000.00")
    assert outcome.missing_fields == []


# ------------------------------------------------------------- total verification

def test_verify_invoice_totals_flags_mismatch():
    from core.extraction_engine import InvoiceExtraction

    invoice = InvoiceExtraction(
        taxable_value=Decimal("100000"), cgst=Decimal("9000"), sgst=Decimal("9000"),
        igst=None, cess=None, total_amount=Decimal("120000"),  # should be 118000
    )
    warnings = verify_invoice_totals(invoice)
    assert len(warnings) == 1
    assert "does not match" in warnings[0]


def test_verify_invoice_totals_passes_when_exact():
    from core.extraction_engine import InvoiceExtraction

    invoice = InvoiceExtraction(
        taxable_value=Decimal("100000.00"), cgst=Decimal("9000.00"), sgst=Decimal("9000.00"),
        igst=None, cess=None, total_amount=Decimal("118000.00"),
    )
    warnings = verify_invoice_totals(invoice)
    assert warnings == []


def test_verify_invoice_totals_skips_when_fields_missing():
    from core.extraction_engine import InvoiceExtraction

    invoice = InvoiceExtraction(taxable_value=Decimal("100000"), total_amount=None)
    warnings = verify_invoice_totals(invoice)
    assert warnings == []  # nothing to verify -- not a false alarm


def test_verify_invoice_totals_handles_realistic_intra_state_invoice():
    """A typical intra-state invoice has IGST and cess as None (not zero) --
    verification must still run using CGST+SGST alone, not skip entirely."""
    from core.extraction_engine import InvoiceExtraction

    invoice = InvoiceExtraction(
        taxable_value=Decimal("100000.00"), cgst=Decimal("9000.00"), sgst=Decimal("9000.00"),
        igst=None, cess=None, total_amount=Decimal("118000.00"),  # deliberately wrong: should be 118000
    )
    warnings = verify_invoice_totals(invoice)
    assert warnings == []  # 100000 + 9000 + 9000 = 118000, correct

    invoice.total_amount = Decimal("120000.00")  # now deliberately wrong
    warnings = verify_invoice_totals(invoice)
    assert len(warnings) == 1
