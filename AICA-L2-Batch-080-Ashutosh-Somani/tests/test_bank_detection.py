import pytest
from app.services.bank_detector import BankDetector

@pytest.fixture
def detector(tmp_path):
    import json
    config_file = tmp_path / "bank_signatures.json"
    with open(config_file, "w") as f:
        json.dump({
            "banks": [
                {"id": "hdfc", "display_name": "HDFC Bank", "signatures": ["HDFC BANK LTD"]},
                {"id": "sbi", "display_name": "State Bank of India", "signatures": ["STATE BANK OF INDIA"]}
            ]
        }, f)
    return BankDetector(config_path=config_file)

def test_bank_detector_known(detector):
    status, name, sigs = detector.detect_bank("Some text here HDFC BANK LTD and some more")
    assert status == "detected"
    assert name == "HDFC Bank"
    assert "HDFC BANK LTD" in sigs

def test_bank_detector_unknown(detector):
    status, name, sigs = detector.detect_bank("Some text here random bank and some more")
    assert status == "unknown"
    assert name == "Unknown Bank"
    assert len(sigs) == 0

def test_bank_detector_ambiguous(detector):
    status, name, sigs = detector.detect_bank("HDFC BANK LTD and STATE BANK OF INDIA")
    assert status == "ambiguous"
    assert name == "Unknown Bank"
    assert len(sigs) == 2

def test_bank_detector_case_insensitive(detector):
    status, name, sigs = detector.detect_bank("hdfc bank ltd")
    assert status == "detected"
    assert name == "HDFC Bank"
