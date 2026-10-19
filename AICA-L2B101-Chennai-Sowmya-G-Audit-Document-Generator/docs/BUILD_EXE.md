# Building the Windows program (.exe)

The exe runs on any Windows PC without Python. Choose one way.

## A. On your own PC (simplest)

1. Install Python 3.12 or 3.13 from python.org. Very new versions such as 3.15 may not
   be supported by the packaging tools yet.
2. Double-click `build_exe.bat` in the project folder.
3. After a few minutes the program is in `dist\Audit Document Generator.exe`. Copy it to
   any Windows PC.

## B. Let GitHub build it (no Python needed on your PC)

1. Create your **own private** GitHub repository and upload the project files.
2. Copy `docs/github-workflow/build-exe.yml` to `.github/workflows/build-exe.yml` in
   that repository.
3. Open the **Actions** tab. Every upload starts a build on a Windows machine using
   Python 3.12. The build also **tests** the exe with a dummy MCA PDF before publishing it.
4. Open the run with the green tick. Under **Artifacts**, download
   **Audit-Document-Generator-exe**.

## Using the exe

- **First run:** Windows SmartScreen may show "Windows protected your PC", because the
  program is not code-signed. Click **More info → Run anyway**.
- **Saved documents:** `Documents\Audit Documents\<Company>_FY_<year>\`
- **Confidentiality:** everything runs on the PC. No client data is sent anywhere.
