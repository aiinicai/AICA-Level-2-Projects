# ITR Filing Preparation Assistant with Optimal Regime Selector

**Version 1.0 — AY 2026–27 / FY 2025–26.** A Python desktop application for evidence-led ITR preparation and old/new tax regime comparison. The application does not file an ITR or generate the portal's upload JSON.

Participant: [Name] • Batch: [Batch] • ICAI AICA Level 2 project

## Start on Windows

1. Extract the ZIP completely. Open `ITR_Regime_Assistant`.
2. Double-click `install.bat`. Internet is needed to install dependencies.
3. Double-click `run.bat`.
4. Click **Load example / profile**, select `samples/01_salary_new_zero.json`, and inspect all four tabs.

Uses `python`, not the potentially broken `py` launcher. Installer bootstraps pip using `ensurepip`. If Python is missing, install Python with tkinter and Add Python to PATH enabled. Each project has its own environment; dependencies installed for another project are not shared automatically.

VS Code: open this folder, select **Python: Select Interpreter** from Ctrl+Shift+P, choose `.venv\Scripts\python.exe`, then run `app.py`. Running `run.bat` is simplest.

## What makes this a professional preparation tool?

- Traceable salary, HRA, deductions, taxable-income and slab computations for both regimes.
- Age-sensitive old-regime slabs, new-regime section 87A marginal relief, cess, and statutory rounding.
- Eligibility scope gates; unsupported cases produce a blocked result, not a guessed recommendation.
- Hypothetical 80C/NPS scenarios distinguish additional contributions from resulting tax savings.
- Verified tax credits, indicative payable/refund, filing readiness and a conditional regime preference.
- Reviewer choice and reasons, with checks against stale calculations when facts change.
- Eight-sheet Excel working paper with inputs, slabs, deduction buckets, scenarios and review evidence.
- Optional AI explanation from the exact calculation; anonymous prompt preview and consent before API transmission. Manual copy/paste works without an API key. All drafts require professional review.

## Scope and limitations

Resident and ordinarily resident adult individuals with salary/regular pension, eligible savings/deposit interest and other normal-rate income; gross supported income capped at Rs 50 lakh. A supported self-occupied house-interest claim is available. Annual HRA inputs must cover the same period; variable periods require separate professional computation.

**Excluded:** business/profession, all capital gains, agricultural income, special-rate income, family pension, foreign income/assets complexity, clubbing, let-out/multiple-property calculations, brought-forward/carry-forward losses, employer NPS, LTA/other exemptions, deductions outside the displayed buckets, AMT, reliefs including section 89, interest 234A/B/C and late fees. Uncheck the relevant scope gate if any excluded item applies. Capital gains are outside this engine even when a limited 112A case might qualify for ITR-1 under official rules.

The form indicator is a candidate only. Residency, form-specific exclusions, filing obligation, deadlines, valid regime election, all omitted charges and portal validation must be independently checked. No filing due date is assumed. The new regime is the default; a lower numerical old-regime tax is conditional on a valid and timely opt-out. A comparison is not a filing-ready certificate.

Do not enter CTC: use taxable gross salary/regular pension before standard deduction, with HRA included and excluded exemptions removed only after specialist review (such cases are outside the base scope). No negative income allowed. Do not treat a bank credit or AIS receipt as automatically taxable income.

## Files

`engine.py`: deterministic tax calculations and scope gates; `app.py`: desktop UI; `report.py`: Excel export; `ai_review.py`: optional API drafting; `samples/`: five fictional profiles; `test_engine.py`, `test_ai.py`: automated tests; `USER_GUIDE.md`: workflow; `RULES_AND_SOURCES.md`: rule register; `SUBMISSION_NOTES.md`: demonstration and project explanation.

## Test

From this folder: `.venv\Scripts\python.exe -m unittest discover -v`

See `TEST_RESULTS.md` for the tests actually performed. GUI import was checked on Linux; Windows GUI operation and live API requests still need your trial. Real PAN, Aadhaar and bank account identifiers are not needed. Profile JSON and Excel exports are unencrypted: use fictional data for the submission.

## Moving / submission

You can put this entire project folder inside a folder named with your name and batch. If the project folder itself moves after installation, delete its `.venv` and run `install.bat` again. Submit source, examples and documentation; exclude `.venv`, `__pycache__`, real taxpayer data, credentials and your private reports. This package is not certified or endorsed by ICAI; confirm the instructor's required submission structure before uploading.
