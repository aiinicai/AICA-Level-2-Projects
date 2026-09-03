# Workshop360 🔧

### Smart Workshop Repair Tracking & Billing Management System

**Workshop360** is a full-stack, mobile-first web application designed for motorcycle spare-parts shops that also operate repair workshops.

The application solves a simple but common problem: **mechanics and workshop owners often forget which parts were used during a repair when preparing the final bill.**

Workshop360 creates a digital record of every part used during a repair, allowing the workshop owner to review, correct and prepare the bill accurately.

---

## 🚨 Problem Statement

In a traditional motorcycle workshop, the repair process generally works like this:

1. A customer brings a motorcycle for repair.
2. The mechanic identifies the parts that need replacement.
3. Parts are taken from the spare-parts shop and fitted to the motorcycle.
4. The mechanic continues working on the motorcycle.
5. Once the repair is completed, the owner prepares the bill.
6. Some parts may be forgotten or incorrectly recorded during billing.

This can result in:

- Missed items in customer bills
- Incorrect quantities
- Revenue leakage
- Time wasted recalling which parts were used
- Dependency on handwritten notes or memory
- Difficulty tracking workshop performance

**Workshop360 addresses this problem by recording parts at the time they are used rather than trying to reconstruct the repair afterwards.**

---

# 💡 Solution

Workshop360 provides separate interfaces for:

### 👨‍🔧 Mechanic
The mechanic records the motorcycle and adds parts/products as they are used during the repair.

### 👨‍💼 Owner
The owner can monitor ongoing repairs, review parts, correct mistakes, prepare bills and view workshop analytics.

### 🏪 Shopkeeper
The shopkeeper can perform day-to-day workshop and billing operations with almost the same operational access as the owner, while being restricted from viewing analytics and managing users.

---

# ✨ Key Features

## 🔐 Role-Based Authentication

Workshop360 supports three user roles:

- **Owner/Admin**
- **Shopkeeper**
- **Mechanic**

### Owner

The first user to register becomes the Owner/Admin.

The Owner has complete access to the application, including:

- Workshop dashboard
- Repairs
- Billing
- Mechanics
- Shopkeepers
- User approvals
- Password resets
- Analytics
- Repair history

### Mechanic

Mechanics register through the common signup page and remain in **Pending Approval** status until approved by the Owner.

Mechanics can:

- Start repairs
- Record motorcycle details
- Add parts/products
- Edit quantities
- Delete items
- Finish repairs
- View their repair records

### Shopkeeper

Shopkeepers are created by the Owner and must be approved by the Owner before accessing the application.

They can perform operational activities such as:

- View repairs
- Review parts
- Edit quantities
- Add/delete items
- Enter prices
- Prepare bills
- Finalise bills
- Generate customer PDFs

Shopkeepers **cannot access analytics or owner-level user management.**

---

# 🏍️ Repair Tracking

When a mechanic starts working on a motorcycle, they enter:

- Bike name/model
- Registration number
- Customer name (optional)
- Customer phone (optional)

A unique repair record is created.

The repair is initially marked as:

**REPAIRING**

---

# 📦 Parts & Product Tracking

While repairing the motorcycle, the mechanic can add products as they use them.

For example:

```text
Gulf Engine Oil 20W-50
Oil Filter
Brake Pad
Spark Plug
Chain Cleaner
```

The mechanic only records:

- Product/Part name
- Quantity

### No prices are required from the mechanic.

This keeps the process extremely simple and prevents mechanics from having to know or enter selling prices.

Previously used product names can also be suggested while typing, making future entries faster.

---

# ✅ Repair Completion

Once the motorcycle is fully repaired, the mechanic clicks:

**FINISH REPAIR**

After finishing:

- The repair status changes to **READY FOR BILLING**
- The mechanic can no longer edit the repair
- The Owner/Shopkeeper can review and make corrections

This prevents accidental changes after the repair has been handed over for billing.

---

# 🧾 Billing

The Owner or Shopkeeper can open a completed repair and prepare the bill.

Each item initially has a price of:

**₹0**

The Owner/Shopkeeper enters the applicable selling rate.

The application automatically calculates:

```text
Amount = Quantity × Rate
```

The Owner/Shopkeeper can also:

- Change quantity
- Change rate
- Change item name
- Add an item
- Delete an item
- Add labour charges
- Apply discount
- Apply GST/tax

All calculations update automatically.

---

# 📄 Customer PDF

After the bill is finalised, Workshop360 generates a PDF preview that can be downloaded locally to the user's device.

The customer-facing PDF is intentionally minimal.

It contains **ONLY**:

| Product / Item | Quantity | Rate |
|---|---:|---:|
| Gulf Engine Oil 20W-50 | 1 | ₹650 |
| Oil Filter | 1 | ₹250 |
| Brake Pad | 2 | ₹800 |

The PDF does **not** contain:

- Shop name
- Shop logo
- Shop address
- Customer details
- Bike details
- Mechanic name
- Bill number
- Bill date
- Labour charges
- Discount
- GST/tax
- Item amount
- Subtotal
- Grand total
- Payment information

The full billing calculation remains available inside Workshop360 for the Owner/Shopkeeper.

---

# 📊 Owner Dashboard

The Owner dashboard provides an overview of workshop operations.

It includes information such as:

