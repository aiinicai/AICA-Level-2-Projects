# User Manual — CA DocuFlow AI

*(formerly PDF Office Utility)*

A plain-language guide for everyday office use. No programming knowledge
required.

---

## Getting Started

When you open the app, you'll see a sidebar on the left with: **Dashboard,
Sign PDF, Word → PDF, Merge PDF, Split PDF, Organize Pages, OCR / Scan,
Edit / Redact, Compare, AI Assistant, PDF Tools, Submission Pack,
Integrity / QR, Batch Workflow, Templates, Settings, Logs, About**. Click
any item to switch screens. The **Dashboard** has quick-action cards that
jump straight to the most common tasks.

---

## How to Sign 1 PDF

1. Go to **Sign PDF**.
2. Click **Add Files**, pick your one PDF (or drag it straight into the file
   list).
3. Under **Signature Layers**, click **Browse...** and choose your
   signature image (PNG/JPG).
4. Choose a **Position** (e.g. Bottom Right) and leave **Apply to pages**
   as **Last Page** (or pick whichever page you need).
5. Set your **Output folder**, or leave it blank to save next to the
   original (the app will add `_Signed` to the filename — your original
   file is never changed).
6. Click **SIGN ALL SELECTED PDFs**, review the confirmation screen, then
   click **SIGN ALL 1 DOCUMENTS**.
7. Done — check the report that appears, and your signed file is in the
   output folder.

---

## How to Sign 100 PDFs (the fast way)

This is the whole point of the app:

1. **Drag 100 PDFs** straight into the Sign PDF file list (or use *Add
   Folder* to grab every PDF in a folder at once).
2. Configure your signature **once**: image, position (e.g. **Bottom
   Right**), and page rule (e.g. **Last Page**).
3. Click **SIGN ALL SELECTED PDFs**.
4. Review the confirmation screen — it shows *Documents selected: 100*,
   total pages, your signature, rule, position and output folder.
5. Click **SIGN ALL 100 DOCUMENTS**. A progress bar tracks completion; you
   can **Cancel** at any time.
6. When finished, a report shows how many succeeded/failed, with a reason
   for every failure, and a button to **Retry Failed**.

The app figures out each file's own last page independently — a 3-page
file and a 40-page file in the same batch each get signed correctly.

---

## How to Sign the Last Page

Under **Signature Layers → Apply to pages**, choose **Last Page** from the
dropdown. That's it — no page number to type in.

## How to Sign Every Page

Under **Apply to pages**, choose **All Pages**. Useful for "Initial Every
Page" style requirements — add a second layer of type **Initial**, set its
page rule to **All Pages**, and its position to somewhere that won't
overlap your main signature (e.g. Bottom Left while the signature is
Bottom Right).

## Other Page Rules You Can Use

| You want... | Choose... |
|---|---|
| Just page 3 | **Single Page**, type `3` |
| Pages 1, 3 and 5 | **Multiple Pages**, type `1,3,5` |
| Pages 2 through 10 | **Page Range**, type `2-10` |
| The first page only | **First Page** |
| First and last page | **First and Last Page** |
| Only odd-numbered pages | **Odd Pages** |
| Only even-numbered pages | **Even Pages** |
| Every 2nd page | **Every Nth Page**, type `2` |
| The last 2 pages | **Last N Pages**, type `2` |
| A mix, e.g. page 1, 3, and 5 through 8, plus the last page | **Custom Expression**, type `1,3,5-8,last` |

## Placing a Signature Visually (Drag & Drop)

1. In **Sign PDF**, select a file in the table, then click **Load Selected
   File Into Preview**.
2. The page appears with your signature shown as a movable box.
3. **Drag** it wherever you like; **drag the small blue square** at its
   bottom-right corner to resize it.
4. Click **Use This Position For Selected Layer** — the layer's position is
   now locked to exactly where you placed it (saved as a percentage of the
   page, so it stays correct even on a different page size).

## Saving a Signing Template

Templates remember an entire signature layer's setup (image, size,
position, opacity, rotation, and page rule) so you never have to
reconfigure it.

