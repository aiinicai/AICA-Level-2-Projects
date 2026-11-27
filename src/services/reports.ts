import { Account, CategoryBudget, ExpenseCategory, Transaction } from '../types/finance';

export function exportTransactionsToCSV(
  transactions: Transaction[],
  accounts: Account[],
  filenamePrefix = 'DirhamTrack_UAE_Expenses'
): void {
  const accountMap = new Map(accounts.map(a => [a.id, a.name]));

  const headers = [
    'Transaction ID',
    'Date',
    'Bank / Source',
    'Account',
    'Type',
    'Merchant',
    'Category',
    'Amount (AED)',
    'Original Amount',
    'Original Currency',
    'Red Flag Alert',
    'Red Flag Reason',
    'Status',
    'Notes'
  ];

  const rows = transactions.map(t => {
    const accName = accountMap.get(t.accountId) || 'Unknown Account';
    return [
      `"${t.id}"`,
      `"${t.date} ${t.time || ''}"`,
      `"${t.bankName || 'Manual'}"`,
      `"${accName}"`,
      `"${t.type}"`,
      `"${t.merchant.replace(/"/g, '""')}"`,
      `"${t.categorySplits && t.categorySplits.length > 1 ? t.categorySplits.map(s => `${s.category} (AED ${s.amount.toFixed(2)})`).join(' + ') : t.category}"`,
      t.amount.toFixed(2),
      t.originalAmount ? t.originalAmount.toFixed(2) : '',
      `"${t.originalCurrency || 'AED'}"`,
      t.isRedFlag ? 'YES (FLAGGED)' : 'NO',
      `"${(t.redFlagReason || '').replace(/"/g, '""')}"`,
      t.isVerifiedByUser ? 'Verified' : 'Pending Review',
      `"${(t.notes || '').replace(/"/g, '""')}"`
    ];
  });

  const csvContent = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
  const blob = new Blob(['\uFEFF' + csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.setAttribute('href', url);
  link.setAttribute('download', `${filenamePrefix}_${new Date().toISOString().split('T')[0]}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export interface StatementData {
  monthTitle: string;
  monthPeriod: string;
  transactions: Transaction[];
  accounts: Account[];
  budgets: CategoryBudget[];
  totalIncome: number;
  totalExpense: number;
  netSavings: number;
  savingsRate: number;
  categoryTotals: Record<string, number>;
  redFlags: Transaction[];
}

export function generateStandaloneStatementHTML(data: StatementData): string {
  const accountMap = new Map(data.accounts.map(a => [a.id, a.name]));
  const todayStr = new Date().toLocaleDateString('en-AE', { day: 'numeric', month: 'short', year: 'numeric' });

  const categoryRows = data.budgets.map(b => {
    const spent = data.categoryTotals[b.category] || 0;
    const share = data.totalExpense > 0 ? (spent / data.totalExpense) * 100 : 0;
    return `
      <tr>
        <td style="padding: 8px 12px; font-weight: 600; color: #1e293b;">${b.category}</td>
        <td style="padding: 8px 12px; text-align: right; font-weight: 700; color: #0f172a;">AED ${spent.toLocaleString('en-AE', { minimumFractionDigits: 2 })}</td>
        <td style="padding: 8px 12px; text-align: right; color: #64748b;">AED ${b.monthlyLimit.toLocaleString('en-AE', { minimumFractionDigits: 2 })}</td>
        <td style="padding: 8px 12px; text-align: right; color: #475569; font-weight: 500;">${share.toFixed(1)}%</td>
      </tr>
    `;
  }).join('');

  const redFlagRows = data.redFlags.map(rf => `
    <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 0; border-bottom: 1px solid #fee2e2;">
      <span>
        <strong>${rf.date}</strong> · ${rf.merchant} (${rf.bankName || 'Bank'})
        ${rf.redFlagReason ? `<span style="color: #991b1b; font-size: 11px; margin-left: 6px;">[${rf.redFlagReason}]</span>` : ''}
      </span>
      <span style="font-weight: 700; color: #b91c1c;">AED ${rf.amount.toFixed(2)} ${rf.originalAmount ? `(${rf.originalCurrency} ${rf.originalAmount})` : ''}</span>
    </div>
  `).join('');

  const txRows = data.transactions.map(t => {
    const acc = accountMap.get(t.accountId) || t.bankName || 'Manual Ledger';
    const isIncome = t.type === 'income';
    return `
      <tr>
        <td style="padding: 7px 10px; color: #64748b; font-family: monospace; font-size: 11px; white-space: nowrap;">${t.date}</td>
        <td style="padding: 7px 10px; font-weight: 700; color: #0f172a;">${t.merchant}</td>
        <td style="padding: 7px 10px;"><span style="display: inline-block; padding: 2px 6px; border-radius: 4px; background: #f1f5f9; color: #334155; font-size: 10px; font-weight: 600;">${t.category}</span></td>
        <td style="padding: 7px 10px; color: #475569; font-size: 11px;">${acc}</td>
        <td style="padding: 7px 10px; text-align: right; font-weight: 800; color: ${isIncome ? '#047857' : '#0f172a'};">
          ${isIncome ? '+' : '-'} AED ${t.amount.toLocaleString('en-AE', { minimumFractionDigits: 2 })}
        </td>
      </tr>
    `;
  }).join('');

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>DirhamTrack Statement — ${data.monthTitle}</title>
  <style>
    @page {
      size: A4 portrait;
      margin: 10mm;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      padding: 20px;
      background: #ffffff;
      color: #0f172a;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      font-size: 12px;
      line-height: 1.5;
    }
    .action-bar {
      position: sticky;
      top: 0;
      background: #042f2e;
      color: #ffffff;
      padding: 12px 20px;
      margin: -20px -20px 20px -20px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      box-shadow: 0 4px 12px rgba(0,0,0,0.15);
      z-index: 100;
    }
    .action-btn {
      background: #0d9488;
      color: #ffffff;
      border: none;
      padding: 8px 16px;
      border-radius: 8px;
      font-size: 12px;
      font-weight: 700;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }
    .action-btn:hover { background: #14b8a6; }
    .close-btn {
      background: transparent;
      color: #94a3b8;
      border: 1px solid #334155;
      padding: 7px 14px;
      border-radius: 8px;
      font-size: 12px;
      cursor: pointer;
    }
    .close-btn:hover { color: #fff; background: #1e293b; }
    .header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      border-bottom: 2px solid #0d9488;
      padding-bottom: 16px;
      margin-bottom: 20px;
    }
    .badge {
      display: inline-block;
      background: #0f172a;
      color: #ffffff;
      padding: 3px 8px;
      border-radius: 6px;
      font-weight: 800;
      font-size: 11px;
      margin-right: 6px;
    }
    .brand-title {
      font-size: 22px;
      font-weight: 900;
      color: #0f172a;
      margin: 0;
      display: inline-block;
      vertical-align: middle;
    }
    .sub-title {
      font-size: 14px;
      font-weight: 700;
      color: #0f766e;
      margin: 6px 0 2px 0;
    }
    .meta-text {
      font-size: 11px;
      color: #64748b;
      margin: 0;
    }
    .kpi-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 12px;
      margin-bottom: 22px;
    }
    .kpi-card {
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 10px;
      padding: 12px 14px;
    }
    .kpi-label {
      font-size: 10px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: #64748b;
      margin-bottom: 4px;
      display: block;
    }
    .kpi-val {
      font-size: 17px;
      font-weight: 900;
      color: #0f172a;
    }
    .val-income { color: #059669; }
    .val-savings { color: #0d9488; }
    .table-container {
      margin-bottom: 24px;
    }
    .table-title {
      font-size: 12px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: #1e293b;
      margin-bottom: 8px;
      display: flex;
      justify-content: space-between;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 11px;
    }
    thead th {
      background: #f1f5f9;
      color: #334155;
      font-weight: 700;
      padding: 9px 12px;
      border-bottom: 2px solid #cbd5e1;
      text-align: left;
    }
    tbody tr:nth-child(even) {
      background: #f8fafc;
    }
    tbody td {
      border-bottom: 1px solid #e2e8f0;
    }
    .flag-box {
      background: #fff1f2;
      border: 1px solid #fecdd3;
      border-radius: 10px;
      padding: 12px 14px;
      margin-bottom: 22px;
    }
    .flag-title {
      color: #9f1239;
      font-weight: 800;
      font-size: 11px;
      margin-bottom: 8px;
    }
    .footer {
      border-top: 1px solid #cbd5e1;
      padding-top: 12px;
      margin-top: 30px;
      display: flex;
      justify-content: space-between;
      color: #64748b;
      font-size: 10px;
    }
    @media print {
      .no-print { display: none !important; }
      body { padding: 0 !important; }
      .header { border-bottom-color: #0f172a; }
      tr { break-inside: avoid; page-break-inside: avoid; }
    }
  </style>
</head>
<body>
  <div class="action-bar no-print">
    <div style="font-weight: 700; font-size: 13px;">
      📄 Statement: ${data.monthTitle} (DirhamTrack UAE)
    </div>
    <div style="display: flex; gap: 8px;">
      <button class="action-btn" onclick="window.print()">
        🖨️ Click to Print / Save PDF
      </button>
      <button class="close-btn" onclick="window.close()">
        Close
      </button>
    </div>
  </div>

  <div class="header">
    <div>
      <div>
        <span class="badge">د.إ AED</span>
        <h1 class="brand-title">DirhamTrack</h1>
      </div>
      <div class="sub-title">Monthly Financial &amp; Expense Statement — ${data.monthTitle}</div>
      <p class="meta-text">Statement Period: <strong>${data.monthPeriod}</strong></p>
    </div>
    <div style="text-align: right;">
      <div style="font-size: 9px; font-weight: 800; text-transform: uppercase; color: #64748b; letter-spacing: 0.5px;">Currency &amp; Region</div>
      <div style="font-size: 15px; font-weight: 900; color: #0d9488;">AED (United Arab Emirates)</div>
      <div style="font-size: 10px; color: #64748b; margin-top: 2px;">Generated: ${todayStr}</div>
      <div style="font-size: 10px; font-weight: 700; color: #059669; margin-top: 3px;">✓ Verified Personal Ledger</div>
    </div>
  </div>

  <div class="kpi-grid">
    <div class="kpi-card">
      <span class="kpi-label">Total Monthly Income</span>
      <span class="kpi-val val-income">AED ${data.totalIncome.toLocaleString('en-AE', { minimumFractionDigits: 2 })}</span>
    </div>
    <div class="kpi-card">
      <span class="kpi-label">Total Expenses</span>
      <span class="kpi-val">AED ${data.totalExpense.toLocaleString('en-AE', { minimumFractionDigits: 2 })}</span>
    </div>
    <div class="kpi-card">
      <span class="kpi-label">Net Monthly Savings</span>
      <span class="kpi-val val-savings">AED ${data.netSavings.toLocaleString('en-AE', { minimumFractionDigits: 2 })}</span>
    </div>
    <div class="kpi-card">
      <span class="kpi-label">Savings Rate</span>
      <span class="kpi-val">${data.savingsRate.toFixed(1)}%</span>
    </div>
  </div>

  <div class="table-container">
    <div class="table-title">
      <span>Spending by Category — ${data.monthTitle}</span>
      <span style="font-weight: 500; color: #64748b; font-size: 10px;">${data.budgets.length} Categories</span>
    </div>
    <table>
      <thead>
        <tr>
          <th>Category</th>
          <th style="text-align: right;">Actual Spent (AED)</th>
          <th style="text-align: right;">Budget Limit (AED)</th>
          <th style="text-align: right;">% of Total Spend</th>
        </tr>
      </thead>
      <tbody>
        ${categoryRows}
      </tbody>
    </table>
  </div>

  ${data.redFlags.length > 0 ? `
    <div class="flag-box">
      <div class="flag-title">⚠️ Security Audit: ${data.redFlags.length} Flagged / International Transaction(s)</div>
      ${redFlagRows}
    </div>
  ` : ''}

  <div class="table-container">
    <div class="table-title">
      <span>Transaction Ledger — ${data.monthTitle}</span>
      <span style="font-weight: 500; color: #64748b; font-size: 10px;">${data.transactions.length} Transactions</span>
    </div>
    ${data.transactions.length === 0 ? `
      <div style="padding: 20px; text-align: center; color: #64748b; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px;">
        No transactions recorded for ${data.monthTitle}.
      </div>
    ` : `
      <table>
        <thead>
          <tr>
            <th>Date</th>
            <th>Merchant</th>
            <th>Category</th>
            <th>Bank / Ledger Source</th>
            <th style="text-align: right;">Amount (AED)</th>
          </tr>
        </thead>
        <tbody>
          ${txRows}
        </tbody>
      </table>
    `}
  </div>

  <div class="footer">
    <div>DirhamTrack · Smart UAE Budget &amp; Bank Notification Interceptor · Confidential Statement</div>
    <div>Developed by <strong>Fakhruddin</strong></div>
  </div>
</body>
</html>`;
}

export function downloadStatementHTML(title: string, fullHtml: string): void {
  const safeTitle = title.replace(/\s+/g, '_');
  const filename = `DirhamTrack_Statement_${safeTitle}_${new Date().toISOString().split('T')[0]}.html`;
  const blob = new Blob([fullHtml], { type: 'text/html;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.setAttribute('href', url);
  link.setAttribute('download', filename);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export async function triggerPrintPDF(standaloneHtml?: string): Promise<{ success: boolean; error?: string }> {
  // Method 1: Use an isolated hidden iframe
  // This completely solves "taking back side screen also" because the iframe has NO backdrop, NO dark mode, NO dashboard
  try {
    const existing = document.getElementById('dirhamtrack-print-iframe');
    if (existing) {
      existing.remove();
    }

    const iframe = document.createElement('iframe');
    iframe.id = 'dirhamtrack-print-iframe';
    iframe.style.position = 'fixed';
    iframe.style.right = '0';
    iframe.style.bottom = '0';
    iframe.style.width = '0';
    iframe.style.height = '0';
    iframe.style.border = '0';
    iframe.style.opacity = '0';
    iframe.style.pointerEvents = 'none';
    document.body.appendChild(iframe);

    const frameDoc = iframe.contentDocument || iframe.contentWindow?.document;
    if (frameDoc && standaloneHtml) {
      frameDoc.open();
      frameDoc.write(standaloneHtml);
      frameDoc.close();

      await new Promise(r => setTimeout(r, 400));

      if (iframe.contentWindow) {
        iframe.contentWindow.focus();
        iframe.contentWindow.print();
        setTimeout(() => {
          iframe.remove();
        }, 5000);
        return { success: true };
      }
    }
  } catch (iframeErr) {
    console.warn('Iframe printing caught error, trying direct print:', iframeErr);
  }

  // Method 2: Direct window.print()
  try {
    window.focus();
    window.print();
    return { success: true };
  } catch (winErr) {
    console.error('Direct window.print() failed:', winErr);
    return { success: false, error: (winErr as Error).message };
  }
}
