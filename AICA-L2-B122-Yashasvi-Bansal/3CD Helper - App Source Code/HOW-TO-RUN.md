# How to run 3CD Helper on your own computer

1. Install Node.js 20 or newer (https://nodejs.org).
2. Open a terminal in this folder and run: `npm install`
3. Create a Supabase project, run the SQL files in `drizzle/migrations/` in number order, then copy
   `.env.example` to `.env` and put that project's URL and publishable key in it.
   (The quickest way to see the app is the live demo link and login given in the main README.)
4. Start the app: `npm run dev` and open the address it prints.
5. Create an account, a firm, a client and an assessment year, then press **Bring data (all clauses)**
   and choose **Connect to Tally** (with the demo TallyPrime data open) or a Tally XML export.

Tally Connector (to bring data straight from TallyPrime): Chrome → chrome://extensions → Developer mode →
Load unpacked → choose the "3cd-tally-connector" folder. In TallyPrime: F1 → Settings → Connectivity →
TallyPrime acts as "Both", port 9000.
