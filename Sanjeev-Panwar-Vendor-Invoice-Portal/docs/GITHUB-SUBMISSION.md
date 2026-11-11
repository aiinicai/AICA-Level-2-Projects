# Fork and pull request submission

Guide target: https://github.com/aiinicai/AICA-Level-2-Projects . No live availability or branch check has been made. Follow any current repository contribution instructions if present, and resolve conflicts with the course organiser.

## Recommended Git method
1. Sign in to GitHub, open the target repository, select Fork, and create your personal fork. Use your own GitHub account; never share its credentials.
2. Clone YOUR fork into a new empty working location, not the running application folder:
```powershell
git clone https://github.com/Sanjeev-Panwar899/AICA-Level-2-Projects.git
Set-Location .\AICA-Level-2-Projects
git branch --show-current
git remote -v
```
Replace Sanjeev-Panwar899 first. Confirm origin points to your fork and the branch matches the target default branch (the guide uses main).
3. Copy ONLY the completed, sanitized Sanjeev-Panwar-Vendor-Invoice-Portal folder into the clone root. Preserve existing repository contents. No nested .git directory or .git file may be present; never delete the clone's root .git. Do not copy any ZIP. The project source folder is the deliverable.
4. Review and stage that folder alone:
```powershell
git status --short
git add -- Sanjeev-Panwar-Vendor-Invoice-Portal
git diff --cached --stat
git diff --cached --name-only
git diff --cached
```
Confirm there are no private files, unrelated modifications or unfinished placeholders. Inspect binary files separately; diff does not show their contents. If a private file was staged, unstage it with `git restore --staged -- path/to/file`, remove it from the copy and fix exclusions before continuing. Do not paste secrets from a diff into chat.
5. Only after review:
```powershell
git commit -m "Add Sanjeev Panwar - Vendor Invoice Portal AICA Level 2 project"
git push origin main
```
Use the verified branch name if different. Follow GitHub's sign-in prompt. Never include tokens in URLs, screenshots, README or commands. If push is rejected, inspect why; do not force-push. Sync your fork safely and resolve conflicts before retrying.
6. In your fork select Contribute > Open pull request, or Pull requests > New pull request. Confirm base repository aiinicai/AICA-Level-2-Projects and base main; head Sanjeev-Panwar899/AICA-Level-2-Projects, compare main (or verified branch names).
7. Title: `Add AICA Level 2 Project - Sanjeev Panwar - Vendor Invoice Portal`. Adapt the template below. Review Files changed. Create the PR and save its URL. Opening a PR is not the same as acceptance; the owner decides whether to merge.
8. Respond to review by committing changes to the same fork branch and pushing; the PR updates. Keep your submission/PR URL and commit hash as evidence.

## Website alternative (guide pp. 1-4)
In YOUR fork choose Add file > Upload files. From File Explorer open the PARENT of the sanitized project folder and drag the whole named folder onto the uploader. Confirm its paths remain under Sanjeev-Panwar-Vendor-Invoice-Portal/. Review the upload list manually, including hidden files: .gitignore does not filter web uploads. For the guide's under-100-files upload method use batches, or use Git for many files. Platform limits may differ; use Git if upload is refused. Do not upload this ZIP. Commit to your fork's main branch, then follow PR steps 6-8 above.

## PR description template
Author: REPLACE with public display name
Project: Vendor Invoice Portal
Folder: REPLACE with actual folder name

Purpose: A Django portal for vendor registration and invoice submission with Finance review. REPLACE this sentence if the verified source differs.
Included: sanitized source, README, pinned dependencies, sample configuration, architecture/security notes and demo instructions.
AI use: REPLACE with accurate development-assistance or runtime-AI description; do not claim unimplemented AI features.
Validation: REPLACE with checks actually run, environment and results. Do not mark tests passed without evidence.
Data: demonstration uses fictional records; no private data, databases, credentials, real invoice PDFs, logs or virtual environment included.
Optional demo: REPLACE with a sanitized video link, or remove this line.
Known limitations: REPLACE with actual limitations.
