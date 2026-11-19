PDF Studio Pro 1.2.0 - how to get the .exe (do this ONCE, on one Windows PC)
=========================================================================
1. Install Python 3.12 (python.org, tick "Add python.exe to PATH"). Python 3.9-3.13 also works.
2. OPTIONAL but recommended - so OCR works on every PC without installing anything:
   install Tesseract (UB-Mannheim build) with the language packs you need (English, Hindi, Marathi ...).
   The build copies it into the program automatically.
   OPTIONAL: create a "fonts" folder here with Noto Sans Indic .ttf files, and/or an admin_settings.json - they are copied in too.
3. Keep this README, build_exe.bat and pdf_studio_pro.py in ONE folder. Double-click build_exe.bat. Wait 10-20 minutes.
   - The build runs in a LOCAL folder (%LOCALAPPDATA%\PDFStudioProBuild), so it works even if this kit
     sits on a network drive. The finished program is copied back next to build_exe.bat.
   - Some steps print nothing for a few minutes. Do not click inside the black window (a click pauses it;
     press Enter if it looks frozen). If your antivirus is slow, let it finish or exclude that folder.
4. Result:   PDFStudioPro_Windows.zip   <- send this to your team
             dist\PDFStudioPro\PDFStudioPro.exe   <- the program itself

FOR YOUR TEAM
  * Right-click the zip > Extract All (do NOT run it from inside the zip), then open the folder and double-click PDFStudioPro.exe.
  * Keep the whole folder together; the exe will not work if copied out alone.
  * If Windows SmartScreen warns ("unknown publisher"): More info > Run anyway. (An unsigned exe always shows this.)
  * Nothing else needs installing. Only the USB digital-signature token needs the token vendor's own driver on that PC.
  * The new tool is under  Edit > Edit PDF  (also a tile on the Home page). See EDIT_PDF_GUIDE.txt.

NEW IN 1.2.0  (see WHATS_NEW_1.2_GUIDE.txt for how to use each one)
  * Compress PDF rebuilt for quality: five quality levels, "Fit under N MB", lossless handling of text / line-art /
    logos / black-and-white scans, and a before/after quality check printed with every result.
  * PDF to PowerPoint now makes EDITABLE slides: real text boxes (font, size, colour, bold, italic), separate pictures,
    lines and tables kept as a background. "Exact picture" is still there as the second choice.
  * AI: Settings > "AI set-up" has ready-made choices (AI on this PC / office gateway with access key / internet AI
    service with your own API key). The messages now say exactly how to become a Prime user.
  * DSC: new "USB token through Windows" mode (no driver file to find), automatic choice of the signing certificate
    on tokens that also hold an encryption certificate, tokens whose driver shows several slots now work,
    several PDFs per run, first / last / numbered page, more token drivers found automatically.

WHAT CHANGED VERSUS YOUR ORIGINAL pdf_studio_pro.py  (original logic untouched; everything is additive)
  * NEW  Edit PDF tool (about 1,200 lines) + Home tiles for Edit PDF / Annotate / Reader; version 1.1.0.
  * find_tesseract(): also looks for  <program folder>\tesseract\tesseract.exe  (the bundled copy).
  * main(): gives print() a harmless target when there is no console window.
  * Closing the program asks first if Edit PDF has unsaved changes.

TESTED HERE (Linux, headless, PyMuPDF 2.1 + PyQt5 5.15, and inside a PyInstaller build made on Linux with the same options):
  * Compress: colour / gray / black-and-white scans, photos, text-only files; all levels; fit-under-size; batch step.
  * PDF to PowerPoint: text, table, picture, rotated text, rotated page, second page size, scanned page with OCR notes;
    the result was opened with LibreOffice and compared with the original page.
  * AI: against a stand-in AI server (key check, model list, providers that refuse max_tokens / temperature).
  * DSC: real signing + verification with a SOFTWARE token (SoftHSM, PKCS#11) holding a signing certificate, an
    encryption certificate and a CA certificate; wrong PIN; .pfx; two signatures on one file; several files.
  * Everything listed for 1.1 (Edit PDF) was run again; all 57 tool pages open.
NOT TESTED - please check on your PC before relying on it:
  * Anything on real Windows: the .exe build, the screens, PowerPoint / Adobe Reader opening the results.
  * "USB token through Windows": the Windows calls that reach the token could not be run here (no Windows, no token).
    The rest of that path (certificate choice, chain, signature format) was tested with a stand-in key.
    If it fails with your token, use "USB token / smart card - PKCS#11 driver file", which was tested with SoftHSM.
  * A real hardware token of any make, and real AI services (LM Studio, Ollama, OpenAI, Gemini).
Run the checklist at the top of pdf_studio_pro.py before sharing widely.
