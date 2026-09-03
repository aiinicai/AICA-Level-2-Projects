from app.services.ocr_eligibility_service import OcrEligibilityService
from app.models.extraction_result import ExtractionResult, RawPage

class DummyConfig:
    def __init__(self, d):
        self.d = d
    def getboolean(self, section, key, fallback=False):
        return self.d.get(section, {}).get(key, fallback)
    def getint(self, section, key, fallback=0):
        return self.d.get(section, {}).get(key, fallback)

def test_ocr_eligibility_disabled():
    cfg = DummyConfig({'ocr': {'enabled': False}})
    svc = OcrEligibilityService(cfg)
    ext = ExtractionResult(job_id='1', extractor_used='x', extractor_version='1', status='s', page_count=1, pages_processed=1, total_words=5, total_characters=10, text_layer_status='x', table_candidate_count=0, pages=[
        RawPage(page_number=1, width=10, height=10, raw_text='', word_count=5, character_count=10)
    ])
    res = svc.assess_job(ext)
    assert res['overall_status'] == 'OCR_DISABLED'

def test_ocr_eligibility_required():
    cfg = DummyConfig({'ocr': {'enabled': True, 'limited_text_word_threshold': 20}})
    svc = OcrEligibilityService(cfg)
    ext = ExtractionResult(job_id='1', extractor_used='x', extractor_version='1', status='s', page_count=1, pages_processed=1, total_words=5, total_characters=10, text_layer_status='x', table_candidate_count=0, pages=[
        RawPage(page_number=1, width=10, height=10, raw_text='', word_count=5, character_count=10)
    ])
    res = svc.assess_job(ext)
    assert res['overall_status'] == 'OCR_REQUIRED'
    assert res['requires_ocr_count'] == 1

def test_ocr_eligibility_mixed():
    cfg = DummyConfig({'ocr': {'enabled': True, 'limited_text_word_threshold': 20}})
    svc = OcrEligibilityService(cfg)
    ext = ExtractionResult(job_id='1', extractor_used='x', extractor_version='1', status='s', page_count=2, pages_processed=2, total_words=105, total_characters=10, text_layer_status='x', table_candidate_count=0, pages=[
        RawPage(page_number=1, width=10, height=10, raw_text='', word_count=100, character_count=10),
        RawPage(page_number=2, width=10, height=10, raw_text='', word_count=5, character_count=10)
    ])
    res = svc.assess_job(ext)
    assert res['overall_status'] == 'MIXED_PDF_OCR_REQUIRED'
    assert res['requires_ocr_count'] == 1
