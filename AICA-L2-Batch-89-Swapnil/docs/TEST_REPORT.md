# Test report

## Final summary (25-09-2026)
**188 automated tests passed, 0 failed** (Python 3.14.7, Windows 11). Coverage: engine 99 %, overall 92 %.
The same 188 tests also pass inside the **clean upload copy** after a fresh install (Phase 5, below).

| # | Golden test (brief §13, as corrected in LEGAL_NOTES) | Result |
|---|---|---|
| 1 | Alpha first year (BM/auditor 19-02-2026, share certificates **20-03-2026**, INC-20A 19-07-2026, DPT-3 30-06-2026, AGM deadline 31-12-2027) | PASS |
| 2 | Alpha provisional AOC-4 30-01-2028 / MGT-7A 29-02-2028 → AGM 15-09-2027 moves them to 15-10 / 14-11 / ADT-1 30-09-2027, history kept | PASS |
| 3 | Alpha directors' triennial KYC **30-06-2029** (MCA illustration); change filing 04-09-2026, ₹500 | PASS |
| 4 | Beta OPC AOC-4 27-09-2026, MGT-7A 29-11-2026, no AGM | PASS |
| 5 | Gamma non-small: MGT-7, MGT-8, AOC-4 XBRL, 26-10 / 25-11 / 11-10-2026, PAS-6 29-11-2026 & 30-05-2027, REGULAR | PASS |
| 6 | Delta small under new limits; non-small under old; FY 2024-25 → AMBIGUOUS → partner decision | PASS |
| 7 | Epsilon DIR-12 09-11-2026, PAS-3 (PP) 16-10-2026, PAS-3 (rights) 31-10-2026, MGT-14 04-11-2026 | PASS |
| 8 | Eta LLP Form 3 15-12-2025; elected Form 11 30-05-2027 / Form 8 30-10-2027; else 30-05-2026 / 30-10-2026 | PASS |
| 9 | MSME-1 only when flagged; 31-10-2026 | PASS |
| 10 | Rollover at 01-04-2027: new FY obligations, no duplicates, statuses kept | PASS |
| 11 | DIR3KYC_ANNUAL for FY 2024-25 (30-09-2025); none for 30-09-2026; triennial from 31-03-2026 | PASS |
| 12 | ADT-1, 109 days late, nominal ₹5 L → ₹4,400 | PASS |
| 13 | AOC-4, 730 days late → ₹73,400; AOC-4 + MGT-7 each 60 days → ₹6,000 + ₹6,000 | PASS |
| 14 | Zeta Form 11, 113 days late → ₹1,650 | PASS |
| 15 | CCFS: 10-09-2026 → 10 % of additional fee (₹7,200); 20-09-2026 → full; LLP → none | PASS |
| 16 | Unverified rule → "Estimate — unverified"; client letter refused (409) naming the rows | PASS |
| 17 | Preparer "Filed" → 403 with plain-English message; audit / staff / delete → 403; self-approval → 403 | PASS |
| 18 | Waiver with a 9-character reason → 422; 20+ by partner → accepted and audited | PASS |
| 19 | Raw SQL UPDATE/DELETE on audit_log refused by trigger; chain verifies; tampered copy → broken link found | PASS |
| 20 | Paid-up > authorised, future incorporation date, 20-character CIN → rejected in plain English | PASS |
| 21 | 5 wrong passwords → locked 15 minutes; Owner unlocks | PASS |
| 22 | Backup while running → integrity ok, triggers intact, restorable | PASS |
| 23 | Same database from any working directory | PASS |
| 24 | Rule edited and published → the next page load shows the new due date (`Cache-Control: no-store`) | PASS |

## Phase 5: hardening and packaging (25-09-2026)
- **Security headers:** checked by `test_security_and_cache_headers`:
  - CSP with a per-request nonce and no `unsafe-inline` (no inline `style=` attributes anywhere in the templates);
  - `X-Frame-Options: DENY`, `nosniff`, `Referrer-Policy: same-origin`;
  - `Cache-Control: no-store` on pages; static files cached with a per-start version string.
