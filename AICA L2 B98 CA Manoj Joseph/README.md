# Money Garden 🌿
### A Smart Personal Finance & Accounting Android App

**Money Garden** is an accounting-grade personal finance Android application designed to build lifelong financial discipline. It combines an engaging, gamified growing garden metaphor with a rigorous, professional double-entry bookkeeping ledger underneath, smart friend expense splitting, and Firebase Google Sign-In authentication.

---

## 📱 How to Download, Install & Update MoneyGarden.apk

### Option A: Direct Download from GitHub Repository (Recommended)
The ready-to-install Android package **`MoneyGarden.apk`** is located right in the root of this GitHub repository!
1. In this repository, click on **`MoneyGarden.apk`**.
2. Click **Download raw file** (or **Download**) to save `MoneyGarden.apk` (Version 1.4) directly to your Android device or computer.

### Option B: Export / Download from Google AI Studio
1. In the **Google AI Studio** project menu (top right):
2. Click **Download APK** or **Export Project** to obtain the latest build `MoneyGarden.apk` / `app-debug.apk`.

---

### Step 2: Transfer to Your Android Device (if downloaded on PC)
- Transfer the downloaded `MoneyGarden.apk` file to your phone via:
  - USB cable transfer to your device's `Download` folder.
  - Upload to Google Drive / OneDrive and download on your phone.
  - Send to yourself via Telegram / WhatsApp / Email.

### Step 3: Enable "Install Unknown Apps"
Because this is a standalone APK installed directly (not from Google Play Store):
1. Open your device's **Settings** ⚙️.
2. Search for **"Install unknown apps"** (or navigate to **Apps** → **Special app access** → **Install unknown apps**).
3. Select the app you are using to open the APK (e.g., **Files by Google**, **File Manager**, or **Chrome**).
4. Toggle **Allow from this source** to **ON**.

### Step 4: Install the App
1. Open your phone's **Files** or **Downloads** app.
2. Tap on **`MoneyGarden.apk`**.
3. Tap **Install** (or **Update**).
4. If **Google Play Protect** displays a prompt saying *"Unrecognized app"* or *"Blocked by Play Protect"*:
   - Tap **"More details"** (or the small arrow dropdown).
   - Tap **"Install anyway"**.
5. Once complete, tap **Open** to launch **Money Garden**.

---

## 🚀 Version History & Changes (v1.0 to v1.4)

| Version | Build | Key Updates & Features |
| :--- | :--- | :--- |
| **v1.4** | **5** | **Google Sign-In & Firebase Auth**: Secure Google authentication via Jetpack `CredentialManager`, user profile dialog, app title updated to **Money Garden**, in-app version badges, and updated root `MoneyGarden.apk`. |
| **v1.3** | **4** | **Opening Balances Wizard**: Easily configure starting cash in hand, bank accounts, and initial friend receivables/payables without dummy transactions; zero-out data reset option. |
| **v1.2** | **3** | **Friends Expense Splitting**: Full shared expense support (equal and custom splits, friend-paid expenses, debt settlement receipts, clear "Who owes who" statements). |
| **v1.1** | **2** | **Accounting Engine & Indian Currency**: Double-entry ledger with integer paise accuracy, Indian Lakh formatting (`₹1,25,000.00`), auditable balance sheet (`Assets = Liabilities + Equity`). |
| **v1.0** | **1** | **Initial Core Release**: Virtual money garden gamification (5 plant growth stages), savings goals tracker, and categorized daily expense & income ledger. |

---

## 🌟 Key Highlights & Philosophy

1. **User Authentication & Google Sign-In:**
   - Seamless sign-in with your Google Account powered by Jetpack `CredentialManager` and Firebase Authentication.
   - Tap your user avatar in the top app bar to view account details, email, and sign out at any time.

