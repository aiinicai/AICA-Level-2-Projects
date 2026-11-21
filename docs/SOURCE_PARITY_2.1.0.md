# Bounded2.1.2 acceptance patch

Actual Linux2.1.1 GUI passed compact header/footer, pinned asset Save and valuer
scrolling, Firm wheel, stable Paper/Orientation, whole-page watermark/footer
preview, second import5assets3,126,200, SaveAs/Open and all3export dialogs.
Remaining actionable issues: selected tab geometry/wheel, preview initial bounds,
Report actions far down form, Cancel reset and unconditional clean-case warning.
2.1.2 patches ONLY these, with headless regressions; fresh GUI retest is pending.
No file-dialog typing/performance fix is claimed.

Actual2.1.1 GUI output files were inspected for content, not only existence:
JSON2applicants/5assets, assets3,126,200, annual620,000; XLSX cached same; Word
certificate separates immovable3,050,000 +movable76,200 from annual620,000 and
uses behind-text artwork; PDF6pages contains both financial totals and full
850x1200 artwork. XLSX contains full artwork and printed-header VML. Native
Office rendering still has no runtime verification. See GUI_ACCEPTANCE_2.1.1.md.

# 2.1.1 GUI acceptance repair addendum

2.1.0 actual Linux acceptance passed wide-window listed workflows but failed
1024x578 layout: footer hidden, squeezed asset editor, clipped header; settings
wheel and first print-control focus also failed.2.1.1 replaces root pack priority
with a weighted grid/pinned footer, compact two-row header, deterministic Window
size control, one continuous Assets form with pinned actions, routed child-field
wheel events and no canvas focus stealing. Current desktop retest is PENDING.

Whole-page mode now preserves all pixels, not only cropped bands. PDF uses a
full-page background; Word uses page-relative behind-text anchors; Excel uses
printed header VML picture backgrounds rather than unprinted sheet backgrounds.
PDF actual image rendering and Word/Excel XML/media are tested; native Office
background rendering remains unverified. Header-image mode remains once per
Excel sheet. Prior crop-only JSON needs original artwork re-selection.

The actual gui_case.json/gui_export files from2.1.0 were inspected:2applicants,
5assets, assets3,126,200 and separate income620,000; PDF6pages; old PDF image
bands850x141 and850x81. The old850x1200 fixture intentionally had white centre
and gold footer; crop-only implementation additionally lost any middle artwork.
The new full-page fixture has a large central SAMPLE watermark and strong footer.

# Source-to-UI-to-output audit — 2.1.0

## What was actually opened (read only)

All three XLSM sources were read in formula and cached-value views with openpyxl.
All seven sheets in each, including hidden SUMMARY and Sheet1, outside-print
cells, merges, defined names, bold/number formats, styled empty cells, row heights
and column widths were inspected. No macros or VBA UDFs ran. Privacy-safe full
coordinate inventories are in reference_structure_2.1.0.json; literal personal
values and cached financial values are deliberately omitted there.

| Reference | Populated cells | Formulas | Populated bold cells | Outside print | Broken #REF formulas |
|---|---:|---:|---:|---:|---:|
| DOUBLE (8cade…xlsm) |459|143|168|9|12|
| SINGLE (328eb…xlsm) |426|135|162|9|8|
| FILE WITH ITR (c858…xlsm, 93,624 bytes) |418|140|161|6|6|

All three have SUMMARY, Sheet1, intro, certificate, immovable, movable, annual
income; no defined names. The newly accessible c858… reference supersedes the
previously missing ba0df… attachment. Do not describe the current ITR reference as
unavailable. The real ITR PDF (130055…pdf, 473,931 bytes) was also read locally.
No actual client source file or extracted private text is included in this ZIP.

## Ground-truth financial wording / mapping

