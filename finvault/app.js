'use strict';
/* FinVault – local-first. Records live in this device's IndexedDB. Nothing is uploaded except
   IFSC lookups to ifsc.razorpay.com (when you press the Find button). */

const $ = (s, r = document) => r.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const inr = n => (n === '' || n == null || isNaN(n)) ? '—' : '₹' + Number(n).toLocaleString('en-IN');
const today = () => { const d = new Date(); d.setHours(0, 0, 0, 0); return d; };
const iso = d => new Date(d.getTime() - d.getTimezoneOffset() * 6e4).toISOString().slice(0, 10);
const fmtD = s => s ? new Date(s + 'T00:00:00').toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }) : '—';

const FREQ = ['Monthly', 'Quarterly', 'Half-yearly', 'Yearly', 'Single'];
const STEP = { Monthly: 1, Quarterly: 3, 'Half-yearly': 6, Yearly: 12, Single: 0 };

const CATS = {
  life: {
    label: 'Life insurance', icon: '🛡️', title: r => r.policyName, sub: r => [r.insurer, r.policyNo].filter(Boolean).join(' · '),
    cols: ['insurer', 'policyNo', 'premium', 'frequency', 'nextDue', 'maturityDate', 'taxable'],
    fields: [
      { k: 'policyName', l: 'Policy name', req: 1 }, { k: 'insurer', l: 'Insurer' }, { k: 'policyNo', l: 'Policy number' },
      { k: 'type', l: 'Type', t: 'select', o: ['Endowment', 'Term', 'ULIP', 'Money back', 'Whole life', 'Pension / annuity', 'Other'] },
      { k: 'holder', l: 'Policy holder / life assured' }, { k: 'nominee', l: 'Nominee' },
      { k: 'sumAssured', l: 'Sum assured (₹)', t: 'number' }, { k: 'premium', l: 'Premium (₹)', t: 'number' },
      { k: 'frequency', l: 'Premium frequency', t: 'select', o: FREQ },
      { k: 'nextDue', l: 'Next premium due', t: 'date' },
      { k: 'maturityDate', l: 'Maturity date', t: 'date' }, { k: 'maturityAmount', l: 'Expected maturity amount (₹)', t: 'number' },
      { k: 'premiumAccount', l: 'Account debited for premium' }, { k: 'maturityAccount', l: 'Account to receive maturity' },
      { k: 'taxable', l: 'Maturity taxable?', t: 'select', o: ['Check with CA', 'Exempt u/s 10(10D)', 'Taxable'] },
      { k: 'notes', l: 'Notes', t: 'textarea', full: 1 }]
  },
  general: {
    label: 'General insurance', icon: '🚗', title: r => r.policyName, sub: r => [r.insurer, r.policyNo].filter(Boolean).join(' · '),
    cols: ['insurer', 'type', 'insured', 'premium', 'renewalDate', 'sumInsured'],
    fields: [
      { k: 'policyName', l: 'Policy name', req: 1 }, { k: 'insurer', l: 'Insurer' }, { k: 'policyNo', l: 'Policy number' },
      { k: 'type', l: 'Type', t: 'select', o: ['Health', 'Motor – car', 'Motor – two-wheeler', 'Home / fire', 'Travel', 'Personal accident', 'Critical illness', 'Business', 'Other'] },
      { k: 'insured', l: 'Insured person / vehicle no. / property' }, { k: 'nominee', l: 'Nominee' },
      { k: 'sumInsured', l: 'Sum insured (₹)', t: 'number' }, { k: 'premium', l: 'Premium (₹)', t: 'number' },
      { k: 'startDate', l: 'Policy start date', t: 'date' }, { k: 'renewalDate', l: 'Renewal / expiry date', t: 'date' },
      { k: 'premiumAccount', l: 'Account / card used for premium' }, { k: 'agent', l: 'Agent / TPA contact' },
      { k: 'notes', l: 'Notes (claim helpline, add-ons, etc.)', t: 'textarea', full: 1 }]
  },
  card: {
    label: 'Credit cards', icon: '💳', title: r => r.cardName, sub: r => [r.bank, r.last4 ? '•••• ' + r.last4 : ''].filter(Boolean).join(' · '),
    cols: ['bank', 'last4', 'limit', 'amountDue', 'dueDate', 'annualFee', 'expiry'],
    fields: [
      { k: 'cardName', l: 'Card name', req: 1 }, { k: 'bank', l: 'Issuing bank' }, { k: 'last4', l: 'Last 4 digits only' },
      { k: 'network', l: 'Network', t: 'select', o: ['Visa', 'Mastercard', 'RuPay', 'Amex', 'Diners'] }, { k: 'holder', l: 'Card holder' },
      { k: 'limit', l: 'Credit limit (₹)', t: 'number' }, { k: 'billingDay', l: 'Statement date (day of month)' },
      { k: 'dueDate', l: 'Next payment due date', t: 'date' }, { k: 'amountDue', l: 'Amount due (₹)', t: 'number' },
      { k: 'annualFee', l: 'Annual fee (₹)', t: 'number' }, { k: 'feeDate', l: 'Annual fee date', t: 'date' },
      { k: 'expiry', l: 'Expiry (MM/YY)' }, { k: 'autopay', l: 'Auto-pay account' },
      { k: 'notes', l: 'Notes (rewards, helpline)', t: 'textarea', full: 1 }],
    warn: 'Never store the full card number, CVV or PIN here – only the last 4 digits.'
  },
  loan: {
    label: 'Loans', icon: '🏦', title: r => r.loanName, sub: r => [r.lender, r.accountNo].filter(Boolean).join(' · '),
    cols: ['lender', 'emi', 'nextDue', 'outstanding', 'endDate', 'debitAccount'],
    fields: [
      { k: 'loanName', l: 'Loan name', req: 1 }, { k: 'lender', l: 'Lender' }, { k: 'accountNo', l: 'Loan account no.' },
      { k: 'loanType', l: 'Type', t: 'select', o: ['Home', 'Car', 'Personal', 'Education', 'Gold', 'Business', 'Credit card', 'Other'] },
      { k: 'principal', l: 'Principal (₹)', t: 'number' }, { k: 'rate', l: 'Interest rate (%)', t: 'number' },
      { k: 'emi', l: 'EMI (₹)', t: 'number' }, { k: 'nextDue', l: 'Next EMI date', t: 'date' },
      { k: 'endDate', l: 'Loan end date', t: 'date' }, { k: 'outstanding', l: 'Outstanding (₹)', t: 'number' },
      { k: 'debitAccount', l: 'Account debited for EMI' }, { k: 'coBorrower', l: 'Co-borrower / guarantor' },
      { k: 'notes', l: 'Notes', t: 'textarea', full: 1 }]
  },
  bank: {
    label: 'Bank accounts', icon: '🏛️', title: r => r.bank, sub: r => [r.accountNo, r.branch].filter(Boolean).join(' · '),
    cols: ['accountNo', 'accType', 'mode', 'branch', 'ifsc', 'nominee'],
    fields: [
      { k: 'bank', l: 'Bank name', req: 1 }, { k: 'accountNo', l: 'Account number' },
      { k: 'accType', l: 'Account type', t: 'select', o: ['Savings', 'Current', 'Salary', 'NRE', 'NRO', 'Demat-linked', 'Other'] },
      { k: 'mode', l: 'Single / Joint', t: 'select', o: ['Single', 'Joint'] },
      { k: 'holders', l: 'Account holder(s)' }, { k: 'operation', l: 'Mode of operation (e.g. Either or Survivor)' },
      { k: 'ifsc', l: 'IFSC code', ifsc: 1 }, { k: 'branch', l: 'Branch' },
      { k: 'nominee', l: 'Nominee(s) & share' }, { k: 'customerId', l: 'Customer ID / CRN' },
      { k: 'notes', l: 'Notes', t: 'textarea', full: 1 }]
  },
  fd: {
    label: 'Fixed deposits', icon: '📈', title: r => (r.bank || '') + (r.fdNo ? ' – ' + r.fdNo : ''), sub: r => r.holders || '',
    cols: ['bank', 'principal', 'rate', 'maturityDate', 'maturityAmount', 'maturityAccount', 'nominee'],
    fields: [
      { k: 'bank', l: 'Bank', req: 1 }, { k: 'fdNo', l: 'FD / Receipt number' }, { k: 'holders', l: 'Holder(s)' },
      { k: 'principal', l: 'Principal (₹)', t: 'number' }, { k: 'rate', l: 'Interest rate (%)', t: 'number' },
      { k: 'startDate', l: 'Start date', t: 'date' }, { k: 'maturityDate', l: 'Maturity date', t: 'date' },
      { k: 'maturityAmount', l: 'Maturity amount (₹)', t: 'number' },
      { k: 'payout', l: 'Interest payout', t: 'select', o: ['Cumulative', 'Monthly', 'Quarterly', 'Half-yearly', 'Yearly'] },
      { k: 'autoRenew', l: 'On maturity', t: 'select', o: ['Auto-renew', 'Credit to account'] },
      { k: 'maturityAccount', l: 'Linked account for proceeds' }, { k: 'nominee', l: 'Nominee' },
      { k: 'notes', l: 'Notes', t: 'textarea', full: 1 }]
  },
  locker: {
    label: 'Lockers', icon: '🔐', title: r => (r.bank || '') + ' locker ' + (r.lockerNo || ''), sub: r => r.branch || '',
    cols: ['bank', 'branch', 'lockerNo', 'rent', 'rentDue', 'nominee'],
    fields: [
      { k: 'bank', l: 'Bank', req: 1 }, { k: 'branch', l: 'Branch' }, { k: 'lockerNo', l: 'Locker number' },
      { k: 'size', l: 'Size', t: 'select', o: ['Small', 'Medium', 'Large', 'Extra large'] },
      { k: 'holders', l: 'Locker holder(s)' }, { k: 'nominee', l: 'Nominee' },
      { k: 'rent', l: 'Annual rent incl. GST (₹)', t: 'number' }, { k: 'rentDue', l: 'Rent due date', t: 'date' },
      { k: 'debitAccount', l: 'Account debited for rent' }, { k: 'agreementDate', l: 'Agreement date', t: 'date' },
      { k: 'notes', l: 'Notes (key location, etc.)', t: 'textarea', full: 1 }]
  },
  vehicle: {
    label: 'Vehicles', icon: '🚙', title: r => (r.vehicleName || '') + (r.regNo ? ' – ' + r.regNo : ''), sub: r => [r.owner, r.rcNo ? 'RC ' + r.rcNo : ''].filter(Boolean).join(' · '),
    cols: ['regNo', 'owner', 'rcNo', 'rcValidity', 'insuranceExpiry', 'pucExpiry', 'hypothecation'],
    fields: [
      { k: 'vehicleName', l: 'Vehicle (e.g. Honda City ZX)', req: 1 }, { k: 'regNo', l: 'Registration number' },
      { k: 'vtype', l: 'Type', t: 'select', o: ['Car', 'Two-wheeler', 'Commercial', 'Tractor / farm', 'Other'] }, { k: 'owner', l: 'Registered owner' },
      { k: 'make', l: 'Make' }, { k: 'model', l: 'Model / variant' }, { k: 'mfgYear', l: 'Manufacturing year' },
      { k: 'fuel', l: 'Fuel', t: 'select', o: ['Petrol', 'Diesel', 'CNG', 'Electric', 'Hybrid'] }, { k: 'colour', l: 'Colour' },
      { k: 'chassisNo', l: 'Chassis number' }, { k: 'engineNo', l: 'Engine number' },
      { k: 'rcNo', l: 'RC book / smart card number' }, { k: 'regDate', l: 'Registration date', t: 'date' }, { k: 'rcValidity', l: 'RC valid until', t: 'date' },
      { k: 'rto', l: 'Registering authority (RTO)' }, { k: 'hypothecation', l: 'Hypothecation (bank / loan)' },
      { k: 'insurer', l: 'Insurer' }, { k: 'insurancePolicyNo', l: 'Insurance policy no.' },
      { k: 'insuranceExpiry', l: 'Insurance expiry / renewal', t: 'date' }, { k: 'insurancePremium', l: 'Insurance premium (₹)', t: 'number' },
      { k: 'pucExpiry', l: 'PUC valid until', t: 'date' }, { k: 'fitnessExpiry', l: 'Fitness certificate valid until', t: 'date' },
      { k: 'roadTaxDue', l: 'Road tax due', t: 'date' }, { k: 'nextService', l: 'Next service due', t: 'date' },
      { k: 'purchaseDate', l: 'Purchase date', t: 'date' }, { k: 'purchasePrice', l: 'Purchase price (₹)', t: 'number' },
      { k: 'notes', l: 'Notes', t: 'textarea', full: 1 }]
  }
};
const lab = (c, k) => (CATS[c].fields.find(f => f.k === k) || {}).l || k;

