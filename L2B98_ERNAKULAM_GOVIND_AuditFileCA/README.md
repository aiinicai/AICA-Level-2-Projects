# AuditFile CA — Audit Engagement File Management System

**Version:** 1.1 (Capstone Final)  
**Author:** Govind P  
**Project:** ICAI AI Level 2 Capstone Project

## Overview

AuditFile CA is a locally hosted audit engagement file manager built with Python, Streamlit and SQLite. It provides indexed audit working-paper folders, document version history, preparer/reviewer workflow, review observations, audit trail and engagement reporting. Files and database records are stored on the machine running the application; no cloud document storage is configured.

## Features

* Client and engagement administration, with partner assignment on engagement creation.
* Employee accounts, designation and engagement-level assignments.
* Hierarchical folders, folder rename/move, and deletion of empty folders.
* Automatic folder/working-paper reference indexing based on the parent folder.
* Individual and multiple-file uploads; ZIP import of nested folder hierarchies.
* Working-paper versioning, preparer sign-off and one- or two-level review.
* Reviewer observations, preparer responses, review approvals and engagement finalisation.
* Search, engagement dashboard, audit trail, and export of working-paper/engagement records.

## System requirements

* Windows 11 (the provided `.bat` launchers target Windows).
* Python 3.13 recommended, with the Windows `py` launcher installed.
* Internet connection **for first-time dependency installation only**.
* A modern web browser. The Streamlit application runs locally at `http://127.0.0.1:8501` by default.

## Fresh installation

1. Download this project folder from GitHub and extract it on your Windows computer.
2. Open the project folder and double-click **`setup.bat`**. This creates `.venv`, installs the Python dependencies from `requirements.txt`, and initialises a fresh local SQLite database and `storage` directory.
3. Double-click **`run\_app.bat`** to launch the application.
4. Open the local address printed in the command window (typically `http://127.0.0.1:8501`).
5. On a fresh database, the **First-run administrator setup** screen appears. Choose your own administrator name, username and a password of at least 12 characters. **No default administrator password is included.**
6. Log in, create employee accounts and a client, then create an engagement with a partner assignment. Assign the preparer and required review levels before testing working-paper uploads.

If Windows cannot find Python, install Python 3.13 from python.org, enable the Python launcher, and rerun `setup.bat`. Alternatively, run `py -3 -m venv .venv` followed by `.venv\\Scripts\\python.exe -m pip install -r requirements.txt` and `.venv\\Scripts\\python.exe -m streamlit run app.py --server.address 127.0.0.1`.

## First-time administrator login (important for evaluators)

**There is no preset System Administrator username or password.** The project does not include an existing user database.

On a new installation:

1. Run `setup.bat` once, then `run\_app.bat`.
2. Visit the local URL displayed by Streamlit (normally `http://127.0.0.1:8501`).
3. On the **First-run administrator setup** screen, enter an **Administrator name**, a **Username**, and a **Password of at least 12 characters**.
4. Select **Create administrator account**.
5. Log in using the username and password you just created.
6. Create staff users and clients, then configure an engagement and assign its preparer and reviewers.

**Important:** The administrator setup screen is displayed only when no administrator account exists in the local database. On later launches, use the credentials you created; the application does not supply a shared default password. Keep those credentials safe. Do not upload `auditfile.db` or `storage/` to GitHub.

## Basic workflow

1. **Administrator:** Create employee accounts, client master, engagement and designated partner.
2. **Engagement team:** Configure the preparer and Level 1 / Level 2 reviewers as appropriate.
3. **Preparer:** Create indexed folders, upload a WP (or bulk-import files), sign off and submit it.
4. **Reviewer:** Review the WP; return with an observation or approve.
5. **Preparer:** When a WP is returned, upload a corrected version and **resubmit** it. Closing a review observation alone does not resubmit the WP.
6. **Final reviewer:** Approve at the final configured review level to close the WP.
7. **Assigned partner:** Finalise the engagement when the workflow requirements are satisfied.

## Data storage and privacy

At first run, the application creates these **local** paths in the project folder:

* `auditfile.db` — SQLite database containing users, engagement metadata, review history and audit trail.
* `storage/` — uploaded working-paper files and versions.

Both are excluded by `.gitignore` and **must not be committed to a public repository**. Do not commit client records, passwords, environment secrets or confidential working papers. Passwords are hashed using Argon2. Back up both the database and `storage/` together when the app is not actively being written to.

## Scope and limitations

* This is a capstone demonstration, not a certified audit documentation or document management product.
* The application is configured for local-machine access (`127.0.0.1`). Secure multi-user LAN deployment requires additional network, authentication, access-control and backup review.
* Every engagement must have an assigned partner; manager-only engagement finalisation is outside the current scope.
* Excel workbooks are stored as uploaded versions, not collaboratively edited within the browser. Links between independently downloaded workbooks may not remain valid.
* Bulk ZIP import reproduces folder hierarchy and registers WPs but does not repair Excel external links.
* For professional use, independently assess retention, confidentiality, audit documentation standards and security controls.

## Technology

Python 3.13, Streamlit, `streamlit-antd-components`, SQLAlchemy, SQLite, Argon2, Pandas, OpenPyXL and Altair.

## GitHub submission

This repository contains application source and installation instructions only. The project is intended to be submitted as a single named folder in a fork of `aiinicai/AICA-Level-2-Projects`, followed by a pull request to the original repository.

