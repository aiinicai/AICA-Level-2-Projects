import React, { useEffect, useMemo, useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  Download,
  FileSpreadsheet,
  Plus,
  RefreshCw,
  Search,
  Upload,
  UserCheck,
  UserMinus,
  UserPlus,
  X,
} from 'lucide-react';
import { normalizeEmail } from '../lib/dateUtils';
import { getSheetsAccessToken, requestSheetsPermission } from '../lib/firebase';
import {
  autoDetectColumnMapping,
  computeRosterDiff,
  downloadRosterTemplate,
  extractSpreadsheetId,
  fetchGoogleSheetRows,
  fetchSpreadsheetMetadata,
  parseCsvFromUrl,
  parseExcelOrCsvFile,
  type ColumnMapping,
  type RawSheetTable,
  type SpreadsheetMetadata,
} from '../lib/sheetsAndExcel';
import {
  VALIDATION_LIMITS,
  type Employee,
  type EmployeeStatus,
  type RosterDiffSummary,
  type RosterSource,
  type RosterSyncConfig,
} from '../types/leave';
import { ConfirmDialog } from './ConfirmDialog';

interface RosterSyncViewProps {
  employees: Employee[];
  syncConfig: RosterSyncConfig | null;
  onCommitSync: (params: {
    diff: RosterDiffSummary;
    source: RosterSource;
    sheetMeta?: { spreadsheetId: string; spreadsheetTitle: string; sheetName: string };
  }) => Promise<void>;
  onSaveSingleEmployee: (emp: Omit<Employee, 'id' | 'updatedAt'>) => Promise<void>;
  onNotify: (type: 'success' | 'error' | 'info', title: string, detail?: string) => void;
}

