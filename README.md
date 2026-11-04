# InsightFlow AI — Business Dashboard Generator

Upload a CSV or Excel file and get a business analytics dashboard: KPIs, charts,
rule-based insights, and anomaly detection — automatically, from whatever columns
your file happens to have.

## Run it locally

```bash
npm install
npm run dev
```

Then open the URL Vite prints (usually http://localhost:5173).

To build a production bundle:

```bash
npm run build
npm run preview
```

## How it works

Every dataset goes through the same seven-stage pipeline (see `src/lib/`):

1. **Parse** (`parseFile.js`) — reads .csv/.xlsx/.xls into `{ headers, rows }`. Never assumes column order.
2. **Validate** (`validate.js`) — structural checks (empty file, empty rows, duplicate headers). Warns, doesn't crash.
3. **Detect Columns** (`detectColumns.js`) — scores every header by name *and* by sampling its values, then greedily maps headers to roles (date, revenue, profit, quantity, product, category, region, customer). A column that isn't recognized is simply left unmapped.
4. **Normalize** (`normalize.js`) — converts raw cells to typed values (Date/number/text). A bad cell only nulls that one field, never the row.
5. **Calculate Metrics** (`metrics.js`) — builds KPI cards, but only for roles that were actually detected.
6. **Generate Charts** (`chartData.js`) — builds chart datasets, only for column combinations that exist (e.g. revenue-over-time needs both date and revenue).
7. **Generate Insights** (`insights.js`) — a local, rule-based insight engine (no API key needed) that reads only the aggregates already computed upstream. `anomalies.js` runs IQR outlier detection and period-over-period % change detection alongside it.

Because every stage only reacts to what it's given, the app works unchanged whether
your file has 3 columns or 12, in any order, under any names — as long as the
detector can find something date-, revenue-, or category-like in the header text
or the values themselves.

## Try it without a file

Click **"Try demo dataset"** on the upload screen for ~500 rows of synthetic order
data (with a touch of realistic messiness) across regions, categories, and products.

## Stack

React + Vite, Tailwind CSS v4, Recharts, PapaParse (CSV), SheetJS/xlsx (Excel).
No backend, no auth, no external API calls — everything runs in the browser.
