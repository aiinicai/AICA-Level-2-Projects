SME GSTAT AppealKit - PROFESSIONAL v0.6.2 PORTABLE
===================================================

HOW TO OPEN
1. Extract the complete ZIP to a normal folder.
2. Double-click START_SME_GSTAT_AppealKit.bat.
3. The application opens in Microsoft Edge, Google Chrome or the default browser.

NO INSTALLATION REQUIRED
- Internet is not required to use the application.
- PDFs and images are processed locally in the browser.
- Do not install Python or any PDF library.

THE SIMPLE WORKFLOW IS UNCHANGED
1. Case
2. Documents
3. Annexure & Pagination
4. Stamp & Signature
5. Preview & Generate

PROFESSIONAL v0.6.2 CORRECTIONS
- “Prepared by” is optional and is hidden unless its checkbox is selected.
- Clearing the Prepared by field no longer restores a hidden default in the PDF.
- Subject justification uses a safe spacing limit; sparse lines remain naturally left aligned.
- The final line and every paragraph-ending line remain naturally left aligned.
- Long unbroken references, IDs and pasted text wrap inside the cover and master-index margins.
- Master-index pagination now reserves space according to the actual case-title length.
- A crowded first page no longer silently suppresses the subject.

PROFESSIONAL v0.6.1 FEATURES RETAINED
- First-page text size can be Small, Normal or Large.
- The case-title paragraph uses smart justification in the generated cover.
- Order date prints as DD-MMM-YYYY.
- Drag documents by the handle to rearrange; Up/Down buttons remain available.
- Automatic mixed numbering supports 1, 2, 3 followed by A1, A2, A3.
- Annexure checking captures complete multi-digit references including Anx12 and Anx123.

PROFESSIONAL v0.6.0 FEATURES RETAINED
- A compact header, slim private/offline message and denser professional layout.
- On mobile, the five workflow steps scroll horizontally instead of taking five rows.
- Page-range selection accepts examples such as 1-5, 8, 12-15, all, odd and even.
- Select many pages and rotate, include/exclude or move them together.
- Preview jump list opens an annexure directly in the correct volume and physical page.
- Optional Draft review mode adds a visible DRAFT - FOR REVIEW mark. It does not lock the PDF.
- Optional actual-size check warns when a generated PDF exceeds the chosen MB guide.
- Optional filing reminders remain collapsed and never block generation.

CURRENT GSTAT PORTAL GUIDANCE BUILT INTO THE DEFAULTS
- The official Help Centre presently advises files not above 20 MB and scans at 300 DPI or less.
- Multiple volumes may be uploaded where required.
- The v0.6 size check is advisory because portal requirements may change.
- The application measures the actual generated PDF size; it does not silently downsample evidence.
- Always confirm the current limit shown on the filing portal before filing.

CORE FEATURES RETAINED
- Exact-preview PDF bytes are reused for final generation when nothing has changed.
- Complete master index in every volume, with internal and cross-volume links.
- Dynamic index rows and full particulars without intentional silent truncation.
- Reversible page editor; original source bytes remain unchanged.
- Optional chronology, issue-wise CSV and appeal-to-annexure reference checking.
- Editable cover, annexure formats, continuous pagination, themes and layout styles.
- Visible stamp/signature images and text stamps, clearly distinguished from DSC.
- Signed originals are kept separately in the generated package.
- Audit manifest records page mapping, actual bytes and SHA-256 where available.
- Portal Upload Map CSV lists each generated PDF, pages, MB, stage, size result and hash.

FINAL VERIFICATION
Open every generated volume in Adobe Acrobat Reader and verify:
- every index entry, page range, bookmark and cross-volume link
- edited order, excluded pages, rotation and document completeness
- page numbers, Return to Index, annexure labels, stamps and Draft mark if used
- actual file sizes against the current portal requirement
- online and any service/physical copy match exactly

Visible signature/stamp placement is not a cryptographic DSC. Copying pages from a
digitally signed source into a new paper book does not preserve signature validity.
Keep and file the unchanged signed original wherever required.

Do not file generated documents without manual review.

OFFICIAL REFERENCES CHECKED FOR THIS RELEASE
- GSTAT Help Centre / FAQ: https://efiling.gstat.gov.in/helpInner.drt
- GSTAT Appeal Filing User Manual: https://efiling.gstat.gov.in/downloads/manual/manual.pdf
- GSTAT portal: https://efiling.gstat.gov.in/
- W3C visual-presentation guidance: https://www.w3.org/WAI/WCAG21/Understanding/visual-presentation.html
- pdf-lib font measurement API: https://pdf-lib.js.org/docs/api/classes/pdffont