1. Set up a signature layer exactly the way you want it.
2. In that layer's **Template** row, click **Save As Template**.
3. Give it a name, e.g. `CA Signature – Bottom Right` or `Director
   Signature`.
4. Next time, just pick it from the **Template** dropdown and click
   **Apply** — or manage all your templates from the **Templates** tab
   (create/edit/delete from there too).

## Applying Different Rules to Different Files

Sometimes one file in a batch needs different treatment:

1. In the Sign PDF file table, **double-click** the row for that file.
2. In the dialog, set a page rule and/or position that applies **only to
   this file** — leave a field as "(Use global setting)" to keep the
   batch-wide setting for that field.
3. Click OK. That file now shows its own rule; everything else in the
   batch still uses your global configuration.

## Signing Multiple Documents/Seals on the Same PDF

Click **Add Layer**, choose a type (**Signature**, **Initial**, **Stamp**,
or **Company Seal**), and configure it independently — its own image,
size, position and pages. Add as many layers as you need; each is applied
in the order shown.

---

## How to Convert Word to PDF

1. Go to **Word → PDF**.
2. **Add Word Files** (or a whole folder) — `.doc` and `.docx` both work.
3. Pick an **Output folder**.
4. Click **CONVERT ALL TO PDF**, confirm, and you're done.

If Microsoft Word is installed, it's used automatically for the best
possible formatting. If not, the app falls back to LibreOffice
automatically (install it once from libreoffice.org if you don't have
Word).

## How to Convert + Sign in One Step

1. Go to **Word → PDF**, add your Word documents.
2. Under **Optional: Apply Signature After Conversion**, set the image,
   position and page rule just like on the Sign PDF tab.
3. Click **CONVERT & SIGN ALL**. Each document is converted to PDF *and*
   signed in one pass.

---

## How to Merge PDFs

