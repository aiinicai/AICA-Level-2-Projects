# FinVault – Final Complete Build Prompt

Paste everything below the line into an AI app builder (Claude, Lovable, etc.) to recreate the app.

---

## 1. Goal
Build **FinVault**, a personal-finance *record keeper and reminder* app for Indian users. People forget the details of their insurance policies, loans, bank accounts, fixed deposits, lockers, cards, vehicles and properties, and forget what they must pay next month. FinVault stores all of it in one place, reminds them, reads reminders aloud, and lets them enter data by typing, voice or Excel.

## 2. Hard constraints
- **Local-first.** All data stays on the user's own device (browser IndexedDB). No server, no login, no cloud database. (Supabase/cloud sync is deliberately NOT used because data must stay on the user's laptop/phone.)
- **Runs on web, desktop and mobile**: a responsive, installable **PWA** (manifest, service worker, works offline after first load, "Install app" button). The service worker must fetch network-first with `cache: 'no-cache'`, and `index.html` must link `style.css?v=N` / `app.js?v=N` so updates are never stale.
- **No build step.** Plain `index.html`, `style.css`, `app.js`, `sw.js`, `manifest.webmanifest`, `icon.svg`, plus SheetJS (`xlsx.full.min.js`) loaded from cdnjs with a local `vendor/` fallback.
- **No secrets in code.** The user pastes their own **Sarvam API key** in Settings; it is stored only in that browser's localStorage.
- Professional colour theme: navy `#0b2545` sidebar, teal `#0e7c86` primary, gold `#c9a227` badges, light grey background, automatic dark mode. Sidebar on desktop, slide-in menu on mobile. Indian number format (₹ 1,00,000) and dd-MMM-yyyy dates.

## 3. Sidebar tabs (in this order)
1. 👤 **My profile** (first tab)
2. 🏠 **Dashboard**
3. 🔔 **Reminders** (badge = items due within 7 days or recently passed)
4. 🗓️ **Next month**
5. 🛡️ **Life insurance**
6. 🚗 **General insurance**
7. 💳 **Credit cards**
8. 🏦 **Loans**
9. 🏛️ **Bank accounts**
10. 📈 **Fixed deposits**
11. 🔐 **Lockers**
12. 🚙 **Vehicles**
13. 🏘️ **Properties**
14. 📂 **Documents**
15. 📁 **Import / Export**
16. ⚙️ **Settings**

A top bar has: page title, a global search box with its own 🎤, and a "+ Add" button (opens a form for the current category, or a chooser on the dashboard). Category pages show a table with search filtering, a **Docs** column (📎 n) and an Edit button.

## 4. Categories and fields (all optional except the name field marked *)
Every field is typed text, number, date, dropdown or notes. Each category's form is generated from one schema so everything (form, table, Excel, voice) stays consistent.

- **Life insurance**: Policy name*, Insurer, Policy number, Type (Endowment/Term/ULIP/Money back/Whole life/Pension/Other), Policy holder/life assured, Nominee, Sum assured, Premium, Premium frequency (Monthly/Quarterly/Half-yearly/Yearly/Single), Next premium due, Maturity date, Expected maturity amount, Account debited for premium, Account to receive maturity, **Maturity taxable?** (Check with CA / Exempt u/s 10(10D) / Taxable), Notes. Show a live hint: if annual premium > 10 % of sum assured → amber warning that maturity is generally taxable (policies after 1-Apr-2012; also ₹5 lakh aggregate-premium cap from 1-Apr-2023); otherwise a neutral teal ℹ note that it is likely exempt. Always "confirm with your CA".
- **General insurance**: Policy name*, Insurer, Policy number, Type (Health/Motor car/Motor two-wheeler/Home-fire/Travel/Personal accident/Critical illness/Business/Other), Insured person/vehicle/property, Nominee, Sum insured, Premium, Start date, Renewal/expiry date, Premium account, Agent/TPA contact, Notes.
- **Credit cards**: Card name*, Issuing bank, **Last 4 digits only** (warn never to store full number/CVV/PIN), Network, Holder, Credit limit, Statement day, Next payment due date, Amount due, Annual fee, Annual-fee date, Expiry (MM/YY), Auto-pay account, Notes.
- **Loans**: Loan name*, Lender, Loan account no., Type (Home/Car/Personal/Education/Gold/Business/Credit card/Other), Principal, Interest rate, EMI, Next EMI date, Loan end date, Outstanding, Account debited, Co-borrower/guarantor, Notes.
- **Bank accounts**: Bank*, Account number, Type (Savings/Current/Salary/NRE/NRO/Demat-linked/Other), **Single / Joint**, Holder(s), Mode of operation, **IFSC** with a "🔍 Find bank & branch" button (calls `https://ifsc.razorpay.com/{IFSC}` and fills Bank and Branch; validate `^[A-Z]{4}0[A-Z0-9]{6}$`), Branch, Nominee(s) & share, Customer ID, Notes.
- **Fixed deposits**: Bank*, FD/receipt no., Holder(s), Principal, Rate, Start date, Maturity date, Maturity amount, Interest payout (Cumulative/Monthly/Quarterly/Half-yearly/Yearly), On maturity (Auto-renew/Credit to account), Linked account, Nominee, Notes.
- **Lockers**: Bank*, Branch, Locker number, Size, Holder(s), Nominee, Annual rent incl. GST, Rent due date, Account debited, Agreement date, Notes.
- **Vehicles**: Vehicle name*, Registration number, Type, Registered owner, Make, Model/variant, Manufacturing year, Fuel, Colour, Chassis no., Engine no., **RC book / smart card number**, Registration date, **RC valid until**, Registering authority (RTO), Hypothecation (bank/loan), Insurer, Insurance policy no., Insurance expiry/renewal, Insurance premium, PUC valid until, Fitness certificate valid until, Road tax due, Next service due, Purchase date, Purchase price, Notes.
- **Properties**: Property name*, Type (Flat/House/Plot/Agricultural land/Commercial/Parking-other), Address, City, Area, Ownership (Sole/Joint/HUF/Company), Owner names & share, Purchase date, Purchase value, Approx. market value, Sale deed/registration no., Survey/gat/CTS/khata no., Society/project, Property tax ID, Property tax due date, Property tax amount, Status (Self-occupied/Rented out/Vacant/Under construction), Tenant, Monthly rent, Next rent due date, Linked home loan, Nominee/legal heir, Notes.

