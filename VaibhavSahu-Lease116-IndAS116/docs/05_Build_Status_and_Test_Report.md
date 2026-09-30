# Lease116 — Build Status and Test Report

| Item | Detail |
|---|---|
| Document | 05 — Build status, validation and test report |
| Release | v1.1.0 — lessee engine 1.0.0; lessor engine 2.0.0 (lessor module rebuilt in this release) |
| Test run | 27 September 2026 — **101 automated test executions passed, 0 failed** (`python -m pytest -q`), in two independent environments |
| Target PC | Windows 11 (ARM64), Python 3.12.10 x64 — Setup self-test passed; on-device agreement-reader test passed (§2.4) |
| UI verification | Browser automation (Chromium): every screen opened as Administrator and as Auditor; end-to-end flows executed; 0 application errors in the browser console |

## 1. Scope delivered (v1)

| Area | Status | Notes |
|---|---|---|
| Accounting engine — lessee (initial and subsequent measurement, events, FX, deposits, restoration, impairment) | Complete | Decimal arithmetic; exact dates; balance-driven rounding |
| Accounting engine — lessor (classification, finance and operating leases, manufacturer / dealer, deposits received, IDC, variable and non-lease components, modifications 79 / 80(a) / 80(b) / 87, termination, residual reduction, ECL, para 89–97 note) | Complete (v1.1) | Recomputed independently — §2.5 |
| Exemptions, sublease (B58), sale and leaseback, deferred-tax support | Complete (core) | See methodology §10 |
| Agreement reader — PDF / scanned PDF / image / Word / text; OCR; computer vision; rules; optional local LLM or Claude API | Complete | Offline by default; cloud use needs admin permission + per-document consent |
| Database, REST API (78 operations, OpenAPI documented), maker-checker workflow, period locks, audit trail | Complete | SQLite in `%LOCALAPPDATA%\Lease116\data`; no schema change in v1.1 |
| Web UI — 18 screens, 12 lease tabs, "How calculated?" drill-down, dark mode, ₹ absolute / lakh / crore | Complete | Offline single-page app served from the PC |
| Journals (CSV, Excel, Tally XML, SAP-style CSV), 19 reports (Excel / CSV / PDF), disclosure note (Excel, lessee and lessor), audit workpaper and accounting memo for lessee and lessor leases | Complete | |
| Imports with validation, error report and maker-checker approval | Complete | 5 templates |
| Windows installer (x64 and ARM64) | Complete | `Setup.bat`; `Lease116.exe` launcher (no console window, tray icon to stop); `Start.bat` as console alternative |
| Phase 2 | Not in v1 | Network / PostgreSQL deployment, direct ERP posting, transition (Appendix C) calculators, ROU revaluation model |

## 2. Automated tests

| Suite | Tests | What it proves |
|---|---|---|
| `test_engine_25_cases.py` | 25 | The 25 scenarios in the specification (§35), each asserting liability, ROU, schedules, journals (Dr = Cr) and row reconciliation |
| `test_engine_invariants.py` | 16 (21 runs) | Invariants under every policy combination: liability = PV of remaining payments at every month-end; rows reconcile; validation errors; cut-over; lessor benchmarks; disclosure aggregation; tax bridge; Indian number format |
| `test_docintel.py` | 10 | Indian amount-in-words parsing, OCR text repair, hallucination rejection (AI quote not in document ⇒ rejected), evidence-sentence boundaries (figures, clause numbers, abbreviations), premises description, all four sample agreements incl. the tilted, noisy scanned deed (deskew, OCR, seal detection) |
| `test_lessor.py` | 21 | Lessor engine against independent worked examples: implicit rate and net investment (FV + IDC), constant-rate finance income by year, current / non-current split, para 94 reconciliation at a month-end and a mid-month date; operating lease with rent-free, escalation, deposit (Ind AS 109) and IDC; variable and CAM components; equal-monthly vs daily income; modifications (87, 80(a), 80(b)); terminations (operating and finance); residual reduction (77); ECL; manufacturer / dealer with a market rate (71–74); classification benchmarks, override and blocking rules; finance sublease (B58); portfolio note (paras 90–97) |
| `test_api.py` | 24 | Authentication; maker-checker and segregation of duties; period lock blocks changes; event preview and approval flow; journal balance and exports; reports; imports with SoD; AI reader in offline mode; cloud-AI permission gate; audit trail; **ledger integrity** (below); stale-calculation detection; launcher shutdown accepted only with the per-launch token; deleting agreement reads (administrator only, lease evidence kept, shared files kept, audited); a refused upload leaves no copy on disk; lessor: register filter, ledger integrity for the lessor demo leases, manual lessor lease → workpaper / memo / position, blocking messages, agreement reader and CSV import as lessor, event preview, dashboard, note and reports; a run from the previous lessor engine is flagged and excluded without breaking any screen |

