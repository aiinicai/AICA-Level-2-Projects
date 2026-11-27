# Test plan

Two kinds of testing: **A. automatic tests** (one command, 15 tests) and **B. screen-by-screen tests** (about 30 minutes, using the dummy files in `04_Test_Data`). Fill the *Result* column while testing and save the screenshots named in the last column into the `screenshots` folder.

## A. Automatic tests

In Command Prompt, inside the `03_Code` folder:

```
python tests/test_core.py --report ../05_Test_Plan_and_Evidence/automatic_test_results.txt
```

Expected: `15 of 15 tests passed`. What they check:

| Test | What it proves |
| --- | --- |
| users_are_created, login | 30 users exist (2 per department + Audit Admin + Management); wrong password refused; passwords stored hashed |
| import_valid_and_invalid_rows | Good rows import; unknown department, bad date, bad risk, bad auditor type and duplicate serial numbers are rejected with the Excel row number; missing column refuses the whole file |
| ageing_buckets | Boundaries 0, 1, 30, 31, 60, 61, 90, 91 days fall in the right bucket |
| status_logic_auditor_is_official | Auditor status drives the official status; disagreement flag; revised date and extension count; closed findings leave the ageing |
| round_eligibility_quarterly_and_monthly | Quarterly = all unclosed; monthly = High risk only; closed findings drop out; no double entry on the same date |
| permissions | Owner cannot touch another department; admin/management cannot use the owner form; owner cannot do audit work; owner locked out after auditor review; evidence over 5 MB refused |
| original_target_date_is_locked_and_revision_is_rule_checked | Original target date unchanged; revised date compulsory when date has passed; audit trail entry; evidence stored and retrievable |
| reminders_one_week_after_due_date | Reminder due exactly 7 days after the due date (not 6); sent once; goes to both department users with audit team in copy; none for answered items |
| email_redirect_and_failure_handling | Test redirect works; a failing mail is logged, never crashes |
| escalation_is_off_by_default_and_works_when_on | Switch behaviour |
| open_round_sends_one_email_per_department | One e-mail per department |
| sample_data | 14 departments x 30-50 findings; all three statuses, all ageing buckets and disagreements present; wipe keeps users |
| wide_export_and_excel | Wide layout columns and Excel file |
| edit_finding_is_logged | Edits logged with old and new value; duplicate serial refused |

## B. Screen-by-screen tests

Start the app (`streamlit run app.py`) with the default settings (`EMAIL_MODE=log`: e-mails are written to the e-mail log and not really sent). Start from an empty database (delete `audit_tracker.db`).

