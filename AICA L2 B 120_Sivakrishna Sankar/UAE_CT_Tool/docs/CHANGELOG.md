# Changes in this version (bug-fix and rework pass, 19 Oct 2026)

Found by stress-testing the tool (GUI driven with an exception hook, malformed and regional-format files, odd trial balances):

1. **CSV files with a title row failed to load** ("Expected 5 fields ..."). CSV reading is rewritten: delimiter detected (, ; tab |), ragged rows allowed, UTF-8/UTF-16/Windows encodings.
2. **European and other number styles were misread silently** (1.234,56 became 1.23456; space or apostrophe thousands separators). Now read correctly: 1,234.50 / 1.234,50 / 1 234,50 / 1'234.50 / 1234,5 / unicode minus / currency codes.
3. **Changing the currency after an analysis left the old results (and Export) unlocked.** Later steps now lock until the new currency is confirmed.
4. **Choosing a header row by hand did nothing** when automatic detection had failed. Fixed (also two-row headings), with a clear message if the row is not a heading.
5. **A post-closing TB (no income/expense accounts) produced nil profit and nil tax with no warning.** New failed check FS-04.
6. **UAE bank names (Emirates NBD, ADCB, Mashreq, FAB, RAKBANK ...) were not recognised as cash/bank** and fell to a default line.
7. **Damaged / empty / password-protected files** now give a plain message instead of a Python error.
8. **File names**: Arabic company names are kept (were reduced to "Entity"); Windows reserved names handled.
9. **Review workbook** showed answers the user had accepted as "Unanswered"; now "Answered / confirmed".
10. **Cosmetics**: "-0" in the Word report; ".;" in the Small Business Relief note; trial balance currency label now follows the confirmed currency; AED can be chosen on the first page (earlier fix).

Added: sample trial balance `sample_data/marjan/` with a hand-calculated example (`docs/MARJAN_WORKED_EXAMPLE.md`), 23 new tests (83 in total).
