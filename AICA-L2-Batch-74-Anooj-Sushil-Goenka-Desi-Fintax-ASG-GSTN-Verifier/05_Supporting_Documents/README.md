# Desi Fintax ASG GSTN Verifier

Windows desktop application for GST supplier registration and GSTR-3B filing verification, invoice aggregation, evidence preservation, and professional reporting.

**Desi Fintax — CA Anooj Sushil Goenka**  
Mobile: **9833049094** | WhatsApp: **9028593321**

## Safeguards

- GSTIN is normalised and checksum-validated before verification.
- One supplier row is maintained per project/GSTIN; invoice data remains at invoice level and is aggregated supplier-wise.
- Re-verification creates history and never overwrites prior results.
- Public verification first attempts a hidden official-page session. Edge opens only when the GST Portal blocks hidden rendering or requires login/CAPTCHA. Login, CAPTCHA and MFA/OTP remain manual; GSTIN entry, result capture, evidence PDF and queue advancement are automatic after the portal accepts the search.
- Authorised GSP/API integration is optional and hidden unless enabled. No provider is required for portal-assisted use.
- GSTR-3B filing is not represented as proof of invoice-wise payment of tax.

## Run and build

For normal use, double-click `START_DESI_FINTAX_ASG_GSTN_VERIFIER.bat`, open the EXE under `Standalone EXE`, or install the application using the Setup EXE under `Installer`. These routes do not require Python.

For source development only, install standard 64-bit Python 3.12/3.13 and Microsoft Edge, run `setup_windows.bat`, then `run_app.bat`. Run `build.bat` for a PyInstaller one-folder EXE. Compile `installer.iss` with Inno Setup.

Data is stored under `%LOCALAPPDATA%\DesiFintax\ASGGSTNVerifier` and preserved during upgrades/uninstall. Test the installer on clean Windows 10 and 11 machines without Python.

## Portal workflow

Choose the active client project, then click **Start Automatic Verification**. The app inserts each GSTIN and processes the selected FY. If CAPTCHA appears, enter it and submit it once for that search; capture, evidence PDF and the next queued GSTIN continue automatically. The GST Portal controls whether CAPTCHA repeats. Supported FYs run from FY 2017-18 through the ongoing FY.