| No. | Sign in as | Steps | Expected | Result | Screenshot |
| --- | --- | --- | --- | --- | --- |
| 1 | - | Open the app | Sign-in page with test hint | | 01_login |
| 2 | Audit Admin / wrong password | Sign in | "Wrong user name or password" | | |
| 3 | Audit Admin | Sign in with `Test@123` | Menu with 7 pages | | 02_admin_menu |
| 4 | Audit Admin | Import and sample data > upload `import_with_errors.xlsx` > Import | 2 imported, 5 rejected; table lists Excel rows 4 to 8 with reasons | | 03_import_errors |
| 5 | Audit Admin | Upload `import_missing_column.xlsx` > Import | Message: file is missing the column "Risk level" | | |
| 6 | Audit Admin | Type WIPE and click Delete all findings | All findings deleted; users stay | | |
| 7 | Audit Admin | Upload `sample_findings_import.xlsx` > Import | 584 imported, 0 rejected | | 04_import_ok |
| 8 | Audit Admin | Rounds and reminders > Quarterly, follow-up today, due in 14 days, tick e-mail > Open round | "Round opened with 584 finding(s)"; 14 department lines | | 05_round_opened |
| 9 | Audit Admin | Audit trail and e-mail log > E-mail log | 14 e-mails, mode `log`, each To = the department's 2 users, Cc = audit admin | | 06_email_log |
| 10 | Credit 1 | Respond to findings | Only Credit findings listed; definitions of Open / Ongoing / Closed shown | | 07_owner_view |
| 11 | Credit 1 | Pick an item, status Ongoing, response text, no revised date > Submit (only if its target date has passed) | Error: give a revised target date | | |
| 12 | Credit 1 | Tick "revised target date", pick a date, upload a small file > Submit | "Your response has been saved" | | 08_owner_saved |
| 13 | Credit 2 (same department) | Open the same item | Sees Credit 1's response and can still edit it | | |
| 14 | Credit 1 | Findings register | Only Credit findings; no edit forms; original target date shown but not editable | | |
| 15 | Audit Admin | Review responses > Awaiting my review | The item from step 12 appears with the evidence download | | 09_review |
| 16 | Audit Admin | Choose Closed, leave remarks empty > Save | Error: remarks required to close | | |
| 17 | Audit Admin | Choose Ongoing with remarks > Save | Saved | | |
| 18 | Credit 1 | Try to edit the same item again | Item no longer appears in the to-do list (the auditor has reviewed it; it stays in the history) | | |
| 19 | Audit Admin | Rounds and reminders > Monthly (High risk only), a new follow-up date | Only unclosed High-risk findings included | | 10_monthly |
| 20 | Management | Sign in | Menu has only Dashboard and Findings register; no edit forms | | |
| 21 | Audit Admin | Import and sample data > WIPE > Load sample data | 584 findings loaded; "245 items waiting" style message | | 11_sample_loaded |
| 22 | Audit Admin | Rounds and reminders > Reminders section | Lists items whose due date + 7 days has passed, by department | | 12_reminders_due |
| 23 | Audit Admin | Click Send reminders now | One line per department; e-mail log shows REMINDER mails, To = 2 users, Cc = audit admin | | 13_reminders_sent |
| 24 | Audit Admin | Click Send reminders now again | "Nothing to send" (no second reminder) | | |
| 25 | Audit Admin | Dashboard | Tiles, ageing chart with all 5 buckets filled, charts by department / risk / source / year, trend by round, disagreement list | | 14_dashboard |
| 26 | Audit Admin | Dashboard filters: Department = Finance, Risk = High | Numbers change; Excel download works | | |
| 27 | Credit 1 | Dashboard | Department locked to Credit; only Credit numbers | | 15_owner_dashboard |
| 28 | Audit Admin | Import and sample data > Download wide layout | Excel with the 14 columns, current status, then FU1 date / management status / management response / auditor status blocks | | 16_wide_export |
| 29 | Audit Admin | Audit trail | Entries for import, round, management update, auditor review, reminders | | 17_audit_trail |
| 30 | Audit Admin | Findings register > Edit a finding > change the heading > Save | "1 field(s) changed"; audit trail shows old and new heading | | |

## C. Variant A checks (Gmail and Supabase), done once on your own computer

| No. | Steps | Expected | Result |
| --- | --- | --- | --- |
| C1 | Fill `secrets.toml`: `EMAIL_MODE="gmail"`, `GMAIL_USER`, `GMAIL_APP_PASSWORD`, and `TEST_EMAIL_OVERRIDE` = your own address. Restart. Rounds page > Send test e-mail | "Sent through Gmail" and the mail arrives in your inbox | |
| C2 | Open a round with the e-mail box ticked | You receive the department e-mails (all redirected to you, the log shows the original recipients) | |
| C3 | Fill `DATABASE_URL` with the Supabase connection string. Restart the app, load sample data, close the app, start it again | Data is still there | |

## D. Variant B (Microsoft 365)

Cannot be tested until IT gives clearance (server, mailbox, app registration). When ready: set `EMAIL_MODE="graph"` (or `smtp`) with the settings in `secrets.toml.example`, then repeat C1 and C2.
