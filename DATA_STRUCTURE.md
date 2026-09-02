# 📊 Data Structure & File Format Reference

## Overview

This document explains all data files used in the Stock Statement UDIN Automation Tool, their structure, and how to manage them.

All data is stored in **JSON format** (JavaScript Object Notation) in the `StockStatementData` folder.

---

## 1️⃣ `clients.json` - Client Master Data

### Purpose
Stores information about all your bank clients for whom you issue stock statements and drawing power certificates.

### File Location
```
StockStatementData/clients.json
```

### Data Structure

```json
[
  {
    "name": "MODESTY DIGITAL",
    "pan": "KCWPK6654L",
    "address": "surat",
    "gst": "24KCWPK6654L1ZK",
    "bank": "bank of india",
    "branch": "Ashram Road Branch",
    "loanAccountNo": "CC/OD-4021589631",
    "sanctionLimit": 1000000
  },
  {
    "name": "Another Client",
    "pan": "AABBCC1234D",
    "address": "Full Address Here",
    "gst": "24AABBCC1234D1ZZ",
    "bank": "HDFC Bank",
    "branch": "Branch Name",
    "loanAccountNo": "CC-ACCOUNT-NO",
    "sanctionLimit": 5000000
  }
]
```

### Field Descriptions

| Field | Type | Length | Example | Required |
|-------|------|--------|---------|----------|
| `name` | String | Any | "MODESTY DIGITAL" | ✅ Yes |
| `pan` | String | 10 chars | "KCWPK6654L" | ✅ Yes |
| `address` | String | Any | "Surat, Gujarat" | ✅ Yes |
| `gst` | String | 15 chars | "24KCWPK6654L1ZK" | ✅ Yes |
| `bank` | String | Any | "Bank of India" | ✅ Yes |
| `branch` | String | Any | "Ashram Road Branch" | ✅ Yes |
| `loanAccountNo` | String | Any | "CC/OD-4021589631" | ✅ Yes |
| `sanctionLimit` | Number | Numeric | 1000000 | ✅ Yes |

### How to Add a New Client

1. Open `clients.json` in any text editor (Notepad, VS Code, etc.)
2. Add a new entry before the closing bracket `]`
3. Follow the JSON format exactly (commas, quotes, braces matter!)
4. Save the file
5. Restart the application

### Example - Adding New Client

**Before:**
```json
[
  { "name": "MODESTY DIGITAL", "pan": "KCWPK6654L", ... },
  { "name": "TRIDENT DIGITAL", "pan": "APFPV3494R", ... }
]
```

**After:**
```json
[
  { "name": "MODESTY DIGITAL", "pan": "KCWPK6654L", ... },
  { "name": "TRIDENT DIGITAL", "pan": "APFPV3494R", ... },
  {
    "name": "NEW CLIENT NAME",
    "pan": "ABCD1234E",
    "address": "City Name",
    "gst": "24ABCD1234E1ZZ",
    "bank": "Bank Name",
    "branch": "Branch Name",
    "loanAccountNo": "CC/OD-12345",
    "sanctionLimit": 2500000
  }
]
```

### PAN Format Validation
- **Length**: Exactly 10 characters
- **Format**: 5 letters + 4 numbers + 1 letter
- **Example**: KCWPK6654L ✅

### GSTIN Format Validation
- **Length**: Exactly 15 characters
- **Format**: 2-digit state code + PAN (10) + Z (1) + Check digit (1)
- **Example**: 24KCWPK6654L1ZK ✅
- **State Code**: First 2 digits (24 = Gujarat, 27 = Maharashtra, 29 = Karnataka, etc.)

---

## 2️⃣ `profiles.json` - CA Profile & Credentials

### Purpose
Stores your CA's ICAI credentials and firm information for UDIN certificate generation.

### File Location
```
StockStatementData/profiles.json
```

### Data Structure

```json
[
  {
    "id": "ca-1787725356322-wb6tq",
    "label": "Shapy - Atul Talaviya",
    "icaiUsername": "159692@icai.org",
    "savePassword": true,
    "icaiPassword": "YourPassword123",
    "lastUsed": true,
    "firmName": "S H A P Y AND ASSOCIATES",
    "caName": "CA ATUL TALAVIYA",
    "membershipNo": "159692",
    "frn": "124268W",
    "firmAddress": "411, 4th Floor, Mahek Icon, Sumul dairy Road, Surat-395008, Gujarat, India",
    "certificatePlace": "Surat"
  }
]
```

### Field Descriptions