/* ---------- storage ---------- */
let db;
const idb = () => new Promise((res, rej) => {
  const rq = indexedDB.open('finvault', 2);
  rq.onupgradeneeded = () => { const d = rq.result; for (const s of ['records', 'profile', 'docs']) if (!d.objectStoreNames.contains(s)) d.createObjectStore(s, { keyPath: 'id' }); };
  rq.onsuccess = () => res(rq.result); rq.onerror = () => rej(rq.error);
});
const tx = (mode, fn) => new Promise((res, rej) => { const t = db.transaction('records', mode); const r = fn(t.objectStore('records')); t.oncomplete = () => res(r.result); t.onerror = () => rej(t.error); });
const all = async () => { let a; await tx('readonly', s => (a = s.getAll(), a)); return a.result; };
const put = r => tx('readwrite', s => s.put(r));
const del = id => tx('readwrite', s => s.delete(id));
let DATA = [];
/* older versions had a single "insurance" category – sort those records into life / general */
const reload = async () => {
  DATA = (await all()).filter(r => r.cat === 'insurance' || CATS[r.cat]);   // records of removed tabs (e.g. Properties) stay in storage but are hidden
  for (const r of DATA.filter(x => x.cat === 'insurance')) {
    const t = r.type || '';
    r.cat = /^life/i.test(t) || /endow|term|ulip|money|whole|pension/i.test(t) ? 'life' : /health|motor|home|travel|accident|fire/i.test(t) ? 'general' : (r.renewalDate && !r.maturityDate ? 'general' : 'life');
    if (r.cat === 'life') r.type = t.replace(/^Life\s*[–-]\s*/i, '');
    await put(r);
  }
};

const cfg = {
  get: () => { try { return JSON.parse(localStorage.getItem('fv_cfg')) || {}; } catch { return {}; } },
  set: o => localStorage.setItem('fv_cfg', JSON.stringify({ ...cfg.get(), ...o }))
};

/* ---------- events & reminders ---------- */
const addMonths = (d, n) => { const x = new Date(d); const day = x.getDate(); x.setDate(1); x.setMonth(x.getMonth() + n); x.setDate(Math.min(day, new Date(x.getFullYear(), x.getMonth() + 1, 0).getDate())); return x; };
const dt = s => new Date(s + 'T00:00:00');