- **Start-up robustness:** `run.py` re-launches itself with the project's `.venv` Python (the system Python has no Flask), opens the browser, and reports a busy port clearly instead of crashing.
- **`START_APP.bat`:** creates `.venv`, installs pinned requirements, creates `.env`, migrates, seeds the fictitious demo firm only into an empty database, starts the app, and switches the console to UTF-8.
- **Fresh install following only the README:**
  1. `cli.py package` produced the clean upload copy (97 files; no `.venv`, `instance/`, `.env` or caches).
  2. In that copy, `START_APP.bat` went from nothing to the sign-in page in **71 s**:
     ```
     Created .env with fresh SECRET_KEY and FERNET_KEY (keep it safe; never commit it).
     Database ready: sqlite:///…/fresh/AICA-L2-Batch-89-Swapnil/instance/mca.db
     Seeded 8 fictitious entities, 8 persons, 252 historical filings (as of 25-09-2026).
       MCA Compliance Mapper is running:  http://127.0.0.1:5050
     ```
  3. `pytest` inside the copy, using its own new `.venv`: **188 passed in 74.85 s**.
- **Docker:** `Dockerfile` and `docker-compose.yml` were written but **not run**; Docker is not installed on the development PC.
- **PyInstaller:** the optional single-file build was not produced.

## Phase 1: engine (run 25-09-2026, Python 3.14.7, Windows 11)

Command: `python -m pytest -v --cov=engine --cov-report=term-missing`

**Result:** 102 passed, 0 failed. Engine coverage **99%** (target ≥ 90%).

### Golden tests 1–16

| # | Golden test (brief §13, as corrected) | Test(s) | Result |
|---|---|---|---|
| 1 | Alpha first year: BM/auditor 19-02-2026; share certificates **20-03-2026** (corrected from 21-03); INC-20A 19-07-2026; DPT-3 30-06-2026 before FY1 closes; first AGM deadline 31-12-2027 | `test_g01_alpha_first_year`, `test_g01_first_auditor_adt1_setting` | PASS |
| 2 | Alpha no AGM: AOC-4 30-01-2028, MGT-7A 29-02-2028, both Provisional; AGM 15-09-2027 → 15-10-2027 / 14-11-2027 / ADT-1 30-09-2027; same stable key | `test_g02_alpha_provisional_then_actual_agm` | PASS (history kept by the service layer: Phase 2) |
| 3 | Alpha directors: triennial KYC **30-06-2029** (corrected, MCA illustration, partner Q1); legacy DIN 30-06-2028; change 05-08-2026 → 04-09-2026, fee ₹500 | `test_g03_alpha_directors_kyc`, `test_g03_legacy_din_and_override`, `test_kyc_fees` | PASS |
| 4 | Beta OPC: AOC-4 27-09-2026; MGT-7A 29-11-2026; no AGM | `test_g04_beta_opc` | PASS |
| 5 | Gamma: MGT-7, MGT-8, AOC-4 XBRL; 26-10 / 25-11 / 11-10-2026; PAS-6 29-11-2026 and 30-05-2027; REGULAR | `test_g05_gamma_non_small`, `test_gamma_panel` | PASS |
| 6 | Delta: small under new limits → MGT-7A (+ AOC-4 XBRL, MGT-8); non-small under old; FY 2024-25 → AMBIGUOUS, partner decision | `test_g06_*`, `test_delta_small_new_not_small_old`, `test_delta_fy2024_25_ambiguous_until_decided` | PASS |
| 7 | Epsilon: DIR-12 09-11-2026; PAS-3 (PP) 16-10-2026; PAS-3 (rights) 31-10-2026; MGT-14 04-11-2026 | `test_g07_epsilon_events` | PASS |
| 8 | Eta LLP: Form 3 15-12-2025; elected Form 11 30-05-2027 / Form 8 30-10-2027; otherwise 30-05-2026 / 30-10-2026 | `test_g08_eta_llp_election` | PASS |
| 9 | MSME-1: flagged Apr–Sep 2026 → 31-10-2026; no flag → none | `test_g09_msme1` | PASS |
| 10 | Rollover at as_of 01-04-2027: every entity has FY 2026-27 obligations; re-run gives identical keys, no duplicates | `test_g10_rollover_and_idempotence` | PASS (status preservation on upsert: Phase 2) |
| 11 | Law change: DIR3KYC_ANNUAL for FY 2024-25 (30-09-2025); none for 30-09-2026; triennial from 31-03-2026 | `test_g11_law_change_annual_to_triennial`, `test_law_change_is_a_yaml_edit` | PASS |
| 12 | ADT-1 109 days late, nominal ₹5 L → ₹400 + ₹4,000 = ₹4,400 | `test_g12_adt1_109_days` | PASS |
| 13 | AOC-4 730 days late → ₹73,400; AOC-4 and MGT-7 each 60 days → ₹6,000 + ₹6,000 | `test_g13_*` | PASS |
| 14 | Zeta Form 11, 113 days late → ₹150 + ₹1,500 = ₹1,650 | `test_g14_zeta_form11` | PASS |
| 15 | CCFS: Theta AOC-4 filed 10-09-2026 → 10% of additional fee (₹7,200 total); 20-09-2026 → full (₹69,400); LLP → no relief | `test_g15_ccfs_overlay` | PASS |
| 16 | Unverified rule → `verified=False`, "Estimate — unverified"; export refused naming the rows | `test_g16_unverified`, `test_verification_overlay` | PASS (UI export block: Phase 4) |

