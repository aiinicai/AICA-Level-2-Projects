# Net Asset Report 2.1.2

Private, local desktop source application for reviewed net-asset reports.
Made by CA LOVE KUMAR · MB: 88378-83498

**This ZIP is Python source, not a standalone EXE.** No client workbooks, real
ITR PDF, credentials, CA profiles or OCR engines are bundled. Windows Python
3.14 and a compiled EXE have not been runtime-tested here. Current2.1.2 desktop
acceptance of the bounded2.1.2 changes is PENDING.2.1.1 passed the repaired
compact layout, scrolling, preview and listed functional workflows; its remaining
tab/cancel/clean-prompt/preview-position/export-access issues are patched here. Do not treat headless tests as a desktop PASS.
Headless tests run on Linux Python 3.12; see `docs/QA_RESULTS.md`.

## Start on Windows

1. Extract the ENTIRE ZIP to a writable local folder. Keep the modules together.
2. Install Python with Tk support. Run **Install Dependencies.bat** once with
   internet access. It creates a local `.venv` and installs `requirements.txt`.
   Python 3.12 is the tested interpreter; the selected dependency versions must
   also provide wheels for any newer interpreter you choose.
3. Double-click **Launch Net Asset Report.vbs**. It uses the local
   `.venv\Scripts\pythonw.exe`, so it does not create a console window.
   `Launch Net Asset Report.pyw` is an alternate pythonw launcher.
4. Optional: **Build Net Asset Report EXE.bat** builds a Windows PyInstaller
   distribution on Windows. This source delivery does not contain that EXE.
   Selenium/Chrome and OCR resources still require their own runtime setup.

Running `python.exe net_asset_report.py` inside an existing command prompt
cannot hide that parent console. OCR/version probes suppress their own Windows
windows and capture binary bytes with safe decoding; no locale reader-thread
UnicodeDecodeError is expected from those probes. This is source/mocked
coverage, not proof on the user's Python 3.14 installation.

Linux: `python3 -m venv .venv`, `.venv/bin/python -m pip install -r requirements.txt`,
then `.venv/bin/python net_asset_report.py` in a graphical desktop. Tk may require
your OS's `python3-tk` package. macOS/Tk startup behavior is not runtime-verified.

Old2.1.0 JSON cases with cropped-only letterpad data must reselect the original
whole-page image/PDF; discarded centre pixels cannot be reconstructed. New
2.1.2 cases preserve full artwork portably.

## Ordinary workflow

1. **Applicants**: add one or more applicants. Import passport front/back into
   the explicitly selected person, review the extracted name, dates and labels,
   then Apply. A valid reviewed name can fill an unnamed selected applicant.
   Wrong-type documents offer reclassification instead of empty ITR fields.
   Add family owners separately; review Relationships before asserting a family
   link. A person's own father name is not their relationship to an applicant.
2. **Assets**: choose an owner, asset type, editable **Asset name**, INR value and
   the source-specific supporting fields. Cash is inline, not a popup. The table
   groups immovable and movable items with subtotals; select a row to read its
   complete details and confirmed relationship without table truncation.
3. **Documents & review**: import reports; check owner evidence/name and choose
   or explicitly create/match an owner. Every asset document has an editable
   proposal even if its amount is uncertain. Choose a contextual **Value
   candidate** or type **Value (INR)**, edit Asset name and Apply. Final certified
   totals outrank per-unit rates; true conflicts stay visible. Applying a second
   document preserves the first asset. Identical-document hashes, not common
   owner names, drive duplicate warnings.
4. **Remove document** removes the selected intake record, never its disk file.
   For applied records choose document-only or removal of unchanged linked
   imports. Manually edited records are protected. Passport removal preserves
   the applicant identity and unrelated assets. **Undo removal** is session-local.
5. **ITR & income** appears only after ITR/computation evidence is selected or
   applied. Review person AND assessment year. Independently extracted ITR and
   computation values remain available; choose sources and confirm additional
   agriculture/other exempt values do not overlap. Missing values are unknown,
   not zero. One reviewed annual figure per person/year enters Annexure C,
   **never asset/net-asset totals**. Select one report year when several exist.
6. **Firm settings**: enter the chosen signer's details; Add/Load/Update/Remove
   saved CA profiles. **Remove CA** names the target and confirms; it leaves the
   current report/signature snapshot unchanged and deletes no shared images.
   Upload your JPEG/PNG signature and tick Include in reports. Custom letterpad
   accepts a header image or a one-page PDF/image; whole-page mode retains the complete artwork as a behind-text page background,
   including centre watermark and footer. Header/footer body margins are reserved.
   Preview your actual artwork: a dark centre can reduce text contrast. Images are embedded
   portably in JSON, not dependent solely on their original filesystem paths.
7. **Report**: choose country (original eight supported currencies), with currency
   override where needed. FX date is the statement date unless explicitly set.
   Date/country changes invalidate and asynchronously fetch the requested dated
   rate. The display states **INR per 1 foreign currency**, source, requested and
   effective dates. Alternate dates require approval. Future automatic rates
   are unavailable; past reports are permitted with a review warning. A manual
   override is explicitly labelled, not an invented market quote.
