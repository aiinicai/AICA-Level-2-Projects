import pytest
from utils.validation import ValidationError, validate_category_code


def test_category_code_valid():
    assert validate_category_code("com") == "COM"


def test_category_code_blank():
    with pytest.raises(ValidationError):
        validate_category_code("")


def test_category_code_duplicate():
    with pytest.raises(ValidationError):
        validate_category_code("COM", existing_codes={"COM"})


def test_category_code_too_long():
    with pytest.raises(ValidationError):
        validate_category_code("TOOLONGCODE")