| Source cell / semantic | Screen and model | Excel / Word / PDF implementation |
|---|---|---|
| Sheet1 B3/B4 and B7: applicants, title, passport, address; C3 spouse/father formula | Applicants; stable Person IDs, fields, parent override, formula mode | Source-style Sheet1 and linked intro/certificate; all applicants in narrative, identity lines in ownership. Full passport metadata in hidden Sheet1 K:N outside A:I print area; raw OCR only JSON |
| DOUBLE C3 spouse-first, SINGLE/new ITR A13 Mrs suppression | Visible Report line and formula warnings; father override | Source modes and explicit review, not guessed gender. See FORMULA_REVIEW |
| Owner C column and following bold relationship line | Owner selector, Relationships confirmation, asset table + complete detail | All annexures show owner, applicant-specific confirmed family link and owner's own S/o/D/o/W/o separately. Unknown relation is pending, not invented; second applicant context preserved |
| Immovable B11 bold nature; B12 measure regular; B13 location regular | Asset name; area/details/address | asset_details.template_lines produces distinct lines with corresponding emphasis in all three formats |
| Immovable B14 bold '(Valued by [firm]'; B15 licence bold | Architect/valuer name/firm, licence; reviewed source extraction | Valuer/firm and licence in immovable particulars. No fictitious qualifications; supplied report date/reference/source notes are additional user/original-app fields |
| Movable B12 Cash in Hand bold; B13 self declaration regular | Cash inline + owner/value/name | '(As per Self Declaration by Party)' and separate owner/relation, not a bank/gold generic row |
| Movable bank / FD A/c No bold; next line source-date note regular | Bank name, account identifier, as-on date, evidence type; explicit owner | '[bank] Bank A/c No. [id]' / FD variant; '(As Per Bank [Fd] Certificate/Statement as on [date])'. Real identifier only when supplied; examples synthetic |
| Movable Gold Valuation bold; jeweller and as-on note regular | Gold/Jewellery name, valuer/jeweller, valuation date, source details | 'Gold Valuation'; '(As Valued by [jeweller] as on [date])'. Weight, purity/rate are OPTIONAL only if supplied; not mandatory template fields and never fabricated |
| Certificate E18/F18 and E19/F19; E20/F20 asset sums | Grouped Assets and subtotal footer | Immovable and movable separate annexures/totals in all three exports. XLSX uses linked formulas. Word/PDF certificate has parallel INR/selected FX columns, separate group rows and net total |
| Source ROUND(INR/rate,0) per row then SUM | Report country/currency/date, INR-per-unit label | Decimal rate retained, per-row Excel-compatible rounding then sum; true cached results written to own generated XLSX formulas; Word/PDF same arithmetic |
| New certificate E28/F28 link annual D28/E28, E29/F29 annual totals | ITR & income; explicit applicant/year/source review | Separate annual summary and Annexure C in all three formats. No income in asset/net-asset total. New workbook's first+second block total retained and mislabeled income caption repaired |
| Annual PAN bold; acknowledgement, date, FY/AY regular; bold owner/relation | Evidence metadata, report AY, reviewed taxable/agriculture/other exempt | Source wording and metadata included in annual blocks. Reviewed additional components and provenance explicitly identified; no duplicate ITR+computation income |
| Signer/date/UDIN block, firm identity, original-app logo | Firm settings, signature toggle, custom letterpad; Report date and UDIN | Selected signer snapshot only. Portable JPEG/PNG signature with aspect preserved in Excel/Word/PDF. App author's credit does not become a client-report signer |
| Source print ranges, A4, bold row structure | Expandable Print layout: paper/orientation/margins/sections/A1 ranges | Actual XLSX page setup, DOCX dimensions and PDF dimensions. Preview rasterizes the exact exported PDF; it is not Excel/Word's layout engine |

Excel row anchors follow source structure: asset headers9/group10, immovable
first11, movable first12; annual header11/group12/first14; certificate E18:E20
and parallel F, annual E28/F28. Additional data uses dynamic blocks rather than
copying fixed sample rows or stale identities. Liabilities are an explicit
extension (Annexure D), never annual income. Excel template identity emphasis is
fixed policy; Word/PDF identity bold toggles remain user-controlled. Supporting
source detail lines preserve regular versus bold; not every cell is bold.

## Actual sample ITR PDF findings (no private amounts reproduced)

Six physical pages. Readable acknowledgement sections for AY2025-26 (page1) and
AY2024-25 (page4); readable computation AY2024-25 on pages5–6. Pages2–3 had no
selectable text and this box lacked an OCR engine; incomplete-read warnings are
retained. Three readable tax sections are extracted independently rather than
merging different years. The computation's unrounded total differs from the
acknowledgement's statutory rounded total; both remain evidence and divergence
is flagged, not silently overwritten. The sample filing date uses a month-name
format, now normalized. Missing agriculture/exempt income is unknown, not zero.

Variable professional computation layouts are parsed by contextual labels and
nearby lines/table rows, not screen coordinates. Row codes1A/2, deductions,
taxes, refund/bank amounts and later subtotals do not become annual income.
Reconciliation lets the reviewer choose taxable total and independent additional
agriculture/other exempt sources for the SAME person/year, with overlap checks.
Actual source-specific extraction was checked privately; public regressions clone
its structure with synthetic figures/IDs. J-Form additions found in the workbook
are evidence of a non-ITR source, not proof of an automatic tax-law calculation;
such additions require deliberate reviewed input.

