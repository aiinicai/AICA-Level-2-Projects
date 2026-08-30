import pytest
from app.extractors.pdfplumber_extractor import PdfPlumberExtractor
import configparser
import pypdf

@pytest.fixture
def test_config():
    return configparser.ConfigParser()

def test_pdfplumber_extractor_blank(sample_pdf, test_config):
    extractor = PdfPlumberExtractor()
    assert extractor.name == "pdfplumber"
    assert isinstance(extractor.version, str)
    
    assert extractor.can_handle(sample_pdf, {}) is True
    
    result = extractor.extract("job_id_123", sample_pdf, test_config)
    assert result.status == "success"
    assert result.page_count == 1
    assert result.pages_processed == 1
    assert result.total_words == 0
    assert result.text_layer_status == "none"
    assert len(result.warnings) > 0
    assert "No usable digital text was detected" in result.warnings[0]

@pytest.fixture
def digital_pdf_with_text(tmp_path):
    # We create a simple PDF using pypdf that has no text (pypdf can't easily write text),
    # actually let's just make a valid pdf, pdfplumber will return 0 words but succeed parsing.
    # To test actual digital text, we'd need a fixture with text.
    # We will test the basic structural parsing using sample_pdf.
    pdf_path = tmp_path / "text.pdf"
    from reportlab.pdfgen import canvas
    c = canvas.Canvas(str(pdf_path))
    c.drawString(100, 750, "Hello World")
    c.drawString(100, 730, "This is a digital text test.")
    # Add a mock table look
    c.drawString(100, 700, "Date       Narration         Debit     Credit    Balance")
    c.drawString(100, 680, "01/01/2026 Test transaction  100.00              1000.00")
    c.save()
    return str(pdf_path)

def test_pdfplumber_extractor_with_text(digital_pdf_with_text, test_config):
    # Need reportlab to create the fixture, if not available, we skip
    try:
        import reportlab
    except ImportError:
        pytest.skip("reportlab not installed, skipping text extraction test")
        
    extractor = PdfPlumberExtractor()
    result = extractor.extract("job_id_123", digital_pdf_with_text, test_config)
    assert result.status == "success"
    assert result.total_words > 0
    assert result.text_layer_status in ["usable", "limited"]
    assert len(result.pages) == 1
    
    page = result.pages[0]
    assert page.word_count > 0
    assert len(page.words) > 0
    
    # Check word geometry
    word = page.words[0]
    assert word.text != ""
    assert word.x0 >= 0
    assert word.page_number == 1
