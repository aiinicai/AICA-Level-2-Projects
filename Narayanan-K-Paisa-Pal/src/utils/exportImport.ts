import { AppRow, Kind, UserProfile } from '../types';
import {
  CATS,
  DEF_ALERTS,
  DEF_INV_ALERTS,
  FREQ,
  inr,
  INV,
  longD,
  normAll,
  REC,
  stateOf,
  todayIST,
  uid,
  whenTxt,
} from './calculations';
import { parseCsv } from './documentParser';
import { getAllAttachments, restoreAttachments, AttachmentRecord } from './attachmentStorage';

export interface BackupPayloadV2 {
  version: 2;
  format: 'paisa-pal-backup';
  exportedAt: string;
  profile: UserProfile;
  rows: AppRow[];
  attachments: AttachmentRecord[];
}

export function downloadFile(name: string, content: string, type: string) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

// Complete JSON backup including all IndexedDB attachments
export async function exportBackupJson(rows: AppRow[], profile: UserProfile): Promise<{ attachmentCount: number }> {
  const dateStr = todayIST();
  let attachments: AttachmentRecord[] = [];
  try {
    attachments = await getAllAttachments();
  } catch (e) {
    console.warn('Could not read attachments for backup', e);
  }

  const payload: BackupPayloadV2 = {
    version: 2,
    format: 'paisa-pal-backup',
    exportedAt: new Date().toISOString(),
    profile,
    rows,
    attachments,
  };

  const jsonStr = JSON.stringify(payload, null, 2);
  downloadFile(`paisa-pal-backup-${dateStr}.json`, jsonStr, 'application/json');
  return { attachmentCount: attachments.length };
}

// Complete JSON backup restore supporting both v2 (with attachments) and v1 legacy
export async function parseAndRestoreBackup(
  jsonStr: string
): Promise<{ rows: AppRow[]; profile: UserProfile; attachmentCount: number }> {
  const parsed = JSON.parse(jsonStr);
  const rows = Array.isArray(parsed.rows) ? parsed.rows : [];
  const profile = parsed.profile || {};
  let restoredAttachmentCount = 0;

  if (Array.isArray(parsed.attachments) && parsed.attachments.length > 0) {
    try {
      await restoreAttachments(parsed.attachments);
      restoredAttachmentCount = parsed.attachments.length;
    } catch (e) {
      console.error('Failed to restore some attachments from backup', e);
    }
  }

  return { rows, profile, attachmentCount: restoredAttachmentCount };
}

