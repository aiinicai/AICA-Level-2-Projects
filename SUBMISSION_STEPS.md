# Submission Steps for GitHub

Target repository: https://github.com/aiinicai/AICA-Level-2-Projects
Your folder to upload: `Ritesh-Dedhia-Vendor-Name-Matching`

This follows Method 2 (Git command line) of the Upload Guide. Replace `YOUR-USERNAME` with your GitHub username.

## Before you start

- Git is installed (https://git-scm.com/downloads).
- You have a GitHub account. For the first push, Git asks for your username and a **Personal Access Token** as the password: GitHub, Settings, Developer settings, Personal access tokens, Generate new token (classic), tick the `repo` scope.

## Steps

1. **Fork.** Open https://github.com/aiinicai/AICA-Level-2-Projects and click **Fork**, then **Create fork**.
2. **Clone your fork** (not the aiinicai repository):
   ```
   git clone https://github.com/YOUR-USERNAME/AICA-Level-2-Projects.git
   cd AICA-Level-2-Projects
   ```
3. **Unzip** the submission package and copy the folder `Ritesh-Dedhia-Vendor-Name-Matching` into the cloned folder (Windows):
   ```
   xcopy /E /I "C:\path\to\Ritesh-Dedhia-Vendor-Name-Matching" "Ritesh-Dedhia-Vendor-Name-Matching"
   ```
   The package contains no `.git` folder, so nothing needs removing.
4. **Check the structure.** You should see `AICA-Level-2-Projects\Ritesh-Dedhia-Vendor-Name-Matching\README.md`.
5. **Commit and push:**
   ```
   git add .
   git commit -m "Add Ritesh Dedhia - Vendor Name Matching project folder"
   git push origin main
   ```
6. **Open the Pull Request.** On your fork's page click **Contribute**, then **Open pull request**. Check that base is `aiinicai/AICA-Level-2-Projects (main)` and compare is your fork `(main)`.

## Ready to paste: Pull Request title

```
Add AICA Level 2 Project - Ritesh Dedhia - Vendor Name Matching
```

## Ready to paste: Pull Request description

```
Project: Vendor Name Matching
Author: Ritesh Dedhia, Chartered Accountant

A desktop tool (Python, PyQt5, openpyxl) that checks the account number and IFSC code in a payment file against an approved vendor master and confirms that the vendor name agrees. Each payment row is marked Matched or Not Matched with a reason, and saved to a new time stamped Excel file.

Highlights:
- Bank details are looked up first, then the name is verified, so a valid account under the wrong name is caught
- Vendor master editing inside the tool, protected by an admin passkey, with bulk upload, download, automatic backups and duplicate prevention
- Fictional demo data with expected results, 43 automated tests, user guide, demo script and a 5 slide presentation

Folder: Ritesh-Dedhia-Vendor-Name-Matching
Start here: README.md
Quick demo: python prepare_demo.py --launch
Run the tests: python tests/test_vendor_name_matching.py
```

## Checklist from the guide

- [ ] Project is inside ONE clearly named folder (`Ritesh-Dedhia-Vendor-Name-Matching`)
- [ ] The folder contains a `README.md`
- [ ] No `.git` folder inside the project folder
- [ ] No file above 100 MB (the whole package is well under 5 MB)
- [ ] Committed to YOUR fork, then a Pull Request opened against aiinicai/AICA-Level-2-Projects
- [ ] PR title and description identify you and your project
