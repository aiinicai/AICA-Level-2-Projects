# 🧸 Toys Exchange — Full-Stack Python Platform

> **"Connecting outgrown modern toys and early learning materials with childhood joy across the globe."**

An enterprise-grade, full-stack Python application built with **FastAPI**, **SQLite (WAL mode)**, **Jinja2**, **Tailwind CSS**, and **PyInstaller**. Designed to address the household storage crisis and social stigma of outgrown modern toys in middle/upper-class homes by directing them through verified NGOs to impoverished children and community orphanages.

---

## 📋 Table of Contents
1. [Core Features & Social Workflow](#-core-features--social-workflow)
2. [System Architecture](#-system-architecture)
3. [Live Demo Credentials & Role Switcher](#-live-demo-credentials--role-switcher)
4. [Quick Start Guide](#-quick-start-guide)
5. [Automated Testing Suite](#-automated-testing-suite)
6. [Generating a Standalone Desktop `.exe`](#-generating-a-standalone-desktop-exe)
7. [REST API Documentation](#-rest-api-documentation)
8. [Production Deployment Instructions](#-production-deployment-instructions)

---

## 🌟 Core Features & Social Workflow

### 1. 🎁 Donation Portal (`/donate`)
* **Overcoming Stigma & Space Bottlenecks:** Provides high-income and middle-class parents with an anonymous, direct route to donate outgrown modern toys without awkward family hand-downs.
* **Photo & Specs Upload:** Drag-and-drop image upload (supporting PNG, JPG, WEBP, SVG) with auto-categorization.
* **Granular Attributes:** Title, category (*Toy*, *Early Learning*, *Play Equipment*), condition (*Like New*, *Gently Used*, *Needs Repair*), and age group (*0-2*, *3-5*, *6-8*, *9-12+*).
* **Institutional Flag:** Dedicated checkbox to route bulky gear (swings, slides, bouncy castles) directly to community facilities.

### 2. 🔍 Marketplace & Selection (`/browse`)
* **Real-Time Dynamic Search:** Instant client-side and server-side keyword searching across titles, locations, and descriptions.
* **Multi-Factor Filters:** Filter by category, condition, pipeline status, and institutional equipment.
* **Interactive Claiming:** Verified NGOs can claim available items with 1 click.

### 3. 🛠️ NGO Facilitation Dashboard (`/ngo-dashboard`)
* **Condition Assessment:** Dedicated refurbishment queue for items flagged as *Needs Repair*.
* **Reconditioning Logger:** Log sanitization (UV-C / steam), repairs (seam stitching, battery replacements, motor tests), and upgrade conditions to *Refurbished - Like New*.
* **Stewardship Transfer:** Track claimed items from receipt to final handover.

### 4. 🚚 Shipping & Global Logistics (`/shipments`)
* **Automated Batch Manifests:** Generates unique tracking codes (`TE-SHP-2026-XXXX`).
* **Multi-Modal Carriers:** Support for DHL Global Forwarding, Maersk Aid Logistics, Astral Aviation, and Emirates SkyCargo.
* **Interactive Stepper:** Track shipments through 4 visual milestones: *Dispatched* &rarr; *In Transit* &rarr; *Customs Clearance* &rarr; *Delivered to Children*.

### 5. 🌍 Global Distribution Tracking (`/global-distribution`)
* **Targeted Impoverished Footprint:** Explicit tracking for remote regions and African nations where modern toys and STEM books are inaccessible:
  * 🇰🇪 **Kenya:** 1,840 toys delivered · 32 institutions served · 5,600 children smiling
  * 🇺🇬 **Uganda:** 1,120 toys delivered · 24 institutions served · 3,450 children smiling
  * 🇧🇩 **Bangladesh:** 980 toys delivered · 19 institutions served · 2,890 children smiling
  * 🇪🇹 **Ethiopia:** 760 toys delivered · 15 institutions served · 2,150 children smiling
  * 🇵🇭 **Philippines:** 640 toys delivered · 12 institutions served · 1,920 children smiling
  * 🇭🇳 **Honduras:** 410 toys delivered · 9 institutions served · 1,230 children smiling
* **Regional Filters:** Sub-Saharan Africa, South Asia, Southeast Asia, Latin America.

### 6. 🏫 Institutional Allocation (`/institutions`)
* **Bulky Play Equipment Routing:** Diverts heavy, high-volume items (commercial bounce houses, double swing sets, rotating seesaws) directly to collective playgrounds.
* **Verified Registry:** Pre-configured with vetted orphanages, primary schools, and refugee shelters (e.g. *St. Jude Children's Orphanage*, *Kibera Primary School*, *Dhaka Slum Educational Mission*).

### 7. 🛡️ Superadmin Control Center (`/admin`)
* **NGO Credential Verification:** Admin approval portal with 1-click verification of non-profit credentials.
* **User & Role Directory:** Manage Donors, NGOs, and Administrators.
* **Live Audit Stream:** View all recently added inventory with removal capability.
* **One-Click Database Reset:** Re-seeds dummy database for testing anytime.

---

## 🏗️ System Architecture

```
toys_exchange/
├── app/
│   ├── config.py              # Application settings, ports, and base paths
│   ├── database.py            # SQLite connection with WAL mode & dictionary rows
│   ├── models.py              # Pydantic schemas and request validators
│   ├── seed_data.py           # Populates realistic dummy database & SVG graphics
│   ├── main.py                # FastAPI ASGI application & static mount
│   ├── routes/
│   │   ├── api.py             # RESTful API endpoints (/api/toys, /api/shipments...)
│   │   └── views.py           # HTML template views (/browse, /donate, /admin...)
│   ├── static/
│   │   ├── css/custom.css     # Dot pattern, animations, status tags
│   │   ├── js/app.js          # Role switcher, modals, notifications, AJAX flows
│   │   └── uploads/           # Uploaded photos & vector illustrations
│   └── templates/             # Responsive Jinja2 templates with Tailwind CSS
│       ├── base.html          # Global layout, sticky nav, mobile menu, toast
│       ├── index.html         # Hero, stats ribbon, 3 steps, global impact preview
│       ├── browse.html        # Marketplace grid & multi-filter search
│       ├── donate.html        # Donation portal with drag-and-drop photo upload
│       ├── my_donations.html  # Donor tracking ledger
│       ├── ngo_dashboard.html # Refurbishment work queue & action modals
│       ├── shipments.html     # Logistics ledger & tracking stepper
│       ├── global_distribution.html # African & remote territory impact tracker
│       ├── institutions.html  # Orphanage allocation module
│       └── admin.html         # Superadmin dashboard & NGO verification
├── tests/
│   ├── test_models.py         # Schema and database integrity tests
│   ├── test_api.py            # REST API integration tests
│   └── test_workflows.py      # End-to-end full user journeys
├── desktop_launcher.py        # Desktop runner (embedded server + browser launch)
├── build_exe.py               # Automated PyInstaller packaging script
├── requirements.txt           # Version-pinned production dependencies
├── run.sh                     # One-click start script for macOS & Linux
└── run.bat                    # One-click start script for Windows
```

---

## 🎭 Live Demo Credentials & Role Switcher

A top banner with a **Live Role Switcher** is present on every page:
1. **Donor (Sarah Jenkins - Toronto):** Can donate toys and inspect status in `/my-donations`.
2. **Donor (David Chen - Dubai):** Alternate international donor.
3. **NGO (Dr. Amina Osei - Hope for Childhood Global, Nairobi):** Can claim available toys, log refurbishment, and dispatch cargo.
4. **NGO (Marcus Vance - Bright Start Foundations, London):** Secondary partner NGO.
5. **Platform Admin (Alex Rivera):** Has master administrative access to approve pending NGOs and reset demo data.

---

## 🚀 Quick Start Guide

### Prerequisites
* Python 3.10+ (Standard Python from python.org)

### 1. Installation
```bash
# Navigate to directory
cd toys_exchange

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS / Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Run Desktop / Web Application
Simply run the start script or launcher:
```bash
# macOS / Linux:
./run.sh
# Or directly:
python3 desktop_launcher.py

# Windows:
run.bat
# Or directly:
python desktop_launcher.py
```
The launcher will:
1. Initialize the SQLite database and seed dummy records automatically.
2. Find an available local port.
3. Launch the server.
4. Automatically open your default web browser to `http://127.0.0.1:8000/`.

---

## 🧪 Automated Testing Suite

The application includes a comprehensive test suite covering database constraints, API endpoints, and end-to-end user workflows.

Run all tests:
```bash
pytest tests -v
```

### Test Coverage Highlights:
* `test_models.py`: Verifies database table creation, foreign keys, and seed integrity.
* `test_api.py`: Tests marketplace filtering, photo upload, claim logic, refurbishment logging, institutional routing, and shipment lifecycles.
* `test_workflows.py`: Validates complete multi-role journeys:
  * Family Donates &rarr; NGO Claims &rarr; Reconditions &rarr; Dispatches &rarr; Delivered to Kenyan Orphanage.
  * Bulky Playground Equipment directly routed to Children's Orphanage.
  * NGO Registration &rarr; Admin Review &rarr; NGO Verification.

---

## 📦 Generating a Standalone Desktop `.exe`

To package the entire Python application into a single executable that users can double-click without needing to install Python:

### Step 1: Install PyInstaller (Included in requirements.txt)
```bash
pip install pyinstaller
```

### Step 2: Build Executable
Run the included build script:
```bash
python build_exe.py
```

### Output:
* **On Windows:** Produces `dist/ToysExchange.exe`
* **On macOS:** Produces `dist/ToysExchange`
* **On Linux:** Produces `dist/ToysExchange`

### How the Standalone Executable Works:
1. Bundles Python runtime, FastAPI, Uvicorn, SQLite engine, templates, and static assets into a single binary.
2. When double-clicked, it starts an embedded local server in memory and opens the user's desktop browser to the application interface.
3. No configuration, environment setup, or technical steps required for end users.

---

## 📡 REST API Documentation

FastAPI provides interactive Swagger documentation out of the box:
* **Interactive UI:** `http://localhost:8000/docs`
* **OpenAPI Schema:** `http://localhost:8000/openapi.json`

### Key Endpoints:
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/stats` | Platform KPIs and global humanitarian metrics |
| `GET` | `/api/toys` | Filter toys by category, condition, status, search |
| `GET` | `/api/toys/{id}` | Detailed toy metadata & refurbishment log history |
| `POST` | `/api/toys` | Upload a new toy donation with photo |
| `POST` | `/api/toys/{id}/claim` | NGO claims an available toy |
| `POST` | `/api/toys/{id}/refurbish` | Log refurbishment work and mark ready for dispatch |
| `POST` | `/api/toys/{id}/route-institutional` | Direct allocation of large gear to an orphanage |
| `GET` | `/api/institutions` | List partner orphanages and primary schools |
| `POST` | `/api/institutions` | Register a new partner institution |
| `GET` | `/api/shipments` | List global logistics shipments |
| `POST` | `/api/shipments` | Generate a consolidated dispatch batch |
| `PATCH` | `/api/shipments/{id}/status` | Advance shipment milestone (Transit/Customs/Delivered) |
| `GET` | `/api/global-distribution` | Regional metrics and country footprint |
| `POST` | `/api/users/{id}/verify` | Admin approval for NGO credentials |
| `POST` | `/api/admin/reset-database` | Reset database to clean demo state |

---

## 🌐 Production Deployment Instructions

### Deploy to Cloud VPS (Ubuntu / Debian / AWS / DigitalOcean)
```bash
# 1. Clone repository and install dependencies
git clone <repo-url>
cd toys_exchange
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Run with production ASGI server (Gunicorn with Uvicorn workers)
pip install gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:8000
```

### Docker Deployment
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN python -m app.seed_data
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```
Build and run:
```bash
docker build -t toys-exchange .
docker run -p 8000:8000 toys-exchange
```
