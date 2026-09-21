# How to test SurakshaScan yourself

Five stages, each one proving something different. Do them in order — if an
early one fails, the later ones will fail confusingly.

Commands are written for Windows PowerShell. On macOS or Linux, replace
`.venv\Scripts\activate` with `source .venv/bin/activate`.

---

## 1. Set it up (five minutes)

Unzip the project, then open a terminal **in the SurakshaScan folder**:

```powershell
cd path\to\SurakshaScan
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

You should see `(.venv)` at the start of your prompt. If `python` is not
recognised, install Python 3.11 or later from python.org and tick **Add
python.exe to PATH** during installation.

Three of the packages are optional and may fail on some machines —
`anthropic`, `pymupdf`, `keyring`, `mcp`. The tool runs without any of them
and will tell you what it skipped. Only the first six in `requirements.txt`
are required.

**Proves:** the environment is sound.

---

## 2. Run the test suite (thirty seconds)

```powershell
pytest tests -q
```

Expect **29 passed**. If pytest did not install, use:

```powershell
python tests\run_tests.py
```

which runs the same 29 tests with a small bundled substitute.

These touch no network at all — they run against HTML fixtures in
`tests/fixtures/`. Four of them exist purely to prove the AI layer cannot
assert something the policy does not say.

**Proves:** the logic is correct and reproducible.

---

## 3. Run the self-test (one minute)

```powershell
python -m surakshascan.tools.demo
```

This serves a deliberately bad fixture school on localhost, runs the complete
pipeline against it, and writes all three reports to `output_reports/`.

Expected output:

```
  Score 7/100 (Critical)
  Coverage 66% of the catalogue
  13 gaps, 2 partly met, 10 not assessed

  [x] advertising pixel
  [x] insecure form action
  [x] sensitive form fields
  [x] no policy page found

  Self-test passed.
```

Now open the three files in `output_reports/` and look at them properly:

- **`Sample_DPDP_Readiness_Report.docx`** — check the donut chart shows 7,
  the bar chart is sorted worst-first, the remediation table is ordered by
  score gain, and section 3 has the two side-by-side perspective panels.
- **`Sample_DPDP_Workings.xlsx`** — seven sheets. Check **Remediation** has
  blank Owner / Target date / Done columns for a school to fill in, and that
  **Evidence log** lists every URL fetched with its HTTP status.
- **`Sample_DPDP_Dashboard.html`** — open in a browser. Narrow the window to
  phone width; it should collapse to one column. View source and confirm
  there is no `<script src=` anywhere — it must be fully self-contained.

**Proves:** the whole pipeline works and the outputs are what you'd hand a
principal.

---

## 4. Run the desktop app (ten minutes)

```powershell
python run.py
```

Things worth deliberately trying, because these are the behaviours a judge
will poke at:

| Try this | What should happen |
|---|---|
| Click **Run the review** with both fields blank | A "Missing information" warning, not a crash |
| Enter a name and `https://example.com`, run it | The Activity log fills in, the score appears top-right, the app stays responsive throughout |
| Go to **Working paper**, pick a line, set Status to Completed, Save, **without** filling the Reviewer name on the Scan tab | Refused, with "a reviewer name is required before a line is marked Completed" |
| Fill the Reviewer name, then Save that line again | Accepted, and a neutral remark appears naming you and today's date |
| Mark eight or ten lines, then **Re-score with the working paper** | The score and the coverage figure both move |
| Open **Findings**, click any row | The lower panel shows the provision, the evidence and the remediation |
| Open **Two views** | Every gap has an institution panel and a Board panel |
| Go to **Reports**, save all three formats | Three files, and it offers to open each one |

**Proves:** the interface holds up under someone who is not you.

---

## 5. Run it against a real school

Only a school that has authorised you in writing. The tool obeys robots.txt
and never logs in, but authorisation is a professional matter, not a technical
one.

```powershell
python -m surakshascan.cli scan `
    --name "Little Flower House Senior Secondary School" `
    --url https://littleflowerhouse.com `
    --docx report.docx --xlsx workings.xlsx --html dashboard.html --verbose
```

Then read the report **against the site itself**, which is the real test:

- Did it find the privacy policy, if there is one? If the site has one and the
  scan missed it, that is a bug worth telling me about.
- Are the trackers it lists actually on the page? Check in Chrome with F12 →
  Network.
- Are the form fields it flagged as sensitive really being asked for?
- Does any finding say something you know to be wrong?

That last question is the one that matters. A compliance tool that is
confidently wrong is worse than no tool.

**Proves:** it works on the messy real thing, not just on a fixture.

---

## Optional: with the AI layer

Only if you want to demo it. Set the key first — it is never stored by the
app:

```powershell
$env:ANTHROPIC_API_KEY = "sk-..."
python -m surakshascan.cli scan --name "X" --url https://x.edu.in --ai --docx r.docx
```

Then open section 6 of the Word report. Check that:

- every accepted finding carries a quotation, and
- you can find that exact quotation in the school's actual policy page.

If any accepted finding quotes something that is not on the page, that is a
serious bug and the report should not go out until it is fixed.

Without a key, the report says plainly that the AI layer did not run. It never
prints a placeholder and calls it analysis — that was the v1 failure this
version exists to correct.

---

## Optional: build the executable

```powershell
pyinstaller SurakshaScan.spec
```

`dist\SurakshaScan.exe` is the result. **Test it on a machine with no Python
installed** — a build that works only on the build machine is the usual first
bug, and it is the one that bites during a demo.

---

## If something breaks

- `ModuleNotFoundError` → the virtual environment is not active. Re-run
  `.venv\Scripts\activate`.
- The scan finds nothing and reports errors → check the site is reachable in a
  browser, and read the `robots.txt` line in Appendix A of the report.
- Charts fail to render → matplotlib did not install cleanly; reinstall it.
- The window freezes → it should not; the scan runs on a worker thread. If it
  does, note what you were doing, because that is a real bug.