// Unified CSV Export for all kinds (due, inv, rec) with round-trip compatibility
export function exportCsvData(rows: AppRow[]) {
  const cols = [
    'kind',
    'name_or_title',
    'category_or_type',
    'provider_or_institution',
    'holder',
    'ref_or_number',
    'amount',
    'date_or_due',
    'frequency',
    'interval',
    'alerts',
    'status',
    'anchor',
    'notes',
  ];

  const q = (s: any) => '"' + String(s ?? '').replace(/"/g, '""') + '"';

  const lines = [cols.join(',')].concat(
    rows.map((r) => {
      const d = r.data || {};
      const amountVal =
        d.amount != null && d.amount !== ''
          ? d.amount
          : d.current != null && d.current !== ''
          ? d.current
          : d.invested ?? '';

      const dateVal = d.due || d.maturity || d.expires || '';
      const alertVal = Array.isArray(d.alerts) ? d.alerts.join('|') : '';

      return [
        r.kind,
        d.name || d.title || '',
        d.category || d.type || '',
        d.provider || d.institution || '',
        d.holder || '',
        d.ref || d.number || '',
        amountVal,
        dateVal,
        d.freq || '',
        d.interval || '',
        alertVal,
        d.status || '',
        d.anchor || '',
        d.notes || '',
      ]
        .map(q)
        .join(',');
    })
  );

  downloadFile('paisa-pal-data.csv', lines.join('\n'), 'text/csv;charset=utf-8;');
}

// Clean raw numeric string from CSV (handles commas, currency signs like ₹ or Rs)
function cleanNumber(val: string): number {
  if (!val) return 0;
  const cleaned = val.replace(/[₹,Rs\s]/g, '');
  const num = parseFloat(cleaned);
  return Number.isFinite(num) ? num : 0;
}

// Unified CSV Importer handling all kinds and both new and legacy formats
export function importCsvData(txt: string): { imported: AppRow[]; count: number } {
  const [headRaw, ...body] = parseCsv(txt.replace(/^\uFEFF/, ''));
  if (!headRaw || headRaw.length === 0) {
    throw new Error('CSV file is empty or cannot be read.');
  }

  const head = headRaw.map((h) => h.toLowerCase().trim().replace(/[\s_-]+/g, '_'));

  const findIdx = (...keys: string[]) => {
    for (const k of keys) {
      const idx = head.findIndex((h) => h === k || h.includes(k));
      if (idx !== -1) return idx;
    }
    return -1;
  };

  const nameIdx = findIdx('name_or_title', 'name', 'title', 'item');
  const dateIdx = findIdx('date_or_due', 'date', 'due', 'maturity', 'expires');

  if (nameIdx === -1 && dateIdx === -1) {
    throw new Error(
      'CSV header must include at least an item name or date column.'
    );
  }

  const kindIdx = findIdx('kind', 'type_of_entry');
  const catIdx = findIdx('category_or_type', 'category', 'type');
  const provIdx = findIdx('provider_or_institution', 'provider', 'institution', 'bank', 'company');
  const holderIdx = findIdx('holder', 'who', 'person');
  const refIdx = findIdx('ref_or_number', 'ref', 'number', 'account', 'policy');
  const amtIdx = findIdx('amount', 'amount_or_value', 'value', 'invested', 'premium');
  const freqIdx = findIdx('frequency', 'freq');
  const intervalIdx = findIdx('interval', 'interval_days');
  const alertsIdx = findIdx('alerts', 'alert_days');
  const statusIdx = findIdx('status');
  const anchorIdx = findIdx('anchor', 'anchor_day');
  const notesIdx = findIdx('notes', 'remarks', 'description');

  const col = (r: string[], idx: number) => (idx !== -1 && r[idx] ? r[idx].trim() : '');

  const imported: AppRow[] = [];

  for (const r of body) {
    const rawName = col(r, nameIdx);
    const rawDate = col(r, dateIdx);
    if (!rawName && !rawDate) continue;

    const rawKind = col(r, kindIdx).toLowerCase();
    const rawCat = col(r, catIdx).toLowerCase();
    const rawAmount = cleanNumber(col(r, amtIdx));
    const holder = col(r, holderIdx);
    const provider = col(r, provIdx);
    const ref = col(r, refIdx);
    const notes = col(r, notesIdx);

    // Determine entry kind: explicit or inferred
    let kind: Kind = 'due';
    if (rawKind === 'inv' || rawKind === 'investment') {
      kind = 'inv';
    } else if (rawKind === 'rec' || rawKind === 'record' || rawKind === 'document') {
      kind = 'rec';
    } else if (['fd', 'rd', 'mf', 'stocks', 'gold', 'bond', 'ppf', 'nps', 'property'].includes(rawCat)) {
      kind = 'inv';
    } else if (['passport', 'licence', 'id', 'bank_rec', 'vehicle_rec'].includes(rawCat)) {
      kind = 'rec';
    }

    const rawAlerts = col(r, alertsIdx);
    const parsedAlerts = rawAlerts
      ? rawAlerts.split(/[|\s,]+/).map(Number).filter((x) => Number.isFinite(x) && x >= 0)
      : [];

    if (kind === 'inv') {
      const invType = (INV as Record<string, string>)[rawCat] ? rawCat : 'fd';
      imported.push({
        id: uid(),
        kind: 'inv',
        data: {
          name: rawName || 'Investment',
          type: invType,
          institution: provider,
          holder,
          ref,
          invested: rawAmount || '',
          current: rawAmount || '',
          alerts:
            parsedAlerts.length > 0
              ? parsedAlerts
              : (DEF_INV_ALERTS as Record<string, number[]>)[invType] || [30, 7],
        },
      });
    } else if (kind === 'rec') {
      const recType = (REC as Record<string, string>)[rawCat] ? rawCat : 'other';
      imported.push({
        id: uid(),
        kind: 'rec',
        data: {
          title: rawName || 'Document record',
          type: recType,
          holder,
          number: ref,
          expires: rawDate || '',
          alerts: parsedAlerts.length ? parsedAlerts : [60, 30, 7],
          notes,
        },
      });
    } else {
      // Kind: 'due'
      const cat = (CATS as Record<string, string>)[rawCat] ? rawCat : 'utility';
      const rawFreq = col(r, freqIdx).toLowerCase();
      const freq = (FREQ as Record<string, string>)[rawFreq] ? rawFreq : 'monthly';
      const interval = cleanNumber(col(r, intervalIdx)) || 35;
      const status = col(r, statusIdx).toLowerCase() === 'paid' ? 'paid' : 'pending';
      const anchorVal = cleanNumber(col(r, anchorIdx));
      const anchor = anchorVal > 0 ? anchorVal : rawDate ? +rawDate.slice(8, 10) || 1 : 1;

      imported.push({
        id: uid(),
        kind: 'due',
        data: {
          name: rawName || 'Due entry',
          category: cat,
          provider,
          holder,
          ref,
          amount: rawAmount || '',
          due: rawDate || todayIST(),
          freq,
          interval,
          alerts: parsedAlerts.length ? parsedAlerts : DEF_ALERTS[cat] || [7, 1],
          status,
          anchor,
          notes,
        },
      });
    }
  }

  return { imported, count: imported.length };
}

export function generateWhatsAppDigest(rows: AppRow[]): string {
  const t = todayIST();
  const al = rows
    .flatMap(normAll)
    .filter((a) => ['overdue', 'today', 'soon'].includes(stateOf(a)))
    .sort((a, b) => a.due.localeCompare(b.due));

  if (!al.length) {
    return `*Paisa Pal* - ${longD(t)}\nNothing is due inside your alert windows. All clear!`;
  }

  const out = [`*Paisa Pal* - ${longD(t)}`];
  let tot = 0;

  const sections: [string, string][] = [
    ['overdue', '*Overdue*'],
    ['today', '*Due today*'],
    ['soon', '*Coming up*'],
  ];

  for (const [k, title] of sections) {
    const g = al.filter((a) => stateOf(a) === k);
    if (!g.length) continue;
    out.push('', title);
    g.forEach((a) => {
      const whoTag = a.who ? ` [${a.who}]` : '';
      const subTag = a.sub ? ` (${a.sub})` : '';
      const amtTag = a.amount ? `, ${inr(a.amount)}` : '';
      out.push(`- ${a.label}: ${a.name}${whoTag}${subTag}${amtTag}, ${whenTxt(a)}`);
    });
    tot += g.filter((a) => a.vk === 'due').reduce((s, a) => s + a.amount, 0);
  }

  if (tot) {
    out.push('', `Total: ${inr(tot)}`);
  }

  return out.join('\n');
}

export function triggerPrint() {
  window.print();
}

// Download the project's index.html file directly
export async function downloadIndexHtml() {
  try {
    const resp = await fetch('/index.html');
    if (resp.ok) {
      const htmlText = await resp.text();
      downloadFile('index.html', htmlText, 'text/html;charset=utf-8;');
      return;
    }
  } catch (e) {
    console.warn('Could not fetch /index.html directly', e);
  }
  const fallbackHtml = `<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
    <title>Paisa Pal - Due Dates, Investments & Records</title>
    <meta name="description" content="Installable personal finance manager for due dates, bills, investments, maturities, and document records." />
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>`;
  downloadFile('index.html', fallbackHtml, 'text/html;charset=utf-8;');
}

// Export complete data as a standalone, self-contained HTML report
export function exportStandaloneHtml(rows: AppRow[], profile: UserProfile) {
  const dues = rows.filter((r) => r.kind === 'due');
  const invs = rows.filter((r) => r.kind === 'inv');
  const recs = rows.filter((r) => r.kind === 'rec');

  const totalDue = dues.reduce((sum, r) => sum + (Number(r.data?.amount) || 0), 0);
  const totalInvested = invs.reduce((sum, r) => sum + (Number(r.data?.invested) || 0), 0);
  const totalMaturity = invs.reduce((sum, r) => sum + (Number(r.data?.current || r.data?.invested) || 0), 0);

  const formatMoney = (v: number | string) => {
    const n = Number(v);
    return isNaN(n) ? '—' : `₹${n.toLocaleString('en-IN')}`;
  };

  const htmlContent = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Paisa Pal - Portfolio & Records Statement (${todayIST()})</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin: 40px; color: #1e293b; background: #fff; line-height: 1.5; }
    .header { display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 2px solid #0e7c86; padding-bottom: 16px; margin-bottom: 24px; }
    h1 { color: #0e7c86; margin: 0 0 4px 0; font-size: 24px; font-weight: 700; }
    .subtitle { color: #64748b; font-size: 13px; margin: 0; }
    .btn-print { background: #0e7c86; color: #fff; border: none; padding: 8px 16px; border-radius: 6px; font-size: 12px; font-weight: 600; cursor: pointer; }
    .kpi-bar { display: flex; gap: 16px; margin-bottom: 28px; flex-wrap: wrap; }
    .kpi-card { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px 18px; min-width: 170px; }
    .kpi-label { font-size: 11px; text-transform: uppercase; color: #64748b; font-weight: 600; letter-spacing: 0.5px; }
    .kpi-value { font-size: 20px; font-weight: 700; color: #0f172a; margin-top: 4px; }
    h2 { font-size: 16px; margin-top: 32px; margin-bottom: 12px; color: #0f172a; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #cbd5e1; padding-bottom: 6px; }
    table { width: 100%; border-collapse: collapse; font-size: 12px; margin-bottom: 24px; }
    th { text-align: left; background: #f1f5f9; padding: 9px 12px; border: 1px solid #cbd5e1; font-weight: 600; color: #334155; }
    td { padding: 9px 12px; border: 1px solid #e2e8f0; }
    tr:nth-child(even) { background: #f8fafc; }
    .pill { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 10px; font-weight: 600; }
    .pill-green { background: #dcfce7; color: #166534; }
    .pill-blue { background: #e0f2fe; color: #075985; }
    .pill-amber { background: #fef3c7; color: #92400e; }
    .footer { margin-top: 40px; font-size: 11px; color: #94a3b8; text-align: center; border-top: 1px solid #e2e8f0; padding-top: 16px; }
    @media print { body { margin: 15px; } .btn-print { display: none; } }
  </style>
</head>
<body>
  <div class="header">
    <div>
      <h1>Paisa Pal - Financial & Records Statement</h1>
      <p class="subtitle">Generated on ${todayIST()} | Total active records: ${rows.length}</p>
    </div>
    <button class="btn-print" onclick="window.print()">Print / Save PDF</button>
  </div>

  <div class="kpi-bar">
    <div class="kpi-card">
      <div class="kpi-label">Total Bills / Dues</div>
      <div class="kpi-value">${formatMoney(totalDue)}</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Total Principal Invested</div>
      <div class="kpi-value">${formatMoney(totalInvested)}</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Expected Maturity Value</div>
      <div class="kpi-value">${formatMoney(totalMaturity)}</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Official Records & IDs</div>
      <div class="kpi-value">${recs.length} Saved</div>
    </div>
  </div>

  <h2>1. Upcoming Bills & Dues (${dues.length})</h2>
  <table>
    <thead>
      <tr>
        <th>Name / Biller</th>
        <th>Category</th>
        <th>Due Date</th>
        <th>Frequency</th>
        <th>Person</th>
        <th>Amount</th>
      </tr>
    </thead>
    <tbody>
      ${dues.map((d) => `<tr>
        <td><strong>${d.data?.name || '—'}</strong><br><small style="color:#64748b">${d.data?.provider || ''}</small></td>
        <td><span class="pill pill-blue">${d.data?.category || 'Bill'}</span></td>
        <td>${d.data?.due || '—'}</td>
        <td>${d.data?.freq || 'Monthly'}</td>
        <td>${d.data?.holder || 'Family'}</td>
        <td><strong>${formatMoney(d.data?.amount)}</strong></td>
      </tr>`).join('')}
    </tbody>
  </table>

  <h2>2. Investments & Fixed Deposits (${invs.length})</h2>
  <table>
    <thead>
      <tr>
        <th>Investment / Institution</th>
        <th>Account / Ref #</th>
        <th>Depositor</th>
        <th>Interest Rate</th>
        <th>Maturity Date</th>
        <th>Principal</th>
        <th>Maturity Value</th>
      </tr>
    </thead>
    <tbody>
      ${invs.map((i) => `<tr>
        <td><strong>${i.data?.name || i.data?.institution || 'Fixed Deposit'}</strong><br><small style="color:#64748b">${i.data?.institution || ''}</small></td>
        <td><code>${i.data?.ref || i.data?.number || '—'}</code></td>
        <td>${i.data?.holder || '—'}</td>
        <td><span class="pill pill-green">${i.data?.rate ? `${i.data.rate}% p.a.` : '—'}</span></td>
        <td>${i.data?.maturity || '—'}</td>
        <td><strong>${formatMoney(i.data?.invested)}</strong></td>
        <td style="color:#0e7c86"><strong>${formatMoney(i.data?.current || i.data?.invested)}</strong></td>
      </tr>`).join('')}
    </tbody>
  </table>

  <h2>3. Official Records, IDs & Passports (${recs.length})</h2>
  <table>
    <thead>
      <tr>
        <th>Document Title</th>
        <th>Type</th>
        <th>Document / ID Number</th>
        <th>Holder Name</th>
        <th>Expiry Date</th>
        <th>Notes</th>
      </tr>
    </thead>
    <tbody>
      ${recs.map((r) => `<tr>
        <td><strong>${r.data?.title || r.data?.name || 'Document'}</strong></td>
        <td><span class="pill pill-amber">${r.data?.type || 'Record'}</span></td>
        <td><code>${r.data?.number || '—'}</code></td>
        <td>${r.data?.holder || '—'}</td>
        <td>${r.data?.expires || 'No Expiry'}</td>
        <td style="color:#64748b; font-size:11px;">${r.data?.notes || '—'}</td>
      </tr>`).join('')}
    </tbody>
  </table>

  <div class="footer">
    Generated by Paisa Pal · Client-Side Encrypted Personal Finance Vault · Standalone Offline HTML Statement
  </div>
</body>
</html>`;

  downloadFile(`paisa-pal-statement-${todayIST()}.html`, htmlContent, 'text/html;charset=utf-8;');
}
