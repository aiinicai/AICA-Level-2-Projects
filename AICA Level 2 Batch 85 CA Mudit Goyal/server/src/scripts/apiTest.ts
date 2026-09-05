/**
 * End-to-end API test.
 *
 * Boots the real Express app against the real database and drives it over HTTP
 * exactly as the browser does — no mocks, no direct Prisma calls to set up
 * state. What it proves is that the whole stack works together: auth, role
 * gates, GST arithmetic, invoice numbering, payment settlement, the punch
 * state machine and the registers.
 *
 * Everything it creates is namespaced with a run-specific tag and deleted at
 * the end, so it is safe to run against the seeded demo database.
 *
 *   npm test
 */
import dotenv from 'dotenv';
import { PrismaClient } from '@prisma/client';
import bcrypt from 'bcryptjs';
import type { Server } from 'http';

dotenv.config();

const prisma = new PrismaClient();

const TAG = `test-${Date.now()}`;
const ADMIN_EMAIL = `admin.${TAG}@test.local`;
const STAFF_EMAIL = `staff.${TAG}@test.local`;
const PASSWORD = 'TestPass@123';

let base = '';
let passed = 0;
const failures: string[] = [];

// ── Tiny assertion harness ───────────────────────────────────────────────────

function check(name: string, condition: boolean, detail?: unknown): void {
  if (condition) {
    passed++;
    console.log(`  ok   ${name}`);
  } else {
    failures.push(name);
    console.log(`  FAIL ${name}${detail === undefined ? '' : ` — ${JSON.stringify(detail)}`}`);
  }
}

function eq(name: string, actual: unknown, expected: unknown): void {
  check(name, JSON.stringify(actual) === JSON.stringify(expected), { actual, expected });
}

function section(title: string): void {
  console.log(`\n${title}`);
}

interface ApiResponse<T = any> {
  status: number;
  body: T;
}

