# ✈️ Travel Tails - Desktop Travel Itinerary & Package Downloader

**Travel Tails** is a desktop application built in Python using **PyQt5** that creates travel packages and executive itineraries with rates in **Indian Rupee (INR ₹)** and downloads them into structured PDF files.

---

## 📦 Required Libraries & 1-Line Pip Install

All required libraries can be installed with a single horizontal command in Command Prompt (`cmd`):

```cmd
pip install PyQt5 reportlab requests pillow beautifulsoup4 qrcode
```

### Library Breakdown:
| Library | Purpose |
| :--- | :--- |
| **`PyQt5`** | Modern desktop user interface, location drop-downs, progress bar & activity console |
| **`reportlab`** | Executive 8-page PDF generation matching authentic agency format with INR (`₹`) support |
| **`requests`** | Web crawling, real landmark photography acquisition, and PDF downloads |
| **`pillow`** | Real photo resizing, thumbnail processing, and airplane route graphics |
| **`qrcode`** | Dynamic generation of scannable UPI payment QR codes for the Bank Details section |
| **`beautifulsoup4`** | Web scraping for embedded PDF links (`<embed>`, `<iframe>`, `<object>`, `<a href="...">`) |

---

## 🚀 How to Run

### Method 1: Using Python IDLE (Beginner-Friendly)
1. Open **Python IDLE**.
2. Go to **File ➔ Open...** and select `travel_tails.py`.
3. Press **`F5`** (or click **Run ➔ Run Module**).
4. The **Travel Tails** window will open immediately with large, clear fonts!

### Method 2: Double-Click Launcher (Windows)
- Simply double-click [`run_travel_tails.bat`](run_travel_tails.bat) in this folder.

### Method 3: Command Line
```cmd
python travel_tails.py
```

---

## 🌟 Key Features

1. **Exact Transit Connectivity Intelligence (Train 🚆 vs. Flight ✈️)**:
   - **Non-Airport Origins Handled**: Intelligently identifies cities without commercial airports (e.g. `Bareilly`, `Haridwar`, `Rishikesh`, `Mathura`, `Katra`, etc.).
   - **Confirmed Indian Railways Routing**: For example, choosing **Bareilly to Amritsar** automatically routes via **IRCTC Train No. 13005 / 13006 Howrah - Amritsar Mail** (Bareilly Jn `BE` ➔ Amritsar Jn `ASR`) with confirmed 2A/3A AC sleeper berths, bedroll, and meal inclusions.
   - **Dual Sector Cards**: Page 6 renders dedicated **Train 🚆** cards for rail sectors and **Flight ✈️** cards for air sectors, complete with station codes, exact departure/arrival times, and vector icons.