Golden tests 17–24 (security, audit, packaging) belong to Phases 2 and 5.

### Raw output
```text
============================= test session starts =============================
platform win32 -- Python 3.14.7, pytest-9.1.1, pluggy-1.6.0 -- .venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\CA Swapnil\Desktop\AICA-L2-Batch-89-Swapnil
plugins: cov-7.1.0
collecting ... collected 102 items

tests/test_classification.py::test_delta_small_new_not_small_old PASSED  [  0%]
tests/test_classification.py::test_delta_fy2024_25_ambiguous_until_decided PASSED [  1%]
tests/test_classification.py::test_small_exclusions[is_holding-holding] PASSED [  2%]
tests/test_classification.py::test_small_exclusions[is_subsidiary-subsidiary] PASSED [  3%]
tests/test_classification.py::test_small_exclusions[special_act-special Act] PASSED [  4%]
tests/test_classification.py::test_public_never_small PASSED             [  5%]
tests/test_classification.py::test_gamma_panel PASSED                    [  6%]
tests/test_classification.py::test_board_regimes PASSED                  [  7%]
tests/test_classification.py::test_aoc4_variants PASSED                  [  8%]
tests/test_classification.py::test_mgt8_delta PASSED                     [  9%]
tests/test_classification.py::test_csr PASSED                            [ 10%]
tests/test_classification.py::test_secretarial_audit_uses_fy_end_borrowings PASSED [ 11%]
tests/test_classification.py::test_internal_audit PASSED                 [ 12%]
tests/test_classification.py::test_rule_9b PASSED                        [ 13%]
tests/test_classification.py::test_llp_classifications PASSED            [ 14%]
tests/test_classification.py::test_fact_fallbacks_mark_stale PASSED      [ 15%]
tests/test_classification.py::test_expressions PASSED                    [ 16%]
tests/test_classification.py::test_inr_short PASSED                      [ 17%]
tests/test_dates.py::TestDueDate::test_days_excludes_anchor_day PASSED   [ 18%]
tests/test_dates.py::TestDueDate::test_months_keeps_day PASSED           [ 19%]
tests/test_dates.py::TestDueDate::test_months_clip_to_month_end PASSED   [ 20%]
tests/test_dates.py::TestDueDate::test_months_then_days PASSED           [ 21%]
tests/test_dates.py::TestDueDate::test_negative_and_empty PASSED         [ 22%]
tests/test_dates.py::TestDueDate::test_rejects_unknown_key PASSED        [ 23%]
tests/test_dates.py::TestDueDate::test_leap_year_60_days PASSED          [ 24%]
tests/test_dates.py::test_holiday_hint PASSED                            [ 25%]
tests/test_dates.py::TestFinancialYear::test_first_fy_invariant_every_day_of_two_years PASSED [ 26%]
tests/test_dates.py::TestFinancialYear::test_examples PASSED             [ 27%]
tests/test_dates.py::TestFinancialYear::test_keys PASSED                 [ 28%]
tests/test_dates.py::TestFinancialYear::test_series PASSED               [ 29%]
tests/test_dates.py::TestFinancialYear::test_llp_election PASSED         [ 30%]
tests/test_dates.py::test_half_years PASSED                              [ 31%]
tests/test_dates.py::test_march31s PASSED                                [ 32%]
tests/test_dates.py::TestAGM::test_first_agm_nine_months PASSED          [ 33%]
tests/test_dates.py::TestAGM::test_later_agm_earlier_of_six_and_fifteen PASSED [ 34%]
tests/test_dates.py::TestKYC::test_new_din_fy_2025_26 PASSED             [ 35%]
tests/test_dates.py::TestKYC::test_legacy_din PASSED                     [ 36%]
tests/test_dates.py::TestKYC::test_din_fy_2026_27 PASSED                 [ 37%]
tests/test_dates.py::TestKYC::test_override PASSED                       [ 38%]
tests/test_dates.py::TestKYC::test_cycle PASSED                          [ 39%]
tests/test_fees.py::test_g12_adt1_109_days PASSED                        [ 40%]
tests/test_fees.py::test_g13_aoc4_730_days PASSED                        [ 41%]
tests/test_fees.py::test_g13_per_form_60_days PASSED                     [ 42%]
tests/test_fees.py::test_g14_zeta_form11 PASSED                          [ 43%]
tests/test_fees.py::test_g15_ccfs_overlay PASSED                         [ 44%]
tests/test_fees.py::test_g16_unverified PASSED                           [ 45%]
tests/test_fees.py::test_verification_overlay PASSED                     [ 46%]
tests/test_fees.py::test_s139_first_slab_and_on_time PASSED              [ 47%]
tests/test_fees.py::test_general_multiplier_slabs PASSED                 [ 48%]
tests/test_fees.py::test_s139_before_2022_falls_back PASSED              [ 49%]
tests/test_fees.py::test_higher_additional_fee_on_repeat PASSED          [ 50%]
tests/test_fees.py::test_charge PASSED                                   [ 50%]
tests/test_fees.py::test_kyc_fees PASSED                                 [ 51%]
tests/test_fees.py::test_llp_beyond_360 PASSED                           [ 52%]
tests/test_fees.py::test_no_fee_and_extension_overlay PASSED             [ 53%]
tests/test_fees.py::test_normal_fee_bands PASSED                         [ 54%]
tests/test_fees.py::test_fmt_inr PASSED                                  [ 55%]
tests/test_fees.py::test_default_rulepack_loaded_when_none PASSED        [ 56%]
tests/test_fees.py::test_validate_fee_tables_errors PASSED               [ 57%]
tests/test_generator.py::test_g01_alpha_first_year PASSED                [ 58%]
tests/test_generator.py::test_g01_first_auditor_adt1_setting PASSED      [ 59%]
tests/test_generator.py::test_g02_alpha_provisional_then_actual_agm PASSED [ 60%]
tests/test_generator.py::test_g03_alpha_directors_kyc PASSED             [ 61%]
tests/test_generator.py::test_g03_legacy_din_and_override PASSED         [ 62%]
tests/test_generator.py::test_director_on_three_boards_gets_one_kyc PASSED [ 63%]
tests/test_generator.py::test_g04_beta_opc PASSED                        [ 64%]
tests/test_generator.py::test_g05_gamma_non_small PASSED                 [ 65%]
tests/test_generator.py::test_gamma_rule_9b_and_extension PASSED         [ 66%]
tests/test_generator.py::test_gamma_pre_engagement PASSED                [ 67%]
tests/test_generator.py::test_g06_delta_small_under_new_limits PASSED    [ 68%]
tests/test_generator.py::test_g06_delta_fy2024_25_ambiguous PASSED       [ 69%]
tests/test_generator.py::test_g07_epsilon_events PASSED                  [ 70%]
tests/test_generator.py::test_md_appointment_mr1_only_for_public PASSED  [ 71%]
tests/test_generator.py::test_g08_eta_llp_election PASSED                [ 72%]
tests/test_generator.py::test_llp_audit_only_when_both_limits_crossed PASSED [ 73%]
tests/test_generator.py::test_g09_msme1 PASSED                           [ 74%]
tests/test_generator.py::test_g10_rollover_and_idempotence PASSED        [ 75%]
tests/test_generator.py::test_facts_stale_for_future_fy PASSED           [ 76%]
tests/test_generator.py::test_agm_not_held_runs_from_deadline PASSED     [ 77%]
tests/test_generator.py::test_g11_law_change_annual_to_triennial PASSED  [ 78%]
tests/test_generator.py::test_detail_change_before_triennial_rule_ignored PASSED [ 79%]
tests/test_generator.py::test_spec_carries_traceability PASSED           [ 80%]
tests/test_generator.py::test_board_approval_anchor_public PASSED        [ 81%]
tests/test_generator.py::test_dormant_and_cost_audit_and_csr PASSED      [ 82%]
tests/test_generator.py::test_other_company_events PASSED                [ 83%]
tests/test_generator.py::test_llp_events PASSED                          [ 84%]
tests/test_rulepack.py::test_real_pack_loads PASSED                      [ 85%]
tests/test_rulepack.py::test_unknown_predicate_named PASSED              [ 86%]
tests/test_rulepack.py::test_bad_field_names_row PASSED                  [ 87%]
tests/test_rulepack.py::test_rule_validations[<lambda>-unknown entity type] PASSED [ 88%]
tests/test_rulepack.py::test_rule_validations[<lambda>-effective_to is before] PASSED [ 89%]
tests/test_rulepack.py::test_rule_validations[<lambda>-needs 'fixed] PASSED [ 90%]
tests/test_rulepack.py::test_rule_validations[<lambda>-needs event_types] PASSED [ 91%]
tests/test_rulepack.py::test_rule_validations[<lambda>-unknown variant] PASSED [ 92%]
tests/test_rulepack.py::test_rule_validations[<lambda>-Extra inputs] PASSED [ 93%]
tests/test_rulepack.py::test_duplicate_codes PASSED                      [ 94%]
tests/test_rulepack.py::test_missing_files_and_yaml_errors PASSED        [ 95%]
tests/test_rulepack.py::test_fee_and_scheme_validation PASSED            [ 96%]
tests/test_rulepack.py::test_fee_file_validation PASSED                  [ 97%]
tests/test_rulepack.py::test_scheme_file_validation PASSED               [ 98%]
tests/test_rulepack.py::test_lookup_errors PASSED                        [ 99%]
tests/test_rulepack.py::test_law_change_is_a_yaml_edit PASSED            [100%]

=============================== tests coverage ================================
_______________ coverage: platform win32, python 3.14.7-final-0 _______________

Name                   Stmts   Miss  Cover   Missing
----------------------------------------------------
engine\__init__.py         5      0   100%
engine\dates.py          106      0   100%
engine\fees.py           225      0   100%
engine\generator.py      157      2    99%   75, 173
engine\predicates.py     305      2    99%   99, 387
engine\rulepack.py       230      0   100%
engine\types.py          107      2    98%   48, 52
----------------------------------------------------
TOTAL                   1135      6    99%
============================= 102 passed in 3.32s =============================
```


