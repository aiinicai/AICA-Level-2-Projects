# CA Task Mitra – user guide (fictional demo data)

## 1. First launch (CA)
Run `run_windows.bat`. Enter firm name, your name, a CA username and password. Tick "Load fictional demo data" to practise. Sign in. A skippable guided tour starts; press **? Guide** any time to restart it.

## 2. Set up a new office (CA)
1. **Admin → Bulk import:** download each template, fill it in Excel, save as CSV, upload. Order: Clients → Employees → Assignments → Compliance applicability.
2. **Admin → Users & logins:** create employee logins (use *Generate password*).
3. **Admin → Firm settings:** firm name, CA e-mail, SMTP (optional), n8n webhook URL, Tally company and ledgers.
4. **Admin → Module manager:** switch modules or single features on or off.

## 3. Daily work
- **Dashboard:** CA sees work (with employee-wise table), who has reached the office, fees, a 10-day compliance preview, e-mails awaiting approval and announcements. Employees see only their own work, new tasks, compliance dates, e-mails and announcements.
- **Assignments:** grouped cards with counts (status, service, employee, client, due month, compliance/manual). Click a card to open the list. Tick several tasks to *Submit for review* (employee) or *Approve*, *Approve & close*, *Send back* (CA/manager).
- **New assignment:** type in plain English or fill the form; choose default or custom fee; add remarks.
- **Compliance:** Applicability (or CSV import) → *Generate work* for a period. Running it twice never creates duplicates. *Due-date extension* updates open work.
- **Documents insufficient:** open a task → button → e-mail draft goes to the CA approval queue. CA edits and approves; with no SMTP set it is saved as an .eml file in `data/outbox`.
- **Skills library:** open a task with a linked skill → ▶ Run opens Claude/ChatGPT with the prompt filled in (also copied to the clipboard). Employees can suggest skills; the CA approves them.
- **Billing:** closing an assignment creates the invoice automatically from its fee and queues it for Tally. Closed work with no fee waits in *Billing queue*.
- **Tally:** open TallyPrime with the demo company and port 9000 enabled; set company and ledger names in Firm settings; *Tally posting → Post pending*.
- **Alerts:** *Alert rules* – days relative to due date (e.g. -2,0,1); *Send test now* to try. n8n receives the webhook and e-mails the CA.
- **Announcements:** CA posts to everyone or to one employee.

## 4. Safety
Passwords are stored hashed; every change is in the audit trail; backups from Admin → Backup. Do not enter real client data into AI tools.
