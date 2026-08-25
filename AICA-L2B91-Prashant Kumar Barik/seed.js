const bcrypt = require('bcryptjs');

function daysAgo(n) {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString().slice(0, 10);
}
function hash(pw) { return bcrypt.hashSync(pw, 8); }

const DEMO_PASSWORD = 'password123';

// Real team for Swala Solutions Ltd. Two Employees, and the full 5-step
// Accounts approval chain (Accountant -> Sr Accountant -> Asst FC -> FC ->
// GM) each held by one named person. There is currently no Manager account,
// so Employee imprest requests skip the manager-approval step and disburse
// immediately (see the "no manager assigned" auto-approve rule in
// server.js) — there is simply no one in that role to review them yet. If a
// Manager (or a dual-hat "alsoManager" Accounts user) is added later via
// User Management, employee requests will automatically start requiring
// that person's approval again.
module.exports = function seed() {
  const pw = hash(DEMO_PASSWORD);

  // `email` is intentionally blank — fill it in per person via User Management
  // > Edit. The Accountant's email specifically needs to be set for the
  // "GM final approval" email alert to actually deliver (see server.js).
  const users = [
    { id: 'U1', username: 'sujeet.kumar', passwordHash: pw, role: 'Employee', name: 'Sujeet Kumar', title: '', email: '', employeeId: 'E1' },
    { id: 'U2', username: 'rahul.khanna', passwordHash: pw, role: 'Employee', name: 'Rahul Khanna', title: '', email: '', employeeId: 'E2' },
    { id: 'U3', username: 'hans.robin', passwordHash: pw, role: 'Accounts', step: 0, name: 'Hans Robin', title: 'Accountant', email: '' },
    { id: 'U4', username: 'livin', passwordHash: pw, role: 'Accounts', step: 1, name: 'Livin', title: 'Sr Accountant', email: '' },
    { id: 'U5', username: 'prashant.barik', passwordHash: pw, role: 'Accounts', step: 2, name: 'Prashant Barik', title: 'Assistant Finance Controller', email: '' },
    { id: 'U6', username: 'dipen.patel', passwordHash: pw, role: 'Accounts', step: 3, name: 'Dipen Patel', title: 'Financial Controller', email: '' },
    { id: 'U7', username: 'vineet.verma', passwordHash: pw, role: 'Accounts', step: 4, name: 'Vineet Verma', title: 'General Manager', email: '' },
  ];

  const employees = {
    E1: { id: 'E1', name: 'Sujeet Kumar', dept: '', managerId: null },
    E2: { id: 'E2', name: 'Rahul Khanna', dept: '', managerId: null },
  };

  // Clean slate — no sample requests, settlements, or notifications tied to
  // the old demo accounts. Reports and dashboards will show empty states
  // until real imprest activity starts.
  const requests = [];
  const settlements = [];
  const notifications = [];

  return {
    users, employees, requests, settlements, notifications,
    counters: { nextReqNo: 1000, nextSetNo: 2000, nextLineId: 1, nextNotifId: 1, nextVoucherNo: 1 },
  };
};

module.exports.DEMO_PASSWORD = DEMO_PASSWORD;
