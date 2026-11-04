# Test Report: Statutory Audit Document Generator

**Result: 232 automated tests passed, 0 failed.** In addition, the packed program (exe)
and a run in a real web browser were both tested end to end.

Environment: Python 3.12, python-docx 1.2.0, pdfplumber 0.11.10, Streamlit 1.66.0,
PyInstaller 6.22.3, pytest 9.1.1.
Test data: fictitious companies, people and DINs only (`tests/make_fixtures.py`).

## 1. How to run the tests

```
py -m pip install pytest reportlab
py -m pytest -v tests
```

On a Linux server without a screen, use `xvfb-run -a python -m pytest -v tests`.

## 2. Reading the MCA master data PDF (17 tests)

Six dummy PDFs were made. Three copy the **real MCA V3 layout**: same page size and the
same label and value positions, with values centred vertically against their labels, a
two-line "books of account" label, and a bordered Director/Signatory table with a
wrapped name.

| Fixture | What it checks | Result |
|---|---|---|
| `mca_v3_one_line_address.pdf` | One-line address; listed company (CIN starts with L); class "Public" | Pass |
| `mca_v3_two_line_address.pdf` | Address starts **above** the label line (the original bug) | Pass |
| `mca_v3_three_line_address.pdf` | Three-line address centred on the label | Pass |
| `bordered_table.pdf` | All fields in a bordered table; directors with designation and category columns | Pass |
| `value_below_label.pdf` | Values printed under labels; constitution worked out from the CIN (NPL, Section 8) | Pass |
| `scanned_no_text.pdf` | Image-only PDF gives "no readable text", not a crash | Pass |

Also checked on every layout:
- The books-of-account address is never taken.
- Director **name and DIN only**, never designation or category.
- A wrapped name is joined ("VALLIAMMAI RAMANATHAN").

## 3. Documents (208 tests)

| Area | Tests | What is checked |
|---|---|---|
| **Auditor's report: every combination** | 192 | 4 opinions × 3 audit-trail answers × private/public × 4 CARO/IFC combinations × cash flow yes/no. Checks: opinion and basis headings, the qualification text, cash flow wording, annexure lettering (CARO = A, IFC = A or B), G.S.R. 583(E) exemption, section 197 and 177/188 wording, the clause 2(b) exception and the Rule 11(g) wording for each audit-trail answer, the gap period ("01/04/2025 to 14/06/2025"), no Ind AS wording, no books-of-account address |
| Engagement letter | 1 | Auditor's letterhead; no "head office / elsewhere" wording; AI and redaction clause; DPDP Act reference; director acknowledgement |
| DSC authorisation | 3 | One page per director (1, 2 and 4 directors); FY and next FY; company letterhead |
| Letter of representation | 5 | Blank depreciation and cash figures; related party table with 5 empty rows; two bank tables; sections follow the "company facts" ticks; audit-trail wording for all three answers |
| CARO clauses | 1 | Clauses (i), (iii) and (xx) follow the ticks |
| Word files | 1 | All four documents open and are A4 |
| Helpers | 5 | Financial-year text, date validation (including 31/02), spacing clean-up, safe folder names |

## 4. Screens (7 tests)

| Screen | Test | Result |
|---|---|---|
| Desktop window | Loading the MCA PDF fills company, address, directors; designation stays "Director" | Pass |
| Desktop window | An empty form lists every missing field | Pass |
| Desktop window | Audit-trail date box is enabled only for "enabled during the year", and is required then | Pass |
| Desktop window | Generates the 4 documents into the chosen folder | Pass |
| Browser app | Starts with the four tabs | Pass |
| Browser app | Generate with an empty form lists the missing details | Pass |
| Browser app | Generates the audit report and a downloadable zip | Pass |

## 5. End-to-end checks (outside pytest)

| Check | How | Result |
|---|---|---|
| **Packed program (exe build)** | Built with PyInstaller using the same settings as the Windows exe; ran `tests/exe_smoke_check.py` inside it | Logo found inside the package; PDF read correctly; 4 documents saved to `Documents\Audit Documents` |
| **Real browser** | Streamlit app driven in Chromium: upload the dummy MCA PDF, enter FRN and membership number, Generate, Download all | Zip with all 4 documents downloaded |
| **Visual check** | All 19 pages of the sample documents converted to PDF and inspected | Letterheads, tables, highlights and annexures render correctly |

## 6. Defects found by testing and fixed

| # | Found by | Problem | Fix |
|---|---|---|---|
| 1 | Real MCA PDF (user) | Only the last line of a two-line registered office was read | Values are now matched to the label with the nearest vertical centre |
| 2 | Real MCA PDF (user) | Books-of-account address and director designation/category were picked up | Field boundaries and name cleaning; tested on every layout |
| 3 | Real MCA PDF | Words ran together ("5,WEST", "tobe") with the first PDF library | Switched to pdfplumber word positions |
| 4 | Exe smoke test | The packed program could not find python-docx's header template, so no document could be saved | The template folder is recreated at start-up when running as an exe |
| 5 | Exe smoke test | Saving next to the exe would write into a temporary folder that is deleted | The exe saves to `Documents\Audit Documents` |
| 6 | Unit test | A space before a comma was kept ("STREET , MADURAI") | Spacing clean-up corrected |
| 7 | Unit test | "&" in a company name gave a double underscore in the folder name | Folder-name clean-up corrected |

## 7. Not covered by automated tests

- **The real Windows exe on a Windows PC.** The package build was tested on Linux with
  identical settings. The GitHub workflow in `docs/BUILD_EXE.md` also builds and tests
  the exe on Windows.
- **Unredacted real MCA PDFs.** Only a redacted real file and dummy copies of its layout
  were used. Check the filled-in details against the master data on first use.
- **Legal accuracy of the wording.** The documents are drafts for professional review.
