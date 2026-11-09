# Putting the project on GitHub

Two routes: **A. GitHub Desktop** (no commands - recommended) or **B. command line**. Then **C** submits it to the course repository.

## Before you start - what goes on GitHub
Everything in this folder **except** what `.gitignore` excludes: your API key (`.env`), registers (`*.db`), stored judgments (`register_judgments/`), recipient lists, audit logs, settings, logs and `__pycache__`. The fictitious sample order and `examples/Sample_recipient_list.xlsx` (example.com addresses) are included on purpose.

Check once more that the folder holds **no client judgments, client names or real email addresses** - a public repository can be read by anyone and its history keeps deleted files.

Files that make up the project (all included):

| Item | Purpose |
|---|---|
| `README.md` | Front page of the repository: problem, features, technology, setup, usage, troubleshooting |
| `LICENSE` | MIT licence (change the copyright line to your name if you wish) |
| `.gitignore` | Keeps secrets and real data out of GitHub |
| `.env.example` | Shows the variable name for the API key without a real key |
| `requirements.txt`, `requirements-dev.txt` | Python packages for the app and for tests |
| `main.py`, `run_windows.bat`, `run_mac_linux.sh` | Start the app |
| `judgment_analyzer/` | Application code |
| `tests/`, `pytest.ini` | Automated tests |
| `tools/reliability_eval.py` | Reliability test kit |
| `assets/`, `config/settings.example.json`, `examples/` | Logo, example settings, fictitious sample data |
| `docs/` | Architecture, reliability, video script, development notes, build prompt, screenshots, this guide |

## A. GitHub Desktop (recommended)
1. Create a free account at github.com (or sign in).
2. Install **GitHub Desktop** from desktop.github.com and sign in with that account.
3. Extract the project ZIP to a normal folder, e.g. `Documents\GitHub\Judgement-Insights-Analyser`.
4. GitHub Desktop → **File → Add local repository…** → choose the folder. It will say "this directory does not appear to be a Git repository" → click **create a repository** → Name `Judgement-Insights-Analyser`, leave *Git ignore* = None and *License* = None (both are already in the folder) → **Create repository**.
5. Look at the list of changed files on the left: there must be **no** `.env`, `.db`, `register_judgments`, `email_audit_log` or recipient-list files.
6. Bottom-left: Summary `Initial upload` → **Commit to main**.
7. Click **Publish repository** → choose **Keep this code private** (recommended until you are ready) → **Publish**.
8. Open it on github.com: the README is shown on the front page. Later changes: edit the files, then in GitHub Desktop **Commit to main** → **Push origin**.

## B. Command line (Git for Windows)
```bash
cd "C:\Users\<you>\Documents\GitHub\Judgement-Insights-Analyser"
git init
git add .
git status            # check: no .env, .db, audit logs or recipient lists listed
git commit -m "Initial upload"
git branch -M main
# create an EMPTY repository on github.com first (no README, no licence), then:
git remote add origin https://github.com/<your-user-name>/Judgement-Insights-Analyser.git
git push -u origin main
```
GitHub asks you to sign in through the browser (Git Credential Manager) the first time.

## C. Submitting to the course repository (aiinicai/AICA-Level-2-Projects)
See `docs/GITHUB_SUBMISSION.md`: fork the course repository, add your folder in the course's naming format, include `VIDEO_LINK.txt`, commit, and open a pull request. Confirm the folder-name format and deadline with the course administrator.

## Good practice
- Make a **release** of what you submit: on github.com → *Releases* → *Draft a new release* → tag `capstone-submission`, title `Judgement Insights Analyser` → attach the ZIP.
- Add screenshots to the README from `docs/screenshots/` (already referenced) and the demo-video link.
- Never paste an API key or App Password into an issue, commit message or file. If one is ever committed, revoke it immediately in Google AI Studio / Google Account, then remove it from the repository.
