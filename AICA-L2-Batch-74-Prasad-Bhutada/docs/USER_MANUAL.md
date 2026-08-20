# User Manual — Daily Staff Use

No login is required for anything in this manual — only the **Manage Formats** area (covered in the Administrator Manual) is password protected.

## Generating documents for a client

1. Open the app and go to **Generate Documents** (the home screen).
2. **Step 1 — Select Templates.** Search or scroll the table and tick every document you need for this client (e.g. Appointment Letter, Consent Letter, Engagement Letter). Click **Next**.
3. **Step 2 — Fill Placeholders.**
   - If the client already exists in Client Master, choose them from the **Import from Client Master** dropdown and click **Auto Fill** — every mapped field (name, address, PAN, etc.) fills in automatically.
   - Fill in anything left blank. Each field shows which document(s) use it, in small italic text below the box, so you know why you're being asked for it.
   - Image fields (Signature, Logo, Photograph) let you choose a file from your PC.
   - If you selected the wrong templates, go **Back** — anything you already typed is kept for placeholders still needed; only fields no longer used by any selected template are dropped.
4. Click **Preview & Generate**. If anything is missing or invalid (e.g. an incomplete PAN), you'll see exactly what to fix before it will proceed.
5. **Step 3 — Preview & Download.** The left panel lists every document just generated — click one to see a Word-like preview of it in the centre. The right panel has Word/PDF download buttons for each document individually, plus **Download All** at the top for everything in one go (as a ZIP if there's more than one file). Generated files are automatically named `<Document Name> - <Client Name>.docx` (and `.pdf`), so there's never any ambiguity about which client a file belongs to.

## Managing clients

Go to **Manage Clients**:
- **Add/Edit**: fill the form at the top and click Add/Update.
- **Search**: the search box filters by name, mobile, or email instantly.
- **Bulk Import**: click **Bulk Import**, choose an Excel file with columns `Client Name, Address Line 1, Address Line 2, Client Type, Mobile, Email` (plus any custom columns your office admin has added) — matching rows are created automatically.
- **Bulk Export**: click **Export to Excel** to download the full client list, useful for backups or sharing with other software.

## Viewing generation history

Go to **Generation History** to see everything generated, by whom (client), when, and with which templates. Filter by date range and export the filtered list to Excel for record-keeping — e.g. "show me everything generated for Client X in March."

## Tips

- You never need to touch a template file directly — if a document format needs fixing, ask whoever holds the Manage Formats password to update it once, and every future generation automatically uses the corrected version.
- Line breaks you type into a field are automatically stripped so text stays on one line in the generated document, exactly as the template's formatting expects.
- Dates are inserted exactly as you type them — the app does not reformat dates, so type them the way you want them to appear (e.g. `06/08/2026`).
