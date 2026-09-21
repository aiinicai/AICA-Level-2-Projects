# Scheduling a recurring review

A readiness review that happens once is a document. One that repeats is a
control. Websites change: an agency adds a marketing pixel, a gallery page
appears, a policy is quietly replaced.

`surakshascan watch` re-scans, compares against the last evidence file and
reports only if the score moved by more than the threshold. A quiet quarter
produces no output.

## Windows Task Scheduler

```
Program:    C:\path\to\.venv\Scripts\python.exe
Arguments:  -m surakshascan.cli watch --name "My School"
            --url https://myschool.edu.in --threshold 5
            --docx C:\Reports\MySchool.docx
Trigger:    quarterly, 06:00
```

## cron

```
0 6 1 1,4,7,10 * /path/to/.venv/bin/python -m surakshascan.cli watch \
    --name "My School" --url https://myschool.edu.in --threshold 5
```

## n8n

Import `integrations/n8n_dpdp_quarterly_review.json`. Read the JSON before you
import it, set the two credentials in n8n's credential manager rather than in
the workflow, and check the execution log after the first run.

## The approval rule

None of these send anything to anyone. Each writes a report and raises a task
or a file for a person to look at. Sending a readiness report to a school —
or to its management committee — is a deliberate act with professional
consequences, and it stays a human one.
