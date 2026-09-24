'use strict';

/**
 * Profitability allocation engine for Kashyap & Co.
 *
 * Rules implemented (as specified by the firm):
 *  1. Every assignment (a client / capstone engagement) is owned by exactly
 *     one Manager.
 *  2. Billing directly attributable to an assignment = sum of billing entries
 *     - sum of credit notes recorded against that assignment.
 *  3. Staff cost is recorded with a "scope":
 *       - 'dedicated'  -> tied to one specific assignment. Added straight to
 *                          that assignment's cost.
 *       - 'many'       -> a staff member who works across several
 *                          assignments under ONE named manager ("Many
 *                          Assignments"). This cost is first pooled at the
 *                          manager level, then spread across that manager's
 *                          own assignments in proportion to each
 *                          assignment's billing vs the manager's total
 *                          billing.
 *       - 'partner'    -> the Partner's own cost, or staff who report
 *                          directly to the Partner across many assignments.
 *                          This is first spread across the four Managers in
 *                          proportion to each manager's total billing vs
 *                          firm-wide billing, and the manager-level share is
 *                          then spread across that manager's assignments in
 *                          proportion to assignment billing vs manager
 *                          billing (same two-step waterfall as above).
 *  4. Overhead = overheadRate (default 30%) x the assignment's billing, also
 *     charged as a cost.
 *  5. Profit (assignment) = Billing - (dedicated + allocated-many +
 *     allocated-partner + overhead).
 *  6. Manager and firm figures are simple roll-ups of the assignment
 *     figures.
 *
 * The engine is deliberately pure (no I/O) so it can be unit-tested and
 * reused by the server, scripts, or a future front-end build step.
 */

