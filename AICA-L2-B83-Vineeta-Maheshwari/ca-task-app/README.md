# CA Task Delegation & Tracking App

A simple, self-contained web app for a Chartered Accountant firm to create
team member accounts, assign client tasks, track progress, and view a
visual, colour-coded dashboard — with a real database and a white & blue
theme. The app server itself needs no internet connection; the one
exception is the dashboard's charts library, which loads from a public CDN
the first time a browser opens the app (like any normal webpage), so keep
a normal internet connection on the computer/browser you use to view it.
The app now tries three different CDNs in turn (so it survives one being
blocked by a particular office network or antivirus) and shows a clear
"Charts couldn't load" message on the dashboard, instead of blank boxes,
if a computer genuinely has no internet access at all.

## What's inside

- **Backend:** Plain Node.js (no npm packages required at all — it uses
  only Node's built-in modules: `http`, `node:sqlite`, `node:crypto`).
- **Database:** SQLite, stored as a single file at `data/app.db`. Created
  automatically on first run.
- **Frontend:** Plain HTML/CSS/JS, served by the same server. Charts are
  drawn with Chart.js, loaded from a CDN in the browser.
- **Login:** Username/password. The admin/partner creates every team
  member's account — there is no public sign-up.
- **Windows launchers:** `Start CA Task App.bat`, `Stop CA Task App.bat`,
  and `Create Desktop Shortcut.bat` — double-click to run the app without
  using a terminal. See "How to run it" below.
- **Native desktop app (optional):** `main.js`, `setup.html`, and
  `package.json` turn this into a real installable Windows program with
  its own window (no browser tab at all) — see "Building the native
  desktop app" further down. This is a bigger, optional upgrade; the
  `.bat` launchers above already give you a no-terminal experience without
  it.

## Requirements

- **Node.js version 22.5 or newer** (the app uses Node's built-in SQLite
  support, which needs this version or later). Check your version with:

  ```
  node -v
  ```

  If you have an older version, download the current LTS release from
  https://nodejs.org.

## How to run it (Windows — easiest way, no typing commands)

Three double-click launchers are included in the folder, so you never need
to open a terminal or remember a URL:

1. Unzip the project folder anywhere (e.g. your Desktop or Documents).
2. Double-click **`Start CA Task App.bat`**. It starts the app and opens it
   in your default browser automatically. A small window titled
   "CA Task App Server" opens and stays running in the background — leave
   it open (you can minimize it) while anyone is using the app; closing it
   stops the app.
3. First time only: Windows may show a firewall prompt — click **Allow
   access** so teammates on your Wi-Fi can reach it (see "Sharing it with
   your team" below).
4. When you're done for the day, double-click **`Stop CA Task App.bat`**
   to shut the server down cleanly (or just close the "CA Task App Server"
   window).
5. Optional, recommended: double-click **`Create Desktop Shortcut.bat`**
   once — it adds a "CA Task App" icon (blue checkmark) to your Desktop
   that runs the same launcher, so you don't need to keep the unzipped
   folder open to start it next time.

If Node.js isn't installed yet, `Start CA Task App.bat` will tell you and
point you to https://nodejs.org — install the LTS version once, then run
the launcher again.

### Running it manually instead (any OS, or if you prefer a terminal)

1. Open a terminal inside the unzipped folder.
2. Run:

   ```
   node server.js
   ```

3. You'll see:

   ```
   CA Task Delegation App running at: http://localhost:3000
   Default admin login -> username: admin / password: admin123
   ```

4. Open **http://localhost:3000** in your browser.

### First login

Log in with the default admin account:
- **Username:** `admin`
- **Password:** `admin123`

Please create your real admin/partner account and team member accounts,
and stop using the default password once you're set up (see "Managing
users" below — there's no self-service password change screen yet, but
the admin can reset any user's password from the Team Members tab by
re-creating their entry, or you can ask for that feature to be added).

## Using the app

### Admin / Partner
- **Dashboard tab:** Live counts of total, overdue, completed and urgent
  tasks, plus charts: tasks by status, tasks by priority, and workload by
  team member (stacked by status).
- **Tasks tab:** See every task in the firm. Create a new task (client
  name, task type, assigned date, due date, priority, one or more
  assignees, notes), filter by status/priority/assignee, search, update
  status inline, edit, or delete a task.
- **Team Members tab:** Add new team members (name, username, password,
  role), and activate/deactivate accounts.

### Team Members
- Log in with the account the admin created.
- **Dashboard tab:** A personal view scoped to just your own tasks — "My
  Tasks" count, your overdue/completed/urgent tiles, and "My Tasks by
  Status/Priority" charts. It won't show other people's tasks or the
  firm-wide workload chart (that stays admin-only).
- **Tasks tab:** Opens already filtered to "My tasks only" — the tasks
  assigned to you. Untick that box any time to see the full firm list
  (useful for checking a client's status or coordinating with a
  colleague); it re-checks itself next time you log in. You can still
  create new tasks and assign them to one or more people on the team, and
  mark any task you're assigned to as In Progress / Completed.

The admin/partner's Dashboard and Tasks tabs are unchanged — they still
see everything across the firm by default, exactly as before.

### Assigning a task to multiple people
When creating or editing a task, "Assign To" is a checklist — tick as many
team members as should share the task. Every person ticked can see the
task under "My tasks only" and can update its status; any of them marking
it Completed marks it complete for everyone. Only the admin/partner, or
whoever originally created and assigned the task, can change who it's
assigned to later — other assignees can still update its status, just not
reassign it.

### Assigned date & days pending
Every task records the date it was assigned (editable if you're backdating
something) alongside its due date. The Tasks table shows a live "Days
Pending" column calculated from that date — it turns amber past 3 days and
red past 7, so ageing tasks stand out at a glance. Once a task is marked
Completed, that column instead shows how many days it took.

### Priorities & statuses
- **Priority:** Low, Medium, High, Urgent (color-coded badges).
- **Status:** Pending → In Progress → Completed. Tasks overdue and not yet
  completed are flagged with a red "Overdue" badge automatically.

## Updating from an earlier version

If you're replacing an earlier copy of this app, just copy your existing
`data/app.db` file into the new `data` folder before you run it the first
time (or drop the new files into the same folder as before, overwriting
`server.js`, `db.js`, and everything in `public/`, but leaving your
`data/app.db` alone). The app checks its database on startup and upgrades
it automatically the first time it runs — your existing team members and
tasks (including each task's original assignee) carry over safely; you'll
just see a one-line "Upgrading database..." message in the terminal.

## Where your data lives

Everything is stored in `data/app.db`, a single SQLite file. Back it up by
simply copying that file. To start completely fresh, stop the server and
delete `data/app.db` — a new one (with a fresh default admin account) will
be created the next time you run `node server.js`.

## Sharing it with your team on the office Wi-Fi

The app is already reachable by anyone on your network — you just need to
give teammates the right address and let the connection through.

1. **Find your PC's local IP address.**
   - Windows: Command Prompt → `ipconfig` → look for "IPv4 Address" under
     your Wi-Fi adapter, e.g. `192.168.1.15`.
   - Mac: System Settings → Wi-Fi → Details → TCP/IP, or run
     `ifconfig | grep inet` in Terminal.
2. **Allow it through your firewall.** The first time you run
   `node server.js`, Windows usually shows a prompt — "Windows Defender
   Firewall has blocked some features" — click **Allow access** (at least
   for Private networks). If you missed it, search Windows Settings for
   "Allow an app through firewall" and make sure Node.js is checked.
3. **Keep the server running.** Leave the terminal window with
   `node server.js` open — closing it stops the app for everyone.
4. **Teammates browse to `http://<your-ip>:3000`** (not `localhost`) from
   their own computer, on the same Wi-Fi, and log in with the account you
   created for them in the Team Members tab.

Two common snags: if your router has a "guest network" or "AP/client
isolation" turned on, devices can't see each other even on the same
Wi-Fi — make sure everyone's on the main network with isolation off. And
your PC's local IP can change after a reboot or reconnect (unless you fix
it — see below), which breaks the link teammates are using.

