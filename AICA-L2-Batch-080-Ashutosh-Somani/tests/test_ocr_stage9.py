"""Stage 9: Comprehensive OCR pipeline tests.

Tests cover the full OCR lifecycle including:
- Cooperative cancellation via threading.Event
- Max page limit enforcement
- Partial and complete success/failure
- RawWord ocr_confidence alias round-trips
- Digital page bypass (no engine call)
- Mixed PDF selective page OCR
- Thread safety of ocr_job_locks
- Route endpoint error handling
- ocr_result.json and effective_extraction.json output verification
"""
import pytest
import json
import threading
import dataclasses
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.models.extraction_result import (
    RawWord, RawPage, RawTableCandidate, ExtractionResult,
)
from app.services.ocr_service import OcrService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _add_ocr_section(config, overrides=None):
    """Ensure the config has an [ocr] section with sensible defaults."""
    defaults = {
        'enabled': 'true',
        'render_dpi': '250',
        'minimum_word_confidence': '70',
        'limited_text_word_threshold': '20',
        'max_pages': '250',
        'worker_count': '1',
        'keep_rendered_pages': 'false',
        'model_dir': 'models/ocr',
    }
    if overrides:
        defaults.update(overrides)
    config['ocr'] = defaults


def make_extraction_result(job_id, pages_spec):
    """Build an ExtractionResult from a compact page specification.

    Args:
        job_id: Job identifier.
        pages_spec: list of dicts, each with keys:
            page_number, word_count  (required)
            source_type             (optional, default 'DIGITAL')
    Returns:
        ExtractionResult
    """
    pages = []
    total_words = 0
    total_chars = 0
    for spec in pages_spec:
        wc = spec['word_count']
        src = spec.get('source_type', 'DIGITAL')
        raw_text = ' '.join(['word'] * wc)
        words = [
            RawWord(
                text='word', x0=10.0, x1=50.0,
                top=10.0, bottom=20.0,
                page_number=spec['page_number'],
                source_type=src,
            )
            for _ in range(wc)
        ]
        pages.append(RawPage(
            page_number=spec['page_number'],
            width=612.0,
            height=792.0,
            raw_text=raw_text,
            word_count=wc,
            character_count=len(raw_text),
            source_type=src,
            words=words,
            table_candidates=[],
            warnings=[],
        ))
        total_words += wc
        total_chars += len(raw_text)

    return ExtractionResult(
        job_id=job_id,
        extractor_used='pdfplumber',
        extractor_version='0.10.0',
        status='success',
        page_count=len(pages),
        pages_processed=len(pages),
        total_words=total_words,
        total_characters=total_chars,
        text_layer_status='has_text',
        table_candidate_count=0,
        pages=pages,
    )


def _fake_ocr_page_success(*args, **kwargs):
    """Deterministic fake OCR engine result for one page."""
    words = [
        {
            'text': f'ocr_word_{i}',
            'x0': 10.0 + i * 40,
            'x1': 45.0 + i * 40,
            'top': 100.0,
            'bottom': 112.0,
            'confidence': 92.5,
            'source_type': 'OCR',
        }
        for i in range(5)
    ]
    raw_text = ' '.join(w['text'] for w in words)
    return words, raw_text


def _create_temp_pdf(tmp_path, job_id):
    """Create a minimal valid PDF under the jobs directory and return its Path."""
    import pypdf
    job_dir = tmp_path / 'temp' / 'jobs' / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = job_dir / 'source.pdf'
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=612, height=792)
    with open(pdf_path, 'wb') as f:
        writer.write(f)
    return pdf_path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestOcrCancellation:
    """1. Cooperative cancellation via threading.Event."""

    def test_cancellation_cooperative(self, temp_config, tmp_path):
        _add_ocr_section(temp_config)
        job_id = 'cancel-job-1'
        pdf_path = _create_temp_pdf(tmp_path, job_id)
        extraction = make_extraction_result(job_id, [
            {'page_number': 1, 'word_count': 5},
            {'page_number': 2, 'word_count': 5},
            {'page_number': 3, 'word_count': 5},
        ])

        cancel_event = threading.Event()
        call_count = 0

        def _ocr_then_cancel(*args, **kwargs):
            page_number = args[1] if len(args) > 1 else kwargs.get("page_number")
            nonlocal call_count
            call_count += 1
            # After completing page 1, signal cancellation
            if page_number == 1:
                cancel_event.set()
            return _fake_ocr_page_success(*args, **kwargs)

        with patch('app.services.pdf_intake_service.get_job_pdf_path', return_value=pdf_path), patch('app.services.ocr_service.get_job', return_value=None):
            svc = OcrService(temp_config)
            svc.engine_svc.ocr_page = _ocr_then_cancel
            result = svc.run_ocr(job_id, extraction, cancel_event=cancel_event)

        assert result == 'OCR_CANCELLED'
        # Only page 1 should have been OCR'd before cancellation was detected
        assert call_count == 1


