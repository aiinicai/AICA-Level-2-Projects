# 1-Click Tax Notice Decoder

**Vaibhav Jain, Chartered Accountant**  
AI-assisted Income Tax & GST Notice Analysis

A runnable Python/Streamlit tool: decode a notice, review client evidence, research
applicable law and judgments on both sides, prepare a strategy, then generate and
critically review a comprehensive reply for editing and Word download. The app
retains one page with no accounts, database, dashboard or sidebar. Navy/blue,
gold/yellow, grey and maroon styling adds light effects and readable highlights.

## Quick start

Prerequisites: **Python 3.11+** (64-bit), an internet connection for package setup
and live AI requests, and an API key with access to a structured-output model.
Tesseract is required only for scanned or image-only pages. Poppler is **not**
required: this implementation uses the PDFium renderer supplied by `pypdfium2`.

Open a terminal in this project directory.

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env with your API key and supported model.
.\.venv\Scripts\python.exe -m streamlit run app.py
```

macOS/Linux:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API key and supported model.
streamlit run app.py
```

Open **http://localhost:8501**. The **Try Sample Notice** button works without
credentials and uses fictional, prewritten analysis and draft templates. It is
explicitly labelled “Demo Notice”. Live uploads never silently use demo results.
The included `assets/fictional_sample_notice.pdf` can be uploaded to exercise the
real extraction and AI path after configuration. It is not an official notice.

On Windows, after setup double-click `start_app.cmd`. It starts the app in the
background, waits for it to be ready, then opens the browser. Closing the launcher
window does not stop the app. Run the launcher again after restarting Windows;
it reuses an already-running server. Startup diagnostics are in `.runtime/`.
If you instead use the foreground terminal command, closing that terminal stops
that server.

If an environment is already set up, the basic launch command is:

```sh
streamlit run app.py
```

## Configuration

`.env` is read next to `app.py`; environment variables already set by the host take
precedence. Never commit `.env` or paste credentials into the editor.

| Variable | Purpose |
| --- | --- |
| `OPENAI_API_KEY` | Server-side API credential; required for live notices |
| `OPENAI_MODEL` | Model available to your account with structured JSON support |
| `OPENAI_RESEARCH_MODEL` | Optional model supporting Responses `web_search` with structured outputs; otherwise uses `OPENAI_MODEL` |
| `OPENAI_BASE_URL` | Optional trusted OpenAI-compatible API endpoint |
| `TESSERACT_CMD` | Optional full path to the Tesseract executable |
| `OCR_LANGUAGE` | Installed Tesseract language(s); default `eng`, e.g. `eng+hin` |

The sample model in `.env.example` is configurable, not a promise of account
availability. Alternative providers must support the OpenAI chat-completions
endpoint, strict JSON schemas and `store=False`. Unsupported providers return a
friendly error; there is no fallback to unvalidated free-form output.
Live research additionally requires the Responses API, hosted web search, official
domain filters and structured outputs. It may incur separate search charges.

