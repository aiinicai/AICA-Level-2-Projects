# CA FIRM INTRANET — Installation Guide

## Prerequisites
- Windows PC / Server
- XAMPP (recommended) or Laragon / WAMP
- Any modern browser (Chrome, Edge, Firefox)

---

## Step 1 — Install XAMPP

Download from: https://www.apachefriends.org/download.html
- Choose PHP 8.0+ version
- Install to `C:\xampp\`
- Start **Apache** and **MySQL** from XAMPP Control Panel
- Set both Apache and MySQL to **Auto-start** (checkbox in XAMPP)

---

## Step 2 — Copy Application Files

1. Open Windows Explorer → go to `C:\xampp\htdocs\`
2. Create a new folder: `ca_intranet`
3. Copy all application files into `C:\xampp\htdocs\ca_intranet\`

Your folder structure should look like:
```
C:\xampp\htdocs\ca_intranet\
    index.php
    login.php
    dashboard.php
    clients.php
    gst_register.php
    etds_register.php
    roc_register.php
    users.php
    audit_log.php
    logout.php
    database.sql
    .htaccess
    includes/
        config.php
        header.php
        footer.php
    assets/
        css/app.css
        js/app.js
    api/
        update_status.php
```

---

## Step 3 — Create the Database

1. Open browser → go to: `http://localhost/phpmyadmin`
2. Click **"New"** in the left sidebar
3. Database name: `ca_intranet` → Collation: `utf8mb4_unicode_ci` → Click **Create**
4. Click the new `ca_intranet` database in the left sidebar
5. Click **"Import"** tab at the top
6. Click **"Choose File"** → select `database.sql` from your application folder
7. Click **"Go"** (Import button at the bottom)
8. You should see "Import has been successfully finished"

---

## Step 4 — Configure the Application

Open `includes/config.php` in Notepad and update:

```php
define('DB_HOST', 'localhost');     // Leave as localhost for XAMPP
define('DB_NAME', 'ca_intranet');   // Database name you created
define('DB_USER', 'root');          // Default XAMPP MySQL username
define('DB_PASS', '');              // Leave blank for default XAMPP (no password)
define('FIRM_NAME', 'Your Firm Name');  // ← CHANGE THIS to your firm name
```

---

## Step 5 — First Login & Setup

1. Open browser → go to: `http://localhost/ca_intranet/`
2. Login with:
   - Username: `admin`
   - Password: `password`
3. **IMMEDIATELY** change the admin password:
   - Go to Admin → User Management
   - Edit the admin user → set a strong password
4. Change passwords for all default users (partner1, supervisor1, staff1)
5. Update user names and emails to match your actual staff

---

## Step 6 — Configure Firm Details

In `includes/config.php`, update:
```php
define('FIRM_NAME', 'ABC & Associates');  // Your firm name shown in navbar/footer
```

---

## Step 7 — Network Access (Other PCs on LAN)

To allow other computers in your office to access the intranet:

1. Find your server's IP address:
   - Open Command Prompt → type `ipconfig`
   - Note the IPv4 Address (e.g., `192.168.1.100`)

2. Other users can access via: `http://192.168.1.100/ca_intranet/`

3. **Optional — Set a hostname** (easier to remember):
   - On each client PC, open `C:\Windows\System32\drivers\etc\hosts` (as Administrator)
   - Add a line: `192.168.1.100  cafirm`
   - Users can then access via: `http://cafirm/ca_intranet/`

---

## Step 8 — Auto-Start on Server Reboot

1. Open XAMPP Control Panel → click **Config** button for Apache → check **"Start with Windows"**
2. Do the same for MySQL
3. Alternatively, add XAMPP to Windows startup services via Services (services.msc)

---

## Default User Accounts

| Username    | Role       | Default Password |
|-------------|------------|-----------------|
| admin       | Admin      | password        |
| partner1    | Partner    | password        |
| supervisor1 | Supervisor | password        |
| staff1      | Staff      | password        |

⚠️ **Change all passwords immediately after installation!**

---

## Role Permissions

| Feature                    | Admin | Partner | Supervisor | Staff |
|----------------------------|-------|---------|------------|-------|
| View all clients           | ✅    | ✅      | Own only   | Own only |
| Add/Edit clients           | ✅    | ✅      | ✅         | ❌    |
| Add/Edit register entries  | ✅    | ✅      | ✅         | ❌    |
| Update status (inline)     | ✅    | ✅      | ✅         | ✅ (assigned only) |
| Bulk create entries        | ✅    | ✅      | ✅         | ❌    |
| User management            | ✅    | ✅      | ❌         | ❌    |
| Audit log                  | ✅    | ✅      | ❌         | ❌    |
| Export to Excel            | ✅    | ✅      | ✅         | ✅    |

---

## Due Date Color Code Reference

| Color     | Meaning                              |
|-----------|--------------------------------------|
| 🔴 Red    | Overdue (past due date, not filed)   |
| 🟠 Orange | Due within 7 days                    |
| 🟡 Yellow | Due within 15 days                   |
| 🔵 Blue   | Due within 30 days                   |
| 🟢 Green  | Filed / Due date is comfortable      |

---

## GST Due Dates Reference

| Return     | Type    | Due Date                              |
|------------|---------|---------------------------------------|
| GSTR-1     | Monthly | 11th of next month                    |
| GSTR-3B    | Monthly | 20th of next month                    |
| GSTR-1     | QRMP    | 13th of month after quarter end       |
| GSTR-3B    | QRMP    | 22nd of month after quarter end       |
| GSTR-9     | Annual  | 31st December of next FY              |
| GSTR-9C    | Annual  | 31st December of next FY              |
| CMP-08     | QRMP    | 18th of month after quarter end       |
| GSTR-4     | Annual  | 30th April of next FY                 |

---

## ETDS Due Dates Reference

| Quarter | Months    | Return Due Date |
|---------|-----------|-----------------|
| Q1      | Apr–Jun   | 31st July       |
| Q2      | Jul–Sep   | 31st October    |
| Q3      | Oct–Dec   | 31st January    |
| Q4      | Jan–Mar   | 31st May        |

**Challan deposit:** 7th of following month (30th April for March)

---

## ROC Due Dates Reference

| Form          | Due Date Basis                        |
|---------------|---------------------------------------|
| MGT-7/7A      | 60 days from AGM date                 |
| AOC-4         | 30 days from AGM date                 |
| ADT-1         | 15 days from AGM date                 |
| DIR-3 KYC     | 30 September every year               |
| DPT-3         | 30 June every year                    |
| MSME-1        | 30 April & 31 October (half-yearly)   |
| LLP-11        | 30 May every year                     |
| LLP-8         | 30 October every year                 |

---

## Troubleshooting

**Page shows blank / white screen:**
- Check `C:\xampp\php\logs\php_error_log` for PHP errors
- Ensure MySQL is running in XAMPP Control Panel

**Cannot connect to database:**
- Verify DB_USER and DB_PASS in `includes/config.php`
- Default XAMPP: user = `root`, password = `` (blank)

**Session expires too quickly:**
- Edit `SESSION_TIMEOUT` in `config.php` (default: 7200 = 2 hours)

**Other PCs cannot access:**
- Check Windows Firewall → allow port 80 for Apache
- Ensure all devices are on the same network/subnet

---

## Backup

Backup the database regularly via phpMyAdmin:
1. Go to `http://localhost/phpmyadmin`
2. Select `ca_intranet` database
3. Click **Export** → Quick → Format: SQL → **Go**
4. Save the .sql file to a safe location (Google Drive / USB)

---

*Application Version 1.0 | Built for PHP 8.0+ / MySQL 5.7+*
