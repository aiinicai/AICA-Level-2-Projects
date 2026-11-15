"""Offline extraction, evidence-backed rules and a small supervised NLP model."""
from dataclasses import dataclass
from functools import lru_cache
from io import BytesIO
from pathlib import Path
import csv
import re
import pdfplumber
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from knowledge import ISSUES, PROCEDURE

BASE = Path(__file__).resolve().parent
MAX_BYTES = 10 * 1024 * 1024
MAX_CHARS = 100_000

@dataclass
class Extracted:
    text: str
    warnings: list
    pages: int

def extract_document(data: bytes, filename: str) -> Extracted:
    if len(data) > MAX_BYTES:
        raise ValueError('The file exceeds 10 MB. Split it into smaller documents.')
    warnings, texts = [], []
    if filename.lower().endswith('.txt'):
        try: text = data.decode('utf-8-sig')
        except UnicodeDecodeError:
            raise ValueError('Save the text file as UTF-8, then upload it again.')
        if len(text) > MAX_CHARS: raise ValueError('Text exceeds 100,000 characters. Split the document.')
        return Extracted(text, [], 1)
    if not filename.lower().endswith('.pdf'):
        raise ValueError('Please upload a PDF or UTF-8 text file.')
    try:
        with pdfplumber.open(BytesIO(data)) as pdf:
            if len(pdf.pages) > 30:
                raise ValueError('More than 30 pages. Split the notice and its annexures.')
            for n, page in enumerate(pdf.pages, 1):
                text = page.extract_text(x_tolerance=2, y_tolerance=3) or ''
                if len(text.strip()) < 25:
                    warnings.append(f'Page {n} has little or no readable text. OCR or manual transcription is required; it may contain missing issues.')
                texts.append(f'[Page {n}]\n{text}')
            pages = len(pdf.pages)
    except ValueError: raise
    except Exception as exc:
        raise ValueError('Cannot read this PDF. It may be encrypted, damaged or image-only. Use a searchable PDF or paste a verified transcription.') from exc
    text = '\n\n'.join(texts)
    if len(text) > MAX_CHARS: raise ValueError('Extracted text exceeds 100,000 characters. Split the document.')
    return Extracted(text, warnings, pages)


def labelled(text, labels):
    """Only read an explicitly labelled line; never guess a deadline from a date."""
    for label in labels:
        m = re.search(r'(?im)^\s*' + label + r'\s*[:=]\s*(.+)$', text)
        if m: return m.group(1).strip()[:180]
    return ''


def metadata(text):
    # Prefer an explicit FORM label over mentions in body text or reply instructions.
    m = re.search(r'(?im)^\s*(?:FORM\s+)?(?:GST\s+)?(ASMT\s*[-\u2013]?\s*10|DRC\s*[-\u2013]?\s*01A|DRC\s*[-\u2013]?\s*01)\b', text)
    form = 'Unknown'
    if m:
        token = re.sub(r'[\s\-\u2013]+', '', m.group(1).upper())
        prefix = 'ASMT' if token.startswith('ASMT') else 'DRC'
        form = prefix + '-' + token[len(prefix):]
    gstins = list(dict.fromkeys(re.findall(r'\b\d{2}[A-Z]{5}\d{4}[A-Z]\d[A-Z0-9][A-Z0-9]\b', text.upper())))
    gstin_line = labelled(text, [r'(?:Taxpayer\s+)?GSTIN'])
    return {
        'form': form,
        'taxpayer': labelled(text, ['Taxpayer(?: name)?', 'Trade name', 'Legal name', 'Name']),
        'gstin': gstin_line or (gstins[0] if len(gstins) == 1 else ''),
        'reference': labelled(text, [r'Notice (?:reference|no\.?|number)', r'Reference(?: no\.?)?', r'Ref(?: no\.?)?']),
        'period': labelled(text, ['Tax period', 'Period', 'Financial year']),
        'issue_date': labelled(text, ['(?:Notice |Issue )?[Dd]ate', 'Date of issue']),
        'deadline': labelled(text, ['Reply due(?: date)?', 'Response (?:deadline|due date)', 'Reply by', 'Due date for reply']),
        'alleged_tax': labelled(text, ['Total (?:proposed |alleged )?tax', 'Alleged tax']),
        'gstins': gstins,
    }


