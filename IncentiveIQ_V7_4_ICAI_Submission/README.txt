IncentiveIQ India V6.5
Extract into a new folder. Double-click START.bat or run python -m pip install -r requirements.txt then python -m streamlit run app.py. Python 3.10+ required for truststore.
Select state, fetch official HTTPS sources or upload browser-downloaded PDFs. Never bypass browser certificate warnings. Windows trust store may resolve certificate errors but not all server issues. Uploaded provenance is unverified. Text PDFs only, first 250 pages, 20 MB limit. Local cache is stored in policy_cache; clear per state in UI. Directory covers 36 jurisdictions via search; only UP and historical Maharashtra have prefilled policy URLs. Other policy links must be found manually; no automatic fallback discovery. Compare candidate excerpts, not legal entitlements. Optional Ollama retained; fast mode does not need it. Calculator uses illustrative inputs. Live websites and Windows performance require user testing.

V6.5: explicit evidence rendering (no Streamlit magic conditional expression), page-isolated retrieval, ranked excerpts, conservative MSME SGST clause extraction. Unsupported or ambiguous wording remains evidence-only. No claim of current eligibility. For existing cached documents, copy the policy_cache folder from V6.5 into this folder or fetch again. PDF page numbers are physical file pages. Clause numbers are shown only when present in the excerpt. No new dependencies.

V6.5 update: category proximity ranking, overlapping evidence suppression, English preference, explicit SGST category/rate matching and layout-aware PDF text extraction (not full table reconstruction). Fetch PDFs again to rebuild old cached text. No automatic entitlement calculation; ambiguous clauses remain evidence-only. Run python TESTS.py for synthetic regression tests. Actual Maharashtra PDF and Windows UI not tested in this build.

V6.5: Use related-document search links to locate policy, PSI, resolutions, amendments, guidelines and FAQs. Paste multiple official URLs or upload PDFs. Each document is ranked separately, and the conservative answer extractor checks candidates across documents. Uploaded files remain unverified. No automatic legal reconciliation or automatic discovery; check effective dates and eligibility.

V6.5: Expanded MSME SGST extraction; supports spaced percentages, expanded tax names and hundred percent. Tested with reconstructed screenshot clause, not live PDF. Conflicting explicit rates remain evidence-only.

V6.7: Combined ceiling extraction supports explicit paired rates, basis, duration and category mapping in prose. Sector-specific queries filter extracted rows. OCR values remain provisional. Arbitrary OCR table reconstruction and automatic effective-date determination are not supported; inspect original PDF. Existing policy_cache folder can be copied from V6.6 while both apps are stopped.

V6.8: Multi-sector paired ceiling comparison separates explicitly named industry categories. Specify Large Industrial Undertakings to restrict comparison; otherwise all supported categories are labeled separately. Missing requested sectors or conflicting rates cause evidence-only fallback. Compare states supports the same paired-ceiling pattern, otherwise excerpts. Not a universal table parser. Synthetic regression tests only; live Gujarat and Windows UI require testing. Copy policy_cache from V6.7 while both apps are stopped to avoid repeating OCR.

V6.9: Compare states now offers seven incentive topics, explicit rate candidates, scope, basis, source, page and evidence expanders, CSV and Excel exports. Missing rates are not inferred. Policy year is only a URL hint; ceilings and periods remain blank unless established by the paired ceiling parser. Multiple candidate rows are not reconciled entitlements. Copy policy_cache from V6.8 to reuse documents. Run START.bat; openpyxl is installed automatically. Synthetic tests: python TESTS.py. Live UI and real document comparison require user retest.

VERSION 7.0 UPDATE
Keep V6.9 as backup. Copy policy_cache into this folder before running START.bat.
Business case: IRR (conventional cash flows), ROI, discounted payback, annual cash flows and delay/rate sensitivity. Delay shifts receipts and truncates receipts outside the project horizon. All assumptions are illustrative.
Comparison: repeated missing-rate rows consolidated; private industrial park context flagged; explicit duration/cap patterns supported, not full table reconstruction. Unclear rates remain candidates only. Maharashtra 2019 is historical. No automatic current-policy verification.
Excel: Executive Summary, Detailed Comparison and Source Evidence worksheets. Verify all rates, eligibility and OCR against originals. Synthetic tests do not establish live accuracy.

V7.1: targeted UP base capital subsidy table parser for the observed flattened header and complete four-cell regional rows. Other states retain V7.0 extractors; no universal table parsing claimed. Local AI exact-quote prompt and validation updated; deterministic table answers bypass Ollama. Existing cache format unchanged. Copy policy_cache from V7.0. Synthetic tests: python TESTS.py. Actual cached policy and Windows/Ollama testing pending. If table format differs, evidence fallback remains available.

V7.2: flexible UP table parser and failure diagnostics. Existing cache format unchanged. Live cached policy and Windows/Ollama not tested.

V7.3: Local AI selects evidence by index; original text is displayed, not unverified paraphrases. Connection check, configurable timeout, elapsed time and raw diagnostic output added. AI selection is not proof of relevance.

V7.4: Fixed SGST regex alternation in comparison duration and ceiling extraction; missing values remain blank.

V7.4: scoped stamp duty clause extraction in Ask AI; OCR and historical policy caveats retained.
