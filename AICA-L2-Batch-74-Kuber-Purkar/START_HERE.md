# Start Here - CMA Pro Builder

## Project identity

- Participant: Kuber Ranjan Purkar
- ICAI Membership No.: 187707
- Course: AI for Chartered Accountants, Level 2
- Batch: Batch 74, Nashik
- Batch completion: 6 August 2026

## What this folder contains

This is the source-code submission for CMA Pro Builder. Source code does not run
by double-clicking an individual `.tsx` file. It is started through Node.js using
the instructions below. The compiled Windows executable was submitted separately
through the ICAI Google Form.

## Fastest Windows evaluation

1. Install Node.js 20 or later from <https://nodejs.org/> if it is not already
   installed.
2. Download this complete project folder from GitHub and extract it.
3. Double-click `START_DEMO.bat`.
4. On the first run, dependency installation may take several minutes and needs
   an internet connection.
5. The application opens at <http://localhost:41731>.
6. Keep the server window open while reviewing the application. Close that
   window or press `Ctrl+C` in it when finished.

## Manual evaluation

Open Command Prompt or PowerShell in this folder and run:

```bash
npm ci
npm run dev
```

Open <http://localhost:41731> if the browser does not open automatically.

## Technical verification

```bash
npm run lint
npm run build
```

Successful completion confirms that the TypeScript source passes its type check
and that Vite can produce the frontend bundle.

## Important notes

- No Gemini API key is needed at runtime.
- The native SQLite package is optional and is not required for frontend
  capstone evaluation.
- The demonstration data are fictitious.
- The capstone evaluation build does not require a commercial license key.
- `dist/index.html` should not be opened directly from File Explorer because the
  generated asset paths expect a web server.
- The executable was supplied separately because GitHub's browser uploader has
  a lower per-file limit than the normal Git repository limit.
- Port 41731 is deliberately used for the source-code demo to avoid conflicts
  with other local applications that commonly use port 3000.

## Main review areas

- `src/engine/cmaEngine.ts` - financial calculation engine
- `src/components/` - data-entry, simulation, report and ratio screens
- `src/lib/excelExport.ts` - Excel output generation
- `server/` - optional local/LAN data mode
- `test/` - calculation and export verification scripts

For the complete project description, limitations and architecture, review the
Project Summary, User Manual, screenshots and example workbook included in the
main capstone submission package.
