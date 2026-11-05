# 🍳 What's cooking today?
### *AI-Powered Multi-Cuisine Zero-Waste Meal Planner & Progressive Web App (PWA)*

[![Python Version](https://img.shields.io/badge/Python-3.11%2B-blue.svg?logo=python&logoColor=white)](https://python.org)
[![Django Version](https://img.shields.io/badge/Django-5.x%20%7C%206.x-092E20.svg?logo=django&logoColor=white)](https://djangoproject.com)
[![HTMX](https://img.shields.io/badge/HTMX-1.9%2B-336699.svg?logo=htmx&logoColor=white)](https://htmx.org)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-3.x-38B2AC.svg?logo=tailwind-css&logoColor=white)](https://tailwindcss.com)
[![Alpine.js](https://img.shields.io/badge/Alpine.js-3.x-8BC0D0.svg?logo=alpine.js&logoColor=white)](https://alpinejs.dev)
[![PWA Ready](https://img.shields.io/badge/PWA-100%25%20Installable-ea580c.svg?logo=pwa&logoColor=white)](https://web.dev/progressive-web-apps/)
[![Test Suite](https://img.shields.io/badge/Tests-15%20Passing-success.svg?logo=pytest&logoColor=white)](#-automated-testing)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

A lively, mobile-responsive, and production-grade Progressive Web Application that tackles daily household food waste and solves the universal question: **"What's cooking today?"**. 

Featuring an intelligent **2 Meals Per Day Engine (☀️ Lunch & 🌙 Dinner)**, multi-cuisine culinary generation (**Desi Rasoi 🇮🇳**, **Pan-Asian Wok 🥢**, and **Continental Bistro 🍝**), dynamic shelf-life inventory tracking, and distraction-free cooking timers with audio synthesis.

---

## 📸 Core Features & Highlights

- 🍱 **Dual Meal Planner (2/Day):** Plan Lunch & Dinner across 3 rolling days with 1-click scheduling.
- 🚨 **Urgent Shelf-Life Pantry:** Highlighting perishable ingredients in animated Red/Amber alert badges before they spoil.
- 🤖 **Hybrid AI Recipe Engine:** Powered by Google Gemini 1.5 Flash with a robust zero-latency offline heuristic fallback.
- 📷 **Computer Vision Receipt Scanner:** Upload supermarket receipts or paste grocery lists for instant AI ingestion.
- 👨‍🍳 **Distraction-Free Cooking Mode:** Step-by-step visual cards, culinary action icons (`🔪`, `🍳`, `🍲`), and interactive countdown timers with Web Audio API chime alerts.
- 🛒 **Smart Aisle-Grouped Shopping List:** 1-click "Move Bought Items to Pantry" batch inventory conversion.
- 📱 **Full Progressive Web App (PWA):** Installs natively on Android, iPhone (iOS Safari), Windows, and macOS without an app store middleman.

---

## 🏗️ System Architecture

```
┌────────────────────────────────────────────────────────┐
│                      CLIENT UI                         │
│   Tailwind CSS (CDN) + HTMX 1.9+ + Alpine.js 3.x       │
│   PWA Service Worker + Web Audio API Chimes            │
└───────────────────────────┬────────────────────────────┘
                            │ Dynamic DOM Swaps / REST
                            ▼
┌────────────────────────────────────────────────────────┐
│                   DJANGO APPLICATION                   │
│   pantryzero_core (Settings, URLs, WSGI)               │
│   pantry (Models, Views, Context Processors, Tests)    │
└─────────────┬────────────────────────────┬─────────────┘
              │                            │
              ▼                            ▼
┌──────────────────────────┐  ┌──────────────────────────┐
│      SERVICES LAYER      │  │     PERSISTENCE (DB)     │
│   services/ai_service.py │  │   SQLite (Zero Config)   │
│   - Google Gemini Flash  │  │   - HouseholdProfile     │
│   - Offline Fallback     │  │   - PantryItem           │
│   - Vision OCR Parser    │  │   - Recipe               │
└──────────────────────────┘  │   - MealQueueItem        │
                              │   - ShoppingItem         │
                              └──────────────────────────┘
```

---

## ⚡ Quickstart & Local Installation

### Prerequisites
- Python 3.11 or higher
- Git (optional)

### 1. Clone or Extract the Project
```bash
git clone https://github.com/<YOUR_USERNAME>/khane-mein-kya-hain.git
cd khane-mein-kya-hain
```

### 2. Set Up Virtual Environment (Recommended)
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS / Linux:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run Migrations & Seed Default Data
```bash
python manage.py migrate
python manage.py seed_kitchen
```

### 5. Launch the Server
```bash
python manage.py runserver 0.0.0.0:8000
```
Open **[http://127.0.0.1:8000/](http://127.0.0.1:8000/)** on your computer, or access it from your mobile phone via your local Wi-Fi network!

---

## 🧪 Automated Testing

The project includes 15 automated unit tests verifying data models, shelf-life categorization, AI fallback generation, and HTMX endpoints:

```bash
python manage.py test
```
```text
Creating test database for alias 'default'...
...............
----------------------------------------------------------------------
Ran 15 tests in 0.603s

OK
```

---

## 📱 Progressive Web App (PWA) Installation

| Device Platform | Installation Mechanism | Standalone Experience |
| :--- | :--- | :--- |
| **Android (Chrome)** | Tap "Install App" or "Add to Home Screen" | Full screen, native splash screen & icon |
| **iPhone / iPad (Safari)** | Tap Share (`⬆️`) $\rightarrow$ "Add to Home Screen" (`+`) | Standalone window with iOS status bar |
| **Desktop (Chrome/Edge)** | Click `⊕ Install` icon in the address bar | Dedicated desktop window & taskbar icon |

---

## 🎓 Capstone Submission Deliverables

- **Full Capstone Project Report:** [`CAPSTONE_REPORT.md`](CAPSTONE_REPORT.md)
- **Automated Packaging Tool:** Run `python package_capstone.py` to generate a fresh submission archive (`Whats_Cooking_Today_Capstone.zip`) for Google Drive or academic portals.

---

## 📄 License
This project is open-source and available under the [MIT License](LICENSE).
