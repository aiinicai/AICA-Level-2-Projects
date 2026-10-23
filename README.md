# BreakBuddy Pro v4.0 — Desktop Wellness & Work Companion

A private, local-first Windows desktop tool for Chartered Accountants, auditors, finance professionals, and anyone spending long hours on a laptop. It builds on the original BreakBuddy Pro v2.0 and **preserves the dashboard, Pomodoro tasks, guided breaks, character companions, deadline calendar, analytics, floating HUD, hydration and posture reminders**.

## Start on Windows

1. Extract the **entire ZIP** to a normal folder, for example `Documents\BreakBuddy_Pro`.
2. Install **Python 3.9 or newer** from [python.org](https://www.python.org/downloads/windows/). When installing, enable **Add python.exe to PATH**. Tkinter is included with the standard Windows Python installer.
3. Double-click **`run_windows.bat`** to open the desktop app. If the app does not open, double-click **`run_windows_debug.bat`** and read the error shown.
4. Optional: run **`install_tray_support.bat`** once to enable a Windows system-tray icon. Optional dependencies are `pystray` and `Pillow`. They are **not** needed for the new screen-time, Schulte game, notes, or meditation features.

No login, web service, account, or API key required. With Python already installed, all wellness, timer and local tracking features work offline. Live news is the only feature that requires internet access. Windows is required for the per-application foreground monitor. On macOS/Linux, the other functions can still work but app usage tracking reports “Windows only.”

## What was added in v4.0

### India Tax & Finance News — new live tab

Click **India Tax & Finance** in the left sidebar to see newly published India-focused finance and tax headlines. **Internet access is required for live news**. No login, paid account, API key, or optional Python libraries are needed.

- **Sources:** Official RSS feeds from the Income Tax Department (CBDT circulars, notifications and press releases), RBI (press releases and notifications), SEBI, and selected relevant PIB press releases; alongside Business Standard finance/market feeds and Google News search headlines for direct tax, GST, audit and finance news. A source can be temporarily unavailable or change its RSS format.
- **Topics:** All Topics / Direct Tax / GST & Indirect Tax / RBI & Banking / Finance & Markets / Audit & Corporate. Use **Official only** to see only feeds published by government agencies/regulators.
- **Quick digest:** A list of the latest three matching news headlines at the top, for a rapid review.
- **Article detail:** Selecting a headline displays its original publisher, date and available excerpt. Official or news RSS descriptions may supply a short excerpt. **When the RSS feed does not supply a reliable summary, the app says so rather than generating unverified content.**
- **Open source:** Double-click a headline or select **Open Original Article** to open the source in your usual web browser. You can also copy the article link.
- **Refresh:** Press **Refresh Live News** for an immediate update. Auto-refresh is enabled by default and checks at most every 15 minutes **while that tab is open**. Disable this with the checkbox.
- **Offline cache:** The last successful batch is saved in `userdata/india_news_cache.json`. Cached news is clearly identified when sources fail or data is old. No article is marked as legally effective based on its headline.
- **Dates:** News publication timestamps are shown in Indian Standard Time (IST), when present in the feed. An undated source is labelled accordingly.
- **Privacy:** Only public news feeds are requested; window usage information, task notes, and other app data are **not** sent to news publishers. Opening a story in your browser uses your usual browser and network settings.

### Stop & Exit — new always-visible red button

Click **STOP & EXIT APP** at the bottom-left or choose **Actions → STOP & EXIT BreakBuddy Pro**. **Ctrl+Q** also exits. It saves your notes, statistics and settings, stops the timer, requests termination of live news fetching, closes the tray icon and closes the desktop window. The app does not continue monitoring your Windows activity after that process exits. Unfinished external RSS requests may be interrupted without holding the app open. This button **always quits**, even if the separate "Keep running in system tray on close" setting is enabled.

The normal **X** in the window corner still minimizes/keeps the app running as configured; use **Stop & Exit** to fully terminate it. If you enabled "Launch automatically with Windows", turn that setting off if you also want to prevent future launches after restarting Windows.

## Features retained from v3.0

| Feature | How to use it |
|---|---|
| **☀ Day / 🌙 Night mode** | Sidebar button or **Ctrl+L** switches between light and dark instantly. Other palettes remain in Settings. |
| **💻 Active App & Window Screen Time** | Open **App Screen Time**. Shows the active Windows program and live window title, total time by application, today/yesterday/7-day comparison, top-five visual bars and CSV export. |
| **Pause/resume app tracking** | App Screen Time → **Pause Monitoring**. Existing general screen-time/break timer stays active. |
| **Privacy** | Only program names are stored by default. The live window title is shown on screen but **never written to disk** unless you expressly enable “Store window titles”. Disabling title storage deletes existing saved title history. “Erase Usage History” removes app usage data. Data automatically expires after 30 days. |
| **📝 Where I Left Off** | **Ctrl+R** or sidebar → Wellness Lab → Where I Left Off. Capture client/project, current work, and next action. Saves automatically after an edit, plus Save Now / Copy / Clear. Use before lunch or any break to make resuming easier. |
| **🧩 Schulte focus game** | Wellness Lab → Schulte Focus Game. Find numbers 1→25 on a randomized 5×5 grid; optional 4×4 or 6×6, stopwatch, errors, and locally saved best times. |
| **🧘 Meditation break** | Wellness Lab → Meditation & Breathing. Start/pause/reset a 2, 5 or 10-minute session with visual 4-second inhale / 6-second exhale pacing. Completed sessions record daily minutes locally. |
| **Daily app history CSV** | App Screen Time → Export Screen-Time CSV, opens in Excel. Only records from the currently retained local history are exported. |

## Suggested CA workflow

1. Start work and note your priority audit/filing task on the **Focus & Tasks** tab.
2. During work, the reminder engine tracks device activity and prompts for water, posture checks, eye rests and movement breaks.
3. Before leaving a reconciliation, tax return, or working paper, press **Ctrl+R** and capture where you stopped and what to do next.
4. Use a guided break, or use a short meditation session. The Schulte game is an *optional concentration challenge*, not a substitute for looking away from the screen.
5. At the end of the day, inspect **App Screen Time**, the dashboard, and weekly analytics. Export CSV if needed.

## Updating from BreakBuddy Pro v3.0

For an existing installation, exit v3.0 first. You can copy the files from the v4.0 ZIP over your older app directory without deleting `userdata/`; your existing notes, settings and monitoring history will remain. Make a backup of `userdata/` beforehand. Alternatively, install the v4.0 ZIP in a new directory and copy your old `userdata/` JSON files into that directory.

## Shortcuts

- **Ctrl+B** — Guided break
- **Ctrl+M** — Show/hide mini HUD
- **Ctrl+P** — Start/pause Pomodoro
- **Ctrl+L** — Toggle light/dark theme
- **Ctrl+R** — Open Where I Left Off
- **Ctrl+Q** — Stop all activity and exit BreakBuddy Pro
- **Space / →** — Pause / advance step inside the guided-break window

## Your data & privacy

All local state is inside `userdata/`. It contains settings, wellness statistics, task notes and screen-time statistics. It can include client names if **you type them into a note**. Do not share `userdata/` in a public ZIP. App tracking doesn't capture typed text, screenshot contents or clipboard data. Window-title capture is off by default; enabling it can log sensitive information such as file names or email subjects. Data stays in the folder unless **you** copy or export it. There is no network sync of user data. The optional India News tab makes outbound requests only to public news feeds (unless using your browser to open a story). Application usage uses Windows foreground window and idle time; it doesn't track multiple simultaneous programs or work done away from the keyboard. Time totals are estimates, especially when the computer sleeps or is locked.

Data files:
- `userdata/where_i_left_off.json` — your break scratchpad
- `userdata/screen_time.json` — per-app usage, with optional titled windows
- `userdata/wellness_tools.json` — Schulte bests and completed meditation minutes
- `userdata/india_news_cache.json` — cached public articles, titles, sources and dates
- Existing `userdata/settings.json`, `stats.json`, `tasks.json`, etc.

For privacy, when copying the app to another computer, leave the personal `userdata/` JSON files behind. The ZIP supplied here contains an **empty** `userdata` folder.

## Closing and quitting

Closing the window will keep the app in the system tray if optional tray support is installed. Otherwise it minimizes to the taskbar. To stop tracking and exit completely, click the **red Stop & Exit** sidebar button, use **Ctrl+Q**, or choose **Actions → STOP & EXIT BreakBuddy Pro** (tray → Quit also works). The application does not run after you actually quit.

## Notes

- The Schulte number game is a concentration exercise, *not* clinically validated eye therapy. For screen-related eye strain, take periodic distance-viewing and off-screen breaks.
- Pacing in the meditation exercise is optional; breathe comfortably and stop if dizzy.
- Filing deadline presets in the previous version are illustrative and must be checked against current statutory dates; do not rely on presets for compliance decisions.
- This app provides general wellbeing reminders, not medical advice.

## Troubleshooting

- **Nothing happens on double-click:** run `run_windows_debug.bat` and inspect the console output. Check that Python 3.9+ is installed.
- **No system-tray icon:** run `install_tray_support.bat` once (requires internet for optional pip packages), then restart.
- **No app usage stats:** works only on Windows; check the **Pause Monitoring** switch and idle detection. Data will start accumulating after you switch to another application and work there.
- **Windows asks about folder permissions:** extract the ZIP to Documents, not Program Files, so the local JSON files can be saved.

## News troubleshooting

- **Shows only cached headlines / network errors:** Check your internet connection, proxy or firewall. Some official sites may block access or temporarily change their feed URLs. Try again later with **Refresh Live News**. Other BreakBuddy features remain usable.
- **Headline does not include a detailed summary:** The publisher's RSS feed lacks usable article text. The app does not invent article summaries. Select **Open Original Article** to read the story.
- **News not updating in the background:** Auto-refresh runs only while the news tab is visible and enabled, to avoid unnecessary traffic and interruptions. Press Refresh for an immediate update.
- **Windows time incorrect:** News dates are presented in IST regardless of the Windows timezone; ensure your device's system clock is accurate for "last refreshed" indicators.
