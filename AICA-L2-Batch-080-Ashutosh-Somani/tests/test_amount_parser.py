import pytest
from decimal import Decimal
from app.utils.amount_utils import parse_amount

def test_parse_amount_standard():
    val, hint = parse_amount('1234.56')
    assert val == Decimal('1234.56')
    assert hint is None
    assert type(val) is Decimal

def test_parse_amount_commas():
    # International
    val, hint = parse_amount('1,234.56')
    assert val == Decimal('1234.56')
    
    # Indian
    val, hint = parse_amount('1,23,456.78')
    assert val == Decimal('123456.78')

def test_parse_amount_currency_symbols():
    val, hint = parse_amount('₹1,23,456.78')
    assert val == Decimal('123456.78')
    
    val, hint = parse_amount('INR 1,23,456.78')
    assert val == Decimal('123456.78')

def test_parse_amount_negatives():
    val, hint = parse_amount('-1,234.56')
    assert val == Decimal('-1234.56')
    
    # Parentheses
    val, hint = parse_amount('(1,234.56)')
    assert val == Decimal('-1234.56')

def test_parse_amount_cr_dr():
    val, hint = parse_amount('1,234.56 CR')
    assert val == Decimal('1234.56')
    assert hint == 'CR'
    
    val, hint = parse_amount('1,234.56DR')
    assert val == Decimal('1234.56')
    assert hint == 'DR'

def test_parse_amount_zero():
    val, hint = parse_amount('0.00')
    assert val == Decimal('0.00')

def test_parse_amount_invalid():
    assert parse_amount('hello') == (None, None)
    assert parse_amount('') == (None, None)
    assert parse_amount(None) == (None, None)
