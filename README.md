# Ind AS 116 — Lease Accounting Suite

A modular, GUI-based lease accounting model for Chartered Accountancy
practices, covering **Day-0 measurement** of the Right-of-Use (ROU)
asset and Lease Liability under **Ind AS 116**, plus month-wise
liability amortisation and ROU depreciation schedules.

## Requirements
- Python 3.9 or later
- Tkinter (ships with standard Python installers on Windows/macOS; on
  some Linux distributions install via `sudo apt install python3-tk`)

All other third-party packages (`pandas`, `openpyxl`,
`python-dateutil`) are detected and installed **automatically the
first time you run the app** — you will see a live installation log
window while this happens. This only happens once per machine.

## Running the application
```
python main.py
```

## What it does
1. **Lease Inputs tab** — enter monthly rental, lease term, escalation,
   payment timing (advance/arrears), the Interest Rate Implicit in the
   Lease (or Incremental Borrowing Rate if not determinable), initial
   direct costs, incentives, restoration costs, etc.
2. **Run Model** computes:
   - Lease Liability at Day 0 = PV of unpaid lease payments
   - ROU Asset at Day 0 = Lease Liability + prepaid rentals + initial
     direct costs − incentives + PV of restoration costs
   - Month-wise lease liability amortisation (effective interest method)
   - Month-wise ROU depreciation (straight-line over the lease term)
3. **Export to Excel** — saves all schedules to a multi-sheet workbook
   suitable for client working papers.
4. **Save/Load Template** — save a lease's input set as a `.json` file
   so recurring engagements (e.g. annual re-runs, similar leases across
   branches) can be reloaded instantly instead of re-keyed.

## Project structure (for maintenance)
```
ind_as_116_suite/
├── main.py                  Entry point (run this)
├── README.md
└── ind_as_116/
    ├── __init__.py           Package metadata
    ├── bootstrap.py          First-run dependency detection & install
    ├── models.py             LeaseInputs / LeaseResult data structures
    ├── engine.py             All Ind AS 116 calculations (no I/O)
    ├── excel_export.py       Excel workbook export
    └── gui.py                Tkinter GUI (install log + main window)
```

The calculation engine (`engine.py`) is fully decoupled from the GUI —
it can be imported and run headlessly (e.g. from a script that batch-
processes many client leases from a CSV, or from a future web/CLI
front-end) without any Tkinter dependency:

```python
from datetime import date
from ind_as_116.models import LeaseInputs
from ind_as_116.engine import LeaseEngine
from ind_as_116.excel_export import export_to_excel

inputs = LeaseInputs(
    lease_commencement_date=date(2025, 4, 1),
    lease_term_months=60,
    monthly_rental=100000,
    incremental_borrowing_rate_annual=0.10,
)
result = LeaseEngine(inputs).run()
print(result.summary)
export_to_excel(result, "lease_model.xlsx")
```

## Key accounting reference
Ind AS 116 (Leases) — lessee recognition and initial measurement:
the Right-of-Use asset is measured at cost, and the lease liability
at the present value of lease payments not paid at the commencement
date, discounted using the interest rate implicit in the lease if
readily determinable, or otherwise the lessee's incremental
borrowing rate.

## Notes on assumptions built into this model
- Depreciation is charged straight-line over the full lease term. If
  the underlying asset's useful life is shorter and ownership does not
  transfer, adjust `build_depreciation_schedule()` accordingly.
- Variable lease payments (not based on an index/rate), sublease
  accounting, and lease modification/reassessment are **not** yet
  modelled — flagged here so future maintainers know the current scope
  boundary.
- All amounts are assumed to be in a single currency (no FX translation
  built in).

## Extending this suite
Because the engine, GUI, and export layers are separate modules,
common extensions are isolated to one file each:
- New calculation logic (e.g. lease modifications) → `engine.py`
- New input fields → add to `LeaseInputs` in `models.py` and to the
  `FIELDS` list in `gui.py`
- New export formats (e.g. PDF working paper) → new module alongside
  `excel_export.py`
# INNFLOW — Enterprise Hotel Operations & Management Ecosystem
**AICA Level-2 Capstone Project**  
**Author:** CA Ankit Tandon  
**Target Industry:** Hospitality, Hotel Property Management & Internal Financial Controls
# Upload Your Project Folder to the AICA Level 2 Projects Repository