8. Expand **Print layout, sections & Excel print areas**: A4/Legal/Letter,
   portrait/landscape, margins, selected report sections and Excel fit width or
   actual size. Excel per-sheet A1 ranges must be inside the generated used
   range. PDF page selection is distinct from Excel print areas.
9. The Report **Preview final PDF / Export Excel / Export Word / Export PDF**
   action bar stays pinned above the scrolling form; JSON Save is separate.
   **Preview final PDF** creates the actual report PDF through the same exporter.
   Navigate pages/last page, zoom, then Open/Print PDF in the system viewer.
   Changed inputs make a preview stale and require rebuilding. The application
   does not submit a print job. This is NOT Excel/Word's own print pagination.
10. Separate pinned **Export Excel / Export Word / Export PDF** buttons write actual
    `.xlsx` / `.docx` / `.pdf` files. Save dialogs use normal overwrite prompts.
    Invalid/inaccessible paths produce visible errors; atomic writes protect an
    existing target when export fails. **Save case** is different: private JSON
    for reopening/editing, reusing its active path. **Save as / JSON** creates
    another case; **Open case** restores the editable case. Clean Save/Save-as/Open
    does not ask an unsaved-change question. Fingerprints detect real changes,
    including unapplied inline edits, which still require Add/Save changes.
    Cancel edit clears the draft and resets Add item in one callback.

## Assisted UDIN (source parity, live selectors UNVERIFIED)

The Report controls check readiness then open a visible Selenium/Chrome browser
using selectors recovered from the uploaded original app. Log in and handle
captcha yourself in that browser. The helper waits for expected form fields,
fills the report mapping and highlights missing fields without blind clicking.
Review before pressing **Request OTP**; each explicit action requests at most
one OTP with a cooldown. Enter OTP and perform final generation yourself in the
browser. **Read generated UDIN** reads a completed result. No passwords or OTPs
are saved in cases/profiles/exports. Tests use a fake DOM/driver only: no portal
login, OTP request or final submission was performed for this release. Selector
mismatch stops and allows manual completion; it does not bypass captcha or use
internal endpoints. Chrome/Selenium Manager may need internet to obtain a driver.

## OCR setup and privacy

Text PDFs and TXT files work without an OCR executable. Image/scanned pages need
local Tesseract and its language files. Choose a local OCR executable in the
Documents controls if automatic discovery fails. No OCR executable is included;
resource folder compatibility with the original `networth_ocr` is retained.
Original OCR bytes/text and conservatively repaired display text remain evidence;
uncertain values still need review. Unread scanned pages produce warnings rather
than invented values. All processing is local except requested public FX queries
and the explicitly opened UDIN portal. Reports do not silently upload documents.

JSON contains personal evidence, document references and embedded images: treat
it as sensitive, not as an anonymized interchange file. Case schema/version and
stable IDs preserve ownership, sources, review choices, rates and print settings.
Known original JSON shapes migrate; unknown or ambiguous owners require review.
Secrets are excluded. Source PDFs themselves are NOT embedded; missing original
paths do not erase reviewed assets/evidence, but re-OCR needs the originals.
**Generated Excel includes hidden Sheet1 passport metadata outside its print
range. Hidden cells are not security: share the workbook only as a private file.**

## Exact template mapping and limits

See `docs/SOURCE_PARITY_2.1.0.md`, `docs/FORMULA_REVIEW.md` and the privacy-safe
`docs/reference_structure_2.1.0.json`. All three accessible Excel references and
the actual sample ITR PDF were inspected; macros were never run or shipped.
The separate immovable/movable/income structure and bold/source wording are
preserved with dynamic rows, not a byte/pixel-identical copy. Deliberate repairs
include broken references, incomplete income sums and a wrong income total label.

Concrete limits: one explicit owner per asset row (no fractional joint-owner
allocation); the current eight-currency country list is not a world-country
catalogue; no automatic tax-law decision about net agricultural/J-Form income;
no guaranteed recognition of every vendor/scanned computation; UDIN selectors
need live user verification; Header-image mode in Excel uses a once-per-sheet image and its first-page
toggle skips the first selected worksheet; whole-page mode uses repeating print
header VML picture backgrounds (Office rendering not yet runtime-verified); Word/Excel pagination differs from
PDF preview. Use the header Window dropdown to set an exact1024 x578 or1280 x800 client
size; it exits maximized state. The footer and asset actions are pinned outside
scrolling content; Assets uses one continuous scrollable form, not squeezed
vertical panels. Wheel events route over child fields without moving focus.
Corrected desktop controls still require acceptance retest, as does Windows runtime. This delivery does not claim a built/tested Windows EXE.

## Reproducible smoke fixtures/tests

`examples/SYNTHETIC_review_case_2.1.2.json` contains two artificial applicants,
a reviewed family owner, grouped assets, paired income and embedded signature /
letterpad. `SYNTHETIC_valuation_first.txt` and
`SYNTHETIC_valuation_second_ambiguous.txt` exercise consecutive imports with a
manual/candidate total. All examples are **NOT FOR ISSUE**. Actual synthetic
Excel/Word/PDF reports are included. No real uploaded client files are packaged.

Install `requirements-dev.txt`, then `python -m pytest -q tests`.
`MANIFEST.sha256` authenticates the included files against accidental changes;
it is not a cryptographic publisher signature. The ZIP and extracted-tree test
results are documented in `docs/QA_RESULTS.md`.