## Turning one PC into an always-on office server

For the address to stay stable and the app to survive restarts without
you manually starting it each morning:

- Use a PC that can stay on continuously (a spare desktop or small
  always-on mini PC works well); wired Ethernet is more reliable than
  Wi-Fi for something that needs to stay reachable.
- Give that PC a **static IP reservation** in your router's admin page
  (look for "DHCP reservation" or "static lease," usually at
  `192.168.1.1` or `192.168.0.1`) so its address never changes.
- Auto-start the app on boot:
  - **Windows:** create a Task Scheduler task that runs `node server.js`
    from the app folder "at startup," set to run whether or not a user is
    logged in.
  - **Cross-platform (recommended if that PC has normal internet
    access):** install a small process manager —
    `npm install -g pm2`, then from the app folder run `pm2 start
    server.js`, `pm2 save`, and `pm2 startup` — it also restarts the app
    automatically if it ever crashes.

Once set up, your team always reaches the tracker at the same
`http://<server-ip>:3000` link, even after the server PC restarts.

## Building the native desktop app (optional upgrade)

This turns the app into a real installed Windows program with its own
window — no browser tab, address bar, or typing `localhost:3000`. One
installer works for everyone: on first launch, each computer picks whether
it's the **Host** (the one PC holding the shared database — same role as
"Turning one PC into an always-on office server" above) or a **Client**
that connects to the Host over your Wi-Fi (what every teammate's PC
should pick).