class TestPageLimits:
    """2. Max page limit enforcement."""

    def test_max_page_limit_exceeded(self, temp_config, tmp_path):
        _add_ocr_section(temp_config, {'max_pages': '2'})
        job_id = 'limit-job-1'
        pdf_path = _create_temp_pdf(tmp_path, job_id)
        extraction = make_extraction_result(job_id, [
            {'page_number': 1, 'word_count': 5},
            {'page_number': 2, 'word_count': 5},
            {'page_number': 3, 'word_count': 5},
        ])

        with patch('app.services.pdf_intake_service.get_job_pdf_path', return_value=pdf_path), patch('app.services.ocr_service.get_job', return_value=None):
            svc = OcrService(temp_config)
            result = svc.run_ocr(job_id, extraction)

        assert result == 'OCR_PAGE_LIMIT_EXCEEDED'


class TestPartialFailure:
    """3. OCR engine failure on some pages yields OCR_PARTIAL."""

    def test_partial_failure(self, temp_config, tmp_path):
        _add_ocr_section(temp_config)
        job_id = 'partial-job-1'
        pdf_path = _create_temp_pdf(tmp_path, job_id)
        extraction = make_extraction_result(job_id, [
            {'page_number': 1, 'word_count': 5},
            {'page_number': 2, 'word_count': 5},
        ])

        def _mixed_ocr(pdf_path, page_number, w, h):
            if page_number == 2:
                raise Exception('Simulated OCR engine crash')
            return _fake_ocr_page_success(*args, **kwargs)

        with patch('app.services.pdf_intake_service.get_job_pdf_path', return_value=pdf_path), patch('app.services.ocr_service.get_job', return_value=None):
            svc = OcrService(temp_config)
            svc.engine_svc.ocr_page = _mixed_ocr
            result = svc.run_ocr(job_id, extraction)

        assert result == 'OCR_PARTIAL'


class TestCompleteSuccess:
    """4. All pages OCR successfully → OCR_COMPLETE."""

    def test_ocr_complete_success(self, temp_config, tmp_path):
        _add_ocr_section(temp_config)
        job_id = 'complete-job-1'
        pdf_path = _create_temp_pdf(tmp_path, job_id)
        extraction = make_extraction_result(job_id, [
            {'page_number': 1, 'word_count': 5},
            {'page_number': 2, 'word_count': 5},
        ])

        with patch('app.services.pdf_intake_service.get_job_pdf_path', return_value=pdf_path), patch('app.services.ocr_service.get_job', return_value=None):
            svc = OcrService(temp_config)
            svc.engine_svc.ocr_page = _fake_ocr_page_success
            result = svc.run_ocr(job_id, extraction)

        assert result == 'OCR_COMPLETE'


class TestMissingPdf:
    """5. Missing source PDF → OCR_FAILED."""

    def test_missing_pdf_returns_failed(self, temp_config, tmp_path):
        _add_ocr_section(temp_config)
        job_id = 'missing-pdf-job'
        extraction = make_extraction_result(job_id, [
            {'page_number': 1, 'word_count': 5},
        ])

        # Return None so the path check fails
        with patch('app.services.pdf_intake_service.get_job_pdf_path', return_value=None):
            svc = OcrService(temp_config)
            result = svc.run_ocr(job_id, extraction)

        assert result == 'OCR_FAILED'


class TestNoPagesNeedOcr:
    """6. All pages already digital and above threshold → OCR_COMPLETE (skip)."""

    def test_no_pages_need_ocr(self, temp_config, tmp_path):
        _add_ocr_section(temp_config)
        job_id = 'no-ocr-job'
        pdf_path = _create_temp_pdf(tmp_path, job_id)
        extraction = make_extraction_result(job_id, [
            {'page_number': 1, 'word_count': 100},
            {'page_number': 2, 'word_count': 80},
        ])

        with patch('app.services.pdf_intake_service.get_job_pdf_path', return_value=pdf_path), patch('app.services.ocr_service.get_job', return_value=None):
            svc = OcrService(temp_config)
            result = svc.run_ocr(job_id, extraction)

        assert result == 'OCR_COMPLETE'


