import fs from 'fs';

// Sample HTML representation of IBJA table row
const sampleIbjaHtml = `
<table id="MainContent_GridView1" class="table table-bordered table-striped">
  <thead>
    <tr>
      <th>Date</th>
      <th>Gold 999 AM</th>
      <th>Gold 999 PM</th>
      <th>Gold 995 AM</th>
      <th>Gold 995 PM</th>
      <th>Gold 916 AM</th>
      <th>Gold 916 PM</th>
      <th>Silver 999 AM</th>
      <th>Silver 999 PM</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>31-10-2026</td>
      <td>140200.00</td>
      <td>140450.00</td>
      <td>139650.00</td>
      <td>139900.00</td>
      <td>128420.00</td>
      <td>128650.00</td>
      <td>181500.00</td>
      <td>181800.00</td>
    </tr>
    <tr>
      <td>30-10-2026</td>
      <td>139800.00</td>
      <td>140054.00</td>
      <td>139250.00</td>
      <td>139493.78</td>
      <td>128050.00</td>
      <td>128289.00</td>
      <td>181000.00</td>
      <td>181344.00</td>
    </tr>
  </tbody>
</table>
`;

function parseIbjaHtml(html) {
  // Regex extraction for table rows
  const rowRegex = /<tr[^>]*>([\s\S]*?)<\/tr>/gi;
  const rows = [];
  let match;
  while ((match = rowRegex.exec(html)) !== null) {
    const rowHtml = match[1];
    const cellRegex = /<t[dh][^>]*>([\s\S]*?)<\/t[dh]>/gi;
    const cells = [];
    let cellMatch;
    while ((cellMatch = cellRegex.exec(rowHtml)) !== null) {
      cells.push(cellMatch[1].replace(/<[^>]+>/g, '').replace(/,/g, '').trim());
    }
    if (cells.length >= 7) {
      rows.push(cells);
    }
  }

  // Look for the first data row with date
  for (let i = 1; i < rows.length; i++) {
    const r = rows[i];
    const dateStr = r[0]; // e.g. 31-10-2026
    const dParts = dateStr.match(/^(\d{1,2})[-\/](\d{1,2})[-\/](\d{4})$/);
    if (!dParts) continue;

    const day = dParts[1].padStart(2, '0');
    const mon = dParts[2].padStart(2, '0');
    const year = dParts[3];
    const isoDate = `${year}-${mon}-${day}`;

    // Find Gold 999 PM, Gold 995 PM, Silver 999 PM
    // In standard IBJA table:
    // col 1: Gold 999 AM, col 2: Gold 999 PM
    // col 3: Gold 995 AM, col 4: Gold 995 PM
    // Silver 999 PM is typically last or second to last
    const g999Pm = parseFloat(r[2]) || parseFloat(r[1]);
    const g995Pm = parseFloat(r[4]) || parseFloat(r[3]);
    const s999Pm = parseFloat(r[r.length - 1]) || parseFloat(r[r.length - 2]);

    if (g999Pm > 0 && g995Pm > 0 && s999Pm > 0) {
      return {
        success: true,
        date: isoDate,
        session: 'PM',
        gold999Per10g: g999Pm,
        gold999PerGram: Math.round((g999Pm / 10) * 1000) / 1000,
        gold995Per10g: g995Pm,
        gold995PerGram: Math.round((g995Pm / 10) * 1000) / 1000,
        silver999PerKg: s999Pm,
        silver999PerGram: Math.round((s999Pm / 1000) * 1000) / 1000,
        source: 'IBJA (Official Free Daily PM Benchmark)'
      };
    }
  }

  return { success: false, error: 'Could not extract IBJA rate row from HTML' };
}

const parsed = parseIbjaHtml(sampleIbjaHtml);
console.log('Parsed IBJA Sample:', parsed);
