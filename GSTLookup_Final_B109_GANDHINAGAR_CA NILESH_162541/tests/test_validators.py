import pytest
from core.validators import *
@pytest.mark.parametrize("state", sorted(STATES))
def test_every_state(state):
    s=state+"AAACT1234K1Z"
    assert validate_gstin(s+checksum(s)).kind == "GSTIN"
@pytest.mark.parametrize("value", ["AAACT1234K", "AABCU9603R", " aaact1234k "])
def test_pan(value): assert validate_pan(value).meaning == "Company"
@pytest.mark.parametrize("value", ["ABCDE1234F", "ABCDE12345", "ABCD1234FG", "ABCXE1234F", "", None, "A"*11])
def test_bad_pan(value):
    with pytest.raises(ValueError): validate_pan(value)
@pytest.mark.parametrize("prefix", ["00AAACT1234K1Z", "39AAACT1234K1Z", "45AAACT1234K1Z", "27AAACT1234K0Z", "27AAACT1234K1X", "27ABCXE1234F1Z"])
def test_bad_gstin(prefix):
    with pytest.raises(ValueError): validate_gstin(prefix+checksum(prefix))
@pytest.mark.parametrize("value", ["27AAACT1234K1Z", "27AAACT1234K1Z00", "27AAACT1234K1Z!", "27AAACT1234K1Z0"])
def test_invalid(value):
    with pytest.raises(ValueError): validate_gstin(value)
def test_lowercase():
    s="07AABCU9603R1Z"; assert validate(s.lower()+checksum(s)).value == s+checksum(s)
def test_batch(): assert batch(" aaact1234k,AAACT1234K;bad\n27AAACT1234K1ZV") == ["AAACT1234K","BAD","27AAACT1234K1ZV"]
