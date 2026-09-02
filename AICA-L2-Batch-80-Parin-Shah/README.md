# BioLock Web — AICA Level 2 Capstone Project

**Batch:** AICA-L2-Batch-80
**Participant:** Parin Shah

## Overview

BioLock Web is a Chrome browser extension (Manifest V3) that lets a user lock
specific websites behind a biometric (Windows Hello / Face ID / fingerprint)
check using the WebAuthn API. Once a site is added to the locked list, any
navigation to that site is intercepted and redirected to an authentication
screen; the original page only loads after a successful platform-authenticator
check.

## How it works

- **`popup.html` / `popup.js`** — the extension's toolbar popup. Lets the user
  add a domain to the locked-sites list (`chrome.storage.local`) and register
  a biometric credential via `navigator.credentials.create()` (WebAuthn
  registration, `authenticatorAttachment: "platform"`).
- **`background.js`** — a service worker that listens for tab navigation
  (`chrome.tabs.onUpdated`). If the destination URL matches a locked site and
  the tab hasn't already been unlocked in this session, it redirects the tab
  to the extension's own `auth.html` page instead of letting the navigation
  through.
- **`auth.html` / `auth.js`** — the authentication screen. On load it pulls
  the saved credential ID from storage and calls
  `navigator.credentials.get()` to trigger the OS biometric prompt
  (WebAuthn assertion). On success it messages the background script to mark
  the tab as unlocked and redirects to the original target URL.
- **`manifest.json`** — Manifest V3 configuration: `tabs` and `storage`
  permissions, `<all_urls>` host permission (needed to intercept navigation
  on any locked domain), and the background service worker / popup wiring.

All credential material stays local to the browser via `chrome.storage.local`
and the WebAuthn platform authenticator — nothing is sent to a server.

## Relevance to AICA Level 2 modules

This project draws on the course's application-development modules
(Full-Stack Web Based App Development, Android/APK packaging concepts, and
Agentic/automation workflow design) by building an end-to-end browser-based
tool: front-end UI (popup/auth pages), an event-driven background service,
browser storage, and a modern web authentication API — assembled and
iterated with AI coding assistance as taught during the course.

## How to load and test the extension

1. Open `chrome://extensions` in Chrome.
2. Enable **Developer mode** (top-right toggle).
3. Click **Load unpacked** and select this project folder.
4. Click the extension icon, enter a domain (e.g. `example.com`) in
   **Lock a Website**, then click **Add to Locked List**.
5. Click **Register Biometric (Device Setup)** and complete the OS prompt.
6. Navigate to the locked domain in a new tab — you should be redirected to
   the authentication screen and prompted for biometric verification before
   the site loads.

## Files

| File | Purpose |
|---|---|
| `manifest.json` | Extension manifest (MV3) |
| `popup.html`, `popup.js` | Toolbar popup UI — add locked sites, register biometrics |
| `background.js` | Service worker — intercepts navigation to locked sites |
| `auth.html`, `auth.js` | Biometric authentication gate page |
