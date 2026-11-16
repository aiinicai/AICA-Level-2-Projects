# GSTNova

**Offline GST return preparation for e-commerce sellers.**
Import · Validate · File-ready — Version **1.0.0** — Developed by **JD**

GSTNova is a Windows desktop application (Python, PySide6) that turns the reports of Amazon, Flipkart, Meesho and Myntra into a GSTR-1 that is checked, reconciled and ready to upload on the GST portal. It also covers the TDS & TCS credit, IMS, GSTR-2B, GSTR-3B and the cash, credit and liability ledgers. It works offline: all clients and periods are kept in one database on the user's own computer, and no client data is ever sent anywhere.

> GSTNova prepares returns; it files nothing by itself. Every upload and payment is done by the user on the GST portal, and the user must check every figure there.

---

## What it does

| Area | What you get |
|---|---|
| **GSTR-1** | Import of Amazon (MTR), Flipkart, Meesho and Myntra reports, the official GSTR-1 Excel template, or any Excel with column mapping. Review of every table, validation, reconciliation, the JSON for the GST portal, the working Excel file, and portal-error fix. |
| **TDS & TCS credit** | Accept / reject lines, comparison with platform sales, Table 14(a), upload JSON. |
| **IMS** | Accept / reject / pending on records, remarks, JSON of the changed records, "saved on the portal" mark. |
| **GSTR-2B** | Import of the JSON; fills Table 4 of GSTR-3B. |
| **GSTR-3B** | All tables, Table 6.1, interest and late-fee estimate, JSON, working file; PMT-06 for QRMP. |
| **Ledgers** | Cash, credit and liability ledgers, posted from the filed returns. |
| **Control** | One database for all clients and periods, users with an administrator, locks on filed returns, change log, backups. |
| **Licence** | Registration at first start, 3-month trial, yearly licence key per computer, optional licence server. |
| **User manual** | Inside the program: side menu > User manual, or **F1**, with search and Save as PDF. |

---

## Quick start (from source)

Requires **Python 3.12 (64-bit)**.

```bash
pip install -r requirements.txt
python GSTNova.pyw
```

At the first start GSTNova asks for the registration details (licensee name, e-mail id, mobile number, city, State; GSTIN / membership number optional), then creates the administrator (a recovery phrase is shown once), and the 3-month trial begins.

## Tests

```bash
python tests/run_tests.py     # every check must pass before a build
python tests/golden.py        # golden comparison of the generated JSON
```

## Build for sale (Windows)

Needs Python 3.12 (64-bit) and Inno Setup 6.

1. Run the developer tool with `--new-keys` and paste the new **public** key in `gstnova/devunlock.py` (`PUBLIC_KEY`).
2. Optional licence server: set it up with the `SETUP.txt` of the licence-server folder, then fill `gstnova/licence_config.py` (`SERVER_URL`, `SERVER_PUBLIC_KEY`). While both are empty, GSTNova works fully offline and registration stays on the buyer's computer.
3. Read `assets/LICENCE_AGREEMENT.txt` — it is shown by the installer and inside the program.
4. Double-click `build_protected.bat`. It installs the libraries, runs `tools/check_release.py` and the tests, compiles GSTNova with Nuitka, runs the self-test, signs the program when a certificate is given (`SIGN_PFX` / `SIGN_PWD`) and makes `installer_output/GSTNova_Setup.exe`. The first build takes 20–60 minutes.

`build_installer.bat` and `build_exe.bat` (PyInstaller) are for your own trials only, not for sale.

**Keep the developer tool folder (which holds the private key) outside this kit.** The private key must never reach a buyer. Buyers receive only the installer.

## Version

The version is set once in `gstnova/engine.py` (`APP_VERSION`). `installer.iss` and `build_protected.bat` carry the same number, and `tools/check_release.py` stops the build when they differ.

## Project layout

```
GSTNova.pyw                 starts GSTNova
gstnova/                    the program code
  engine*.py                calculations, validation, JSON, data file
  importer.py, reports*.py, myntra.py, othersales.py     reading the reports
  ims.py, tdstcs.py, ledger.py, qrmp.py                  IMS, TDS & TCS credit, ledgers, QRMP
  store.py, auth.py         the database and the users
  licence.py, licence_config.py, registration.py, devunlock.py, ed25519.py
  manual.py                 text of the user manual
  ui/                       the window, the look, one file per page (ui/pages)
assets/                     icons, built-in GST lists, HSN / SAC list, licence agreement, third-party notices
tests/                      the tests and sample data generator
tools/check_release.py      checks before a build for sale
tools/update_gst_lists.py   rebuilds the official lists
build_protected.bat, installer.iss, requirements*.txt     build files
```

## Built with

Python 3.12 · PySide6 (Qt) · SQLite · pandas · openpyxl · Ed25519-signed licence keys · Nuitka (protected build) · Inno Setup (installer) · optional licence server on Cloudflare Workers.

## Demo

A fictitious demo pack (platform reports, TDS & TCS, GSTR-2B and IMS files, a ready demo database, a 5-minute video and its script) is available separately. All names, GSTINs and figures in it are invented. Restoring the demo database replaces all data in that installation — use a spare computer or a fresh installation.

## Please note

- Interest and late-fee figures are estimates from **editable defaults**; confirm them against the notification in force.
- GST facts in the program come from the official GST portal pages (gst.gov.in, tutorial.gst.gov.in).
- IMS import and export has not been tested on real portal files by the developer of this kit; test it on your own files.

## Licence and support

Use of GSTNova is governed by `assets/LICENCE_AGREEMENT.txt`. Third-party components are listed in `assets/THIRD_PARTY_NOTICES.txt`.
Support: cajd19@gmail.com

---

© GSTNova — Developed by JD