function eventsBetween(from, to) {
  const ev = [];
  const rec = (r, c, dateKey, step, amt, label, kind = 'out') => {
    if (!r[dateKey]) return;
    let d = dt(r[dateKey]); if (isNaN(d)) return;
    if (!step) { if (d >= from && d <= to) ev.push({ d, r, c, label, amt, kind }); return; }
    let i = 0;
    while (d < from && i < 1200) { i++; d = addMonths(dt(r[dateKey]), step * i); }
    while (d <= to && i < 1200) { ev.push({ d, r, c, label, amt, kind }); i++; d = addMonths(dt(r[dateKey]), step * i); }
  };
  for (const r of DATA) {
    if (r.cat === 'life') {
      rec(r, 'life', 'nextDue', STEP[r.frequency || 'Yearly'] ?? 12, r.premium, 'Premium: ' + r.policyName);
      rec(r, 'life', 'maturityDate', 0, r.maturityAmount, 'Maturity: ' + r.policyName, 'in');
    } else if (r.cat === 'general') rec(r, 'general', 'renewalDate', 12, r.premium, 'Renewal: ' + r.policyName);
    else if (r.cat === 'card') {
      rec(r, 'card', 'dueDate', 1, r.amountDue, 'Card bill: ' + r.cardName);
      rec(r, 'card', 'feeDate', 12, r.annualFee, 'Card annual fee: ' + r.cardName);
    } else if (r.cat === 'loan') {
      const end = r.endDate ? dt(r.endDate) : null;
      const lim = end && end < to ? end : to;
      rec(r, 'loan', 'nextDue', 1, r.emi, 'EMI: ' + r.loanName + (r.lender ? ' (' + r.lender + ')' : ''));
      if (end) for (let i = ev.length - 1; i >= 0; i--) if (ev[i].r === r && ev[i].d > lim && ev[i].label.startsWith('EMI')) ev.splice(i, 1);
    } else if (r.cat === 'fd') rec(r, 'fd', 'maturityDate', 0, r.maturityAmount, 'FD matures: ' + CATS.fd.title(r), 'in');
    else if (r.cat === 'locker') rec(r, 'locker', 'rentDue', 12, r.rent, 'Locker rent: ' + CATS.locker.title(r));
    else if (r.cat === 'vehicle') {
      const n = CATS.vehicle.title(r);
      rec(r, 'vehicle', 'insuranceExpiry', 12, r.insurancePremium, 'Vehicle insurance: ' + n);
      rec(r, 'vehicle', 'roadTaxDue', 0, null, 'Road tax due: ' + n, 'due');
      rec(r, 'vehicle', 'pucExpiry', 0, null, 'PUC expires: ' + n, 'due');
      rec(r, 'vehicle', 'fitnessExpiry', 0, null, 'Fitness certificate expires: ' + n, 'due');
      rec(r, 'vehicle', 'rcValidity', 0, null, 'RC validity ends: ' + n, 'due');
      rec(r, 'vehicle', 'nextService', 0, null, 'Service due: ' + n, 'due');
    }
  }
  return ev.sort((a, b) => a.d - b.d);
}
const daysTo = d => Math.round((d - today()) / 864e5);
const dueClass = n => n < 0 ? 'red' : n <= 7 ? 'red' : n <= 30 ? 'amber' : 'green';
const dueText = n => n < 0 ? Math.abs(n) + 'd overdue' : n === 0 ? 'Today' : n === 1 ? 'Tomorrow' : 'in ' + n + 'd';

function nextMonthRange() { const t = today(); const a = new Date(t.getFullYear(), t.getMonth() + 1, 1); const b = new Date(t.getFullYear(), t.getMonth() + 2, 0); return [a, b]; }
function thisMonthRange() { const t = today(); return [t, new Date(t.getFullYear(), t.getMonth() + 1, 0)]; }
const sum = a => a.reduce((s, e) => s + (+e.amt || 0), 0);

/* ---------- IFSC ---------- */
async function ifscLookup(code) {
  code = code.trim().toUpperCase();
  if (!/^[A-Z]{4}0[A-Z0-9]{6}$/.test(code)) throw new Error('IFSC must look like HDFC0001234');
  const r = await fetch('https://ifsc.razorpay.com/' + code);
  if (!r.ok) throw new Error('IFSC not found');
  return r.json();
}

/* ---------- UI ---------- */
let state = { view: 'dashboard', q: '' };
function toast(m, ms = 3500) { const t = $('#toast'); t.textContent = m; t.hidden = false; clearTimeout(toast.t); toast.t = setTimeout(() => t.hidden = true, ms); }