1. Go to **Merge PDF**, **Add Files** (order matters — this is the order
   they'll appear in the final document).
2. Use **Move Up / Move Down** to reorder if needed.
3. Double-click the **Pages to Include** cell for any file to restrict it
   to specific pages (e.g. `1-5`, or `all` for everything).
4. Set your output file name (e.g. `Merged.pdf`) and location.
5. Click **MERGE PDFs**.

## How to Split a PDF

1. Go to **Split PDF**, add the file(s) you want to split.
2. Pick a **Split Mode**:
   - **Split Every Page** — one PDF per page.
   - **Split by Page Range** — type one range per line, e.g. `1-5`,
     `6-10`, `11-20`.
   - **Extract Pages** — pull out just the pages you list, e.g. `1,3,7-10`,
     into one new PDF.
   - **Split Every N Pages** — e.g. every 5 pages becomes its own file.
   - **Split Into Equal Parts** — e.g. a 100-page PDF into 5 files of ~20
     pages each.
   - **Remove Pages** — delete specific pages (e.g. `2,5,8`) and save
     what's left as one file.
3. Choose an output folder and click **SPLIT PDF(s)**.

## How to Organize Pages Visually

1. Go to **Organize Pages**, click **Open PDF**.
2. Every page appears as a thumbnail — **drag** thumbnails to reorder
   them.
3. **Right-click** a page for Delete / Rotate / Duplicate / Extract.
4. Use the toolbar to **Insert Blank Page** or **Insert Other PDF**.
5. Click **Save As New PDF** when you're happy — your original file is
   untouched until you explicitly save.

## How to Build a Batch Workflow

For repeatable multi-step jobs, e.g. *Word Agreement + Annexure PDF →
merge → sign last page → add company seal → save as "..._Final.pdf"*:

1. Go to **Batch Workflow**, **Add Source Document(s)**.
2. **Add Step** for each stage you need, in order: Convert Word to PDF →
   Merge With Other Documents → Apply Signature → Add Image
   Watermark/Seal. Configure each step in its own dialog.
3. Set an output folder and suffix (e.g. `_Final`).
4. Click **RUN WORKFLOW** — every source document goes through all the
   steps automatically.

---

## How to Make a Scanned PDF Searchable (OCR)

1. Go to **OCR / Scan**, add your scanned PDF(s).
2. Choose a **Language** (English, Hindi, or Kannada), and leave **Skip
   pages that already have text** checked so you don't double-process pages
   that are already digital.
3. Click **MAKE SEARCHABLE**. Each output file can now be searched,
   copy-pasted from, and read by the AI Assistant — the original scan
   images are untouched, just made selectable.

This runs entirely on your computer using Tesseract OCR — nothing is
uploaded anywhere. If you see "Tesseract OCR was not detected," install it
from the link shown, or set its location in **Settings → OCR**.

## How to Permanently Redact Sensitive Data

1. Go to **Edit / Redact**, click **Open PDF**.
2. Tick which types of data to search for (PAN, GSTIN, Aadhaar-like number,
   email, phone, or a generic long-number heuristic for account numbers),
   then click **Find Sensitive Data**.
3. Review every match in the table — click a row to jump the preview to
   that page. Untick anything you don't want redacted, or use **Approve
   All** / **Approve None**.
4. Click **APPLY REDACTION**, confirm, and choose where to save the new
   file. The app reopens the result and automatically verifies the
   approved values are truly gone (not just covered up) before telling you
   it's done.

**Important:** redaction only finds matches in the document's actual text
(if it's a scan, run OCR first). A value can also appear embedded inside
another field — for example, a person's PAN is literally the middle part
of their GSTIN — so review the full document visually before sending it
out, even after redaction.

## How to Compare Two Document Versions

1. Go to **Compare**, browse to **Version A** (the original) and **Version
   B** (the revised copy).
2. Click **COMPARE DOCUMENTS**. The page list on the left marks every page
   as "unchanged" or "CHANGED."
3. Click any page to see the exact added/removed text lines, plus a visual
   image with changed regions highlighted in red — useful for catching a
   moved stamp, redrawn table, or image change that text alone wouldn't show.
4. Click **Export Report** to save a plain-text summary.

## How to Use the AI Assistant

The AI Assistant is optional and needs a provider configured first (see
**Settings → AI Assistant** — pick Ollama for a free, fully local/offline
model, or add an API key for Anthropic/OpenAI/Gemini). Nothing is sent
anywhere until you click a button below.

1. Go to **AI Assistant**, click **Add Document(s)** and pick one or more
   PDFs.
2. **Classify & Summarize** tab: select a document, click **Classify
   Document** to see its category (Invoice, GST Notice, Bank Statement,
   etc.) or **Summarize Document** for a plain-language summary — parties,
   dates, amounts, issues, and any deadline it explicitly mentions (always
   double-check that date yourself; nothing is auto-scheduled).
3. **Extract Data** tab: select a document and a type (Invoice, Bank
   Statement, GST Notice, Income Tax Notice), click **Extract**. Every
   field the AI couldn't find is shown in red as "missing" — treat those
   as needing manual entry, not zero. For invoices, the app automatically
   checks whether the extracted total matches taxable value + taxes and
   warns you if they don't agree. Export the result to JSON when you're
   satisfied it's correct.
4. **Ask Document** tab: type a question that spans everything you've
   added (e.g. "What is the demand amount in the GST notice?") and click
   **Ask**. The answer comes with citations — the exact document and page
   it was drawn from — and the app tells you plainly when it isn't
   confident, rather than guessing.

**Every AI result is a draft for you to check, not a final answer.**

---

## How to Use PDF Tools (Compress, Scan Enhance, Forms, Bates, Repair)

Go to **PDF Tools** — five sub-tabs across the top:

- **Compress**: add files, choose a preset (Maximum Quality down to Maximum
  Compression), click **COMPRESS**. Only embedded images are recompressed;
  your text stays sharp and searchable.
- **Scan Enhance**: for scanned pages only (it rasterizes each page) — fixes
  crooked scans, removes speckle noise, trims scanner borders, and can
  auto-rotate pages using Tesseract if installed.
- **Forms**: open a fillable PDF, edit values directly in the table, then
  **Save Filled PDF** (keeps it fillable), **Save Flattened PDF** (bakes
  values in as static text, no longer editable), or **Export Field Data**
  to JSON.
- **Bates Numbering**: add files in the order you want numbered, set a
  prefix (e.g. `KSC-`) and starting number, click **APPLY BATES
  NUMBERING** — the sequence continues correctly across every file.
- **Repair PDF**: for a file that behaves oddly in some viewers even though
  it opens fine here — rewrites its internal structure into a clean copy.

## How to Build a Submission Pack

1. Go to **Submission Pack**, fill in the client name and engagement (e.g.
   "GST Notice Reply - DRC-01").
2. Optionally list expected document categories in the **Checklist** box
   (one per line) — anything you don't add later gets flagged.
3. Optionally write a **Cover Letter**.
4. Click **Add Document(s)**, then double-click each row to set its
   category (e.g. "Invoice") and which pages to include.
5. Set a **Bates prefix** if you want continuous numbering across the whole
   pack (e.g. `KSC-` → `KSC-000001`, `KSC-000002`, ...).
6. Click **BUILD SUBMISSION PACK**. You get one combined PDF (with a cover
   letter, table of contents, and annexure-labelled sections), a manifest
   listing every source file's hash and page range, and a ZIP bundling both
   — ready to send.

## How to Use Integrity / QR

This is a **local check on this computer**, not a public verification
website — see the in-app notice for why.

1. **Stamp Document**: pick a PDF, choose where the QR/ID goes, click
   **STAMP DOCUMENT ID + QR**. Note the Document ID shown.
2. Do any further processing you need (OCR, watermark, digital signature)
   on the *stamped* file.
3. Once it's truly final, come back to the **Stamp Document** tab, confirm
   the Document ID and select the final file, then click **REGISTER FINAL
   HASH**.
4. Later, use **Verify Document** on any copy of that file — it tells you
   whether the content still matches exactly what was registered, or has
   changed since.
5. **Local Registry** lists everything registered on this computer.

---

## Team Features, Hardware Tokens & Cloud (For Your Firm's IT/Admin)

Everything above is a point-and-click feature of this desktop app. A few
additional capabilities exist as tested building blocks but need someone
technical to set them up — they are documented in `README.md`, not here,
because they involve installing/configuring things outside this app rather
than clicking buttons inside it:

- **Team Deployment** — a separate web application your firm can run so
  documents move through Preparer → Reviewer → Signatory → Auditor →
  Partner with a server keeping track, instead of everyone working on
  local files. See README.md "Team Deployment".
- **USB hardware signing token (DSC)** — this manual's signing steps above
  use a certificate *file*. If your firm's DSC is a USB token instead, that
  needs a one-time technical setup — see README.md "Hardware DSC Token
  Signing (PKCS#11)". This is not yet available as an in-app screen.
- **Outlook/Gmail/OneDrive/Google Drive** — connecting the app to your
  firm's email or cloud storage requires a one-time registration with
  Microsoft or Google that only an admin can do — see README.md "Email &
  Cloud Integrations".
- **Auto-processing an "Incoming" folder** — an opt-in feature that can
  watch a folder and apply a saved template automatically; requires
  explicit setup and a recorded consent before it will do anything — see
  README.md "Folder Watcher (Auto-Processing)".

If none of this applies to you, you can safely ignore this section — the
rest of this manual covers everything the app does on its own.

---

## Before Any Bulk Run: the Confirmation Screen

Every "process all" button shows a summary first — document count, total
pages, what's being applied, and the output folder — with **Cancel**,
**Preview**, and a clearly-labelled action button (e.g. **SIGN ALL 47
DOCUMENTS**). Nothing processes until you confirm.

## If Something Fails Partway Through

The report screen after every batch lists exactly which files succeeded,
which failed (with the reason), and which were skipped. Click **Retry
Failed** to re-run just the failed ones after fixing the issue — no need
to redo the whole batch.

## Your Original Files Are Safe

By default, the app **never overwrites your original file**. A signed
`ABC Agreement.pdf` becomes `ABC Agreement_Signed.pdf` alongside it (or in
your chosen output folder). Only if you deliberately choose **Overwrite
Original** in Output Options will the original file be replaced — and even
then, the app writes the new file completely first and swaps it in, so an
interrupted process can never leave you with a half-written file.
