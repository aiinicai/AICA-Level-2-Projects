"""
Unit tests for CertificateExtractor.
Tests metadata extraction from mock TRACES PDF files.
"""

from pathlib import Path
import pytest
from core.extractor import CertificateExtractor
from core.models import ProcessingStatus
from config import ACT_1961, ACT_2025


@pytest.fixture(scope="module")
def sample_dir():
    dir_path = Path("./sample_test_certificates")
    if not any(dir_path.glob("*.pdf")):
        from tests.generate_samples import generate_mock_certificates
        generate_mock_certificates(dir_path)
    return dir_path


@pytest.fixture
def extractor():
    return CertificateExtractor()


def test_extract_form_16a(extractor, sample_dir):
    f = sample_dir / "raw_download_001_f16a.pdf"
    cert = extractor.extract(f)

    assert cert.status == ProcessingStatus.EXTRACTED
    assert "TATA CONSULTANCY SERVICES" in cert.deductee_name
    assert cert.deductee_pan == "AAACT1234K"
    assert cert.deductor_tan == "CALB00123D"
    assert cert.form_code == "16A"
    assert cert.act == ACT_1961
    assert cert.quarter == "Q2"
    assert cert.financial_year == "2024-25"
    assert cert.assessment_year == "2025-26"
    assert cert.certificate_no == "TR16A9928172"


def test_extract_form_16_salary(extractor, sample_dir):
    f = sample_dir / "raw_download_002_f16.pdf"
    cert = extractor.extract(f)

    assert cert.status == ProcessingStatus.EXTRACTED
    assert "RAHUL ARVIND DESHMUKH" in cert.deductee_name
    assert cert.deductee_pan == "ABCDE1234F"
    assert cert.form_code == "16"
    assert cert.act == ACT_1961
    assert cert.quarter == "Q4"


def test_extract_form_27d_tcs(extractor, sample_dir):
    f = sample_dir / "raw_download_003_f27d.pdf"
    cert = extractor.extract(f)

    assert cert.status == ProcessingStatus.EXTRACTED
    assert "JINDAL STEEL AND POWER LIMITED" in cert.deductee_name
    assert cert.deductee_pan == "AAACJ5544K"
    assert cert.form_code == "27D"
    assert cert.act == ACT_1961
    assert cert.category == "TCS Certificate"


def test_extract_form_130_2025_act(extractor, sample_dir):
    f = sample_dir / "raw_download_006_f130.pdf"
    cert = extractor.extract(f)

    assert cert.status == ProcessingStatus.EXTRACTED
    assert "VIKRAM NARENDRA PATEL" in cert.deductee_name
    assert cert.deductee_pan == "BTRPP5432M"
    assert cert.form_code == "130"
    assert cert.act == ACT_2025


def test_extract_form_131_2025_act(extractor, sample_dir):
    f = sample_dir / "raw_download_007_f131.pdf"
    cert = extractor.extract(f)

    assert cert.status == ProcessingStatus.EXTRACTED
    assert "HCL TECHNOLOGIES LIMITED" in cert.deductee_name
    assert cert.form_code == "131"
    assert cert.act == ACT_2025
    assert cert.deductee_pan == "AAACH9988P"


def test_extract_real_traces_form_27d(extractor):
    real_f27d_dir = Path(r"C:\Users\Pankil\Desktop\TDS-TCS CERTIFICATE\FORM 27D")
    sample_file = real_f27d_dir / "AAEPI8985N_Q4_2026-27.pdf"
    if sample_file.exists():
        cert = extractor.extract(sample_file)
        assert cert.status == ProcessingStatus.EXTRACTED
        assert cert.deductee_name == "SURAJMAL TEJPAL INTODIA"
        assert cert.deductee_pan == "AAEPI8985N"
        assert cert.deductor_tan == "AHMG00263E"
        assert cert.form_code == "27D"
        assert cert.quarter == "Q4"
        assert cert.assessment_year == "2026-27"
        assert cert.financial_year == "2025-26"
        assert cert.certificate_no == "JLSVHUA"


def test_extract_specimen_form_16a(extractor):
    specimen = Path("Sample TDS Certificate (Form 16A).pdf")
    if specimen.exists():
        cert = extractor.extract(specimen)
        assert cert.status == ProcessingStatus.EXTRACTED
        assert cert.deductee_name == "RAJESH KUMAR SHARMA"
        assert cert.deductee_pan == "BKPSK4910M"
        assert cert.deductor_tan == "AHMV02847E"
        assert cert.form_code == "16A"
        assert cert.quarter == "Q1"
        assert cert.assessment_year == "2027-28"
        assert cert.financial_year == "2026-27"
        assert cert.certificate_no == "TRC-2026-99482103"


def test_extract_real_traces_form_131_2025(extractor):
    real_f131_dir = Path(r"C:\Users\Pankil\Desktop\TDS-TCS CERTIFICATE\FORM 131")
    sample_file = real_f131_dir / "131_AAACI5607C_Q1_2026-27.pdf"
    if sample_file.exists():
        cert = extractor.extract(sample_file)
        assert cert.status == ProcessingStatus.EXTRACTED
        assert cert.deductee_name == "INLAND WORLD LOGISTICS PRIVATE LIMITED"
        assert cert.deductee_pan == "AAACI5607C"
        assert cert.deductor_tan == "AHMG00263E"
        assert cert.form_code == "131"
        assert cert.form_type == "Form 131"
        assert cert.act == ACT_2025
        assert cert.quarter == "Q1"
        assert cert.assessment_year == "2026-27"
        assert cert.financial_year == "2026-27"
        assert cert.certificate_no == "AAI262719021825"