function renderNav() {
  const items = [['profile', '👤', 'My profile'], ['dashboard', '🏠', 'Dashboard'], ['reminders', '🔔', 'Reminders'], ['calendar', '🗓️', 'Next month'], ...Object.entries(CATS).map(([k, c]) => [k, c.icon, c.label]), ['docs', '📂', 'Documents'], ['data', '📁', 'Import / Export'], ['settings', '⚙️', 'Settings']];
  $('#nav').innerHTML = items.map(([k, i, l]) => `<button data-v="${k}" class="${state.view === k ? 'on' : ''}"><span>${i} ${l}</span>${CATS[k] ? `<span class="cnt">${DATA.filter(r => r.cat === k).length}</span>` : k === 'reminders' && soonCount() ? `<span class="cnt">${soonCount()}</span>` : ''}</button>`).join('');
}
function go(v) { state.view = v; $('#side').classList.remove('open'); render(); }
function render() {
  renderNav();
  const v = state.view;
  $('#title').textContent = v === 'dashboard' ? 'Dashboard' : v === 'calendar' ? 'Next month' : CATS[v]?.label || ({ data: 'Import / Export', profile: 'My profile', reminders: 'Reminders', docs: 'Documents' }[v] || 'Settings');
  $('#btnAdd').hidden = !CATS[v] && v !== 'dashboard';
  const q = state.q.toLowerCase();
  if (q && !CATS[v] && v !== 'docs') return $('#view').innerHTML = searchView(q);
  const fn = { dashboard, calendar, data: dataView, settings, profile: profileView, reminders: remindersView, docs: docsView }[v];
  fn ? fn() : catView(v);
}
function evRows(ev, limit = 50) {
  return ev.length ? ev.slice(0, limit).map(e => { const n = daysTo(e.d); return `<div class="row"><div><b>${esc(e.label)}</b><small>${fmtD(iso(e.d))}</small></div><div style="text-align:right"><span class="${e.kind}">${e.kind === 'in' ? '+' : ''}${inr(e.amt)}</span><br><span class="pill ${dueClass(n)}">${dueText(n)}</span></div></div>`; }).join('') : '<div class="empty">Nothing here</div>';
}
function dashboard() {
  const [a, b] = thisMonthRange(), [c, d] = nextMonthRange();
  const rem = cfg.get().lead || 30;
  const soon = eventsBetween(today(), new Date(today().getTime() + rem * 864e5));
  const over = DATA.flatMap(r => ['nextDue', 'renewalDate', 'rentDue'].filter(k => r[k] && dt(r[k]) < today() && !(r.cat === 'insurance' && r.frequency && k === 'nextDue')).map(k => ({ r, k })));
  const nm = eventsBetween(c, d);
  $('#view').innerHTML = `
  <div class="grid">
    <div class="card"><h3>Records</h3><div class="big">${DATA.length}</div><span class="note">${Object.entries(CATS).map(([k, x]) => x.label + ' ' + DATA.filter(r => r.cat === k).length).join(' · ')}</span></div>
    <div class="card"><h3>Payable this month</h3><div class="big out">${inr(sum(eventsBetween(a, b).filter(e => e.kind === 'out')))}</div></div>
    <div class="card"><h3>Payable next month</h3><div class="big out">${inr(sum(nm.filter(e => e.kind === 'out')))}</div></div>
    <div class="card"><h3>Maturities next month</h3><div class="big in">${inr(sum(nm.filter(e => e.kind === 'in')))}</div></div>
  </div>
  <div class="sec card"><h2>Coming up in the next ${rem} days</h2>${evRows(soon)}</div>
  ${!DATA.length ? `<div class="sec card"><h2>Get started</h2><p>Use <b>+ Add</b> to type a record, or go to <b>Import / Export</b> to download the Excel template and bulk-load your data.</p></div>` : ''}`;
}
function calendar() {
  const [a, b] = nextMonthRange();
  const ev = eventsBetween(a, b);
  const out = ev.filter(e => e.kind === 'out'), inn = ev.filter(e => e.kind === 'in');
  $('#view').innerHTML = `<div class="actions"><button class="btn" id="ics">📅 Export reminders (.ics)</button></div>
  <div class="grid"><div class="card"><h3>Expected payments</h3><div class="big out">${inr(sum(out))}</div><span class="note">${out.length} payments · ${a.toLocaleDateString('en-IN', { month: 'long', year: 'numeric' })}</span></div>
  <div class="card"><h3>Expected receipts</h3><div class="big in">${inr(sum(inn))}</div><span class="note">${inn.length} maturities</span></div></div>
  <div class="sec card"><h2>Schedule</h2>${evRows(ev, 200)}</div>`;
  $('#ics').onclick = exportICS;
}
function searchView(q) {
  const hits = DATA.filter(r => JSON.stringify(r).toLowerCase().includes(q));
  return `<div class="sec card"><h2>${hits.length} result(s) for “${esc(q)}”</h2>${hits.map(r => `<div class="row"><div><b>${esc(CATS[r.cat].title(r))}</b><small>${CATS[r.cat].label} · ${esc(CATS[r.cat].sub(r))}</small></div><button class="btn sm" data-edit="${r.id}">Open</button></div>`).join('') || '<div class="empty">No match</div>'}</div>`;
}
function catView(cat) {
  const c = CATS[cat], q = state.q.toLowerCase();
  const rows = DATA.filter(r => r.cat === cat && (!q || JSON.stringify(r).toLowerCase().includes(q)));
  const cell = (r, k) => { const f = c.fields.find(x => x.k === k); const v = r[k]; return f?.t === 'date' ? fmtD(v) : f?.t === 'number' ? inr(v) : esc(v || '—'); };
  $('#view').innerHTML = rows.length ? `<div class="tablewrap"><table><thead><tr><th>Name</th>${c.cols.map(k => `<th>${esc(lab(cat, k))}</th>`).join('')}<th>Docs</th><th></th></tr></thead><tbody>${rows.map(r => `<tr><td><b>${esc(c.title(r))}</b></td>${c.cols.map(k => `<td>${cell(r, k)}</td>`).join('')}<td>${docsFor(r.id).length ? '📎 ' + docsFor(r.id).length : '—'}</td><td><button class="btn sm" data-edit="${r.id}">Edit</button></td></tr>`).join('')}</tbody></table></div>` : `<div class="card empty">No ${c.label.toLowerCase()} yet. Press <b>+ Add</b>.</div>`;
}

/* ---------- form ---------- */
function openForm(cat, rec0 = {}) {
  const c = CATS[cat], r = { ...rec0 }, rid = rec0.id || crypto.randomUUID();
  $('#sheet').innerHTML = `<h2>${rec0.id ? 'Edit' : 'Add'} – ${c.label}</h2>
  <form id="f" class="form">${c.fields.map(f => `<label class="${f.t === 'textarea' || f.full ? 'full' : ''}">${esc(f.l)}${f.req ? ' *' : ''}
    ${f.t === 'select' ? `<select name="${f.k}"><option value=""></option>${f.o.map(o => `<option ${r[f.k] === o ? 'selected' : ''}>${esc(o)}</option>`).join('')}</select>`
      : f.t === 'textarea' ? `<textarea name="${f.k}" rows="2">${esc(r[f.k] || '')}</textarea>`
        : `<input name="${f.k}" type="${f.t || 'text'}" ${f.t === 'number' ? 'step="any"' : ''} value="${esc(r[f.k] ?? '')}" ${f.req ? 'required' : ''}>`}
    ${f.ifsc ? '<button class="btn sm" type="button" id="ifscBtn">🔍 Find bank & branch from IFSC</button>' : ''}</label>`).join('')}
    ${cat === 'life' ? '<div class="full hint" id="taxhint"></div>' : ''}${c.warn ? `<div class="full hint">⚠ ${esc(c.warn)}</div>` : ''}
    <div class="full actions" style="margin:0"><button class="btn primary" type="submit">Save</button><button class="btn" type="button" id="cancel">Cancel</button>${rec0.id ? '<button class="btn danger" type="button" id="del">Delete</button>' : ''}</div></form>
  <div class="sec"><h3 style="margin:0 0 8px;font-size:13px;color:var(--mute);letter-spacing:.04em">📎 DOCUMENTS FOR THIS ITEM</h3><div id="recdocs"></div></div>`;
  mountDocPanel($('#recdocs'), rid, cat);
  $('#modal').hidden = false;
  const f = $('#f'), setV = (k, v) => { const el = f.elements[k]; if (el && v != null && v !== '') el.value = v; };
  const dropDocs = async () => { for (const d of docsFor(rid)) await stx('docs', 'readwrite', s => s.delete(d.id)); DOCS = DOCS.filter(d => (d.ref || 'profile') !== rid); };
  $('#cancel').onclick = async () => {
    if (!rec0.id && docsFor(rid).length) { if (!confirm('Discard the ' + docsFor(rid).length + ' document(s) you attached to this unsaved item?')) return; await dropDocs(); }
    $('#modal').hidden = true;
  };
  if ($('#del')) $('#del').onclick = async () => {
    const n = docsFor(rid).length;
    if (confirm('Delete this record' + (n ? ' and its ' + n + ' attached document(s)' : '') + ' permanently?')) { await del(rec0.id); await dropDocs(); await reload(); $('#modal').hidden = true; render(); }
  };
  if ($('#ifscBtn')) $('#ifscBtn').onclick = async () => { try { const j = await ifscLookup(f.elements.ifsc.value); f.elements.ifsc.value = j.IFSC; setV('bank', j.BANK); setV('branch', j.BRANCH + (j.CITY ? ', ' + j.CITY : '')); toast('Found: ' + j.BANK + ', ' + j.BRANCH); } catch (e) { toast(e.message); } };
  const taxHint = () => {
    const h = $('#taxhint'); if (!h) return;
    const sa = +f.elements.sumAssured.value, p = +f.elements.premium.value, fr = f.elements.frequency.value;
    const annual = p * (fr === 'Monthly' ? 12 : fr === 'Quarterly' ? 4 : fr === 'Half-yearly' ? 2 : 1);
    h.classList.toggle('warn', !!(sa && annual && annual > sa * 0.10));
    h.textContent = sa && annual && annual > sa * 0.10 ? '⚠ Annual premium exceeds 10% of sum assured – for policies issued after 1-Apr-2012 the maturity proceeds are generally taxable (10(10D)). Also, aggregate premium above ₹5 lakh/yr (non-ULIP, from 1-Apr-2023) is taxable. Confirm with your CA.' : sa && annual ? 'ℹ Premium is within 10% of sum assured – maturity likely exempt u/s 10(10D), subject to the ₹5 lakh aggregate-premium cap. Confirm with your CA.' : '';
  };
  f.addEventListener('input', taxHint); taxHint();
  f.onsubmit = async e => {
    e.preventDefault(); const o = { ...rec0, cat, id: rid, updated: Date.now() };
    c.fields.forEach(fl => { const v = f.elements[fl.k].value; o[fl.k] = fl.t === 'number' && v !== '' ? +v : v; });
    await put(o); await reload(); $('#modal').hidden = true; toast('Saved'); render();
  };
}