Older single "insurance" records (from earlier versions or old Excel/backup files) must be auto-migrated into Life or General based on type/dates.

## 5. Reminders engine
One function `eventsBetween(from, to)` expands every record into dated events:
- Life premium (recurs by frequency), maturity (receipt)
- General renewal (yearly), card bill (monthly) and annual fee (yearly)
- Loan EMI (monthly until end date), FD maturity (receipt), locker rent (yearly)
- Vehicle insurance (yearly, payment); road tax, PUC, fitness, RC validity, next service (due items, no amount)
- Property tax (yearly, payment); monthly rent (receipt)
Kinds: `out` (payment), `in` (receipt), `due` (no money). Totals use out/in only.

Screens built on it:
- **Dashboard**: record counts, payable this month, payable next month, maturities next month, "coming up in next N days" (N configurable, default 30).
- **Next month**: expected payments total/count, expected receipts, full schedule, "🔊 Read aloud", ".ics export".
- **Reminders tab**: groups – Recently passed (last 7 days), Due today, Next 7 days, Later (next N days); each row shows amount and "in 5d / 2d overdue" pill. **Opening this tab (a click) automatically reads the reminders aloud** (setting to turn off), with Read and Stop buttons. Spoken text begins "Namaste <first name>…" and lists up to 6 items per group.
- **Notifications**: after the user taps "Turn on notifications", check at app start, every 30 minutes and on tab focus; notify once per event per bucket (late, today, 1, 3, 7 days), bundled into one notification, via the service worker's `showNotification`; clicking opens the app. Be honest in the UI that a web app cannot wake itself when fully closed, and offer an **.ics export** (VEVENT per due date with a 3-day VALARM) for guaranteed calendar alerts.

## 6. Voice (Sarvam AI – https://api.sarvam.ai, header `api-subscription-key`)
- **Speech-to-text**: `POST /speech-to-text` multipart (`file`, `model=saarika:v2.5`, `language_code=unknown`) using MediaRecorder (tap to start, tap to stop).
- **Text-to-speech**: `POST /text-to-speech` JSON `{text (≤450-char chunks), target_language_code, speaker, model:"bulbul:v2", pitch:-0.2, pace}`; play `audios[0]` base64 WAV; chunk long text; support Stop. Voice choices: a **deep male Sarvam voice** (abhilash / karun / hitesh); output language selectable (English-IN, Hindi, Marathi, Gujarati, Tamil, Telugu, Bengali, Kannada, Malayalam, Punjabi). **Do not clone or imitate any real person's voice** (e.g., a celebrity) – impersonation is not allowed; use the stock deep voice and say so in Settings. Fall back to the browser's speechSynthesis if no key.
- **Whole-form voice**: a "🎤 Speak details" button in each record form and in the profile; the transcript is sent to `POST /v1/chat/completions` (`model: sarvam-m`, temperature 0.1) with a system prompt listing field keys/labels/types and today's date, replying JSON only (strip `<think>` blocks) → fills the form for review before Save.
- **Every input field has its own 🎤** (record forms, profile, document name/type, global search). Convert speech by field type: numbers ("25,000 rupees" → 25000), dates ("15 March 2027" → 2027-03-15, LLM fallback), dropdowns (fuzzy match to options, LLM fallback), email ("a dot b at gmail dot com" → a.b@gmail.com), codes (PAN, IFSC, Aadhaar, PIN, mobile, account/policy/RC/registration/chassis/engine numbers: strip spaces; upper-case PAN/IFSC/regNo/chassis/engine), notes append. Without a Sarvam key fall back to the browser's SpeechRecognition (en-IN).
- Do NOT voice-enable the API-key field.

