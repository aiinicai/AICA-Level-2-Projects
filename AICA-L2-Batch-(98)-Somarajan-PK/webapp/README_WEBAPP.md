# Web app (AICA Module 7)
For the Tally pull panel, start the connector (`start_tool.bat`) and use the page it opens. Opening `index.html` directly still works for sample data and CSV/JSON upload, but the Tally panel is disabled (browsers cannot reach Tally without the connector).
1. **Load sample data** - two synthetic banks; pick a bank in the dropdown.
2. **Own data** - choose `tally_export\tally_bank_books.json` (from tally_extract.py). A bank dropdown appears (Current Assets > Bank Accounts). Upload that bank's statement CSV and press Reconcile. Alternatively upload a Bank books CSV instead of the Tally file.
Bank opening can be left blank: it is derived from the first statement balance.
`index.template.html` is the source; `python build.py` re-embeds the sample; `node test_webapp.js` checks it against the Python engine.