/* ---------- import / export ---------- */
function dataView() {
  $('#view').innerHTML = `<div class="grid">
  <div class="card"><h3>Excel</h3><p class="note">Download the template (one sheet per category), fill it, then import. Existing records are kept; imports are added.</p>
    <div class="actions"><button class="btn" id="tpl">⬇ Template</button><button class="btn" id="xexp">⬇ Export all</button><label class="btn primary">⬆ Import .xlsx<input type="file" id="ximp" accept=".xlsx,.xls,.csv" hidden></label></div></div>
  <div class="card"><h3>Backup</h3><p class="note">Because data lives only on this device, keep a backup file. Restore it on a new phone/laptop.</p>
    <div class="actions"><button class="btn" id="bk">⬇ Backup (.json)</button><label class="btn">⬆ Restore<input type="file" id="rs" accept=".json" hidden></label></div></div>
  <div class="card"><h3>Reminders</h3><p class="note">Export every due date as a calendar file to get alerts on your phone/laptop calendar.</p><div class="actions"><button class="btn" id="ics">📅 Export .ics</button></div></div></div>`;
  $('#tpl').onclick = () => xlsxOut(true); $('#xexp').onclick = () => xlsxOut(false); $('#ics').onclick = exportICS;
  $('#ximp').onchange = e => xlsxIn(e.target.files[0]);
  $('#bk').onclick = async () => {
    const prof = { ...PROFILE }; if (prof.photo) prof.photo = await b2d(prof.photo);
    const docs = []; for (const d of DOCS) docs.push({ ...d, blob: await b2d(d.blob) });
    download(new Blob([JSON.stringify({ v: 2, records: DATA, profile: prof, docs })], { type: 'application/json' }), 'finvault-backup-' + iso(today()) + '.json');
  };
  $('#rs').onchange = async e => {
    const j = JSON.parse(await e.target.files[0].text()), recs = Array.isArray(j) ? j : j.records || [];
    for (const r of recs) await put(r);
    if (j.profile) { const p = { ...j.profile, id: 'me' }; if (typeof p.photo === 'string') p.photo = await d2b(p.photo); await stx('profile', 'readwrite', s => s.put(p)); }
    for (const d of j.docs || []) { const o = { ...d, blob: await d2b(d.blob) }; await stx('docs', 'readwrite', s => s.put(o)); }
    await reload(); await loadExtra(); toast('Restored ' + recs.length + ' records'); render();
  };
}
const download = (blob, name) => { const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 5e3); };
function xlsxOut(template) {
  const wb = XLSX.utils.book_new();
  for (const [k, c] of Object.entries(CATS)) {
    const rows = template ? [] : DATA.filter(r => r.cat === k).map(r => Object.fromEntries(c.fields.map(f => [f.l, r[f.k] ?? ''])));
    const ws = rows.length ? XLSX.utils.json_to_sheet(rows) : XLSX.utils.aoa_to_sheet([c.fields.map(f => f.l)]);
    ws['!cols'] = c.fields.map(() => ({ wch: 22 })); XLSX.utils.book_append_sheet(wb, ws, c.label.slice(0, 31));
  }
  XLSX.writeFile(wb, template ? 'FinVault-template.xlsx' : 'FinVault-export-' + iso(today()) + '.xlsx');
}
async function xlsxIn(file) {
  if (!file) return;
  const wb = XLSX.read(await file.arrayBuffer(), { cellDates: true }); let n = 0;
  const legacy = { insurance: { label: 'Insurance', fields: [...CATS.life.fields, ...CATS.general.fields.filter(f => !CATS.life.fields.some(g => g.k === f.k))] } };
  for (const [k, c] of [...Object.entries(CATS), ...Object.entries(legacy)]) {
    const ws = wb.Sheets[c.label.slice(0, 31)] || (wb.SheetNames.length === 1 && Object.keys(CATS).indexOf(k) === 0 ? wb.Sheets[wb.SheetNames[0]] : null); if (!ws) continue;
    for (const row of XLSX.utils.sheet_to_json(ws, { defval: '' })) {
      const o = { id: crypto.randomUUID(), cat: k, updated: Date.now() }; let any = false;
      for (const f of c.fields) {
        let v = row[f.l] ?? row[f.k] ?? ''; if (v === '') continue;
        if (v instanceof Date) v = iso(v); else if (f.t === 'date') { const d = new Date(v); v = isNaN(d) ? String(v) : iso(d); }
        else if (f.t === 'number') v = +String(v).replace(/[₹,\s]/g, '') || 0;
        o[f.k] = v; any = true;
      }
      if (any) { await put(o); n++; }
    }
  }
  await reload(); toast('Imported ' + n + ' records'); render();
}
function exportICS() {
  const t = today(), ev = eventsBetween(t, addMonths(t, 12));
  const p = n => String(n).padStart(2, '0'), ds = d => d.getFullYear() + p(d.getMonth() + 1) + p(d.getDate());
  const L = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//FinVault//EN'];
  ev.forEach((e, i) => L.push('BEGIN:VEVENT', 'UID:fv' + i + '-' + e.r.id + '@finvault', 'DTSTAMP:' + ds(t) + 'T000000Z', 'DTSTART;VALUE=DATE:' + ds(e.d), 'SUMMARY:' + e.label.replace(/[,;]/g, ' ') + (e.amt ? ' – Rs ' + e.amt : ''), 'BEGIN:VALARM', 'TRIGGER:-P3D', 'ACTION:DISPLAY', 'DESCRIPTION:Due in 3 days', 'END:VALARM', 'END:VEVENT'));
  L.push('END:VCALENDAR'); download(new Blob([L.join('\r\n')], { type: 'text/calendar' }), 'finvault-reminders.ics'); toast(ev.length + ' reminders exported');
}

/* ---------- profile & documents (all optional, stored on this device) ---------- */
const stx = (s, mode, fn) => new Promise((res, rej) => { const t = db.transaction(s, mode); const r = fn(t.objectStore(s)); t.oncomplete = () => res(r && r.result); t.onerror = () => rej(t.error); });
let PROFILE = { id: 'me' }, DOCS = [], camActive = false;
const loadExtra = async () => { PROFILE = (await stx('profile', 'readonly', s => s.get('me'))) || { id: 'me' }; DOCS = (await stx('docs', 'readonly', s => s.getAll())) || []; };
const b2d = b => new Promise(r => { const f = new FileReader(); f.onload = () => r(f.result); f.readAsDataURL(b); });
const d2b = async u => (await fetch(u)).blob();
const PF = [['name', 'Full name'], ['dob', 'Date of birth', 'date'], ['mobile', 'Mobile'], ['email', 'Email', 'email'], ['pan', 'PAN'], ['aadhaar', 'Aadhaar number', 'secret'],
['address', 'Address', 'textarea'], ['city', 'City'], ['state', 'State'], ['pincode', 'PIN code'], ['notes', 'Notes', 'textarea']];
const DOCTYPES = ['Aadhaar card', 'PAN card', 'Passport', 'Driving licence', 'Voter ID', 'Insurance policy', 'Bank passbook / statement', 'FD receipt', 'Loan agreement', 'Locker agreement', 'Other'];

