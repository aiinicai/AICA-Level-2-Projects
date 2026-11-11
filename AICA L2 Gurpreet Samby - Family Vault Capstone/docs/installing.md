# Installing Family Vault

Written for someone who is not a programmer. If any step does not look like
this, stop and ask rather than guessing.

Downloads are on the [Releases page](../../releases). Take the newest version.

---

## Before you start: the one thing that matters

Family Vault has **no password reset**. If you forget your master password,
nobody can open the vault — not you, not the person who built it. That is the
price of nobody else being able to read it either.

So before you put anything real in it:

1. Choose a master password you will not forget, or write it down.
2. Keep that note somewhere a burglar would not look but you would — not
   taped to the laptop, not in a file called `passwords.txt`.

Until syncing is built, **your vault lives on one device only**. If the phone is
lost or wiped, the vault goes with it. Put the same entries on your laptop too
if they matter.

---

## Android

### What you need

An Android phone or tablet, Android 6 or newer.

### Steps

1. On the phone, open the [Releases page](../../releases).
2. Tap **`FamilyVault-Android.apk`** to download it.
3. Open the downloaded file. Your browser or Files app will offer to install
   it.
4. Android will warn you. It will say something like **"For your security,
   your phone is not allowed to install unknown apps from this source"** or
   **"unknown developer"**.

   This is expected. It appears because the app is signed with a development
   key rather than a Play Store key, not because anything is wrong with it.
   Tap **Settings**, turn on **Allow from this source**, then press back and
   tap **Install**.
5. Open **Family Vault** from your app list.
6. The setup screen appears. Choose your master password, tick the box to say
   you understand there is no reset, and tap **Create my vault**.

### If it will not install

| What you see | What to do |
|---|---|
| "App not installed" | You may already have a copy. Uninstall the old one first; **this deletes its vault**, so only do it if the vault is empty or you have the entries elsewhere. |
| "There was a problem parsing the package" | The download was incomplete. Delete the file and download it again. |
| No install option at all | Open the Files app, find the `.apk` in Downloads, and tap it from there. |

---

## Windows

### What you need

Windows 10 or Windows 11, 64-bit.

### Steps

1. Open the [Releases page](../../releases) and download
   **`FamilyVault-Windows.zip`**.
2. Windows or your browser may warn that the file is not commonly downloaded.
   Choose **Keep**.
3. Right-click the downloaded zip and choose **Extract All…**. Put it
   somewhere you will keep it, such as `Documents\FamilyVault`.

   **Do not run it from inside the zip.** Windows opens zips as if they were
   folders, but the program cannot work from there.
4. Open the extracted folder and double-click **`family_vault.exe`**.
5. Windows may show a blue **"Windows protected your PC"** box. Click **More
   info**, then **Run anyway**. This appears because the program is not signed
   with a paid certificate.
6. The setup screen appears. Choose your master password, tick the box, and
   click **Create my vault**.

### Keep the folder together

The folder contains the program *and* the files it needs. Moving
`family_vault.exe` out on its own will stop it working. If you want it on the
Start menu or taskbar, right-click the `.exe` and choose **Pin to Start** or
**Pin to taskbar** — that makes a shortcut and leaves the folder alone.

### If it will not start

| What you see | What to do |
|---|---|
| Nothing happens | You are probably running it from inside the zip. Extract it properly first. |
| "A required DLL was not found" | Files are missing from the folder. Extract the zip again, all of it. |
| It opens and closes at once | Extract to a folder you own, such as under Documents, rather than to `Program Files`. |

---

## Where your vault is kept

One encrypted file. The app shows you exactly where under **Settings → Where
your vault is kept**.

| Platform | Roughly where |
|---|---|
| Android | Inside the app's own private storage, which other apps cannot read |
| Windows | Under your user profile, in your AppData folder |

The file is useless to anyone without your master password — but it is also the
only copy. Until syncing and backup arrive, if you want a second copy you must
make one yourself.

---

## Upgrading to a newer version

**Android.** Download the new APK and install it over the top. Your vault stays
where it is. Do **not** uninstall first — that deletes the vault.

**Windows.** Extract the new zip to a *new* folder and run it from there. Your
vault is in AppData, not in the program folder, so it is untouched. Delete the
old folder once the new one works.

---

## Removing it

**Android.** Uninstall as you would any app. **This deletes the vault.**

**Windows.** Delete the folder. That removes the program but *not* the vault.
To remove the vault as well, open the app first and use **Settings → Delete
this vault**, which asks twice and makes you type DELETE.

---

## A note on the warnings

Both platforms warn about this app, and both are right to: it is not
distributed through a store, so neither can vouch for it. You are trusting the
source rather than the shop. The source is this repository, where every line
can be read.
