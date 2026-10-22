/**
 * Bill Bol — Google Sheet database (Apps Script)
 * ------------------------------------------------
 * Makes one Google Sheet the database for Bill Bol and stores every bill copy and
 * claim PDF in a Google Drive folder, with links written into the sheet.
 *
 * SET-UP (once, about 10 minutes):
 *  1. Create a new Google Sheet (for example "Bill Bol Database").
 *  2. Extensions → Apps Script. Delete the sample code, paste this whole file, Save.
 *  3. Back in the sheet, reload the page. A "Bill Bol" menu appears.
 *     Bill Bol → 1. Set up sheets. Approve the permissions (Sheets + Drive).
 *     A box shows your ACCESS KEY — note it.
 *  4. In Apps Script: Deploy → New deployment → type "Web app".
 *       Execute as: Me      Who has access: Anyone
 *     Deploy, then copy the "Web app URL" (ends with /exec).
 *  5. In Bill Bol → Profile → Company database: paste the Web app URL and the
 *     access key, tap "Connect and test".
 *  6. Profile → "For accountants: client setup link" → copy the link and send it
 *     to each client's staff. Their phones connect automatically.
 *
 * After changing this code later: Deploy → Manage deployments → Edit → Version:
 * "New version" → Deploy (the URL stays the same).
 *
 * Privacy: files are created in YOUR Drive and stay private to you. Staff phones
 * only upload; they cannot read the sheet or the folder.
 */

const ROOT_FOLDER_NAME = 'Bill Bol Claims';

const SHEETS = {
  Expenses: ['Entry ID', 'Date', 'Employee', 'Mobile', 'Company', 'Trip', 'Category', 'Account head',
    'Details', 'Shop / place', 'Paid by', 'Amount (Rs.)', 'Bill copies', 'No-bill reason', 'Bill links',
    'Spoken as', 'Claim no', 'Status', 'Employee ID', 'Trip ID', 'Saved at', 'Updated at'],
  Claims: ['Claim no', 'Submitted at', 'Employee', 'Mobile', 'Company', 'Trip', 'From', 'To', 'Entries',
    'Total (Rs.)', 'Advance (Rs.)', 'Net payable (Rs.)', 'Claim PDF', 'Status', 'Approved by', 'Paid on',
    'Remarks', 'Employee ID', 'Trip ID'],
  Employees: ['Employee ID', 'Name', 'Mobile', 'Company', 'Employee code', 'Designation', 'Email',
    'Language', 'First seen', 'Last seen']
};
const CLAIM_STATUSES = ['Submitted', 'Checked', 'Approved', 'Paid', 'Rejected'];

/* ---------------- menu & set-up ---------------- */
function onOpen() {
  SpreadsheetApp.getUi().createMenu('Bill Bol')
    .addItem('1. Set up sheets', 'setup')
    .addItem('Show access key', 'showKey')
    .addItem('Make a new access key', 'newKeyMenu')
    .addItem('Open Drive folder', 'showFolder')
    .addToUi();
}

function setup() {
  const ss = SpreadsheetApp.getActive();
  Object.keys(SHEETS).forEach(name => sheet_(name));
  const claims = ss.getSheetByName('Claims');
  const col = SHEETS.Claims.indexOf('Status') + 1;
  claims.getRange(2, col, claims.getMaxRows() - 1, 1).setDataValidation(
    SpreadsheetApp.newDataValidation().requireValueInList(CLAIM_STATUSES, true).setAllowInvalid(false).build());
  const first = ss.getSheetByName('Sheet1');
  if (first && first.getLastRow() === 0 && ss.getSheets().length > 1) ss.deleteSheet(first);
  rootFolder_();
  if (!props_().getProperty('KEY')) newKey_();
  showKey();
}

function props_() { return PropertiesService.getScriptProperties(); }
function newKey_() {
  const k = Utilities.getUuid().replace(/-/g, '').slice(0, 16).toUpperCase();
  props_().setProperty('KEY', k);
  return k;
}
function newKeyMenu() {
  const ui = SpreadsheetApp.getUi();
  if (ui.alert('Make a new access key?', 'Phones using the old key will stop uploading until they enter the new key or open a new setup link.', ui.ButtonSet.OK_CANCEL) !== ui.Button.OK) return;
  newKey_(); showKey();
}
function showKey() {
  SpreadsheetApp.getUi().alert('Bill Bol access key',
    'Access key:  ' + props_().getProperty('KEY') +
    '\n\nEnter this key with the Web app URL in Bill Bol → Profile → Company database.', SpreadsheetApp.getUi().ButtonSet.OK);
}
function showFolder() {
  SpreadsheetApp.getUi().alert('Drive folder', rootFolder_().getUrl(), SpreadsheetApp.getUi().ButtonSet.OK);
}

