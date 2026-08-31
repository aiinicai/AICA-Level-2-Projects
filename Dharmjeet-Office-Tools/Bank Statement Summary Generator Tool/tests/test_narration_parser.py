"""Unit tests for Indian banking narration parser."""

import pytest
from normalization.narration_parser import parse_narration

def test_upi_narration():
    raw = "UPI/412345678901/Rahul Sharma/rahul@okaxis/Payment for office supplies"
    res = parse_narration(raw)
    assert res["mode"] == "UPI"
    assert "Rahul Sharma" in res["counterparty_name"]
    assert res["counterparty_vpa"] == "rahul@okaxis"
    assert res["reference_no"] == "412345678901"

def test_neft_narration():
    raw = "NEFT-HDFC0001234-N123456789012-RAMESH ENTERPRISES-INVOICE PMT"
    res = parse_narration(raw)
    assert res["mode"] == "NEFT"
    assert "Ramesh Enterprises" in res["counterparty_name"]
    assert "HDFC0001234" in res["counterparty_vpa"]
    assert "N123456789012" in res["reference_no"]

def test_imps_narration():
    raw = "IMPS/P2A/412345678901/DEEPAK VERMA/HDFC0000123"
    res = parse_narration(raw)
    assert res["mode"] == "IMPS"
    assert "Deepak Verma" in res["counterparty_name"]

def test_cash_atm_narration():
    raw_atm = "ATM CASH WITHDRAWAL - S1NA000123 - CONNAUGHT PLACE"
    res_atm = parse_narration(raw_atm)
    assert res_atm["mode"] == "ATM"

    raw_cash = "BY CASH - SELF DEPOSIT AT CDM"
    res_cash = parse_narration(raw_cash)
    assert res_cash["mode"] == "CASH"

def test_pos_narration():
    raw = "POS 412345678901 RELIANCE RETAIL MUMBAI"
    res = parse_narration(raw)
    assert res["mode"] == "POS"
    assert "Reliance Retail" in res["counterparty_name"]
