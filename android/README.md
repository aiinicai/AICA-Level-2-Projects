# DirhamTrack AI - Android Native Notification Interceptor & APK Guide

## How Automatic Bank Notification Catching Works
DirhamTrack AI captures transaction notifications directly from Android's **Notification Center** using the native `NotificationListenerService` (`android.permission.BIND_NOTIFICATION_LISTENER_SERVICE`).

### The Zero-Paste Automatic Pipeline:
1. **Bank Alert Fires**: When you tap your card at Carrefour, ENOC, Lulu, make a payment, or receive your monthly salary, your bank (Emirates NBD, Citi, Mashreq, FAB, CBD, etc.) sends a push alert or SMS to your Android notification shade.
2. **Silent Background Interception**: Android OS wakes up `BankNotificationListener.kt` (even if the app is closed in background).
3. **Smart Extraction & UAE Categorization**:
   - Extracts amount (AED or foreign currency), currency, merchant, and card mask.
   - Categorizes by merchant: ENOC/ADNOC -> Petrol, KFC/McDonald's -> Food, Carrefour/Lulu -> Groceries, DEWA -> Utilities, Etisalat/du -> Telecom, Amazon/Noon -> Shopping, Salik/RTA -> Transport.
   - Flags suspicious or foreign currencies (🔴 RED FLAG).
4. **Instant Sync to Dashboard**: `BankNotificationListener` broadcasts the transaction to `MainActivity.kt`, which executes `window.onNativeBankNotificationReceived(payload)` into the UI.
5. **Zero User Action Needed**: No copying, no pasting, no typing. The transaction appears in your budget and ledger automatically!

---

## Files in `/android`:
- `BankNotificationListener.kt`: 24/7 background service that intercepts notifications.
- `MainActivity.kt`: Native Android container running the dashboard with WebView bridge.
- `AndroidManifest.xml`: Declares permissions and `BIND_NOTIFICATION_LISTENER_SERVICE`.
- `build.gradle.kts`: Gradle build configuration with Kotlin and Android SDK dependencies.

---

## Step-by-Step Android APK Build & Install Guide

### Method A: Using Android Studio (Recommended)
1. Open **Android Studio** (Hedgehog, Iguana, Ladybug, or newer).
2. Click **Open** and select the `/android` directory.
3. Wait for Gradle sync to complete.
4. Click **Build** > **Build Bundle(s) / APK(s)** > **Build APK(s)**.
5. Once built, click **locate** or find the file at:
   `app/build/outputs/apk/debug/app-debug.apk`
6. Transfer this APK to your Android phone (via USB, Google Drive, WhatsApp, or Telegram) and tap to install.

### Method B: Command Line (Gradle)
```bash
cd android
./gradlew assembleDebug
```
The APK will be generated at `app/build/outputs/apk/debug/app-debug.apk`.

---

## ⚠️ Essential One-Time Setup: Enable Notification Access on Android
For privacy and security reasons, Android OS requires you to grant permission once before any app can read notifications:

1. On your Android phone, open **Settings**.
2. Tap **Apps** (or **Apps & Notifications**) > **Special app access** > **Device & app notifications** (or search *"Notification access"* in the Settings search bar).
3. Find **DirhamTrack AI** and toggle it **ON**.
4. Tap **Allow** on the Android system confirmation popup.
5. **Done!** From now on, whenever Emirates NBD, Citi, FAB, Mashreq (including salary deposits), or any bank sends an SMS or push alert, DirhamTrack records it into your ledger automatically with 0 clicks.