**Target repository:** [aiinicai/AICA-Level-2-Projects](https://github.com/aiinicai/AICA-Level-2-Projects)

This guide explains how to contribute your complete project folder to the **AICA-Level-2-Projects** repository using GitHub’s **Fork + Pull Request** workflow.

Two methods are covered:

1. **Website-only method** — no software installation required.
2. **Git command-line method** — recommended for complete project folders and projects containing many files.

---

## Fork + Pull Request Workflow

1. **Fork:** Create a personal copy of `aiinicai/AICA-Level-2-Projects` under your GitHub account.
2. **Add your folder:** Upload or copy your project folder into your fork.
3. **Commit:** Save the changes in your fork with a clear commit message.
4. **Open a Pull Request:** Request the `aiinicai` account to merge your changes into the original repository.
5. **Merge:** The repository owner reviews and accepts your Pull Request. After it is merged, your project folder will appear in the official repository.

---

# Method 1: Website Only

Use this method if:

- You do not want to install Git.
- Your project contains relatively few files.
- You do not need to preserve the project’s earlier commit history.

> [!NOTE]
> GitHub’s web uploader generally allows up to 100 files in a single upload. If your project contains more files, upload them in batches or use the Git command-line method.

## Step 1: Fork the Repository

1. Log in to your GitHub account.
2. Open the [AICA-Level-2-Projects repository](https://github.com/aiinicai/AICA-Level-2-Projects).
3. Click **Fork** in the upper-right corner of the page.
4. On the **Create a new fork** page, keep the default settings.
5. Click **Create fork**.

You will be redirected to your personal copy of the repository:

```text
https://github.com/YOUR-USERNAME/AICA-Level-2-Projects
```

Replace `YOUR-USERNAME` with your GitHub username.

## Step 2: Upload Your Project Folder

GitHub provides two ways to add a folder through the website.

### Option A: Drag and Drop the Complete Folder

1. Open your fork of the repository.
2. Click **Add file** → **Upload files**.
3. Open the parent location of your project folder in File Explorer.
4. Drag the **complete project folder**—not only the files inside it—into GitHub’s upload area.
5. Wait until all the files appear in the upload list.

Modern browsers such as Google Chrome and Microsoft Edge generally preserve the folder structure during upload.

### Option B: Create the Folder Using a File Path

1. Open your fork of the repository.
2. Click **Add file** → **Create new file**.
3. In the filename box, enter:

   ```text
   MyProjectName/README.md
   ```

   Typing `/` in the filename automatically creates the folder.

4. Add a short description of your project to the new `README.md` file.
5. Click **Commit changes**.
6. Open the newly created folder.
7. Click **Add file** → **Upload files** and upload the remaining project files.

Replace `MyProjectName` with the name of your project.

## Step 3: Commit the Upload

1. Scroll down to the **Commit changes** section.
2. Enter a clear commit message, for example:

   ```text
   Add <Your Name> - <Project Name> project folder
   ```

3. Keep **Commit directly to the main branch** selected.
4. Click **Commit changes**.

Because this is your personal fork, committing directly to its `main` branch is acceptable for this submission workflow.

## Step 4: Open a Pull Request

1. Return to the main page of your fork.
2. GitHub may display a banner stating:

   ```text
   This branch is X commits ahead of aiinicai:main
   ```

3. Click **Contribute** → **Open pull request**.

Alternatively:

1. Open the **Pull requests** tab.
2. Click **New pull request**.

Before creating the Pull Request, confirm the following direction:

| Setting | Selection |
| --- | --- |
| Base repository | `aiinicai/AICA-Level-2-Projects` |
| Base branch | `main` |
| Head repository | `YOUR-USERNAME/AICA-Level-2-Projects` |
| Compare branch | `main` |

Then:

1. Enter a clear Pull Request title, for example:

   ```text
   Add AICA Level 2 Project - <Your Name>
   ```

2. In the description, briefly explain:
   - The purpose of your project.
   - Its main features.
   - Any setup or usage instructions.
3. Click **Create pull request**.

## Step 5: Wait for Review and Merge

The owner of the `aiinicai/AICA-Level-2-Projects` repository will receive your Pull Request.

The repository owner may:

- Review your project.
- Ask questions.
- Suggest changes.
- Approve and merge the Pull Request.

If changes are requested, update the files in your fork and commit them. Your existing Pull Request will update automatically.

After the Pull Request is merged, your project folder will become part of the official repository.

---

# Method 2: Git Command Line

This method is recommended when:

- Your project contains many files.
- You want to upload the complete folder structure reliably.
- You are comfortable using Git commands.

## Prerequisites

Before beginning:

- Install [Git](https://git-scm.com/downloads).
- Create or log in to your GitHub account.
- Fork the [AICA-Level-2-Projects repository](https://github.com/aiinicai/AICA-Level-2-Projects) as explained in Method 1.

## Step 1: Clone Your Fork

Open Terminal, Command Prompt, PowerShell, or Git Bash and run:

```bash
git clone https://github.com/YOUR-USERNAME/AICA-Level-2-Projects.git
```

Then open the cloned repository:

```bash
cd AICA-Level-2-Projects
```

Replace `YOUR-USERNAME` with your GitHub username.

## Step 2: Copy Your Project Folder

Copy your complete project folder into the cloned `AICA-Level-2-Projects` directory.

Recommended folder naming format:

```text
YourName-ProjectName/
```

Example:

```text
Rahul-Sharma-AI-Invoice-Analyzer/
```

## Step 3: Review the Changes

Run:

```bash
git status
```

Confirm that Git lists only the files and folders you intend to submit.

## Step 4: Stage and Commit the Project

Stage your project folder:

```bash
git add YourName-ProjectName/
```

Commit the changes:

```bash
git commit -m "Add <Your Name> - <Project Name> project folder"
```

## Step 5: Push the Changes to Your Fork

Run:

```bash
git push origin main
```

Your project folder will now appear in your fork on GitHub.

## Step 6: Open a Pull Request

1. Open your fork on GitHub.
2. Click **Contribute** → **Open pull request**.
3. Confirm the base and compare repositories:

| Setting | Selection |
| --- | --- |
| Base repository | `aiinicai/AICA-Level-2-Projects` |
| Base branch | `main` |
| Head repository | `YOUR-USERNAME/AICA-Level-2-Projects` |
| Compare branch | `main` |

4. Add a clear title and project description.
5. Click **Create pull request**.

---

## Before Submitting

Please verify the following:

- Your complete project is inside one clearly named folder.
- Your folder includes a `README.md` explaining the project.
- The project does not contain passwords, API keys, access tokens, or other confidential information.
- Unnecessary generated files and dependency folders are excluded where applicable.
- The project opens or runs using the instructions included in its `README.md`.
- Your Pull Request targets `aiinicai/AICA-Level-2-Projects` on the `main` branch.

## Need to Update Your Submission?

If your Pull Request is still open, make the required changes in the same fork and branch, then commit and push them. GitHub will automatically add the new commits to the existing Pull Request.

