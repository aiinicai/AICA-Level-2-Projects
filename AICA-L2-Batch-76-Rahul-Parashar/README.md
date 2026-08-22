# CFO Multi-Layered Financial Dashboard

Upload any Ratio-file-template workbook (sheets named `Financials_Standalone` / `Financials_Consol`,
`Ratio Analysis` / `Ratio Analysis_Conso`) and get a live, drillable 21-page dashboard — parsed
entirely client-side, no data leaves the browser except the one AI chat endpoint.

## Run it

```bash
npm run install:all   # once
npm run dev            # starts backend (8787) + frontend (5173)
```

Open http://localhost:5173, then either drag in your own `.xlsx` or click **"Load demo data"** to
use the bundled Endurance Technologies sample.

## Enable the AI chat / causal-chain explanations

```bash
cp backend/.env.example backend/.env
# then edit backend/.env and set ANTHROPIC_API_KEY=sk-ant-...
```

Without a key, the app still works fully — the chat widget and the causal-chain's "in plain
English" sentence just show a graceful fallback instead of an AI-generated one.

## What's deliberately not built (MVP scope)

- No persistence: re-uploading resets the dashboard; peer-comparison data clears on refresh.
- No live competitor-data fetch (the peer panel has upload + manual entry only).
- Cash Flow Statement is a genuine empty state — this template's CFS tabs are not parsed because
  the sample workbook never populated them.

## Project layout

- `frontend/` — React 18 + Vite + Tailwind v3. All parsing, charts, and routing live here.
- `backend/` — a single Express endpoint (`/api/chat`) that keeps the Anthropic API key server-side.
- `frontend/src/lib/parseWorkbook.js` — the label-based, header-detecting Excel parser; this is
  the part that has to work on a workbook it's never seen before.
