# ABC Private Limited – Travel & Expense Management (PWA)

Pre-travel approval → booking → expense statement with bills → approvals → accounting & payment,
with an admin analytics dashboard, exception flags and full install-as-app (PWA) support.

## Start
| Platform | How |
|---|---|
| Windows | Double-click **Start_ABC_Travel_App.bat** (installs Node.js LTS via winget if missing) |
| Windows – demo data | Double-click **Start_Demo_Mode.bat** → login `admin@abc-demo.com` / `Demo@1234` |
| macOS | Double-click **Start_ABC_Travel_App.command** (or `./start_mac_linux.sh`) |
| Linux / any | `node launch.js` (demo: `node launch.js --demo`) |
| **Mobile / share link** | Double-click **Start_Public_Link.bat** – installs the free Cloudflare Tunnel once and prints a secure `https://….trycloudflare.com` link that anyone can open and install on their phone (also saved in PUBLIC_LINK.txt). Keep the window open. |

Open http://localhost:8080. **The first person to sign up becomes the Admin.** The Admin then adds
employees (email id + role); only those email ids can sign up.

Requires Node.js 22 LTS or newer. No npm install, no external database – SQLite is built into Node.js.

## Folder layout
```
server.js            Backend: HTTP server, REST API, workflow engine, SQLite database
launch.js            Launcher: version check, starts server, opens browser (--demo, --no-browser)
public/              Front-end PWA (index.html, app.js, charts.js, styles.css, manifest, sw.js, icons)
tools/seed_demo_data.js   Builds a demo database with sample employees and 46 trips
tests/api_workflow_test.js  Automated end-to-end workflow test (npm test)
data/                SQLite database files (created on first run)
uploads/             Attached bills, tickets, payment proofs
```

## Roles
Admin · Managing Director · Business Head · Sales Manager · Sales Executive · HR Head · Accountant ·
Travel Assistant · Finance Manager · Operations Manager · Employee (+ any custom roles added in Settings).

## Workflow
Employee request → Business Head → Managing Director → Travel Assistant (booking per Matrix of Authority)
→ travel → expense statement with bills → Business Head → HR Head → Accountant (voucher, advance
adjustment, payment) → Paid & Closed. Send back / reject at every approval stage; complete audit trail.

## Tests
`npm test` (or `node --no-warnings tests/api_workflow_test.js`) – runs 43 checks on a temporary database.