function sheet_(name) {
  const ss = SpreadsheetApp.getActive();
  let sh = ss.getSheetByName(name);
  if (!sh) sh = ss.insertSheet(name);
  const head = SHEETS[name];
  if (sh.getLastRow() === 0 || sh.getRange(1, 1).getValue() !== head[0]) {
    sh.getRange(1, 1, 1, head.length).setValues([head]);
  }
  sh.getRange(1, 1, 1, head.length).setFontWeight('bold').setBackground('#0B2A5B').setFontColor('#FFFFFF');
  sh.setFrozenRows(1);
  return sh;
}

function rootFolder_() {
  const id = props_().getProperty('FOLDER');
  if (id) { try { const f = DriveApp.getFolderById(id); if (!f.isTrashed()) return f; } catch (e) {} }
  const f = DriveApp.createFolder(ROOT_FOLDER_NAME);
  props_().setProperty('FOLDER', f.getId());
  return f;
}
function subFolder_(parent, name) {
  const clean = String(name || 'Unknown').replace(/[\\/:*?"<>|]/g, ' ').trim().slice(0, 80) || 'Unknown';
  const it = parent.getFoldersByName(clean);
  return it.hasNext() ? it.next() : parent.createFolder(clean);
}
function employeeFolder_(emp, kind) {
  const company = subFolder_(rootFolder_(), emp.company);
  const person = subFolder_(company, (emp.name || 'Employee') + ' (' + (emp.mobile || emp.id || '') + ')');
  return kind ? subFolder_(person, kind) : person;
}

/* ---------------- web app ---------------- */
function out_(o) {
  return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON);
}
function doGet() { return out_({ ok: true, app: 'Bill Bol', note: 'This address receives data from the Bill Bol app.' }); }

function doPost(e) {
  let d;
  try { d = JSON.parse(e.postData.contents); } catch (err) { return out_({ ok: false, error: 'Bad request' }); }
  const key = props_().getProperty('KEY');
  if (!key) return out_({ ok: false, error: 'The sheet is not set up yet. Open the sheet → Bill Bol → 1. Set up sheets.' });
  if (String(d.key || '').trim().toUpperCase() !== key) return out_({ ok: false, error: 'Wrong access key. Check Profile → Company database.' });

  const lock = LockService.getScriptLock();
  lock.waitLock(30000);
  try {
    const emp = d.employee || {};
    if (!emp.id || !emp.name) return out_({ ok: false, error: 'Profile missing. Fill the profile in the app.' });
    upsertEmployee_(emp);
    switch (d.action) {
      case 'ping':
      case 'profile': return out_({ ok: true, sheet: SpreadsheetApp.getActive().getName() });
      case 'entry': return out_(saveEntry_(emp, d.entry || {}, d.files || []));
      case 'delete': return out_(deleteEntry_(d.entryId));
      case 'claim': return out_(saveClaim_(emp, d.claim || {}, d.pdf));
      default: return out_({ ok: false, error: 'Unknown action' });
    }
  } catch (err) {
    return out_({ ok: false, error: String((err && err.message) || err) });
  } finally {
    lock.releaseLock();
  }
}

/* ---------------- helpers ---------------- */
function findRow_(sh, id) {
  if (!id || sh.getLastRow() < 2) return 0;
  const hit = sh.getRange(2, 1, sh.getLastRow() - 1, 1).createTextFinder(String(id)).matchEntireCell(true).findNext();
  return hit ? hit.getRow() : 0;
}
function toDate_(ymd) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(ymd || ''));
  return m ? new Date(+m[1], +m[2] - 1, +m[3]) : '';
}
function linksCell_(sh, row, col, items) {
  /* items: [{text, url}] → one cell with each label linked */
  const cell = sh.getRange(row, col);
  if (!items.length) { cell.setValue(''); return; }
  const text = items.map(i => i.text).join('\n');
  const b = SpreadsheetApp.newRichTextValue().setText(text);
  let pos = 0;
  items.forEach(i => { b.setLinkUrl(pos, pos + i.text.length, i.url); pos += i.text.length + 1; });
  cell.setRichTextValue(b.build());
}

function upsertEmployee_(emp) {
  const sh = sheet_('Employees');
  const r = findRow_(sh, emp.id);
  const now = new Date();
  const first = r ? sh.getRange(r, 9).getValue() : now;
  const row = [emp.id, emp.name, emp.mobile || '', emp.company || '', emp.emp || '', emp.designation || '',
    emp.email || '', emp.lang || '', first || now, now];
  if (r) sh.getRange(r, 1, 1, row.length).setValues([row]); else sh.appendRow(row);
}

