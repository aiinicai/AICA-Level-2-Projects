import pytest
import datetime
from app.utils.date_utils import parse_date

def test_parse_date_dmy():
    # standard D M Y
    assert parse_date('01/04/2026', 'DMY') == (datetime.date(2026, 4, 1), 'success')
    assert parse_date('01-04-2026', 'DMY') == (datetime.date(2026, 4, 1), 'success')
    assert parse_date('01.04.2026', 'DMY') == (datetime.date(2026, 4, 1), 'success')
    
    # 2 digit year
    assert parse_date('01/04/26', 'DMY') == (datetime.date(2026, 4, 1), 'success')
    
def test_parse_date_mdy():
    assert parse_date('04/01/2026', 'MDY') == (datetime.date(2026, 4, 1), 'success')
    
def test_parse_date_alpha_month():
    assert parse_date('01 Apr 2026') == (datetime.date(2026, 4, 1), 'success')
    assert parse_date('01-APR-26') == (datetime.date(2026, 4, 1), 'success')
    assert parse_date('01-APR-2026') == (datetime.date(2026, 4, 1), 'success')
    
def test_parse_date_iso():
    assert parse_date('2026-04-01') == (datetime.date(2026, 4, 1), 'success')
    
def test_parse_date_leap_year():
    assert parse_date('29/02/2024', 'DMY') == (datetime.date(2024, 2, 29), 'success')
    date_val, status = parse_date('29/02/2025', 'DMY')
    assert status == 'invalid_date'
    
def test_parse_date_invalid():
    # 31 April
    date_val, status = parse_date('31/04/2026', 'DMY')
    assert status == 'invalid_date'
    
    # Garbage
    assert parse_date('hello')[1] == 'unparseable'
    assert parse_date('')[1] == 'empty'
    assert parse_date(None)[1] == 'empty'