The integration follows OpenAI's [structured outputs documentation](https://developers.openai.com/api/docs/guides/structured-outputs).
An analysis request is made per chunk, followed by document planning. Supporting
documents are analysed separately. Research uses the documented
[Responses web search tool](https://developers.openai.com/api/docs/guides/tools-web-search).
Strategy preparation, drafting and a critical-review pass are separate requests.
Changing a checkbox, editing the reply or downloading Word does not call the API.

## Tesseract installation

See the [official Tesseract installation guidance](https://tesseract-ocr.github.io/tessdoc/Installation.html).

- **Windows:** install a Windows distribution linked by the Tesseract project;
  ensure the English language data is selected. Add the install folder to PATH or
  set `TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe` in `.env`.
  The app also detects the standard Program Files install automatically.
- **macOS:** `brew install tesseract` (with Homebrew already installed).
- **Debian/Ubuntu:** `sudo apt-get install tesseract-ocr tesseract-ocr-eng`.
- Install additional language packs before setting `OCR_LANGUAGE` to them.

Confirm installation with `tesseract --version`, then restart Streamlit. No
Poppler install or `pdf2image` dependency is needed. A clear scan at about 300 DPI
works best. The app renders only pages that have inadequate selectable text.
Tesseract’s temporary files are cleaned by pytesseract; rendered images and PDF
handles are closed in `finally` blocks.

## Using the app

1. Upload a PDF of up to **20 MB and 60 pages** and select **Decode Notice**.
2. Read the summary and issue cards, check the source excerpts, and verify any
   uncertain or unreadable pages. The original extracted text is available below.
3. **Gather & analyse client documents.** Review the issue-linked requirements,
   distinguishing notice requests from AI suggestions. Mark what the client has,
   upload available PDF/DOCX/XLSX/CSV/TXT files and analyse them. Maximum 10 files,
   20 MB each, 50 MB combined. Export photographs as PDFs. Explain missing records
   and client instructions; unverified statements are not established facts.
4. **Research applicable provisions.** Review the editable public legal topics,
   remove private details, and include the jurisdiction and legal period. Run
   **Research law & case law** to search acts, rules, regulations, circulars,
   notifications and judgments on official Indian government/court domains.
5. **Examine case law on both sides.** Review favorable, adverse and neutral/mixed
   authorities, original source links, pinpoints, factual distinctions and status
   checks. Missing categories remain research gaps; no cases are invented.
6. **Settle the response strategy.** Prepare an issue-wise plan using the evidence,
   law, competing arguments, procedural checks and gaps. If research cannot be
   performed, explicitly record it as outstanding before proceeding; no sourced
   legal conclusions are implied by that route.
7. **Review your reply.** Generate a comprehensive reply, followed by a separate
   critical-review pass. Resolve its notes, edit and download Word or copy the
   text. If clipboard permissions block copying, use Ctrl+C / Cmd+C in the editor.

Changes to supporting files, availability, client notes or research invalidate
the strategy. Changed research topics also invalidate research. Existing draft
edits remain visible with a stale-record warning. Rebuild the strategy before
regenerating; one previous draft can be restored. Style changes apply to the next
generation only. Uploads are **not** attached to Word or filed automatically.

**Clear notice & start again** clears notice, evidence, research and strategy
session data. In sample mode, the complete workflow works offline without
inventing legal research. It cannot analyse real client documents; use live mode
for those. The sample research report intentionally contains no authorities.

The sample contains fictional amounts and dates and no real taxpayer identifiers.
Its fixed 27 September 2026 deadline can legitimately appear overdue after that
date; days remaining are computed in the Asia/Kolkata timezone.

## Architecture

```text
app.py                         Single-page UI and session lifecycle
services/models.py             Strict Pydantic analysis/draft schemas
services/pdf_service.py         Validation, pdfplumber, per-page OCR selection
services/ocr_service.py         PDFium rendering and local Tesseract adapter
services/llm_service.py         Structured extraction, evidence checks, drafting
services/document_service.py    In-memory Word export from current edited text
services/demo_service.py        Fictional offline sample and style variants
services/case_models.py         Evidence, legal authority and strategy schemas
services/case_service.py        Document planning/review, strategy, critical review
services/evidence_service.py    Bounded client PDF/Word/Excel/CSV/text extraction
services/research_service.py    Live official-source legal research
services/demo_case.py           Offline strategy and research-gap examples
utils/validators.py             File limits and user-safe errors
utils/helpers.py                Text/date/file formatting and clipboard helper
utils/case_workflow.py          Seven-stage session workflow and invalidation
utils/ui.py                     Escaped presentation helpers
assets/styles.css              Responsive colour palette, highlights, lighting
tests/                         Service and Streamlit workflow regression checks
assets/fictional_sample_notice.pdf  Fictional upload fixture
scripts/create_test_notices.py  Rebuild fictional test PDFs (dev dependencies)
requirements.txt               Runtime dependencies
requirements-dev.txt           Additional test dependencies
.env.example                   Credential-free configuration example
.streamlit/config.toml          Theme, local binding and upload/error settings
```

Files are processed in memory wherever practical. Each page is checked for
meaningful text; mixed PDFs receive OCR only on low-text pages. Blank or poorly
readable pages raise a visible warning and are not treated as proven empty.
Encrypted PDFs are rejected, including those that can be opened with a blank
password. Oversized documents are rejected rather than silently truncated.

Notices longer than 18,000 characters are covered by overlapping chunks. Every
chunk is extracted, then facts are combined deterministically without dropping
later-page issues. Conflicting metadata and deadlines are surfaced. Drafting only
starts after consolidation; oversized consolidated facts cause a clear error
rather than truncation. The full list of summary points is retained for drafting,
while the initial summary displays at most six points.

Sections, issues and requested documents include source excerpts. Quotes and
section strings are checked against extracted text; these checks verify textual
support, not the correctness of every AI interpretation. Exact deadline dates
require high confidence and an explicit matching date in source wording. Relative
receipt/service periods and conflicting deadlines do not produce a countdown.
Legal research is a separate explicit step. Only HTTPS gov.in/nic.in sources
actually returned by a completed web-search call are accepted as linked authorities.
Matching a URL does not prove a legal proposition, good-law status or applicability.
There is no guarantee of exhaustive research or a legally watertight outcome.

## Confidentiality and limitations

**Tax documents may contain confidential information. Ensure your organisation
permits processing through the configured AI provider.**

- Live analysis sends extracted notice text to the configured provider. Drafting
  sends extracted facts and evidence. Provider billing and retention policies
  apply, even though the request sets `store=False`.
- Supporting documents also go to the configured AI provider for evidence review.
  Only the editable public-research field is sent to the web-search request, not
  raw notices, client notes or evidence. Review that field before searching.
- Evidence-review, strategy and critical-review roles are application prompts.
  They are not a claim that desktop Codex skills or a separate human expert run
  inside the app. The critical review uses another model call, not an independent
  certification of factual or legal accuracy.
- Excel formulas are preserved as expressions, not recalculated. Word text boxes,
  embedded images, headers, comments and revisions need manual review. Export a
  faithful PDF when those parts matter. Office archives and text sizes are bounded.
- This app does not intentionally persist uploaded notices or log their contents.
  Text, analysis and drafts remain in Streamlit session memory. Browser memory,
  operating-system temporary storage and deployment infrastructure have their
  own retention behavior. This is not a guarantee of complete security or no storage.
- Refreshing/disconnecting can lose session data. Download reviewed work before
  closing the page. There is no persistent draft history or database.
- OCR can misread dates, names, Indian digit grouping, stamps and tables. Low-text
  heuristics cannot detect every bad hidden-text layer. Review the original PDF.
- AI can misclassify a document or produce unsupported interpretations despite
  schema validation and evidence checks. It does not validate supplied evidence,
  attach documents, file responses, or confirm portal compliance.
- Word export preserves the editor's plain text and line breaks. Subject lines
  and numbered issue headings are bold; Markdown syntax is not rendered.
- Clipboard behavior depends on browser permissions and secure-context support.
- Processing time depends on page count, scan quality, hardware and provider
  latency; “in seconds” is interface copy, not a service-level guarantee.

**AI-assisted draft. Verify facts, legal provisions, portal requirements,
attachments and deadlines before submission.**

## Verification

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

Tests use fictional PDFs and mocked provider responses; they do not send documents
to a provider or require a paid API call. An OCR integration test runs only when
Tesseract is available. Tests cover searchable/mixed PDFs, encryption and invalid
files, all-chunk coverage, unsupported evidence, relative/conflicting deadlines,
Word content, safe copying markup, and Streamlit edit/regenerate/reset behavior.
Additional tests cover evidence formats, source-URL allowlisting, requiring actual
web-search calls, two-pass drafting and invalidation after case inputs change.
Live API operation requires valid credentials and should be checked with a
fictional test notice in the target deployment before confidential use.

## Deployment

Deploy on a private host supporting Python and Tesseract. Install runtime
dependencies, set secrets as server environment variables, and run Streamlit.
For a container or remote host, explicitly override the local default:

```sh
streamlit run app.py --server.address=0.0.0.0 --server.port=8501
```

Place remote deployments behind your organisation's HTTPS access control. Do not
expose this unauthenticated MVP publicly with real notices. Configure resource
limits, request timeouts, permitted outbound providers and retention policies at
the hosting layer. Keep Streamlit error-detail hiding enabled. No deployment,
account setup, payment, or API credential is included with the source project.

Troubleshooting: missing credentials/model → update `.env` and restart; scans not
readable → install Tesseract/language data or improve the scan; provider failure →
check model access, quota, connection and structured-output compatibility; Word
failure → remove control characters from the editor and retry. Error messages
never intentionally expose raw exception text or notice contents.