2. **Accounting-Grade Accuracy:**
   - Every financial transaction posts balanced debits and credits (`sum(debit) == sum(credit)`).
   - All amounts are computed in integer minor units (**paise**, 1 INR = 100 paise) to eliminate floating-point rounding errors.
   - Beautiful Indian number formatting (`₹1,25,000.50`, `₹250.00`).
   - True auditable ledger: transactions are never deleted silently. Any correction is posted as a balanced reversal journal entry linked to the original.

3. **Smart Shared Expenses & Dynamic Friends Register:**
   - **Full Friend Management:** Add and delete friends directly from the Friends screen, with options to delete individual friends or clear the register. All legacy pre-populated friends have been removed so your register is completely user-controlled.
   - **Dynamic User Name:** On first sign-in, you are asked how you'd like to be addressed. All greetings ("Hello, Manoj! 🌿"), who-paid options ("[Name] Paid", "Friend Paid for [Name]"), and split statements update dynamically based on your chosen name (editable anytime in the Profile modal).
   - Equal splits, unequal splits, and multi-friend splits.
   - Clearly separates **personal expenditure** from **receivables owed by friends**.
   - Supports purchases where a friend pays for you (records a payable without touching cash or bank funds).
   - Repayments of receivables are treated as collection of assets (never artificial income).
   - Repayments of payables are treated as settlement of liabilities (never new expenses).
   - Clear human-friendly statements: *"[Friend] owes [You] ₹250.00"*, *"[You] owe [Friend] ₹180.00"*, *"[You] and [Friend] are settled up! ✨"*.

4. **The Virtual Money Garden & Positive Gamification:**
   - Custom-drawn 5-stage plant visualizer (Seed 🌰 → Tender Sprout 🌱 → Growing Bush 🌿 → Budding Flower 🌸 → Money Tree in Bloom 🌳).
   - Savings goals track real intentions within bank/cash funds without creating duplicate financial assets.
   - **"No-Spending Today" Check-in:** Users can check in to maintain consistency routines without fabricating fake financial transactions.
   - 10 Genuine, verifiable achievements: *First Seed*, *Getting Organised*, *Consistency Champion*, *Receipt Ready*, *Balance Checker*, *Settlement Star*, *Savings Starter*, *Goal Getter*, *Money Detective*, and *Financially Organised*.

5. **Explainable Money Health Score:**
   - 0–100 score based on recordkeeping habits, reconciliation, and split reviews—never penalizing low income or necessary expenses.
   - Actionable tips to water and nurture the garden.

6. **Financial Reports & Audit:**
   - Income & Personal Expenditure breakdown by category.
   - Complete Balance Sheet (`Assets = Liabilities + Equity`) mathematically verified.
   - Cash & Bank movement statement.
   - CSV Ledger Export with properly escaped quotes and headers.
   - Monthly and Weekly review wizard.
   - Account Balance Reconciliation wizard.

---

## 🏗️ Architecture & Technology Stack

- **Platform:** Native Android (Kotlin & Jetpack Compose).
- **Authentication:** Firebase Auth & Jetpack Credential Manager (Google Sign-In).
- **Architecture:** MVVM + Clean Architecture + Repository Pattern.
- **Database:** Room (SQLite) with transactional consistency (`@Transaction`), foreign keys, and reactive `Flow`.
- **Theming & Design:** Material Design 3 (M3) palette with soft mint green, deep teal, soft lavender, warm cream, and golden accents.
- **Testing:** Local JVM JUnit & Robolectric testing for CUJs and complete accounting rules.

---

## 🧪 Testing Verification

The project includes unit and Robolectric tests in `app/src/test/java/com/example/`:
- Personal expense balances debits and credits and reduces payment account.
- Shared expenses accurately divide personal expense from receivables.
- Friend-paid expenses credit payables without reducing bank funds.
- Unequal splits sum exactly to total purchase amounts.
- Reversals flip debits and credits and restore ledger balances.
- Repayments do not create artificial income or expense.
- Balance Sheet balances (`Assets == Liabilities + Equity`).
- Indian numbering handles lakhs and paise accurately.

To execute tests via Gradle:
```bash
gradle :app:testDebugUnitTest
```