### 2.1 Benchmarks against IFRS 16 Illustrative Examples

Figures in the examples are rounded to whole currency units; the engine is asserted to within ±0.5 (±1 where the example itself rounds a difference).

| Example | Scenario | Published figure | Engine | Result |
|---|---|---|---|---|
| IE13 | Initial liability / ROU (10 yrs, 50,000 p.a. in advance, 5%, IDC 20,000, incentive 5,000) | 355,391 / 420,391 | 355,391 / 420,391 | Match |
| IE13 | Reassessment of extension option at end of year 6: liability before → after | 186,162 → 378,174 | 186,162 → 378,174 | Match |
| IE13 | ROU before → after; depreciation year 7 | 168,156 → 360,168; 40,019 | same | Match |
| IE16 | Term extended by 4 years (not a separate lease): liability | 346,511 → 597,130; ROU +250,619 | same | Match |
| IE15 pattern | Additional space at stand-alone price | Separate lease, original unchanged | Separate lease flagged, balances unchanged | Match |
| IE17 | 50% space surrendered; revised rate 5% | ROU −92,001; liability −105,309; gain 13,308; remeasurement +24,575 | same | Match |
| IE18 | Consideration change only: liability | 421,236 → 389,519; ROU −31,717 | same (±1 rounding) | Match |
| IE19 | Scope increase and term decrease combined | ROU −147,202; liability −153,935; gain 6,733; remeasurement +126,346 | same | Match |
| IE24 | Sale and leaseback: PV of leaseback payments; ROU; gain on rights transferred | 1,459,200; 699,555; 240,355 | same | Match |

Independent cross-checks: every initial liability is re-computed in the tests with an independent XNPV / annuity formula; the Excel workpaper re-computes the PV with live formulas (LibreOffice recalculation of three demo workpapers: 1,260 formulas, **0 errors, difference to engine = 0.00**).

### 2.2 Ledger integrity (added in this release)

For every capitalised lease in the demonstration portfolio and **every period end**, the posted journals rolled up by accounting role must equal the schedule balances:

| Account role | Must equal | Result |
|---|---|---|
| Lease liability | − closing liability | Pass (all periods, all leases, incl. USD and sale-and-leaseback) |
| ROU asset — cost | Gross carrying amount | Pass |
| Accumulated depreciation | Accumulated depreciation | Pass |
| Accumulated impairment | Accumulated impairment | Pass |

This test found and fixed one defect before release: the sale-and-leaseback commencement journal credited a separate "SLB financial liability" account while subsequent interest and payments ran through "Lease liability" (see §4).

### 2.5 Lessor module — independent recomputation (v1.1)