async function shrink(file, max = 1280) {
  if (!file.type.startsWith('image/')) return file;
  try {
    const bmp = await createImageBitmap(file), k = Math.min(1, max / Math.max(bmp.width, bmp.height));
    const c = document.createElement('canvas'); c.width = Math.round(bmp.width * k); c.height = Math.round(bmp.height * k);
    c.getContext('2d').drawImage(bmp, 0, 0, c.width, c.height);
    return await new Promise(r => c.toBlob(r, 'image/jpeg', .82));
  } catch { return file; }
}
function camera(facing) {
  return new Promise(async res => {
    let st; try { st = await navigator.mediaDevices.getUserMedia({ video: { facingMode: facing } }); } catch { toast('Camera not available or permission denied.'); return res(null); }
    camActive = true;
    const ov = document.createElement('div'); ov.className = 'modal'; ov.style.zIndex = 40;
    ov.innerHTML = '<div class="sheet"><h2>Camera</h2><video id="cv" autoplay playsinline muted style="width:100%;border-radius:10px;background:#000"></video><div class="actions" style="margin-top:12px"><button class="btn primary" id="snap">📸 Capture</button><button class="btn" id="ccx">Cancel</button></div></div>';
    document.body.appendChild(ov); const cv = ov.querySelector('#cv'); cv.srcObject = st;
    const done = b => { st.getTracks().forEach(t => t.stop()); camActive = false; ov.remove(); res(b); };
    ov.querySelector('#ccx').onclick = () => done(null);
    ov.querySelector('#snap').onclick = () => { const c = document.createElement('canvas'); c.width = cv.videoWidth; c.height = cv.videoHeight; c.getContext('2d').drawImage(cv, 0, 0); c.toBlob(done, 'image/jpeg', .9); };
  });
}
function readProfileForm() { const f = $('#pf'); if (!f) return; PF.forEach(([k]) => { PROFILE[k] = f.elements[k].value.trim(); }); }
const saveProfile = () => stx('profile', 'readwrite', s => s.put({ ...PROFILE, id: 'me' }));

/* ---- shared document panel: ref = record id, or 'profile' ---- */
const DOCTYPES_BY = {
  life: ['Policy document', 'Premium receipt', 'Maturity / claim', 'Nomination', 'Other'],
  general: ['Policy document', 'Renewal receipt', 'Claim', 'Other'],
  card: ['Card statement', 'Welcome kit', 'Other'],
  loan: ['Sanction letter', 'Loan agreement', 'EMI schedule', 'Statement', 'NOC / closure', 'Other'],
  bank: ['Passbook / statement', 'Cheque book', 'Nomination', 'KYC', 'Other'],
  fd: ['FD receipt', 'Interest certificate', 'Nomination', 'Other'],
  locker: ['Locker agreement', 'Rent receipt', 'Nomination', 'Other'],
  vehicle: ['RC book / smart card', 'Insurance policy', 'PUC certificate', 'Fitness certificate', 'Driving licence', 'Purchase invoice', 'Service record', 'Road tax receipt', 'Other']
};
const docsFor = ref => DOCS.filter(d => (d.ref || 'profile') === ref).sort((a, b) => b.added - a.added);
const docRow = d => `<div class="row"><div style="display:flex;gap:10px;align-items:center">${d.blob.type.startsWith('image/') ? `<img class="thumb" src="${URL.createObjectURL(d.blob)}" alt="">` : '<div class="thumb">📄</div>'}<div><b>${esc(d.name)}</b><small>${esc(d.type)} · ${(d.blob.size / 1024).toFixed(0)} KB · ${new Date(d.added).toLocaleDateString('en-IN')}</small></div></div>
  <div class="actions" style="margin:0"><button type="button" class="btn sm" data-dview="${d.id}">View</button><button type="button" class="btn sm" data-ddl="${d.id}">⬇</button><button type="button" class="btn sm danger" data-ddel="${d.id}">✕</button></div></div>`;
function mountDocPanel(el, ref, cat, onChange) {
  const types = DOCTYPES_BY[cat] || DOCTYPES;
  el.classList.add('docpanel');
  const draw = () => {
    el.innerHTML = `<div class="actions"><select class="btn dp-t">${types.map(t => `<option>${esc(t)}</option>`).join('')}</select><input class="btn dp-n" placeholder="Name / note (optional)" style="min-width:190px"><label class="btn">⬆ Upload (image / PDF)<input class="dp-u" type="file" accept="image/*,application/pdf" multiple hidden></label><button class="btn dp-c" type="button">📸 Scan with camera</button></div>${docsFor(ref).map(docRow).join('') || '<div class="empty">No documents yet.</div>'}`;
    const q = s => el.querySelector(s);
    const MAXMB = 30;
    const add = async (blob, name) => {
      if (!blob.type.startsWith('image/') && blob.size > MAXMB * 1e6) { toast(name + ' is ' + (blob.size / 1e6).toFixed(1) + ' MB – too large (limit ' + MAXMB + ' MB). Compress the PDF and try again.', 7000); return false; }
      try {
        const d = { id: crypto.randomUUID(), ref, cat, type: q('.dp-t').value, name: q('.dp-n').value.trim() || name, blob: await shrink(blob), added: Date.now() };
        await stx('docs', 'readwrite', s => s.put(d)); DOCS.push(d); return true;
      } catch (er) { toast('Could not save ' + name + ': ' + (er && (er.message || er.name) || 'storage error') + '. Your device storage may be full.', 7000); return false; }
    };
    q('.dp-u').onchange = async e => { let ok = 0; for (const f of [...e.target.files]) if (await add(f, f.name)) ok++; if (ok) toast(ok + ' document(s) added'); el._draw(); };
    q('.dp-c').onclick = async () => { const b = await camera('environment'); if (b) { if (await add(b, 'scan-' + iso(today()) + '.jpg')) toast('Scan added'); el._draw(); } };
  };
  el._draw = () => { draw(); if (onChange) onChange(); };
  draw();
}