## Phase 2: persistence, auth, roles, audit (run 25-09-2026)

Command: `python -m pytest -q --cov=engine --cov=app`

**Result:** 157 passed, 0 failed (102 engine + 55 web). Coverage: engine 99%, app 87%, overall 92%.

| # | Golden test | Test(s) | Result |
|---|---|---|---|
| 17 | Preparer marks Filed → 403 with the plain-English message; preparer on the audit trail / staff management / entity delete → 403, 403, 403; a manager approving an item they marked Ready → 403 (maker–checker); every denial audit-logged | `test_g17_preparer_cannot_mark_filed`, `test_g17_preparer_blocked_from_audit_staff_delete`, `test_g17_maker_checker`, `test_route_role_matrix[*]` | PASS |
| 18 | Waiver with a 9-character reason → 422; 20+ characters by a partner → accepted and audit-logged | `test_g18_waiver_reason_length`, `test_manager_cannot_waive` | PASS |
| 19 | Raw SQL UPDATE/DELETE on audit_log refused by trigger; row count unchanged; chain verifies; a tampered copy reports the first broken link | `test_g19_raw_sql_update_and_delete_refused`, `test_g19_tampered_copy_reports_broken_link` | PASS |
| 20 | Paid-up > authorised, future incorporation date, 20-character CIN → rejected in plain English | `test_g20_validations` | PASS |
| 21 | 5 wrong passwords → locked 15 minutes (right password also refused); owner unlocks | `test_g21_lockout_and_owner_unlock`, `test_lock_expires_after_15_minutes` | PASS |
| 22 | Backup taken while the app has open connections → integrity ok, triggers intact, chain verifies, restorable and bootable | `test_g22_backup_while_running_is_restorable` | PASS |
| 23 | Same database from any working directory; a relative `DATABASE_URL` resolves to the project | `test_g23_same_db_from_any_working_directory` | PASS |

