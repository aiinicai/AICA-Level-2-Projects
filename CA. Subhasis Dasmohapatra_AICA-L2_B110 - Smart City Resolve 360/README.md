# RESOLVE 360 – Smart City Command Center

Offline, browser-only dashboard that prioritises smart-city service issues
from `data/smart_city_issues.csv`.

## Project structure

```
resolve360/
├── index.html                 Page layout
├── css/styles.css             Visual design
├── js/config.js               Settings, weights, recommended actions
├── js/data.js                 Embedded copy of the CSV (auto-generated)
├── js/csv.js                  CSV parsing, validation, export
├── js/scoring.js              Priority score, risk band, HTML escaping
├── js/app.js                  Loading, filters, rendering, events
├── data/smart_city_issues.csv Input dataset (240 records)
└── tools/build_data_js.py     Rebuilds js/data.js from the CSV
```

## Run

Option A – double-click `index.html` (uses the embedded copy in js/data.js).

Option B – local server (reads the CSV file directly):

```
cd resolve360
python -m http.server 8000
```
Then open http://localhost:8000

## Update the data

Replace `data/smart_city_issues.csv`, then run `python tools/build_data_js.py`.
Or use the **Upload CSV** button in the app.
