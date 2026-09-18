const { runCma, makeEmptyActual, defaultSimParams, DEFAULT_BLOCKS } = require('./engine.cjs');
const { buildCmaWorkbook } = require('./excel.cjs');
const path = require('path');
(async () => {
  const actual = makeEmptyActual('2023-24');
  Object.assign(actual, {
    salesDomestic: 34279072, rmOpening: 900000, rmPurchases: 12176122, rmClosing: 1000000,
    powerFuel: 95887, salary: 7108379, freight: 115854, salesPromo: 264287, travelAdmin: 129402,
    repairs: 243682, professionalFees: 1572149, operatingExp: 1672671, otherExp: 5172919,
    depreciation: 1645123, interestCC: 380000, bankCharges: 74305, tax: 1409958,
    fixedAssets: 7250000, deposits: 350000, debtors: 4200000, cash: 800000, otherCurrentAssets: 200000,
    shareCapital: 5000000, reserves: 2500000, cc: 3500000, unsecured: 500000,
    creditors: 1800000, otherCurrentLiab: 600000,
    customValues: { hExp: 250000, hAst: 400000, hLiab: 300000 },
  });
  const config = { clientName: 'TEST', startYear: 2023, actualYears: 1, estimatedYears: 1, projectedYears: 2, unit: 'lakhs',
    assetBlocks: DEFAULT_BLOCKS.map(b => b.id === 'plantMachinery' ? { ...b, opening: 5000000 } : { ...b }),
    customHeads: [
      { id: 'hExp', name: 'Packing Charges', kind: 'expense', current: true },
      { id: 'hAst', name: 'GST Refund Due', kind: 'asset', current: true },
      { id: 'hLiab', name: 'GST Payable', kind: 'liability', current: true },
    ],
    loan: { loanType: 'both', ccLimit: 5000000, ccRate: 10.5, ccStockMarginPct: 25, ccDebtorMarginPct: 40, ccDebtorCoverDays: 90,
      tlAmount: 8759098, tlRate: 9.1, tlTenureMonths: 87, tlMoratoriumMonths: 6, grantMonthIndex: 1, emiDay: 10, grantDay: 10 },
    actuals: [actual] };
  const res = runCma(config, defaultSimParams());
  for (const y of res.years) {
    console.log(y.year, y.type.padEnd(10),
      'customExp:', (y.customHeadValues.hExp/1e5).toFixed(2),
      'customAst:', (y.customHeadValues.hAst/1e5).toFixed(2),
      'customLiab:', (y.customHeadValues.hLiab/1e5).toFixed(2),
      '| totExp:', (y.totalExpenses/1e5).toFixed(2),
      '| totA:', (y.totalAssets/1e5).toFixed(2), 'totL:', (y.totalLiabilities/1e5).toFixed(2),
      '| BSdiff:', Math.round(y.bsDifference),
      '| CA:', (y.currentAssets/1e5).toFixed(2), 'CL:', (y.currentLiabilities/1e5).toFixed(2));
  }
  const wb = await buildCmaWorkbook(res);
  await wb.xlsx.writeFile(path.join(__dirname, 'verify-output.xlsx'));
  console.log('excel OK, sheets:', wb.worksheets.map(w => w.name).join(', '));
})().catch(e => { console.error(e); process.exit(1); });
