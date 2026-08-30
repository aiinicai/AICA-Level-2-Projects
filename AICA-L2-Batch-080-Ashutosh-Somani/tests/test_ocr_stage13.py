import pytest
import os
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import pypdfium2 as pdfium
from PIL import Image

from app.models.profile import BankProfile, ColumnDefinition, TableRegion
from app.services.extraction_service import run_extraction, get_extraction_result
from app.services.ocr_service import OcrService
from app.services.normalization_service import run_normalization, get_normalization_result
from app.services.profile_manager import ProfileManager

def generate_synthetic_pdfs(job_id, tmp_path):
    digital_path = tmp_path / f"{job_id}_digital.pdf"
    
    # 1. Generate digital PDF
    c = canvas.Canvas(str(digital_path), pagesize=letter)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, 750, "Bank of Synthetic - Account Statement")
    c.setFont("Helvetica", 10)
    c.drawString(50, 730, "Account: 123456789")
    
    # Draw table header
    c.drawString(50, 700, "Date")
    c.drawString(150, 700, "Narration")
    c.drawString(350, 700, "Debit")
    c.drawString(450, 700, "Credit")
    c.drawString(550, 700, "Balance")
    
    y = 680
    balance = 10000.00
    
    for i in range(25):
        if y < 100:
            c.showPage()
            y = 750
        
        is_debit = i % 2 == 0
        amt = 100.50 + i
        if is_debit:
            balance -= amt
        else:
            balance += amt
            
        # Add some tricky OCR cases for dates and amounts
        date_str = "30/03/2026" if i % 2 == 0 else "31/03/2026"
        c.drawString(50, y, date_str)
        c.drawString(150, y, f"Transaction detail row {i}")
        
        if is_debit:
            c.drawString(350, y, f"{amt:.2f}")
            c.drawString(450, y, "")
        else:
            c.drawString(350, y, "")
            c.drawString(450, y, f"{amt:.2f}")
            
        c.drawString(550, y, f"{balance:.2f}")
        y -= 20
        
    c.save()
    
    # 2. Generate scanned PDF
    scanned_path = tmp_path / f"{job_id}_scanned.pdf"
    pdf = pdfium.PdfDocument(str(digital_path))
    images = []
    for i in range(len(pdf)):
        page = pdf[i]
        bitmap = page.render(scale=300/72.0)
        img = bitmap.to_pil().convert("RGB")
        images.append(img)
        page.close()
    pdf.close()
    
    images[0].save(str(scanned_path), save_all=True, append_images=images[1:], format="PDF", resolution=300.0)
    
    return str(digital_path), str(scanned_path)


def _reconstruct_extraction(raw_extraction_dict):
    from app.models.extraction_result import ExtractionResult, RawPage, RawWord
    pages = []
    for p in raw_extraction_dict.get('pages', []):
        words = [RawWord(**w) for w in p.get('words', [])]
        p_copy = p.copy()
        if 'words' in p_copy: del p_copy['words']
        if 'table_candidates' in p_copy: del p_copy['table_candidates']
        pages.append(RawPage(words=words, **p_copy))

    ext_copy = raw_extraction_dict.copy()
    if 'pages' in ext_copy: del ext_copy['pages']
    return ExtractionResult(pages=pages, **ext_copy)

def create_synthetic_profile(config):
    pm = ProfileManager(config)
    
    prof = BankProfile(
        profile_id="SYNTHETIC_1",
        bank_name="Bank of Synthetic",
        profile_name="Synthetic Profile",
        table_bbox=TableRegion(x0=40, top=80, x1=600, bottom=750),
        continuation_table_bbox=TableRegion(x0=40, top=40, x1=600, bottom=750),
        column_definitions=[
            ColumnDefinition("transaction_date", x0=45, x1=140),
            ColumnDefinition("narration", x0=145, x1=340),
            ColumnDefinition("debit", x0=345, x1=440),
            ColumnDefinition("credit", x0=445, x1=540),
            ColumnDefinition("balance", x0=545, x1=610),
        ],
        row_y_tolerance=10.0
    )
    pm.save_profile(prof)
    return prof

