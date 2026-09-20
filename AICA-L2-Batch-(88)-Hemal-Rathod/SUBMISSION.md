# ICAI AICA Level 2 — Capstone submission

Source: **AI for Chartered Accountants-Level-2, Ver 5.0**, Annexure D (page 18), and the
submission Google Form itself.

> **Supersedes an earlier version of this file.** That version was written from
> `AICA_Level2_Ver1.pdf` and said GitHub was optional and a ZIP file was the submission
> route. **Ver 5.0 reverses this.** GitHub is now the submission route and there is no ZIP
> upload. If you read the earlier note, disregard it.

---

## What ICAI requires

| # | Requirement | Detail |
| --- | --- | --- |
| 1 | **Upload the project to GitHub** | Fork + Pull Request into `aiinicai/AICA-Level-2-Projects` |
| 2 | **Folder name** | `AICA-L2-Batch-(XXX)-Name-Surname` — brackets included. This project: **`AICA-L2-Batch-(88)-Hemal-Rathod`** |
| 3 | **Record a video** | Must show **your face** *and* the technical content |
| 4 | **Host the video** | YouTube **unlisted**, or Google Drive — link accessible to anyone |
| 5 | **Fill the Google Form** | <https://forms.gle/cucnBGn34bVHFaxt9> |
| 6 | **Deadline** | Within **10 days** of batch completion. The form then expires and no submission is accepted. |

Marks: 30, passing 15.

**No ZIP file is uploaded anywhere.** The Google Form asks for a GitHub URL, not a file.

---

## What the Google Form asks for

Have all of this ready before you open it:

1. Email
2. Your name
3. **Batch number** — numeric only (**88**, Ahmedabad)
4. **Membership number**
5. Phone number
6. Registered email ID
7. **Title of the project**
8. **Description of the project**
9. **Video link** — YouTube unlisted or Google Drive
10. **GitHub project URL**
11. Declaration (tick)

### Suggested title

> Tax Audit Applicability Decision System — Section 44AB, Income-tax Act 1961

### Suggested description

> A deterministic, offline decision system that determines whether tax audit under section
> 44AB applies for FY 2025-26 (AY 2026-27), and produces the working paper evidencing the
> conclusion. It evaluates all five limbs of s. 44AB together with the first proviso, the
> s. 44AD and s. 44ADA presumptive ceilings and the s. 44AD(4) five-year bar, then states
> the limb relied on with the statutory text and its source. Where a fact is missing it
> asks for exactly that fact rather than guessing. Every threshold was verified against the
> Gazette texts of the Finance Act 2023, Finance (No. 2) Act 2024 and Finance Act 2025;
> that verification found eight errors in the first AI-assisted draft, two of which would
> have produced a wrong "no audit" conclusion. The application makes no AI calls at run
> time and sends no data anywhere. AI was used during development to structure the logic,
> draft explanations and generate test cases — never to supply the law.

---

## Note on the declaration

The form's declaration assigns the project to ICAI and permits ICAI to publish it. Read it
before ticking. Two consequences worth understanding as a practising CA:

- **The repository is public.** Anything committed is visible to anyone, permanently, and
  remains in Git history even if deleted later.
- **No client data may appear anywhere in it.** This project contains none: all 12 sample
  cases are synthetic and no real PAN or client name appears. Keep it that way.

---

## Upload procedure — Fork + Pull Request

Per Annexure D. **Your folder is the only thing you touch.** The repository holds ~100
other participants' folders; never modify or delete anything at the root.

### Step 1 — Fork

Open <https://github.com/aiinicai/AICA-Level-2-Projects> → **Fork** → **Create fork**.
You get `https://github.com/YOUR-USERNAME/AICA-Level-2-Projects`.

### Step 2 — Add your folder

In **your fork**: **Add file** → **Upload files**, then drag **the folder itself** (not the
files inside it) onto the upload area. Chrome and Edge preserve the structure.

### Step 3 — Commit

Commit message: `Add AICA-L2-Batch-(88)-Hemal-Rathod - Tax Audit Applicability Decision System`
Keep "Commit directly to the main branch" — it is your fork, so this is safe.

### Step 4 — Pull Request

On your fork: **Contribute** → **Open pull request**. Check the direction:

- base = `aiinicai/AICA-Level-2-Projects` (main)
- compare = `YOUR-USERNAME/AICA-Level-2-Projects` (main)

Title: `Add AICA Level 2 Project - Hemal Rathod`. Then **Create pull request**.

### Step 5 — Wait for merge, then submit the form

Once ICAI merges, your folder appears in the official repository. Put the GitHub URL in the
Google Form along with the video link.

You can submit the form with your **fork's** folder URL without waiting for the merge — the
PR is the request; the merge is ICAI's action.

---

## ⚠ Do not do this

**Never push your local project repository's history to the fork.** Its history is
unrelated to the 636 commits upstream. Git will reject it, and forcing it would delete
every other participant's work. Use the web upload above, or the Git method in Annexure D
which clones the fork first.

**Do not copy a `.git` folder into your project folder.** Git would treat it as a submodule
and none of your files would upload. The prepared folder has none.

---

## Checklist before you submit

- [ ] Folder named `AICA-L2-Batch-(88)-Hemal-Rathod`
- [ ] `README.md` present inside the folder
- [ ] No `.git` folder inside
- [ ] No file above 100 MB
- [ ] No client data, no real PAN, no API keys
- [ ] Pull request opened against `aiinicai/AICA-Level-2-Projects`
- [ ] Video recorded with face visible **and audio working** — test it before recording
- [ ] Video uploaded, link set to "anyone with the link"
- [ ] `01_PROJECT_SUMMARY.pdf` re-exported from the current version
- [ ] CA sign-off completed in `legal/sources.md` §6 and `caSignOff` in `app/js/ruleset.js`
- [ ] Google Form submitted within 10 days of batch completion