export const RosterSyncView: React.FC<RosterSyncViewProps> = ({
  employees,
  syncConfig,
  onCommitSync,
  onSaveSingleEmployee,
  onNotify,
}) => {
  const [sourceTab, setSourceTab] = useState<'sheets' | 'excel'>('sheets');
  const [sheetInput, setSheetInput] = useState<string>(syncConfig?.spreadsheetId || '');
  const [hasToken, setHasToken] = useState<boolean>(Boolean(getSheetsAccessToken()));
  const [loadingMeta, setLoadingMeta] = useState(false);
  const [loadingRows, setLoadingRows] = useState(false);
  const [meta, setMeta] = useState<SpreadsheetMetadata | null>(null);
  const [selectedTab, setSelectedTab] = useState<string>(syncConfig?.sheetName || '');

  const [rawTable, setRawTable] = useState<RawSheetTable | null>(null);
  const [activeSource, setActiveSource] = useState<RosterSource>('google_sheet');
  const [mapping, setMapping] = useState<ColumnMapping>({
    employeeCode: '',
    name: '',
    email: '',
    designation: '',
    department: '',
    managerEmail: '',
    status: '',
    joiningDate: '',
    isAdmin: '',
  });
  const [markMissingResigned, setMarkMissingResigned] = useState(true);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [committing, setCommitting] = useState(false);

  // Directory Search & Manual Edit
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'resigned'>('active');
  const [editingEmp, setEditingEmp] = useState<Partial<Employee> | null>(null);
  const [savingEmp, setSavingEmp] = useState(false);

  useEffect(() => {
    if (syncConfig?.spreadsheetId && !sheetInput) {
      setSheetInput(syncConfig.spreadsheetId);
    }
    if (syncConfig?.sheetName && !selectedTab) {
      setSelectedTab(syncConfig.sheetName);
    }
  }, [syncConfig, sheetInput, selectedTab]);

  const ensureToken = async (): Promise<string> => {
    const existing = getSheetsAccessToken();
    if (existing) {
      setHasToken(true);
      return existing;
    }
    const token = await requestSheetsPermission();
    setHasToken(true);
    return token;
  };

  const handleConnectSheets = async () => {
    try {
      await requestSheetsPermission();
      setHasToken(true);
      onNotify('success', 'Google Sheets connected', 'You can now load and sync employee spreadsheets.');
    } catch (err) {
      onNotify('error', 'Connection cancelled', err instanceof Error ? err.message : 'Unable to connect Google Sheets.');
    }
  };

  const handleLoadSpreadsheet = async () => {
    setLoadingMeta(true);
    setRawTable(null);
    try {
      const token = await ensureToken();
      const loadedMeta = await fetchSpreadsheetMetadata(sheetInput, token);
      setMeta(loadedMeta);
      const preferredTab =
        syncConfig?.sheetName && loadedMeta.sheetNames.includes(syncConfig.sheetName)
          ? syncConfig.sheetName
          : loadedMeta.sheetNames[0];
      setSelectedTab(preferredTab);
      await loadRowsForTab(loadedMeta.spreadsheetId, preferredTab, token);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Could not load Google Sheet.';
      if (msg === 'TOKEN_EXPIRED') {
        try {
          const fresh = await requestSheetsPermission();
          setHasToken(true);
          const loadedMeta = await fetchSpreadsheetMetadata(sheetInput, fresh);
          setMeta(loadedMeta);
          const preferredTab = loadedMeta.sheetNames[0];
          setSelectedTab(preferredTab);
          await loadRowsForTab(loadedMeta.spreadsheetId, preferredTab, fresh);
          return;
        } catch (retryErr) {
          onNotify('error', 'Google Sheets authorization failed', retryErr instanceof Error ? retryErr.message : undefined);
          return;
        }
      }
      onNotify('error', 'Failed to load spreadsheet', msg);
    } finally {
      setLoadingMeta(false);
    }
  };

  const loadRowsForTab = async (spreadsheetId: string, tabName: string, tokenOverride?: string) => {
    setLoadingRows(true);
    try {
      const token = tokenOverride || (await ensureToken());
      const table = await fetchGoogleSheetRows(spreadsheetId, tabName, token);
      setRawTable(table);
      setActiveSource('google_sheet');
      setMapping(autoDetectColumnMapping(table.headers));
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Unable to read sheet tab.';
      if (msg === 'TOKEN_EXPIRED') {
        const fresh = await requestSheetsPermission();
        setHasToken(true);
        const table = await fetchGoogleSheetRows(spreadsheetId, tabName, fresh);
        setRawTable(table);
        setActiveSource('google_sheet');
        setMapping(autoDetectColumnMapping(table.headers));
        return;
      }
      onNotify('error', 'Sheet read failed', msg);
    } finally {
      setLoadingRows(false);
    }
  };

  const handleExcelUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const table = await parseExcelOrCsvFile(file);
      setRawTable(table);
      setActiveSource('excel');
      setMapping(autoDetectColumnMapping(table.headers));
      onNotify('info', 'File parsed', `${table.rows.length} rows loaded from ${file.name}. Review mapping below.`);
    } catch (err) {
      onNotify('error', 'Could not read Excel/CSV file', err instanceof Error ? err.message : undefined);
    } finally {
      e.target.value = '';
    }
  };

  const handleLoadAttachedCsv = async () => {
    try {
      const table = await parseCsvFromUrl('/assets/aistudio/Untitled_spreadsheet_5ab60f9f');
      setRawTable(table);
      setActiveSource('excel');
      setMapping(autoDetectColumnMapping(table.headers));
      onNotify('info', 'Attached spreadsheet loaded', `${table.rows.length} employees ready to preview.`);
    } catch (err) {
      onNotify('error', 'Failed to load attached spreadsheet', err instanceof Error ? err.message : undefined);
    }
  };

  const diffPreview = useMemo(() => {
    if (!rawTable || !mapping.email || !mapping.name) return null;
    return computeRosterDiff(rawTable, mapping, employees, markMissingResigned);
  }, [rawTable, mapping, employees, markMissingResigned]);

  const handleConfirmCommit = async () => {
    if (!diffPreview) return;
    setCommitting(true);
    try {
      await onCommitSync({
        diff: diffPreview,
        source: activeSource,
        sheetMeta:
          activeSource === 'google_sheet' && meta
            ? {
                spreadsheetId: meta.spreadsheetId,
                spreadsheetTitle: meta.title,
                sheetName: selectedTab,
              }
            : undefined,
      });
      setConfirmOpen(false);
      setRawTable(null);
    } finally {
      setCommitting(false);
    }
  };

  const filteredEmployees = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    return employees
      .filter((e) => (statusFilter === 'all' ? true : e.status === statusFilter))
      .filter((e) => {
        if (!q) return true;
        return (
          e.name.toLowerCase().includes(q) ||
          e.email.toLowerCase().includes(q) ||
          e.designation.toLowerCase().includes(q) ||
          e.department.toLowerCase().includes(q) ||
          e.managerEmail.toLowerCase().includes(q)
        );
      })
      .sort((a, b) => a.name.localeCompare(b.name));
  }, [employees, searchQuery, statusFilter]);

  const handleSaveEmployeeModal = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingEmp?.name || !editingEmp?.email) return;
    const email = normalizeEmail(editingEmp.email);
    const managerEmail = editingEmp.managerEmail ? normalizeEmail(editingEmp.managerEmail) : '';
    const managerRecord = employees.find((emp) => emp.email === managerEmail);

    setSavingEmp(true);
    try {
      await onSaveSingleEmployee({
        employeeCode: (editingEmp.employeeCode || '').trim().slice(0, VALIDATION_LIMITS.maxEmployeeCodeLength),
        name: editingEmp.name.trim().slice(0, VALIDATION_LIMITS.maxNameLength),
        email,
        designation: (editingEmp.designation || 'Team Member').trim().slice(0, VALIDATION_LIMITS.maxDesignationLength),
        department: (editingEmp.department || '').trim().slice(0, VALIDATION_LIMITS.maxDepartmentLength),
        managerEmail,
        managerName: managerRecord?.name || managerEmail,
        isManager: employees.some((emp) => emp.managerEmail === email && emp.status === 'active'),
        isAdmin: Boolean(editingEmp.isAdmin),
        status: (editingEmp.status as EmployeeStatus) || 'active',
        joiningDate: (editingEmp.joiningDate || '').trim().slice(0, VALIDATION_LIMITS.maxJoiningDateLength),
        source: 'manual',
      });
      setEditingEmp(null);
    } finally {
      setSavingEmp(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Employee Roster &amp; Sheet Sync</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Link a dynamic Google Sheet or upload Excel to sync designations, reporting managers, new joinees, and resignees
          </p>
        </div>
        <button
          type="button"
          onClick={downloadRosterTemplate}
          className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-medium text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 whitespace-nowrap shrink-0 cursor-pointer"
        >
          <Download className="w-3.5 h-3.5" />
          Download Sample Excel
        </button>
      </div>

      {/* Sync Source Panel */}
      <section className="bg-white border border-slate-200 rounded-xl p-6 space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 pb-4">
          <div className="inline-flex items-center gap-1 p-1 bg-slate-100 border border-slate-200 rounded-lg">
            <button
              type="button"
              onClick={() => setSourceTab('sheets')}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
                sourceTab === 'sheets'
                  ? 'bg-white text-slate-900 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Google Sheet (Live Sync)
            </button>
            <button
              type="button"
              onClick={() => setSourceTab('excel')}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
                sourceTab === 'excel'
                  ? 'bg-white text-slate-900 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Excel / CSV Upload
            </button>
          </div>

          {syncConfig?.spreadsheetId && (
            <div className="text-xs text-slate-500">
              Last linked: <span className="font-medium text-slate-800">{syncConfig.spreadsheetTitle || syncConfig.spreadsheetId}</span>
              {syncConfig.sheetName ? ` (${syncConfig.sheetName})` : ''}
            </div>
          )}
        </div>

        {sourceTab === 'sheets' ? (
          <div className="space-y-4">
            <div className="flex flex-col md:flex-row items-stretch md:items-end gap-3">
              <div className="flex-1">
                <label className="block text-xs font-medium text-slate-700 mb-1.5">
                  Google Sheet URL or Spreadsheet ID
                </label>
                <input
                  type="text"
                  value={sheetInput}
                  onChange={(e) => setSheetInput(e.target.value)}
                  placeholder="https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit"
                  className="w-full px-3 py-2 text-sm bg-white border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-slate-900"
                />
              </div>

              {!hasToken && (
                <button
                  type="button"
                  onClick={handleConnectSheets}
                  className="inline-flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium text-slate-900 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 whitespace-nowrap shrink-0 cursor-pointer"
                >
                  <FileSpreadsheet className="w-4 h-4 text-emerald-700" />
                  Connect Google Sheets
                </button>
              )}

              <button
                type="button"
                onClick={handleLoadSpreadsheet}
                disabled={loadingMeta || loadingRows || !extractSpreadsheetId(sheetInput)}
                className="inline-flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium text-white bg-slate-900 rounded-lg hover:bg-slate-800 whitespace-nowrap shrink-0 cursor-pointer disabled:opacity-50"
              >
                <RefreshCw className={`w-4 h-4 ${loadingMeta || loadingRows ? 'animate-spin' : ''}`} />
                {loadingMeta || loadingRows ? 'Loading Sheet...' : 'Load & Preview Sheet'}
              </button>
            </div>

            {meta && (
              <div className="flex flex-wrap items-center gap-4 pt-1">
                <div className="text-xs text-slate-600">
                  Spreadsheet: <strong className="text-slate-900">{meta.title}</strong>
                </div>
                <div className="flex items-center gap-2">
                  <label className="text-xs font-medium text-slate-700">Worksheet Tab:</label>
                  <select
                    value={selectedTab}
                    onChange={(e) => {
                      const tab = e.target.value;
                      setSelectedTab(tab);
                      loadRowsForTab(meta.spreadsheetId, tab);
                    }}
                    className="px-2.5 py-1.5 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-900"
                  >
                    {meta.sheetNames.map((tab) => (
                      <option key={tab} value={tab}>
                        {tab}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="border border-dashed border-slate-300 rounded-xl p-6 flex flex-col sm:flex-row items-center justify-between gap-4 bg-slate-50/70">
            <div className="space-y-1">
              <h3 className="text-sm font-semibold text-slate-900">Upload Employee Excel or CSV</h3>
              <p className="text-xs text-slate-600">
                Include Employee Code, Employee Name, Designation, Reporting Manager (name or email), and Email ID.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2.5 shrink-0">
              <button
                type="button"
                onClick={handleLoadAttachedCsv}
                className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-medium text-slate-800 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 whitespace-nowrap shrink-0 cursor-pointer"
              >
                <FileSpreadsheet className="w-4 h-4 text-emerald-700" />
                Load Attached Roster
              </button>
              <label className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-slate-900 rounded-lg hover:bg-slate-800 whitespace-nowrap shrink-0 cursor-pointer">
                <Upload className="w-4 h-4" />
                Choose .xlsx / .csv
                <input
                  type="file"
                  accept=".xlsx,.xls,.csv"
                  onChange={handleExcelUpload}
                  className="sr-only"
                />
              </label>
            </div>
          </div>
        )}

        {/* Column Mapping & Diff Preview */}
        {rawTable && (
          <div className="border-t border-slate-200 pt-6 space-y-5">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <h3 className="text-sm font-semibold text-slate-900">
                  Column Mapping ({rawTable.rows.length} rows detected)
                </h3>
                <p className="text-xs text-slate-500">
                  Verify which spreadsheet columns correspond to employee identity and reporting manager emails.
                </p>
              </div>
              <label className="inline-flex items-center gap-2 text-xs text-slate-700 cursor-pointer">
                <input
                  type="checkbox"
                  checked={markMissingResigned}
                  onChange={(e) => setMarkMissingResigned(e.target.checked)}
                  className="rounded border-slate-300 text-slate-900 focus:ring-slate-900"
                />
                Mark active employees absent from this sheet as Resigned
              </label>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
              {(
                [
                  ['employeeCode', 'Employee Code'],
                  ['name', 'Employee Name *'],
                  ['email', 'Email ID *'],
                  ['designation', 'Designation'],
                  ['managerEmail', 'Reporting Manager (Name/Email)'],
                  ['department', 'Department'],
                  ['status', 'Status (Active/Resigned)'],
                  ['joiningDate', 'Joining Date'],
                  ['isAdmin', 'HR Admin Flag'],
                ] as Array<[keyof ColumnMapping, string]>
              ).map(([key, label]) => (
                <div key={key}>
                  <label className="block text-xs font-medium text-slate-600 mb-1">{label}</label>
                  <select
                    value={mapping[key]}
                    onChange={(e) => setMapping((prev) => ({ ...prev, [key]: e.target.value }))}
                    className="w-full px-2.5 py-1.5 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-900"
                  >
                    <option value="">— Not Mapped —</option>
                    {rawTable.headers.map((h) => (
                      <option key={h} value={h}>
                        {h}
                      </option>
                    ))}
                  </select>
                </div>
              ))}
            </div>

            {diffPreview && (
              <div className="space-y-4">
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3.5">
                    <div className="flex items-center gap-1.5 text-xs font-medium text-emerald-800">
                      <UserPlus className="w-3.5 h-3.5" />
                      New Joinees
                    </div>
                    <div className="text-xl font-mono tabular-nums font-semibold text-emerald-900 mt-1">
                      {diffPreview.newJoinees.length}
                    </div>
                  </div>
                  <div className="bg-slate-50 border border-slate-200 rounded-lg p-3.5">
                    <div className="flex items-center gap-1.5 text-xs font-medium text-slate-700">
                      <UserCheck className="w-3.5 h-3.5" />
                      Profile / Manager Updates
                    </div>
                    <div className="text-xl font-mono tabular-nums font-semibold text-slate-900 mt-1">
                      {diffPreview.updated.length}
                    </div>
                  </div>
                  <div className="bg-red-50 border border-red-200 rounded-lg p-3.5">
                    <div className="flex items-center gap-1.5 text-xs font-medium text-red-800">
                      <UserMinus className="w-3.5 h-3.5" />
                      Resignees
                    </div>
                    <div className="text-xl font-mono tabular-nums font-semibold text-red-900 mt-1">
                      {diffPreview.resignees.length}
                    </div>
                  </div>
                  <div className="bg-slate-50 border border-slate-200 rounded-lg p-3.5">
                    <div className="text-xs font-medium text-slate-600">Unchanged</div>
                    <div className="text-xl font-mono tabular-nums font-semibold text-slate-900 mt-1">
                      {diffPreview.unchangedCount}
                    </div>
                  </div>
                </div>

                {diffPreview.warnings.length > 0 && (
                  <div className="bg-amber-50 border border-amber-200 rounded-lg p-3.5 space-y-1">
                    <div className="flex items-center gap-1.5 text-xs font-semibold text-amber-800">
                      <AlertTriangle className="w-4 h-4" />
                      Sheet Warnings ({diffPreview.warnings.length})
                    </div>
                    <ul className="text-xs text-amber-800 space-y-0.5 max-h-28 overflow-y-auto">
                      {diffPreview.warnings.map((w, i) => (
                        <li key={i}>{w}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {(diffPreview.newJoinees.length > 0 ||
                  diffPreview.updated.length > 0 ||
                  diffPreview.resignees.length > 0) ? (
                  <div className="border border-slate-200 rounded-lg overflow-hidden">
                    <div className="bg-slate-50 px-4 py-2.5 border-b border-slate-200 text-xs font-semibold text-slate-700">
                      Preview of Pending Directory Changes
                    </div>
                    <div className="max-h-56 overflow-y-auto divide-y divide-slate-200 text-xs">
                      {[...diffPreview.newJoinees, ...diffPreview.updated, ...diffPreview.resignees].map(
                        (item) => (
                          <div
                            key={item.employeeId}
                            className="px-4 py-2.5 flex flex-col sm:flex-row sm:items-center justify-between gap-2"
                          >
                            <div>
                              <span className="font-semibold text-slate-900">
                                {item.incoming.name}
                              </span>
                              <span className="text-slate-300 mx-1.5">·</span>
                              <span className="text-slate-600">{item.incoming.email}</span>
                              <span className="text-slate-300 mx-1.5">·</span>
                              <span className="text-slate-600">{item.incoming.designation}</span>
                            </div>
                            <span
                              className={`font-medium ${
                                item.changeType === 'new_joinee'
                                  ? 'text-emerald-700'
                                  : item.changeType === 'resignee'
                                    ? 'text-red-700'
                                    : 'text-slate-700'
                              }`}
                            >
                              {item.changes.join(' · ')}
                            </span>
                          </div>
                        )
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="flex items-center gap-2 text-xs text-emerald-700">
                    <CheckCircle2 className="w-4 h-4" />
                    <span>Directory is already in sync with this spreadsheet.</span>
                  </div>
                )}

                <div className="flex items-center justify-end gap-3">
                  <button
                    type="button"
                    onClick={() => setRawTable(null)}
                    className="px-4 py-2 text-xs font-medium text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 cursor-pointer"
                  >
                    Discard Preview
                  </button>
                  <button
                    type="button"
                    onClick={() => setConfirmOpen(true)}
                    disabled={diffPreview.resolvedRecords.length === 0}
                    className="px-4 py-2 text-xs font-medium text-white bg-slate-900 rounded-lg hover:bg-slate-800 cursor-pointer disabled:opacity-50"
                  >
                    Apply Sync Changes ({diffPreview.resolvedRecords.length} employees)
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </section>

      {/* Live Directory Table */}
      <section className="bg-white border border-slate-200 rounded-xl overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h2 className="text-base font-semibold text-slate-900">
              Synced Employee Directory ({filteredEmployees.length})
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Employees listed as a Reporting Manager automatically receive approval authority and login pop-ups.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            <div className="inline-flex items-center gap-1 p-1 bg-slate-100 border border-slate-200 rounded-lg">
              {(['active', 'resigned', 'all'] as const).map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => setStatusFilter(s)}
                  className={`px-2.5 py-1 text-xs font-medium rounded-md capitalize cursor-pointer ${
                    statusFilter === s
                      ? 'bg-white text-slate-900 shadow-xs'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  {s}
                </button>
              ))}
            </div>

            <div className="relative w-56">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search name, email, manager..."
                className="w-full pl-8 pr-3 py-1.5 text-xs bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-900"
              />
            </div>

            <button
              type="button"
              onClick={() =>
                setEditingEmp({
                  name: '',
                  email: '',
                  designation: '',
                  department: '',
                  managerEmail: '',
                  status: 'active',
                  joiningDate: '',
                  isAdmin: false,
                })
              }
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-slate-900 rounded-lg hover:bg-slate-800 whitespace-nowrap shrink-0 cursor-pointer"
            >
              <Plus className="w-3.5 h-3.5" />
              Add Employee
            </button>
          </div>
        </div>

        {filteredEmployees.length === 0 ? (
          <div className="p-8 text-center text-sm text-slate-500">
            No employees match the current filter. Link your Google Sheet or add employees above.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50/70 text-xs font-medium text-slate-600">
                  <th className="py-3 px-6">Employee</th>
                  <th className="py-3 px-4">Designation &amp; Dept</th>
                  <th className="py-3 px-4">Reporting Manager</th>
                  <th className="py-3 px-4">Authority</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-6 text-right">Edit</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 text-sm">
                {filteredEmployees.map((emp) => (
                  <tr key={emp.id} className="hover:bg-slate-50/70">
                    <td className="py-2.5 px-6">
                      <div className="font-medium text-slate-900">
                        {emp.employeeCode ? (
                          <span className="font-mono tabular-nums text-xs text-slate-500 mr-2">
                            {emp.employeeCode}
                          </span>
                        ) : null}
                        {emp.name}
                      </div>
                      <div className="text-xs text-slate-500">{emp.email}</div>
                    </td>
                    <td className="py-2.5 px-4">
                      <div className="text-slate-800">{emp.designation}</div>
                      {emp.department && (
                        <div className="text-xs text-slate-500">{emp.department}</div>
                      )}
                    </td>
                    <td className="py-2.5 px-4 text-xs text-slate-700">
                      {emp.managerEmail ? (
                        <>
                          <div className="font-medium text-slate-800">
                            {emp.managerName || emp.managerEmail}
                          </div>
                          {emp.managerName && emp.managerName !== emp.managerEmail && (
                            <div className="text-slate-500">{emp.managerEmail}</div>
                          )}
                        </>
                      ) : (
                        <span className="text-slate-400">Top-level / Unassigned</span>
                      )}
                    </td>
                    <td className="py-2.5 px-4 text-xs text-slate-600">
                      {[
                        emp.isManager ? 'Reporting Manager' : null,
                        emp.isAdmin ? 'HR Admin' : null,
                      ]
                        .filter(Boolean)
                        .join(' · ') || 'Employee'}
                    </td>
                    <td
                      className={`py-2.5 px-4 text-xs font-medium capitalize ${
                        emp.status === 'active' ? 'text-emerald-700' : 'text-red-700'
                      }`}
                    >
                      {emp.status}
                    </td>
                    <td className="py-2.5 px-6 text-right">
                      <button
                        type="button"
                        onClick={() => setEditingEmp(emp)}
                        className="text-xs font-medium text-slate-600 hover:text-slate-900 underline underline-offset-2 cursor-pointer"
                      >
                        Edit
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <ConfirmDialog
        open={confirmOpen}
        title="Confirm Employee Roster Sync"
        description={`Apply changes from ${activeSource === 'google_sheet' ? `Google Sheet "${meta?.title || 'Spreadsheet'}"` : 'uploaded Excel/CSV'} to the live employee directory?`}
        details={
          diffPreview
            ? [
                `• ${diffPreview.newJoinees.length} new joinee(s) will be onboarded with default leave balances.`,
                `• ${diffPreview.updated.length} existing employee(s) will have profile/manager lines updated.`,
                `• ${diffPreview.resignees.length} employee(s) will be marked Resigned (historical leave records preserved).`,
              ]
            : []
        }
        confirmLabel="Confirm & Sync Roster"
        busy={committing}
        onConfirm={handleConfirmCommit}
        onCancel={() => setConfirmOpen(false)}
      />

      {editingEmp && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/45 p-4"
          role="dialog"
          aria-modal="true"
        >
          <form
            onSubmit={handleSaveEmployeeModal}
            className="bg-white border border-slate-200 rounded-xl max-w-lg w-full p-6 space-y-4 shadow-xl"
          >
            <div className="flex items-start justify-between">
              <h3 className="text-base font-semibold text-slate-900">
                {editingEmp.id ? 'Edit Employee Record' : 'Add Employee Manually'}
              </h3>
              <button
                type="button"
                onClick={() => setEditingEmp(null)}
                className="text-slate-400 hover:text-slate-600 p-1 cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Employee Code</label>
                <input
                  type="text"
                  maxLength={VALIDATION_LIMITS.maxEmployeeCodeLength}
                  value={editingEmp.employeeCode || ''}
                  onChange={(e) => setEditingEmp((p) => ({ ...p, employeeCode: e.target.value }))}
                  placeholder="e.g., 1004"
                  className="w-full px-3 py-2 text-sm font-mono tabular-nums border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-900"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Full Name *</label>
                <input
                  type="text"
                  required
                  value={editingEmp.name || ''}
                  onChange={(e) => setEditingEmp((p) => ({ ...p, name: e.target.value }))}
                  className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-900"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Work Email *</label>
                <input
                  type="email"
                  required
                  disabled={Boolean(editingEmp.id)}
                  value={editingEmp.email || ''}
                  onChange={(e) => setEditingEmp((p) => ({ ...p, email: e.target.value }))}
                  className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg disabled:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-slate-900"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Designation *</label>
                <input
                  type="text"
                  required
                  value={editingEmp.designation || ''}
                  onChange={(e) => setEditingEmp((p) => ({ ...p, designation: e.target.value }))}
                  className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-900"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Department</label>
                <input
                  type="text"
                  value={editingEmp.department || ''}
                  onChange={(e) => setEditingEmp((p) => ({ ...p, department: e.target.value }))}
                  className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-900"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">
                  Reporting Manager Email
                </label>
                <input
                  type="email"
                  value={editingEmp.managerEmail || ''}
                  onChange={(e) => setEditingEmp((p) => ({ ...p, managerEmail: e.target.value }))}
                  placeholder="manager@company.com"
                  className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-900"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Status</label>
                <select
                  value={editingEmp.status || 'active'}
                  onChange={(e) =>
                    setEditingEmp((p) => ({ ...p, status: e.target.value as EmployeeStatus }))
                  }
                  className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-900"
                >
                  <option value="active">Active</option>
                  <option value="resigned">Resigned</option>
                </select>
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setEditingEmp(null)}
                className="px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={savingEmp}
                className="px-4 py-2 text-sm font-medium text-white bg-slate-900 rounded-lg hover:bg-slate-800 cursor-pointer disabled:opacity-60"
              >
                {savingEmp ? 'Saving...' : 'Save Employee'}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
};
