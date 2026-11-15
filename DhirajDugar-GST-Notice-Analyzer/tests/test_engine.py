from io import BytesIO
from pathlib import Path
from zipfile import ZipFile
import pytest
from engine import extract_document, metadata, detect_rules, ai_predictions, review_warnings, create_draft, docx_bytes, MAX_BYTES

ROOT = Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('file,form,topics', [
 ('01_ASMT10_Scrutiny.pdf', 'ASMT-10', {'itc_mismatch', 'liability_gap'}),
 ('02_DRC01_ShowCause.pdf', 'DRC-01', {'rcm', 'blocked_itc'}),
 ('03_DRC01A_PreNotice.pdf', 'DRC-01A', {'rcm', 'late_filing'}),
])
def test_demo_end_to_end(file, form, topics):
    extracted = extract_document((ROOT/'samples'/file).read_bytes(), file)
    meta = metadata(extracted.text)
    detected = detect_rules(extracted.text)
    assert meta['form'] == form
    assert set(detected) == topics
    assert meta['gstin'].startswith('24DEMO')
    assert meta['deadline']
    assert not extracted.warnings
    draft = create_draft(meta, list(detected))
    assert 'NOT FOR FILING' in draft
    assert '[TO BE VERIFIED]' not in draft  # sample metadata is complete
    assert 'Draft response: [Insert verified explanation' in draft
    with ZipFile(BytesIO(docx_bytes(draft))) as zipped:
        assert 'word/document.xml' in zipped.namelist()
        assert b'NOT FOR FILING' in zipped.read('word/document.xml')

@pytest.mark.parametrize('text,topic', [
 ('ITC mismatch between GSTR-2B and GSTR-3B needs explanation.', 'itc_mismatch'),
 ('Tax liability in GSTR-1 differs from GSTR-3B.', 'liability_gap'),
 ('Reverse charge short-payment has been identified.', 'rcm'),
 ('Blocked credit under section 17(5) is disputed.', 'blocked_itc'),
 ('Late filing of returns and late fee are noted.', 'late_filing'),
])
def test_rules(text, topic): assert topic in detect_rules(text)

@pytest.mark.parametrize('text', ['There is no ITC mismatch in this period.', 'RCM is not applicable.', 'No reverse charge is alleged.'])
def test_simple_negation(text): assert not detect_rules(text)

def test_no_deadline_invention():
    meta = metadata('GST ASMT-10\nIssue date: 01-11-2026\nRespond within thirty days of service.')
    assert meta['deadline'] == ''
    assert any('deadline' in w.lower() for w in review_warnings(meta, ''))

def test_pre_notice_not_confused_with_body_reference():
    assert metadata('GST DRC-01A\nThis precedes FORM GST DRC-01.')['form'] == 'DRC-01A'

def test_unknown_form_abstains():
    assert metadata('GST DRC-07\nAn order is enclosed.')['form'] == 'Unknown'

def test_missing_metadata_keeps_placeholders():
    assert '[TO BE VERIFIED]' in create_draft(metadata('Unknown letter'), [])

def test_multiple_gstins_not_guessed():
    meta = metadata('24DEMOX0000X1Z0 and 24DEMOY0000Y1Z0')
    assert meta['gstin'] == ''
    assert any('Multiple' in w for w in review_warnings(meta, ''))

def test_utf8_text():
    assert extract_document('GST notice ₹ 100'.encode(), 'notice.txt').text == 'GST notice ₹ 100'

@pytest.mark.parametrize('data,name', [(b'invalid PDF', 'bad.pdf'), (b'bad', 'script.exe'), (b'\xff\xfe', 'bad.txt'), (b'x'*(MAX_BYTES+1), 'large.pdf')])
def test_invalid_inputs(data, name):
    with pytest.raises(ValueError): extract_document(data, name)

def test_local_model_real_inference():
    rows = ai_predictions('The recipient is liable to pay GST on the notified service under reverse charge and has omitted this tax.')
    assert rows and rows[0]['key'] == 'rcm'
    assert 0 < rows[0]['score'] <= 1

def test_table_fragment_not_classified():
    assert not ai_predictions('Input credit 1296000 1440000 144000')

def test_user_facts_inserted_without_new_claims():
    text = create_draft(metadata('Unknown'), [], facts='[Verified case fact]')
    assert '[Verified case fact]' in text
    assert 'no liability is payable' not in text.lower()

def test_new_period_old_provision_warns():
    meta = metadata('GST DRC-01\nTax period: FY 2024-25\nSection 73 is invoked.')
    assert any('74A' in w for w in review_warnings(meta, 'Section 73'))


@pytest.mark.parametrize('text,expected', [('FORM GST ASMT - 10', 'ASMT-10'), ('FORM GST DRC - 01A', 'DRC-01A'), ('ASMT10', 'ASMT-10')])
def test_spaced_form_headings(text, expected):
    assert metadata(text)['form'] == expected
