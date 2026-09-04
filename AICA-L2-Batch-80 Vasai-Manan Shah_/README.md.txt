ICFR Testing AI Assistant v1.1.6 — Revised Build / EXE Notes
==============================================================

FUNCTIONAL CHANGES
------------------
1. Save Auditor Evaluation now performs database read-back verification and shows a success/failure confirmation.
2. Test-result approval is persisted with:
   - auditor_approved
   - auditor_approved_by
   - auditor_approved_at
3. Approvals survive a Run Tests re-run when the evidence-driven facts remain unchanged.
4. If evidence-driven facts materially change, the stale approval is intentionally reset and audit logged.
5. Final control conclusion cannot be approved until all ACTIVE test steps are auditor-approved.
6. Working Paper generation is locked until all ACTIVE test steps are auditor-approved.
7. Working Papers include approval status, approver and approval timestamp for each test step.
8. Reports has been removed from the sidebar and source feature set.
9. Save confirmations were strengthened for Control, manual Response, Exception and Auditor Evaluation; existing confirmations remain for Inquiry, Standard Steps, Custom Steps and Settings.

DATA PRESERVATION
-----------------
APP_SLUG remains DigiLens_IFCR_Testing.
The application continues to use the existing local workspace:
    %LOCALAPPDATA%\DigiLens_IFCR_Testing

The database migration is non-destructive. It only adds two nullable test_steps columns:
    auditor_approved_by
    auditor_approved_at

Inquiry, response, evidence, testing and exception rows/files are not deleted, copied, reset or relocated.
A guest who enters Local Demonstration Mode in the same Windows user workspace sees the same existing local audit database, with actions attributed to the guest identity in the audit trail.

LEAN EXE STRATEGY
-----------------
The v1.1.6 source removes unused ReportLab and Matplotlib dependencies.
The dashboard chart is implemented using Tkinter Canvas instead of Matplotlib/Numpy.
The PyInstaller spec excludes Matplotlib, Numpy, ReportLab and other unused scientific/notebook packages.
Only Tesseract English OCR traineddata (eng.traineddata) is bundled, not the full language pack.

This is intended to materially reduce the prior ~124 MB EXE. Actual final size depends on the Python, PyInstaller, Tcl/Tk, Pillow, pywin32 and Tesseract builds installed on the Windows build machine. The build script reports the exact final size and SHA-256. A sub-100 MB result is the target, not an absolute guarantee.

BUILD
-----
1. Put these files in one folder:
   ICFR_Testing_AI_Assistant_v1_1_6.py
   ICFR_Testing_AI_Assistant_v1_1_6_LEAN.spec
   requirements-exe-v116.txt
   BUILD_WINDOWS_EXE_v1_1_6.bat
2. Verify local OCR:
   where tesseract
   tesseract --version
   tesseract --list-langs
3. Double-click BUILD_WINDOWS_EXE_v1_1_6.bat (or Run as Administrator if your environment requires it).
4. Output:
   dist\ICFR_Testing_AI_Assistant_v1_1_6.exe

EXTERNAL MACHINE DEPENDENCIES
-----------------------------
- Outlook features require Classic Outlook Desktop/profile on the machine.
- Legacy .xls/.doc extraction requires Microsoft Excel/Word Desktop.
- OpenAI features require internet and an API key configured for that user.
- Modern local testing, .xlsx/.pdf/.docx/.csv/.txt evidence, Working Papers and bundled English Tesseract OCR do not require a separate Python or Tesseract installation on the guest machine.
