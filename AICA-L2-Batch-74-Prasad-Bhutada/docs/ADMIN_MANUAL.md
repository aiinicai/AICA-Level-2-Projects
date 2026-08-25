# Administrator Manual

Everything in this manual lives behind **Manage Formats** (top-right button), which requires the Template Management password.

## First login

1. Click **Manage Formats**, enter the password set in `backend/.env` as `DEFAULT_ADMIN_PASSWORD` during installation.
2. Immediately go to **Settings** and change it: **Change Template Management Password** → enter a new password → **Update Password**. This is the only password in the system and it is never hardcoded — it's stored (bcrypt-hashed) in the database and changeable any time here.

## Importing templates

1. In **Manage Formats**, click **+ Import Template**.
2. Choose one or more `.docx` files (legacy `.doc` files must be re-saved as `.docx` from Word first — the app will tell you if you try to import a `.doc`).
3. Pick a **Category** (Income Tax, GST, Audit, ROC, Certificates, Engagement Letters, Miscellaneous, or any custom category you've created).
4. Add **Keywords** (comma separated) to help staff find it later via search.
5. Click **Import**. The app immediately scans the document and lists every `#Placeholder#` it found in the right-hand panel — check this looks right before relying on the template.

### Placeholder rules when authoring a template in Word

- Wrap every variable with `#`, e.g. `#Client Name#`, `#PAN#`, `#Date#`.
- Reserved names `#Signature#`, `#Logo#`, `#Photograph#` / `#Photo#` are automatically treated as **image** placeholders — staff will be prompted to upload an image for these instead of typing text.
- Placeholders can go anywhere: body text, tables, headers, footers, text boxes, and shapes.
- Keep a placeholder's formatting (font/bold/color/etc.) set exactly the way you want the final replaced text to look — generation preserves that formatting exactly.

## Replacing, renaming, and deleting templates

- **Replace**: select a template, use Replace to upload a corrected `.docx` — this keeps the same template record (and thus the same category/keywords/history links) but updates the file and re-scans placeholders. The template's version number increments.
- **Rename**: changes the display name only, not the file.
- **Delete**: moves the template to the Recycle Bin (nothing is destroyed). If the template has previously been used to generate documents, you'll see a warning telling you how many times, but you can still proceed — past generated documents are never affected, since they are independent files.
- **Restore**: from the Recycle Bin, bring a deleted template back to Active.

## Categories

Manage Formats includes the ability to add new categories beyond the seven defaults. Default categories cannot be deleted; custom categories can be deleted only once no active template uses them.

## Placeholder → Client Master Mapping

This is what powers the **Auto Fill** button for staff. Go to the mapping screen (linked from Manage Formats) and, for each placeholder that corresponds to a Client Master field (e.g. `#Client Name#` → Client Name, `#PAN#` → a custom "PAN Number" field you've added), choose the matching field from the dropdown. Any placeholder without a mapping simply stays a manual-entry field during generation — nothing breaks, staff just type it in.

## Client Master fields

Beyond the six built-in fields (Name, Address 1, Address 2, Type, Mobile, Email), CA Docs comes pre-loaded with the fields a CA office needs on essentially every client: **PAN, GSTIN, TAN, CIN/Registration No., and Date of Incorporation/Birth**. These already appear on the client Add/Edit form and are ready to map to placeholders.

To add still more fields without any code changes: go to **Manage Clients → + Custom Field** (visible once Manage Formats is unlocked), give it a name and a type (Text/Email/Mobile/Date/PAN/GSTIN/PIN Code). It immediately appears on the client form and in the Placeholder Mapping screen.

## Application Settings

All under Manage Formats → Settings, all changeable without touching the source code:

| Setting | What it controls |
|---|---|
| Template Folder | Where master `.docx` files are stored on disk. |
| Generated Documents Folder | Where per-client generated output is written. |
| Backup Folder | Where scheduled/manual backup ZIPs are written. |
| PDF Engine | Currently `libreoffice`; the field exists so a different engine can be plugged in later. |
| Backup Frequency | A cron expression, e.g. `0 21 * * *` = every day at 9 PM. |
| Default Theme | `light` or `dark`. |
| Excel Export Location | Default folder suggested when exporting client/history Excel files. |

Changing a folder setting does **not** move existing files — copy them manually if you relocate a folder, then update the setting to match.

### PDF downloads not working

The `SOFFICE_PATH` in `backend\.env` (not the Settings screen — this one requires a restart to take effect) must point directly at `soffice.exe`, not the folder it's in — e.g. `C:\Program Files\LibreOffice\program\soffice.exe`. Confirm the path is correct by running it with `--version` from Command Prompt.

If the path is correct but conversion still fails: each conversion runs in its own temporary, isolated LibreOffice profile specifically to avoid the most common cause of headless failures on Windows — a background "LibreOffice Quickstarter" (the icon that appears in the system tray after installing LibreOffice) holding a lock on the default profile. This means a running Quickstarter should **not** block PDF generation. If it still fails, the error banner in the app now shows the specific LibreOffice error detail — check that message first, and check the backend's log files (`backend\logs`) for the full detail if it's not clear.

Word documents always download successfully regardless of PDF status — PDF failures never block or lose a generated Word document.

## Backup & Restore

- **Run Backup** (Manage Formats → Backup) creates an immediate ZIP containing the database file and the entire templates folder.
- **Scheduled backups** run automatically per the cron expression in Settings.
- **Restore** uploads a previous backup ZIP and replaces the current database and templates folder. **Restart the backend service afterward** for the restored database to be fully reloaded (Windows: `net stop CADocsBackend && net start CADocsBackend`).
- Client Master, categories, mappings, and generation history are all inside the single database file, so restoring the database restores all of them together — there's no separate "restore clients" step.

## Full-text search

The left panel of Manage Formats and the template-selection table in document generation both search Template Name, Keywords, and Category simultaneously — start typing and results narrow immediately.
