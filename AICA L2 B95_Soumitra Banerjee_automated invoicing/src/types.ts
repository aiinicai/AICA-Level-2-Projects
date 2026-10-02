export interface User {
  id: string;
  username: string;
  name: string;
  email: string;
  role: 'Admin' | 'User';
}

export interface Client {
  id: string;
  clientCode: string;
  name: string;
  contactPerson: string;
  email: string;
  address: string;
  gstin: string;
  ratePerFile: number;
  active: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface DeliveryLog {
  id: string;
  clientId: string;
  clientCode: string;
  clientName: string;
  month: string;
  quarter: string;
  financialYear: string;
  fileCount: number;
  amount: number;
  createdAt: string;
}

export interface BillingClientSummary {
  billingId: string | null;
  clientId: string;
  clientCode: string;
  clientName: string;
  ratePerFile: number;
  months: { [month: string]: number };
  totalFileCount: number;
  subtotal: number;
  tax: number;
  totalAmount: number;
  status: 'PENDING_CONFIRMATION' | 'CONFIRMED' | 'INVOICE_GENERATED' | 'INVOICE_SENT' | 'REJECTED' | string;
}

export interface ConfirmationItem {
  id: string;
  clientId: string;
  clientName: string;
  clientCode: string;
  clientEmail: string;
  quarter: string;
  financialYear: string;
  totalFileCount: number;
  ratePerFile: number;
  subtotal: number;
  tax: number;
  totalAmount: number;
  status: string;
  invoiceNumber?: string;
  pdfPath?: string;
  invoiceId?: string;
  createdAt: string;
  updatedAt: string;
}

export interface InvoiceItem {
  id: string;
  billingId: string;
  invoiceNumber: string;
  invoiceDate: string;
  clientId: string;
  clientCode: string;
  clientName: string;
  clientEmail: string;
  quarter: string;
  financialYear: string;
  totalFileCount: number;
  ratePerFile: number;
  subtotal: number;
  tax: number;
  totalAmount: number;
  pdfPath?: string;
  status: string;
  createdAt: string;
}

export interface AuditLogItem {
  id: string;
  action: string;
  entity: string;
  entityId: string;
  description: string;
  createdAt: string;
}

export interface EmailLogItem {
  id: string;
  clientId?: string;
  clientName?: string;
  clientCode?: string;
  billingId?: string;
  type: 'CONFIRMATION' | 'INVOICE' | 'REMINDER';
  recipient: string;
  subject: string;
  body: string;
  status: 'SENT' | 'SIMULATED' | 'FAILED';
  sentAt: string;
  createdAt: string;
}

export interface SystemSettings {
  companyName: string;
  companyAddress: string;
  companyGstin: string;
  companyPan: string;
  companyEmail: string;
  companyPhone: string;
  defaultTaxRate: string;
  currency: string;
  paymentTerms: string;
  invoicePrefix: string;
  invoiceStartingNumber: string;
  smtpHost: string;
  smtpPort: string;
  smtpUser: string;
  smtpPass: string;
  senderEmail: string;
  demoMode: string;
  reminderIntervalDays: string;
  adminPassword: string;
  userPassword: string;
}
