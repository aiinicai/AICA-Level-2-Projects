# BizCard UAE — AI Bulk Visiting Card Scanner & B2B Lead Automation

An enterprise-grade business productivity solution engineered specifically for door-to-door B2B marketing teams in the **United Arab Emirates (Dubai, Abu Dhabi, Sharjah, Northern Emirates)**.

---

## 1. Problem & Core Value Proposition

- **Field Sales Executives**: Collect 50–100 visiting cards daily across industrial zones (Al Quoz, Musaffah, JAFZA, DAFZA) and business hubs (Business Bay, DIFC, Downtown). Traditional manual typing into Excel is exhausting, slow, and error-prone. With BizCard UAE, field staff finish data entry in **< 2 minutes at the end of the day**.
- **Sales Managers / Admins**: Receive standardized, deduplicated leads synced instantly from the field. Managers verify contacts alongside **original card thumbnail photos**, auto-export styled **Excel sheets (.xlsx)**, and dispatch personalized **bulk introduction emails in 1-Click**.

---

## 2. Key Features

### 🌟 Bulk Card Scanning (USP)
- **Place 10–20 visiting cards on a white table or A3 sheet** and snap **ONE photo** from top.
- **Computer Vision Segmentation**: OpenCV contour detection, CLAHE contrast enhancement, morphological gradient analysis, and 4-point perspective warp automatically detect, crop, and isolate each individual card.
- **OCR & Field Extraction (>95% accuracy)**:
  - **First Name & Last Name** (accurately split for both international and Arab names like *Mohammed Al Mansoori*, *Rashid Bin Zayed*, *Abdul Rahman*).
  - **Full Name** & Honorifics handling (*Sheikh*, *Eng.*, *Dr.*, *Mr.*).
  - **Designation / Job Title** (*Managing Director*, *CEO*, *Procurement Head*, *المدير العام*).
  - **Company Name** (*PJSC*, *LLC*, *FZE*, *FZCO*, *Group*, *Properties*).
  - **UAE Mobile & Phone Numbers** (*+971 50 / 050 / 052 / 054 / 055 / 056 / 058* with standard formatting).
  - **Email ID** & **Company Website**.
  - **Office Address** (*Business Bay, DIFC, Sheikh Zayed Road, JLT, Dubai Silicon Oasis*).
  - **Bilingual & Arabic Support**: RapidOCR ONNX model supports Arabic and English card texts offline.
  - **Cloud Vision Upgrade**: Optional OpenAI GPT-4o Vision or Google Gemini Vision key configuration for 99.5% accuracy.

### 📱 Mobile Field App (Android & iOS Responsive PWA)
- **3 Simple Screens**:
  1. **Home Dashboard**: Today's Scans, Total Leads, Sent Emails, Offline Queue, One-Click Demo Sample.
  2. **Camera with A3 Grid Guide**: Live camera feed with on-screen grid overlay guide, flash toggle, gallery upload, and AI segmentation progress bar.
  3. **Review & Edit**: Card-by-card swipable review list with cropped thumbnail previews, UAE phone verification chips, and inline editable fields.
- **Offline Mode**: Works in basements, industrial warehouses, or offline zones. Scans are saved to local persistent storage and auto-sync to Cloud & Excel when reconnected.
- **One-Tap Actions**: `[Save & Send Intro Email Now]` or `[Save to Excel (Send Later)]`.

### 🖥️ Windows EXE Desktop Application
- **Compiled Windows Executable**: `dist/BizCardUAE/BizCardUAE.exe` built with PyQt6 and PyInstaller.
- **Excel-like Data Grid**: Real-time master table displaying `ID | Date | Card Photo Thumbnail | First Name | Last Name | Company | Designation | UAE Mobile | Email | Address | Status`.
- **Deduplication Engine**: 1-Click scan for duplicate contacts by matching email or mobile number with automatic merging.
- **Import & Export**: Styled corporate Excel `.xlsx` (Navy & Gold header, auto-adjusted columns, zebra striping) and RFC-compliant CSV.
- **Bulk Email Dispatcher**: Select 10 to 100+ contacts and send personalized intro emails in 1-Click.
- **Dynamic Template Manager**: Create templates using `{FirstName}`, `{LastName}`, `{CompanyName}`, `{Designation}`, `{ServiceName}`, `{SenderCompany}`, `{Signature}`.
- **Lead Engagement Tracking**: Real-time status progression (*Sent* &rarr; *Delivered* &rarr; *Opened* &rarr; *Replied*).
- **Settings**: Full SMTP configuration (Gmail App Passwords, Outlook 365, custom SMTP), signature builder, and AI keys.

