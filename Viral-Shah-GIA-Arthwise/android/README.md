# GIA_Arthwise Loan Facilitator - Android Mobile Application

This directory contains the complete native Android application project and APK build pipeline for the GIA_Arthwise Loan Proposal Evaluation and Debt Syndication platform.

---

## 1. Project Architecture

- **`AndroidManifest.xml`**:
  - Package: `com.giaarthwise.loanfacilitator`
  - Permissions: `INTERNET`, `ACCESS_NETWORK_STATE`, `READ_EXTERNAL_STORAGE`, `READ_MEDIA_IMAGES`, `CAMERA`
  - Cleartext HTTP traffic enabled for local Wi-Fi / private subnet connections (`network_security_config.xml`).
- **`src/com/giaarthwise/loanfacilitator/MainActivity.java`**:
  - Full-screen Android Activity with hardware-accelerated WebView.
  - Native file chooser (`onShowFileChooser`) allowing users to upload bank statements, GST returns, and KYC documents directly from their phone storage or camera.
  - In-app **Server Configuration Dialog** (`⚙ Server IP`): Allows switching between local development IP (e.g. `http://192.168.1.15:8000`), emulator (`http://10.0.2.2:8000`), or production cloud domain.
  - Friendly connection error handling with retry and server reconfiguration buttons.
  - Android system back-button navigation (`onBackPressed`).
- **`assets/www/`**:
  - Contains pre-packaged web application assets (HTML, JavaScript, CSS, and icons) for instant loading.
- **`res/`**:
  - Branded app launcher icons (`ic_launcher.png`), brand colors (`#1b2632` and `#a45139`), Material themes, and network security policies.

---

## 2. Generating the Standalone APK File

Both **OpenJDK 17** and the **Android SDK Platform 33 / Build-Tools 33.0.2** are already downloaded on your system.

To compile and sign the release APK, open your Terminal and run:

```bash
cd "/Users/viralshah/Desktop/GIA_Arthwise"
./android/build_apk.sh
```

### What `build_apk.sh` does automatically:
1. Detects OpenJDK 17 and Android SDK command-line tools.
2. Generates resource symbols with `aapt`.
3. Compiles `MainActivity.java` with `javac`.
4. Converts bytecode into Dalvik Executable (`classes.dex`) with `d8`.
5. Packages resources, assets, and bytecode into an APK.
6. 4-byte aligns the package with `zipalign`.
7. Signs the APK with release keys (`giaarthwise-release.keystore`) using `apksigner`.
8. Generates the final, installable file:
   👉 **`android/bin/giaarthwise-loan-facilitator.apk`**

---

## 3. Installing on Your Android Phone

### Option A: Install via Standalone APK File
1. Transfer `android/bin/giaarthwise-loan-facilitator.apk` to your phone (via USB cable, Google Drive, or by visiting `http://<mac-ip>:8000/download/app.apk` on your phone's browser).
2. Tap on the downloaded `.apk` file.
3. If prompted, toggle **"Allow from this source"** (Install unknown apps).
4. Tap **Install**.
5. Launch the app from your home screen!

### Option B: Instant WebAPK Install via Chrome (No APK build step needed)
Android's official WebAPK Minting Service allows installing the app directly from Chrome:
1. Ensure your phone is connected to the same Wi-Fi as your Mac.
2. Open **Google Chrome** on your Android phone and navigate to `http://<your-mac-ip>:8000`.
3. Tap the **three-dots menu (`⋮`)** in the top right corner.
4. Select **"Install app"** (or "Add to Home screen").
5. Tap **Install**. Android will automatically generate, sign, and install an official WebAPK on your phone!
