# Rex & George Document Toolkit v10.20

**Submitted by:** CA Augustne Rex  
**Project type:** Offline Windows desktop document-processing application  
**Version:** 10.20 Professional Plus

## Problem Statement

Professionals frequently use separate applications for PDF, Word, Excel, OCR, image extraction, webpage capture and digital-signature work. This increases processing time, software dependency, cost and confidentiality risk.

## Solution

Rex & George Document Toolkit provides these functions in one professional desktop application. Documents are processed locally, with visual previews and simple workflow controls.

## AI Integration

The application uses AI-assisted OCR through RapidOCR and ONNX Runtime to recognise text in scanned documents and image-based PDFs. OCR runs locally without uploading confidential documents to an external service.

## Key Features

- Merge, split, compress, protect, unlock and organise PDFs
- Visual PDF page manager with reorder, rotate, duplicate and delete controls
- Merge Word documents and arrange rendered pages
- Merge Excel workbooks with visual worksheet ordering
- Extract selected embedded PDF images with filtering and contact sheets
- Convert PDF, Word, Excel and image formats
- OCR scanned documents and image-based PDFs
- Preview documents before processing
- Create visible signatures and certificate-based PDF signatures
- Capture webpages as documents using a bundled browser
- Offline processing with no Python requirement for setup users

## Working / Demo

1. Open the application and select the required document tool.
2. Add the relevant PDF, Word, Excel or image files.
3. Preview, select, reorder or configure the required options.
4. Process the files and save the output locally.

## Windows Installer

The compiled installer is larger than GitHub's 100 MB single-file limit and is therefore provided separately:

**[Download Rex & George Document Toolkit v10.20 Offline Setup](https://drive.google.com/file/d/17VfaXRD4b3QVydPmHkHj8wbDdpp9sy1f/view?usp=sharing)**

The installer is intended for 64-bit Windows 10/11. Python is not required on the client's computer.

## Run From Source

1. Download and extract `RexGeorgeDocumentToolkit_v10_20_Source.zip` from this project folder.
2. Install Python 3.12 on Windows.
3. Open the extracted folder and install the dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   python -m playwright install chromium
   ```

4. Start the application:

   ```powershell
   python RexGeorgeDocumentToolkit_v10_20.pyw
   ```

## Business Impact

- Reduces time spent switching between document utilities
- Improves document-processing consistency and accuracy
- Protects client confidentiality through local processing
- Reduces recurring dependence on multiple paid applications
- Provides a user-friendly workflow for professional offices

## Privacy

The project does not contain client documents, credentials, passwords, API keys or confidential datasets. Users should test document outputs before relying on them in production.