/* ---- Documents folder tab ---- */
let dsel = { c: 'profile', r: 'profile' };
function docsView() {
  const folders = [['profile', '👤', 'Profile'], ...Object.entries(CATS).map(([k, c]) => [k, c.icon, c.label])];
  const title = d => { const ref = d.ref || 'profile'; if (ref === 'profile') return PROFILE.name || 'My profile'; const r = DATA.find(x => x.id === ref); return r ? CATS[r.cat].title(r) : null; };
  const ql = state.q.toLowerCase();
  const docs = DOCS.filter(d => !ql || [d.name, d.type, title(d) || ''].join(' ').toLowerCase().includes(ql));
  const folderOf = d => { const ref = d.ref || 'profile'; if (ref === 'profile') return 'profile'; const r = DATA.find(x => x.id === ref); return r ? r.cat : 'unlinked'; };
  const sub = list => { const g = {}; list.forEach(d => { const k = d.ref || 'profile'; (g[k] = g[k] || []).push(d); }); return Object.values(g).map(a => `<div class="sub">📁 ${esc(title(a[0]) || 'Unlinked (item was removed or not saved)')}</div>${a.map(docRow).join('')}`).join(''); };
  const tree = [...folders, ['unlinked', '❔', 'Unlinked']].map(([k, ic, l]) => {
    const inF = docs.filter(d => folderOf(d) === k); if (!inF.length) return '';
    return `<details class="card folder" open><summary>📂 ${ic} ${esc(l)} <span class="pill">${inF.length}</span></summary>${sub(inF)}</details>`;
  }).join('');
  $('#view').innerHTML = `<div class="card"><h2 style="margin-top:0">Add / scan a document</h2>
    <div class="actions"><select id="dfc" class="btn">${folders.map(([k, ic, l]) => `<option value="${k}" ${dsel.c === k ? 'selected' : ''}>${ic} ${esc(l)}</option>`).join('')}</select><select id="dfr" class="btn"></select></div><div id="dfp"></div></div>
    <div class="sec">${tree || '<div class="card empty">No documents yet. Choose a folder and item above, then upload or scan.</div>'}</div>
    <p class="note">Stored only in this browser on this device. Include them in your Backup (Import / Export) so you can restore on a new device.</p>`;
  const fillR = () => {
    dsel.c = $('#dfc').value;
    const opts = dsel.c === 'profile' ? [['profile', PROFILE.name || 'My profile']] : DATA.filter(r => r.cat === dsel.c).map(r => [r.id, CATS[dsel.c].title(r)]);
    $('#dfr').innerHTML = opts.map(([v, t]) => `<option value="${esc(v)}" ${dsel.r === v ? 'selected' : ''}>${esc(t)}</option>`).join(''); $('#dfr').hidden = !opts.length;
    mountP();
  };
  const mountP = () => {
    dsel.r = $('#dfr').value; $('#dfp').innerHTML = '';
    if (!dsel.r) return $('#dfp').innerHTML = '<div class="empty">Add a record in this folder first, then attach documents to it.</div>';
    const m = document.createElement('div'); $('#dfp').appendChild(m); mountDocPanel(m, dsel.r, dsel.c, docsView);
  };
  $('#dfc').onchange = () => { dsel.r = null; fillR(); }; $('#dfr').onchange = mountP; fillR();
}

function profileView() {
  const p = PROFILE, url = b => URL.createObjectURL(b);
  const fld = ([k, l, t]) => `<label class="${t === 'textarea' ? 'full' : ''}">${esc(l)}${t === 'textarea' ? `<textarea name="${k}" rows="2">${esc(p[k] || '')}</textarea>` :
    t === 'secret' ? `<span style="display:flex;gap:6px"><input style="flex:1" name="${k}" type="password" inputmode="numeric" autocomplete="off" value="${esc(p[k] || '')}"><button type="button" class="btn sm" id="showA">Show</button></span>` :
      `<input name="${k}" type="${t || 'text'}" value="${esc(p[k] || '')}" ${k === 'pan' ? 'style="text-transform:uppercase"' : ''}>`}</label>`;
  $('#view').innerHTML = `<div class="card"><div class="phead"><div class="avatar">${p.photo ? `<img src="${url(p.photo)}" alt="">` : '👤'}</div>
    <div><b>${esc(p.name || 'Your profile')}</b><div class="note">Everything here is optional and stays on this device.</div>
    <div class="actions" style="margin:8px 0 0"><label class="btn sm">⬆ Upload photo<input id="ph" type="file" accept="image/*" hidden></label><button class="btn sm" id="phc">📸 Take photo</button>${p.photo ? '<button class="btn sm danger" id="phx">Remove</button>' : ''}</div></div></div>
    <form id="pf" class="form" style="margin-top:14px">${PF.map(fld).join('')}<div class="full hint" id="pfh"></div><div class="full actions" style="margin:0"><button class="btn primary" type="submit">Save profile</button></div></form></div>
  <div class="sec card"><h2>Documents</h2><div id="docp"></div>
    <p class="note">Documents are kept only in this browser's storage. Include them in your Backup, and don't use this on a shared computer.</p></div>`;
  const f = $('#pf'); mountDocPanel($('#docp'), 'profile', 'profile');
  const chk = () => { const pan = f.elements.pan.value.toUpperCase(), a = f.elements.aadhaar.value.replace(/\s/g, ''); $('#pfh').textContent = (pan && !/^[A-Z]{5}[0-9]{4}[A-Z]$/.test(pan) ? 'PAN format looks unusual (expected ABCDE1234F). ' : '') + (a && !/^\d{12}$/.test(a) ? 'Aadhaar should be 12 digits.' : ''); };
  f.addEventListener('input', chk); chk();
  $('#showA').onclick = e => { const i = f.elements.aadhaar; i.type = i.type === 'password' ? 'text' : 'password'; e.target.textContent = i.type === 'password' ? 'Show' : 'Hide'; };
  f.onsubmit = async e => { e.preventDefault(); readProfileForm(); PROFILE.pan = (PROFILE.pan || '').toUpperCase(); await saveProfile(); toast('Profile saved'); profileView(); };
  const setPhoto = async b => { if (!b) return; readProfileForm(); PROFILE.photo = await shrink(b, 600); await saveProfile(); profileView(); };
  $('#ph').onchange = e => setPhoto(e.target.files[0]);
  $('#phc').onclick = async () => setPhoto(await camera('user'));
  if ($('#phx')) $('#phx').onclick = async () => { readProfileForm(); delete PROFILE.photo; await saveProfile(); profileView(); };
}
/* In-app viewer: works on https, localhost and when index.html is opened straight from disk (file://),
   where opening a blob: link in a new tab fails with "File not found". */
function viewDoc(d) {
  const isImg = d.blob.type.startsWith('image/'), isPdf = d.blob.type === 'application/pdf' || /\.pdf$/i.test(d.name);
  const blob = isPdf && d.blob.type !== 'application/pdf' ? new Blob([d.blob], { type: 'application/pdf' }) : d.blob;
  const url = URL.createObjectURL(blob);
  const ov = document.createElement('div'); ov.className = 'modal'; ov.style.zIndex = 45;
  ov.innerHTML = `<div class="sheet" style="max-width:980px"><div class="actions" style="justify-content:space-between;align-items:center"><b style="overflow-wrap:anywhere">${esc(d.name)}</b><span style="display:flex;gap:6px"><button class="btn sm" id="vdl">⬇ Download</button><button class="btn sm primary" id="vx">✕ Close</button></span></div>
    ${isImg ? `<img src="${url}" alt="" style="max-width:100%;border-radius:8px;display:block;margin:auto">` : isPdf ? `<iframe src="${url}" title="${esc(d.name)}" style="width:100%;height:78vh;border:1px solid var(--line);border-radius:8px;background:#fff"></iframe><p class="note">If the PDF does not show here, use Download and open it on your device.</p>` : '<div class="empty">This file type cannot be previewed. Use Download.</div>'}</div>`;
  const close = () => { ov.remove(); URL.revokeObjectURL(url); document.removeEventListener('keydown', esc2); };
  const esc2 = ev => { if (ev.key === 'Escape') close(); };
  ov.querySelector('#vx').onclick = close; ov.querySelector('#vdl').onclick = () => download(d.blob, d.name);
  ov.addEventListener('click', ev => { if (ev.target === ov) close(); }); document.addEventListener('keydown', esc2);
  document.body.appendChild(ov);
}
document.addEventListener('click', async e => {
  const g = a => { const id = e.target.closest('[' + a + ']')?.getAttribute(a); return DOCS.find(d => d.id === id); };
  const v = g('data-dview'); if (v) return viewDoc(v);
  const dl = g('data-ddl'); if (dl) return download(dl.blob, /\.[a-z0-9]{2,5}$/i.test(dl.name) ? dl.name : dl.name + (dl.blob.type === 'application/pdf' ? '.pdf' : dl.blob.type === 'image/jpeg' ? '.jpg' : ''));
  const x = g('data-ddel');
  if (x && confirm('Delete this document?')) { await stx('docs', 'readwrite', s => s.delete(x.id)); DOCS = DOCS.filter(d => d !== x); const pan = e.target.closest('.docpanel'); if (pan && pan._draw) pan._draw(); else render(); }
});

