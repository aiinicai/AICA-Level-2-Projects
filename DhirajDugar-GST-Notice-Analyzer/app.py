"""Run locally with: python -m streamlit run app.py"""
from pathlib import Path
from hashlib import sha256
import json
import re
import streamlit as st
from engine import extract_document, metadata, detect_rules, ai_suggestions, ai_predictions, review_warnings, create_draft, docx_bytes
from knowledge import ISSUES, PROCEDURE, S74A

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title='GST Notice Analyzer', page_icon='📑', layout='wide')
st.markdown('''<style>
.block-container {padding-top:2.5rem; max-width:1280px}
h1 {font-family:Georgia,serif; letter-spacing:-1px; font-weight:500}
h2,h3 {letter-spacing:-.4px}
[data-testid="stMetric"] {background:#f4efec; padding:18px; border-radius:10px; min-height:120px}
[data-testid="stMetricValue"] {font-size:1.7rem}
[data-testid="stSidebar"] {border-right:1px solid #eae9ea}
</style>''', unsafe_allow_html=True)

with st.sidebar:
    st.markdown('### GST Notice Analyzer')
    st.caption('AICA Level-2 • Capstone prototype')
    st.divider()
    mode = st.radio('Notice source', ['Sample notice', 'Upload PDF / text', 'Paste notice text'])
    data = None; filename = ''
    if mode == 'Sample notice':
        choices = {
            'ASMT-10 · ITC + output liability': '01_ASMT10_Scrutiny.pdf',
            'DRC-01 · RCM + blocked credit': '02_DRC01_ShowCause.pdf',
            'DRC-01A · late filing + RCM': '03_DRC01A_PreNotice.pdf',
        }
        choice = st.selectbox('Choose a fictional example', list(choices))
        filename = choices[choice]
        data = (ROOT / 'samples' / filename).read_bytes()
        st.download_button('Download sample PDF', data, file_name=filename, mime='application/pdf', use_container_width=True)
    elif mode == 'Upload PDF / text':
        uploaded = st.file_uploader('Searchable PDF or UTF-8 text', type=['pdf', 'txt'])
        if uploaded: data, filename = uploaded.getvalue(), uploaded.name
        st.caption('10 MB / 30 pages / 100,000 characters maximum. Scanned PDFs need OCR first.')
    else:
        pasted = st.text_area('Paste verified notice text', height=240, max_chars=100000)
        if pasted.strip(): data, filename = pasted.encode('utf-8'), 'pasted_notice.txt'
    st.divider()
    use_ai = st.toggle('Local AI suggestions', value=True)
    st.caption('Offline TF-IDF + logistic regression. Suggestions need confirmation. No API key or external model call.')
    st.info('Runs locally. Do not put client notices in a public repository. Do not deploy publicly with live client data.')
    st.caption('Prepared for Dhiraj Dugar • Educational use')

st.caption('NOTICE → EVIDENCE → REVIEW → DRAFT')
st.title('From GST notice to a clear review plan')
st.write('Find the issues, inspect the evidence and prepare a structured reply skeleton. You remain in control of every conclusion.')
st.warning('Drafting aid, not a tax opinion. All extracted fields and suggested provisions require CA review. No reply is filed and no liability is admitted.')

if data is None:
    st.info('Upload a notice, paste its text, or choose a fictional sample to begin.')
    st.stop()

fingerprint = sha256(data).hexdigest()[:12]
try:
    extracted = extract_document(data, filename)
except ValueError as exc:
    st.error(str(exc)); st.stop()
if len(re.sub(r'\[Page \d+\]', '', extracted.text).strip()) < 25:
    st.error('No usable text found. Use OCR outside this app, then upload a searchable PDF or paste a checked transcription.'); st.stop()

meta = metadata(extracted.text)
detected = detect_rules(extracted.text)
predictions = ai_predictions(extracted.text) if use_ai else []
suggestions = [row for row in predictions if row['key'] not in detected]
for warning in extracted.warnings:
    st.error(warning)