| Field | Type | Format | Required | Example |
|-------|------|--------|----------|---------|
| `id` | String | Unique ID | Auto-generated | "ca-1787725356322-wb6tq" |
| `label` | String | Display name | ✅ Yes | "Shapy - Atul Talaviya" |
| `icaiUsername` | String | Email format | ✅ Yes | "159692@icai.org" |
| `icaiPassword` | String | Plain text | ✅ Yes | "YourPassword123" |
| `savePassword` | Boolean | true/false | ✅ Yes | true |
| `lastUsed` | Boolean | true/false | Auto-managed | true |
| `firmName` | String | Registered name | ✅ Yes | "S H A P Y AND ASSOCIATES" |
| `caName` | String | CA's full name | ✅ Yes | "CA ATUL TALAVIYA" |
| `membershipNo` | String | ICAI membership | ✅ Yes | "159692" |
| `frn` | String | Firm Registration | ✅ Yes | "124268W" |
| `firmAddress` | String | Full address | ✅ Yes | "411, 4th Floor..." |
| `certificatePlace` | String | City name | ✅ Yes | "Surat" |

### How to Add a New Profile

1. Open `profiles.json`
2. Add a new profile object
3. Generate unique ID (can use timestamp + random string)
4. Set only ONE profile to `"lastUsed": true`
5. Save the file

### ICAI Username Format
⚠️ **Critical**: Must be in email format
```
MEMBERSHIP_NUMBER@icai.org
```

**Examples:**
```
✅ Correct:   159692@icai.org
❌ Wrong:     atul.talaviya@gmail.com
❌ Wrong:     159692
❌ Wrong:     159692@icai
```

---

## 3️⃣ `stock.json`, `debtors.json`, `creditors.json` - Financial Data

### Purpose
Stores PDF backups and financial statement information.

### File Structure

```json
[
  {
    "id": "1787825140961-7ntvs5jdd9b",
    "name": "SUNDRY DEBTORS.pdf",
    "type": "application/pdf",
    "size": 2146,
    "data": "JVBERi0xLjMNCjYgMCBvYmoNCjw8DQovTGVuZ3...",
    "category": "debtors"
  }
]
```

### Field Descriptions

| Field | Purpose |
|-------|---------|
| `id` | Unique identifier |
| `name` | File name |
| `type` | MIME type (always "application/pdf") |
| `size` | File size in bytes |
| `data` | Base64 encoded PDF content |
| `category` | Category: "debtors", "creditors", "stock", or "other" |

**Note**: These files are auto-generated. You don't need to manually edit them.

---

## 4️⃣ `other.json` - Additional Data

### Purpose
Stores miscellaneous financial data not in other categories.

### File Structure
```json
[]
```

**Note**: Usually empty unless you have additional data categories.

---

## 5️⃣ Form State Files - Auto-Backup

### Files Generated
```
stock-statement_active-tab-*.json
stock-statement_cert-counter_*.json
stock-statement_migrated-to-files-*.json
```

### Purpose
Application automatically saves form state and counters for data recovery.

**Example Content:**
```json
"details"    // Currently active tab
```

```json
19           // Certificate counter (how many generated)
```

```json
"2026-08-26T06:08:09.298Z"  // Migration timestamp
```

**Note**: These are auto-managed. Don't edit manually.

---

## 6️⃣ Step Recordings - Debugging

### Files Generated
```
steps-20260826-130024.txt
steps-20260826-130024.jsonl
```

### Purpose
Records ICAI form interactions for debugging failed automations.

### File Content Example

```
ICAI UDIN - recorded steps
started 20260826-130024

   1. pointerdown   username  label='Username'
   2. focusin       username  label='Username'
   3. click         username  label='Username'
   ...
```

**Use Case**: If UDIN auto-fill fails, the step recording helps debug what went wrong.

---

## 📋 Sample Data Templates

### Template 1: Minimum Required Client

```json
{
  "name": "Client Name",
  "pan": "ABCD1234E",
  "address": "City, State",
  "gst": "24ABCD1234E1ZZ",
  "bank": "Bank Name",
  "branch": "Branch Name",
  "loanAccountNo": "CC/OD-XXXXXX",
  "sanctionLimit": 1000000
}
```

### Template 2: Complete Client Entry

```json
{
  "name": "XYZ INDUSTRIES PVT LTD",
  "pan": "AABCT5055K",
  "address": "123, Industrial Park, Surat, Gujarat 395007",
  "gst": "24AABCT5055K1ZA",
  "bank": "State Bank of India",
  "branch": "Ashram Road Branch",
  "loanAccountNo": "CC/OD-4021589631",
  "sanctionLimit": 5000000
}
```

