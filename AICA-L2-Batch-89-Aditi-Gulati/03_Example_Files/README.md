# Example files

Everything here comes from **Sunrise Public School (demonstration)** — a
fictitious school built to exercise every check. No real institution's data
appears in this folder.

## Inputs

| File | What it represents |
|---|---|
| `01_Sample_School_Website/` | A small school website with a Meta pixel, an admission form posting over plain http:// and asking for Aadhaar, and no privacy policy |

The self-test also fills in ten lines of the internal-practices working paper,
as a reviewer would mid-engagement, to show those answers flowing into the
score.

## Outputs

| File | For |
|---|---|
| `01_Sample_DPDP_Readiness_Report.docx` | The management committee — scored overview with charts, prioritised actions, findings, two-perspective panels |
| `02_Sample_DPDP_Workings.xlsx` | Whoever does the work — findings, remediation plan with owner and date columns, working paper, evidence log |
| `03_Sample_DPDP_Dashboard.html` | A principal on a phone — open in any browser, no internet needed |
| `04_Sample_Evidence_File.json` | An auditor — the timestamped record of everything the scan saw and concluded |

## Reproduce them

From the extracted `04_Executable_Files/SurakshaScan_Source.zip`:

```
python -m surakshascan.tools.demo
```

This serves the sample website on your own computer, reviews it, and rebuilds
all four outputs. Expected: score 8/100 (Critical), 12 gaps, 2 partly met,
and `Self-test passed.`
