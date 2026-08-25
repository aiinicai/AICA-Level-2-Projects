# PuruNiti Smart Billing Manager

A professional, offline, GST-compliant desktop billing and timesheet management application built with Python and PyQt5. Designed for consultants, professionals, and small businesses to manage invoicing, client databases, timesheets, received payments, and accounts export seamlessly.

---

## 🔑 Default Administrator Credentials

When the database is initialized on the first run, the system automatically provisions a default administrator account:

*   **Username**: `admin`
*   **Password**: `admin123`
*   **Security Question**: `"What is the default role?"`
*   **Security Answer**: `"admin"`

> [!IMPORTANT]
> For security, it is highly recommended that you change the default administrator password immediately after logging in. Navigate to the top header menu and click **Change Password** or use the **User Settings** menu to manage accounts.

---

## 🛠️ Stacks & Technologies

*   **GUI Framework**: PyQt5 (Python binding for Qt v5)
*   **Database**: SQLite (local single-file database engine)
*   **PDF Generation**: ReportLab (programmatic PDF document rendering)
*   **Spreadsheet Reports**: openpyxl (compiles styled Excel ledgers)
*   **Word Guides**: python-docx (compiles Microsoft Word documentation)
*   **Binary Compilation**: PyInstaller (packages standalone Windows executables)

---

## 🚀 How to Run the Application

### Option A: Standalone Windows Binary (Recommended)
You do not need to install Python or dependencies to run the compiled application. Just open the executable:
👉 **File Location**: [**`dist/PuruNiti_Smart_Billing_system.exe`**](file:///c:/Users/CA%20Shyam%20Sharma/OneDrive/Desktop/AI%20Work/Level%202/Day%203/Test/PuruNitiBilling/dist/PuruNiti_Smart_Billing_system.exe)

### Option B: Running from Python Source
If you wish to run the project from source, ensure you have Python 3.10+ installed and follow these steps:

1.  **Clone or Open the project directory** in your terminal.
2.  **Install dependencies** using `requirements.txt`:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Launch the main program**:
    ```bash
    python main.py
    ```

---

## 📋 Core System Features

1.  **GST-Compliant Invoicing**: Automatically determines Intrastate (CGST/SGST) vs. Interstate (IGST) tax based on State GSTIN codes. Supports Reverse Charge Mechanism (RCM), customizable cess rates, round-offs, and automated Indian currency "Amount in Words" conversion.
2.  **Multi-Seller Profiles**: Register multiple trade company details and switch profiles dynamically. Invoices will automatically pull details (bank account, address, GSTIN, letterhead) from the active seller configuration.
3.  **Timesheet Tracking**: Log project hours, tasks, rates, and conversion parameters. Generate draft sales invoices directly from completed timesheets with automatic GST calculation.
4.  **Received Payments & Aging Analysis**: Track client outstanding balances, log part/full receipts, and view receivables segmented into custom aging brackets (e.g., 0-30, 30-60, 60-90, 90+ days).
5.  **Period-Filtered Receipts Ledger**: Filter logged payments by Month, Custom Date Range, or Financial Year (April–March) and export the ledger to a styled Excel sheet.
6.  **Tally XML & accounting Exporters**: Generate compliant XML files to import Ledgers and Sales Vouchers directly into Tally Prime/Tally ERP 9, or export CSV sheets for Zoho Books and QuickBooks.
7.  **Template Styles**: Switch themes dynamically (e.g., *Classic Elegant*, *Modern Minimalist*, *Professional Compact*) to customize the look of generated PDFs.

---

## 🧪 Running Unit & GUI Tests

Three test suites are included to verify functionality:

1.  **GUI Validation & Flow Simulator**:
    ```bash
    python test_gui_crash.py
    ```
2.  **User Authentication & Payments Logic**:
    ```bash
    python test_payments_auth.py
    ```
3.  **Timesheet & Layout Exporter Test**:
    ```bash
    python test_timesheet.py
    ```

---

## 📦 How to Rebuild the Executable

If you modify the source files and want to regenerate the standalone `.exe` binary, run the automated build script:
```bash
python build_exe.py
```
The compiled binary will be placed inside the `dist/` directory.
