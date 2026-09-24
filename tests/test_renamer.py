"""
Unit tests for CertificateRenamer and UndoManager.
Tests filename templating, sanitization, collision avoidance, and rollback.
"""

import shutil
from pathlib import Path
import pytest

from core.models import CertificateData, ProcessingStatus
from core.renamer import CertificateRenamer
from core.undo_manager import UndoManager
from config import (
    COLLISION_AUTO_INCREMENT,
    COLLISION_DISAMBIGUATE,
    MODE_RENAME_IN_PLACE,
    MODE_COPY_TO_FOLDER,
)


@pytest.fixture
def sample_cert():
    return CertificateData(
        file_path=Path("sample.pdf"),
        original_filename="sample.pdf",
        act="Income-tax Act, 1961",
        form_type="Form 16A",
        form_code="16A",
        deductee_name="TATA CONSULTANCY SERVICES LIMITED",
        deductee_pan="AAACT1234K",
        deductor_tan="CALB00123D",
        financial_year="2024-25",
        assessment_year="2025-26",
        quarter="Q2",
        certificate_no="TR16A99281",
    )


def test_format_filename_default(sample_cert):
    renamer = CertificateRenamer(template="{DeducteeName}")
    name = renamer.format_filename(sample_cert)
    assert name == "TATA CONSULTANCY SERVICES LIMITED.pdf"


def test_format_filename_custom_tokens(sample_cert):
    renamer = CertificateRenamer(template="{DeducteeName}_{FormType}_{Quarter}_{FinancialYear}")
    name = renamer.format_filename(sample_cert)
    assert name == "TATA CONSULTANCY SERVICES LIMITED_Form 16A_Q2_2024-25.pdf"


def test_sanitize_filename():
    renamer = CertificateRenamer()
    dirty = 'M/s. John & Doe "Tech" / <Ltd> : Branch * ? |'
    cleaned = renamer.sanitize_filename(dirty)
    for bad_char in r'\/*?:"<>|':
        assert bad_char not in cleaned


def test_collision_auto_increment(tmp_path, sample_cert):
    # Setup two mock files with identical deductee
    f1 = tmp_path / "cert1.pdf"
    f2 = tmp_path / "cert2.pdf"
    f1.write_bytes(b"%PDF-mock")
    f2.write_bytes(b"%PDF-mock")

    c1 = CertificateData(file_path=f1, deductee_name="RELIANCE INDUSTRIES LIMITED")
    c2 = CertificateData(file_path=f2, deductee_name="RELIANCE INDUSTRIES LIMITED")

    renamer = CertificateRenamer(
        template="{DeducteeName}",
        collision_policy=COLLISION_AUTO_INCREMENT,
        execution_mode=MODE_RENAME_IN_PLACE,
    )
    batch = renamer.plan_batch([c1, c2])

    assert batch[0].proposed_filename == "RELIANCE INDUSTRIES LIMITED.pdf"
    assert batch[1].proposed_filename == "RELIANCE INDUSTRIES LIMITED (1).pdf"


def test_collision_disambiguate(tmp_path):
    f1 = tmp_path / "c1.pdf"
    f2 = tmp_path / "c2.pdf"
    f1.write_bytes(b"%PDF-mock")
    f2.write_bytes(b"%PDF-mock")

    c1 = CertificateData(file_path=f1, deductee_name="WIPRO LTD", quarter="Q1", deductee_pan="AAACW1234K")
    c2 = CertificateData(file_path=f2, deductee_name="WIPRO LTD", quarter="Q2", deductee_pan="AAACW1234K")

    renamer = CertificateRenamer(
        template="{DeducteeName}",
        collision_policy=COLLISION_DISAMBIGUATE,
        execution_mode=MODE_RENAME_IN_PLACE,
    )
    batch = renamer.plan_batch([c1, c2])

    assert batch[0].proposed_filename == "WIPRO LTD.pdf"
    # Second should have disambiguating metadata
    assert "Q2" in batch[1].proposed_filename or "AAACW1234K" in batch[1].proposed_filename


def test_rename_and_rollback(tmp_path):
    f1 = tmp_path / "original_doc.pdf"
    f1.write_bytes(b"%PDF-test-data")

    cert = CertificateData(
        file_path=f1,
        original_filename="original_doc.pdf",
        deductee_name="SUN PHARMACEUTICALS",
    )

    renamer = CertificateRenamer(template="{DeducteeName}", execution_mode=MODE_RENAME_IN_PLACE)
    renamer.plan_batch([cert])
    success, msg = renamer.execute_rename(cert)

    assert success
    assert not f1.exists()
    renamed_file = tmp_path / "SUN PHARMACEUTICALS.pdf"
    assert renamed_file.exists()

    # Record undo session
    undo_mgr = UndoManager(audit_dir=tmp_path)
    session_id = undo_mgr.record_session(str(tmp_path), [cert], mode=MODE_RENAME_IN_PLACE)
    assert session_id

    # Execute rollback
    succ_cnt, err_cnt, logs = undo_mgr.rollback_session(session_id)
    assert succ_cnt == 1
    assert err_cnt == 0
    assert f1.exists()
    assert not renamed_file.exists()
