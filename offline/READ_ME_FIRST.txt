FAMILY TASKS - OFFLINE VERSION (data stays on your phone)

Files: index.html, manifest.json, sw.js, icon-192.png, icon-512.png  (keep them together, at the top level)

STEP 1 - Put the files on a web address (free, one time)
 Easiest: https://app.netlify.com/drop  -> drag this whole folder onto the page -> you get an https address.
 Or Vercel: new project -> upload these files (no build, no framework, "Other").
 The files are only the app. Your tasks are NEVER sent there; they are saved inside your phone.

STEP 2 - Use it on the phone
 Open the address in Chrome on the phone -> menu (3 dots) -> "Install app" / "Add to Home screen".
 It now opens like an app and works without internet.

STEP 3 (optional) - Real APK file
 pwabuilder.com -> paste the address -> Package for Android -> "Other Android (APK)" -> download, keep the signing key.
 Send the APK to your phone and install it (allow "Install unknown apps").

IMPORTANT
 - Always open the SAME address. Data belongs to that address; a new address starts empty.
 - Family tab > "Save backup file" often (every week) and keep the file in Google Drive/WhatsApp.
   Clearing Chrome/app data or losing the phone deletes everything otherwise.
 - Restore on a new phone: Family tab > Restore > choose the backup file.
 - Reminders show only while the app is open. There is no server, so no PIN, Excel/PDF or import: reports save as CSV.

BACKUP IN THIS VERSION
 - A copy is taken automatically at 01:00 (or the first time you open the app after 01:00); the last 5 days are kept inside the phone
   (Family tab > Backup & restore). They protect against mistakes only, because they live in the same place as your data.
 - A phone web app cannot save into a folder by itself, so use "Save backup file" weekly and choose Downloads / Google Drive.
 - Automatic WhatsApp messages at 5 AM need the server version (an always-on computer). This offline version cannot send by itself.