An independent reviewer recomputed five worked examples from first principles (own scripts, without access to the application's code; ACT/365 fixed, effective annual rates) and the figures were compared with Lease116's output:

| Scenario | Figure | Independent | Lease116 | Result |
|---|---|---|---|---|
| Finance lease: 20 quarterly receipts of 1,50,000 in arrears; FV 25,00,000; carrying amount 21,00,000; UGR 2,00,000; IDC 25,000 | Rate implicit in the lease | 9.271698% | 9.271698% | Match |
| | Net investment at commencement (FV + IDC) | 25,25,000.00 | 25,25,000.00 | Match |
| | Gain on derecognition (not selling profit — lessor is not a dealer) | 4,00,000.00 | 4,00,000.00 | Match |
| | Finance income FY 2025-26 / 26-27 / 27-28 / 28-29 / 29-30 | 2,13,539.50 / 1,77,708.05 / 1,38,895.72 / 95,802.21 / 49,054.52 | same | Match |
| | Net investment at 31-Mar-2026; current / non-current | 21,38,539.50; 4,22,291.95 / 17,16,247.55 | same | Match |
| | Para 94 at 31-Mar-2026: undiscounted 24,00,000 − unearned 4,01,707.55 + discounted UGR 1,40,247.05 | 21,38,539.50 | 21,38,539.50 (difference 0.00) | Match |
| Operating lease: 60 months, 2,00,000 p.m. + 5% p.a., 2 months rent-free, deposit 12,00,000 at 9%, IDC 2,00,000, CAM 40,000 | Deposit fair value; lease-payment element | 7,79,733.54; 4,20,266.46 | same | Match |
| | Straight-line income per month | 2,21,363.02 | 2,21,363.02 | Match |
| | Accrued / (deferred) income 31-Dec-2025; 31-Dec-2026 | 2,36,089.84; 3,72,446.13 | 2,36,089.83; 3,72,446.12 | Match (0.01 rounding) |
| | Deposit carrying amount 31-Dec-2025; 31-Dec-2026 | 8,49,909.56; 9,26,401.42 | same | Match |
| | IDC per month; CAM revenue per month; total income | 3,333.33; 40,000.00; 1,32,81,781.46 | same | Match |
| | Para 97 maturity at 31-Mar-2026 (years 1–4) | 25,51,500 / 26,79,075 / 28,13,028.75 / 21,87,911.25 | same | Match |
| Para 87 modification from 01-Jul-2026 (2,30,000 p.m. + 5%) | Accrued income carried forward; monthly income thereafter | 3,04,267.98; 2,37,956.06 | same | Match |
| Termination on 01-Jan-2027 with penalty 5,00,000 | Accrued released; gain; IDC written off; deposit catch-up | 3,72,446.13; 1,27,553.87; 1,20,000.00; 2,73,598.58 | 3,72,446.12; 1,27,553.88; 1,20,000.00; 2,73,598.58 | Match (0.01 rounding) |
| Manufacturer / dealer (market rate 12%) | Revenue; cost of sale; selling profit; IDC | 9,01,045.45; 7,00,000.00; 2,01,045.45; expensed | same | Match |

The reviewer's treatment review agreed with every accounting treatment; three were rated as policy judgments and are now documented in the product: (1) a non-dealer lessor's fair-value / carrying-amount difference is presented as a gain on derecognition (Ind AS 16.68) outside the para 90(a)(i) selling profit; (2) on a para 80(a) reclassification the asset is recognised net of any loss allowance (judgment flag); (3) the current portion of the net investment is the principal recovered within 12 months (basis stated in the note). The reviewer also noted that an early termination agreed in advance is a modification shortening the term — the event form and a judgment flag now say so.

Ledger integrity for lessor leases: at every period end the posted journals, rolled up by role, equal the schedule balances (net investment, loss allowance, accrued / deferred lease income, IDC, deposit received) — asserted for both lessor demo leases and for a lessor lease created through the API.

### 2.3 Verified package environments

The suite was run in two independent environments (Linux build servers; the Windows install is verified on the target PC — §2.4):

| Package | Environment A (development) | Environment B (clean install from `requirements*.txt`) |
|---|---|---|
| Python | 3.11 | 3.11.15 |
| FastAPI / SQLAlchemy / pydantic | 0.141 / 2.1.0 / 2.13 | 0.141.1 / 2.1.1 / 2.13.5 |
| OpenCV | 4.13 | 5.0.0 |
| PyMuPDF / pypdf / pypdfium2 | 1.28.2 / 3.17 / 5.7 | 1.28.2 / 6.19 / 5.13 |
| onnxruntime / RapidOCR | 1.25 / 1.4.4 | 1.30 / 1.4.4 |
| reportlab / openpyxl / python-docx | 4.4 / 3.1.5 / 1.2 | 5.0.1 / 3.1.5 / 1.2 |
| Result | 101 passed | 101 passed |

Environment B surfaced an OpenCV 5 change in the line-detection output shape used for deskewing; the code now handles both shapes and falls back to the unprocessed image if any image clean-up step fails.

### 2.4 Target-PC verification (Windows 11 on ARM64)

| Check | Result |
|---|---|
| Setup self-test (imports and engines) | `engine 1.0.0 \| OCR: rapidocr \| vision: OpenCV \| PDF: PyMuPDF` |
| Agreement reader, run on the PC through the application's own upload service (rules mode, fully offline): a rendered one-page lease tilted by 1.5° | OCR by RapidOCR (PP-OCRv4, ONNX Runtime under x64 emulation); deskewed by −1.51°; no essential field missing; 5.8 s including model loading |
| Values proposed vs. text of the test page | Agreement date 10-Mar-2025; commencement 01-Apr-2025; term 36 months; rent ₹1,50,000 monthly, in advance, due by the 5th; interest-free deposit ₹9,00,000 — all agree |
| Local AI detected (not enabled by default) | Ollama at `localhost:11434` with `qwen2.5:7b` — can be selected under *Settings → AI engine* |

## 3. User-interface verification

| Check | Result |
|---|---|
| All 18 screens and 12 lease tabs open without script errors (Administrator and Auditor roles) | Pass |
| Agreement reader — text PDF: 44 fields proposed with source quotes and page highlights; judgments answered; draft lease created | Pass — the created lease reproduced the demonstration lease DEMO-001 to the paisa (initial liability ₹2,30,73,810.00) |
| Agreement reader — tilted scanned deed: deskew −1.5°, OCR, seal detected, highlight positioned on the source paragraph | Pass (≈30 s on the test machine) |
| Calculate → submit (preparer) → review (reviewer) → approve (approver) | Pass; segregation of duties enforced |
| Modification preview and recording (25% area surrendered, revised rate 9.60%) | Pass — gain ₹1,50,098.72 shown before saving; recorded event produced a new run |
| Manual lease wizard (6 steps) → create → calculate | Pass |
| "How was this calculated?" drawer: interest sub-intervals, depreciation segments, arithmetic checks = 0.00 | Pass |
| Dark theme, ₹ lakh display, Indian digit grouping | Pass |

## 4. Defects found during QA and fixed

| # | Defect | Fix |
|---|---|---|
| 1 | Sale-and-leaseback: leaseback liability booked to a different ledger account from the subsequent interest / payment postings (ledger did not tie to the schedule) | Commencement journal now credits the lease-liability account; additional financing (if any) raised as a judgment flag for Ind AS 109 presentation |
| 2 | "Inputs changed — recalculate" warning shown after workflow actions that do not change inputs | Separate `inputs_changed_at` timestamp; automated test added |
| 3 | Setting "Payments credited to Bank / Lessor payable" was not applied to journals | Wired into journal generation |
| 4 | Reader page: source highlight misplaced on long pages | Highlight layer now scrolls with the page image and auto-scrolls to the evidence |
| 5 | Lease-detail tabs did not change when navigated by link | Route query watched |
| 6 | OpenCV 5.0: deskew failed on scanned PDFs (array shape change) | Shape-agnostic handling; image clean-up failures can no longer stop OCR |
| 7 | Reader evidence: a sentence ending in a figure ("… commencing from 1st April, 2025.") was not treated as ended, so the quoted clause and page highlight ran on into the next clauses | Sentence rule now closes on figures while still ignoring clause numbers ("1.", "2.3") and abbreviations ("Rs.", "No."); premises description stops before the term clause. Extracted values unchanged on all samples; over-long quotes (≥ 300 characters) reduced from 20 to 3 (all three are genuinely long sentences); 2 tests added |
| 8 | An upload refused before reading (e.g. cloud AI not permitted) left the uploaded agreement on disk although no record pointed to it | The stored copy is now removed when the upload is refused (unless an identical earlier upload uses it); test added |
| 9 | Lessor (v1.1 review): operating leases could not be calculated without a residual value or implicit rate, even when classified as operating; lessor events ran through the lessee engine ("discount rate missing"); deposits received ignored; workpaper and memo used the lessee templates; lessor leases missing from the dashboard and most reports; note limited to income and one maturity table | Lessor engine 2.0 and services rebuilt (classification evidence and blocking rules, deposits under Ind AS 109, lessor events, lessor workpaper / memo / KPIs / reports / para 89–97 note); Lessee / Lessor choice on every entry route |
| 10 | Lessor engine: an annual payment in arrears dated the day after the term end was excluded, distorting the implicit rate | Within-term rule uses the period the payment covers |
| 11 | Lessor engine: payment dates added by a mid-month event could be skipped in that month | Event points recomputed after every step |
| 12 | Sublease: sublease income posted to the head-lessor net-investment account | Separate net-investment role for subleases; day-1 receivable handled |
| 13 | Lessor schedules continued with empty months after a termination / shortening | Trailing empty months after the revised end are dropped |
| 14 | Non-dealer lessor's fair value / carrying-amount difference presented as selling profit | Presented as gain on derecognition (Ind AS 16.68) outside para 90(a)(i); own GL role 43090 |
| 15 | Upgraded databases: a lessor run produced by the previous engine lacks the v1.1 structure and would break the lessor note | Such runs are excluded from the lessor note, dashboard and reports, listed in the exception report, shown with a 'recalculate' banner; lessor exports explain the step instead of failing |

## 5. Known limitations and items requiring your confirmation

> **Please note — items not independently verified in this build environment.** (1) The ICAI-hosted Ind AS 116 PDF could not be downloaded here; paragraph wording was checked against the IFRS 16 text, which Ind AS 116 mirrors. (2) IFRS 16 Illustrative Example figures in §2.1 were taken from the published examples as recalled and are matched by the engine; confirm against your licensed copy before citing them in an audit file. (3) The 25.168% default tax rate is a placeholder for companies under section 115BAA — confirm per client.

| Area | Limitation | Mitigation |
|---|---|---|
| OCR on Windows-on-ARM with native ARM64 Python | OCR packages have no ARM64 wheels | Setup installs x64 Python 3.12 (runs under Windows' built-in emulation) where needed |
| Handwritten or very poor scans | OCR accuracy falls | Reader flags low quality; every value is confirmed by the user |
| Multi-user network use | v1 is a single-PC application | Phase 2 (PostgreSQL) |
| Narrative disclosures (para 59) | Not generated | Prompts provided; management input required by design |
| Lessor | Depreciation and impairment of assets let out under operating leases stay in the fixed-asset register (Ind AS 16 / 40 / 36); lessor foreign-currency leases are not modelled; a substantial finance-lease modification (derecognition under Ind AS 109) is flagged, not calculated | Judgment flags raised on the lease |
| Sublease, sale-and-leaseback | Core scenarios covered; complex variable-payment SLBs (para 102A) need judgment | Flags raised |

## 6. How to re-run the tests

```
%LOCALAPPDATA%\Lease116\venv\Scripts\python.exe -m pip install -r requirements-dev.txt
%LOCALAPPDATA%\Lease116\venv\Scripts\python.exe -m pytest -q
```
Run from the application folder. Expected: 101 passed.
