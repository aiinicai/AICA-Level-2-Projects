# GST SCN Reply Assistant

**ICAI AICA Level 2 (Ver 5.0) - Individual Capstone, Option 1**
**Prepared by:** Umesh Goyal, Batch 102

> **Disclaimer.** Every notice, name, GSTIN, officer, figure and date in this folder is invented for the
> Capstone demonstration. No real client data, password or portal credential is included.
> The tools help a Chartered Accountant to organise and check work; they do not replace professional
> judgement and nothing here is legal advice.

## The problem

When a GST Show Cause Notice (SCN) arrives, the same manual routine repeats for every client:
read the notice, note the section and years, check whether the notice is in time, re-add the tax table,
list the issues, find the reply date, and then draft an issue-wise reply. Mistakes creep in at three
places: a wrong date, a wrong figure copied from a scan, and a reply that argues from assumed facts.

## What was built

| # | Folder | What it is | Tool used |
|---|--------|------------|-----------|
| 1 | `1_claude_skill` | A custom Skill that drafts a taxpayer-side, issue-wise SCN reply. It asks for every missing fact first, checks limitation year by year, recomputes the numbers, and ends with a verification list for the Consultant. | Claude Skills |
| 2 | `2_ai_studio` | A system instruction that turns an SCN PDF into a structured JSON summary. | Google AI Studio |
| 3 | `3_offline_models_test` | A small test of local/offline models on the same SCN text, to see what is safe to run without sending data out. | LM Studio, Google AI Edge Gallery |
| 4 | `4_python_checks` | `check_scn.py` reads the AI Studio JSON and works out the limitation dates and the reply date, re-does the arithmetic of the demand table and checks every figure against the notice. Helpers: OCR of a scanned SCN, header extraction, and a bridge that turns the JSON into a due-date list. | Python, pypdf, PyMuPDF, Tesseract |
| 5 | `5_samples` | The fictional sample SCN (text PDF and scan-like PDF), fictional intake answers, an example JSON, and the outputs the scripts produce. | - |

## How the parts fit together

```
SCN PDF -> (2) AI Studio: JSON summary (AI reads)
                     |
                     v
           (4) check_scn.py: limitation dates, arithmetic, figures found in the notice (code counts)
                     |
                     v
        (1) Claude Skill: intake questions -> extraction table -> limitation -> number check
            -> issue-wise draft -> verification list (human decides)
```

The human stays in the loop at every step. The Skill refuses to draft over a gap: if a date, document or
instruction is missing it stops and asks. Every section, date, amount and authority used in a draft is
listed again at the end, marked "from notice", "from user" or "from authentic source".

## Try it in five minutes (with the fictional SCN)

1. Open `5_samples/sample_scn_text.pdf` (Section 74, FY 2021-22 to FY 2023-24, tax Rs. 10,85,600).
2. **Python checks** (Python 3.10+, `py -m pip install pypdf pymupdf pytesseract pillow`):
   ```
   cd 4_python_checks
   copy ..\5_samples\scn_output_example.json scn_output.json
   copy ..\5_samples\sample_scn_text.pdf .
   py check_scn.py                                  (or open check_scn.py in IDLE and press F5)
   py ocr_scanned_pdf.py ..\5_samples\sample_scn_scanned.pdf      (needs the Tesseract program)
   ```
   `check_scn.py` reads the AI Studio JSON, computes the limitation dates, re-does the arithmetic and checks every
   figure against the notice. For another SCN: run it in AI Studio, save the JSON as `scn_output.json` here, press F5.
   The results should match the files in `5_samples/expected_output`.
3. **Skill**: upload `1_claude_skill/gst-scn-reply-drafter.zip` as a custom Skill, attach the sample SCN and
   ask Claude to analyse it. Answer the intake questions with `5_samples/demo_intake_answers.txt`.
4. **AI Studio**: paste the system instruction from `2_ai_studio`, attach the sample SCN, read the JSON.

## What the sample shows

The fictional SCN is under section 74 for three years, so the checks have something to find:

* **Arithmetic.** Tax at 5% on minerals plus tax at 18% under reverse charge on royalty, year by year,
  adds up to the Total row and to Rs. 10,85,600. The check passes on the text PDF and on the OCR text of the scan.
* **Limitation, year by year.** For an SCN dated 05-10-2026 the section 73 window has closed for FY 2021-22
  and FY 2022-23 and is open for FY 2023-24, while section 74 is open for all three. So the case turns on whether the
  notice states real foundational facts of suppression. The notice only recites the words in paragraph 6, which is
  exactly the point the Skill is written to test. (Standard GSTR-9 due dates are used; extensions under
  section 168A must be verified on the official site.)
* **OCR is not proof.** On the scan, the GSTIN came out as `0OOAAAAAO0000A1Z0` instead of `00AAAAA0000A1Z0`. The
  script reports it as "verify" instead of guessing. Figures are always checked against the original PDF.

## Limitations and responsible use

* AI output is a draft for the Consultant's review. The Skill is written to say so and to avoid a final legal conclusion.
* Only fictional data was given to any AI tool in this project. For real matters, client data should be shared
  only as the Consultant's confidentiality duties allow.
* Limitation law changes by amendment, notification and court order. The dates computed here use the standard
  GSTR-9 due dates and must be verified before they are relied on.
* No portal password, OTP or captcha is stored or automated anywhere in this project.
* OCR can misread digits and identifiers. Every figure is re-checked against the original.

## Future work (not part of this submission)

* A Chrome-extension diary of deadlines with reminders, and reading the "View Notices and Orders" list of the GST portal
  for many clients with one click. Both were not tested enough for this submission, so they are not included or claimed.
* A daily e-mail of due dates with n8n. The workflow was built and the e-mail was received when run by hand;
  starting it automatically with Windows is still being fixed, so it is not included here.
* WhatsApp reminders.

## Folder map

```
AICA-L2-Batch-(102)-Umesh-Goyal/
  README.md
  VIDEO_LINK.txt
  1_claude_skill/        SKILL.md, zip for upload, README
  2_ai_studio/           system instruction, screenshots, README
  3_offline_models_test/ README with the test table
  4_python_checks/       check_scn.py, helper scripts, scn_common.py, README
  5_samples/             fictional SCN (text + scan), intake answers, example JSON, expected_output/
  screenshots/           the run screenshots used in the video
```
