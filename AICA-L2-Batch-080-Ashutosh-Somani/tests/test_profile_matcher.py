import pytest
import configparser
from app.models.profile import BankProfile, TableRegion, ColumnDefinition
from app.services.profile_matcher import ProfileMatcher

def get_temp_config():
    c = configparser.ConfigParser()
    c.add_section('profiles')
    c.set('profiles', 'match_threshold', '85')
    c.set('profiles', 'auto_apply', 'false')
    return c

def test_profile_matching():
    p1 = BankProfile(
        profile_id="p1", profile_name="HDFC Current", bank_name="HDFC",
        page_width=595.0, page_height=842.0,
        expected_header_signatures=["Statement of Account", "Branch"]
    )
    p2 = BankProfile(
        profile_id="p2", profile_name="ICICI Savings", bank_name="ICICI",
        page_width=600.0, page_height=800.0,
        expected_header_signatures=["ICICI Bank"]
    )
    
    matcher = ProfileMatcher([p1, p2], get_temp_config())
    
    # Exact match for HDFC
    status, prof, score, details = matcher.match(
        bank_detected="HDFC Bank Ltd",
        page_width=595.0,
        page_height=842.0,
        extracted_text="Some text... Statement of Account ... Branch ... "
    )
    
    assert status == "AUTO_APPLIED"
    assert prof.profile_id == "p1"
    assert score == 100
    assert details['top']['bank_match'] is True
    assert details['top']['dimension_match'] is True
    
    # Low confidence match
    status, prof, score, details = matcher.match(
        bank_detected="HDFC Bank Ltd",
        page_width=100.0,
        page_height=100.0,
        extracted_text="No signatures here"
    )
    
    assert status == "SELECTION_REQUIRED"
    assert score < 85

def test_ambiguous_match():
    p1 = BankProfile(
        profile_id="p1", profile_name="HDFC Current", bank_name="HDFC",
        page_width=595.0, page_height=842.0,
        expected_header_signatures=["HDFC"]
    )
    p2 = BankProfile(
        profile_id="p2", profile_name="HDFC Savings", bank_name="HDFC",
        page_width=595.0, page_height=842.0,
        expected_header_signatures=["HDFC"]
    )

    matcher = ProfileMatcher([p1, p2], get_temp_config())

    status, prof, score, details = matcher.match(
        bank_detected="HDFC Bank",
        page_width=595.0,
        page_height=842.0,
        extracted_text="HDFC"
    )

    assert status == "SELECTION_REQUIRED"
    assert prof is None

