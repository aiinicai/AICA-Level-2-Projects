# 🎓 CAPSTONE PROJECT REPORT

## Project Title: **What's cooking today?**
### *An Intelligent Multi-Cuisine Zero-Waste Meal Planner & Progressive Web Application*

---

### **Project Metadata**
- **Domain:** Full-Stack Web Development, Applied Artificial Intelligence & Human-Computer Interaction (HCI)
- **Primary Tech Stack:** Python 3.11+, Django 5.x / 6.x, HTMX 1.9+, Alpine.js 3.x, Tailwind CSS, Google Gemini Flash API, SQLite
- **Architecture Pattern:** Model-View-Template (MVT) with HTML-Over-The-Wire (Hotwire / HTMX) & Progressive Web App (PWA)
- **Test Coverage:** 15 Automated Unit Tests (100% Pass Rate)

---

## 1. Executive Summary & Problem Statement

### 1.1 The Problem
Global municipal food waste statistics indicate that over **1.3 billion metric tons** of edible food are discarded annually. A significant portion of this waste originates at the household level due to:
1. **Perishable Ingredient Expiration:** Items purchased with good intentions (e.g., spinach, paneer, cream) spoil unnoticed in the refrigerator.
2. **Daily Decision Fatigue:** The universal question *"What's cooking today?"* often leads to impulsive takeout orders while fresh groceries rot at home.
3. **Cuisine Disconnect:** Existing meal planning apps enforce rigid Western dietary frameworks with ingredients rarely found in modern multicultural kitchens (e.g., Indian, Indo-Chinese, Pan-Asian pantries).

### 1.2 The Solution
**What's cooking today?** is a production-grade, zero-waste AI culinary planner designed to solve both problems simultaneously. It prioritizes perishable ingredients across a 3-tier shelf-life model (`URGENT`, `THIS_WEEK`, `STAPLE`), schedules **2 culturally tailored meals per day** (☀️ Lunch & 🌙 Dinner), and delivers a distraction-free cooking experience with interactive voice/audio kitchen timers.

---

## 2. Key System Capabilities

| Feature Module | Technical Implementation | Practical Benefit |
| :--- | :--- | :--- |
| **Urgent Shelf-Life Pantry** | Dynamic Django ORM filtering + HTMX instant DOM updates | Highlights expiring items in glowing amber/rose badges, preventing waste. |
| **Multi-Cuisine Recipe AI** | Google Gemini Flash LLM + Heuristic deterministic fallback | Curates recipes across Indian, Pan-Asian, and Continental cuisines instantly. |
| **Rolling 2-Meals/Day Queue** | Composite relational model (`planned_for` $\times$ `meal_slot`) | Distinguishes between afternoon Lunch and evening Dinner schedules. |
| **Receipt / Grocery OCR** | Pillow Image processing + Gemini Multimodal Vision API | Digitizes paper supermarket receipts into categorized pantry inventory. |
| **Distraction-Free Cook Mode** | Alpine.js reactive states + HTML5 Web Audio API | Full-screen step checklist with synthesized audio kitchen timers. |
| **PWA Installability** | Web App Manifest + Service Worker network-first caching | Installable on Android, iPhone, Windows, macOS with native-app feel. |

---

## 3. System Architecture & Component Design

