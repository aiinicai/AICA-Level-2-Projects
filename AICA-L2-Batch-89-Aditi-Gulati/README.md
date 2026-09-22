# SurakshaScan — AICA Level 2 Capstone

**A DPDP readiness scanner for educational institutions**

CA Aditi Gulati · Deputy Director, Little Flower House Senior Secondary
School & College, Varanasi
AI for Chartered Accountants — Level 2 · Batch 89, Gurugram

---

## What is in this submission

| Folder | Contents |
|---|---|
| `01_Project_Summary_Document` | The project summary, in Word and PDF |
| `02_Prompt_Files` | The prompts used inside the application, the reusable DPDP review skill, and the development prompts used to build it |
| `03_Example_Files` | Sample inputs, and the reports SurakshaScan produced from them |
| `04_Executable_Files` | The complete source code (zipped) and build instructions; `SurakshaScan.exe` in the portal submission |
| `05_Supporting_Documents` | Architecture, the five-day syllabus map, the obligation catalogue, module guides, the n8n workflow, and the version 1 baseline |

## Quick start

**Without Python:** open `04_Executable_Files` and double-click
`SurakshaScan.exe`. Windows may show a SmartScreen warning because the file is
unsigned — choose *More info* → *Run anyway*.

**From source:**

Extract `04_Executable_Files/SurakshaScan_Source.zip`, then:

```
cd SurakshaScan_Source
pip install -r requirements.txt
python -m surakshascan.tools.demo
python run.py
```

The first command after installing runs an offline self-test against a
bundled demonstration school and prints `Self-test passed.`

## In one paragraph

Under the DPDP Act everyone below eighteen is a child, so for a school the
whole student body is a child Data Principal. SurakshaScan reviews a school
against 25 obligations from the Act and the DPDP Rules 2025, across its
website, published privacy policy, supporting documents and internal
practices, and produces a Word report, an Excel workbook and an HTML
dashboard. Every rating comes from a deterministic rules engine, so the same
inputs always produce the same score; an optional AI layer adds quoted
evidence but can never change a rating. It records who authorised each
review and refuses to run without it. 42 tests, all passing offline.

Review of a school's own social media and its ERP / Tally records was
prototyped and is deliberately held back for a later hackathon build.

---

*All sample outputs in this submission are from a fictitious demonstration
school. SurakshaScan performs a readiness review; it is not a certificate of
compliance and it is not legal advice.*