- Active repairs
- Repairs ready for billing
- Completed repairs
- Today's billing
- Pending user approvals
- Which mechanic is handling which motorcycle

This allows the owner to understand the current workload without constantly asking mechanics for updates.

---

# 📈 Workshop Analytics

Workshop360 also provides basic analytics to help the Owner understand workshop performance.

Analytics include:

### Motorcycle Insights
- Frequently returning motorcycles
- Most common motorcycle models
- Repair history

### Mechanic Insights
- Repairs handled by each mechanic
- Current workload
- Average repair completion time

### Product Insights
- Most frequently used products
- Frequently used brands based on product names

Analytics can be viewed using simple time filters such as:

- Today
- This Week
- This Month

Analytics are available only to the Owner.

---

# 🔄 Repair History

Workshop360 uses the motorcycle registration number to maintain repair history.

When the same motorcycle returns, the Owner can view previous repair records, including:

- Previous repair dates
- Parts/products used
- Mechanic who handled the repair
- Previous billing information

This helps the workshop understand recurring customers and recurring repairs.

---

# 🔑 Password Management

Workshop360 intentionally avoids complicated OTP-based password recovery for workshop staff.

If a Mechanic or Shopkeeper forgets their password, they can contact the Owner.

The Owner can assign a new password to the user.

Existing passwords are never displayed.

---

# 📱 Mobile-First Design

Workshop360 is designed primarily for smartphones because mechanics will generally use their phones while working on motorcycles.

The mechanic interface focuses on:

- Large buttons
- Simple navigation
- Large readable text
- Minimal typing
- Simple terminology
- Few screens
- Clear actions

The goal is to allow a mechanic to record a part in **seconds**, without interrupting the repair workflow.

---

# 🏗️ Application Architecture

Workshop360 follows a full-stack architecture consisting of:

```text
              ┌──────────────────────┐
              │      Workshop360     │
              │      Web App         │
              └──────────┬───────────┘
                         │
             ┌───────────┴───────────┐
             │                       │
       Mechanic Interface      Owner Interface
             │                       │
             │                 Shopkeeper Interface
             │                       │
             └───────────┬───────────┘
                         │
                  Authentication
                         │
                    Backend / DB
                         │
                  Persistent Storage
```

The application uses role-based access controls to ensure that users only access features permitted for their role.

---

# 🔒 Security & Access Control

Workshop360 implements role-based access control.

For example:

```text
OWNER
 ├── Full Workshop Access
 ├── User Management
 ├── Billing
 └── Analytics

SHOPKEEPER
 ├── Workshop Operations
 ├── Billing
 └── No Analytics

MECHANIC
 ├── Own Repairs
 ├── Add Parts
 └── No Billing / Analytics
```

Backend/database-level permissions are used rather than relying only on frontend restrictions.

---

# 🎯 Core Workflow

The complete workflow can be summarised as:

```text
Mechanic Login
      ↓
Start New Repair
      ↓
Enter Bike Details
      ↓
Add Parts as Used
      ↓
Repair Completed
      ↓
FINISH REPAIR
      ↓
Repair Sent to Owner
      ↓
Owner/Shopkeeper Reviews
      ↓
Correct Quantity / Add / Delete Items
      ↓
Enter Rates
      ↓
Calculate Bill
      ↓
FINALISE BILL
      ↓
Generate PDF Preview
      ↓
Download Customer PDF
```

---

# 🌟 Benefits

### For Mechanics

- Simple interface
- No need to remember parts used
- No need to enter prices
- Faster recording
- Less paperwork

### For Owners

- Fewer missed items
- Better billing accuracy
- Real-time repair visibility
- Mechanic workload tracking
- Repair history
- Product usage insights
- Reduced dependency on memory

### For Customers

- Clear record of products used
- Simple downloadable bill
- Faster billing process

---

# 🚀 Future Scope

Workshop360 has been designed with future expansion in mind.

Potential future features include:

- Inventory management
- Automatic stock deduction
- Low-stock alerts
- Supplier management
- Purchase management
- Customer database
- WhatsApp bill sharing
- Online payments
- Customer service history
- Advanced business analytics
- Multi-branch workshop support
- PWA installation
- Native Android application
- AI-assisted repair recommendations
- OCR-based bill/part recognition
- Integration with accounting software

These features are outside the current V1 scope but can be added as the platform evolves.

---

# 🛠️ Project Objective

The primary objective of Workshop360 is to **digitise the parts-tracking and billing workflow of small and medium-sized motorcycle workshops** while keeping the interface simple enough for everyday use by mechanics.

Rather than forcing workshops to adopt a complicated ERP system, Workshop360 focuses on solving one important operational problem:

> **Record every part when it is used, so nothing is forgotten when the bill is prepared.**

---

# 📌 Project Status

**Version:** V1  
**Project Type:** Full-Stack Web Application  
**Platform:** Web / Mobile-First  
**Primary Users:** Workshop Owners, Shopkeepers & Mechanics

---

## 👨‍💻 Project

**Workshop360 — Smart Workshop Repair Tracking & Billing Management System**

Built as a capstone project demonstrating the application of:

- Full-stack web development
- Database management
- Authentication & authorisation
- Role-based access control
- CRUD operations
- Real-time data handling
- Automated calculations
- PDF generation
- Dashboard & analytics
- Mobile-first UI/UX
- AI-assisted application development