### Template 3: Multiple Clients (Array Format)

```json
[
  {
    "name": "Client One",
    "pan": "AAAA0001A",
    "address": "Location 1",
    "gst": "24AAAA0001A1ZZ",
    "bank": "Bank A",
    "branch": "Branch A",
    "loanAccountNo": "CC-001",
    "sanctionLimit": 1000000
  },
  {
    "name": "Client Two",
    "pan": "BBBB0002B",
    "address": "Location 2",
    "gst": "24BBBB0002B1ZZ",
    "bank": "Bank B",
    "branch": "Branch B",
    "loanAccountNo": "CC-002",
    "sanctionLimit": 2000000
  }
]
```

---

## 🔄 Data Import/Export Workflow

### Exporting Client Data to Excel

1. Open `StockStatementData/clients.json`
2. Copy the content
3. Use online JSON to Excel converter (google: "JSON to Excel")
4. Download as `.xlsx` file
5. Edit in Excel

### Importing from Excel to JSON

1. Save Excel file as `.csv` (comma-separated values)
2. Use online CSV to JSON converter
3. Copy the JSON output
4. Paste into `clients.json`
5. Verify format is correct
6. Save

**Tools:**
- JSON to Excel: convertjson.com
- Excel to JSON: convertcsv.com

---

## ✅ Data Validation Checklist

Before importing/adding data, verify:

- [ ] PAN is exactly 10 characters
- [ ] GSTIN is exactly 15 characters
- [ ] State code in GSTIN matches actual state (24=GJ, 27=MH, 29=KA, etc.)
- [ ] Bank name is spelled correctly
- [ ] Account number format is correct
- [ ] Sanction limit is in rupees (no commas in JSON number)
- [ ] No special characters in names except hyphen
- [ ] All required fields are filled
- [ ] JSON syntax is valid (matching braces, commas, quotes)

---

## 🐛 Common Errors

### Error 1: JSON Syntax Error
**Symptom**: Application won't load or says "Invalid JSON"

**Cause**: Mismatched quotes, missing comma, or extra comma

**Fix Example**:
```json
❌ "name": "Client Name"   // Missing comma
❌ "address": "Address'}   // Wrong quote type

✅ "name": "Client Name",
✅ "address": "Address"
```

### Error 2: Invalid PAN/GSTIN
**Symptom**: ICAI form shows error during submission

**Cause**: Wrong format or length

**Fix**:
- PAN: Must be exactly 10 characters (5 letters + 4 numbers + 1 letter)
- GSTIN: Must be exactly 15 characters

### Error 3: Client Dropdown Empty
**Symptom**: Client dropdown in form shows no options

**Cause**: clients.json is empty or has JSON error

**Fix**:
1. Check `clients.json` is not empty `[]`
2. Validate JSON at jsonlint.com
3. Restart application

---

## 📈 Sample Data Statistics

### Current Data (August 2026)

```
Total Clients: 18
├── Debtors: 1 PDF backup (2,146 bytes)
├── Creditors: 1 PDF backup (1,570 bytes)
└── Stock: Stored in stock.json

CA Profiles: 1
└── Shapy - Atul Talaviya (FRN: 124268W)

Certificates Generated: 19
Last Updated: 2026-08-26
```

---

## 🔐 Data Security Best Practices

1. **Backup Regularly**
   - Copy entire `StockStatementData` folder
   - Store in secure location
   - Keep version history

2. **Protect Credentials**
   - Don't share `profiles.json`
   - Don't upload to cloud unencrypted
   - Change ICAI password regularly

3. **Validate Data**
   - Before bulk import, validate in Excel
   - Use PAN/GSTIN validator tools
   - Test with one client first

4. **Audit Trail**
   - Step recordings help audit UDIN submissions
   - Keep old recordings for compliance
   - Review before year-end audit

---

## 📞 Troubleshooting Data Issues

| Problem | Solution |
|---------|----------|
| Can't add client | Check JSON syntax at jsonlint.com |
| Client not visible in dropdown | Restart application after saving |
| ICAI login fails | Verify username format: `MEMBERSHIPNO@icai.org` |
| Certificate counter wrong | Delete `.json` counter file and restart |
| Data lost after restart | Check if file was saved (not just closed) |

---

**Last Updated**: August 26, 2026  
**Version**: V21  
**Format**: JSON