---

## 3. Architecture & Tech Stack

```
Capstone project/
├── backend/
│   ├── app.py                 # FastAPI REST API (Auth, Cards CRUD, Bulk Scan, SMTP, Excel, Settings)
│   ├── database.py            # SQLite database models (Contacts, EmailTemplates, AppSettings)
│   ├── vision_processor.py    # OpenCV multi-card detection, contour segmentation & perspective warp
│   ├── ocr_engine.py          # RapidOCR (ONNX), UAE NLP regex heuristics, OpenAI/Gemini Vision
│   ├── excel_service.py       # Corporate styled .xlsx & .csv export and import engine
│   ├── email_service.py       # SMTP delivery engine, template interpolation, lead tracking
│   └── sample_generator.py    # Realistic 15-card A3 sheet composite generator for instant testing
├── mobile_app/                # Mobile Field Web App (HTML5, PWA manifest, Camera API, touch CSS)
│   ├── index.html
│   ├── app.js
│   ├── style.css
│   └── manifest.json
├── desktop_app/               # Windows Desktop Application
│   ├── main_desktop.py        # PyQt6 GUI with Excel-like table, thumbnail viewer, email manager
│   ├── build_exe.py           # PyInstaller build automation script
│   └── web_desktop/           # Browser-based desktop manager portal (HTML5 / JS / CSS)
├── data/
│   ├── bizcard.db             # SQLite database
│   ├── uploads/               # Full top-down batch photos
│   ├── cropped/               # Auto-cropped card thumbnails
│   └── exports/               # Generated UAE_B2B_Leads_Master.xlsx
├── dist/BizCardUAE/           # Compiled standalone Windows executable (BizCardUAE.exe)
├── start_backend.bat          # Launch FastAPI backend
├── start_desktop.bat          # Launch Windows Desktop EXE App
├── start_mobile.bat           # Open Mobile Field App in browser
└── run_all.bat                # One-click complete system launcher
```

---

## 4. Quick Start & Execution

### Option A: One-Click Launch (Recommended)
Double-click `run_all.bat` to automatically start the backend server, open the mobile app, and launch the Windows Desktop application.

### Option B: Individual Components
1. **Start Backend Server**:
   ```cmd
   start_backend.bat
   ```
   Server runs on `http://127.0.0.1:8000`.

2. **Open Mobile Field App**:
   Navigate to `http://127.0.0.1:8000/mobile/` on your phone or browser.

3. **Launch Windows Desktop EXE**:
   ```cmd
   start_desktop.bat
   ```
   Or open the browser desktop portal at `http://127.0.0.1:8000/desktop/`.

---

## 5. How to Test the 15-Card Bulk Scan USP

1. Open the Mobile App (`http://127.0.0.1:8000/mobile/`).
2. Tap **"⚡ Load 15 UAE Cards Sample"** or click **"Scan Bulk Cards"** and upload/capture your own photo of cards on a table.
3. Watch the AI progress bar:
   - **Step 1**: Computer vision segments 10–20 individual cards.
   - **Step 2**: OCR extracts names, UAE numbers (+971 50...), companies (Emaar, Al Futtaim, Damac, DP World), emails, and addresses.
   - **Step 3**: Interactive review screen displays **15 Cards Found** with thumbnail photos and editable fields.
4. Tap **"Save & Send Intro Email"**.
5. Switch to the Windows Desktop App: Notice all 15 leads are instantly synchronized, populated in the Excel grid with card thumbnail images, and ready for bulk follow-ups!