async function call<T = any>(
  method: string,
  path: string,
  options: { token?: string; body?: unknown } = {},
): Promise<ApiResponse<T>> {
  const res = await fetch(`${base}${path}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(options.token ? { Authorization: `Bearer ${options.token}` } : {}),
    },
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  });
  const text = await res.text();
  let body: unknown = text;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    /* a non-JSON body is itself the finding — keep the raw text */
  }
  return { status: res.status, body: body as T };
}

const n = (v: unknown) => Number(v ?? 0);

// ── Fixtures ─────────────────────────────────────────────────────────────────

async function createUser(email: string, name: string, role: 'ADMIN' | 'STAFF') {
  const staff = await prisma.staff.create({
    data: { staffName: name, email, designation: 'Test user' },
  });
  await prisma.user.create({
    data: { email, password: await bcrypt.hash(PASSWORD, 10), role, staffId: staff.id },
  });
  return staff;
}

async function cleanup(adminStaffId?: number, staffStaffId?: number) {
  const ids = [adminStaffId, staffStaffId].filter((v): v is number => typeof v === 'number');
  if (ids.length === 0) return;

  // Order matters: the children go before the rows they point at.
  const invoices = await prisma.invoice.findMany({ where: { createdById: { in: ids } }, select: { id: true } });
  const invoiceIds = invoices.map((i) => i.id);
  if (invoiceIds.length) {
    await prisma.payment.deleteMany({ where: { invoiceId: { in: invoiceIds } } });
    await prisma.invoiceLineItem.deleteMany({ where: { invoiceId: { in: invoiceIds } } });
    await prisma.invoice.deleteMany({ where: { id: { in: invoiceIds } } });
  }
  await prisma.attendancePunch.deleteMany({ where: { staffId: { in: ids } } });
  await prisma.attendance.deleteMany({ where: { staffId: { in: ids } } });
  await prisma.user.deleteMany({ where: { staffId: { in: ids } } });
  await prisma.staff.deleteMany({ where: { id: { in: ids } } });
}

// ── The run ──────────────────────────────────────────────────────────────────

async function run() {
  process.env.NODE_ENV = 'test';
  // Port 0 lets the OS pick a free one, so the suite never collides with a dev
  // server the developer already has running.
  process.env.PORT = '0';

  // Importing index.ts starts the real server; it parks the http.Server on
  // globalThis so this run can find the port it took and close it afterwards.
  await import('../index');
  const listening: Server = await new Promise((resolve) => {
    const poll = () => {
      const srv = (globalThis as { __capstoneServer?: Server }).__capstoneServer;
      if (srv?.listening) return resolve(srv);
      setTimeout(poll, 25);
    };
    poll();
  });
  const address = listening.address();
  const port = typeof address === 'object' && address ? address.port : 5100;
  base = `http://127.0.0.1:${port}/api`;

  let adminStaffId: number | undefined;
  let staffStaffId: number | undefined;

  try {
    // ── Health ───────────────────────────────────────────────────────────────
    section('Health');
    const health = await call('GET', '/health');
    eq('database reachable', health.body.database, 'connected');

    // ── Authentication ───────────────────────────────────────────────────────
    section('Authentication');
    const admin = await createUser(ADMIN_EMAIL, 'Test Admin', 'ADMIN');
    const staff = await createUser(STAFF_EMAIL, 'Test Staff', 'STAFF');
    adminStaffId = admin.id;
    staffStaffId = staff.id;

    const badLogin = await call('POST', '/auth/login', { body: { email: ADMIN_EMAIL, password: 'wrong' } });
    eq('a wrong password is refused', badLogin.status, 401);
    eq('the refusal does not say which half was wrong', badLogin.body.message, 'Invalid credentials');

    const unknownLogin = await call('POST', '/auth/login', { body: { email: 'nobody@test.local', password: PASSWORD } });
    eq('an unknown email gets the same message', unknownLogin.body.message, 'Invalid credentials');

    const adminLogin = await call('POST', '/auth/login', { body: { email: ADMIN_EMAIL, password: PASSWORD } });
    eq('an admin can sign in', adminLogin.status, 200);
    const adminToken: string = adminLogin.body.token;
    check('a token is issued', typeof adminToken === 'string' && adminToken.length > 20);

    const staffLogin = await call('POST', '/auth/login', { body: { email: STAFF_EMAIL, password: PASSWORD } });
    const staffToken: string = staffLogin.body.token;
    eq('a staff member can sign in', staffLogin.status, 200);

    const noToken = await call('GET', '/invoices');
    eq('an unauthenticated request is refused', noToken.status, 401);

    const badToken = await call('GET', '/invoices', { token: 'not-a-real-token' });
    eq('a forged token is refused', badToken.status, 401);

    const profile = await call('GET', '/auth/profile', { token: adminToken });
    eq('the profile is the signed-in user', profile.body.email, ADMIN_EMAIL);

    // ── Role gates ───────────────────────────────────────────────────────────
    section('Role gates');
    const staffAtRegister = await call('GET', '/attendance/register', { token: staffToken });
    eq('staff cannot read the whole-firm register', staffAtRegister.status, 403);

    const adminAtRegister = await call('GET', '/attendance/register', { token: adminToken });
    eq('an admin can', adminAtRegister.status, 200);

    const staffAddsStaff = await call('POST', '/staff', {
      token: staffToken,
      body: { staffName: 'Nope', email: `nope.${TAG}@test.local`, password: PASSWORD },
    });
    eq('staff cannot create staff', staffAddsStaff.status, 403);

    const staffPeeking = await call('GET', `/attendance/monthly?staffId=${admin.id}&year=2026&month=9`, { token: staffToken });
    eq('staff cannot read a colleague’s attendance', staffPeeking.status, 403);

    // ── Invoicing: intra-state GST ───────────────────────────────────────────
    section('Invoicing — GST arithmetic');
    const intra = await call('POST', '/invoices', {
      token: adminToken,
      body: {
        clientName: `Intra Client ${TAG}`,
        clientState: 'Rajasthan',
        clientGstin: '08AABCI1234C1ZK',
        invoiceDate: '2026-06-10',
        dueDate: '2026-07-10',
        taxType: 'CGST_SGST',
        gstRate: 18,
        lineItems: [
          { description: 'Statutory audit', hsnSac: '998221', quantity: 1, rate: 100000 },
          { description: 'Travel', quantity: 2, rate: 2500 },
        ],
      },
    });
    eq('an invoice is created', intra.status, 201);
    const intraInvoice = intra.body;
    eq('the taxable value totals the lines', n(intraInvoice.amount), 105000);
    eq('CGST is half the combined rate', n(intraInvoice.cgstRate), 9);
    eq('SGST is the other half', n(intraInvoice.sgstRate), 9);
    eq('CGST is computed on the taxable value', n(intraInvoice.cgstAmount), 9450);
    eq('SGST matches CGST', n(intraInvoice.sgstAmount), 9450);
    eq('no IGST on an intra-state bill', intraInvoice.igstAmount, null);
    eq('the total is value plus both taxes', n(intraInvoice.totalAmount), 123900);
    eq('a new invoice starts as a draft', intraInvoice.status, 'DRAFT');
    check('the number follows the financial year', /^MGSG\/26-27\/\d{4}$/.test(intraInvoice.invoiceNumber), intraInvoice.invoiceNumber);
    eq('the lines are numbered in order', intraInvoice.lineItems.map((l: any) => l.slNo), [1, 2]);

    // ── Invoicing: inter-state GST ───────────────────────────────────────────
    const inter = await call('POST', '/invoices', {
      token: adminToken,
      body: {
        clientName: `Inter Client ${TAG}`,
        clientState: 'Maharashtra',
        invoiceDate: '2026-06-11',
        taxType: 'IGST',
        gstRate: 18,
        status: 'SENT',
        lineItems: [{ description: 'GST advisory', quantity: 1, rate: 50000 }],
      },
    });
    const interInvoice = inter.body;
    eq('IGST carries the whole rate', n(interInvoice.igstRate), 18);
    eq('IGST is computed on the taxable value', n(interInvoice.igstAmount), 9000);
    eq('no CGST on an inter-state bill', interInvoice.cgstAmount, null);
    eq('the total is value plus IGST', n(interInvoice.totalAmount), 59000);
    eq('an invoice can be issued on creation', interInvoice.status, 'SENT');

    check(
      'invoice numbers do not repeat',
      intraInvoice.invoiceNumber !== interInvoice.invoiceNumber,
      [intraInvoice.invoiceNumber, interInvoice.invoiceNumber],
    );

    // ── Invoicing: no GST ────────────────────────────────────────────────────
    const exempt = await call('POST', '/invoices', {
      token: adminToken,
      body: {
        clientName: `Exempt Client ${TAG}`,
        invoiceDate: '2026-06-12',
        taxType: 'NONE',
        lineItems: [{ description: 'Bookkeeping', quantity: 1, rate: 20000 }],
      },
    });
    eq('an untaxed total equals the taxable value', n(exempt.body.totalAmount), 20000);
    eq('no tax rows are stamped', [exempt.body.cgstAmount, exempt.body.igstAmount], [null, null]);

    // ── Validation ───────────────────────────────────────────────────────────
    section('Invoicing — validation');
    const noName = await call('POST', '/invoices', {
      token: adminToken,
      body: { clientName: '  ', lineItems: [{ description: 'x', quantity: 1, rate: 1 }] },
    });
    eq('a nameless client is refused', noName.status, 400);

    const noLines = await call('POST', '/invoices', {
      token: adminToken,
      body: { clientName: 'X', lineItems: [] },
    });
    eq('an invoice with no lines is refused', noLines.status, 400);

    const zeroValue = await call('POST', '/invoices', {
      token: adminToken,
      body: { clientName: 'X', taxType: 'NONE', lineItems: [{ description: 'Free', quantity: 1, rate: 0 }] },
    });
    eq('a zero-value invoice is refused', zeroValue.status, 400);

    const badRate = await call('POST', '/invoices', {
      token: adminToken,
      body: { clientName: 'X', taxType: 'IGST', gstRate: 250, lineItems: [{ description: 'x', quantity: 1, rate: 100 }] },
    });
    eq('an impossible GST rate is refused', badRate.status, 400);

    const backwardsDates = await call('POST', '/invoices', {
      token: adminToken,
      body: {
        clientName: 'X', invoiceDate: '2026-06-10', dueDate: '2026-06-01',
        taxType: 'NONE', lineItems: [{ description: 'x', quantity: 1, rate: 100 }],
      },
    });
    eq('a due date before the invoice date is refused', backwardsDates.status, 400);

    // ── Lifecycle ────────────────────────────────────────────────────────────
    section('Invoicing — lifecycle');
    const earlyPayment = await call('POST', `/invoices/${intraInvoice.id}/payments`, {
      token: adminToken,
      body: { amount: 1000 },
    });
    eq('a draft cannot take a payment', earlyPayment.status, 409);

    const issued = await call('POST', `/invoices/${intraInvoice.id}/issue`, { token: adminToken });
    eq('a draft can be issued', issued.body.status, 'SENT');

    const reIssue = await call('POST', `/invoices/${intraInvoice.id}/issue`, { token: adminToken });
    eq('an issued invoice cannot be issued again', reIssue.status, 409);

    const overpay = await call('POST', `/invoices/${intraInvoice.id}/payments`, {
      token: adminToken,
      body: { amount: 999999 },
    });
    eq('an overpayment is refused', overpay.status, 400);

    const part = await call('POST', `/invoices/${intraInvoice.id}/payments`, {
      token: adminToken,
      body: { amount: 50000, mode: 'BANK', reference: 'NEFT-1' },
    });
    eq('a part payment is accepted', part.status, 201);
    eq('the invoice becomes part paid', part.body.status, 'PARTIALLY_PAID');
    eq('the receipt total is tracked on the header', n(part.body.paidAmount), 50000);

    const editAfterPayment = await call('PUT', `/invoices/${intraInvoice.id}`, {
      token: adminToken,
      body: { clientName: 'Renamed', lineItems: [{ description: 'x', quantity: 1, rate: 1 }] },
    });
    eq('an invoice with payments cannot be edited', editAfterPayment.status, 409);

    const cancelAfterPayment = await call('POST', `/invoices/${intraInvoice.id}/cancel`, { token: adminToken });
    eq('an invoice with payments cannot be cancelled', cancelAfterPayment.status, 409);

    const settle = await call('POST', `/invoices/${intraInvoice.id}/payments`, {
      token: adminToken,
      body: { amount: 73900, mode: 'UPI' },
    });
    eq('the balance settles the invoice', settle.body.status, 'PAID');
    eq('the full value is recorded as received', n(settle.body.paidAmount), 123900);
    eq('both receipts are kept', settle.body.payments.length, 2);

    const removed = await call('DELETE', `/invoices/payments/${settle.body.payments[1].id}`, { token: adminToken });
    eq('removing a payment reopens the invoice', removed.body.status, 'PARTIALLY_PAID');
    eq('the header re-sums from the remaining receipts', n(removed.body.paidAmount), 50000);

    // ── Editing a draft ──────────────────────────────────────────────────────
    const editedDraft = await call('PUT', `/invoices/${exempt.body.id}`, {
      token: adminToken,
      body: {
        clientName: `Exempt Client ${TAG}`,
        taxType: 'IGST',
        gstRate: 12,
        lineItems: [
          { description: 'Bookkeeping', quantity: 1, rate: 20000 },
          { description: 'Filing fees', quantity: 1, rate: 5000 },
        ],
      },
    });
    eq('a draft can be edited', editedDraft.status, 200);
    eq('the edit re-totals the lines', n(editedDraft.body.amount), 25000);
    eq('the edit re-computes tax at the new rate', n(editedDraft.body.igstAmount), 3000);
    eq('the replaced lines are not duplicated', editedDraft.body.lineItems.length, 2);

    const cancelled = await call('POST', `/invoices/${exempt.body.id}/cancel`, { token: adminToken });
    eq('an unpaid invoice can be cancelled', cancelled.body.status, 'CANCELLED');

    // ── Listing and totals ───────────────────────────────────────────────────
    section('Invoicing — listing');
    const listed = await call('GET', `/invoices?search=${encodeURIComponent(TAG)}`, { token: adminToken });
    eq('search finds this run’s invoices', listed.body.invoices.length, 3);
    eq('cancelled invoices are left out of the totals', n(listed.body.summary.billed), 123900 + 59000);
    eq('collected matches what was received', n(listed.body.summary.collected), 50000);
    eq('outstanding is billed less collected', n(listed.body.summary.outstanding), 132900);

    const filtered = await call('GET', `/invoices?search=${encodeURIComponent(TAG)}&status=CANCELLED`, { token: adminToken });
    eq('the status filter narrows the list', filtered.body.invoices.length, 1);

    const fetched = await call('GET', `/invoices/${interInvoice.id}`, { token: adminToken });
    eq('one invoice can be fetched by id', fetched.body.invoiceNumber, interInvoice.invoiceNumber);

    const missing = await call('GET', '/invoices/99999999', { token: adminToken });
    eq('an unknown invoice is a 404', missing.status, 404);

    const deleted = await call('DELETE', `/invoices/${interInvoice.id}`, { token: adminToken });
    eq('an unpaid invoice can be deleted', deleted.status, 200);
    const afterDelete = await call('GET', `/invoices/${interInvoice.id}`, { token: adminToken });
    eq('a deleted invoice is gone from the register', afterDelete.status, 404);

    // ── Attendance ───────────────────────────────────────────────────────────
    section('Attendance');
    const emptyDay = await call('GET', '/attendance/punches', { token: staffToken });
    eq('a fresh day has no punches', emptyDay.body.punches.length, 0);
    eq('the first tap is a check in', emptyDay.body.nextDirection, 'IN');

    const punchIn = await call('POST', '/attendance/punch', {
      token: staffToken,
      body: { latitude: 26.9124, longitude: 75.7873, locationAccuracy: 12.5 },
    });
    eq('a punch is recorded', punchIn.status, 201);
    eq('the server decides it is a check in', punchIn.body.direction, 'IN');
    eq('the next tap will be a check out', punchIn.body.nextDirection, 'OUT');
    eq('an open shift counts no time yet', punchIn.body.workedMinutes, 0);

    const doubleTap = await call('POST', '/attendance/punch', { token: staffToken });
    eq('a double tap is refused', doubleTap.status, 409);
    eq('the refusal returns the true state', doubleTap.body.punches.length, 1);

    // A completed shift has to sit in the past, or the next punch through the
    // API would land before the recorded check-out. The morning is therefore
    // backdated — check in three hours ago, out ninety minutes ago — which is
    // also what a real half-day looks like by the time someone returns.
    const dayRow = await prisma.attendance.findFirstOrThrow({ where: { staffId: staff.id } });
    const checkinAt = new Date(Date.now() - 180 * 60_000);
    const checkoutAt = new Date(Date.now() - 90 * 60_000);
    await prisma.attendancePunch.updateMany({
      where: { attendanceId: dayRow.id, direction: 'IN' },
      data: { punchedAt: checkinAt },
    });
    await prisma.attendancePunch.create({
      data: { attendanceId: dayRow.id, staffId: staff.id, date: dayRow.date, direction: 'OUT', punchedAt: checkoutAt },
    });
    await prisma.attendance.update({
      where: { id: dayRow.id },
      data: { checkedInAt: checkinAt, checkOutAt: checkoutAt, workedMinutes: 90 },
    });

    const afterOut = await call('GET', '/attendance/punches', { token: staffToken });
    eq('both punches are on the day', afterOut.body.punches.length, 2);
    eq('the completed shift is 90 minutes', afterOut.body.workedMinutes, 90);
    eq('the next tap is a check in again', afterOut.body.nextDirection, 'IN');

    const thirdPunch = await call('POST', '/attendance/punch', { token: staffToken });
    eq('a day can be re-opened after lunch', thirdPunch.body.direction, 'IN');
    eq('an open shift does not inflate the total', thirdPunch.body.workedMinutes, 90);
    eq('all three taps are kept', thirdPunch.body.punches.length, 3);

    const ownMonth = await call('GET', `/attendance/monthly?year=${new Date().getFullYear()}&month=${new Date().getMonth() + 1}`, {
      token: staffToken,
    });
    eq('a staff member can read their own month', ownMonth.status, 200);
    eq('today shows in the month', ownMonth.body.days.length, 1);
    eq('the month totals the minutes worked', ownMonth.body.summary.workedMinutes, 90);

    const adminViewingStaff = await call('GET', `/attendance/monthly?staffId=${staff.id}&year=${new Date().getFullYear()}&month=${new Date().getMonth() + 1}`, {
      token: adminToken,
    });
    eq('an admin can read anyone’s month', adminViewingStaff.status, 200);

    const register = await call('GET', '/attendance/register', { token: adminToken });
    const staffRow = register.body.rows.find((r: any) => r.staffId === staff.id);
    check('the register lists the staff member', !!staffRow);
    eq('their status is present', staffRow?.status, 'PRESENT');
    eq('the register counts their punches', staffRow?.punchCount, 3);
    const adminRow = register.body.rows.find((r: any) => r.staffId === admin.id);
    eq('someone who never punched still appears, as absent', adminRow?.status, 'ABSENT');

    const marked = await call('POST', '/attendance/mark', {
      token: adminToken,
      body: { staffId: admin.id, date: register.body.date, status: 'ON_LEAVE', notes: 'Casual leave' },
    });
    eq('an admin can mark a day by hand', marked.body.status, 'ON_LEAVE');

    const badStatus = await call('POST', '/attendance/mark', {
      token: adminToken,
      body: { staffId: admin.id, date: register.body.date, status: 'HOLIDAY' },
    });
    eq('an unknown status is refused', badStatus.status, 400);

    const future = await call('POST', '/attendance/mark', {
      token: adminToken,
      body: { staffId: admin.id, date: '2099-01-01', status: 'PRESENT' },
    });
    eq('a future date cannot be marked', future.status, 400);

    const markedRegister = await call('GET', `/attendance/register?date=${register.body.date}`, { token: adminToken });
    const markedRow = markedRegister.body.rows.find((r: any) => r.staffId === admin.id);
    eq('the register reflects the correction', markedRow?.status, 'ON_LEAVE');
    check('the punches behind a marked day are untouched', (markedRow?.punchCount ?? 0) === 0);

    // ── Staff administration ─────────────────────────────────────────────────
    section('Staff administration');
    const duplicate = await call('POST', '/staff', {
      token: adminToken,
      body: { staffName: 'Clone', email: STAFF_EMAIL, password: PASSWORD },
    });
    eq('a duplicate email is refused', duplicate.status, 409);

    const shortPassword = await call('POST', '/staff', {
      token: adminToken,
      body: { staffName: 'Shorty', email: `short.${TAG}@test.local`, password: 'abc' },
    });
    eq('a short password is refused', shortPassword.status, 400);

    const renamed = await call('PUT', `/staff/${staff.id}`, {
      token: adminToken,
      body: { staffName: 'Test Staff Renamed', designation: 'Senior' },
    });
    eq('a staff record can be edited', renamed.body.staffName, 'Test Staff Renamed');

    const selfDeactivate = await call('PUT', `/staff/${admin.id}/toggle-active`, { token: adminToken });
    eq('an admin cannot deactivate themselves', selfDeactivate.status, 400);

    const deactivated = await call('PUT', `/staff/${staff.id}/toggle-active`, { token: adminToken });
    eq('a staff member can be deactivated', deactivated.body.isActive, false);

    const deactivatedRequest = await call('GET', '/attendance/punches', { token: staffToken });
    eq('a deactivated token stops working immediately', deactivatedRequest.status, 401);

    const deactivatedLogin = await call('POST', '/auth/login', { body: { email: STAFF_EMAIL, password: PASSWORD } });
    eq('a deactivated account cannot sign in', deactivatedLogin.status, 401);

    await call('PUT', `/staff/${staff.id}/toggle-active`, { token: adminToken });
    const reset = await call('POST', `/staff/${staff.id}/reset-password`, {
      token: adminToken,
      body: { newPassword: 'BrandNew@2026' },
    });
    eq('an admin can reset a password', reset.status, 200);

    const newLogin = await call('POST', '/auth/login', { body: { email: STAFF_EMAIL, password: 'BrandNew@2026' } });
    eq('the new password works', newLogin.status, 200);

    const oldLogin = await call('POST', '/auth/login', { body: { email: STAFF_EMAIL, password: PASSWORD } });
    eq('the old password does not', oldLogin.status, 401);

    // ── Settings ─────────────────────────────────────────────────────────────
    section('Settings');
    const settingsRead = await call('GET', '/settings', { token: staffToken });
    eq('anyone signed in can read the settings', settingsRead.status, 200);
    check('the firm name is present', typeof settingsRead.body.firmName === 'string');
    check('an invoice prefix is present', typeof settingsRead.body.invoicePrefix === 'string');

    // Captured so the run can put them back — this row is shared, not created
    // by the test, so it has to be left exactly as it was found.
    const originalSettings = settingsRead.body;

    const staffWrite = await call('PUT', '/settings', {
      token: staffToken,
      body: { ...originalSettings, firmName: 'Hijacked and Co' },
    });
    eq('staff cannot change the settings', staffWrite.status, 403);

    const afterRefusedWrite = await call('GET', '/settings', { token: adminToken });
    eq('the refused write changed nothing', afterRefusedWrite.body.firmName, originalSettings.firmName);

    const noFirmName = await call('PUT', '/settings', { token: adminToken, body: { ...originalSettings, firmName: '  ' } });
    eq('a blank firm name is refused', noFirmName.status, 400);

    const noPrefix = await call('PUT', '/settings', { token: adminToken, body: { ...originalSettings, invoicePrefix: '' } });
    eq('a blank invoice prefix is refused', noPrefix.status, 400);

    const slashPrefix = await call('PUT', '/settings', {
      token: adminToken,
      body: { ...originalSettings, invoicePrefix: 'AB/CD' },
    });
    eq('a prefix containing a slash is refused', slashPrefix.status, 400);

    const longPrefix = await call('PUT', '/settings', {
      token: adminToken,
      body: { ...originalSettings, invoicePrefix: 'THIRTEENCHARS' },
    });
    eq('an over-long prefix is refused', longPrefix.status, 400);

    const badTax = await call('PUT', '/settings', {
      token: adminToken,
      body: { ...originalSettings, defaultTaxType: 'VAT' },
    });
    eq('an unknown default tax type is refused', badTax.status, 400);

    const badDefaultRate = await call('PUT', '/settings', {
      token: adminToken,
      body: { ...originalSettings, defaultGstRate: 150 },
    });
    eq('an impossible default GST rate is refused', badDefaultRate.status, 400);

    const badTerms = await call('PUT', '/settings', {
      token: adminToken,
      body: { ...originalSettings, defaultPaymentTermDays: 400 },
    });
    eq('a payment term of over a year is refused', badTerms.status, 400);

    const fractionalTerms = await call('PUT', '/settings', {
      token: adminToken,
      body: { ...originalSettings, defaultPaymentTermDays: 15.5 },
    });
    eq('a fractional payment term is refused', fractionalTerms.status, 400);

    const saved = await call('PUT', '/settings', {
      token: adminToken,
      body: {
        firmName: `Test Firm ${TAG}`,
        firmAddress: '1 Test Road, Jaipur',
        firmGstin: '08aaacc1234c1zv',
        firmEmail: 'BILLING@Test.Local',
        firmPhone: '+91 141 000 0000',
        invoicePrefix: 'TSTPFX',
        defaultTaxType: 'IGST',
        defaultGstRate: 12,
        defaultPaymentTermDays: 45,
      },
    });
    eq('an admin can save the settings', saved.status, 200);
    eq('the firm name is stored', saved.body.firmName, `Test Firm ${TAG}`);
    eq('a GSTIN is upper-cased', saved.body.firmGstin, '08AAACC1234C1ZV');
    eq('an email is lower-cased', saved.body.firmEmail, 'billing@test.local');
    eq('the default tax type is stored', saved.body.defaultTaxType, 'IGST');
    eq('the payment term is stored', saved.body.defaultPaymentTermDays, 45);

    // The point of the prefix setting: it has to reach the numbers actually
    // issued, not merely sit in a row.
    const prefixed = await call('POST', '/invoices', {
      token: adminToken,
      body: {
        clientName: `Prefix Check ${TAG}`,
        invoiceDate: '2026-06-20',
        taxType: 'NONE',
        lineItems: [{ description: 'Advisory', quantity: 1, rate: 1000 }],
      },
    });
    check(
      'a new invoice takes the configured prefix',
      /^TSTPFX\/26-27\/\d{4}$/.test(prefixed.body.invoiceNumber),
      prefixed.body.invoiceNumber,
    );

    const restored = await call('PUT', '/settings', {
      token: adminToken,
      body: { ...originalSettings, defaultGstRate: Number(originalSettings.defaultGstRate) },
    });
    eq('the settings can be put back', restored.body.invoicePrefix, originalSettings.invoicePrefix);

    const afterRestore = await call('POST', '/invoices', {
      token: adminToken,
      body: {
        clientName: `Prefix Restore ${TAG}`,
        invoiceDate: '2026-06-21',
        taxType: 'NONE',
        lineItems: [{ description: 'Advisory', quantity: 1, rate: 1000 }],
      },
    });
    check(
      'the next invoice uses the restored prefix',
      afterRestore.body.invoiceNumber.startsWith(`${originalSettings.invoicePrefix}/`),
      afterRestore.body.invoiceNumber,
    );

    const reFetched = await call('GET', `/invoices/${prefixed.body.id}`, { token: adminToken });
    eq(
      'a number already issued keeps the prefix it was printed with',
      reFetched.body.invoiceNumber,
      prefixed.body.invoiceNumber,
    );

    // ── Changing your own password ───────────────────────────────────────────
    section('Changing your own password');
    const wrongCurrent = await call('POST', '/auth/change-password', {
      token: adminToken,
      body: { currentPassword: 'not-the-password', newPassword: 'Another@2026' },
    });
    eq('a wrong current password is refused', wrongCurrent.status, 401);

    const tooShort = await call('POST', '/auth/change-password', {
      token: adminToken,
      body: { currentPassword: PASSWORD, newPassword: 'short' },
    });
    eq('a short new password is refused', tooShort.status, 400);

    const anonymousChange = await call('POST', '/auth/change-password', {
      body: { currentPassword: PASSWORD, newPassword: 'Another@2026' },
    });
    eq('changing a password needs a session', anonymousChange.status, 401);

    const changed = await call('POST', '/auth/change-password', {
      token: adminToken,
      body: { currentPassword: PASSWORD, newPassword: 'Changed@2026' },
    });
    eq('a user can change their own password', changed.status, 200);

    const withNew = await call('POST', '/auth/login', { body: { email: ADMIN_EMAIL, password: 'Changed@2026' } });
    eq('the new password signs them in', withNew.status, 200);

    const withOld = await call('POST', '/auth/login', { body: { email: ADMIN_EMAIL, password: PASSWORD } });
    eq('the old password no longer does', withOld.status, 401);

    // Later calls in this run still use adminToken: changing a password does
    // not invalidate a token already issued.
    const stillValid = await call('GET', '/auth/profile', { token: adminToken });
    eq('the existing session survives the change', stillValid.status, 200);

    // ── Dashboard ────────────────────────────────────────────────────────────
    section('Dashboard');
    const dash = await call('GET', '/dashboard', { token: adminToken });
    eq('the dashboard loads', dash.status, 200);
    check('it reports active staff', typeof dash.body.attendance.activeStaff === 'number');
    check('it reports what is outstanding', typeof dash.body.invoicing.outstanding === 'number');
    check('it lists recent invoices', Array.isArray(dash.body.recentInvoices));
  } finally {
    await cleanup(adminStaffId, staffStaffId);
    listening.close();
    await prisma.$disconnect();
  }

  console.log(`\n${'─'.repeat(60)}`);
  if (failures.length === 0) {
    console.log(`All ${passed} checks passed.`);
    process.exit(0);
  } else {
    console.log(`${passed} passed, ${failures.length} FAILED:`);
    for (const f of failures) console.log(`  · ${f}`);
    process.exit(1);
  }
}

run().catch(async (err) => {
  console.error('\nThe test run itself failed:', err);
  await prisma.$disconnect();
  process.exit(1);
});
