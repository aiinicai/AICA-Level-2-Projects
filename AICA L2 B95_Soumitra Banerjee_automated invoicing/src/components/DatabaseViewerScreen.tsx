import React, { useState } from 'react';
import { 
  Database, 
  Table, 
  Code2, 
  Download, 
  Copy, 
  RotateCcw, 
  Search, 
  Check, 
  Layers, 
  Terminal,
  ExternalLink,
  BookOpen,
  Info
} from 'lucide-react';
import { systemService } from '../lib/services/systemService';

interface DatabaseViewerScreenProps {
  onRefresh: () => void;
}

export const DatabaseViewerScreen: React.FC<DatabaseViewerScreenProps> = ({ onRefresh }) => {
  const [activeSubTab, setActiveSubTab] = useState<'tables' | 'schema' | 'guide'>('tables');
  const [selectedTable, setSelectedTable] = useState<string>('Client');
  const [tableSearch, setTableSearch] = useState<string>('');
  const [viewMode, setViewMode] = useState<'table' | 'json'>('table');
  const [copied, setCopied] = useState<boolean>(false);
  const [resetConfirm, setResetConfirm] = useState<boolean>(false);

  const dbDump = systemService.getRawDatabaseDump();
  const tables = dbDump.tables as Record<string, any[]>;
  const currentRecords = tables[selectedTable] || [];

  const filteredRecords = currentRecords.filter((rec) => {
    if (!tableSearch) return true;
    const str = JSON.stringify(rec).toLowerCase();
    return str.includes(tableSearch.toLowerCase());
  });

  const tableColumns = currentRecords.length > 0 ? Object.keys(currentRecords[0]) : [];

  const handleCopyJson = () => {
    navigator.clipboard.writeText(JSON.stringify(currentRecords, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  const handleDownloadBackup = () => {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(dbDump, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute('download', `quarterly_billing_database_backup_${new Date().toISOString().slice(0, 10)}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  const handleResetDb = () => {
    if (!resetConfirm) {
      setResetConfirm(true);
      setTimeout(() => setResetConfirm(false), 5000);
      return;
    }
    systemService.resetDatabase();
    setResetConfirm(false);
    onRefresh();
  };

  const prismaSchemaCode = `// prisma/schema.prisma
// Database Schema for Quarterly Billing & Invoice Automation System

generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "sqlite" // Can be switched to "postgresql" for production
  url      = env("DATABASE_URL")
}

model User {
  id        String   @id @default(uuid())
  username  String   @unique
  name      String
  email     String
  password  String
  role      String   @default("Admin") // "Admin" or "User"
  createdAt DateTime @default(now())
}

model Client {
  id            String        @id @default(uuid())
  clientCode    String        @unique
  name          String
  contactPerson String
  email         String
  address       String
  gstin         String
  ratePerFile   Float         @default(5.0)
  active        Boolean       @default(true)
  createdAt     DateTime      @default(now())
  updatedAt     DateTime      @updatedAt
  deliveryLogs  DeliveryLog[]
  billings      Billing[]
  emailLogs     EmailLog[]
}

model DeliveryLog {
  id            String   @id @default(uuid())
  clientId      String
  client        Client   @relation(fields: [clientId], references: [id], onDelete: Cascade)
  month         String
  quarter       String   // "Q1", "Q2", "Q3", "Q4"
  financialYear String   // e.g. "2026-27"
  fileCount     Int
  amount        Float
  createdAt     DateTime @default(now())
}

model Billing {
  id             String     @id @default(uuid())
  clientId       String
  client         Client     @relation(fields: [clientId], references: [id], onDelete: Cascade)
  quarter        String     // e.g. "Q1"
  financialYear  String     // e.g. "2026-27"
  totalFileCount Int
  ratePerFile    Float
  subtotal       Float
  tax            Float
  totalAmount    Float
  status         String     @default("PENDING_CONFIRMATION")
  createdAt      DateTime   @default(now())
  updatedAt      DateTime   @updatedAt
  invoice        Invoice?
  emailLogs      EmailLog[]

  @@unique([clientId, quarter, financialYear])
}

model EmailLog {
  id         String   @id @default(uuid())
  clientId   String?
  client     Client?  @relation(fields: [clientId], references: [id], onDelete: SetNull)
  billingId  String?
  billing    Billing? @relation(fields: [billingId], references: [id], onDelete: SetNull)
  type       String   // "CONFIRMATION" | "INVOICE"
  recipient  String
  subject    String
  body       String
  status     String   // "SENT" | "SIMULATED" | "FAILED"
  sentAt     DateTime @default(now())
  createdAt  DateTime @default(now())
}

model Invoice {
  id            String   @id @default(uuid())
  billingId     String   @unique
  billing       Billing  @relation(fields: [billingId], references: [id], onDelete: Cascade)
  invoiceNumber String   @unique
  invoiceDate   DateTime @default(now())
  subtotal      Float
  tax           Float
  totalAmount   Float
  pdfPath       String?
  status        String   @default("GENERATED")
  createdAt     DateTime @default(now())
}

model AuditLog {
  id          String   @id @default(uuid())
  action      String
  entity      String
  entityId    String?
  description String
  createdAt   DateTime @default(now())
}

model SystemSetting {
  id        String   @id @default("global")
  key       String   @unique
  value     String
  updatedAt DateTime @updatedAt
}`;

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Database Viewer &amp; Schema Inspector</h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">
              Live Connected
            </span>
          </div>
          <p className="text-sm text-slate-500">
            Inspect raw relational tables, review database records, examine schema definitions, and export backups.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <button
            onClick={handleDownloadBackup}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 rounded-lg text-xs font-semibold shadow-xs transition"
          >
            <Download className="w-3.5 h-3.5 text-slate-500" />
            <span>Export DB (JSON)</span>
          </button>

          <button
            onClick={handleResetDb}
            className={`inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold transition ${
              resetConfirm
                ? 'bg-rose-600 text-white hover:bg-rose-700 animate-pulse'
                : 'bg-white border border-slate-300 text-slate-700 hover:bg-rose-50 hover:text-rose-700'
            }`}
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>{resetConfirm ? 'Click to Confirm Reset' : 'Reset to Seed Data'}</span>
          </button>
        </div>
      </div>

      {/* Navigation Sub-Tabs */}
      <div className="border-b border-slate-200">
        <nav className="flex space-x-6">
          <button
            onClick={() => setActiveSubTab('tables')}
            className={`py-3 px-1 border-b-2 font-medium text-sm transition flex items-center gap-2 ${
              activeSubTab === 'tables'
                ? 'border-blue-600 text-blue-600 font-semibold'
                : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
            }`}
          >
            <Table className="w-4 h-4" />
            <span>Raw Tables Browser ({dbDump.stats.totalRecords} Records)</span>
          </button>

          <button
            onClick={() => setActiveSubTab('schema')}
            className={`py-3 px-1 border-b-2 font-medium text-sm transition flex items-center gap-2 ${
              activeSubTab === 'schema'
                ? 'border-blue-600 text-blue-600 font-semibold'
                : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
            }`}
          >
            <Code2 className="w-4 h-4" />
            <span>Prisma Schema (`schema.prisma`)</span>
          </button>

          <button
            onClick={() => setActiveSubTab('guide')}
            className={`py-3 px-1 border-b-2 font-medium text-sm transition flex items-center gap-2 ${
              activeSubTab === 'guide'
                ? 'border-blue-600 text-blue-600 font-semibold'
                : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
            }`}
          >
            <BookOpen className="w-4 h-4" />
            <span>Database Architecture Guide</span>
          </button>
        </nav>
      </div>

      {/* TAB 1: TABLES BROWSER */}
      {activeSubTab === 'tables' && (
        <div className="space-y-6">
          {/* Table Selector Pills */}
          <div className="flex flex-wrap items-center gap-2">
            {Object.keys(tables).map((tbl) => {
              const count = tables[tbl]?.length || 0;
              const isSelected = selectedTable === tbl;
              return (
                <button
                  key={tbl}
                  onClick={() => {
                    setSelectedTable(tbl);
                    setTableSearch('');
                  }}
                  className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition ${
                    isSelected
                      ? 'bg-blue-600 text-white shadow-xs'
                      : 'bg-white border border-slate-200 text-slate-700 hover:bg-slate-50'
                  }`}
                >
                  <Database className="w-3.5 h-3.5 opacity-70" />
                  <span>{tbl}</span>
                  <span
                    className={`px-1.5 py-0.2 rounded-full text-[10px] font-mono ${
                      isSelected ? 'bg-blue-700 text-white' : 'bg-slate-100 text-slate-600'
                    }`}
                  >
                    {count}
                  </span>
                </button>
              );
            })}
          </div>

          {/* Controls Bar */}
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="relative w-full sm:w-80">
              <Search className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
              <input
                type="text"
                placeholder={`Search records in ${selectedTable}...`}
                value={tableSearch}
                onChange={(e) => setTableSearch(e.target.value)}
                className="w-full pl-9 pr-4 py-2 border border-slate-300 rounded-lg text-xs focus:ring-2 focus:ring-blue-500 focus:outline-none"
              />
            </div>

            <div className="flex items-center gap-3">
              {/* Table / JSON toggle */}
              <div className="inline-flex rounded-lg border border-slate-200 p-0.5 bg-slate-50 text-xs font-medium">
                <button
                  onClick={() => setViewMode('table')}
                  className={`px-3 py-1 rounded-md transition ${viewMode === 'table' ? 'bg-white shadow-xs text-blue-600 font-semibold' : 'text-slate-600'}`}
                >
                  Grid View
                </button>
                <button
                  onClick={() => setViewMode('json')}
                  className={`px-3 py-1 rounded-md transition ${viewMode === 'json' ? 'bg-white shadow-xs text-blue-600 font-semibold' : 'text-slate-600'}`}
                >
                  Raw JSON
                </button>
              </div>

              <button
                onClick={handleCopyJson}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold transition"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copied ? 'Copied!' : 'Copy Table'}</span>
              </button>
            </div>
          </div>

          {/* Content View */}
          {viewMode === 'table' ? (
            <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-xs">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 border-b border-slate-200 text-[11px] font-semibold uppercase text-slate-600 tracking-wider">
                    <tr>
                      {tableColumns.map((col) => (
                        <th key={col} className="py-3 px-3.5 whitespace-nowrap">
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-slate-700">
                    {filteredRecords.length === 0 ? (
                      <tr>
                        <td colSpan={tableColumns.length || 1} className="py-12 text-center text-slate-400">
                          No records found in table <code className="font-mono text-slate-600">{selectedTable}</code>.
                        </td>
                      </tr>
                    ) : (
                      filteredRecords.map((row, idx) => (
                        <tr key={idx} className="hover:bg-slate-50/80 transition">
                          {tableColumns.map((col) => {
                            const val = row[col];
                            return (
                              <td key={col} className="py-2.5 px-3.5 font-mono text-[11px] max-w-xs truncate">
                                {typeof val === 'boolean' ? (
                                  <span
                                    className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                                      val ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'
                                    }`}
                                  >
                                    {val ? 'TRUE' : 'FALSE'}
                                  </span>
                                ) : typeof val === 'object' && val !== null ? (
                                  JSON.stringify(val)
                                ) : (
                                  String(val ?? '—')
                                )}
                              </td>
                            );
                          })}
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xs overflow-x-auto text-xs font-mono text-slate-200 max-h-[500px]">
              <pre>{JSON.stringify(filteredRecords, null, 2)}</pre>
            </div>
          )}
        </div>
      )}

      {/* TAB 2: PRISMA SCHEMA */}
      {activeSubTab === 'schema' && (
        <div className="space-y-4">
          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs flex items-center justify-between">
            <div>
              <h3 className="font-bold text-slate-900 text-sm">Prisma ORM Schema Definition</h3>
              <p className="text-xs text-slate-500">
                Defined in file: <code className="font-mono bg-slate-100 px-1 py-0.5 rounded text-blue-600">prisma/schema.prisma</code>
              </p>
            </div>
            <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
              Provider: SQLite (Portable to PostgreSQL)
            </span>
          </div>

          <div className="bg-slate-900 rounded-xl p-6 shadow-md border border-slate-800 overflow-x-auto font-mono text-xs text-slate-200 leading-relaxed max-h-[600px]">
            <pre>{prismaSchemaCode}</pre>
          </div>
        </div>
      )}

      {/* TAB 3: ARCHITECTURE GUIDE */}
      {activeSubTab === 'guide' && (
        <div className="space-y-6">
          <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs space-y-4">
            <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
              <Info className="w-5 h-5 text-blue-600" />
              <h2 className="text-base font-bold text-slate-900">How to View &amp; Access the Database</h2>
            </div>

            <div className="space-y-4 text-xs text-slate-700 leading-relaxed">
              <div className="p-4 bg-blue-50/60 border border-blue-200 rounded-xl space-y-2">
                <h4 className="font-bold text-blue-900 text-sm flex items-center gap-2">
                  <Table className="w-4 h-4 text-blue-700" />
                  1. View Live Records in the Application
                </h4>
                <p>
                  You are currently inside the built-in <strong>Database Viewer</strong>. Click any table tab above 
                  (<code className="font-mono text-blue-800">Client</code>, <code className="font-mono text-blue-800">DeliveryLog</code>, 
                  <code className="font-mono text-blue-800">Billing</code>, <code className="font-mono text-blue-800">Invoice</code>, 
                  <code className="font-mono text-blue-800">EmailLog</code>, <code className="font-mono text-blue-800">AuditLog</code>, 
                  <code className="font-mono text-blue-800">SystemSetting</code>, <code className="font-mono text-blue-800">User</code>) 
                  to view, search, and copy raw rows or JSON.
                </p>
              </div>

              <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-2">
                <h4 className="font-bold text-slate-900 text-sm flex items-center gap-2">
                  <Terminal className="w-4 h-4 text-slate-700" />
                  2. Inspect via Browser Developer Tools
                </h4>
                <p>
                  All database tables are stored with reactive persistence in your browser. To view or inspect via Chrome / Edge DevTools:
                </p>
                <ol className="list-decimal list-inside space-y-1 pl-2 font-mono text-[11px] text-slate-600">
                  <li>Press <strong>F12</strong> or <strong>Right-Click &gt; Inspect</strong></li>
                  <li>Click on the <strong>Application</strong> (or <strong>Storage</strong>) tab</li>
                  <li>In the left tree, expand <strong>Local Storage</strong> and select the current domain</li>
                  <li>View the table keys: <code className="text-blue-600 font-bold">qb_clients_v2</code>, <code className="text-blue-600 font-bold">qb_delivery_logs_v2</code>, <code className="text-blue-600 font-bold">qb_billings_v2</code>, <code className="text-blue-600 font-bold">qb_invoices_v2</code>, etc.</li>
                </ol>
              </div>

              <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-2">
                <h4 className="font-bold text-slate-900 text-sm flex items-center gap-2">
                  <Code2 className="w-4 h-4 text-slate-700" />
                  3. Relational Schema &amp; PostgreSQL Migration
                </h4>
                <p>
                  The schema file is kept at <code className="font-mono font-bold text-slate-800">prisma/schema.prisma</code>. 
                  When deploying to a production server with PostgreSQL, change the datasource provider:
                </p>
                <div className="p-3 bg-slate-900 text-slate-200 rounded-lg font-mono text-[11px]">
                  {`datasource db {\n  provider = "postgresql"\n  url      = env("DATABASE_URL")\n}`}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