```
+-------------------------------------------------------------------------+
|                              CLIENT LAYER                               |
|  - Tailwind CSS 3.x (Mobile, Tablet, Desktop Responsive Design)        |
|  - HTMX 1.9+ (Dynamic partial DOM updates, zero full-page reloads)      |
|  - Alpine.js 3.x (Local reactive states, cooking checklists, timers)    |
|  - Web Audio API (Synthesized acoustic kitchen chime alerts)            |
|  - Service Worker (Offline asset caching & PWA lifecycle management)    |
+------------------------------------+------------------------------------+
                                     |  HTTP / JSON / HTML Partial Stream
                                     v
+-------------------------------------------------------------------------+
|                           APPLICATION LAYER                             |
|                           (Django 5.x / 6.x)                            |
|                                                                         |
|  [pantry/views.py]                                                      |
|   ├── pantry_list / pantry_quick_add / pantry_delete                    |
|   ├── recipe_suggest / recipe_save / recipe_cook_mode                   |
|   ├── planner_view / queue_schedule_meal / shopping_toggle              |
|   └── manifest_view / service_worker_view                               |
|                                                                         |
|  [pantry/context_processors.py]                                         |
|   └── Real-time urgent alerts, pantry counts, and dynamic local IP      |
+-------------------+---------------------------------+-------------------+
                    |                                 |
                    v                                 v
+-----------------------------+     +-------------------------------------+
|        AI SERVICES          |     |          DATA PERSISTENCE           |
|    (services/ai_service.py) |     |              (SQLite)               |
|                             |     |                                     |
| - Google Gemini 1.5 Flash   |     | - HouseholdProfile                  |
| - Multimodal Receipt Vision |     | - PantryItem (Tiered shelf-life)    |
| - Offline Multi-Cuisine     |     | - Recipe (Ingredients & Steps JSON) |
|   Heuristic Fallback Engine |     | - MealQueueItem (Lunch & Dinner)    |
|                             |     | - ShoppingItem (Aisle Categorized)  |
+-----------------------------+     +-------------------------------------+
```

---

## 4. Database Schema (Entities & Relationships)

1. **`HouseholdProfile`**: Singleton record managing family preferences (Vegetarian, Vegan, Non-Veg, Jain), appliances owned (Air Fryer, Instant Pot, Oven, Skillet), and default servings.
2. **`PantryItem`**: Represents stored groceries categorized by shelf-life tiers:
   - `URGENT`: Expiring within 48 hours (Red Alert).
   - `THIS_WEEK`: Fresh produce (Amber Alert).
   - `STAPLE`: Spices, grains, pulses, and condiments (Stable Green).
3. **`Recipe`**: Structured culinary entry storing dish photography (`image_url`), cuisine classification (`INDIAN`, `PAN_ASIAN`, `CONTINENTAL`), prep/cook times, structured ingredients list, and step-by-step instructions with timer durations.
4. **`MealQueueItem`**: Dynamic planner entry linking a `Recipe` to a calendar slot (`TONIGHT`, `TOMORROW`, `UPCOMING`) and meal period (`LUNCH`, `DINNER`).
5. **`ShoppingItem`**: Supermarket checklist item grouped by supermarket aisle with 1-click batch conversion into active `PantryItem` records upon purchase.

---

## 5. Verification & Automated Test Suite

A rigorous suite of **15 automated unit tests** validates system reliability across all core flows:
- `PantryModelTests`: Verifies model string representations, shelf-life categorization, and badge colors.
- `MealQueueTests`: Confirms ordering logic, lunch/dinner slot assignments, and completion states.
- `AIServiceTests`: Validates multi-cuisine fallback generation, structured JSON compliance, and prompt parsing.
- `PantryViewTests`: Asserts HTTP 200 responses, HTMX partial rendering, and context processor badge counts.

```bash
$ python manage.py test
Creating test database for alias 'default'...
...............
----------------------------------------------------------------------
Ran 15 tests in 0.603s

OK
```

---

## 6. Conclusion & Future Scope

**What's cooking today?** demonstrates that modern, hyper-responsive web applications can be delivered using Python and Django without the excessive architectural overhead of heavy client-side JavaScript frameworks. 

### Future Enhancements:
- **Barcode & UPC Scanning:** Direct camera integration for packaged food items via QuaggaJS.
- **Nutritional Analytics:** Automated macronutrient calculation (Protein, Carbs, Fats) per meal.
- **Collaborative Family Sync:** WebSockets via Django Channels for live updates across multiple family members' phones.
