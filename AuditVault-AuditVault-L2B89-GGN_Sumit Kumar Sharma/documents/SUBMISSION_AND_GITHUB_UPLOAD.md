# Submission and GitHub Upload Instructions

## ICAI capstone submission

1. Use the prepared `AuditVault-MA014784-AICA-Level-2.zip` file.
2. Confirm that the ZIP remains below 100 MB.
3. Record a project-demonstration video showing your face and the technical content.
4. Upload the video to YouTube in unlisted mode or to Google Drive with access enabled for anyone with the link.
5. Submit the ZIP and accessible video link through the form prescribed by ICAI within the applicable deadline.
6. Retain the upload-confirmation message or screenshot.

## GitHub fork and pull-request workflow

1. Sign in to GitHub and open `https://github.com/aiinicai/AICA-Level-2-Projects`.
2. Select **Fork** and create a copy under your own GitHub account.
3. Clone your fork:

   `git clone https://github.com/YOUR-USERNAME/AICA-Level-2-Projects.git`

4. Copy the complete `AuditVault-MA014784` folder into the cloned repository.
5. Confirm that there is no nested `.git` directory inside the project folder.
6. Commit and push:

   `git add .`

   `git commit -m "Add AuditVault - AICA Level 2 project"`

   `git push origin main`

7. On GitHub, select **Contribute** and **Open pull request**.
8. Confirm that the base repository is `aiinicai/AICA-Level-2-Projects`, the base branch is `main`, and the comparison repository is your fork.
9. Use a clear pull-request title and briefly describe AuditVault.

Suggested pull-request title:

`Add AICA Level 2 Project - AuditVault - MA014784`

Suggested description:

`AuditVault is a role-based internal audit engagement and working-paper management application built with Python, Streamlit, SQLAlchemy, and SQLite. It covers client and engagement setup, team assignment, RCM import and testing, evidence versioning, observations, review queries, audit completion, consolidated archival, and audit-trail reporting.`

## Safety check

Before committing, verify that none of the following are included:

- `auditvault.db`
- `AuditVault_Data/`
- `.env`
- `.streamlit/secrets.toml`
- `__pycache__/`
- Real client information or evidence
- Files larger than 100 MB