def segments(text):
    """Keep page/line evidence; one line may contain more than one issue."""
    page = 1
    for line in text.splitlines():
        m = re.fullmatch(r'\[Page (\d+)\]', line.strip())
        if m: page = int(m.group(1)); continue
        for sentence in re.split(r'(?<=[.!?])\s+', line.strip()):
            if len(sentence) >= 12:
                yield page, sentence


def detect_rules(text):
    found = {}
    for key, issue in ISSUES.items():
        evidence = []
        for page, sentence in segments(text):
            if any(re.search(p, sentence, re.I) for p in issue['patterns']):
                # Suppress common explicit negations; this is deliberately not full NLP negation.
                if re.search(r'\bno\s+(?:itc\s+)?(?:mismatch|rcm|reverse charge|blocked credit|late fee)|not\s+(?:alleged|proposed|disputed)|(?:rcm|reverse charge)\s+(?:is\s+)?not applicable', sentence, re.I):
                    continue
                evidence.append({'page': page, 'text': sentence[:700]})
        if evidence: found[key] = evidence[:5]
    return found


@lru_cache(maxsize=1)
def model():
    with (BASE / 'data/training_examples.csv').open(encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    pipeline = make_pipeline(TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True),
                             LogisticRegression(C=6, random_state=42, max_iter=1000))
    pipeline.fit([r['text'] for r in rows], [r['label'] for r in rows])
    return pipeline


def ai_predictions(text):
    """Review-only suggestions. Scores are model outputs, not calibrated confidence."""
    chunks = [(page, line) for page, line in segments(text) if len(re.findall(r'[A-Za-z]{2,}', line)) >= 7]
    if not chunks: return []
    pipeline = model()
    probabilities = pipeline.predict_proba([line for _, line in chunks])
    classes = pipeline.classes_
    best = {}
    for (page, sentence), scores in zip(chunks, probabilities):
        i = int(scores.argmax()); key = classes[i]; score = float(scores[i])
        if key == 'other' or score < 0.38: continue
        if key not in best or score > best[key]['score']:
            best[key] = {'key': str(key), 'page': page, 'text': sentence[:700], 'score': score}
    return sorted(best.values(), key=lambda row: -row['score'])


def ai_suggestions(text, detected):
    return [row for row in ai_predictions(text) if row['key'] not in detected]


def review_warnings(meta, text):
    warnings = []
    if meta['form'] == 'Unknown': warnings.append('Form not recognised. Select the correct form after checking the original notice.')
    for key, name in [('gstin', 'Taxpayer GSTIN'), ('period', 'Tax period'), ('deadline', 'Explicit reply deadline')]:
        if not meta.get(key): warnings.append(f'{name} not found. Verify it manually; the app does not invent missing details.')
    if len(meta.get('gstins', [])) > 1: warnings.append('Multiple GSTINs found. Confirm the taxpayer separately from supplier/other-party GSTINs.')
    if meta['form'] == 'DRC-01': warnings.append('DRC-01 is a summary. Obtain the complete SCN and annexures before drafting a final response.')
    if re.search(r'202[4-9][-/](?:20)?(?:2[5-9]|30)', meta.get('period', '')) and re.search(r'\bsection\s+(?:73|74)\b', text, re.I):
        warnings.append('Period/provision review: the notice mentions section 73/74 with a possible FY 2024-25-onward period. Check section 74A; no automatic procedural conclusion is made.')
    return warnings