The route × role matrix covers 25 routes × 5 roles. `test_every_protected_route_is_decorated` fails the build if any view is added without `@require`.

### Manual demonstration: raw-SQL attack on the live database (server running)

```text
audit_log rows before: 18
  "UPDATE audit_log SET actor_name = 'Nobody' WHERE id = 1"    -> REFUSED: audit_log is append-only
  'DELETE FROM audit_log WHERE id = 1'                         -> REFUSED: audit_log is append-only
  'DELETE FROM audit_log'                                      -> REFUSED: audit_log is append-only
audit_log rows after:  18
Audit chain intact: 18 rows verified
```

### Design notes recorded at this gate
- **Audit of generated obligations:** when the engine creates obligations, one `OBLIGATIONS_GENERATED` row lists every new key; creating Gamma alone would otherwise write hundreds of rows. Every *change* is audited individually: due-date moves (with before/after, which is the history the brief asks for), status changes, filings, supersessions and denials.
- **Superseded, never deleted:** an obligation that no longer applies keeps its status and gets `superseded_at` and a reason. The rollover test proves a filed DPT-3 survives when its flag is turned off.
- **Visibility:** a viewer or preparer sees only entities where they are the preparer or relationship manager (brief §4, "assigned entities"). A preparer who creates an entity is made its preparer automatically.

