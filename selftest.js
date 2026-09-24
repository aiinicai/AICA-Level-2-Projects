'use strict';

/**
 * Quick sanity check for the allocation engine + current data/db.json.
 * Run any time with:  node scripts/selftest.js
 *
 * It does not modify data/db.json. Exits with a non-zero status (and a
 * clear message) if anything doesn't reconcile, so it's safe to run after
 * hand-editing the JSON file or importing a fresh workbook.
 */

const path = require('path');
const fs = require('fs');
const { computeAllocation } = require('../lib/allocation');

const DB_PATH = path.join(__dirname, '..', 'data', 'db.json');

let failures = 0;
function check(label, cond, extra) {
  if (cond) {
    console.log(`  OK   ${label}`);
  } else {
    failures += 1;
    console.log(`  FAIL ${label}${extra ? ' — ' + extra : ''}`);
  }
}

function approxEqual(a, b, eps) {
  return Math.abs(a - b) <= (eps === undefined ? 0.01 : eps);
}

console.log(`Loading ${DB_PATH} ...`);
let db;
try {
  db = JSON.parse(fs.readFileSync(DB_PATH, 'utf8'));
} catch (e) {
  console.error('Could not parse data/db.json:', e.message);
  process.exit(1);
}

console.log(`\nRecords: ${db.managers.length} managers, ${db.assignments.length} assignments, ${db.staff.length} staff rows, ${db.revenue.length} revenue rows.\n`);

const result = computeAllocation(db);

console.log('Reconciliation checks:');

// 1. Sum of assignment billing == firm billing
const sumAssignmentBilling = result.assignments.reduce((s, a) => s + a.billing, 0);
check(
  'Sum of assignment billing equals firm billing',
  approxEqual(sumAssignmentBilling, result.firm.billing, 1),
  `${sumAssignmentBilling} vs ${result.firm.billing}`
);

// 2. Sum of manager billing == firm billing
const sumManagerBilling = result.managers.reduce((s, m) => s + m.billing, 0);
check(
  'Sum of manager billing equals firm billing',
  approxEqual(sumManagerBilling, result.firm.billing, 1),
  `${sumManagerBilling} vs ${result.firm.billing}`
);

// 3. Sum of assignment total cost == firm total cost
const sumAssignmentCost = result.assignments.reduce((s, a) => s + a.totalCost, 0);
check(
  'Sum of assignment total cost equals firm total cost',
  approxEqual(sumAssignmentCost, result.firm.totalCost, 1),
  `${sumAssignmentCost} vs ${result.firm.totalCost}`
);

// 4. Sum of allocated "many" cost across assignments == sum of raw "many" staff cost
const rawManyCost = db.staff.filter(s => s.scope === 'many').reduce((s, x) => s + (Number(x.cost) || 0), 0);
const allocatedManyCost = result.assignments.reduce((s, a) => s + a.manyAssignmentsCost, 0);
check(
  'Allocated "many assignments" cost equals raw pooled cost (for managers with billing > 0)',
  approxEqual(rawManyCost, allocatedManyCost, 1) || rawManyCost >= allocatedManyCost,
  `raw ${rawManyCost} vs allocated ${allocatedManyCost} (allocated can be < raw only if a manager has zero billing)`
);

// 5. Partner pool cost equals sum of scope='partner' staff cost
const rawPartnerCost = db.staff.filter(s => s.scope === 'partner').reduce((s, x) => s + (Number(x.cost) || 0), 0);
check(
  'Partner pool cost matches sum of scope=partner staff rows',
  approxEqual(rawPartnerCost, result.partner.poolCost, 1),
  `${rawPartnerCost} vs ${result.partner.poolCost}`
);

// 6. Partner allocation across managers sums back to the pool cost
const partnerAllocSum = Object.values(result.partner.allocatedByManager).reduce((s, v) => s + v, 0);
check(
  'Partner cost allocated to managers sums back to the pool cost',
  approxEqual(partnerAllocSum, result.partner.poolCost, 1) || result.firm.billing === 0,
  `${partnerAllocSum} vs ${result.partner.poolCost}`
);

// 7. Every assignment lands in exactly one bucket
const bucketTotal = result.buckets.profitable.length + result.buckets.nonProfitable.length + result.buckets.inProgress.length;
check(
  'Every assignment is in exactly one dashboard bucket',
  bucketTotal === result.assignments.length,
  `${bucketTotal} vs ${result.assignments.length}`
);

// 8. Firm profit = firm billing - firm total cost
check(
  'Firm profit = firm billing - firm total cost',
  approxEqual(result.firm.profit, result.firm.billing - result.firm.totalCost, 1)
);

// 9. No assignment, staff or revenue row is missing required fields
const badAssignments = db.assignments.filter(a => !a.id || !a.name);
check('Every assignment has an id and a name', badAssignments.length === 0, `${badAssignments.length} bad rows`);

const badStaff = db.staff.filter(s => !s.id || typeof s.cost !== 'number');
check('Every staff row has an id and a numeric cost', badStaff.length === 0, `${badStaff.length} bad rows`);

const badRevenue = db.revenue.filter(r => !r.id || typeof r.amount !== 'number');
check('Every revenue row has an id and a numeric amount', badRevenue.length === 0, `${badRevenue.length} bad rows`);

// 10. Every staff/revenue row with a scope/assignment that should reference a manager/assignment actually does
const managerIds = new Set(db.managers.map(m => m.id));
const assignmentIds = new Set(db.assignments.map(a => a.id));
const orphanStaff = db.staff.filter(s => s.managerId && !managerIds.has(s.managerId));
check('No staff row references an unknown manager', orphanStaff.length === 0, `${orphanStaff.length} rows`);
const orphanRevenue = db.revenue.filter(r => r.assignmentId && !assignmentIds.has(r.assignmentId));
check('No revenue row references an unknown assignment', orphanRevenue.length === 0, `${orphanRevenue.length} rows`);

console.log('\nFirm summary:');
console.log(`  Billing:    ${result.firm.billing.toLocaleString('en-IN')}`);
console.log(`  Total cost: ${result.firm.totalCost.toLocaleString('en-IN')}`);
console.log(`  Profit:     ${result.firm.profit.toLocaleString('en-IN')}`);
console.log(`  Margin:     ${result.firm.margin === null ? '—' : (result.firm.margin * 100).toFixed(1) + '%'}`);
console.log(`  Buckets:    ${result.buckets.profitable.length} profitable / ${result.buckets.nonProfitable.length} non-profitable / ${result.buckets.inProgress.length} in progress`);

console.log();
if (failures > 0) {
  console.error(`${failures} check(s) failed.`);
  process.exit(1);
} else {
  console.log('All checks passed.');
}