function saveEntry_(emp, en, files) {
  if (!en.id) return { ok: false, error: 'Entry without ID' };
  const folder = employeeFolder_(emp, 'Bills');
  const links = Object.assign({}, en.links || {});
  files.forEach(f => {
    const blob = Utilities.newBlob(Utilities.base64Decode(f.data), f.mime || 'application/octet-stream', f.name || (en.id + '.jpg'));
    const file = folder.createFile(blob);
    links[f.id] = file.getUrl();
  });
  const sh = sheet_('Expenses');
  const r = findRow_(sh, en.id);
  const now = new Date();
  const keepClaim = r ? sh.getRange(r, 17).getValue() : '';
  const keepStatus = r ? sh.getRange(r, 18).getValue() : '';
  const savedAt = r ? sh.getRange(r, 21).getValue() : (en.savedAt ? new Date(en.savedAt) : now);
  const photos = en.photos || [];
  const row = [en.id, toDate_(en.date), emp.name, emp.mobile || '', emp.company || '', en.trip || '', en.category || '',
    en.head || '', en.details || '', en.vendor || '', en.mode || '', Number(en.amount) || 0, photos.length,
    en.noBill || '', '', en.spoken || '', keepClaim || '', keepStatus || 'Saved', emp.id, en.tripId || '', savedAt, now];
  let rowNo = r;
  if (r) sh.getRange(r, 1, 1, row.length).setValues([row]); else { sh.appendRow(row); rowNo = sh.getLastRow(); }
  sh.getRange(rowNo, 2).setNumberFormat('dd-mm-yyyy');
  sh.getRange(rowNo, 12).setNumberFormat('#,##0.00');
  linksCell_(sh, rowNo, 15, photos.filter(p => links[p]).map((p, i) => ({ text: 'Bill ' + (i + 1), url: links[p] })));
  return { ok: true, links: links, row: rowNo };
}

function deleteEntry_(id) {
  const sh = sheet_('Expenses');
  const r = findRow_(sh, id);
  if (r) { sh.getRange(r, 18).setValue('Deleted by employee'); sh.getRange(r, 22).setValue(new Date()); }
  return { ok: true };
}

function saveClaim_(emp, c, pdf) {
  if (!c.no) return { ok: false, error: 'Claim without number' };
  let url = '';
  if (pdf && pdf.data) {
    const folder = employeeFolder_(emp, 'Claims');
    const name = (pdf.name || c.no + '.pdf').replace(/\.pdf$/i, '') + ' (' + c.no + ').pdf';
    const old = folder.getFilesByName(name);
    while (old.hasNext()) old.next().setTrashed(true);
    const file = folder.createFile(Utilities.newBlob(Utilities.base64Decode(pdf.data), 'application/pdf', name));
    url = file.getUrl();
  }
  const sh = sheet_('Claims');
  const r = findRow_(sh, c.no);
  const keep = r ? sh.getRange(r, 14, 1, 4).getValues()[0] : ['Submitted', '', '', ''];
  if (r && keep[0] && keep[0] !== 'Submitted') keep[3] = (keep[3] ? keep[3] + ' | ' : '') + 'Resubmitted ' + Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'dd-MM-yyyy');
  const row = [c.no, c.submittedAt ? new Date(c.submittedAt) : new Date(), emp.name, emp.mobile || '', emp.company || '', c.trip || '',
    toDate_(c.from), toDate_(c.to), Number(c.entries) || 0, Number(c.total) || 0, Number(c.advance) || 0, Number(c.net) || 0, '',
    keep[0] || 'Submitted', keep[1], keep[2], keep[3], emp.id, c.tripId || ''];
  let rowNo = r;
  if (r) sh.getRange(r, 1, 1, row.length).setValues([row]); else { sh.appendRow(row); rowNo = sh.getLastRow(); }
  sh.getRange(rowNo, 7, 1, 2).setNumberFormat('dd-mm-yyyy');
  sh.getRange(rowNo, 10, 1, 3).setNumberFormat('#,##0.00');
  if (url) linksCell_(sh, rowNo, 13, [{ text: 'Open claim PDF', url: url }]);
  /* mark the entries as claimed */
  const ex = sheet_('Expenses');
  (c.entryIds || []).forEach(id => {
    const er = findRow_(ex, id);
    if (er) { ex.getRange(er, 17).setValue(c.no); ex.getRange(er, 18).setValue('Claimed'); }
  });
  return { ok: true, pdfUrl: url, row: rowNo };
}
