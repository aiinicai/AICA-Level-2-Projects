<div align="center">
<img width="1200" height="475" alt="GHBanner" src="https://ai.google.dev/static/site-assets/images/share-ais-513315318.png" />
</div>

# Run and deploy your AI Studio app

This contains everything you need to run your app locally.

View your app in AI Studio: https://ai.studio/apps/31b21528-31d6-4768-be02-f0ef92331fd9

1. **Website-only method** — no software installation required.
2. **Git command-line method** — recommended for complete project folders and projects containing many files.
# Invoice QR → Excel (Offline)

## Overview

A browser-based, offline invoice QR scanner that finds QR codes in invoice PDFs and scanned images, decodes the QR content, parses common QR formats—including GST e-invoice signed QRs—and exports the extracted data to an Excel workbook.

## Fork + Pull Request Workflow

1. **Fork:** Create a personal copy of `aiinicai/AICA-Level-2-Projects` under your GitHub account.
2. **Add your folder:** Upload or copy your project folder into your fork.
3. **Commit:** Save the changes in your fork with a clear commit message.
4. **Open a Pull Request:** Request the `aiinicai` account to merge your changes into the original repository.
5. **Merge:** The repository owner reviews and accepts your Pull Request. After it is merged, your project folder will appear in the official repository.
The application is designed so that scanning happens locally in the browser and files are not uploaded.

## Supported Input

- PDF
- PNG
- JPG
- WEBP
- Multiple files
- Multi-page PDFs

# Method 1: Website Only

Use this method if:

- You do not want to install Git.
- Your project contains relatively few files.
- You do not need to preserve the project’s earlier commit history.

> [!NOTE]
> GitHub’s web uploader generally allows up to 100 files in a single upload. If your project contains more files, upload them in batches or use the Git command-line method.

## Step 1: Fork the Repository

