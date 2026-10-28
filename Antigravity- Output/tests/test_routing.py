"""
Tests for Routing MTR Rows to GST Sections:
B2CL / B2CS / CDNUR / HSN Summary.
"""
from decimal import Decimal
import pytest
from core.sales_to_gst import route_mtr_to_gst_sections


def test_routing_b2cs_b2cl_cdnur_hsn():
    ship_from_code = "33"  # Tamil Nadu

    # Row 1: Normal small B2C interstate shipment -> B2CS
    r1 = {
        "order_id": "ORD-1",
        "invoice_no": "INV-1",
        "is_return": False,
        "ship_from_code": "33",
        "place_of_supply_code": "29",  # Karnataka
        "invoice_value": Decimal("450.00"),
        "taxable_value": Decimal("381.36"),
        "hsn": "33049990",
        "rate": Decimal("0.18")
    }

    # Row 2: B2C Large shipment (> 1,00,000, interstate) -> B2CL
    r2 = {
        "order_id": "ORD-2",
        "invoice_no": "INV-2",
        "is_return": False,
        "ship_from_code": "33",
        "place_of_supply_code": "27",  # Maharashtra
        "invoice_value": Decimal("105000.00"),
        "taxable_value": Decimal("88983.05"),
        "hsn": "33049990",
        "rate": Decimal("0.18")
    }

    # Row 3: Refund against B2CL invoice -> CDNUR
    r3 = {
        "order_id": "ORD-2",
        "invoice_no": "INV-2",
        "credit_note_no": "CN-001",
        "is_return": True,
        "ship_from_code": "33",
        "place_of_supply_code": "27",
        "invoice_value": Decimal("-15000.00"),
        "taxable_value": Decimal("-12711.86"),
        "hsn": "33049990",
        "rate": Decimal("0.18")
    }

    # Row 4: Normal B2C refund for small order -> B2CS
    r4 = {
        "order_id": "ORD-1",
        "invoice_no": "INV-1",
        "credit_note_no": "CN-002",
        "is_return": True,
        "ship_from_code": "33",
        "place_of_supply_code": "29",
        "invoice_value": Decimal("-450.00"),
        "taxable_value": Decimal("-381.36"),
        "hsn": "33049990",
        "rate": Decimal("0.18")
    }

    records = [r1, r2, r3, r4]
    routed = route_mtr_to_gst_sections(records, b2cl_threshold=Decimal("100000.00"))

    # Assertions
    assert len(routed["b2cl"]) == 1
    assert routed["b2cl"][0]["invoice_no"] == "INV-2"

    assert len(routed["cdnur"]) == 1
    assert routed["cdnur"][0]["credit_note_no"] == "CN-001"

    assert len(routed["b2cs"]) == 2
    b2cs_invs = [r["invoice_no"] for r in routed["b2cs"]]
    assert "INV-1" in b2cs_invs

    # All 4 rows route to HSN summary
    assert len(routed["hsn"]) == 4