left, middle, right = st.columns([1, 1, 1])
left.metric('Detected form', meta['form'])
middle.metric('Rule-flagged topics', len(detected))
right.metric('Pages processed', extracted.pages)
st.caption(f'Source: {filename} · No tax or penalty is computed. A detected topic is an allegation to review, not a finding of liability.')

overview, issues, draft_tab, technical = st.tabs(['1  Notice summary', '2  Issues & evidence', '3  Reply draft', '4  AI & audit trail'])

with overview:
    st.subheader('Read the notice before drafting')
    p = PROCEDURE.get(meta['form'], PROCEDURE['Unknown'])
    st.markdown(f'**{p[0]}**')
    st.write(p[1]); st.link_button('Open procedure source', p[2])
    for warning in review_warnings(meta, extracted.text): st.info(warning)
    with st.expander('Confirm or correct extracted details', expanded=True):
        st.caption('Only explicitly labelled fields are extracted. Deadline is copied as text, never calculated from issue date. The GSTIN is not verified against the GST portal.')
        a, b = st.columns(2)
        with a:
            meta['form'] = st.selectbox('Confirmed form', list(PROCEDURE), index=list(PROCEDURE).index(meta['form']), key=f'form_{fingerprint}')
            meta['taxpayer'] = st.text_input('Taxpayer name', meta['taxpayer'], key=f'name_{fingerprint}')
            meta['gstin'] = st.text_input('Taxpayer GSTIN', meta['gstin'], key=f'gstin_{fingerprint}')
            meta['reference'] = st.text_input('Notice reference', meta['reference'], key=f'ref_{fingerprint}')
        with b:
            meta['period'] = st.text_input('Tax period', meta['period'], key=f'period_{fingerprint}')
            meta['issue_date'] = st.text_input('Issue date as printed', meta['issue_date'], key=f'date_{fingerprint}')
            meta['deadline'] = st.text_input('Reply deadline / instruction as printed', meta['deadline'], key=f'deadline_{fingerprint}')
            meta['alleged_tax'] = st.text_input('Alleged tax as labelled, not validated', meta['alleged_tax'], key=f'amount_{fingerprint}')
    if meta['form'] != 'Unknown':
        st.caption('Confirmed procedure: ' + PROCEDURE[meta['form']][1])
    st.info('Demand-regime check: sections 73/74 concern periods up to FY 2023-24; section 74A concerns FY 2024-25 onward. Check the actual period and applicable law. No limitation/deadline calculation is performed.')
    st.link_button('Read CGST section 74A', S74A)
    with st.expander('Inspect extracted notice text'):
        st.text(extracted.text)

with issues:
    st.subheader('Evidence first. Legal conclusion later.')
    st.caption('Rules can miss issues, misread negation or flag a neutral reference. Confirm, remove or add topics below after reading the original notice. Unfamiliar notices may be outside this prototype\'s scope.')
    selected = st.multiselect('Topics to include in the reply skeleton', list(ISSUES), default=list(detected), format_func=lambda key: ISSUES[key]['title'], key=f'issues_{fingerprint}')
    if not detected:
        st.warning('No supported topic was rule-flagged. This does not mean the notice has no issues. Review the complete document and add topics manually if relevant.')
    for key in selected:
        item = ISSUES[key]
        with st.container(border=True):
            st.markdown('### ' + item['title'])
            evidence = detected.get(key, [])
            if evidence:
                st.caption('NOTICE EXTRACT • verify against original')
                for quote in evidence: st.info(f'Page {quote["page"]}: {quote["text"]}')
            else: st.warning('Manually selected topic. Verify and quote the exact allegation; no rule evidence was found.')
            st.markdown('**Provisions to examine**'); st.write(item['provisions'])
            st.markdown('**Facts to confirm**')
            for fact in item['facts']: st.markdown('- ' + fact)
            st.markdown('**Reply direction, subject to verification**'); st.write(item['position'])
            with st.expander('Documents to gather + official source'):
                for doc in item['documents']: st.markdown('- ' + doc)
                st.link_button('Read official source: ' + item['title'], item['source'])

