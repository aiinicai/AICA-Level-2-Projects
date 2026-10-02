# Installing ABC Travel as an App (PWA)

The app is a full Progressive Web App: web manifest, 192/512 px and maskable icons, service worker with an
offline app shell, app shortcuts (New Request, Approvals, My Trips) and install screenshots. Chrome, Edge,
Samsung Internet and Safari therefore offer to install it like a normal app.

## Requirement: a secure address
Browsers only allow installation from **https://** addresses or from **http://localhost**.
* On the server PC itself, `http://localhost:8080` works immediately.
* For other PCs and mobile phones, publish the app over HTTPS (see Deployment_and_HTTPS_Guide.md).

## Desktop – Chrome / Edge (Windows, macOS, Linux)
1. Open the app and log in.
2. Click the green **Install App** button in the top menu bar, then **Install**.
   (Or click the install icon ⊕ at the right end of the address bar.)
3. ABC Travel opens in its own window and appears in the Start menu / Dock / desktop.

## Android – Chrome
1. Open the HTTPS address in Chrome.
2. Tap **Install App** in the menu bar (or ⋮ menu → **Add to Home screen / Install app**).
3. The ABC Travel icon is added to the home screen and app drawer.

## iPhone / iPad – Safari
Apple does not show an automatic prompt. Tap **Install App** in the menu bar for instructions, or:
1. Tap the **Share** button (square with arrow).
2. Choose **Add to Home Screen** → **Add**.

## Behaviour of the installed app
* Opens full-screen without browser bars, with the ABC icon and navy theme colour.
* Long-press / right-click the icon for shortcuts: New Travel Request, My Approvals, My Trips.
* If the connection drops, the app still opens and shows an offline notice; data is always saved on the
  company server, never only on the phone.
* Updates are picked up automatically the next time the app is opened online.

## Uninstall
Chrome/Edge: open the app → ⋮ menu → Uninstall. Android: long-press icon → Uninstall. iOS: long-press → Remove App.