class TestOcrConfidenceAlias:
    """7. RawWord.ocr_confidence read/write alias for confidence."""

    def test_ocr_confidence_alias(self):
        word = RawWord(
            text='test', x0=0.0, x1=10.0,
            top=0.0, bottom=10.0,
            page_number=1,
            source_type='OCR',
            confidence=85.5,
        )
        assert word.ocr_confidence == 85.5

        word.ocr_confidence = 90.0
        assert word.confidence == 90.0


class TestConfidenceRoundTrip:
    """8. Serialize / deserialize RawWord and verify ocr_confidence survives."""

    def test_ocr_confidence_round_trip(self):
        word = RawWord(
            text='hello', x0=1.0, x1=20.0,
            top=5.0, bottom=15.0,
            page_number=1,
            source_type='OCR',
            confidence=77.3,
        )
        d = dataclasses.asdict(word)
        assert 'confidence' in d
        assert d['confidence'] == 77.3

        # Reconstruct
        rebuilt = RawWord(**d)
        assert rebuilt.ocr_confidence == 77.3
        assert rebuilt.confidence == 77.3


class TestDigitalBypass:
    """9. Fully digital PDF should never invoke the OCR engine."""

    def test_digital_bypass_no_engine_call(self, temp_config, tmp_path):
        _add_ocr_section(temp_config)
        job_id = 'digital-bypass-job'
        pdf_path = _create_temp_pdf(tmp_path, job_id)
        extraction = make_extraction_result(job_id, [
            {'page_number': 1, 'word_count': 100, 'source_type': 'DIGITAL'},
            {'page_number': 2, 'word_count': 80, 'source_type': 'DIGITAL'},
        ])

        engine_spy = MagicMock(side_effect=AssertionError('Engine should not be called'))

        with patch('app.services.pdf_intake_service.get_job_pdf_path', return_value=pdf_path), patch('app.services.ocr_service.get_job', return_value=None):
            svc = OcrService(temp_config)
            svc.engine_svc.ocr_page = engine_spy
            result = svc.run_ocr(job_id, extraction)

        assert result == 'OCR_COMPLETE'
        engine_spy.assert_not_called()


class TestMixedPdfSelectiveOcr:
    """10. Only scanned pages (below threshold) trigger OCR engine calls."""

    def test_mixed_pdf_ocr_only_needed_pages(self, temp_config, tmp_path):
        _add_ocr_section(temp_config)
        job_id = 'mixed-job-1'
        pdf_path = _create_temp_pdf(tmp_path, job_id)
        extraction = make_extraction_result(job_id, [
            {'page_number': 1, 'word_count': 100},  # digital, above threshold
            {'page_number': 2, 'word_count': 5},     # scanned, below threshold
            {'page_number': 3, 'word_count': 80},    # digital, above threshold
        ])

        ocr_called_pages = []

        def _tracking_ocr(*args, **kwargs):
            page_number = args[1] if len(args) > 1 else kwargs.get("page_number")
            ocr_called_pages.append(page_number)
            return _fake_ocr_page_success(*args, **kwargs)

        with patch('app.services.pdf_intake_service.get_job_pdf_path', return_value=pdf_path), patch('app.services.ocr_service.get_job', return_value=None):
            svc = OcrService(temp_config)
            svc.engine_svc.ocr_page = _tracking_ocr
            result = svc.run_ocr(job_id, extraction)

        assert result == 'OCR_COMPLETE'
        assert ocr_called_pages == [2], f'Expected OCR only on page 2, got {ocr_called_pages}'


class TestThreadSafety:
    """11. ocr_job_locks is a defaultdict producing threading.Lock."""

    def test_thread_safety_lock_exists(self):
        from collections import defaultdict
        from app.routes.ocr_routes import ocr_job_locks

        assert isinstance(ocr_job_locks, defaultdict)

        lock = ocr_job_locks['test-lock-key']
        assert isinstance(lock, type(threading.Lock()))


class TestCancelEndpoint:
    """12. POST /ocr/<job_id>/cancel when not running → 400."""

    def test_cancel_endpoint_not_running(self, client):
        resp = client.post('/ocr/fake-id/cancel')
        assert resp.status_code == 400
        data = resp.get_json()
        assert 'not currently running' in data.get('message', '').lower() or \
               data.get('message') == 'OCR not currently running'


class TestRetryEndpoint:
    """13. POST /ocr/<job_id>/retry-failed with no prior result → 404."""

    def test_retry_no_previous_result(self, client):
        resp = client.post('/ocr/fake-id/retry-failed')
        assert resp.status_code == 404
        data = resp.get_json()
        assert 'no previous ocr result' in data.get('message', '').lower() or \
               'No previous OCR result found' in data.get('message', '')