def create_draft(meta, selected, facts='', reviewer=''):
    form = meta.get('form', 'Unknown')
    procedure = PROCEDURE.get(form, PROCEDURE['Unknown'])
    value = lambda key: meta.get(key) or '[TO BE VERIFIED]'
    lines = [
        '# GST notice response - working draft',
        'NOT FOR FILING. Educational drafting aid. A qualified professional must verify every fact, provision, annexure and deadline. No admission or denial is generated.',
        '', 'To: [Name/designation/address of proper officer]',
        f'Subject: Response concerning {form} / reference {value("reference")}',
        f'Taxpayer: {value("taxpayer")} | GSTIN: {value("gstin")}',
        f'Tax period: {value("period")} | Issue date: {value("issue_date")}',
        f'Reply deadline as entered (not legally validated): {value("deadline")}',
        '', '## 1. Preliminary verification',
        procedure[1],
        'Verify jurisdiction, service date, complete notice/annexures, limitation and the governing demand provision. Sections 73/74 concern periods up to FY 2023-24; section 74A concerns FY 2024-25 onward. Check the actual period and current law, including applicable SGST/IGST provisions.',
        '', '## 2. Verified factual background', facts.strip() or '[Insert verified facts, notice chronology, business profile and reconciliation results. Do not make unsupported assertions.]',
    ]
    for n, key in enumerate(selected, 1):
        issue = ISSUES[key]
        lines += ['', f'## 3.{n}. {issue["title"]}',
                  'Allegation: [Quote the exact allegation and amount from the notice; confirm its scope.]',
                  'Provisions to examine: ' + issue['provisions'],
                  'Facts to confirm:']
        lines += ['- ' + x for x in issue['facts']]
        lines += ['Position to develop after verification: ' + issue['position'],
                  'Draft response: [Insert verified explanation, invoice/return references, reconciled amounts and applicable legal basis. Record any accepted liability only after instructions.]',
                  'Documents to attach:']
        lines += ['- ' + x for x in issue['documents']]
        lines += ['Source: ' + issue['source']]
    if not selected: lines += ['', '[No supported issue selected. Manually review the complete notice; silence is not a clean bill of health.]']
    lines += ['', '## 4. Conclusion and request',
              '[State the relief sought based on verified facts. If needed, request relied-upon documents, clarification or an opportunity of hearing. Do not use this placeholder as an admission.]',
              '', '## 5. Annexure index', '[Assign numbered annexures and cross-reference each factual statement.]',
              '', 'Prepared for review by: ' + (reviewer.strip() or '[Name of authorised professional]'),
              'Signature / place / date: [To be completed]',
              '', '## Source and review notes',
              f'Procedure source: {procedure[2]}',
              'Demand-regime source: https://taxinformation.cbic.gov.in/content/html/tax_repository/gst/acts/2017_CGST_act/active/chapter15/Section74A_v1.00.html',
              'Curated source notes checked 9 November 2026. This app does not update law automatically, compute interest/penalty/limitation, file a reply or access the GST portal.',
              'AI: local TF-IDF + logistic regression suggests issue labels from synthetic examples. Legal notes and draft skeletons are curated templates, not LLM-generated advice.']
    return '\n\n'.join(lines)


def docx_bytes(markdown):
    from docx import Document
    from docx.shared import Pt, Mm, RGBColor
    doc = Document()
    section = doc.sections[0]
    section.page_width, section.page_height = Mm(210), Mm(297)
    section.top_margin = section.bottom_margin = Mm(20)
    section.left_margin = section.right_margin = Mm(22)
    doc.styles['Title'].font.color.rgb = RGBColor.from_string('251F21')
    doc.styles['Heading 1'].font.color.rgb = RGBColor.from_string('267664')
    doc.styles['Normal'].font.name = 'Calibri'
    doc.styles['Normal'].font.size = Pt(10)
    doc.styles['Normal'].paragraph_format.space_after = Pt(5)
    doc.styles['Normal'].paragraph_format.line_spacing = 1.08
    doc.styles['Normal'].paragraph_format.keep_together = True
    doc.styles['Heading 1'].paragraph_format.space_before = Pt(10)
    doc.styles['Heading 1'].paragraph_format.space_after = Pt(5)
    for line in markdown.splitlines():
        if line.startswith('# '): doc.add_heading(line[2:], 0)
        elif line.startswith('## '): doc.add_heading(line[3:], 1)
        elif line.startswith('- '): doc.add_paragraph(line[2:], style='List Bullet')
        elif line:
            paragraph = doc.add_paragraph(line)
            if line in ('Facts to confirm:', 'Documents to attach:'):
                paragraph.paragraph_format.keep_with_next = True
    buf = BytesIO(); doc.save(buf); return buf.getvalue()