/* ---------- settings ---------- */
function settings() {
  const s = cfg.get();
  $('#view').innerHTML = `<div class="card set">
   <label>Remind me this many days ahead<input id="ld" type="number" min="1" max="120" value="${s.lead || 30}"></label>
   <div class="actions"><button class="btn primary" id="sv">Save</button><button class="btn" id="nt">🔔 Enable notifications</button></div>
   <p class="note">All your data stays in this browser on this device. Use Import / Export → Backup to keep a copy.</p></div>`;
  $('#sv').onclick = () => { cfg.set({ lead: +$('#ld').value || 30 }); toast('Saved'); };
  $('#nt').onclick = async () => toast((await Notification.requestPermission()) === 'granted' ? 'Notifications on' : 'Notifications blocked');
}

/* ---------- reminders: tab, spoken summary, notifications ---------- */
function reminderGroups() {
  const t = today(), lead = +cfg.get().lead || 30;
  const evs = eventsBetween(new Date(t.getTime() - 7 * 864e5), new Date(t.getTime() + lead * 864e5)).map(e => ({ ...e, n: daysTo(e.d) }));
  return { late: evs.filter(e => e.n < 0), today: evs.filter(e => e.n === 0), week: evs.filter(e => e.n > 0 && e.n <= 7), later: evs.filter(e => e.n > 7), lead };
}
const soonCount = () => { const g = reminderGroups(); return g.late.length + g.today.length + g.week.length; };
function remindersView() {
  const g = reminderGroups(), perm = 'Notification' in window ? Notification.permission : 'unsupported';
  const sec = (t, a, c) => a.length ? `<div class="sec card"><h2>${t} <span class="pill ${c}">${a.length}</span></h2>${evRows(a, 100)}</div>` : '';
  const none = !g.late.length && !g.today.length && !g.week.length && !g.later.length;
  $('#view').innerHTML = `<div class="actions">
    ${perm === 'default' ? '<button class="btn" id="rnote">🔔 Turn on notifications</button>' : perm === 'granted' ? '<button class="btn" id="rtest">🔔 Test notification</button>' : ''}
    <button class="btn" id="rics">📅 Calendar alerts (.ics)</button></div>
    ${perm === 'denied' ? '<div class="card note">Notifications are blocked for this site. Allow them in your browser\'s site settings to get alerts.</div>' : perm === 'unsupported' ? '<div class="card note">This browser does not support notifications.</div>' : ''}
    ${sec('Recently passed – please check', g.late, 'red')}${sec('Due today', g.today, 'red')}${sec('Next 7 days', g.week, 'amber')}${sec('Later (next ' + g.lead + ' days)', g.later, 'green')}
    ${none ? `<div class="card empty">No reminders in the next ${g.lead} days. 🎉</div>` : ''}
    <p class="note">Notifications arrive when FinVault is open or running in the background (e.g. installed on your phone or laptop) – at app start, then every 30 minutes, once per payment as it gets near (7, 3, 1 days and on the day). A web app cannot wake itself when fully closed, so for guaranteed alerts also import the .ics file into your phone's calendar.</p>`;
  $('#rics').onclick = exportICS;
  if ($('#rnote')) $('#rnote').onclick = async () => { await Notification.requestPermission(); remindersView(); notifyDue(); };
  if ($('#rtest')) $('#rtest').onclick = () => showNote('FinVault test', 'Notifications are working.', 'fv-test');
}
async function showNote(title, body, tag) {
  try { const reg = await navigator.serviceWorker?.getRegistration(); if (reg) return await reg.showNotification(title, { body, icon: 'icon.svg', badge: 'icon.svg', tag }); } catch { }
  try { new Notification(title, { body, icon: 'icon.svg', tag }); } catch { }
}
function notifyDue() {
  if (!('Notification' in window) || Notification.permission !== 'granted' || !DATA.length) return;
  let seen; try { seen = JSON.parse(localStorage.fv_seen || '{}'); } catch { seen = {}; }
  const g = reminderGroups(), fresh = [];
  for (const e of [...g.late, ...g.today, ...g.week]) {
    const b = e.n < 0 ? 'late' : e.n === 0 ? 0 : e.n <= 1 ? 1 : e.n <= 3 ? 3 : 7;
    const k = e.r.id + '|' + e.label + '|' + iso(e.d) + '|' + b;
    if (!seen[k]) { seen[k] = Date.now(); fresh.push(e); }
  }
  const keys = Object.keys(seen); if (keys.length > 800) keys.sort((a, b) => seen[a] - seen[b]).slice(0, 300).forEach(k => delete seen[k]);
  localStorage.fv_seen = JSON.stringify(seen);
  if (!fresh.length) return;
  fresh.sort((a, b) => a.n - b.n);
  const line = e => e.label + (e.amt ? ' – ' + inr(e.amt) : '') + ' (' + dueText(e.n) + ')';
  showNote(fresh.length === 1 ? 'FinVault reminder' : 'FinVault – ' + fresh.length + ' reminders', fresh.slice(0, 5).map(line).join('\n') + (fresh.length > 5 ? '\n+' + (fresh.length - 5) + ' more' : ''), 'fv-due');
}

/* ---------- boot ---------- */
document.addEventListener('click', e => {
  const n = e.target.closest('[data-v]'); if (n) return go(n.dataset.v);
  const ed = e.target.closest('[data-edit]'); if (ed) { const r = DATA.find(x => x.id === ed.dataset.edit); openForm(r.cat, r); }
  if (e.target === $('#modal') && !camActive) $('#modal').hidden = true;
});
$('#menu').onclick = () => $('#side').classList.toggle('open');
$('#search').oninput = e => { state.q = e.target.value; render(); };
$('#btnAdd').onclick = () => {
  if (CATS[state.view]) return openForm(state.view);
  $('#sheet').innerHTML = '<h2>Add what?</h2><div class="actions">' + Object.entries(CATS).map(([k, c]) => `<button class="btn" data-pick="${k}">${c.icon} ${c.label}</button>`).join('') + '</div>';
  $('#modal').hidden = false; $('#sheet').onclick = e => { const p = e.target.closest('[data-pick]'); if (p) openForm(p.dataset.pick); };
};
let deferred; window.addEventListener('beforeinstallprompt', e => { e.preventDefault(); deferred = e; $('#btnInstall').hidden = false; });
$('#btnInstall').onclick = () => deferred?.prompt();
(async () => {
  db = await idb(); await reload(); await loadExtra();
  if (location.hash === '#reminders') state.view = 'reminders';
  render(); notifyDue();
  setInterval(notifyDue, 30 * 60e3); document.addEventListener('visibilitychange', () => { if (!document.hidden) notifyDue(); });
  if ('serviceWorker' in navigator && location.protocol.startsWith('http')) navigator.serviceWorker.register('sw.js');
  if (navigator.storage?.persist) navigator.storage.persist();
})();
