# Example files

Everything here comes from **Sunrise Public School (demonstration)** — a
fictitious school built to exercise every check. No real institution's data
appears in this folder.

## Inputs

| File | What it represents |
|---|---|
| `01_Sample_ERP_Student_Export.csv` | 120 synthetic student records exported from a school ERP — deliberately including Aadhaar, caste category, blood group, medical notes and bank columns, and records of students who have left |
| `02_Sample_Learning_Platform_Export.csv` | A learning-platform class export |
| `03_Sample_Social_Media_Posts.csv` | Five posts — two naming a child with a class, one carrying a roll number, one boosted |
| `04_Sample_Tally_Ledger_Response.xml` | A TallyPrime ledger-master response, as returned over its local XML interface |
| `05_Sample_School_Website/` | A small website with a Meta pixel, an insecure form and no privacy policy |

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

This rebuilds all four outputs from the inputs above.
