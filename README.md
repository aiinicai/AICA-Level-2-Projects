# BharatBill Enterprise GST v2.0

## What's New in v2.0

### 1. Multi-Company ERP Support
You can now manage **multiple business entities** from a single installation.

**How to use:**
- Click **Company Manager** in the sidebar (🏢) or press `Ctrl+Shift+C`
- Click **➕ New Company** to create a second/third company profile
- Each company gets its own isolated data: invoices, purchases, parties, stock, accounts
- Use the **🏢 company switcher dropdown** in the top header bar to instantly switch between companies
- Or click **🔄 Switch Active** next to any company in Company Manager
- The currently active company is shown in the header bar — all screens refresh automatically

### 2. GSTR-2B Reconciliation
Automatically match your GST portal's GSTR-2B (auto-drafted ITC statement) against purchase bills recorded in the ERP.

**How to use:**
1. Download your GSTR-2B JSON file from the GST Portal (gst.gov.in → Returns → GSTR-2B → Download JSON)
2. In the app, go to **🧾 GSTR-2B Reconciliation** in the sidebar (or press `Ctrl+2`)
3. Select the Financial Year
4. Click **📂 Browse GSTR-2B JSON** and select the downloaded file
5. Click **▶ Run Reconciliation**
6. Review the results in four tabs:
   - ✅ **Matched** — supplier invoice found in books with matching GST
   - ⚠️ **Amt Differs** — found in books but GST amount doesn't match (needs correction)
   - ❌ **In 2B Only** — supplier filed GST but you haven't recorded the bill (record purchase)
   - 📖 **In Books Only** — you recorded the bill but supplier hasn't filed (follow up)
7. Click **📥 Export CSV** to save the reconciliation report

## Running the Application
Double-click `run_app.bat` or:
```
python main.py
```

## Default Login
- Username: `admin`
- Password: `admin123`

## Requirements
```
pip install -r requirements.txt
```