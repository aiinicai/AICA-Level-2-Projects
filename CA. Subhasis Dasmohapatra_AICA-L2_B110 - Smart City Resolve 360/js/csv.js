/* ===== RESOLVE 360 — csv.js =====
   parseCSV(text)  -> array of validated record objects (throws on bad data)
   toCSV(rows)     -> CSV text for export
   downloadText()  -> saves a text file in the browser */

function parseCSV(text) {
  text = text.replace(/^﻿/, '');              // strip Excel BOM
  const rows = [];
  let row = [], cell = '', inQuotes = false;

  // Character-by-character parser: handles quotes, "" escapes, CRLF
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (inQuotes) {
      if (ch === '"' && text[i + 1] === '"') { cell += '"'; i++; }
      else if (ch === '"') inQuotes = false;
      else cell += ch;
    } else if (ch === '"') {
      inQuotes = true;
    } else if (ch === ',') {
      row.push(cell); cell = '';
    } else if (ch === '\n' || ch === '\r') {
      if (ch === '\r' && text[i + 1] === '\n') i++;
      row.push(cell);
      if (row.some(x => x.trim())) rows.push(row);
      row = []; cell = '';
    } else {
      cell += ch;
    }
  }
  if (inQuotes) throw new Error('Unclosed quoted CSV field');
  row.push(cell);
  if (row.some(x => x.trim())) rows.push(row);
  if (!rows.length) throw new Error('Empty CSV');

  // Header check
  const headers = rows.shift().map(h => h.trim());
  const missing = CONFIG.REQUIRED_COLUMNS.filter(k => !headers.includes(k));
  if (missing.length) throw new Error('Missing columns: ' + missing.join(', '));

  // Convert and validate each row
  return rows.map((r, i) => {
    const line = i + 2;                              // +1 header, +1 human count
    if (r.length !== headers.length) throw new Error('Column count mismatch on row ' + line);
    const rec = Object.fromEntries(headers.map((h, j) => [h, r[j].trim()]));

    for (const k of CONFIG.NUMERIC_COLUMNS) {
      const n = Number(rec[k]);
      if (rec[k] === '' || !Number.isFinite(n) || n < 0) throw new Error('Invalid ' + k + ' on row ' + line);
      rec[k] = n;
    }
    if (!Number.isInteger(rec.severity) || rec.severity < 1 || rec.severity > 5)
      throw new Error('Severity must be 1-5 on row ' + line);
    if (!CONFIG.STATUSES.includes(rec.status))
      throw new Error('Invalid status on row ' + line);
    return rec;
  });
}

function toCSV(rows) {
  const keys = CONFIG.EXPORT_COLUMNS;
  const q = v => '"' + String(v ?? '').replace(/"/g, '""') + '"';
  const body = rows.map(r => keys.map(k =>
    q(k === 'priority_score' ? score(r).toFixed(2) : r[k])).join(','));
  return [keys.join(','), ...body].join('\r\n');
}

function downloadText(text, filename) {
  const url = URL.createObjectURL(new Blob([text], { type: 'text/csv;charset=utf-8' }));
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