def test_digital_vs_ocr_parity(temp_config, tmp_path):
    # Setup paths and configs
    jobs_dir = tmp_path / "temp" / "jobs"
    jobs_dir.mkdir(parents=True, exist_ok=True)
    temp_config.set('paths', 'temp', str(tmp_path / 'temp'))
    temp_config.add_section('ocr')
    temp_config.set('ocr', 'render_dpi', '200')
    
    job_id_dig = "test_parity_dig"
    job_id_ocr = "test_parity_ocr"
    
    digital_pdf, scanned_pdf = generate_synthetic_pdfs("test_parity", tmp_path)
    
    # Copy to job dirs
    dig_dir = jobs_dir / job_id_dig
    dig_dir.mkdir(exist_ok=True)
    import shutil
    shutil.copy(digital_pdf, dig_dir / f"{job_id_dig}.pdf")
    
    ocr_dir = jobs_dir / job_id_ocr
    ocr_dir.mkdir(exist_ok=True)
    shutil.copy(scanned_pdf, ocr_dir / f"{job_id_ocr}.pdf")
    
    # Setup DB
    import sqlite3
    from app.database.migrations import init_db
    db_path = tmp_path / 'test.db'
    temp_config.set('paths', 'database', str(db_path))
    
    init_db(temp_config)
    
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.execute("INSERT INTO processing_jobs (id, display_name, status, stage, source_filename, stored_filename, file_size, sha256, page_count, pdf_type, encrypted) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (job_id_dig, "test_dig.pdf", "extracted", "normalization", "test_dig.pdf", job_id_dig + ".pdf", 1000, "abc", 2, "digital", 0))
    conn.execute("INSERT INTO processing_jobs (id, display_name, status, stage, source_filename, stored_filename, file_size, sha256, page_count, pdf_type, encrypted) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (job_id_ocr, "test_ocr.pdf", "extracted", "normalization", "test_ocr.pdf", job_id_ocr + ".pdf", 1000, "def", 2, "scanned", 0))
    conn.commit()
    conn.close()
    
    create_synthetic_profile(temp_config)
    
    # RUN DIGITAL
    from unittest.mock import patch
    with patch('app.services.extraction_service.get_job_pdf_path', return_value=dig_dir / f"{job_id_dig}.pdf"):
        success, err = run_extraction(job_id_dig, temp_config)
        assert success, err
    run_normalization(job_id_dig, temp_config, force_profile_id="SYNTHETIC_1")
    dig_res = get_normalization_result(job_id_dig, temp_config)
    
    # RUN OCR
    with patch('app.services.extraction_service.get_job_pdf_path', return_value=ocr_dir / f"{job_id_ocr}.pdf"):
        success, err = run_extraction(job_id_ocr, temp_config)
        assert success, err
    
    # Mock pre-selection so ROI is used
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.execute("UPDATE processing_jobs SET profile_id = ? WHERE id = ?", ("SYNTHETIC_1", job_id_ocr))
    conn.commit()
    conn.close() 
    
    ext_res_ocr = get_extraction_result(job_id_ocr, temp_config)
    ext_obj = _reconstruct_extraction(ext_res_ocr)
    
    svc = OcrService(temp_config)
    pages_to_ocr = [p.page_number for p in ext_obj.pages]
    with patch('app.services.pdf_intake_service.get_job_pdf_path', return_value=ocr_dir / f"{job_id_ocr}.pdf"):
        res = svc.run_ocr(job_id_ocr, ext_obj, force_pages=pages_to_ocr)
        assert res == 'OCR_COMPLETE'
    
    run_normalization(job_id_ocr, temp_config, force_profile_id="SYNTHETIC_1")
    ocr_res = get_normalization_result(job_id_ocr, temp_config)
    
    # Assertions
    assert dig_res is not None
    assert ocr_res is not None
    
    dig_txns = dig_res['transactions']
    ocr_txns = ocr_res['transactions']
    
    assert len(dig_txns) == 25, f"Digital should have 25 transactions, got {len(dig_txns)}"
    assert len(ocr_txns) == 25, f"OCR should also have exactly 25 transactions, got {len(ocr_txns)}"
    
    for i in range(25):
        dt = dig_txns[i]
        ot = ocr_txns[i]
        assert dt['transaction_date'] == ot['transaction_date']
        if dt.get('debit'):
            assert float(dt['debit']) == float(ot.get('debit', 0) or 0)
        if dt.get('credit'):
            assert float(dt['credit']) == float(ot.get('credit', 0) or 0)
        if dt.get('balance'):
            assert float(dt['balance']) == float(ot.get('balance', 0) or 0)