function computeAllocation(db) {
  const overheadRate = (db.meta && typeof db.meta.overheadRate === 'number')
    ? db.meta.overheadRate
    : 0.30;

  const managers = db.managers || [];
  const assignments = db.assignments || [];
  const staff = db.staff || [];
  const revenue = db.revenue || [];

  const realManagers = managers.filter(m => !m.isPartner);
  const managerIds = new Set(realManagers.map(m => m.id));
  const partnerManager = managers.find(m => m.isPartner);
  const partnerId = partnerManager ? partnerManager.id : 'partner';

  // ---- 1. Net billing per assignment ----
  const billingByAssignment = {};
  assignments.forEach(a => { billingByAssignment[a.id] = 0; });
  const revenueByAssignment = {};
  assignments.forEach(a => { revenueByAssignment[a.id] = []; });

  for (const r of revenue) {
    if (!(r.assignmentId in billingByAssignment)) continue; // orphaned entry, ignore safely
    const sign = r.type === 'credit' ? -1 : 1;
    billingByAssignment[r.assignmentId] += sign * (Number(r.amount) || 0);
    revenueByAssignment[r.assignmentId].push(r);
  }

  // ---- 2. Manager billing (sum of its assignments' billing) ----
  const managerBilling = {};
  realManagers.forEach(m => { managerBilling[m.id] = 0; });
  for (const a of assignments) {
    if (managerIds.has(a.managerId)) {
      managerBilling[a.managerId] += billingByAssignment[a.id] || 0;
    }
  }
  const firmBilling = Object.values(managerBilling).reduce((s, v) => s + v, 0);

  // ---- 3. Dedicated cost per assignment ----
  const directCost = {};
  assignments.forEach(a => { directCost[a.id] = 0; });
  const staffByAssignment = {};
  assignments.forEach(a => { staffByAssignment[a.id] = []; });

  const manyCostByManager = {};
  realManagers.forEach(m => { manyCostByManager[m.id] = 0; });
  const manyStaffByManager = {};
  realManagers.forEach(m => { manyStaffByManager[m.id] = []; });

  let partnerPoolCost = 0;
  const partnerStaff = [];

  for (const s of staff) {
    const cost = Number(s.cost) || 0;
    if (s.scope === 'dedicated' && s.assignmentId in directCost) {
      directCost[s.assignmentId] += cost;
      staffByAssignment[s.assignmentId].push(s);
    } else if (s.scope === 'many' && managerIds.has(s.managerId)) {
      manyCostByManager[s.managerId] += cost;
      manyStaffByManager[s.managerId].push(s);
    } else if (s.scope === 'partner') {
      partnerPoolCost += cost;
      partnerStaff.push(s);
    }
    // unrecognised / orphaned scope-manager combos are ignored defensively
  }

  // ---- 4. Allocate "many assignments" cost within each manager, by billing share ----
  const allocMany = {};
  assignments.forEach(a => { allocMany[a.id] = 0; });
  for (const mgrId of managerIds) {
    const cost = manyCostByManager[mgrId] || 0;
    const mb = managerBilling[mgrId] || 0;
    if (cost <= 0 || mb <= 0) continue;
    for (const a of assignments) {
      if (a.managerId === mgrId) {
        allocMany[a.id] += cost * ((billingByAssignment[a.id] || 0) / mb);
      }
    }
  }

  // ---- 5. Allocate Partner pool cost: firm-wide -> managers -> assignments ----
  const partnerAllocByManager = {};
  const allocPartner = {};
  assignments.forEach(a => { allocPartner[a.id] = 0; });
  for (const mgrId of managerIds) {
    const mb = managerBilling[mgrId] || 0;
    const share = firmBilling > 0 ? partnerPoolCost * (mb / firmBilling) : 0;
    partnerAllocByManager[mgrId] = share;
    if (mb <= 0) continue;
    for (const a of assignments) {
      if (a.managerId === mgrId) {
        allocPartner[a.id] += share * ((billingByAssignment[a.id] || 0) / mb);
      }
    }
  }

  // ---- 6. Overhead + totals + profit, per assignment ----
  const assignmentResults = assignments.map(a => {
    const billing = billingByAssignment[a.id] || 0;
    const dedicated = directCost[a.id] || 0;
    const many = allocMany[a.id] || 0;
    const partner = allocPartner[a.id] || 0;
    const overhead = overheadRate * billing;
    const totalCost = dedicated + many + partner + overhead;
    const profit = billing - totalCost;
    return {
      ...a,
      billing: round2(billing),
      directCost: round2(dedicated),
      manyAssignmentsCost: round2(many),
      partnerCost: round2(partner),
      overhead: round2(overhead),
      totalCost: round2(totalCost),
      profit: round2(profit),
      margin: billing !== 0 ? profit / billing : null,
      staffCount: staffByAssignment[a.id].length,
      revenueEntryCount: revenueByAssignment[a.id].length,
      bucket: bucketFor(a, profit, billing),
    };
  });

  const byId = {};
  assignmentResults.forEach(a => { byId[a.id] = a; });

  // ---- 7. Manager roll-ups ----
  const managerResults = realManagers.map(m => {
    const own = assignmentResults.filter(a => a.managerId === m.id);
    const billing = own.reduce((s, a) => s + a.billing, 0);
    const directCostSum = own.reduce((s, a) => s + a.directCost, 0);
    const overheadSum = own.reduce((s, a) => s + a.overhead, 0);
    const totalCost = own.reduce((s, a) => s + a.totalCost, 0);
    const profit = own.reduce((s, a) => s + a.profit, 0);
    return {
      id: m.id,
      name: m.name,
      assignmentCount: own.length,
      billing: round2(billing),
      directCost: round2(directCostSum),
      manyAssignmentsCost: round2(manyCostByManager[m.id] || 0),
      partnerCostShare: round2(partnerAllocByManager[m.id] || 0),
      overhead: round2(overheadSum),
      totalCost: round2(totalCost),
      profit: round2(profit),
      margin: billing !== 0 ? profit / billing : null,
      manyStaffCount: (manyStaffByManager[m.id] || []).length,
    };
  });

  // ---- 8. Firm summary ----
  const firmDirectCost = assignmentResults.reduce((s, a) => s + a.directCost, 0);
  const firmManyCost = Object.values(manyCostByManager).reduce((s, v) => s + v, 0);
  const firmOverhead = assignmentResults.reduce((s, a) => s + a.overhead, 0);
  const firmTotalCost = firmDirectCost + firmManyCost + partnerPoolCost + firmOverhead;
  const firmProfit = firmBilling - firmTotalCost;

  const buckets = { profitable: [], nonProfitable: [], inProgress: [] };
  assignmentResults.forEach(a => buckets[a.bucket].push(a));

  return {
    overheadRate,
    assignments: assignmentResults,
    assignmentsById: byId,
    managers: managerResults,
    partner: {
      id: partnerId,
      name: partnerManager ? partnerManager.name : 'Partner',
      poolCost: round2(partnerPoolCost),
      staffCount: partnerStaff.length,
      allocatedByManager: Object.fromEntries(
        Object.entries(partnerAllocByManager).map(([k, v]) => [k, round2(v)])
      ),
    },
    firm: {
      billing: round2(firmBilling),
      directCost: round2(firmDirectCost),
      manyAssignmentsCost: round2(firmManyCost),
      partnerCost: round2(partnerPoolCost),
      overhead: round2(firmOverhead),
      totalCost: round2(firmTotalCost),
      profit: round2(firmProfit),
      margin: firmBilling !== 0 ? firmProfit / firmBilling : null,
      assignmentCount: assignments.length,
    },
    buckets: {
      profitable: buckets.profitable,
      nonProfitable: buckets.nonProfitable,
      inProgress: buckets.inProgress,
    },
  };
}

function bucketFor(assignment, profit, billing) {
  if (assignment.status === 'in-progress') return 'inProgress';
  if (billing === 0) return 'inProgress';
  return profit >= 0 ? 'profitable' : 'nonProfitable';
}

function round2(n) {
  return Math.round((Number(n) || 0) * 100) / 100;
}

module.exports = { computeAllocation, round2 };