1. Log in to your GitHub account.
2. Open the [AICA-Level-2-Projects repository](https://github.com/aiinicai/AICA-Level-2-Projects).
3. Click **Fork** in the upper-right corner of the page.
4. On the **Create a new fork** page, keep the default settings.
5. Click **Create fork**.

You will be redirected to your personal copy of the repository:

```text
https://github.com/YOUR-USERNAME/AICA-Level-2-Projects
```
## Run Locally

**Prerequisites:**  Node.js


1. Install dependencies:
   `npm install`
2. Set the `GEMINI_API_KEY` in [.env.local](.env.local) to your Gemini API key
3. Run the app:
   `npm run dev`
# 📊 Stock Statement + ICAI UDIN Automation Tool

**A Professional Automation Solution for Chartered Accountants**

## 🎯 Project Overview

This is an advanced **automation tool** designed specifically for **Chartered Accountants (CAs)** to streamline the process of:

- ✅ Generating **Stock Statements** 
- ✅ Creating **Drawing Power Certificates**
- ✅ Automating **ICAI UDIN** (Unique Document Identification Number) certificate registration
- ✅ Managing multiple **bank clients** and financial data
- ✅ Auto-filling **ICAI forms** with UDIN integration

### 🌟 Key Features

| Feature | Description |
|---------|-------------|
| **Browser Automation** | Uses Selenium + Microsoft Edge for ICAI website automation |
| **Data Management** | JSON-based storage for clients, debtors, creditors, and stock information |
| **UDIN Integration** | Automated UDIN certificate generation and submission to ICAI portal |
| **Multi-Client Support** | Manage multiple clients with different banks and credit limits |
| **CA Profile Storage** | Secure storage of CA credentials (ICAI username, FRN, membership details) |
| **Form Recording** | Records user steps for debugging and process optimization |
| **HTML Interface** | User-friendly web-based interface for data entry |
| **Batch Processing** | Process multiple certificates in one session |

---

## 🛠️ Tech Stack

- **Backend**: Python 3 with Selenium WebDriver
- **Frontend**: HTML5 + Angular (ng-select for dropdowns)
- **Data Storage**: JSON files (structured data format)
- **Browser Automation**: Microsoft Edge WebDriver
- **Platform**: Windows (.bat files for execution)

---

## 📋 Prerequisites

### System Requirements
- Windows 10 or higher
- Python 3.7+
- Microsoft Edge browser
- Internet connection (for ICAI portal access)

### Software Dependencies
- **Python Libraries**: 
  - `selenium` (for browser automation)
  - Additional dependencies auto-installed on first run

### ICAI Credentials Required
- ICAI Member Username (Email format: `MEMBERSHIP_NO@icai.org`)
- ICAI Portal Password
- Firm Registration Number (FRN)
- CA Membership Number

---

## 📦 Project Structure

```
Stock Statement UDIN Automation/
│
├── RUN_STOCK_STATEMENT_UDIN_V21_FIXED.py      # Main automation script
├── Stock_Statement_Drawing_Power_UDIN_Integrated_v20.html  # UI Interface
├── RUN_STOCK_STATEMENT_UDIN_V21.bat            # Batch file to run tool
├── RECORD_ICAI_STEPS.bat                       # Batch file to record steps
│
├── StockStatementData/                         # Data folder (created automatically)
│   ├── clients.json                            # Client master data
│   ├── debtors.json                            # Sundry Debtors list
│   ├── creditors.json                          # Sundry Creditors list
│   ├── stock.json                              # Stock information
│   ├── profiles.json                           # CA profile & credentials
│   ├── stock-statement_*.json                  # Form state backups
│   └── recordings/                             # Step recordings
│
├── README.md                                   # This file
├── DOCUMENTATION.md                            # Detailed process guide
└── DATA_STRUCTURE.md                           # Data format reference

```

---

## 🚀 Installation & Setup

### Step 1: Download Python
1. Visit https://www.python.org/
2. Download **Python 3.9 or higher**
3. During installation, **TICK the checkbox** "Add Python to PATH"
4. Click Install

### Step 2: Extract Project Files
- Extract all project files to a folder (e.g., `C:\StockStatementTool\`)
- Keep all files together in the same folder

### Step 3: Prepare Your Data
- Edit `StockStatementData/profiles.json` with your CA credentials
- Add your clients in `StockStatementData/clients.json`
- Update debtors and creditors data as needed

After the Pull Request is merged, your project folder will become part of the official repository.
Users can either drag files into the drop area or click to browse.

## Core Workflow

1. Select or drop invoice files.
2. For PDFs, render each page at multiple scales and scan for a QR code.
3. For images, resize large images to a maximum side length of 4200 pixels and scan them.
4. Prefer the browser's native `BarcodeDetector` when available.
5. Fall back to `jsQR` when native detection is unavailable or unsuccessful.
6. Try image enhancement using Otsu thresholding when needed.
7. Scan cropped regions at reduced scales to improve QR detection.
8. Parse the decoded QR text.
9. Display one result row per scanned page/file.
10. Export all found QR data to `qr-invoice-data.xlsx`.
### Step 4: First Run
- Double-click `RUN_STOCK_STATEMENT_UDIN_V21.bat`
- The tool will:
  1. Check for Python installation
  2. Install Selenium (if not present)
  3. Open the HTML interface
  4. Launch Microsoft Edge for ICAI automation

## QR Parsing

## 💻 Usage Guide

### Running the Tool

```bash
# Run the main application
RUN_STOCK_STATEMENT_UDIN_V21.bat

# Record ICAI steps for debugging
RECORD_ICAI_STEPS.bat
```

### Workflow

1. **Launch Tool**: Double-click `.bat` file
2. **Select CA Profile**: Choose from saved profiles (picks your CA credentials)
3. **Enter Client Details**: 
   - Select client name
   - Enter statement date
   - Choose certificate type (Stock Statement, Drawing Power, etc.)
4. **Add Figures**:
   - Sundry Debtors amount
   - Stock value
   - Sundry Creditors amount
5. **Auto-Fill ICAI Form**: Tool automatically fills the ICAI portal
6. **Enter CAPTCHA**: Manually enter CAPTCHA (shown in HTML interface, not Edge window)
7. **Generate UDIN**: Submit and receive UDIN from ICAI
8. **Save Certificate**: Download and store UDIN certificate

---

## 📊 Data Files Explained

### `clients.json`
Stores master client data with bank and credit details.

**Fields**:
- `name`: Company/Borrower name
- `pan`: PAN number (10 characters)
- `address`: Complete address
- `gst`: GSTIN (15 characters)
- `bank`: Bank name (e.g., "State Bank of India")
- `branch`: Branch name
- `loanAccountNo`: Loan/CC Account number
- `sanctionLimit`: Credit limit in rupees

### `debtors.json` / `creditors.json` / `stock.json`
PDF backup of financial statements (base64 encoded).

### `profiles.json`
CA credentials and firm information.

**Fields**:
- `id`: Unique profile ID
- `label`: Display name
- `icaiUsername`: ICAI login (format: `MEMBERSHIP_NO@icai.org`)
- `icaiPassword`: ICAI portal password
- `firmName`: Registered firm name
- `caName`: CA's full name
- `membershipNo`: ICAI membership number
- `frn`: Firm Registration Number
- `certificatePlace`: Signing location (usually city name)

---

## 🔧 Troubleshooting

### Issue: Python not found
**Solution**: Reinstall Python and tick "Add Python to PATH"

### Issue: Selenium not installing
**Solution**: Open Command Prompt as Administrator and run:
```bash
python -m pip install --upgrade selenium
```

### Issue: CAPTCHA auto-fill fails
**Check**: Look at `udin_autofill_debug.png` in the project folder for debugging screenshot

### Issue: ICAI login fails
**Check**: 
- Verify username format: `MEMBERSHIP_NO@icai.org`
- Confirm password is correct
- Check ICAI website is accessible: https://udin.icai.org/ICAI/login

### Issue: Form doesn't auto-fill
**Solution**: Run `RECORD_ICAI_STEPS.bat` to record new steps for your workflow

---

## 📁 File Locations & Portability

**Important**: Your data is saved in the `StockStatementData` folder next to this tool.

To move the tool to another computer:
1. Copy the entire project folder
2. The `StockStatementData` folder moves with it
3. All your client data, profiles, and settings come along

---

## 🔐 Security Notes

⚠️ **Be Careful**:
- `profiles.json` contains your ICAI credentials in **plain text**
- Keep this file **SECURE** and **BACKED UP**
- Never share this file with unauthorized persons
- Consider encrypting sensitive data in production use

---

## 📌 ICAI Compliance

✅ This tool is designed to assist CAs in compliance with:
- ICAI guidelines for UDIN (Unique Document Identification Number)
- Stock Statement audit requirements
- Drawing Power Certificate generation
- Banking regulations for credit audits

⚠️ **Disclaimer**: This tool is a **helper application**. Final certificate submission and UDIN generation happens through the **official ICAI portal**. CAs remain responsible for all submitted documents.

---

## 🎓 For Beginners (Step-by-Step)

If you're new to this tool, follow these steps:

1. Read `DOCUMENTATION.md` (detailed process guide)
2. Check `DATA_STRUCTURE.md` (understand your data format)
3. Run the tool with test client first
4. Refer to troubleshooting section if any issue

---

## 🤝 Support & Maintenance

For technical issues:
- Check the `udin_autofill_debug.png` screenshot
- Review step recordings in `StockStatementData/recordings/`
- Run `RECORD_ICAI_STEPS.bat` to capture your specific workflow

---

## 📝 Version Info

4. Add a clear title and project description.
5. Click **Create pull request**.
The parser recognizes the following formats:

### GST e-Invoice Signed QR

A three-part token whose first part matches the expected base64url-safe pattern is treated as a signed e-invoice QR.

The payload is base64url-decoded, parsed as JSON, and—when a `data` property contains a string—parsed again.
- **Tool Version**: V21 (Fixed)
- **Last Updated**: August 2026
- **Python Requirement**: 3.7+
- **Selenium Version**: Latest (auto-updated)

Common fields are given friendly labels:

## ✨ Features Roadmap

Future enhancements:
- [ ] Batch UDIN generation for multiple clients
- [ ] Excel import/export for client data
- [ ] PDF certificate download automation
- [ ] Email notification system
- [ ] Data encryption for credentials
- [ ] Web-based interface (non-browser dependent)

---

## 📞 Contact & Credits

**Developer**: Atul Talaviya (CA, ICAI Member #159692)  
**Firm**: Shapy & Associates  
**ICAI FRN**: 124286W  
**Tool Purpose**: AICA Level 2 Capstone Project  

---

| Source key | Display label |
|---|---|
| `Irn` | IRN |
| `IrnDt` | IRN Date |
| `SellerGstin` | Seller GSTIN |
| `BuyerGstin` | Buyer GSTIN |
| `DocNo` | Invoice No |
| `DocTyp` | Doc Type |
| `DocDt` | Invoice Date |
| `TotInvVal` | Total Invoice Value |
| `ItemCnt` | Item Count |
| `MainHsnCode` | Main HSN |

Nested JSON objects are flattened into spreadsheet-friendly field names.

### JSON

QR content beginning with `{` or `[` is parsed as JSON and flattened.

### UPI Payment QR

QR content beginning with `upi://` is parsed using these labels:

| Parameter | Display label |
|---|---|
| `pa` | Payee VPA |
| `pn` | Payee Name |
| `am` | Amount |
| `tn` | Note |
| `tr` | Ref |

### URL

QR content beginning with `http://` or `https://` is classified as a URL.

### Key-Value Text

Text split by newlines or `|` characters is treated as key-value data when at least half of the lines match a `key: value` or `key=value` pattern.

### Plain Text

Anything else is returned as text under the `Text` field.

## QR Detection

The scanner uses:

- `BarcodeDetector` with `qr_code` format when supported.
- `jsQR` with inversion attempts enabled.
- Otsu thresholding for an enhanced scan.
- Full-image scanning followed by reduced-size regional scans.
- Two reduction factors: 2 and 4.
- Overlapping crop regions to locate QR codes anywhere on a page.

## PDF Processing

PDFs are loaded with PDF.js.

Each page is:

1. Retrieved from the PDF.
2. Rendered at scale 3.
3. Scanned for a QR.
4. If necessary, rendered again at scale 5.
5. Recorded as either `Found` or `No QR found`.

The UI reports progress in the form `page X/Y`.

## Image Processing

Images are loaded through an object URL.

Large images are scaled down while preserving aspect ratio, with the largest dimension capped at 4200 pixels.

The resulting image is drawn to a canvas and scanned for a QR code.

## Excel Export

Found results are exported to an Excel workbook named:

`qr-invoice-data.xlsx`

The workbook contains a single sheet:

`QR Data`

Each row includes:

- File
- Page
- Status
- QR Type
- Every discovered parsed field
- Raw QR Data

Columns are automatically sized within reasonable minimum and maximum widths.

## User Interface

The interface includes:

- Offline/privacy indicator.
- Invoice QR → Excel heading.
- Drag-and-drop upload area.
- File browser.
- Download Excel button.
- Clear button.
- Scan status.
- Results table.
- Expand/collapse control for rows containing more than four fields.

Rows visually distinguish successful scans, errors, and unsuccessful scans.

## Privacy

The page states that all scanning happens locally in the browser and that files are never uploaded.

## External Dependencies

The HTML references these browser-side libraries from jsDelivr:

- `jsQR` 1.4.0
- `pdfjs-dist` 4.8.69
- `xlsx` 0.18.5

Although the application performs file processing locally, the current HTML imports these dependencies from external CDN URLs.

## Key Functions

- `flatten()` — recursively converts parsed objects into flat fields.
- `parseQr()` — detects the QR content format and parses it.
- `otsu()` — applies grayscale Otsu thresholding.
- `scanData()` — runs `jsQR`, optionally with enhancement.
- `native()` — attempts native browser QR detection.
- `scanCanvas()` — combines native, jsQR, enhancement, and regional scanning.
- `imageCanvas()` — loads and scales image files into a canvas.
- `scanPdf()` — renders and scans every PDF page.
- `scanFile()` — dispatches PDF or image processing.
- `exportExcel()` — creates the Excel workbook.
- `render()` — updates the results table and controls.
- `handle()` — processes selected files and updates progress.

## Generated Output

Successful scans are displayed in the table with:

- Source file
- Page number
- QR type
- Parsed fields

The complete decoded QR payload is retained as `Raw QR Data` for Excel export.
**Last Modified**: August 26, 2026  
**Status**: ✅ Production Ready
