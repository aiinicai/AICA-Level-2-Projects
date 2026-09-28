import * as XLSX from 'xlsx';
import { jsPDF } from 'jspdf';
import { 
  User, 
  Client, 
  DeliveryLog, 
  BillingClientSummary, 
  ConfirmationItem, 
  InvoiceItem, 
  AuditLogItem, 
  EmailLogItem,
  SystemSettings 
} from '../../types';

const STORAGE_KEYS = {
  CLIENTS: 'qb_clients_v2',
  DELIVERY_LOGS: 'qb_delivery_logs_v2',
  BILLINGS: 'qb_billings_v2',
  INVOICES: 'qb_invoices_v2',
  EMAILS: 'qb_emails_v2',
  AUDIT_LOGS: 'qb_audit_logs_v2',
  SETTINGS: 'qb_settings_v2',
  USERS: 'qb_users_v2',
};

// Seed Data
const DEFAULT_CLIENTS: Client[] = [
  {
    id: 'c-abc-001',
    clientCode: 'ABC001',
    name: 'ABC Limited',
    contactPerson: 'John Smith',
    email: 'casoumitrabanerjee2001@gmail.com',
    address: '100 Industrial Area, Sector 5, Bangalore - 560001',
    gstin: '29AABCU9603R1Z7',
    ratePerFile: 5.0,
    active: true,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
  {
    id: 'c-xyz-001',
    clientCode: 'XYZ001',
    name: 'XYZ Limited',
    contactPerson: 'Sarah Jenkins',
    email: 'soumitrabanerjeetraining@gmail.com',
    address: '22 Corporate Towers, Nariman Point, Mumbai - 400021',
    gstin: '27AABCT2301M1ZQ',
    ratePerFile: 7.0,
    active: true,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
  {
    id: 'c-gts-001',
    clientCode: 'GTS001',
    name: 'Global Tech Solutions',
    contactPerson: 'Rajesh Kumar',
    email: 'soumitrabanerjeetraining2026@gmail.com',
    address: '88 Cyber Park, Madhapur, Hyderabad - 500081',
    gstin: '36AABCG5542K1ZF',
    ratePerFile: 6.0,
    active: true,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
];

const DEFAULT_LOGS: DeliveryLog[] = [
  { id: 'del-1', clientId: 'c-abc-001', clientCode: 'ABC001', clientName: 'ABC Limited', month: 'April', quarter: 'Q1', financialYear: '2026-27', fileCount: 1200, amount: 6000, createdAt: new Date().toISOString() },
  { id: 'del-2', clientId: 'c-abc-001', clientCode: 'ABC001', clientName: 'ABC Limited', month: 'May', quarter: 'Q1', financialYear: '2026-27', fileCount: 1350, amount: 6750, createdAt: new Date().toISOString() },
  { id: 'del-3', clientId: 'c-abc-001', clientCode: 'ABC001', clientName: 'ABC Limited', month: 'June', quarter: 'Q1', financialYear: '2026-27', fileCount: 1500, amount: 7500, createdAt: new Date().toISOString() },
  { id: 'del-4', clientId: 'c-xyz-001', clientCode: 'XYZ001', clientName: 'XYZ Limited', month: 'April', quarter: 'Q1', financialYear: '2026-27', fileCount: 800, amount: 5600, createdAt: new Date().toISOString() },
  { id: 'del-5', clientId: 'c-xyz-001', clientCode: 'XYZ001', clientName: 'XYZ Limited', month: 'May', quarter: 'Q1', financialYear: '2026-27', fileCount: 900, amount: 6300, createdAt: new Date().toISOString() },
  { id: 'del-6', clientId: 'c-xyz-001', clientCode: 'XYZ001', clientName: 'XYZ Limited', month: 'June', quarter: 'Q1', financialYear: '2026-27', fileCount: 1100, amount: 7700, createdAt: new Date().toISOString() },
];

const DEFAULT_SETTINGS: SystemSettings = {
  companyName: 'FinTech Automated Solutions Pvt Ltd',
  companyAddress: '401 Cyber Towers, Hi-Tech City, Hyderabad - 500081',
  companyGstin: '36AAACF1234D1Z5',
  companyPan: 'AAACF1234D',
  companyEmail: 'soumitrabanerjee2001@gmail.com',
  companyPhone: '+91 98765 43210',
  defaultTaxRate: '18',
  currency: '₹',
  paymentTerms: '30 days',
  invoicePrefix: 'INV-',
  invoiceStartingNumber: '1',
  smtpHost: 'smtp.gmail.com',
  smtpPort: '587',
  smtpUser: 'soumitrabanerjee2001@gmail.com',
  smtpPass: 'demo-smtp-pass',
  senderEmail: 'soumitrabanerjee2001@gmail.com',
  demoMode: 'true',
  reminderIntervalDays: '5',
  adminPassword: 'admin123',
  userPassword: 'demo123',
};

const DEFAULT_AUDIT: AuditLogItem[] = [
  {
    id: 'aud-init-1',
    action: 'SYSTEM_INITIALIZATION',
    entity: 'System',
    entityId: 'ALL',
    description: 'Initial demo client accounts and Q1 delivery logs seeded',
    createdAt: new Date().toISOString(),
  },
];

// Helper storage functions
function getStored<T>(key: string, defaultVal: T): T {
  try {
    const item = localStorage.getItem(key);
    return item ? JSON.parse(item) : defaultVal;
  } catch (e) {
    return defaultVal;
  }
}

function setStored<T>(key: string, val: T): void {
  try {
    localStorage.setItem(key, JSON.stringify(val));
  } catch (e) {
    console.error('Storage quota exceeded:', e);
  }
}

export class SystemService {
  private static instance: SystemService;

  private constructor() {
    this.init();
  }

  public static getInstance(): SystemService {
    if (!SystemService.instance) {
      SystemService.instance = new SystemService();
    }
    return SystemService.instance;
  }

  private init() {
    if (!localStorage.getItem(STORAGE_KEYS.CLIENTS)) {
      setStored(STORAGE_KEYS.CLIENTS, DEFAULT_CLIENTS);
    }
    if (!localStorage.getItem(STORAGE_KEYS.DELIVERY_LOGS)) {
      setStored(STORAGE_KEYS.DELIVERY_LOGS, DEFAULT_LOGS);
    }
    if (!localStorage.getItem(STORAGE_KEYS.SETTINGS)) {
      setStored(STORAGE_KEYS.SETTINGS, DEFAULT_SETTINGS);
    }
    if (!localStorage.getItem(STORAGE_KEYS.AUDIT_LOGS)) {
      setStored(STORAGE_KEYS.AUDIT_LOGS, DEFAULT_AUDIT);
    }
    if (!localStorage.getItem(STORAGE_KEYS.INVOICES)) {
      setStored(STORAGE_KEYS.INVOICES, []);
    }
    if (!localStorage.getItem(STORAGE_KEYS.EMAILS)) {
      setStored(STORAGE_KEYS.EMAILS, []);
    }
    if (!localStorage.getItem(STORAGE_KEYS.BILLINGS)) {
      setStored(STORAGE_KEYS.BILLINGS, []);
      // Auto-compute Q1 billing
      this.calculateQuarterlyBilling('Q1', '2026-27');
    }
  }

  // --- Audit Logging ---
  public logAudit(action: string, entity: string, entityId: string, description: string) {
    const logs = getStored<AuditLogItem[]>(STORAGE_KEYS.AUDIT_LOGS, []);
    const newLog: AuditLogItem = {
      id: 'aud-' + Date.now() + '-' + Math.random().toString(36).substring(2, 6),
      action,
      entity,
      entityId: entityId || 'N/A',
      description,
      createdAt: new Date().toISOString(),
    };
    logs.unshift(newLog);
    setStored(STORAGE_KEYS.AUDIT_LOGS, logs);
    return newLog;
  }

  public getAuditLogs(filters?: { client?: string; action?: string; date?: string }): AuditLogItem[] {
    let logs = getStored<AuditLogItem[]>(STORAGE_KEYS.AUDIT_LOGS, []);
    if (filters?.action && filters.action !== 'ALL') {
      logs = logs.filter((l) => l.action === filters.action);
    }
    if (filters?.client) {
      const q = filters.client.toLowerCase();
      logs = logs.filter((l) => l.description.toLowerCase().includes(q) || l.entityId.toLowerCase().includes(q));
    }
    if (filters?.date) {
      logs = logs.filter((l) => l.createdAt.startsWith(filters.date!));
    }
    return logs;
  }

  // Exports the Audit Trail as an .xlsx workbook. Takes the list to export
  // (the Audit Trail screen passes its currently-filtered logs, so a
  // downloaded report matches whatever the user has filtered/searched to)
  // rather than always re-reading the full unfiltered log from storage.
  public downloadAuditTrailExcel(logs: AuditLogItem[]) {
    const data = logs.map((log) => {
      const dateObj = new Date(log.createdAt);
      return {
        'Date': dateObj.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }),
        'Time': dateObj.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
        'Action': log.action,
        'Entity': log.entity,
        'Entity ID': log.entityId,
        'Description': log.description,
      };
    });

    const ws = XLSX.utils.json_to_sheet(data);
    // Widen columns roughly to fit typical content so the report is
    // readable as soon as it's opened, rather than every column at the
    // default narrow width.
    ws['!cols'] = [
      { wch: 12 }, // Date
      { wch: 10 }, // Time
      { wch: 28 }, // Action
      { wch: 14 }, // Entity
      { wch: 22 }, // Entity ID
      { wch: 80 }, // Description
    ];

    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Audit Trail');

    const stamp = new Date().toISOString().slice(0, 10);
    XLSX.writeFile(wb, `Audit_Trail_Report_${stamp}.xlsx`);

    this.logAudit(
      'AUDIT_TRAIL_EXPORTED',
      'AuditLog',
      `${logs.length} records`,
      `Audit Trail report exported to Excel (${logs.length} records).`
    );
  }

  // --- Clients ---
  public getClients(): Client[] {
    return getStored<Client[]>(STORAGE_KEYS.CLIENTS, []);
  }

  public addClient(clientData: Omit<Client, 'id' | 'createdAt' | 'updatedAt' | 'active'>): Client {
    const clients = this.getClients();
    const existing = clients.find((c) => c.clientCode.toUpperCase() === clientData.clientCode.toUpperCase());
    if (existing) {
      throw new Error(`Client code ${clientData.clientCode} already exists.`);
    }

    const now = new Date().toISOString();
    const newClient: Client = {
      ...clientData,
      id: 'c-' + Date.now(),
      clientCode: clientData.clientCode.toUpperCase(),
      active: true,
      createdAt: now,
      updatedAt: now,
    };

    clients.push(newClient);
    setStored(STORAGE_KEYS.CLIENTS, clients);
    this.logAudit('CLIENT_CREATED', 'Client', newClient.id, `Created client ${newClient.name} (${newClient.clientCode})`);
    return newClient;
  }

  public updateClient(id: string, updates: Partial<Client>): Client {
    const clients = this.getClients();
    const idx = clients.findIndex((c) => c.id === id);
    if (idx === -1) throw new Error('Client not found');

    const updated = {
      ...clients[idx],
      ...updates,
      updatedAt: new Date().toISOString(),
    };
    clients[idx] = updated;
    setStored(STORAGE_KEYS.CLIENTS, clients);
    this.logAudit('CLIENT_UPDATED', 'Client', id, `Updated client ${updated.name}`);
    return updated;
  }

  public toggleClientActive(id: string): Client {
    const clients = this.getClients();
    const client = clients.find((c) => c.id === id);
    if (!client) throw new Error('Client not found');

    client.active = !client.active;
    client.updatedAt = new Date().toISOString();
    setStored(STORAGE_KEYS.CLIENTS, clients);

    this.logAudit(
      client.active ? 'CLIENT_ACTIVATED' : 'CLIENT_DEACTIVATED',
      'Client',
      id,
      `${client.active ? 'Activated' : 'Deactivated'} client ${client.name}`
    );
    return client;
  }

  // --- Delivery Logs ---
  public getDeliveryLogs(): DeliveryLog[] {
    return getStored<DeliveryLog[]>(STORAGE_KEYS.DELIVERY_LOGS, []);
  }

  public async validateExcel(file: File): Promise<{
    valid: boolean;
    totalRows: number;
    validRows: Array<{
      clientCode: string;
      clientId: string;
      clientName: string;
      month: string;
      quarter: string;
      financialYear: string;
      fileCount: number;
      amount: number;
    }>;
    errors: Array<{ rowNumber: number; clientCode?: string; field: string; message: string }>;
  }> {
    const buffer = await file.arrayBuffer();
    const workbook = XLSX.read(buffer, { type: 'array' });
    const sheetName = workbook.SheetNames[0];
    if (!sheetName) {
      return { valid: false, totalRows: 0, validRows: [], errors: [{ rowNumber: 0, field: 'file', message: 'No sheet found' }] };
    }

    const worksheet = workbook.Sheets[sheetName];
    const rawRows: any[] = XLSX.utils.sheet_to_json(worksheet, { defval: '' });

    const clients = this.getClients();
    const clientMap = new Map(clients.map((c) => [c.clientCode.toUpperCase(), c]));

    const errors: Array<{ rowNumber: number; clientCode?: string; field: string; message: string }> = [];
    const validRows: any[] = [];
    const seenKeys = new Set<string>();

    const monthMap: Record<string, string> = {
      april: 'Q1', may: 'Q1', june: 'Q1',
      july: 'Q2', august: 'Q2', september: 'Q2',
      october: 'Q3', november: 'Q3', december: 'Q3',
      january: 'Q4', february: 'Q4', march: 'Q4'
    };

    rawRows.forEach((row, i) => {
      const rowNum = i + 2;
      const getVal = (keys: string[]) => {
        for (const k of Object.keys(row)) {
          const clean = k.trim().toLowerCase().replace(/[^a-z]/g, '');
          for (const cand of keys) {
            if (clean === cand.toLowerCase().replace(/[^a-z]/g, '')) return row[k];
          }
        }
        return undefined;
      };

      const codeRaw = getVal(['clientcode', 'code', 'client code']);
      const monthRaw = getVal(['month']);
      const countRaw = getVal(['filecount', 'files', 'file count', 'count']);
      const amountRaw = getVal(['amount', 'total amount']);

      if (!codeRaw) {
        errors.push({ rowNumber: rowNum, field: 'Client Code', message: 'Client Code is required.' });
        return;
      }

      const clientCode = String(codeRaw).trim().toUpperCase();
      const client = clientMap.get(clientCode);
      if (!client) {
        errors.push({ rowNumber: rowNum, clientCode, field: 'Client Code', message: `Client ${clientCode} not found in master records.` });
        return;
      }

      if (!client.active) {
        errors.push({ rowNumber: rowNum, clientCode, field: 'Client Status', message: `Client ${clientCode} (${client.name}) is deactivated.` });
        return;
      }

      const monthNorm = String(monthRaw).trim().toLowerCase();
      let matchedMonth: string | null = null;
      let matchedQuarter = 'Q1';

      for (const [mName, qName] of Object.entries(monthMap)) {
        if (mName.startsWith(monthNorm) || monthNorm.startsWith(mName.slice(0, 3))) {
          matchedMonth = mName.charAt(0).toUpperCase() + mName.slice(1);
          matchedQuarter = qName;
          break;
        }
      }

      if (!matchedMonth) {
        errors.push({ rowNumber: rowNum, clientCode, field: 'Month', message: `Invalid month: "${monthRaw}".` });
        return;
      }

      const fileCount = Number(countRaw);
      if (isNaN(fileCount) || fileCount <= 0) {
        errors.push({ rowNumber: rowNum, clientCode, field: 'File Count', message: 'File Count must be a positive number.' });
        return;
      }

      let amount = Number(amountRaw);
      if (isNaN(amount) || amount <= 0) {
        amount = fileCount * client.ratePerFile;
      }

      const dupKey = `${clientCode}-${matchedMonth}-2026-27`;
      if (seenKeys.has(dupKey)) {
        errors.push({ rowNumber: rowNum, clientCode, field: 'Duplicate', message: `Duplicate record for ${clientCode} and ${matchedMonth}.` });
        return;
      }
      seenKeys.add(dupKey);

      validRows.push({
        clientCode,
        clientId: client.id,
        clientName: client.name,
        month: matchedMonth,
        quarter: matchedQuarter,
        financialYear: '2026-27',
        fileCount,
        amount,
      });
    });

    this.logAudit('DELIVERY_LOG_UPLOADED', 'File', file.name, `Delivery log ${file.name} uploaded for validation (${validRows.length} valid, ${errors.length} errors)`);

    return {
      valid: errors.length === 0,
      totalRows: rawRows.length,
      validRows,
      errors,
    };
  }

  public importDeliveryRecords(records: any[]): { importedCount: number } {
    const logs = this.getDeliveryLogs();
    let imported = 0;
    const now = new Date().toISOString();

    for (const rec of records) {
      const existIdx = logs.findIndex(
        (l) => l.clientId === rec.clientId && l.month === rec.month && l.financialYear === rec.financialYear
      );

      if (existIdx >= 0) {
        logs[existIdx].fileCount = rec.fileCount;
        logs[existIdx].amount = rec.amount;
      } else {
        logs.unshift({
          id: 'del-' + Date.now() + '-' + Math.random().toString(36).substring(2, 6),
          clientId: rec.clientId,
          clientCode: rec.clientCode,
          clientName: rec.clientName,
          month: rec.month,
          quarter: rec.quarter,
          financialYear: rec.financialYear,
          fileCount: rec.fileCount,
          amount: rec.amount,
          createdAt: now,
        });
      }
      imported++;
    }

    setStored(STORAGE_KEYS.DELIVERY_LOGS, logs);
    this.logAudit('DELIVERY_LOG_IMPORTED', 'DeliveryLog', `${imported} records`, `Imported ${imported} delivery log records into database.`);
    return { importedCount: imported };
  }

  public downloadSampleTemplate() {
    const data = [
      { 'Client Code': 'ABC001', 'Client Name': 'ABC Limited', 'Month': 'April', 'File Count': 1200, 'Amount': 6000 },
      { 'Client Code': 'ABC001', 'Client Name': 'ABC Limited', 'Month': 'May', 'File Count': 1350, 'Amount': 6750 },
      { 'Client Code': 'ABC001', 'Client Name': 'ABC Limited', 'Month': 'June', 'File Count': 1500, 'Amount': 7500 },
      { 'Client Code': 'XYZ001', 'Client Name': 'XYZ Limited', 'Month': 'April', 'File Count': 900, 'Amount': 6300 },
      { 'Client Code': 'XYZ001', 'Client Name': 'XYZ Limited', 'Month': 'May', 'File Count': 950, 'Amount': 6650 },
      { 'Client Code': 'XYZ001', 'Client Name': 'XYZ Limited', 'Month': 'June', 'File Count': 1000, 'Amount': 7000 },
      { 'Client Code': 'GTS001', 'Client Name': 'Global Tech Solutions', 'Month': 'April', 'File Count': 650, 'Amount': 3900 },
      { 'Client Code': 'GTS001', 'Client Name': 'Global Tech Solutions', 'Month': 'May', 'File Count': 720, 'Amount': 4320 },
      { 'Client Code': 'GTS001', 'Client Name': 'Global Tech Solutions', 'Month': 'June', 'File Count': 850, 'Amount': 5100 },
    ];

    const ws = XLSX.utils.json_to_sheet(data);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'DeliveryLogs');
    XLSX.writeFile(wb, 'Delivery_Log_Sample.xlsx');
  }

  // --- Billing Calculation ---
  public calculateQuarterlyBilling(quarter: string, financialYear: string) {
    const clients = this.getClients().filter((c) => c.active);
    const logs = this.getDeliveryLogs().filter(
      (l) => l.quarter === quarter && l.financialYear === financialYear
    );
    const settings = this.getSettings();
    const taxRate = parseFloat(settings.defaultTaxRate) || 18;

    let billings = getStored<ConfirmationItem[]>(STORAGE_KEYS.BILLINGS, []);
    const summaries: BillingClientSummary[] = [];
    let totalFiles = 0;
    let totalBilling = 0;
    const now = new Date().toISOString();

    for (const client of clients) {
      const clientLogs = logs.filter((l) => l.clientId === client.id);
      if (clientLogs.length === 0) continue;

      const months: Record<string, number> = {};
      let clientTotalFiles = 0;

      for (const log of clientLogs) {
        months[log.month] = (months[log.month] || 0) + log.fileCount;
        clientTotalFiles += log.fileCount;
      }

      const subtotal = clientTotalFiles * client.ratePerFile;
      const tax = Math.round(subtotal * (taxRate / 100) * 100) / 100;
      const totalAmount = Math.round((subtotal + tax) * 100) / 100;

      totalFiles += clientTotalFiles;
      totalBilling += totalAmount;

      // Find or create billing record
      let existingBilling = billings.find(
        (b) => b.clientId === client.id && b.quarter === quarter && b.financialYear === financialYear
      );

      if (existingBilling) {
        if (existingBilling.status === 'PENDING_CONFIRMATION') {
          existingBilling.totalFileCount = clientTotalFiles;
          existingBilling.ratePerFile = client.ratePerFile;
          existingBilling.subtotal = subtotal;
          existingBilling.tax = tax;
          existingBilling.totalAmount = totalAmount;
          existingBilling.updatedAt = now;
        }
      } else {
        existingBilling = {
          id: 'bill-' + Date.now() + '-' + Math.random().toString(36).substring(2, 6),
          clientId: client.id,
          clientName: client.name,
          clientCode: client.clientCode,
          clientEmail: client.email,
          quarter,
          financialYear,
          totalFileCount: clientTotalFiles,
          ratePerFile: client.ratePerFile,
          subtotal,
          tax,
          totalAmount,
          status: 'PENDING_CONFIRMATION',
          createdAt: now,
          updatedAt: now,
        };
        billings.push(existingBilling);
      }

      summaries.push({
        billingId: existingBilling.id,
        clientId: client.id,
        clientCode: client.clientCode,
        clientName: client.name,
        ratePerFile: client.ratePerFile,
        months,
        totalFileCount: clientTotalFiles,
        subtotal,
        tax,
        totalAmount,
        status: existingBilling.status,
      });
    }

    setStored(STORAGE_KEYS.BILLINGS, billings);
    this.logAudit(
      'BILLING_CALCULATED',
      'Billing',
      `${quarter} FY ${financialYear}`,
      `Calculated quarterly billing for ${summaries.length} clients (${totalFiles.toLocaleString('en-IN')} total files, ₹${totalBilling.toLocaleString('en-IN')})`
    );

    return { summaries, totalFiles, totalBilling };
  }

  public getQuarterlyBilling(quarter: string, financialYear: string) {
    return this.calculateQuarterlyBilling(quarter, financialYear);
  }

  // --- Real Mail Dispatch ---
  // Posts to the local mail server (server/index.mjs, proxied through Vite at
  // /api) which actually sends via Nodemailer/SMTP. When demoMode is 'true'
  // (the default) we skip the network call entirely and just simulate, exactly
  // like the original prototype behaviour.
  private async dispatchEmail(payload: {
    to: string;
    subject: string;
    body: string;
    attachment?: { filename: string; content: string };
  }): Promise<'SENT' | 'SIMULATED' | 'FAILED'> {
    const settings = this.getSettings();
    if (settings.demoMode === 'true') {
      return 'SIMULATED';
    }

    try {
      const response = await fetch('/api/send-email', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...payload, companyName: settings.companyName }),
      });
      const data = await response.json().catch(() => ({ success: false }));
      if (response.ok && data.success) {
        return data.status === 'SIMULATED' ? 'SIMULATED' : 'SENT';
      }
      return 'FAILED';
    } catch (e) {
      // Mail server unreachable (e.g. `npm run server` isn't running) -
      // fail soft so the rest of the workflow (invoice generation, audit
      // log, etc.) still completes.
      return 'FAILED';
    }
  }

  // --- Confirmation Emails ---
  public async sendConfirmationEmail(billingId: string) {
    const billings = getStored<ConfirmationItem[]>(STORAGE_KEYS.BILLINGS, []);
    const billing = billings.find((b) => b.id === billingId);
    if (!billing) throw new Error('Billing record not found');

    const logs = this.getDeliveryLogs().filter(
      (l) => l.clientId === billing.clientId && l.quarter === billing.quarter && l.financialYear === billing.financialYear
    );

    const breakdownText = logs
      .map((l) => `${l.month}: ${l.fileCount.toLocaleString('en-IN')} files`)
      .join('\n');

    const subject = `Quarterly Billing Confirmation – ${billing.clientName} – ${billing.quarter} FY ${billing.financialYear}`;
    const body = `Dear ${billing.clientName},

Please review the following quarterly file processing details:

${breakdownText || 'Monthly processing details attached'}

Total Files: ${billing.totalFileCount.toLocaleString('en-IN')}

Rate per File: ₹${billing.ratePerFile}

Subtotal: ₹${billing.subtotal.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
Tax: ₹${billing.tax.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
Total Amount: ₹${billing.totalAmount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}

Please confirm the above details by replying to this email with:

CONFIRMED

Regards,
Finance Team`;

    const status = await this.dispatchEmail({ to: billing.clientEmail, subject, body });

    this.recordEmail({
      clientId: billing.clientId,
      clientName: billing.clientName,
      clientCode: billing.clientCode,
      billingId: billing.id,
      type: 'CONFIRMATION',
      recipient: billing.clientEmail,
      subject,
      body,
      status,
    });

    this.logAudit(
      'CONFIRMATION_EMAIL_SENT',
      'Client',
      billing.clientId,
      `Confirmation email ${status === 'SENT' ? 'sent' : status === 'FAILED' ? 'failed to send' : 'simulated'} to ${billing.clientName} (${billing.clientEmail}) for ${billing.quarter} FY ${billing.financialYear}`
    );

    return { success: status !== 'FAILED', status };
  }

  // --- Confirmations & Invoice Generation ---
  public getConfirmations(): ConfirmationItem[] {
    return getStored<ConfirmationItem[]>(STORAGE_KEYS.BILLINGS, []);
  }

  public async simulateConfirmation(billingId: string): Promise<{
    success: boolean;
    invoiceNumber: string;
    pdfPath: string;
  }> {
    const billings = getStored<ConfirmationItem[]>(STORAGE_KEYS.BILLINGS, []);
    const billing = billings.find((b) => b.id === billingId);
    if (!billing) throw new Error('Billing record not found');

    const now = new Date().toISOString();
    billing.status = 'CONFIRMED';
    billing.updatedAt = now;

    this.logAudit(
      'CLIENT_CONFIRMATION_RECEIVED',
      'Billing',
      billingId,
      `Client confirmation simulated for ${billing.clientName} (${billing.quarter} FY ${billing.financialYear})`
    );

    // Generate Invoice
    const invoices = getStored<InvoiceItem[]>(STORAGE_KEYS.INVOICES, []);
    const count = invoices.length + 1;
    const invNum = `INV-2026-${count.toString().padStart(4, '0')}`;

    const newInvoice: InvoiceItem = {
      id: 'inv-' + Date.now(),
      billingId: billing.id,
      invoiceNumber: invNum,
      invoiceDate: now,
      clientId: billing.clientId,
      clientCode: billing.clientCode,
      clientName: billing.clientName,
      clientEmail: billing.clientEmail,
      quarter: billing.quarter,
      financialYear: billing.financialYear,
      totalFileCount: billing.totalFileCount,
      ratePerFile: billing.ratePerFile,
      subtotal: billing.subtotal,
      tax: billing.tax,
      totalAmount: billing.totalAmount,
      pdfPath: '#',
      status: 'SENT',
      createdAt: now,
    };

    invoices.unshift(newInvoice);
    setStored(STORAGE_KEYS.INVOICES, invoices);

    billing.status = 'INVOICE_SENT';
    billing.invoiceNumber = invNum;
    billing.invoiceId = newInvoice.id;
    setStored(STORAGE_KEYS.BILLINGS, billings);

    this.logAudit('INVOICE_GENERATED', 'Invoice', invNum, `Invoice ${invNum} generated for ${billing.clientName}`);

    // Send Invoice Email
    const subject = `Invoice ${invNum} – ${billing.clientName}`;
    const body = `Dear ${billing.clientName},

Please find attached invoice ${invNum} for quarterly file processing services for ${billing.quarter} FY ${billing.financialYear}.

Invoice Amount: ₹${billing.totalAmount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}

Please arrange payment as per the agreed payment terms.

Regards,
Finance Team`;

    const pdfBase64 = this.getInvoicePdfBase64(newInvoice);
    const emailStatus = await this.dispatchEmail({
      to: billing.clientEmail,
      subject,
      body,
      attachment: { filename: `${invNum}.pdf`, content: pdfBase64 },
    });

    this.recordEmail({
      clientId: billing.clientId,
      clientName: billing.clientName,
      clientCode: billing.clientCode,
      billingId: billing.id,
      type: 'INVOICE',
      recipient: billing.clientEmail,
      subject,
      body,
      status: emailStatus,
    });

    this.logAudit(
      'INVOICE_EMAIL_SENT',
      'Invoice',
      invNum,
      `Invoice ${invNum} ${emailStatus === 'SENT' ? 'emailed' : emailStatus === 'FAILED' ? 'email failed to dispatch' : 'email simulated'} to ${billing.clientName} (${billing.clientEmail})`
    );

    return {
      success: true,
      invoiceNumber: invNum,
      pdfPath: '#',
    };
  }

  // Re-sends the invoice email (with the PDF re-attached) for a billing
  // record that has already been invoiced - e.g. the client says they never
  // received it, or an earlier send failed/was misrouted. This does NOT
  // regenerate the invoice or bump the invoice number; it just re-dispatches
  // the existing invoice to the client and logs a fresh audit trail entry so
  // the resend itself is traceable, separately from the original send.
  public async resendInvoiceEmail(billingId: string): Promise<{
    success: boolean;
    status: 'SENT' | 'SIMULATED' | 'FAILED';
    invoiceNumber: string;
  }> {
    const billings = getStored<ConfirmationItem[]>(STORAGE_KEYS.BILLINGS, []);
    const billing = billings.find((b) => b.id === billingId);
    if (!billing) throw new Error('Billing record not found');

    const invoices = getStored<InvoiceItem[]>(STORAGE_KEYS.INVOICES, []);
    const invoice =
      invoices.find((i) => i.id === billing.invoiceId) || invoices.find((i) => i.billingId === billing.id);
    if (!invoice) throw new Error('No invoice found for this billing record yet.');

    const subject = `Invoice ${invoice.invoiceNumber} – ${billing.clientName} (Resent)`;
    const body = `Dear ${billing.clientName},

Please find re-attached invoice ${invoice.invoiceNumber} for quarterly file processing services for ${invoice.quarter} FY ${invoice.financialYear}.

Invoice Amount: ₹${invoice.totalAmount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}

Please arrange payment as per the agreed payment terms. This is a resend of a previously dispatched invoice.

Regards,
Finance Team`;

    const pdfBase64 = this.getInvoicePdfBase64(invoice);
    const status = await this.dispatchEmail({
      to: billing.clientEmail,
      subject,
      body,
      attachment: { filename: `${invoice.invoiceNumber}.pdf`, content: pdfBase64 },
    });

    this.recordEmail({
      clientId: billing.clientId,
      clientName: billing.clientName,
      clientCode: billing.clientCode,
      billingId: billing.id,
      type: 'INVOICE',
      recipient: billing.clientEmail,
      subject,
      body,
      status,
    });

    this.logAudit(
      'INVOICE_EMAIL_RESENT',
      'Invoice',
      invoice.invoiceNumber,
      `Invoice ${invoice.invoiceNumber} ${status === 'SENT' ? 're-emailed' : status === 'FAILED' ? 'resend failed to dispatch' : 'resend simulated'} to ${billing.clientName} (${billing.clientEmail})`
    );

    return { success: status !== 'FAILED', status, invoiceNumber: invoice.invoiceNumber };
  }

  public rejectConfirmation(billingId: string, reason?: string) {
    const billings = getStored<ConfirmationItem[]>(STORAGE_KEYS.BILLINGS, []);
    const billing = billings.find((b) => b.id === billingId);
    if (!billing) throw new Error('Billing record not found');

    billing.status = 'REJECTED';
    billing.updatedAt = new Date().toISOString();
    setStored(STORAGE_KEYS.BILLINGS, billings);

    this.logAudit(
      'CLIENT_CONFIRMATION_REJECTED',
      'Billing',
      billingId,
      `Billing marked as rejected by client. Reason: ${reason || 'Count discrepancy'}`
    );
    return { success: true };
  }

  // --- Real Inbox Reply Detection ---
  // Asks the backend to check the real mailbox (IMAP) for unseen replies
  // from clients that are still PENDING_CONFIRMATION, and looks for an
  // actual "CONFIRMED" / "REJECTED" reply. When found, drives the exact
  // same automation the manual "Simulate Client Confirmation" button does
  // (invoice generation + dispatch, or rejection), so a real email reply
  // now triggers the workflow instead of only a manual click.
  public async checkForReplies(): Promise<{
    checked: boolean;
    reason?: string;
    confirmedClients: string[];
    rejectedClients: string[];
  }> {
    const settings = this.getSettings();
    if (settings.demoMode === 'true') {
      return { checked: false, reason: 'Demo Mode is on', confirmedClients: [], rejectedClients: [] };
    }

    const pendingBillings = this.getConfirmations().filter((c) => c.status === 'PENDING_CONFIRMATION');
    if (pendingBillings.length === 0) {
      return { checked: true, confirmedClients: [], rejectedClients: [] };
    }

    // Correlate each pending billing to the moment ITS confirmation-request
    // email actually went out. Without this, the IMAP search below (which
    // matches purely on "unseen mail from this client address") can pick up
    // an old/stale unseen message from an earlier test or a different
    // billing cycle and misattribute it as the reply for whichever billing
    // happens to be pending right now for that same address - e.g. a client
    // that has both an old leftover unseen email AND a new pending billing.
    // Using the latest CONFIRMATION email's sentAt as a "since" cutoff means
    // only replies that could plausibly be responding to THIS specific
    // confirmation request are ever considered.
    const emails = this.getEmails();
    const pending = pendingBillings.map((b) => {
      const confirmationEmails = emails
        .filter((e) => e.billingId === b.id && e.type === 'CONFIRMATION')
        .sort((a, c) => new Date(c.sentAt).getTime() - new Date(a.sentAt).getTime());
      const since = confirmationEmails[0]?.sentAt || b.createdAt || b.updatedAt;
      return { billingId: b.id, clientEmail: b.clientEmail, since };
    });

    try {
      const response = await fetch('/api/check-confirmations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pending }),
      });
      const data = await response.json().catch(() => null);
      if (!response.ok || !data || !data.checked) {
        return { checked: false, reason: data?.reason || 'Could not reach mail server.', confirmedClients: [], rejectedClients: [] };
      }

      const confirmedClients: string[] = [];
      const rejectedClients: string[] = [];

      for (const billingId of data.confirmed || []) {
        const billing = pendingBillings.find((b) => b.id === billingId);
        try {
          await this.simulateConfirmation(billingId);
          if (billing) confirmedClients.push(billing.clientName);
        } catch {
          // Billing may have already been processed by a concurrent check - ignore.
        }
      }

      for (const item of data.rejected || []) {
        const billing = pendingBillings.find((b) => b.id === item.billingId);
        try {
          this.rejectConfirmation(item.billingId, `[Auto-detected from email reply] ${item.reason}`);
          if (billing) rejectedClients.push(billing.clientName);
        } catch {
          // Already processed - ignore.
        }
      }

      return { checked: true, confirmedClients, rejectedClients };
    } catch (e) {
      return { checked: false, reason: 'Mail server unreachable.', confirmedClients: [], rejectedClients: [] };
    }
  }

  // --- Automated Follow-Up Reminders ---
  // Sends a follow-up reminder email to any client still PENDING_CONFIRMATION
  // once "reminderIntervalDays" (Settings, default 5) days have passed since
  // the last outbound email to them about that specific billing record - the
  // original confirmation request, or an earlier reminder - so a client who
  // never replies keeps getting nudged every N days until they confirm,
  // reject, or the billing record is otherwise resolved (at which point it's
  // no longer PENDING_CONFIRMATION and reminders stop on their own).
  //
  // This runs whenever it's called (App.tsx calls it on an interval while
  // the app is open, and there's also a manual "Send Reminders Now" button),
  // NOT on a real server-side schedule - the app's data lives in the
  // browser's localStorage, not a shared backend database, so reminders can
  // only fire while this browser tab has the app open. Each call is cheap
  // and safe to call often: it only actually sends anything for billings
  // whose interval has genuinely elapsed.
  public async checkAndSendReminders(): Promise<{ sentClients: string[] }> {
    const settings = this.getSettings();
    const intervalDays = parseFloat(settings.reminderIntervalDays) || 5;
    const intervalMs = intervalDays * 24 * 60 * 60 * 1000;

    const pendingBillings = this.getConfirmations().filter((c) => c.status === 'PENDING_CONFIRMATION');
    if (pendingBillings.length === 0) {
      return { sentClients: [] };
    }

    const emails = this.getEmails();
    const now = Date.now();
    const sentClients: string[] = [];

    for (const billing of pendingBillings) {
      // The clock for "days of silence" is measured from the most recent
      // outbound CONFIRMATION or REMINDER email for THIS billing record -
      // never a broad per-client lookup, so two different quarters pending
      // for the same client are tracked independently.
      const related = emails
        .filter((e) => e.billingId === billing.id && (e.type === 'CONFIRMATION' || e.type === 'REMINDER'))
        .sort((a, b) => new Date(b.sentAt).getTime() - new Date(a.sentAt).getTime());
      const lastSentAt = related[0]?.sentAt;
      if (!lastSentAt) continue; // No confirmation email on record yet - nothing to remind about.

      const elapsed = now - new Date(lastSentAt).getTime();
      if (elapsed < intervalMs) continue;

      const reminderNumber = emails.filter((e) => e.billingId === billing.id && e.type === 'REMINDER').length + 1;

      const subject = `Reminder ${reminderNumber}: Quarterly Billing Confirmation Pending – ${billing.clientName} – ${billing.quarter} FY ${billing.financialYear}`;
      const body = `Dear ${billing.clientName},

This is a follow-up reminder (#${reminderNumber}) regarding the quarterly billing confirmation request sent to you earlier for ${billing.quarter} FY ${billing.financialYear}, which is still awaiting your response.

Total Files: ${billing.totalFileCount.toLocaleString('en-IN')}
Total Amount: ₹${billing.totalAmount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}

Please confirm the above details at your earliest convenience by replying to this email with:

CONFIRMED

If there is any discrepancy, please let us know the details in your reply so we can review it.

Regards,
Finance Team`;

      const status = await this.dispatchEmail({ to: billing.clientEmail, subject, body });

      this.recordEmail({
        clientId: billing.clientId,
        clientName: billing.clientName,
        clientCode: billing.clientCode,
        billingId: billing.id,
        type: 'REMINDER',
        recipient: billing.clientEmail,
        subject,
        body,
        status,
      });

      this.logAudit(
        'CONFIRMATION_REMINDER_SENT',
        'Billing',
        billing.id,
        `Reminder #${reminderNumber} (${intervalDays}-day follow-up) ${status === 'SENT' ? 'emailed' : status === 'FAILED' ? 'failed to send' : 'simulated'} to ${billing.clientName} (${billing.clientEmail}) for ${billing.quarter} FY ${billing.financialYear}`
      );

      if (status !== 'FAILED') sentClients.push(billing.clientName);
    }

    return { sentClients };
  }

  // --- PDF Generator using jsPDF ---
  // Builds the invoice PDF document. Shared by downloadInvoicePdf (browser
  // download) and getInvoicePdfBase64 (email attachment) so both stay
  // pixel-identical instead of drifting into two copies of the same layout.
  private buildInvoicePdfDoc(invoice: InvoiceItem): jsPDF {
    const doc = new jsPDF({ unit: 'pt', format: 'a4' });
    const settings = this.getSettings();

    // Deep blue brand header
    doc.setFillColor(30, 58, 138);
    doc.rect(0, 0, 595, 20, 'F');

    // Company Header
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(18);
    doc.setTextColor(30, 58, 138);
    doc.text(settings.companyName, 40, 55);

    doc.setFont('helvetica', 'normal');
    doc.setFontSize(9);
    doc.setTextColor(100, 116, 139);
    doc.text(settings.companyAddress, 40, 70);
    doc.text(`GSTIN: ${settings.companyGstin} | PAN: ${settings.companyPan}`, 40, 83);

    // Invoice Title
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(22);
    doc.setTextColor(15, 23, 42);
    doc.text('TAX INVOICE', 555, 55, { align: 'right' });

    doc.setFontSize(10);
    doc.setTextColor(30, 58, 138);
    doc.text(`Invoice No: ${invoice.invoiceNumber}`, 555, 75, { align: 'right' });

    doc.setFont('helvetica', 'normal');
    doc.setTextColor(100, 116, 139);
    doc.text(`Date: ${new Date(invoice.invoiceDate).toLocaleDateString('en-GB')}`, 555, 90, { align: 'right' });
    doc.text(`Billing Period: ${invoice.quarter} FY ${invoice.financialYear}`, 555, 105, { align: 'right' });

    // Divider
    doc.setDrawColor(226, 232, 240);
    doc.line(40, 120, 555, 120);

    // Bill To
    doc.setFillColor(248, 250, 252);
    doc.roundedRect(40, 135, 250, 95, 4, 4, 'F');
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(9);
    doc.setTextColor(30, 58, 138);
    doc.text('BILLED TO (CLIENT DETAILS):', 50, 150);

    doc.setFont('helvetica', 'bold');
    doc.setFontSize(11);
    doc.setTextColor(15, 23, 42);
    doc.text(invoice.clientName, 50, 168);

    doc.setFont('helvetica', 'normal');
    doc.setFontSize(9);
    doc.setTextColor(100, 116, 139);
    doc.text(`Client Code: ${invoice.clientCode}`, 50, 182);
    doc.text(invoice.clientEmail, 50, 196);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(15, 23, 42);
    doc.text(`GSTIN: Registered Enterprise Client`, 50, 220);

    // Payment Info
    doc.setFillColor(248, 250, 252);
    doc.roundedRect(305, 135, 250, 95, 4, 4, 'F');
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(9);
    doc.setTextColor(30, 58, 138);
    doc.text('PAYMENT DETAILS & TERMS:', 315, 150);

    doc.setFont('helvetica', 'normal');
    doc.setFontSize(9);
    doc.setTextColor(100, 116, 139);
    doc.text(`Payment Terms: ${settings.paymentTerms}`, 315, 168);
    doc.text('Bank Name: HDFC Bank Ltd', 315, 182);
    doc.text('Account No: 50200088991234', 315, 196);
    doc.text('IFSC Code: HDFC0001234', 315, 210);

    // Table Header
    const tableTop = 250;
    doc.setFillColor(30, 58, 138);
    doc.rect(40, tableTop, 515, 24, 'F');
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(9);
    doc.setTextColor(255, 255, 255);
    doc.text('SL', 50, tableTop + 16);
    doc.text('DESCRIPTION', 80, tableTop + 16);
    doc.text('PERIOD', 280, tableTop + 16);
    doc.text('FILE COUNT', 370, tableTop + 16, { align: 'right' });
    doc.text('RATE/FILE', 450, tableTop + 16, { align: 'right' });
    doc.text('AMOUNT (INR)', 545, tableTop + 16, { align: 'right' });

    // Table Row
    const rowY = tableTop + 24;
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(9);
    doc.setTextColor(15, 23, 42);
    doc.text('1', 50, rowY + 18);
    doc.text('Quarterly File Processing Services', 80, rowY + 18);
    doc.text(`${invoice.quarter} FY ${invoice.financialYear}`, 280, rowY + 18);
    doc.text(invoice.totalFileCount.toLocaleString('en-IN'), 370, rowY + 18, { align: 'right' });
    // jsPDF's built-in "helvetica" font is one of the 14 standard PDF fonts,
    // which only cover WinAnsi/Latin-1 - there's no glyph for ₹ (U+20B9), so
    // it silently falls back to an unrelated character (rendering as a
    // stray "1" before every amount). "Rs." is plain ASCII and renders
    // correctly with the standard font, so it's used here instead of ₹
    // throughout the PDF (the email body text elsewhere still uses ₹ since
    // that's rendered by the mail client's own font, not jsPDF's).
    doc.text(`Rs. ${invoice.ratePerFile}`, 450, rowY + 18, { align: 'right' });
    doc.text(`Rs. ${invoice.subtotal.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`, 545, rowY + 18, { align: 'right' });

    // Summary Totals
    const sumY = rowY + 60;
    doc.text('Subtotal:', 350, sumY);
    doc.text(`Rs. ${invoice.subtotal.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`, 545, sumY, { align: 'right' });

    doc.text(`GST / Tax (${settings.defaultTaxRate}%):`, 350, sumY + 20);
    doc.text(`Rs. ${invoice.tax.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`, 545, sumY + 20, { align: 'right' });

    doc.setFillColor(238, 242, 255);
    doc.roundedRect(340, sumY + 30, 215, 32, 4, 4, 'F');
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(11);
    doc.setTextColor(30, 58, 138);
    doc.text('TOTAL AMOUNT:', 350, sumY + 50);
    doc.text(`Rs. ${invoice.totalAmount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`, 545, sumY + 50, { align: 'right' });

    return doc;
  }

  public downloadInvoicePdf(invoice: InvoiceItem) {
    const doc = this.buildInvoicePdfDoc(invoice);
    doc.save(`${invoice.invoiceNumber}.pdf`);
  }

  // Base64-encoded PDF bytes (no data: prefix), suitable for the mail
  // server's nodemailer attachment. Generated fresh per invoice email so it
  // always matches what "Download PDF" would produce.
  private getInvoicePdfBase64(invoice: InvoiceItem): string {
    const doc = this.buildInvoicePdfDoc(invoice);
    return doc.output('datauristring').split(',')[1] || '';
  }

  // --- Invoices ---
  public getInvoices(): InvoiceItem[] {
    return getStored<InvoiceItem[]>(STORAGE_KEYS.INVOICES, []);
  }

  // --- Emails ---
  public getEmails(): EmailLogItem[] {
    return getStored<EmailLogItem[]>(STORAGE_KEYS.EMAILS, []);
  }

  private recordEmail(email: Omit<EmailLogItem, 'id' | 'sentAt' | 'createdAt'>) {
    const emails = this.getEmails();
    const now = new Date().toISOString();
    emails.unshift({
      ...email,
      id: 'eml-' + Date.now() + '-' + Math.random().toString(36).substring(2, 6),
      sentAt: now,
      createdAt: now,
    });
    setStored(STORAGE_KEYS.EMAILS, emails);
  }

  // --- Settings ---
  public getSettings(): SystemSettings {
    // Merge over DEFAULT_SETTINGS (rather than just falling back to it when
    // the key is entirely missing) so that a settings object saved by an
    // older version of the app - before a new field like
    // reminderIntervalDays existed - still comes back with that new field
    // populated, instead of silently missing it until a full database reset.
    const stored = getStored<Partial<SystemSettings>>(STORAGE_KEYS.SETTINGS, {});
    return { ...DEFAULT_SETTINGS, ...stored };
  }

  public updateSettings(updates: Partial<SystemSettings>) {
    const current = this.getSettings();
    const updated = { ...current, ...updates };
    setStored(STORAGE_KEYS.SETTINGS, updated);
    this.logAudit('SETTINGS_UPDATED', 'SystemSetting', 'GLOBAL', 'System settings were updated');
    return updated;
  }

  // --- User Authentication ---
  public authenticateUser(username: string, password: string): User {
    const cleanU = username.trim().toLowerCase();
    const cleanP = password.trim();
    // Passwords are configurable (Settings > Login & Security) rather than
    // hardcoded, so they're read fresh from settings on every login attempt
    // - a password changed there takes effect immediately, no code edit or
    // restart needed. Usernames and login IDs stay fixed by design (per
    // earlier instruction to keep admin@example.com / demo@example.com as
    // the login identities); only the password itself is changeable.
    const settings = this.getSettings();

    if (cleanU === 'admin' && cleanP === settings.adminPassword) {
      const user: User = {
        id: 'u-admin-1',
        username: 'admin',
        name: 'System Administrator',
        email: 'admin@example.com',
        role: 'Admin',
      };
      this.logAudit('USER_LOGIN', 'User', user.id, `User admin (Admin) logged in successfully`);
      return user;
    }

    if (cleanU === 'demo' && cleanP === settings.userPassword) {
      const user: User = {
        id: 'u-user-1',
        username: 'demo',
        name: 'Finance Operator',
        email: 'demo@example.com',
        role: 'User',
      };
      this.logAudit('USER_LOGIN', 'User', user.id, `User demo (User) logged in successfully`);
      return user;
    }

    throw new Error('Invalid username or password.');
  }

  // Changes the login password for the 'admin' or 'demo' account. Requires
  // the CURRENT password to match first (so someone can't change a
  // password just by having Settings access without also knowing the
  // account's existing password), logs the change to the Audit Trail, but
  // never logs the actual password values themselves.
  public changeLoginPassword(
    target: 'admin' | 'demo',
    currentPassword: string,
    newPassword: string
  ): { success: boolean } {
    const settings = this.getSettings();
    const existing = target === 'admin' ? settings.adminPassword : settings.userPassword;

    if (currentPassword.trim() !== existing) {
      throw new Error('Current password is incorrect.');
    }

    const trimmedNew = newPassword.trim();
    if (trimmedNew.length < 4) {
      throw new Error('New password must be at least 4 characters long.');
    }

    this.updateSettings(target === 'admin' ? { adminPassword: trimmedNew } : { userPassword: trimmedNew });

    this.logAudit(
      'LOGIN_PASSWORD_CHANGED',
      'User',
      target === 'admin' ? 'u-admin-1' : 'u-user-1',
      `Login password changed for the ${target === 'admin' ? 'Admin' : 'User (demo)'} account.`
    );

    return { success: true };
  }

  // Lets an Admin reset either account's password WITHOUT knowing its
  // current value - unlike changeLoginPassword above, which is the
  // self-service "I know my password and want a new one" flow. Enforcing
  // that only an Admin may call this is the UI's job (the Settings screen
  // only renders this control when currentUser.role === 'Admin'), matching
  // this app's existing client-side trust model (e.g. the Database Viewer
  // tab is likewise hidden, not separately re-authorized, for non-Admins).
  public adminResetPassword(target: 'admin' | 'demo', newPassword: string): { success: boolean } {
    const trimmedNew = newPassword.trim();
    if (trimmedNew.length < 4) {
      throw new Error('New password must be at least 4 characters long.');
    }

    this.updateSettings(target === 'admin' ? { adminPassword: trimmedNew } : { userPassword: trimmedNew });

    this.logAudit(
      'LOGIN_PASSWORD_RESET_BY_ADMIN',
      'User',
      target === 'admin' ? 'u-admin-1' : 'u-user-1',
      `Login password reset by an administrator for the ${target === 'admin' ? 'Admin' : 'User (demo)'} account.`
    );

    return { success: true };
  }

  // --- Dashboard Data ---
  public getDashboardData() {
    const clients = this.getClients().filter((c) => c.active);
    const logs = this.getDeliveryLogs();
    const billings = this.getConfirmations();
    const invoices = this.getInvoices();
    const auditLogs = this.getAuditLogs();

    const totalFilesProcessed = logs.reduce((acc, curr) => acc + curr.fileCount, 0);
    const totalAmountProcessed = logs.reduce((acc, curr) => acc + curr.amount, 0);
    const totalBillingAmount = billings.reduce((acc, curr) => acc + curr.totalAmount, 0) || (totalAmountProcessed * 1.18);

    const pendingConfirmations = billings.filter((b) => b.status === 'PENDING_CONFIRMATION').length;
    const confirmedClients = billings.filter((b) => b.status !== 'PENDING_CONFIRMATION' && b.status !== 'REJECTED').length;
    const invoicesGenerated = invoices.length;
    const invoicesSent = invoices.filter((i) => i.status === 'SENT').length;

    return {
      totalClients: clients.length,
      currentQuarter: 'Q1 FY 2026-27',
      totalFilesProcessed,
      totalBillingAmount,
      pendingConfirmations,
      confirmedClients,
      invoicesGenerated,
      invoicesSent,
      recentActivity: auditLogs.slice(0, 6),
    };
  }

  // --- Raw Database Access & Inspection ---
  public getRawDatabaseDump() {
    const clients = this.getClients();
    const deliveryLogs = this.getDeliveryLogs();
    const billings = this.getConfirmations();
    const invoices = this.getInvoices();
    const emailLogs = this.getEmails();
    const auditLogs = this.getAuditLogs();
    const settings = this.getSettings();
    const users = [
      { id: 'u-admin-1', username: 'admin', name: 'System Administrator', email: 'admin@example.com', role: 'Admin' },
      { id: 'u-user-1', username: 'demo', name: 'Finance Operator', email: 'demo@example.com', role: 'User' }
    ];

    return {
      tables: {
        Client: clients,
        DeliveryLog: deliveryLogs,
        Billing: billings,
        Invoice: invoices,
        EmailLog: emailLogs,
        AuditLog: auditLogs,
        SystemSetting: Object.entries(settings).map(([key, value]) => ({ key, value })),
        User: users,
      },
      stats: {
        totalTables: 8,
        totalRecords:
          clients.length +
          deliveryLogs.length +
          billings.length +
          invoices.length +
          emailLogs.length +
          auditLogs.length +
          Object.keys(settings).length +
          users.length,
        engine: 'SQLite / In-Browser Storage Engine',
        schemaVersion: '1.0.0 (Prisma SQLite Schema)',
      }
    };
  }

  public resetDatabase() {
    localStorage.removeItem(STORAGE_KEYS.CLIENTS);
    localStorage.removeItem(STORAGE_KEYS.DELIVERY_LOGS);
    localStorage.removeItem(STORAGE_KEYS.BILLINGS);
    localStorage.removeItem(STORAGE_KEYS.INVOICES);
    localStorage.removeItem(STORAGE_KEYS.EMAILS);
    localStorage.removeItem(STORAGE_KEYS.AUDIT_LOGS);
    localStorage.removeItem(STORAGE_KEYS.SETTINGS);
    this.init();
    return this.getRawDatabaseDump();
  }
}

export const systemService = SystemService.getInstance();