class TestOcrResultJson:
    """14. ocr_result.json is written with expected structure."""

    def test_ocr_result_json_written(self, temp_config, tmp_path):
        _add_ocr_section(temp_config)
        job_id = 'result-json-job'
        pdf_path = _create_temp_pdf(tmp_path, job_id)
        extraction = make_extraction_result(job_id, [
            {'page_number': 1, 'word_count': 5},
            {'page_number': 2, 'word_count': 5},
        ])

        with patch('app.services.pdf_intake_service.get_job_pdf_path', return_value=pdf_path), patch('app.services.ocr_service.get_job', return_value=None):
            svc = OcrService(temp_config)
            svc.engine_svc.ocr_page = _fake_ocr_page_success
            result = svc.run_ocr(job_id, extraction)

        assert result == 'OCR_COMPLETE'

        ocr_result_path = tmp_path / 'temp' / 'jobs' / job_id / 'ocr' / 'ocr_result.json'
        assert ocr_result_path.exists(), f'ocr_result.json not found at {ocr_result_path}'

        with open(ocr_result_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        assert data['job_id'] == job_id
        assert 'ocr_engine' in data
        assert data['pages_requested'] == 2
        assert data['pages_completed'] == 2
        assert 'pages' in data
        assert len(data['pages']) == 2


class TestEffectiveExtraction:
    """15. effective_extraction.json is written and OCR pages have source_type 'OCR'."""

    def test_effective_extraction_written(self, temp_config, tmp_path):
        _add_ocr_section(temp_config)
        job_id = 'eff-ext-job'
        pdf_path = _create_temp_pdf(tmp_path, job_id)
        # Page 1 digital (above threshold), page 2 scanned (below threshold)
        extraction = make_extraction_result(job_id, [
            {'page_number': 1, 'word_count': 100},
            {'page_number': 2, 'word_count': 5},
        ])

        with patch('app.services.pdf_intake_service.get_job_pdf_path', return_value=pdf_path), patch('app.services.ocr_service.get_job', return_value=None):
            svc = OcrService(temp_config)
            svc.engine_svc.ocr_page = _fake_ocr_page_success
            result = svc.run_ocr(job_id, extraction)

        assert result == 'OCR_COMPLETE'

        eff_path = tmp_path / 'temp' / 'jobs' / job_id / 'ocr' / 'effective_extraction.json'
        assert eff_path.exists(), f'effective_extraction.json not found at {eff_path}'

        with open(eff_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        pages_by_num = {p['page_number']: p for p in data['pages']}
        # Page 1 should remain DIGITAL (not OCR'd)
        assert pages_by_num[1]['source_type'] == 'DIGITAL'
        # Page 2 should now be OCR
        assert pages_by_num[2]['source_type'] == 'OCR'

class TestLowConfidence:
    """16. Verify low confidence words are preserved and flagged."""

    def test_low_confidence_preservation_and_flagging(self, temp_config, tmp_path):
        _add_ocr_section(temp_config, {'minimum_word_confidence': '70'})
        job_id = 'low-conf-job'
        pdf_path = _create_temp_pdf(tmp_path, job_id)
        extraction = make_extraction_result(job_id, [
            {'page_number': 1, 'word_count': 5},
        ])

        def _fake_ocr_with_low_conf(*args, **kwargs):
            words = [
                {'text': 'good_word', 'x0': 10.0, 'x1': 50.0, 'top': 10.0, 'bottom': 20.0, 'confidence': 70.0, 'source_type': 'OCR'},
                {'text': 'bad_word', 'x0': 60.0, 'x1': 90.0, 'top': 10.0, 'bottom': 20.0, 'confidence': 69.99, 'source_type': 'OCR'},
            ]
            return words, "good_word bad_word"

        with patch('app.services.pdf_intake_service.get_job_pdf_path', return_value=pdf_path), patch('app.services.ocr_service.get_job', return_value=None):
            svc = OcrService(temp_config)
            svc.engine_svc.ocr_page = _fake_ocr_with_low_conf
            result = svc.run_ocr(job_id, extraction)

        assert result == 'OCR_COMPLETE'

        # Check effective extraction
        eff_path = tmp_path / 'temp' / 'jobs' / job_id / 'ocr' / 'effective_extraction.json'
        with open(eff_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        page = data['pages'][0]
        # Verify both words are preserved
        assert len(page['words']) == 2
        words_text = [w['text'] for w in page['words']]
        assert 'good_word' in words_text
        assert 'bad_word' in words_text

        # Verify page warning is present
        assert 'LOW_OCR_CONFIDENCE' in page['warnings']