Building it requires `npm install`, which needs an internet-connected
computer — you'll do this build once, then hand the resulting installer
file to your team.

One thing to know about Node.js and this native app: the **Host** PC still
needs Node.js installed (same requirement as before — the app uses your
computer's own Node.js to run the shared server behind the scenes, for
reliability). **Client** PCs (every teammate connecting to the Host) do
**not** need Node.js at all — their copy is just a window pointed at the
Host, nothing runs locally for them.

**1. Build the installer** (on any Windows PC with Node.js and internet):

```
cd ca-task-app
npm install
npm run dist
```

This downloads Electron and packaging tools the first time (may take a
few minutes), then produces an installer at
`dist\CA Task App Setup <version>.exe`.

**2. Install it on the Host PC** (the one that will hold the shared data —
same computer as in "Turning one PC into an always-on office server"):
run the installer, open "CA Task App" from the Start Menu or Desktop
shortcut, and on the first-run setup screen choose **"This is the main
computer (Host)."** Keep this PC on and the app open (or set it to run at
startup, same idea as the `.bat` launcher) so your team can reach it.

**3. Install it on each teammate's PC:** copy the same installer file to
their computer (USB drive, shared folder, email, etc.), run it, open "CA
Task App," and on the setup screen choose **"Connect to another
computer's app,"** entering the Host PC's local IP address (see "Sharing
it with your team on the office Wi-Fi" above for how to find it). From
then on, their app opens straight into the shared tracker automatically —
no browser, no address to remember.

If someone ever needs to change a computer's role (e.g. it picked the
wrong option, or the Host's IP address changed), use the app's menu:
**App → Change Server Connection…**

Two things worth knowing: the Host PC still needs the firewall allowance
and needs to stay on for others to connect, exactly as with the `.bat`
launcher — this just replaces the browser window with a proper app
window. And since I can't run Electron's own build/packaging tools inside
the sandbox that assembled this project, that one step (`npm run dist`)
will run for the first time on your machine — I have, however, verified
the actual mechanism it depends on (the app starting your computer's own
Node.js as its server and connecting a window to it) by running that exact
sequence directly, so the core behavior is tested even though the Electron
packaging step itself isn't. If `npm run dist` hits an error, send me what
it prints and I'll help sort it out.

## Access from outside the office (optional, not needed for LAN sharing)

This is a separate step, only worth doing if remote/away-from-office
access becomes a real need: either port-forwarding on your router plus a
dynamic-DNS service (e.g. No-IP) if you keep hosting from your own office,
or a small cloud server (a low-cost VPS) if you'd rather not expose your
office network directly. Either way, it should come with HTTPS and
tighter login security first — see "Notes on security" below. Happy to
help set this up if and when you need it.

## Notes on security

This is a straightforward internal tool: passwords are hashed (not stored
in plain text) using Node's built-in `scrypt`, and sessions are cookie-
based. It has not been hardened for exposure to the public internet — keep
it on your office network or behind your firm's own access controls if you
extend it beyond local use.
