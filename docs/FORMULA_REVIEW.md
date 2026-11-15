# Formula review and intentional corrections — three reference workbooks

See SOURCE_PARITY_2.1.0.md and reference_structure_2.1.0.json for the full
coordinate/type/style/formula/cache-type inventory. All three seven-sheet
workbooks were read in formula and cached views including hidden/outside-print
cells; no macros executed. Real cache values were inspected privately, not
published. All sources have no defined names.

## Identity

Sheet1 B3 chooses the applicant and joins title/name; DOUBLE B7 joins B3+B4.
DOUBLE C3 first selects the Spouse of Applicant and emits W/o Sh.; otherwise
it tests Ms for D/o and uses S/o for other titles. SINGLE and FILE WITH ITR add
an A13 Mrs suppression to the spouse branch. These are imperfect source rules:
Mr may yield W/o and Mrs/Miss father fallback may yield S/o. The default DOUBLE
supplies requested husband precedence; the visible father override is deliberate.
Source mode/warnings preserve auditability rather than guessing sex. Explicit
person relationships are required; matching fathers does not establish brother.

## Financials

- Certificate immovable E18/F18 and movable E19/F19 feed total E20/F20. Liabilities
  have a separate optional net-assets extension; income is never an asset.
- Source foreign row formula is ROUND(INR/rate,0) and totals SUM rounded items.
  All three exporters use this policy with Decimal rate precision. Conversion
  direction is INR per one unit foreign; foreign = INR / rate, not multiplication.
- New ITR certificate E28/F28 link annual income D28/E28, with separate annual
  E29/F29 totals. DOUBLE annual D28=SUM(D20:D27) excludes the first block; new ITR
  SUM(D12:D27) includes both. The app totals all selected reviewed person records
  for one AY, not incomplete fixed ranges.
- New ITR annual B28 says 'Total of Immovable Assets' on the income sheet. It is
  corrected to 'Total annual income'. Source formulas containing literal income
  additions are not shipped as personal financial constants.
- Source broken Sheet1!#REF! ownership formulas are replaced by explicit stable
  owner links, not copied. No source macros/UDFs are embedded; SPELLNUMBERINDIAN
  is replaced with local Python number words.
- Original ITR and computation amounts remain independent evidence. Reviewed
  annual taxable total plus explicitly additional non-overlapping agriculture /
  other exempt values produces the annual row. Missing does not mean zero;
  statutory rounded/unrounded differences are flagged. AY mismatch is not merged.

## Generated files and emphasis

Generated XLSX contains live link/ROUND/SUM formulas AND calculated cached results
for the app's own supported formula set; reopening without recalculation shows
valid totals. openpyxl itself does not calculate formulas; formula_cache.py safely
writes caches for generated expressions, never executes arbitrary source macros
or downloaded formulas. Excel can recalculate on opening.

Separate detail lines preserve source nature/valuer/licence bold and measure /
location regular. Bank/FD and gold wording preserves source notes. Identity /
ownership Excel bold is template policy; Word/PDF narrative identity bold remains
adjustable. Rows are dynamic, not pixel/byte copies of uploaded XLSM samples.

Hidden Sheet1 K:N carries passport metadata outside print A:I. This is intentionally
available for private workbook roundtrip/inspection but is NOT anonymized. Raw
OCR stays in private JSON. Privacy-sensitive files must be shared deliberately.
