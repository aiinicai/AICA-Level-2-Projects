# Upload Your Project Folder to the AICA Level 2 Projects Repository

**Target repository:** [aiinicai/AICA-Level-2-Projects](https://github.com/aiinicai/AICA-Level-2-Projects)

This guide explains how to contribute your complete project folder to the **AICA-Level-2-Projects** repository using GitHub’s **Fork + Pull Request** workflow.

Two methods are covered:

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

Replace `YOUR-USERNAME` with your GitHub username.

## Step 2: Upload Your Project Folder

GitHub provides two ways to add a folder through the website.

### Option A: Drag and Drop the Complete Folder

1. Open your fork of the repository.
2. Click **Add file** → **Upload files**.
3. Open the parent location of your project folder in File Explorer.
4. Drag the **complete project folder**—not only the files inside it—into GitHub’s upload area.
5. Wait until all the files appear in the upload list.

Modern browsers such as Google Chrome and Microsoft Edge generally preserve the folder structure during upload.

### Option B: Create the Folder Using a File Path

1. Open your fork of the repository.
2. Click **Add file** → **Create new file**.
3. In the filename box, enter:

   ```text
   MyProjectName/README.md
   ```

   Typing `/` in the filename automatically creates the folder.

4. Add a short description of your project to the new `README.md` file.
5. Click **Commit changes**.
6. Open the newly created folder.
7. Click **Add file** → **Upload files** and upload the remaining project files.

Replace `MyProjectName` with the name of your project.

## Step 3: Commit the Upload

1. Scroll down to the **Commit changes** section.
2. Enter a clear commit message, for example:

   ```text
   Add <Your Name> - <Project Name> project folder
   ```

3. Keep **Commit directly to the main branch** selected.
4. Click **Commit changes**.

Because this is your personal fork, committing directly to its `main` branch is acceptable for this submission workflow.

## Step 4: Open a Pull Request

1. Return to the main page of your fork.
2. GitHub may display a banner stating:

   ```text
   This branch is X commits ahead of aiinicai:main
   ```

3. Click **Contribute** → **Open pull request**.

Alternatively:

1. Open the **Pull requests** tab.
2. Click **New pull request**.

Before creating the Pull Request, confirm the following direction:

| Setting | Selection |
| --- | --- |
| Base repository | `aiinicai/AICA-Level-2-Projects` |
| Base branch | `main` |
| Head repository | `YOUR-USERNAME/AICA-Level-2-Projects` |
| Compare branch | `main` |

Then:

1. Enter a clear Pull Request title, for example:

   ```text
   Add AICA Level 2 Project - <Your Name>
   ```

2. In the description, briefly explain:
   - The purpose of your project.
   - Its main features.
   - Any setup or usage instructions.
3. Click **Create pull request**.

## Step 5: Wait for Review and Merge

The owner of the `aiinicai/AICA-Level-2-Projects` repository will receive your Pull Request.

The repository owner may:

- Review your project.
- Ask questions.
- Suggest changes.
- Approve and merge the Pull Request.

If changes are requested, update the files in your fork and commit them. Your existing Pull Request will update automatically.

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

## QR Parsing

# Method 2: Git Command Line

This method is recommended when:

- Your project contains many files.
- You want to upload the complete folder structure reliably.
- You are comfortable using Git commands.

## Prerequisites

Before beginning:

- Install [Git](https://git-scm.com/downloads).
- Create or log in to your GitHub account.
- Fork the [AICA-Level-2-Projects repository](https://github.com/aiinicai/AICA-Level-2-Projects) as explained in Method 1.

## Step 1: Clone Your Fork

Open Terminal, Command Prompt, PowerShell, or Git Bash and run:

```bash
git clone https://github.com/YOUR-USERNAME/AICA-Level-2-Projects.git
```

Then open the cloned repository:

```bash
cd AICA-Level-2-Projects
```

Replace `YOUR-USERNAME` with your GitHub username.

## Step 2: Copy Your Project Folder

Copy your complete project folder into the cloned `AICA-Level-2-Projects` directory.

Recommended folder naming format:

```text
YourName-ProjectName/
```

Example:

```text
Rahul-Sharma-AI-Invoice-Analyzer/
```

## Step 3: Review the Changes

Run:

```bash
git status
```

Confirm that Git lists only the files and folders you intend to submit.

## Step 4: Stage and Commit the Project

Stage your project folder:

```bash
git add YourName-ProjectName/
```

Commit the changes:

```bash
git commit -m "Add <Your Name> - <Project Name> project folder"
```

## Step 5: Push the Changes to Your Fork

Run:

```bash
git push origin main
```

Your project folder will now appear in your fork on GitHub.

## Step 6: Open a Pull Request

1. Open your fork on GitHub.
2. Click **Contribute** → **Open pull request**.
3. Confirm the base and compare repositories:

| Setting | Selection |
| --- | --- |
| Base repository | `aiinicai/AICA-Level-2-Projects` |
| Base branch | `main` |
| Head repository | `YOUR-USERNAME/AICA-Level-2-Projects` |
| Compare branch | `main` |

4. Add a clear title and project description.
5. Click **Create pull request**.
The parser recognizes the following formats:

### GST e-Invoice Signed QR

A three-part token whose first part matches the expected base64url-safe pattern is treated as a signed e-invoice QR.

The payload is base64url-decoded, parsed as JSON, and—when a `data` property contains a string—parsed again.

Common fields are given friendly labels:

## Before Submitting

Please verify the following:

- Your complete project is inside one clearly named folder.
- Your folder includes a `README.md` explaining the project.
- The project does not contain passwords, API keys, access tokens, or other confidential information.
- Unnecessary generated files and dependency folders are excluded where applicable.
- The project opens or runs using the instructions included in its `README.md`.
- Your Pull Request targets `aiinicai/AICA-Level-2-Projects` on the `main` branch.

## Need to Update Your Submission?

If your Pull Request is still open, make the required changes in the same fork and branch, then commit and push them. GitHub will automatically add the new commits to the existing Pull Request.

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