with draft_tab:
    st.subheader('Build a working reply skeleton')
    st.caption('This is deliberately not a finished legal reply. Unknown facts remain placeholders; the app does not invent admissions, case law, annexure numbers or payment claims.')
    facts = st.text_area('Verified facts / case notes (optional)', key=f'facts_{fingerprint}', height=100, placeholder='Enter only facts you have checked. These are inserted as typed, not validated by the app.')
    reviewer = st.text_input('Reviewing professional (optional)', key=f'reviewer_{fingerprint}')
    generated = create_draft(meta, selected, facts, reviewer)
    draft_key = sha256(generated.encode()).hexdigest()[:16]
    edited = st.text_area('Editable working draft', generated, height=420, key=f'draft_{draft_key}')
    st.caption('Changing notice details, selected topics or case notes regenerates the skeleton. Download your edits before changing those inputs.')
    confirmed = st.checkbox('I understand this is an unverified working draft, not ready for filing.', key=f'confirm_{fingerprint}')
    c1, c2 = st.columns(2)
    c1.download_button('Download Word draft', docx_bytes(edited), file_name='GST_Notice_Working_Draft.docx', mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document', disabled=not confirmed, use_container_width=True)
    c2.download_button('Download Markdown draft', edited, file_name='GST_Notice_Working_Draft.md', mime='text/markdown', disabled=not confirmed, use_container_width=True)

with technical:
    st.subheader('Transparent, local AI')
    st.write('The model is a TF-IDF (word + bigram) vectorizer with logistic regression, trained on 60 synthetic labelled sentences across five supported issues and one "other" class. It suggests additional topics for human review. Evidence rules populate the initial topic selection; AI does not decide the legal position.')
    st.caption('This small training set is a teaching prototype, not validated for production notices. Scores are uncalibrated model outputs, not probabilities of legal correctness. The model can miss unfamiliar wording or overpredict an issue.')
    if predictions:
        st.markdown('**Local model classifications (review only)**')
        st.dataframe([{'Suggested topic': ISSUES[row['key']]['title'], 'Model score': round(row['score'], 2), 'Rule also flagged': row['key'] in detected, 'Page': row['page']} for row in predictions], use_container_width=True, hide_index=True)
    if not use_ai: st.info('Local AI suggestions are switched off. Rule-based review and exports still work.')
    elif suggestions:
        for suggestion in suggestions:
            st.markdown('**Possible additional topic: ' + ISSUES[suggestion['key']]['title'] + '**')
            st.write(f'Model score: {suggestion["score"]:.2f} · page {suggestion["page"]}')
            st.code(suggestion['text'], language=None, wrap_lines=True)
        st.info('To use a suggestion, confirm it against the original notice and add the topic in Issues & evidence. It is never silently added to the reply.')
    else: st.info('No additional AI topic cleared the review threshold of 0.38. This is not an assurance that all issues were found.')
    st.markdown('**Audit trail**')
    audit = {'document_sha256': sha256(data).hexdigest(), 'source_filename': filename, 'confirmed_metadata': meta,
             'selected_topics': selected, 'rule_evidence': detected, 'ai_suggestions': suggestions, 'ai_predictions': predictions,
             'source_notes_checked': '2026-11-09', 'extract_warnings': extracted.warnings,
             'model': 'TF-IDF + LogisticRegression, 60 synthetic training examples, seed 42',
             'limits': 'Review required; no OCR, live law updates, deadline computation, liability calculation or filing.'}
    st.json({'document_hash': fingerprint, 'selected_topics': selected, 'source_notes_checked': '2026-11-09'})
    st.download_button('Download analysis audit JSON', json.dumps(audit, ensure_ascii=False, indent=2), file_name='GST_Notice_Review_Audit.json', mime='application/json')
    st.warning('The audit JSON includes extracted client metadata and notice quotations. Treat downloads as confidential case files, not as public project assets.')

st.divider()
st.caption('Local-first educational prototype • Sources checked 9 November 2026 • Fictional demo notices • Professional review required')
