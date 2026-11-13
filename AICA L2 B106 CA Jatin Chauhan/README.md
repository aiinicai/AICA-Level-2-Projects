# TaxReady

**Know your tax before you file.** *By CA Jatin Chauhan*

TaxReady is a Windows desktop tool (one Python file, PyQt6) that gives a client an **early estimate of the tax payable**, so the client is ready for the payment and has time to arrange the funds.

> **Estimate for information only; not tax advice. Verify against the official Income Tax portal and consult a CA before filing. TaxReady never files anything.**

## The problem and the objective

- **Problem:** clients are often not prepared for the tax amount they have to pay.
- **Objective:** make the client ready for tax payment and give the client time to arrange funds.

## What it does

1. **Downloads the AIS** (Annual Information Statement) from the official Income Tax e-Filing portal in a visible Chrome / Edge window. You complete the CAPTCHA - it is never bypassed.
2. **Decrypts it locally** using the client's PAN and date of birth.
3. **Computes a tentative tax review** - income by head, capital gains (sale value less purchase cost per transaction), deductions, old vs new regime, rebate, surcharge, cess and taxes already paid.
4. **Saves only a Word report** in the client's folder. The downloaded and decrypted AIS files are deleted.
5. **Emails the report** to the client through Gmail (optional) - after you review and, if needed, edit the computation, or automatically.

## Features

- **Single Client** and **Batch - multiple clients** tabs (batch runs ticked clients one after another and ends with a results table).
- **Review and edit before emailing** - classifications, missing purchase costs, deductions, house property, presumptive or books-based business income, property sale, brought-forward losses; totals update instantly.
- Income reported through both TDS and SFT is counted once; *Inactive* AIS rows are excluded by default.
- Local client register (SQLite) with CSV import / export and an activity history (with *Clear history*).
- A designed HTML email with the key figures, nine colour themes and an **About & Help** tab.

## Documentation

**[User manual (PDF)](docs/TaxReady_User_Manual.pdf)** - a 28-page guide covering installation, setup, single and batch runs, the review window, the Word report, the email, how the figures are worked out, privacy and troubleshooting. An editable copy is in `docs/TaxReady_User_Manual.docx`.

Keep the `docs` folder next to `TaxReady.py` and the **Open the user manual** button on the About & Help tab will open the manual.

## Requirements

- Windows 10 / 11 (saved passwords use Windows DPAPI)
- Python 3.11 or newer (tested on 3.14)
- Google Chrome or Microsoft Edge
- Internet access for the portal and, if used, Gmail

## Install and run

Libraries are installed automatically on the first run. To install them yourself:

```bash
pip install PyQt6 playwright python-docx matplotlib pycryptodome
```

```bash
python TaxReady.py
```

(or open the file in IDLE and press **F5**). No Playwright browser download is needed - TaxReady uses the Chrome / Edge already installed.

## Quick start

1. **Gmail Settings** (only to email reports): turn on 2-Step Verification in your Google account, create an App Password at <https://myaccount.google.com/apppasswords>, enter the sender address and the 16-character App Password, click *Save & Verify Gmail*.
2. **Single Client:** enter the client's name, PAN, e-Filing password, date of birth and email, then *Save client* (or use *Import CSV* with the columns `Client Name, PAN, Email, Date of Birth, Password, Download Folder`).
3. Choose the **Financial Year** and the download folder, then click **Download AIS & Prepare Tax Review** and complete the CAPTCHA when Chrome / Edge opens.
4. Check or edit the figures in the review window, then **Send email**.

The report is saved as `<folder>\<PAN>\<financial year>\XXXXX1234F_2025-26_AIS_report.docx` (masked PAN in the file name).

## Privacy and security

- Everything runs on your computer; data goes only to the official portal and the optional Gmail message.
- Saved portal passwords and the Gmail App Password are encrypted with Windows DPAPI and are never logged or exported.
- The temporary browser profile, downloaded AIS and decrypted data are deleted after every run (if processing fails, the downloaded file is kept so the portal download need not be repeated).
- Client data is stored in `%APPDATA%\AIS Auto Downloader\clients.db`. **Never commit client data or reports to a public repository.**

## Known limitations

- **Tax rates and thresholds were entered from public sources and are marked `VERIFY`** - check them against the Finance Act before relying on any figure.
- Interest under sections 234A / 234B / 234C and the 234F fee are not computed.
- Debt mutual funds, unlisted shares and property sales use a best-effort section mapping; grandfathering is not applied.
- Windows only; if the portal changes its page layout the download step may need updating.

## Disclaimer

Provided "as is", without warranty. It produces a preliminary working paper from AIS data only - not a filed return, tax advice or a professional opinion.

## License

No license has been chosen yet, so by default all rights are reserved. Add a `LICENSE` file before others are allowed to reuse the code.
