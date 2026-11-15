# Verification record

Checked on 9 November 2026.

## Automated checks

Command: `python -m pytest -q` after installing `requirements-dev.txt`.

**Result: 29 passed.** Environment: Python 3.10 on Linux; Streamlit 1.41.1, pandas 2.2.3, pdfplumber 0.11.5, python-docx 1.1.2, scikit-learn 1.6.1 and pytest 8.3.4.

Checks include:

- All three included PDF notices extract without blank-page warnings, produce the expected form/metadata and exactly their expected supported issue topics.
- Word exports are valid DOCX archives and include the working-draft warning.
- Individual rule topics and a small set of explicit negations behave as expected.
- Missing dates/metadata remain missing or placeholders; no calendar deadline is invented.
- Multiple unlabelled GSTINs are not silently assigned to the taxpayer.
- Unknown form, malformed PDF, unsupported extension, non-UTF-8 input and oversize file paths fail safely.
- Local model performs real inference and abstains from a numeric table fragment.
- A Streamlit AppTest runs the default sample, acknowledges the draft, switches across the other two samples and reaches paste mode without application exceptions.

## Browser verification

The running app was opened in a local Chromium browser at desktop size (1440 x 1120). Summary, issue cards, editable draft and AI/audit views were exercised. A real Word download completed (approximately 38 KB). No browser page errors were recorded during this flow.

A narrow 390-pixel viewport check found no document-level horizontal overflow. Large evidence tables/text areas still use their normal component scrolling where necessary. Primary use is a Windows laptop, not a phone.

The `screenshots/` files are actual views of the running app with the fictional ASMT-10 sample, not mockups.

## What is not verified

- No Windows computer was available. Windows scripts and README steps are supplied, but the participant should run setup and all three samples on the actual recording laptop before submission.
- No independent real-notice dataset or legal accuracy benchmark was used. Passing software tests is not evidence of legal correctness or real-world classifier accuracy.
- No GST portal, live client document, actual filing, GitHub submission or video upload was performed by the software.
- Complex layouts, scanned/rotated PDFs, non-English notices, unsupported forms and unfamiliar issue types require manual review or additional tooling.

## Repeat the checks

```bat
.venv\Scripts\activate.bat
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

The app requires only `requirements.txt`; pytest is optional for normal use. Do not include the local `.venv` or test caches when publishing the folder.