2. **Authentic Major Attractions for Destinations**:
   - Accurately curated landmark attractions for iconic destinations. For **Amritsar**, it includes:
     - **Sri Harmandir Sahib (Golden Temple)** & sacred **Pavitra Amrit Sarovar**
     - **Palki Sahib Ceremony** & **Guru Ka Langar Seva**
     - **Jallianwala Bagh Memorial** (Martyr's Well)
     - **Attari-Wagah Border Beating Retreat Ceremony**
     - **Historic Gobindgarh Fort & Toshakhana Treasury**
     - **Town Hall Partition Museum**
     - **Durgiana Temple (Silver Temple)**
     - Heritage dinner at legendary **Kesar Da Dhaba**

3. **Nearby Sister Destination Extensions Included in Packages**:
   - Multi-day itineraries automatically expand to include famous sister destinations and scenic hill retreats:
     - **Amritsar** incorporates **Dalhousie & Khajjiar ("Mini Switzerland of India")** and **Dharamshala & McLeod Ganj** (Tsuglagkhang Dalai Lama Temple, Bhagsu Waterfall, HPCA Stadium).
     - **Haridwar** incorporates **Rishikesh (Yoga Capital)**.
     - **Shimla** incorporates **Kufri & Chail**.
     - **Manali** incorporates **Solang Valley & Sissu (Lahaul via Atal Tunnel)**.
     - **Jaipur** incorporates **Pushkar & Ajmer**.
     - **Kashmir** incorporates **Gulmarg & Pahalgam**.

4. **Source / Country & Global Destination Intelligence**:
   - **Source / Country Input Field**: Accepts either origin city or origin country (e.g. `Bareilly`, `Bangalore`, `India`, `New Delhi`, `United States`, `United Kingdom`, etc.).
   - **Any Destination Country Supported**: Choosing **Vietnam**, **Japan**, **Switzerland**, **France**, **Italy**, **Dubai/UAE**, **Egypt**, etc., automatically produces a genuine city-wise multi-destination breakdown with exact airport names and 3-letter IATA codes (e.g. Vietnam: Hanoi `HAN` Noi Bai, Da Nang `DAD`, Saigon `SGN` Tan Son Nhat).
   - **Authentic Non-Repetitive Daily Activities**: Every single day features unique, famous landmarks (e.g. Vietnam: Ba Na Hills Golden Hand Bridge, Ha Long Bay 5-star overnight cruise, Hoi An lantern river cruise, Hanoi Temple of Literature, Cu Chi Tunnels war network).
   - **100% Real Travel Photography**: Downloads genuine high-res photographs dynamically from Unsplash CDN, Wikipedia PageImages API, and Wikimedia Commons. Completely eliminates mock placeholder cards and yellow showcase boxes.
   - **Client Parameter Inputs**: Traveller Name (`Jigeesha`), No. of Adults, No. of Children, and automatic room calculation.

5. **Executive Agency Output Itinerary (Bangalore Headquarters)**:
   - **Page 1: Trip Cover & Highlights**:
     - Large Day count (`5 Days`), Trip Title (`Amritsar Trip`), Client line (`Itinerary created for: Jigeesha`), and Passenger breakdown (`4 (Adults) 1 (Children) 0 (Infant)`).
     - Agency header (`Designed by: Travel Tails, Bangalore, India`) with branded badge.
     - Full-width real destination hero banner (e.g. Sri Harmandir Sahib Golden Temple).
     - Route summary line (`🌐 1 Country India` | `📍 Stay Amritsar 2N-- Dalhousie (Nearby) 2N`).
     - Rich narrative **Overview** and detailed **Tour Highlights** bullets (Confirmed transit Ex-Bareilly, daily buffet breakfast, private transfers, excursions).
   - **Pages 2 & 3: Comprehensive Day-by-Day Visual Itinerary**:
     - Distinct blue headers (`DAY 1 | 15-Oct-2026`).
     - 2-Column cards with real landmark photographs on the left and full activity schedules on the right.
     - Dedicated metadata badges for `🍽️ Meals : Breakfast` and `🚐 Transfer Type : Private`.
   - **Page 4: Exhaustive Daily Major Attractions & Sightseeing Schedule (Tabular Format)**:
     - 5-column tabular matrix detailing for every single day:
       - **Day & Date**: e.g. `DAY 1 | 15-Oct-2026`
       - **City / Hub**: e.g. `Amritsar (Spiritual Punjab)`
       - **Exhaustive Daily Plan & Timelines**: Full breakdown of 🌅 Morning (09:00 - 13:00), ☀️ Afternoon (13:00 - 17:00), and 🌙 Evening (17:00 - 21:30) activities
       - **Major Attractions Covered**: Specific landmark bullets (e.g. `Sri Harmandir Sahib`, `Jallianwala Bagh`, `Attari-Wagah Border Ceremony`, `Khajjiar Meadow`)
       - **Transfers & Inclusions**: Vehicle type, guide details, entry tickets, and meal inclusions
   - **Page 5: Stay and Travel Details (Accommodation Details)**:
     - Multi-city hotel cards with resort photographs, full physical addresses, check-in and check-out dates, and number of rooms.
     - Enclosed sub-strips highlighting **Room Type** (`Deluxe Superior Room`) and **Meal Plan** (`Buffet Breakfast`).
   - **Page 6: Arrival & Departure Details (Train 🚆 / Flight ✈️ Cards)**:
     - Sector cards with train name, train numbers (e.g. `13005 / 13006 Howrah - Amritsar Mail`), departure and arrival railway stations with exact timings.
     - Vector locomotive train icon 🚆 or coral airplane icon ✈️.
     - Class inclusions (Confirmed 2A / 3A AC Sleeper berths, bedroll, linen & meals).
   - **Page 7: Tour Pricing, Important Points & Bank Details**:
     - Personalized **Tour Pricing** for `<Traveller Name> Family` with **Grand Total** in INR.
     - Dedicated prominent rows for **Cost Per Person (Adult)**, **Cost Per Child**, and **Net All-Inclusive Cost Per Person**.
     - 18 standardized agency travel policies (**Important Point**).
     - **Bank Details** (ICICI Current Account, MG Road, Bengaluru) with embedded scannable **UPI Payment QR Code**.
     - **Why book with us** value propositions.
   - **Page 8: Contact Us**:
     - Clean 4-column footer layout: **Bangalore Headquarters** (Prestige Meridian, MG Road, Bengaluru - 560001), Call Us (+91 80 4123 4567), Email (bookings@traveltails.in), and Social Media channels.

---

## 🎛️ Input Customization & Preference Fields

The input section includes 6 customization parameters with enlarged, high-contrast typography (`13pt Segoe UI Bold` labels, `15px` input text, `44px` height):

| Field | Options & Details |
| :--- | :--- |
| **Increased Font Size** | High-contrast bold typography (`13pt Segoe UI Bold`, `15px` input text, `44px` height) across all input controls for optimal readability on all monitor resolutions. |
| **Hotel Star Preference** | **1 to 5 Star Preference**: Choose from `5 Star (Luxury Palaces & Resorts)`, `4 Star (Premium / Grand Hotels)`, `3 Star (Comfort & Boutique)`, `2 Star (Standard / Economy)`, `1 Star (Budget Saver)`, or `All Tiers (1 to 5 Star Comprehensive)`. Highlights properties on Page 1 & Page 5. |
| **Flights / Transit Option** | **Include vs. Exclude**: Select `✈️ Include Flights / Trains (Complete Package)` or `🏨 Exclude Flights / Trains (Land Package Only)`. Zeroes out airfare/rail fare and adapts pricing, highlights, and transit cards accordingly. |
| **Meal Plan Preference** | **Custom Meal Plans**: Choose from `🍳 Breakfast Included (CP Plan)`, `🍽️ Breakfast + Lunch / Dinner (MAP Plan - Half Board)`, `🍱 All Meals Included (AP Plan)`, or `🚫 Room Only / Excluding Meals (EP Plan)`. Automatically updates daily timelines, accommodation cards, and pricing. |
| **Cab / Private Transfer** | **Dedicated Vehicle Option**: Select `🚗 Yes - Dedicated AC Cab & Private Transfers` or `🚶 No - Cab Not Required (Self-Arranged / Transit)`. Dynamically adjusts transfer inclusions and cost deductions. |
| **Country Currency Option** | **Global Currencies**: Select `INR (₹)`, `USD ($)`, `EUR (€)`, `GBP (£)`, `AED (AED)`, `SGD (S$)`, `THB (฿)`, `VND (₫)`, `AUD (A$)`, or `CAD (C$)`. Live top header badge and real-time converted package rates and PDF cards. |



