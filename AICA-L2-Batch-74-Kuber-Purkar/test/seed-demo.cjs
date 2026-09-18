// Seeds a realistic demo client into a data dir via the running server API,
// after validating it through the real CMA engine (BS tally + ratios).
// Run:  node test/seed-demo.cjs <target-data-dir> [port]
const path = require('path');
const { execSync, spawn } = require('child_process');

const ROOT = path.resolve(__dirname, '..');
const DATA_DIR = path.resolve(process.argv[2] || './data-demo-seed');
const PORT = Number(process.argv[3] || 8095);

const client = {
  id: 'demo-ganesh-engg',
  name: 'Shree Ganesh Engineering Works',
  updatedAt: new Date().toISOString(),
  config: {
    clientName: 'Shree Ganesh Engineering Works',
    startYear: 2023,
    actualYears: 2,
    estimatedYears: 1,
    projectedYears: 5,
    unit: 'lakhs',
    assetBlocks: [
      { id: 'plantMachinery', name: 'Plant & Machinery', rate: 15, opening: 85 },
      { id: 'building', name: 'Factory Building', rate: 10, opening: 40 },
      { id: 'furniture', name: 'Furniture & Fixtures', rate: 10, opening: 6 },
      { id: 'computer', name: 'Computers & Equipment', rate: 40, opening: 3 },
      { id: 'other1', name: 'Vehicles', rate: 15, opening: 8 },
      { id: 'other2', name: 'Other Assets', rate: 15, opening: 0 },
    ],
    customHeads: [
      { id: 'ch1', name: 'Job Work Charges', kind: 'expense', current: false },
      { id: 'ch2', name: 'Security Deposit (Electricity)', kind: 'asset', current: false },
    ],
    loan: {
      loanType: 'both',
      ccLimit: 60, ccRate: 10.5,
      ccStockMarginPct: 25, ccDebtorMarginPct: 40, ccDebtorCoverDays: 90,
      tlAmount: 75, tlRate: 9.5, tlTenureMonths: 66, tlMoratoriumMonths: 6,
      grantMonthIndex: 6, emiDay: 10, grantDay: 5,
    },
    actuals: [
      {
        label: '2023-24', months: 12,
        salesDomestic: 385, salesExport: 0, otherIncome: 4,
        rmOpening: 22, rmPurchases: 218, rmClosing: 26,
        powerFuel: 14, directLabour: 28,
        salary: 24, freight: 7.5, salesPromo: 3.5, travelAdmin: 4.2,
        repairs: 5.5, professionalFees: 2.8, operatingExp: 6.5, otherExp: 3.2,
        customExp1: 0, customExp2: 0, customExp1Name: '', customExp2Name: '',
        depreciation: 0, interestCC: 5.2, interestTL: 6.8, bankCharges: 0.9, tax: 11, dividend: 0,
        fixedAssets: 128, deposits: 4, investments: 2, debtors: 58, cash: 6.5, otherCurrentAssets: 3,
        shareCapital: 25, reserves: 59, termLoan: 65, cc: 48, unsecured: 10,
        creditors: 22, otherCurrentLiab: 5,
        customValues: { ch1: 6.5, ch2: 3 },
      },
      {
        label: '2024-25', months: 12,
        salesDomestic: 432, salesExport: 18, otherIncome: 5,
        rmOpening: 26, rmPurchases: 246, rmClosing: 31,
        powerFuel: 16, directLabour: 32,
        salary: 27, freight: 8.5, salesPromo: 4.2, travelAdmin: 4.8,
        repairs: 6, professionalFees: 3.2, operatingExp: 7.2, otherExp: 3.6,
        customExp1: 0, customExp2: 0, customExp1Name: '', customExp2Name: '',
        depreciation: 0, interestCC: 5.6, interestTL: 6.2, bankCharges: 1.0, tax: 12.5, dividend: 0,
        fixedAssets: 122, deposits: 4.5, investments: 2, debtors: 72, cash: 8, otherCurrentAssets: 4,
        shareCapital: 25, reserves: 69.5, termLoan: 58, cc: 55, unsecured: 8,
        creditors: 26, otherCurrentLiab: 5,
        customValues: { ch1: 7.5, ch2: 3 },
      },
    ],
  },
  sim: {
    salesGrowth: 12, marginAdj: 0, inventoryDays: 30, debtorDays: 55, creditorDays: 35,
    taxRate: 25, dividendPct: 15, minCashBalance: 2,
    tlAssetBlockId: 'plantMachinery', manualAssetAdditions: {},
  },
};

async function main() {
  // 1. Validate through the real engine (bundle it like the other tests)
  execSync(`npx esbuild src/engine/cmaEngine.ts --bundle --platform=node --format=cjs --outfile=test/engine.bundle.cjs --external:node:*`, { cwd: ROOT, stdio: 'inherit' });
  const { runCma } = require(path.join(ROOT, 'test', 'engine.bundle.cjs'));
  const result = runCma(client.config, client.sim);
  console.log('\n=== Engine validation ===');
  for (const y of result.years) {
    console.log(
      `${y.year} (${y.type}): bsDiff=${y.bsDifference.toFixed(2)} ` +
      `CR=${y.currentRatio.toFixed(2)} DSCR=${y.dscr.toFixed(2)} DER=${y.debtEquity.toFixed(2)} ` +
      `TOL/TNW=${y.tolTnw.toFixed(2)} ICR=${y.interestCoverage.toFixed(2)} ` +
      `PAT=${y.pat.toFixed(1)} MPBF=${y.mpbf.toFixed(1)}`
    );
  }

  // 2. Seed directly into the SQLite store (no server / license needed)
  const fs = require('fs');
  const { DatabaseSync } = require('node:sqlite');
  fs.mkdirSync(DATA_DIR, { recursive: true });
  const db = new DatabaseSync(path.join(DATA_DIR, 'cma.db'));
  db.exec(`CREATE TABLE IF NOT EXISTS clients (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, data TEXT NOT NULL, updated_at TEXT NOT NULL)`);
  db.prepare('INSERT INTO clients (id, name, data, updated_at) VALUES (?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET name=excluded.name, data=excluded.data, updated_at=excluded.updated_at')
    .run(client.id, client.name, JSON.stringify(client), client.updatedAt);
  const rows = db.prepare('SELECT name FROM clients').all();
  console.log('\n=== Seeding ===');
  console.log(`Clients in store: ${rows.length} → ${rows.map(r => r.name).join(', ')}`);
  db.close();
  console.log(`\n✓ Seeded into ${DATA_DIR}`);
}

main().catch(e => { console.error(e); process.exit(1); });
