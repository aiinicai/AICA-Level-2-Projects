# 2. Google AI Studio: SCN summary as JSON

An AI Studio prompt whose **system instruction** makes the model read an SCN PDF and return only a structured
JSON object, with strict rules against guessing.

| File | Content |
|------|---------|
| `system_instruction.txt` | The exact system instruction used |
| `screenshots/` | The AI Studio run on `../5_samples/sample_scn_text.pdf`: the system instruction, the attached PDF and the JSON output |

## The rules that matter

* Use only what is printed in the notice; return `null` for anything not printed, redacted or illegible.
* Copy numbers, dates and identifiers exactly as printed. Never add, multiply or round figures; return a total
  only if the notice prints it.
* `din_status` is a string ("printed: ..." or "not visible in this copy"), never true or false.
* `source_pages` gives the PDF page for every key, so each value can be checked quickly.
* No legal opinion and no reply draft; that is the job of the Skill in `../1_claude_skill`.

## How to repeat the run

1. Open Google AI Studio and create a new chat prompt.
2. Paste `system_instruction.txt` into **System instructions**.
3. Attach `../5_samples/sample_scn_text.pdf` and run.

## What the output should show for the sample SCN

| Key | Expected |
|-----|----------|
| `scn_number` / `scn_date` | DEMO/SCN/74/R-12/2026-27/0007 / 05-10-2026 |
| `act_and_section` | section 74(1) of the CGST Act |
| `financial_years` | 2021-22, 2022-23, 2023-24 |
| `noticee_name` / `gstin` | M/s Demo Aggregates Private Limited / 00AAAAA0000A1Z0 |
| `issue_1_tax_amount` / `issue_2_tax_amount` | 6,90,500 (5% on minerals) / 3,95,100 (18% RCM on royalty) |
| `interest_section`, `penalty_section`, `penalty_amount` | section 50, section 74(1), 10,85,600 |
| `reduced_penalty_clause` | section 74(8) |
| `personal_hearing_date` | 17-11-2026 |
| `din_status` | "printed: 202610DM00000000007A" |
| `suppression_allegation_paras` | paragraph 6 |
| `file_number`, `section_29_reference`, `quantity` and `rate` in the table | `null`: the sample does not print them. This is the "never guess" rule working. |

The model's figures are then compared with the script check in `../4_python_checks`
(`check_scn.py`: save the JSON as `scn_output.json` in that folder and run it), and with `../5_samples/expected_output`.
Only the fictional sample was uploaded. A real client notice should not be pasted into a consumer AI tool unless the
engagement terms allow it.
