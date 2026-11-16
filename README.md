# Certification Readyrecknor

A single-file Python desktop application for Chartered Accountancy firms to
draft, review and generate standardized **Microsoft Word (.docx)**
certificates — Net Worth, Turnover, Shareholding Pattern, and
Directors/Partners Details — in a firm's house format, with a mandatory
Chartered Accountant approval step before any certificate can be issued.

Built with **PyQt6** (desktop UI) and **python-docx** (Word generation),
backed by a local **SQLite** database. No internet connection or server is
required to run it, beyond the one-time dependency install on first launch.

---

## Table of Contents

- [Why this exists](#why-this-exists)
- [Key features](#key-features)
- [Certificate types supported](#certificate-types-supported)
- [How it works — the 6-step wizard](#how-it-works--the-6-step-wizard)
- [Getting started](#getting-started)
- [Staff sign-in and the Activity Log](#staff-sign-in-and-the-activity-log)
- [Firm Settings](#firm-settings)
- [Where your data lives](#where-your-data-lives)
- [Packaging as a standalone Windows .exe](#packaging-as-a-standalone-windows-exe)
- [Extending the app with a new certificate type](#extending-the-app-with-a-new-certificate-type)
- [UDIN format check — what it does and does not do](#udin-format-check--what-it-does-and-does-not-do)
- [Important disclaimers](#important-disclaimers)
- [Project structure (single file, by section)](#project-structure-single-file-by-section)
- [Known limitations / possible next steps](#known-limitations--possible-next-steps)

---

## Why this exists

CA office staff repeatedly produce the same handful of special-purpose
certificates for clients (net worth for a loan or visa, turnover for a
tender, shareholding pattern, director details) with largely the same
structure every time: a verification paragraph, a figures table, standard
notes and declarations, and a firm signature block with UDIN. This tool
turns that into a guided, repeatable workflow instead of a copy-pasted
Word document each time — while keeping a Chartered Accountant's explicit
sign-off as a mandatory gate before anything is issued.

## Key features

- **Dashboard** with live counts (total / drafts / finalized certificates,
  certificate types in use) and a recent-activity table.
- **6-step certificate wizard**: Select → Enter Details → Review Wording →
  Preview → CA Approval → Generate.
- **Dynamic, type-specific forms** — add/remove rows for assets,
  liabilities, turnover years, shareholders, or directors, with live
  computed totals (Net Worth, % shareholding, turnover totals/averages).
- **"Fill Sample Data (Demo)"** button on the Details step — instantly
  populates the form with realistic, clearly fictitious data (matched to
  the certificate subtype selected) so anyone can walk through the whole
  wizard and see a finished certificate without typing anything.
- **Editable wording templates** per certificate type (Templates page),
  and a per-certificate Review step so wording can be adjusted before
  every issue.
- **Word (.docx) output** in the firm's house format: title → "To,"
  addressee → verification paragraph → figures table → amount in words
  (where applicable) → Notes & Declarations → firm signature block
  (For, Firm / FRN / Signatory / Membership No. / UDIN / Date / Place).
- **Indian-format currency** throughout: ₹ with Indian digit grouping
  (e.g. ₹ 12,34,567.00) and amount-in-words in the Indian numbering
  system (Lakh/Crore).
- **Saved Drafts** (resume, duplicate, delete) and **Certificate History**
  (search by client/UDIN, re-open the generated file).
- **Staff sign-in + Activity Log** — see
  [below](#staff-sign-in-and-the-activity-log).
- **Firm Settings** — firm name, address, FRN, default signatory, logo,
  default disclaimer text, default output folder.
- **Local SQLite database** — all drafts, finalized records, templates and
  settings persist between sessions; schema auto-migrates on upgrade.
- **No certificate reference number printed on the document** — an
  internal reference number is kept only for the app's own history/
  filename purposes, never on the certificate itself.

## Certificate types supported

| Category | Types |
|---|---|
| Net Worth Certificate | Individual, Business Entity, Visa Purpose, Bank Loan Purpose, Tender/EMD Purpose |
| Turnover Certificate | Single Financial Year, Multiple Financial Years |
| Shareholding Pattern Certificate | Shareholding Pattern |
| Directors / Partners Details Certificate | Directors / Partners Details |

The catalogue is intentionally expandable — see
[Extending the app](#extending-the-app-with-a-new-certificate-type).

## How it works — the 6-step wizard

1. **Select** — search/pick a certificate type from the categorized list.
2. **Enter Details** — fill in client particulars and the certificate's
   specific table(s); totals/percentages recompute live as you type (or
   click "Fill Sample Data (Demo)" to see it populated instantly).
3. **Review Wording** — edit the title, opening/verification paragraph,
   and Notes & Declarations before they go into the document.
4. **Preview** — generates a temporary Word file and opens it in your
   default .docx viewer (normally Microsoft Word) for review.
5. **CA Approval** — mandatory gate: signatory name, membership number,
   and an 18-character alphanumeric UDIN, plus an explicit checkbox
   confirming the Chartered Accountant has reviewed and approved the
   certificate. Nothing can be generated without this step.
6. **Generate** — choose/confirm the destination folder and file name,
   with overwrite protection, and produce the final `.docx`.

## Getting started

**Requirements:** Python 3.9 or later.

```bash
python CertificationReadyrecknor.py
```

- Double-clicking the file, or opening it in IDLE and pressing **F5**,
  works the same way.
- On first run, the app automatically installs its two dependencies
  (`PyQt6` and `python-docx`) via `pip` if they are not already present —
  this needs an internet connection the first time only.
- You'll be asked to sign in with your name (see next section), then the
  Dashboard opens.

## Staff sign-in and the Activity Log

On every launch, the app asks for the name of the person operating it
that session. **This is not a password-protected login** — anyone can
type any name — it exists purely for internal office accountability:

- The name is stamped as **"Generated By"** on every certificate, both
  when the draft is created and when it is finalized.
- **Certificate History** shows a "Generated By" column for every
  finalized certificate.
- A dedicated **Activity Log** page lists every "Draft Created" and
  "Finalized" event with timestamp, staff name, certificate type, client,
  and reference number — searchable by any of these.

## Firm Settings

Configure once under **Settings**:

- Firm name, reference code (used only internally for history/filenames,
  never printed on the certificate), address, FRN.
- Default signatory name, designation, and membership number (pre-fills
  the CA Approval step; can still be overridden per certificate).
- Firm logo (optional) and a default disclaimer/additional restriction
  text appended to every certificate's Notes & Declarations.
- Default output folder for generated `.docx` files.

## Where your data lives

All application data is local to the machine it runs on — nothing is sent
anywhere:

```
Windows:  %USERPROFILE%\.certification_readyrecknor\
macOS/Linux: ~/.certification_readyrecknor/
```

Inside that folder:

- `readyrecknor.db` — SQLite database: drafts, finalized certificate
  records, wording templates, firm settings, and the audit/activity log.
- `assets/` — uploaded firm logo.
- `exports/` — default output folder for generated certificates and
  temporary preview files.

## Packaging as a standalone Windows .exe

PyInstaller must run **on the target OS** — it cannot cross-compile, so
this step is done on an actual Windows machine (yours or a colleague's),
not inside this repository's build tooling:

```bash
pip install pyinstaller
pyinstaller --noconsole --onefile --name "CertificationReadyrecknor" CertificationReadyrecknor.py
```

The resulting `dist\CertificationReadyrecknor.exe` is self-contained
(dependencies bundled) and can be copied to and run on any Windows PC
without a separate Python install. Add `--icon=youricon.ico` for a custom
taskbar icon.

## Extending the app with a new certificate type

Everything needed to add a new certificate type lives in a handful of
well-marked spots in the single source file:

1. **`CERTIFICATE_CATEGORIES`** — add the new type (key + display name)
   under an existing category, or add a whole new category dict.
2. **`CERTIFICATE_TITLES`** and **`CERTIFICATE_PREFIX`** — add the
   document title and the short code used in internal reference numbers.
3. **`fields_for_type()`** — describe the scalar fields and any table(s)
   the new certificate needs.
4. **`sample_data_for_type()`** — (optional but recommended) add demo
   data so the "Fill Sample Data" button works for the new type.
5. **`default_wording()`** — add the verification paragraph and notes
   template.
6. A new **`BaseCertificateDocx`** subclass implementing `build_body(doc)`
   for the new table layout, registered in **`_DOCX_BUILDERS`**.

No other wiring is required — the wizard, forms, and generation pipeline
are all driven from these configuration points.

## UDIN format check — what it does and does not do

The CA Approval step requires an **18-character alphanumeric** UDIN and
checks only that it is the right length and character set. It does
**not** connect to, or verify anything against, the ICAI UDIN portal.
Note for reviewers: ICAI's actual system-generated UDIN is 18 **numeric**
digits (2-digit year + 6-digit membership number + 10 random digits); the
alphanumeric check here was set per explicit instruction from the firm —
if that should instead be numeric-only, the single regex in
`validate_udin()` is the only place to change.

## Important disclaimers

- This is a **drafting and production aid**, not a substitute for
  professional judgement. Every certificate requires explicit review and
  approval by an authorized, practising Chartered Accountant before
  issue — enforced by the mandatory Approval step.
- Wording templates are a starting point based on common house-certificate
  practice; they must be reviewed for applicability to each engagement.
- PAN/GSTIN/CIN/UDIN checks are **format-only** (regex), not verification
  against any government or ICAI database.
- No certificate reference number is printed on the issued document.

## Project structure (single file, by section)

The entire application is one file, `CertificationReadyrecknor.py`,
organized into 14 numbered sections:

1. Dependency bootstrap (auto-installs PyQt6 / python-docx)
2. Imports
3. Constants, paths, colours, QSS stylesheet
4. Utility functions (Indian currency/number-to-words, ID validation)
5. Certificate type configuration (catalogue, fields, sample data)
6. Default certificate wording templates
7. Database layer (SQLite, parameterised queries)
8. python-docx certificate generation engine
9. Reusable GUI widgets (dashboard cards, step indicator, table editor)
10. Certificate wizard step pages
11. Certificate wizard orchestrator
12. Main application pages (Dashboard, Drafts, History, Activity Log,
    Templates, Settings)
13. Sidebar navigation + main window
14. Application entry point

## Known limitations / possible next steps

- Staff "sign-in" is a name prompt, not an authenticated login — it
  exists for accountability, not access control.
- No built-in Word-document preview pane; "Preview" opens the generated
  file in your system's default .docx viewer.
- PDF export is not currently included (the app generates `.docx` only,
  per firm request); could be added alongside Word output if needed.
- No multi-user/network database — each installation has its own local
  SQLite file.
