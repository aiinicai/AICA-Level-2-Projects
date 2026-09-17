# myvaluation — Reviewer-Ready Local Demo

This project is a local MVP of an AI-assisted valuation workflow.

## Easiest way to run

### First time only

Double-click:

`Setup-and-Start-MyValuation.bat`

The script will:

1. check Python
2. check Node.js / npm
3. create the backend Python virtual environment
4. install Python packages from `backend\requirements.txt`
5. install frontend packages using `npm install`
6. start the FastAPI backend
7. start the Next.js frontend
8. open the application automatically in the browser

Application URL:

`http://localhost:3000`

Backend health URL:

`http://127.0.0.1:8000`

### Future runs

Double-click:

`Start-MyValuation.bat`

### Stop the application

Double-click:

`Stop-MyValuation.bat`

---

## Reviewer prerequisites

The reviewer computer should have:

- Windows 10 or Windows 11
- Python 3.11 or 3.12
- Node.js LTS
- Internet access for the first dependency installation

No manual Python or npm commands should be required after those prerequisites are installed.

---

## Important note

This is a local MVP, not a deployed cloud application.

The one-click launcher makes the project easy to run on another Windows computer, but the project still runs locally using:

- frontend port 3000
- backend port 8000

---

## Before submission

The project owner should confirm:

1. `backend\requirements.txt` exists.
2. `package.json` and package lock file are present.
3. no API keys or passwords are hardcoded.
4. no confidential client files are included.
5. sample / fictitious assignment data is included if the reviewer needs a ready demonstration assignment.
6. the complete folder is zipped only after a successful clean-machine-style test.

---

## Recommended submission folder

The ZIP uploaded to Google Drive may contain:

- complete source code
- launcher BAT files
- README
- anonymised sample input documents
- sample generated Excel working
- sample generated Word valuation report
- optional sample assignment data

For GitHub, exclude local virtual environments, `node_modules`, secrets and confidential data.
