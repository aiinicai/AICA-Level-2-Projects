# Complete GST Suite

AI-built GST compliance suite for Chartered Accountant firms (ICAI AI Level 2 Capstone).

- **Reconciliation:** GSTR-1, GSTR-2B and GSTR-3B against the books for every client: checks R1–R6, a 3-way view and drill-down to invoices.
- **Invoice matching:** matched, period difference, value mismatch, probable match and one-sided invoices, plus supplier follow-up e-mails.
- **Annual return:** GSTR-9 and GSTR-9C drafts table by table, and DRC-03 with interest.
- **Notices:** tracker with form library, due dates and calendar.
- **Exports:** Excel workbooks (live formulas) and PDF reports.
- **Security:** no GST portal password is ever asked for or stored; access is through a GSP with the client's OTP.

## Folders
| Folder | Contents |
|---|---|
| `web-app/` | Source of the web app (TanStack Start, React, Tailwind, shadcn/ui; design from Lovable) |
| `exe-build/` | Launcher and build script for the one-file exes, plus Start_Local / Start_Server .bat files |
| `docs/` | Master prompt and detailed user guide (Word) |

## Run from source
```
cd web-app
npm install
npm run dev        # http://localhost:8080
npm test           # unit tests
```

## Build the exes (Windows)
1. `cd web-app`, then `npm run build` with `NITRO_PRESET=node-server` set.
2. Copy `.output` to `GST Suite Web/app` and `node.exe` to `GST Suite Web/node`.
3. Run `exe-build/build_exes.ps1`. It creates `Complete GST Suite.exe` (this computer) and `Complete GST Suite Server.exe` (office server).

Demo data: open the app and choose **Load demo firm**, then **Run all clients**.