### Coverage
```text

Name                        Stmts   Miss  Cover
-----------------------------------------------
app\__init__.py                76      2    97%
app\audit.py                   66      2    97%
app\auth.py                   242     18    93%
app\config.py                  54     11    80%
app\models.py                 312      1    99%
app\permissions.py             40      0   100%
app\routes\__init__.py          0      0   100%
app\routes\admin.py           164     49    70%
app\routes\dashboard.py        27      0   100%
app\routes\entities.py        331    103    69%
app\routes\obligations.py     128      8    94%
app\routes\rules.py            39      2    95%
app\services.py               291     27    91%
engine\__init__.py              5      0   100%
engine\dates.py               106      0   100%
engine\fees.py                234      0   100%
engine\generator.py           157      2    99%
engine\predicates.py          305      2    99%
engine\rulepack.py            230      0   100%
engine\types.py               107      2    98%
-----------------------------------------------
TOTAL                        2914    229    92%
157 passed, 3 warnings in 53.72s
```


## Phase 3: user interface (run 25-09-2026)

**Result:** 174 automated tests passed (17 new Phase 3 screen tests plus one engine test). Coverage: engine 99%, overall 93%.

### Screens delivered (brief §7)
| Screen | Where | Notes |
|---|---|---|
| Login, forced password change, two-factor sign-in | `auth.html` | Navy/gold split hero after the firm's website |
| Firm dashboard | `/` | Health-band tiles; overdue list with fee exposure if filed today; next 30 days; my reviews; partner decisions; DSC expiry |
| My work queue | `/work` | Sort; team/unassigned scopes (manager+); one-click HTMX status buttons that respect maker–checker; bulk assign |
| Entities list | `/entities` | Search; filters by type, relationship manager, ROC and health |
| Entity page | `/entities/<id>` | KPI tiles; compliance timeline by FY with anchor; classification panel with reasons, thresholds and citations; partner decisions; facts summary; period flags; events; directors; notes; documents; audit trail (manager+) |
| Onboarding wizard | `/entities/onboard` | Entity → FY preview (both LLP outcomes) → directors → latest facts → preview → confirm. PAN is kept encrypted in the session |
| Annual facts | `/entities/<id>/facts` | One row per FY; "Drives" column shows the obligations each field affects |
| Record event | `/entities/<id>/events/new` | 30 typed forms (HTMX swaps the fields); "This will create" list from the rule pack; appointments and cessations update the director links |
| Director view | `/directors` | Each DIN, its entities, next KYC, DSC expiry and DIN status; detail-change events; partner KYC override |
| Fee calculator | `/tools/fees` | Every regime and scheme; HTMX result; "Estimate — unverified" label |
| Board-meeting planner | `/tools/board` | Regime from classification; 120-day / 90-day gap checks; next meeting due by |
| Rule pack, users and sessions, settings, audit trail | as before | Restyled; settings expose brand colours (colour pickers) |