## Original Python operational feature comparison

Both uploaded Python versions were reopened and inspected, not inferred from UI
screenshots. The 178KB app is the retained library foundation (legacy_engine.py).
The 86KB predecessor was compared as well. Thirteen original item categories,
CA profile concept, asset fields, original narrative, local extraction helpers,
resource discovery and Windows build helper are retained/adapted.

| Original capability | Actual source | 2.1.0 status |
|---|---|---|
| Background currency fetch | newer fetch_exchange_rate, lines2435–2459; latest-only exchangerate-api.com/v4/latest/{code}, rounds2dp | Restored background flow with explicit failures; date-capable Frankfurter public endpoint for requested date; original eight currency codes retained; full rate precision |
| Country list | Neither supplied .py has an explicit country function/variable; destination mapping was currency-driven | Explicit country dropdown added for original currencies with currency override. Not a world-country catalogue |
| Selenium UDIN | newer trigger_udin_generation3131–3164 and Selenium3166–3603 | Restored visible-browser assistance using original selectors/navigation; no live verification. Older86KB AST has no corresponding helper |
| UDIN fields | FRN, source's misspelled certficateType, dd-mm-yyyy, Particulars/Figures in INR, Actual, Details of document, Generate UDIN navigation | Mapped with bounded waits/events, readiness and missing-field messages; Selenium fake-DOM tests cover successful mapping and mismatch |
| Auto Send OTP | newer lines3558–3565 | Deliberately safer explicit user action, one request/cooldown; OTP/final generation user-controlled; no serialized login/OTP |
| Logo/letterhead | logo_path in both originals | Retained fallback plus portable custom image/one-page PDF letterpad. JPEG/PNG signature is a new distinct feature, not falsely attributed to original |
| Original Excel report organization | SINGLE/DOUBLE templates are report standard | Source-style dynamic XLSX plus matching semantic fields/groups in Word/PDF; original practitioner narrative retained |
| Case/edit state | original JSON variants, name-linked ownership | Explicit versioned case JSON, stable IDs, guarded migrations, save/open/save-as, portable images, edits/provenance; secret keys stripped |
| Import errors / ambiguous assets | old empty proposal could dead-end | Editable asset draft/manual amount/candidates, explicit owner matching/create review, append preservation, remove/undo with edit protection |

Original source entrypoints are disabled inside legacy_engine.py so users cannot
accidentally launch the obsolete GUI. The public app entrypoint is net_asset_report.py.

## Deliberate limits and not-yet-verified items

- No Windows 3.14 / current desktop runtime or built EXE proof for2.1.0; parent
  desktop QA should test at1024x578 and1280x800. Typography/layout is implemented,
  not a claim of fresh visual verification. Headless PDF output pages were rendered
  and inspected; that is report-file QA, not GUI QA.
- A row has one explicit owner; fractional/joint co-owner allocations from some
  source examples are not a full multi-owner financial model. Do not duplicate a
  full property value merely to represent a second owner.
- No live UDIN portal login, OTP request or final generation. Original source
  selectors may change; missing selectors stop safely for manual completion.
- FX daily reference observations are not guaranteed valuation spot quotes. When
  provider date differs, explicit acceptance is required. Future rate is not
  fetched. Manual rates remain labelled unverified. No silent today fallback.
- Header-image Excel artwork remains once per worksheet; whole-page artwork now
  uses repeating print-header VML pictures. Office-native rendering is unverified.
  PDF/Word repeat full backgrounds/header artwork. PDF preview does not render Excel A1 print areas or
  Word's own pagination. Whole-page letterpad is now the full behind-text image, not arbitrary
  template placeholders; inspect your actual letterpad before issuing.
- OCR is optional external local software; the box could not read sample scanned
  pages2–3. Unknown image/vendor layouts and uncertain OCR require human review.
- No automatic tax advice or guaranteed net agriculture/exemption policy. The
  user chooses additional reviewed income without overlap; income remains separate.
- JSON embeds selected images, not original source PDFs. Deleted/moved source
  paths prevent re-reading until reselected but preserve reviewed case evidence.
- No automatic external sharing, printer submission, arbitrary architect signing,
  credential storage or macro execution. Original client files are not packaged.
