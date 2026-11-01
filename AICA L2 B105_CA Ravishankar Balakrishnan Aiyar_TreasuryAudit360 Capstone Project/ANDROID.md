# TreasuryAudit360 on Android

The app is a **Progressive Web App (PWA)**. It has a web app manifest, app icons (including Android adaptive/maskable icons), phone screenshots, and an offline service worker. This gives two ways to put it on Android.

| Route | Result | Effort |
|---|---|---|
| **A. Install from Chrome** | App icon on the home screen, opens full-screen like a native app | 1 minute, no accounts |
| **B. Android package (APK / AAB) with PWABuilder** | A real `.apk` file you can share and install, and an `.aab` for the Google Play Store | About 15 minutes |

Both routes need the app hosted on **HTTPS**. GitHub Pages provides this for free.

---

## Step 1 – Host it on GitHub Pages (at the root of your domain)

A full-screen Android app (no browser bar) must be served from the **root** of its domain. So use a *user site* repository:

1. On github.com click **New repository**. Name it exactly **`<your-username>.github.io`** (for example `raviaiyar.github.io`). Set it to **Public** and click **Create repository**.
2. Click **uploading an existing file**. Drag in **everything inside** the `TreasuryAudit360` folder: `index.html`, `manifest.webmanifest`, `sw.js`, `.nojekyll`, and the folders `icons`, `screenshots`, `n8n-workflows`, `sample-data`, `docs`. Then click **Commit changes**.
   - If `.nojekyll` is hidden on Windows, enable *View → Show → Hidden items* in File Explorer.
3. Go to **Settings → Pages**, set **Branch = main / (root)** and click **Save**.
4. After 1–2 minutes open **`https://<your-username>.github.io/`**. The app loads.

(A normal repository named `TreasuryAudit360` also works for route A. For route B its address would be `…github.io/TreasuryAudit360/`, and the Android app would then show a thin browser bar at the top.)

---

## Route A – Install directly from Chrome on the phone

1. On the Android phone open **Chrome** and go to `https://<your-username>.github.io/`.
2. Tap the gold **⬇ Install app** button in the menu (☰), **or** Chrome's **⋮ menu → Install app / Add to Home screen**.
3. The **TreasuryAudit360** icon appears on the home screen and in the app drawer. It opens full-screen in the navy theme, like any other app.

---

## Route B – Make a real Android app (APK + Play Store AAB) with PWABuilder

PWABuilder is a free tool from Microsoft that wraps a PWA into a signed Android app (Trusted Web Activity). No coding and no Android Studio are needed.

1. On a computer open **https://www.pwabuilder.com**, paste `https://<your-username>.github.io/` and click **Start**.
2. PWABuilder scores the app. The manifest, icons, screenshots and service worker are already included, so it should show no blocking errors.
3. Click **Package for stores → Android → Generate Package**. Suggested options:
   - **Package ID:** `io.github.<yourusername>.treasuryaudit360`
   - **App name:** TreasuryAudit360 · **Launcher name:** TreasuryAudit
   - **Version:** 1.0.0 (version code 1)
   - **Signing key:** *Create new* (PWABuilder generates it)
   - Leave the other options at their defaults.
4. Download the ZIP. It contains:
   - `*.apk`: install directly on phones (sideload) for your demo
   - `*.aab`: upload to the Google Play Console
   - `signing.keystore` + `signing-key-info.txt`: **keep these safe and private**. You need the same key for every future update. Never upload them to GitHub.
   - `assetlinks.json`: proves you own the website, so the app opens without a browser bar
5. **Upload `assetlinks.json` to your site:** in your GitHub repository click **Add file → Create new file**, type the name **`.well-known/assetlinks.json`**, paste the file's contents and **Commit**. Check that `https://<your-username>.github.io/.well-known/assetlinks.json` opens.
6. **Install the APK on a phone:**
   - Copy the `.apk` to the phone (WhatsApp to yourself, Google Drive or USB) and tap it.
   - Allow *Install unknown apps* for that source when Android asks, then tap **Install**.

### Publishing on Google Play (optional)
1. Create a Google Play Console developer account (one-time registration fee).
2. Click **Create app** and fill in the name, language, *App* type and *Free*.
3. Go to **Production → Create new release** and upload the **`.aab`**.
4. Complete the store listing:
   - Short and full description: reuse the text in `manifest.webmanifest`.
   - Icon: `icons/icon-512.png`.
   - Phone screenshots: `screenshots/phone-dashboard.png`, `screenshots/phone-findings.png`.
   - Feature graphic: 1024×500.
5. Complete the policy sections:
   - **Privacy policy URL:** you can add a `privacy.html` page to the site.
   - **Data safety:** the demo collects only what the auditor types.
   - **Content rating:** complete the questionnaire.
   - **Target audience:** set this to adults.
6. New personal developer accounts must run a **closed test** with testers before production access. Follow the Play Console prompts, then submit for review.

---

## What works offline

The app shell (menus, pages, icons) is cached on the phone, so the app always opens. Audit data, runs and responses need an internet connection to the n8n back end. When offline the app shows a clear "Could not load data" message with a Retry button.

## Troubleshooting

| Symptom | Fix |
|---|---|
| No "Install app" option in Chrome | The site must be opened over `https://` (GitHub Pages is). Reload once so the service worker activates |
| Android app shows a browser bar at the top | `.well-known/assetlinks.json` is missing, or the site is not at the domain root (use the `<username>.github.io` repository) |
| PWABuilder reports a manifest error | Check that `manifest.webmanifest`, `icons/` and `screenshots/` were all uploaded |
| App opens but data does not load | Check the internet connection and that the n8n workflows are published. Use **Settings → Save & test connection** in the app |