### Refinements found while clicking through
1. **Inherited items stay visible.** Unfiled items that were due before the engagement start (e.g. Theta's FY 2023-24 AOC-4 and MGT-7) were hidden as pre-engagement. They now stay on the dashboard and entity page, tagged *Pre-engagement*; only closed pre-engagement items are hidden. KPIs will still exclude them (Phase 4).
2. **Small-company status is judged on the filing date (I5 refined).** An FY is classified under the limits in force when its MGT-7/7A was actually filed, or today if it is unfiled. Old returns filed years ago no longer demand partner decisions; Delta's unfiled FY 2024-25 return still does (golden test 6). Test: `test_small_status_judged_on_filing_date`.
3. **Wizard test expectation corrected.** A company incorporated 10-06-2025 has its first AGM deadline on 31-12-2026, so AOC-4 is due 30-01-2027. The engine was right; the test expectation was wrong.

### Manual click-through log (every role)
Script: render each screen from a **freshly seeded, fictitious-only** database, with a session per role created directly in that throwaway copy (as the test suite does; no password typed). CSRF was disabled on the throwaway copy only; CSRF enforcement has its own test (`test_csrf_enforced`). Screenshots were taken with headless Edge at 1440 px wide.

```text
user | method | path | status | result
anonymous | GET | /login | 200 | OK
partner | GET | / | 200 | OK
partner | GET | /obligations/345?what_if=2026-09-10 | 200 | OK
partner | POST | /rules/AOC4/verify | 302 | OK
partner | GET | / | 200 | OK
partner | GET | /directors/4 | 200 | OK
manager | POST | /entities/3/events | 302 | OK
manager | POST | /entities/3/events | 302 | OK
manager | GET | /entities/3 | 200 | OK
manager | GET | /tools/board?entity_id=3 | 200 | OK
manager | GET | /work?scope=team | 200 | OK
manager | GET | /admin/users | 403 | OK
article1 | POST | /obligations/14/status | 403 | OK
article1 | GET | /admin/audit | 403 | OK
article1 | POST | /entities/1/delete | 403 | OK
article1 | GET | /work | 200 | OK
article1 | POST | /entities/onboard?step=1 | 302 | OK
article1 | POST | /entities/onboard?step=2 | 302 | OK
article1 | POST | /entities/onboard?step=3 | 302 | OK
article1 | POST | /entities/onboard?step=4 | 302 | OK
article1 | GET | /entities/onboard?step=5 | 200 | OK
article1 | GET | /entities/3 | 403 | OK
viewer | GET | /tools/fees?rule=LLP_FORM11&etype=LLP&contribution=800000&small=yes&due=2026-05-30&filed=2026-09-20 | 200 | OK
viewer | GET | /entities/1 | 403 | OK
viewer | POST | /entities/1/events | 403 | OK
owner | GET | /admin/audit | 200 | OK
owner | GET | /rules/AOC4 | 200 | OK
owner | GET | /admin/users | 200 | OK
owner | GET | /admin/settings | 200 | OK
```

### Screenshots (`docs/screenshots/`)
| File | Role | Shows |
|---|---|---|
| 01-login.png | — | Navy/gold sign-in |
| 02-dashboard-partner.png | Partner | Tiles, overdue with CCFS-aware fee exposure, reviews, 2 pending decisions, DSC |
| 03-entity-gamma-manager.png | Manager | Timeline, classification panel (non-small, MGT-8, XBRL, Rule 9B, REGULAR) |
| 04-work-queue-preparer.png | Preparer | One-click steps; no Approve on her own Ready item |
| 05-obligation-fee-ccfs.png | Partner | Theta AOC-4: ₹400 + ₹68,000 − ₹61,200 CCFS = ₹7,200 (golden test 15) |
| 06-onboarding-wizard-preview.png | Preparer | Wizard step 5 preview |
| 07-director-view.png | Partner | Director on three boards; triennial KYC 30-06-2028 |
| 08-fee-calculator.png | Viewer | Zeta Form 11: ₹1,650 (golden test 14) |
| 09-board-planner.png | Manager | 156-day gap breach (s.173(1)); next meeting by 13-10-2026 |
| 10-audit-trail-owner.png | Owner | DENIED rows from the preparer and viewer; hash column |

### Coverage
```text
app\__init__.py                82      1    99%
app\audit.py                   66      2    97%
app\auth.py                   242     17    93%
app\config.py                  54     11    80%
app\models.py                 323      1    99%
app\permissions.py             40      0   100%
app\routes\__init__.py          0      0   100%
app\routes\admin.py           164     49    70%
app\routes\dashboard.py        27      0   100%
app\routes\entities.py        483    107    78%
app\routes\obligations.py     183     10    95%
app\routes\rules.py            39      2    95%
app\routes\tools.py           324     30    91%
app\services.py               304     23    92%
engine\__init__.py              5      0   100%
engine\dates.py               106      0   100%
engine\fees.py                234      0   100%
engine\generator.py           158      2    99%
engine\predicates.py          309      2    99%
engine\rulepack.py            230      0   100%
engine\types.py               107      2    98%
TOTAL                        3480    259    93%
```


## Phase 4: calendar, reports, reminders, letters, rule-pack admin (run 25-09-2026)

**Result:** 188 passed, 3 warnings in 82.70s (0:01:22). Coverage below.

### What was built
| Feature | Where | Notes |
|---|---|---|
| Calendar: month and agenda views | `/calendar` | Filter by entity, staff and form; health-coloured items; Sunday hint (no date shifting) |
| .ics downloads | `/calendar.ics?scope=mine / entity / firm` | Hand-written RFC 5545: CRLF endings, 75-octet folding (never splits a multi-byte ₹), TEXT escaping, all-day VEVENTs with stable UIDs, a 7-day VALARM on open items. Whole-firm feed for view-all roles only; every export audit-logged |
| Compliance register (.xlsx) | `/reports/register.xlsx` | openpyxl; "About" sheet (firm, preparer, date, rule-pack version, INTERNAL); frozen header, filters, DD-MM-YYYY dates, ₹ Indian grouping |
| Overdue & fee exposure (.xlsx) | `/reports/overdue.xlsx` | Normal / additional / relief / total if filed today, slab, scheme, verified basis; the fee values are written to the audit log |
| Reports page | `/reports` | Total fee exposure; entity compliance score (on-time ÷ due, rolling 24 months, pre-engagement excluded); staff on-time % |
| Client reminder letter | `/letters` | Letterhead from settings; items due in the window plus overdue ones, the documents needed per form, fee if filed today; Print / save as PDF; copy-to-clipboard e-mail text. **Blocked (409) while any included rule is unverified**, naming the rows; fees logged |
| Reminders | nightly job + `cli.py nightly` | T-30 / T-7 / T-1 / first overdue day, to the assignee and the relationship manager (else all managers); idempotent; bell count and `/notifications`; optional SMTP digest (SMTP_* env) |
| Scheduler | APScheduler, 01:00 IST | Started by `run.py` together with a start-up recompute; `cli.py nightly --catch-up` for Task Scheduler / cron |
| Rule-pack versions and diff | `/rules/versions` | Publish snapshots every row with its content hash; a published version is never overwritten (bump VERSION); field-level diff between any two versions or "current" |
| In-app rule editing (Owner) | `/rules/edit/<file>` | The whole pack is re-validated in a temp copy before saving; invalid → 422 naming file and code; valid → saved, reloaded, every entity recomputed, audit-logged with the changed codes |
| Regulatory update log | `/rules/updates` | Number, date, URL (http/https only), summary, linked rows (created / closed / amended); shown on each rule page; seeded with the five Phase 0 notifications |

### Gate: exported files opened and checked outside the app
Exports produced from a freshly seeded, fictitious-only database, then checked with tools that are **not** the app's own code:

```text
exported firm.ics: 94,001 bytes
exported register.xlsx: 19,849 bytes
exported overdue.xlsx: 6,843 bytes
icalendar 7.3.0: parsed 167 VEVENTs, 105 VALARMs
  sample: SUMMARY=AOC-4 — Theta Foods Pvt Ltd | DTSTART=2024-10-30 | DESCRIPTION first line='Filing of financial statements'
  144 events have descriptions long enough to need line folding — all unfolded cleanly

== overdue.xlsx opened in Excel 16.0: sheets = About, Overdue & fee exposure
   rows x cols = 10 x 12
   header: Entity / person | Form | Period | Due date | Days late | Normal ₹
   row 3 : Theta Foods Pvt Ltd | AOC-4 | FY2023-24 | 30-10-2024 | 695 | ₹400 | ₹69,500 | ₹0 | ₹69,900
   exported PDF from Excel: 201190 bytes
== register.xlsx opened in Excel 16.0: sheets = About, Compliance register
   rows x cols = 168 x 17
   row 2 : Zeta Advisors LLP | ABC-1234 | Form 3 | ONCE | 01-07-2021 | Filed / closed | Filed | Article Assistant One | D10000288

Indian grouping as rendered by Excel with the exported format:
         400 -> ₹400
       69900 -> ₹69,900
      313600 -> ₹3,13,600
    12345678 -> ₹1,23,45,678
```
**Known limitation:** Excel number formats allow only two conditions, so amounts of ₹100 crore or more display as `₹123,45,67,890`. Fees never approach this.

### Golden test 24 (brought forward from Phase 5)
`test_g24_rule_edit_publish_diff_and_fresh_due_date`:
1. The Owner edits INC-20A from 180 to 150 days in-app.
2. The pack is validated and saved, and every entity recomputed.
3. The next page load shows **19-06-2026** instead of 19-07-2026, with `Cache-Control: no-store` and the new pack version on the page.
4. `DUE_DATE_CHANGED` is audited, the diff lists INC20A, and republishing an existing version with different content is refused.

### Coverage
```text
app\__init__.py                90      1    99%
app\audit.py                   66      2    97%
app\auth.py                   242     17    93%
app\config.py                  54     11    80%
app\exports.py                225     12    95%
app\models.py                 323      1    99%
app\permissions.py             40      0   100%
app\routes\__init__.py          0      0   100%
app\routes\admin.py           164     49    70%
app\routes\dashboard.py        27      0   100%
app\routes\entities.py        483    107    78%
app\routes\obligations.py     183     10    95%
app\routes\reports.py         165      2    99%
app\routes\rules.py           148      7    95%
app\routes\tools.py           324     30    91%
app\services.py               304     23    92%
engine\__init__.py              5      0   100%
engine\dates.py               106      0   100%
engine\fees.py                234      0   100%
engine\generator.py           158      2    99%
engine\predicates.py          309      2    99%
engine\rulepack.py            230      0   100%
engine\types.py               107      2    98%
TOTAL                        3987    278    93%
```
