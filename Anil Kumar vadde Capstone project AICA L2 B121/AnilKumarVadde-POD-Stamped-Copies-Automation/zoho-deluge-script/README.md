# Zoho Books Deluge Script

Script: [`attach_stamped_copies.deluge`](attach_stamped_copies.deluge). Paste it into a Zoho Books **Schedule** (Settings → Automation → Schedules) and set it to run daily.

**What it does (runs daily inside Zoho Books):**
1. Reads only the Documents folder **"STAMPED COPIES - SALE INVOICES"**.
2. Takes the invoice number from each file name (e.g. `INV-OCT-000001.pdf`, `INV-OCT-000001_2.pdf`).
3. Finds the exact sales invoice and attaches the file.
4. Adds an audit comment on the invoice and skips files already attached (no duplicates).
5. Logs attached / unmatched / failed counts in Workflow Logs and sends an email summary.

**Setup notes**
- Uses an authorised Zoho connection named `books_conn` (written as a literal string, not a variable).
- An admin authorises the connection once; sales users only upload files. No one gets invoice edit rights.

**Before running**
- Set `notifyEmail` to your email address for the daily summary.
- Optional: set `cfStatusId` to the customfield_id of "Stamped Copy Status" so it is set to "Received" automatically.

**Result statuses:** ATTACHED · ALREADY_LINKED / ALREADY_ATTACHED (skipped) · NO_INVOICE_NUMBER / INVOICE_NOT_FOUND (unmatched) · ATTACH_FAILED / DOWNLOAD_FAILED / ERROR (failed)