## 7. My profile (all optional)
Photo (upload or take with camera, shrunk to ≤600 px), Full name, Date of birth, Mobile, Email, PAN (auto-upper-case, soft format check), Aadhaar (masked password-style with Show/Hide, soft 12-digit check), Address, City, State, PIN, Notes; "Save profile"; whole-profile "🎤 Speak profile details"; per-field mics; its own documents panel (Aadhaar card, PAN card, Passport, Driving licence, Voter ID, Insurance policy, Bank passbook, FD receipt, Loan agreement, Locker agreement, Other). Name is used in greetings.

## 8. Documents
- A shared **document panel** (type dropdown suited to the category, optional name/note, 🎤 for both, ⬆ Upload images/PDFs (multiple, **limit 30 MB per file**, images shrunk to 1280 px JPEG), 📸 Scan with camera) appears (a) at the bottom of every record form under "📎 Documents for this item", (b) on the profile, and (c) in the Documents tab.
- Category document types: Life/General (policy, premium/renewal receipt, claim, nomination), Card (statement…), Loan (sanction letter, agreement, EMI schedule, statement, NOC), Bank (passbook, cheque book, nomination, KYC), FD (receipt, interest certificate), Locker (agreement, rent receipt), Vehicle (**RC book / smart card**, insurance, PUC, fitness, driving licence, invoice, service record, road-tax receipt), Property (sale deed, agreement to sale, property-tax receipt, Index II/7-12/khata extract, society share certificate, tenancy agreement, utility bill, loan/mortgage papers).
- **📂 Documents tab** = the in-app folder: Folder (Profile + each category) → item → files, with a top "Add / scan a document" picker (choose folder + item), search by name/type/item, an "Unlinked" folder for orphans.
- **View opens an in-app viewer overlay** (image or PDF iframe, Download, Close, Esc) – never `window.open(blob)` (it fails with "File not found" on `file://`). Download names the file with a proper extension. Delete confirms.
- Camera opens in its own overlay so it never wipes a half-filled form. Cancelling a *new* unsaved record offers to discard its attached docs; deleting a record deletes its docs (confirm with count). Show clear errors (too large, storage full) and only say "added" when saved.
- Store in IndexedDB: stores `records`, `profile`, `docs` (docs hold `{id, ref (record id | 'profile'), cat, type, name, blob, added}`).

## 9. Import / Export
- **Excel**: Download template (one sheet per category: Life insurance, General insurance, Credit cards, Loans, Bank accounts, Fixed deposits, Lockers, Vehicles, Properties; headers = field labels), Export all, Import .xlsx/.csv (match header by label or key; convert dates to ISO, strip ₹/commas from numbers; add records; also accept a legacy "Insurance" sheet and auto-split it).
- **Backup/Restore (.json)** containing records, profile (photo as data URL) and all documents; restore also accepts the old plain-array format. Warn that the backup contains sensitive IDs.
- **.ics** reminder export.

## 10. Settings
Sarvam key (password field), voice, pace, output language, "remind me N days ahead" (default 30), "read reminders aloud when Reminders opens" (Yes/No), Save, Test voice, Enable notifications. Ask the browser for persistent storage.

## 11. Quality bar / acceptance checks
1. Add one record in every category by typing; it appears in its table, search, Reminders and Next month.
2. Voice: mic on a number, date, dropdown and email field fills correctly; "Speak details" fills a whole form.
3. Excel template → fill → import works; export round-trips.
4. Attach a 12 MB PDF to a loan, view it in the viewer, find it under Documents → Loans → that loan, delete it.
5. Reminders tab auto-reads aloud on click; notifications fire after permission.
6. Works offline after first load, installs as an app, usable at 375 px width, dark mode OK.
7. No console errors; no API keys or personal data in the source; all text on a page escaped (no XSS via record fields).

## 12. Out of scope / notes
No login, no backend, no cloud sync, no real-time bank/insurer integration, no payments. Financial/tax hints are informational only – advise confirming with a CA.
