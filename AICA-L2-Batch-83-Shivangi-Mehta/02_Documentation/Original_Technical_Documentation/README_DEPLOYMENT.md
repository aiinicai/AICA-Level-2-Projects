# FinSight — Deployment Guide

FinSight is an offline Financial Review & Compliance Assistant. This guide explains how to get it running on a computer and how to use it day to day. It doesn't assume any technical background.

> **A note on this guide's status:** this guide describes how FinSight is *designed* to be installed and run once it has been built into a Windows application. The actual Windows build has not yet been produced — see "Current Status" at the bottom of this guide before you rely on it.

---

## How to Install

FinSight doesn't need a traditional installer. You (or whoever set it up) will have a `FinSight` folder — copy that whole folder anywhere you like: your Desktop, Documents, or a USB drive. Everything FinSight needs is inside that one folder.

Do not move or rename anything *inside* the folder — the app relies on its pieces staying together.

## How to Start FinSight Locally (just for you, on this computer)

1. Open the `FinSight` folder.
2. Double-click **Start_FINsight_Local.bat**.
3. A window will open showing FinSight getting ready. The first time, this creates your database and data folders — this is normal and only happens once.
4. Your web browser should open automatically to FinSight. If it doesn't, the window will show you an address to type into your browser (it will look like `http://127.0.0.1:5000`).
5. Keep that window open while you use FinSight — closing it stops the application.

## How to Start LAN Mode (so others on your office/home network can use it too)

Use this if other people, on other computers on the **same trusted network**, need to reach FinSight through their own browser.

1. On the computer that will host FinSight, double-click **Start_FINsight_LAN_Host.bat**.
2. The very first time, you'll be asked to create an access password. Choose one that's at least 8 characters and that you can share with the people who need it. Write it down somewhere safe — FinSight can't email or recover it for you.
3. The window will show two addresses:
   - **Local** — for opening FinSight on the host computer itself.
   - **LAN** — this is the one to share with other computers on the network.
4. On another computer, open a browser (Chrome, Edge, or Firefox), type in the LAN address exactly as shown, and enter the shared password when asked.
5. Everyone's data stays on the host computer at all times — nothing is copied to the other computers.

**Only use this on a network you trust** — your home Wi-Fi or your office network, never a public Wi-Fi (like a café or airport), and never with the port forwarded to the internet.

## How to Connect From Another Computer

1. Make sure both computers are on the same Wi-Fi or network.
2. Open a browser and type in the LAN address the host computer showed (e.g. `http://192.168.1.23:8877`).
3. Enter the shared access password.
4. Use FinSight normally. Nothing needs to be installed on this computer.

If it doesn't connect: double-check both computers are really on the same network, and ask whoever manages the host computer's firewall to allow the FinSight port for your home/office network (never for "Public" networks).

## How to Back Up Your Data

Your data lives in three folders inside the FinSight folder:

```
database\
data\
logs\
```

To back up: copy these three folders somewhere safe (an external drive, a network backup location) periodically, and always before moving FinSight to a different computer or updating it to a newer version.

## How to Update FinSight

1. **Back up your data first** (see above) — this matters, because updating replaces the application files.
2. Copy your `database`, `data`, `logs`, and `config` folders somewhere safe.
3. Replace the old FinSight folder's application files with the new version, making sure your `database`, `data`, `logs`, and `config` folders are still there afterward (a proper update process keeps these automatically — this step is your safety net, not the expected outcome).
4. Start FinSight as usual. Your engagements, findings, queries, and settings should all still be there.

## How to Stop FinSight

Close the window that opened when you started FinSight (the one showing "FinSight is ready" and the address). This shuts everything down cleanly. Simply closing your browser tab does **not** stop FinSight — it keeps running until you close that window.

If you're hosting for other people (LAN mode), closing this window disconnects everyone else too — let them know before you close it.

## Troubleshooting

- **A security warning appears when starting FinSight** (Windows Defender or antivirus): this can happen with any newly-built application that isn't yet widely recognized by antivirus vendors — it does not by itself mean anything is wrong. Do not disable your antivirus. If you're unsure, ask whoever manages your computer to verify the file before running it.
- **"FinSight LAN mode refused to start"**: this is a safety check working as intended — it should not happen in a normal install. Contact whoever set up FinSight for you.
- **Another computer can't connect in LAN mode**: confirm you're on the same network, and check the host computer's firewall settings for the FinSight port (see "How to Start LAN Mode" above).
- **Forgot the LAN access password**: there's no automatic recovery — it has to be reset locally on the host computer. See `documentation/stage16_lan_mode.md` for the exact steps, or ask whoever manages FinSight for your organization.
- **Something looks wrong or FinSight won't start**: check the `logs` folder inside the FinSight folder — technical details are recorded there (never shown on-screen) that can help diagnose the problem.

---

## Current Status (please read)

This guide describes FinSight's intended deployment experience. As of this stage of development:

- The application code that makes all of the above work (automatic setup, local/LAN mode selection, automatic browser opening) is written, and its logic has been tested as far as the current development environment allows.
- **The actual Windows `FinSight.exe` file has not yet been built.** Building it requires a Windows computer with PyInstaller — something the current development environment doesn't have. See `documentation/stage17_exe_packaging.md` for the complete, honest account of what has and hasn't been verified yet.
- Once a real build exists, it should be tested against the checklist in that same document before being relied on for real engagement work.
