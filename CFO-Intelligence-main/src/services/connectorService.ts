import { AccountingConnector } from '../types';

export interface ConnectorConfig {
  id: 'qbo' | 'tally' | 'zoho' | 'netsuite' | 'xero';
  name: string;
  category: 'cloud_accounting' | 'on_premise_erp' | 'enterprise_erp';
  status: 'connected' | 'disconnected' | 'syncing' | 'error';
  lastSynced?: string;
  companyName?: string;
  syncFrequency: 'Realtime' | 'Hourly' | 'Daily' | 'Manual';
  environment?: 'Production' | 'Sandbox';
  
  // QBO specific
  qboRealmId?: string;
  qboClientId?: string;
  qboClientSecret?: string;
  qboAutoSyncInvoices?: boolean;
  qboAutoSyncBills?: boolean;

  // Tally specific
  tallyHost?: string;
  tallyPort?: string;
  tallyCompanyName?: string;
  tallyVersion?: string;
  tallyAuthPassword?: string;
  tallySyncVouchers?: boolean;

  // Zoho specific
  zohoDataCenter?: 'zoho.com' | 'zoho.in' | 'zoho.eu' | 'zoho.com.au' | 'zoho.jp' | 'zoho.ca';
  zohoOrgId?: string;
  zohoClientId?: string;
  zohoClientSecret?: string;
  zohoAutoSyncCurrencies?: boolean;

  // NetSuite specific
  netSuiteAccountId?: string;
  netSuiteConsumerKey?: string;
  netSuiteConsumerSecret?: string;
  netSuiteTokenId?: string;
  netSuiteTokenSecret?: string;
  netSuiteSubsidiaryId?: string;
  netSuiteRoleId?: string;

  // Xero specific
  xeroTenantId?: string;
  xeroOrgName?: string;

  // Sync Stats
  recordsCount?: number;
  lastSyncDuration?: string;
  tokenExpiresAt?: string;
}

export interface SyncLogEntry {
  id: string;
  connectorId: string;
  connectorName: string;
  timestamp: string;
  status: 'SUCCESS' | 'WARNING' | 'FAILED';
  recordsImported: number;
  durationMs: number;
  details: string;
  entityBreakdown: {
    chartOfAccounts: number;
    invoices: number;
    bills: number;
    journalEntries: number;
    bankTransactions: number;
  };
}

export const DEFAULT_CONNECTOR_CONFIGS: Record<string, ConnectorConfig> = {
  qbo: {
    id: 'qbo',
    name: 'QuickBooks Online',
    category: 'cloud_accounting',
    status: 'connected',
    lastSynced: 'Today at 03:30 AM',
    companyName: 'Apex Innovations Inc (US Entity)',
    syncFrequency: 'Daily',
    environment: 'Production',
    qboRealmId: '9130354892019482',
    qboClientId: 'AB12345cde67890fghij',
    qboAutoSyncInvoices: true,
    qboAutoSyncBills: true,
    recordsCount: 482,
    lastSyncDuration: '1.4s',
    tokenExpiresAt: 'In 58 days',
  },
  tally: {
    id: 'tally',
    name: 'Tally Prime & ERP 9',
    category: 'on_premise_erp',
    status: 'connected',
    lastSynced: 'Yesterday at 06:15 PM',
    companyName: 'Apex Innovations Pvt Ltd (India)',
    syncFrequency: 'Daily',
    environment: 'Production',
    tallyHost: 'localhost',
    tallyPort: '9000',
    tallyCompanyName: 'Apex Innovations Pvt Ltd',
    tallyVersion: 'TallyPrime 4.1 Enterprise',
    tallySyncVouchers: true,
    recordsCount: 840,
    lastSyncDuration: '2.8s',
    tokenExpiresAt: 'Local XML Gateway',
  },
  zoho: {
    id: 'zoho',
    name: 'Zoho Books',
    category: 'cloud_accounting',
    status: 'disconnected',
    lastSynced: 'Never',
    companyName: '',
    syncFrequency: 'Hourly',
    environment: 'Production',
    zohoDataCenter: 'zoho.com',
    zohoOrgId: '782910482',
    zohoAutoSyncCurrencies: true,
    recordsCount: 0,
    lastSyncDuration: '-',
  },
  netsuite: {
    id: 'netsuite',
    name: 'Oracle NetSuite ERP',
    category: 'enterprise_erp',
    status: 'disconnected',
    lastSynced: 'Never',
    companyName: '',
    syncFrequency: 'Realtime',
    environment: 'Production',
    netSuiteAccountId: 'TSTDRV2918402',
    netSuiteSubsidiaryId: '1 - Global Parent Holding Corp',
    netSuiteRoleId: '1042 - FP&A Integration Admin',
    recordsCount: 0,
    lastSyncDuration: '-',
  },
  xero: {
    id: 'xero',
    name: 'Xero Accounting',
    category: 'cloud_accounting',
    status: 'disconnected',
    lastSynced: 'Never',
    companyName: '',
    syncFrequency: 'Daily',
    environment: 'Production',
    xeroTenantId: 'xer-org-9021849',
    recordsCount: 0,
    lastSyncDuration: '-',
  },
};

export const INITIAL_SYNC_LOGS: SyncLogEntry[] = [
  {
    id: 'log-1',
    connectorId: 'qbo',
    connectorName: 'QuickBooks Online',
    timestamp: 'Today at 03:30 AM',
    status: 'SUCCESS',
    recordsImported: 148,
    durationMs: 1420,
    details: 'Automated overnight general ledger & balance sheet synchronization completed.',
    entityBreakdown: {
      chartOfAccounts: 48,
      invoices: 42,
      bills: 36,
      journalEntries: 18,
      bankTransactions: 4,
    },
  },
  {
    id: 'log-2',
    connectorId: 'tally',
    connectorName: 'Tally Prime',
    timestamp: 'Yesterday at 06:15 PM',
    status: 'SUCCESS',
    recordsImported: 230,
    durationMs: 2810,
    details: 'XML Gateway voucher handshake and trial balance rollup successful.',
    entityBreakdown: {
      chartOfAccounts: 64,
      invoices: 82,
      bills: 54,
      journalEntries: 24,
      bankTransactions: 6,
    },
  },
  {
    id: 'log-3',
    connectorId: 'qbo',
    connectorName: 'QuickBooks Online',
    timestamp: 'Aug 24, 2026, 03:30 AM',
    status: 'SUCCESS',
    recordsImported: 96,
    durationMs: 1190,
    details: 'Daily incremental AR/AP aging reconciliation processed.',
    entityBreakdown: {
      chartOfAccounts: 0,
      invoices: 52,
      bills: 38,
      journalEntries: 6,
      bankTransactions: 0,
    },
  },
];
