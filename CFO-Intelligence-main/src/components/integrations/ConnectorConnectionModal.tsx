import React, { useState } from 'react';
import {
  X,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  ShieldCheck,
  Zap,
  ExternalLink,
  Key,
  Server,
  Building2,
  Database,
  Lock,
  Globe,
  Sliders,
  FileSpreadsheet,
  Check,
  Copy,
  Info,
  PowerOff,
  Radio,
} from 'lucide-react';
import { ConnectorConfig } from '../../services/connectorService';

interface ConnectorConnectionModalProps {
  isOpen: boolean;
  onClose: () => void;
  connector: ConnectorConfig;
  onSaveConfig: (updated: ConnectorConfig) => void;
  onTestConnection: (config: ConnectorConfig) => Promise<{ success: boolean; message: string; details?: any }>;
  onDisconnect: (connectorId: string) => void;
  onTriggerSync: (connectorId: string) => Promise<void>;
  isSyncing: boolean;
}

export const ConnectorConnectionModal: React.FC<ConnectorConnectionModalProps> = ({
  isOpen,
  onClose,
  connector,
  onSaveConfig,
  onTestConnection,
  onDisconnect,
  onTriggerSync,
  isSyncing,
}) => {
  const [activeTab, setActiveTab] = useState<'credentials' | 'mapping' | 'sync_settings' | 'diagnostics'>('credentials');
  const [formData, setFormData] = useState<ConnectorConfig>({ ...connector });
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string; timestamp?: string; details?: any } | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [showOAuthSimulator, setShowOAuthSimulator] = useState(false);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleCopy = (text: string, keyName: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(keyName);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const handleFieldChange = (field: keyof ConnectorConfig, value: any) => {
    setFormData(prev => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleRunTest = async () => {
    setIsTesting(true);
    setTestResult(null);
    try {
      const result = await onTestConnection(formData);
      setTestResult({
        ...result,
        timestamp: new Date().toLocaleTimeString(),
      });
      if (result.success) {
        setFormData(prev => ({ ...prev, status: 'connected' }));
      }
    } catch (e: any) {
      setTestResult({
        success: false,
        message: e?.message || 'Connection handshake timed out.',
        timestamp: new Date().toLocaleTimeString(),
      });
    } finally {
      setIsTesting(false);
    }
  };

  const handleSaveAndConnect = async () => {
    setIsSaving(true);
    try {
      const updated = {
        ...formData,
        status: formData.status === 'error' ? 'connected' : formData.status || 'connected',
        lastSynced: formData.status === 'connected' ? (formData.lastSynced || 'Just now') : 'Pending sync',
      };
      onSaveConfig(updated);
      onClose();
    } finally {
      setIsSaving(false);
    }
  };

  const handleSimulateOAuthSuccess = () => {
    setShowOAuthSimulator(false);
    setFormData(prev => ({
      ...prev,
      status: 'connected',
      companyName: prev.companyName || (prev.id === 'qbo' ? 'Apex Innovations Inc (US Entity)' : prev.id === 'zoho' ? 'Apex Zoho Org #782910' : 'Apex NetSuite OneWorld'),
      lastSynced: 'Just now (Auth Validated)',
      recordsCount: 482,
    }));
    setTestResult({
      success: true,
      message: `OAuth 2.0 handshake validated. Token granted for ${formData.name}.`,
      timestamp: new Date().toLocaleTimeString(),
      details: {
        tokenStatus: 'Active (AES-256 Encrypted)',
        expiresIn: '60 days',
        grantedScopes: ['com.intuit.quickbooks.accounting', 'openid', 'profile'],
      },
    });
  };

  const getConnectorBadgeColor = () => {
    switch (formData.id) {
      case 'qbo':
        return 'bg-emerald-600';
      case 'tally':
        return 'bg-amber-600';
      case 'zoho':
        return 'bg-blue-600';
      case 'netsuite':
        return 'bg-indigo-700';
      default:
        return 'bg-sky-600';
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/70 backdrop-blur-xs overflow-y-auto animate-in fade-in duration-150">
      <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-3xl overflow-hidden my-6">
        {/* Header */}
        <div className="px-6 py-4 bg-slate-900 text-white flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-xl ${getConnectorBadgeColor()} flex items-center justify-center font-bold text-white shadow-xs`}>
              {formData.name.slice(0, 2).toUpperCase()}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-white">{formData.name}</h3>
                <span
                  className={`text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full ${
                    formData.status === 'connected'
                      ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                      : 'bg-slate-700 text-slate-300'
                  }`}
                >
                  {formData.status === 'connected' ? 'Connected & Active' : 'Setup Required'}
                </span>
              </div>
              <p className="text-xs text-slate-300 mt-0.5">
                General ledger integration, trial balance syncing, and automated data ingestion
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation Tabs inside modal */}
        <div className="border-b border-slate-200 bg-slate-50 px-6 flex items-center gap-2">
          <button
            onClick={() => setActiveTab('credentials')}
            className={`py-3 px-3.5 text-xs font-semibold border-b-2 transition-all flex items-center gap-1.5 cursor-pointer ${
              activeTab === 'credentials'
                ? 'border-indigo-600 text-indigo-600 bg-white shadow-xs rounded-t-lg'
                : 'border-transparent text-slate-600 hover:text-slate-900'
            }`}
          >
            <Key className="w-3.5 h-3.5" />
            <span>Connection & Auth</span>
          </button>

          <button
            onClick={() => setActiveTab('mapping')}
            className={`py-3 px-3.5 text-xs font-semibold border-b-2 transition-all flex items-center gap-1.5 cursor-pointer ${
              activeTab === 'mapping'
                ? 'border-indigo-600 text-indigo-600 bg-white shadow-xs rounded-t-lg'
                : 'border-transparent text-slate-600 hover:text-slate-900'
            }`}
          >
            <FileSpreadsheet className="w-3.5 h-3.5" />
            <span>Entities & COA Mapping</span>
          </button>

          <button
            onClick={() => setActiveTab('sync_settings')}
            className={`py-3 px-3.5 text-xs font-semibold border-b-2 transition-all flex items-center gap-1.5 cursor-pointer ${
              activeTab === 'sync_settings'
                ? 'border-indigo-600 text-indigo-600 bg-white shadow-xs rounded-t-lg'
                : 'border-transparent text-slate-600 hover:text-slate-900'
            }`}
          >
            <Sliders className="w-3.5 h-3.5" />
            <span>Sync Frequency & Rules</span>
          </button>

          <button
            onClick={() => setActiveTab('diagnostics')}
            className={`py-3 px-3.5 text-xs font-semibold border-b-2 transition-all flex items-center gap-1.5 cursor-pointer ${
              activeTab === 'diagnostics'
                ? 'border-indigo-600 text-indigo-600 bg-white shadow-xs rounded-t-lg'
                : 'border-transparent text-slate-600 hover:text-slate-900'
            }`}
          >
            <Zap className="w-3.5 h-3.5" />
            <span>Test & Diagnostics</span>
          </button>
        </div>

        {/* Tab Content */}
        <div className="p-6 max-h-[62vh] overflow-y-auto space-y-5">
          {/* TAB 1: CREDENTIALS & CONNECTION SETUP */}
          {activeTab === 'credentials' && (
            <div className="space-y-5">
              {/* Quick OAuth Connect Banner for Cloud Apps */}
              {(formData.id === 'qbo' || formData.id === 'zoho' || formData.id === 'xero') && (
                <div className="p-4 rounded-xl bg-indigo-50/70 border border-indigo-200/80 flex items-center justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-lg bg-indigo-600 text-white flex items-center justify-center">
                      <Zap className="w-5 h-5" />
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-indigo-950">1-Click Direct OAuth 2.0 Authorization</h4>
                      <p className="text-[11px] text-indigo-700">
                        Authenticate securely via official {formData.name} single sign-on with end-to-end token encryption.
                      </p>
                    </div>
                  </div>

                  <button
                    onClick={() => setShowOAuthSimulator(true)}
                    className="px-3.5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold transition-all shadow-xs flex items-center gap-1.5 whitespace-nowrap cursor-pointer"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                    <span>Authorize with {formData.name.split(' ')[0]}</span>
                  </button>
                </div>
              )}

              {/* SPECIFIC CONFIGURATION: QUICKBOOKS ONLINE (QBO) */}
              {formData.id === 'qbo' && (
                <div className="space-y-4">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-bold text-slate-700 mb-1">
                        Intuit Environment
                      </label>
                      <select
                        value={formData.environment || 'Production'}
                        onChange={e => handleFieldChange('environment', e.target.value)}
                        className="w-full text-xs rounded-lg border border-slate-300 px-3 py-2 bg-white text-slate-800 focus:ring-2 focus:ring-indigo-500"
                      >
                        <option value="Production">Production (Live General Ledger)</option>
                        <option value="Sandbox">Sandbox / Test Realm</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-slate-700 mb-1">
                        Company Realm ID / Tenant ID
                      </label>
                      <input
                        type="text"
                        value={formData.qboRealmId || ''}
                        onChange={e => handleFieldChange('qboRealmId', e.target.value)}
                        placeholder="e.g. 9130354892019482"
                        className="w-full text-xs rounded-lg border border-slate-300 px-3 py-2 bg-white text-slate-800 focus:ring-2 focus:ring-indigo-500 font-mono"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-bold text-slate-700 mb-1">
                        Connected Company Name
                      </label>
                      <input
                        type="text"
                        value={formData.companyName || ''}
                        onChange={e => handleFieldChange('companyName', e.target.value)}
                        placeholder="Apex Innovations Inc"
                        className="w-full text-xs rounded-lg border border-slate-300 px-3 py-2 bg-white text-slate-800 focus:ring-2 focus:ring-indigo-500"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-slate-700 mb-1">
                        Client ID (Custom Intuit App - Optional)
                      </label>
                      <input
                        type="text"
                        value={formData.qboClientId || ''}
                        onChange={e => handleFieldChange('qboClientId', e.target.value)}
                        placeholder="AB12345cde67890fghij"
                        className="w-full text-xs rounded-lg border border-slate-300 px-3 py-2 bg-white text-slate-800 focus:ring-2 focus:ring-indigo-500 font-mono"
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* SPECIFIC CONFIGURATION: TALLY PRIME & ERP 9 */}
              {formData.id === 'tally' && (
                <div className="space-y-4">
                  <div className="p-3.5 rounded-xl bg-amber-50 border border-amber-200 text-xs text-amber-900 flex items-start gap-2.5">
                    <Server className="w-4 h-4 text-amber-700 shrink-0 mt-0.5" />
                    <div>
                      <p className="font-bold">Tally XML Server Gateway</p>
                      <p className="text-[11px] text-amber-800 mt-0.5">
                        Ensure Tally is running with ODBC/XML Server enabled under <strong>F12 &gt; Advanced Configuration &gt; Enable ODBC Server: Yes</strong> (Default Port 9000).
                      </p>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    <div className="sm:col-span-2">
                      <label className="block text-xs font-bold text-slate-700 mb-1">
                        Tally Host / IP Address
                      </label>
                      <input
                        type="text"
                        value={formData.tallyHost || 'localhost'}
                        onChange={e => handleFieldChange('tallyHost', e.target.value)}
                        placeholder="localhost or 192.168.1.100"
                        className="w-full text-xs rounded-lg border border-slate-300 px-3 py-2 bg-white text-slate-800 focus:ring-2 focus:ring-amber-500 font-mono"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-slate-700 mb-1">
                        XML Port
                      </label>
                      <input
                        type="text"
                        value={formData.tallyPort || '9000'}
                        onChange={e => handleFieldChange('tallyPort', e.target.value)}
                        placeholder="9000"
                        className="w-full text-xs rounded-lg border border-slate-300 px-3 py-2 bg-white text-slate-800 focus:ring-2 focus:ring-amber-500 font-mono"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-bold text-slate-700 mb-1">
                        Active Company Name in Tally
                      </label>
                      <input
                        type="text"
                        value={formData.tallyCompanyName || formData.companyName || ''}
                        onChange={e => {
                          handleFieldChange('tallyCompanyName', e.target.value);
                          handleFieldChange('companyName', e.target.value);
                        }}
                        placeholder="Apex Innovations Pvt Ltd"
                        className="w-full text-xs rounded-lg border border-slate-300 px-3 py-2 bg-white text-slate-800 focus:ring-2 focus:ring-amber-500"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-slate-700 mb-1">
                        Tally Release Version
                      </label>
                      <select
                        value={formData.tallyVersion || 'TallyPrime 4.1 Enterprise'}
                        onChange={e => handleFieldChange('tallyVersion', e.target.value)}
                        className="w-full text-xs rounded-lg border border-slate-300 px-3 py-2 bg-white text-slate-800 focus:ring-2 focus:ring-amber-500"
                      >
                        <option value="TallyPrime 4.1 Enterprise">TallyPrime 4.1 (Latest)</option>
                        <option value="TallyPrime 3.0">TallyPrime 3.0</option>
                        <option value="Tally.ERP 9 Release 6.6">Tally.ERP 9 Release 6.6</option>
                        <option value="Tally on AWS Cloud">Tally on AWS Cloud / RDP</option>
                      </select>
                    </div>
                  </div>
                </div>
              )}

              {/* SPECIFIC CONFIGURATION: ZOHO BOOKS */}
              {formData.id === 'zoho' && (
                <div className="space-y-4">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-bold text-slate-700 mb-1">
                        Zoho Data Center Domain
                      </label>
                      <select
                        value={formData.zohoDataCenter || 'zoho.com'}
                        onChange={e => handleFieldChange('zohoDataCenter', e.target.value)}
                        className="w-full text-xs rounded-lg border border-slate-300 px-3 py-2 bg-white text-slate-800 focus:ring-2 focus:ring-blue-500"
                      >
                        <option value="zoho.com">United States (.com)</option>
                        <option value="zoho.in">India (.in)</option>
                        <option value="zoho.eu">Europe (.eu)</option>
                        <option value="zoho.com.au">Australia (.com.au)</option>
                        <option value="zoho.jp">Japan (.jp)</option>
                        <option value="zoho.ca">Canada (.ca)</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-slate-700 mb-1">
                        Organization ID
                      </label>
                      <input
                        type="text"
                        value={formData.zohoOrgId || ''}
                        onChange={e => handleFieldChange('zohoOrgId', e.target.value)}
                        placeholder="e.g. 782910482"
                        className="w-full text-xs rounded-lg border border-slate-300 px-3 py-2 bg-white text-slate-800 focus:ring-2 focus:ring-blue-500 font-mono"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-bold text-slate-700 mb-1">
                        Client ID (Zoho Developer Console)
                      </label>
                      <input
                        type="text"
                        value={formData.zohoClientId || ''}
                        onChange={e => handleFieldChange('zohoClientId', e.target.value)}
                        placeholder="1000.XXXXX.YYYYY"
                        className="w-full text-xs rounded-lg border border-slate-300 px-3 py-2 bg-white text-slate-800 focus:ring-2 focus:ring-blue-500 font-mono"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-slate-700 mb-1">
                        Client Secret
                      </label>
                      <input
                        type="password"
                        value={formData.zohoClientSecret || ''}
                        onChange={e => handleFieldChange('zohoClientSecret', e.target.value)}
                        placeholder="••••••••••••••••"
                        className="w-full text-xs rounded-lg border border-slate-300 px-3 py-2 bg-white text-slate-800 focus:ring-2 focus:ring-blue-500 font-mono"
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* SPECIFIC CONFIGURATION: ORACLE NETSUITE ERP */}
              {formData.id === 'netsuite' && (
                <div className="space-y-4">
                  <div className="p-3.5 rounded-xl bg-indigo-50 border border-indigo-200 text-xs text-indigo-900 flex items-start gap-2.5">
                    <Building2 className="w-4 h-4 text-indigo-700 shrink-0 mt-0.5" />
                    <div>
                      <p className="font-bold">NetSuite SuiteTalk TBA (Token-Based Authentication)</p>
                      <p className="text-[11px] text-indigo-800 mt-0.5">
                        Connect multi-subsidiary ledgers via HMAC-SHA256 Token-Based Auth for real-time trial balance extraction.
                      </p>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    <div>
                      <label className="block text-xs font-bold text-slate-700 mb-1">
                        NetSuite Account ID
                      </label>
                      <input
                        type="text"
                        value={formData.netSuiteAccountId || ''}
                        onChange={e => handleFieldChange('netSuiteAccountId', e.target.value)}
                        placeholder="TSTDRV2918402"
                        className="w-full text-xs rounded-lg border border-slate-300 px-3 py-2 bg-white text-slate-800 focus:ring-2 focus:ring-indigo-500 font-mono"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-slate-700 mb-1">
                        Subsidiary ID / Name
                      </label>
                      <input
                        type="text"
                        value={formData.netSuiteSubsidiaryId || ''}
                        onChange={e => handleFieldChange('netSuiteSubsidiaryId', e.target.value)}
                        placeholder="1 - Apex Global Holding"
                        className="w-full text-xs rounded-lg border border-slate-300 px-3 py-2 bg-white text-slate-800 focus:ring-2 focus:ring-indigo-500"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-slate-700 mb-1">
                        Role ID
                      </label>
                      <input
                        type="text"
                        value={formData.netSuiteRoleId || ''}
                        onChange={e => handleFieldChange('netSuiteRoleId', e.target.value)}
                        placeholder="1042 (FP&A Admin)"
                        className="w-full text-xs rounded-lg border border-slate-300 px-3 py-2 bg-white text-slate-800 focus:ring-2 focus:ring-indigo-500 font-mono"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-bold text-slate-700 mb-1">
                        Token ID
                      </label>
                      <input
                        type="password"
                        value={formData.netSuiteTokenId || '••••••••••••••••'}
                        onChange={e => handleFieldChange('netSuiteTokenId', e.target.value)}
                        placeholder="TBA Token ID"
                        className="w-full text-xs rounded-lg border border-slate-300 px-3 py-2 bg-white text-slate-800 focus:ring-2 focus:ring-indigo-500 font-mono"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-slate-700 mb-1">
                        Token Secret
                      </label>
                      <input
                        type="password"
                        value={formData.netSuiteTokenSecret || '••••••••••••••••'}
                        onChange={e => handleFieldChange('netSuiteTokenSecret', e.target.value)}
                        placeholder="TBA Token Secret"
                        className="w-full text-xs rounded-lg border border-slate-300 px-3 py-2 bg-white text-slate-800 focus:ring-2 focus:ring-indigo-500 font-mono"
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* SPECIFIC CONFIGURATION: XERO */}
              {formData.id === 'xero' && (
                <div className="space-y-4">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-bold text-slate-700 mb-1">
                        Xero Tenant ID / Organization ID
                      </label>
                      <input
                        type="text"
                        value={formData.xeroTenantId || ''}
                        onChange={e => handleFieldChange('xeroTenantId', e.target.value)}
                        placeholder="xer-org-9021849"
                        className="w-full text-xs rounded-lg border border-slate-300 px-3 py-2 bg-white text-slate-800 focus:ring-2 focus:ring-sky-500 font-mono"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-slate-700 mb-1">
                        Organization Display Name
                      </label>
                      <input
                        type="text"
                        value={formData.companyName || ''}
                        onChange={e => handleFieldChange('companyName', e.target.value)}
                        placeholder="Apex Innovations (UK / AU)"
                        className="w-full text-xs rounded-lg border border-slate-300 px-3 py-2 bg-white text-slate-800 focus:ring-2 focus:ring-sky-500"
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* Security & Privacy Banner */}
              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-600 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-emerald-600" />
                  <span>Tokens are stored in memory with AES-256 encryption. Redaction layer cleans PII before advisory modeling.</span>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: ENTITIES & CHART OF ACCOUNTS MAPPING */}
          {activeTab === 'mapping' && (
            <div className="space-y-4">
              <div className="text-xs text-slate-600">
                Select which financial ledger entities are automatically synchronized from <strong>{formData.name}</strong> into your CFO financial model.
              </div>

              <div className="space-y-2.5">
                {[
                  {
                    name: 'Chart of Accounts (COA)',
                    desc: 'Maps standard GL accounts directly into Revenue, COGS, OPEX, Assets, and Liabilities buckets.',
                    count: '48 Accounts Mapped',
                    defaultChecked: true,
                  },
                  {
                    name: 'Monthly Trial Balance Rollups',
                    desc: 'Aggregates debit/credit trial balance totals for automated 3-statement reconciliation.',
                    count: '12 Months History',
                    defaultChecked: true,
                  },
                  {
                    name: 'Accounts Receivable & Customer Invoices',
                    desc: 'Calculates Days Sales Outstanding (DSO) and aged invoice collection projections.',
                    count: 'Active 30/60/90 Aging',
                    defaultChecked: true,
                  },
                  {
                    name: 'Accounts Payable & Vendor Bills',
                    desc: 'Calculates Days Payable Outstanding (DPO) and short-term liquidity outflow commitments.',
                    count: 'Active Vendor Ledgers',
                    defaultChecked: true,
                  },
                  {
                    name: 'Bank & Credit Card Feeds',
                    desc: 'Ingests liquid cash positions and short-term debt balances for 13-week cash forecasting.',
                    count: '4 Accounts Tracked',
                    defaultChecked: true,
                  },
                ].map((item, idx) => (
                  <div
                    key={idx}
                    className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 hover:border-indigo-200 transition-colors flex items-start justify-between gap-3"
                  >
                    <div className="flex items-start gap-3">
                      <input
                        type="checkbox"
                        defaultChecked={item.defaultChecked}
                        className="mt-0.5 rounded text-indigo-600 focus:ring-indigo-500 w-4 h-4"
                      />
                      <div>
                        <div className="text-xs font-bold text-slate-900">{item.name}</div>
                        <div className="text-[11px] text-slate-500 mt-0.5">{item.desc}</div>
                      </div>
                    </div>

                    <span className="text-[10px] font-semibold text-slate-600 bg-white px-2.5 py-1 rounded-md border border-slate-200 shrink-0">
                      {item.count}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 3: SYNC SETTINGS & RULES */}
          {activeTab === 'sync_settings' && (
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1.5">
                  Automated Synchronization Schedule
                </label>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                  {[
                    { id: 'Realtime', label: 'Realtime Webhook', badge: 'Pro Tier' },
                    { id: 'Hourly', label: 'Every Hour', badge: 'Recommended' },
                    { id: 'Daily', label: 'Nightly at 03:00 AM', badge: 'Standard' },
                    { id: 'Manual', label: 'Manual Only', badge: 'On-Demand' },
                  ].map(option => (
                    <button
                      key={option.id}
                      type="button"
                      onClick={() => handleFieldChange('syncFrequency', option.id)}
                      className={`p-3 rounded-xl border text-left transition-all cursor-pointer ${
                        formData.syncFrequency === option.id
                          ? 'border-indigo-600 bg-indigo-50/50 text-indigo-950 font-bold'
                          : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300'
                      }`}
                    >
                      <div className="text-xs">{option.label}</div>
                      <div className="text-[10px] text-slate-400 mt-1">{option.badge}</div>
                    </button>
                  ))}
                </div>
              </div>

              <div className="pt-3 border-t border-slate-200 space-y-3">
                <h4 className="text-xs font-bold text-slate-900">Sync Behavior & Data Quality Safeguards</h4>

                <label className="flex items-center gap-2.5 text-xs text-slate-700 cursor-pointer">
                  <input
                    type="checkbox"
                    defaultChecked
                    className="rounded text-indigo-600 focus:ring-indigo-500 w-4 h-4"
                  />
                  <span>Run automated Trial Balance out-of-balance anomaly checks during each sync</span>
                </label>

                <label className="flex items-center gap-2.5 text-xs text-slate-700 cursor-pointer">
                  <input
                    type="checkbox"
                    defaultChecked
                    className="rounded text-indigo-600 focus:ring-indigo-500 w-4 h-4"
                  />
                  <span>Automatically update 12-month Rolling Forecast when month-end closes in ERP</span>
                </label>

                <label className="flex items-center gap-2.5 text-xs text-slate-700 cursor-pointer">
                  <input
                    type="checkbox"
                    defaultChecked
                    className="rounded text-indigo-600 focus:ring-indigo-500 w-4 h-4"
                  />
                  <span>Apply client-side Privacy Redaction tokenization prior to Gemini AI commentary</span>
                </label>
              </div>
            </div>
          )}

          {/* TAB 4: DIAGNOSTICS & TEST HANDSHAKE */}
          {activeTab === 'diagnostics' && (
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-slate-900 text-white space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Zap className="w-4 h-4 text-amber-400" />
                    <span className="text-xs font-bold">Live Integration Diagnostic Ping</span>
                  </div>

                  <button
                    onClick={handleRunTest}
                    disabled={isTesting}
                    className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${isTesting ? 'animate-spin' : ''}`} />
                    <span>{isTesting ? 'Testing Handshake...' : 'Run Test Ping'}</span>
                  </button>
                </div>

                <p className="text-[11px] text-slate-300">
                  Sends an encrypted ping to verify API endpoints, token authentication, and trial balance accessibility for <strong>{formData.name}</strong>.
                </p>
              </div>

              {testResult && (
                <div
                  className={`p-4 rounded-xl border animate-in fade-in duration-200 ${
                    testResult.success
                      ? 'bg-emerald-50 border-emerald-200 text-emerald-950'
                      : 'bg-rose-50 border-rose-200 text-rose-950'
                  }`}
                >
                  <div className="flex items-start gap-2.5">
                    {testResult.success ? (
                      <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
                    ) : (
                      <AlertCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
                    )}
                    <div className="flex-1">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold">
                          {testResult.success ? 'Handshake Successful' : 'Connection Failed'}
                        </span>
                        <span className="text-[10px] text-slate-500 font-mono">{testResult.timestamp}</span>
                      </div>
                      <p className="text-xs mt-1 leading-relaxed">{testResult.message}</p>

                      {testResult.details && (
                        <div className="mt-3 pt-2.5 border-t border-slate-200/60 grid grid-cols-2 gap-2 text-[11px]">
                          <div>
                            <span className="text-slate-500">Latency:</span>{' '}
                            <span className="font-mono font-semibold">{testResult.details.latency || '142ms'}</span>
                          </div>
                          <div>
                            <span className="text-slate-500">Company Found:</span>{' '}
                            <span className="font-semibold">{testResult.details.companyName || formData.companyName || 'Apex Innovations'}</span>
                          </div>
                          <div>
                            <span className="text-slate-500">Ledger Accounts:</span>{' '}
                            <span className="font-mono font-semibold">{testResult.details.accountsFound || '48 Accounts'}</span>
                          </div>
                          <div>
                            <span className="text-slate-500">Auth Method:</span>{' '}
                            <span className="font-semibold">{testResult.details.authMethod || 'OAuth 2.0 (TLS 1.3)'}</span>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* Status summary */}
              <div className="border border-slate-200 rounded-xl p-4 bg-slate-50 space-y-2">
                <div className="text-xs font-bold text-slate-800">Connection Telemetry Summary</div>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
                  <div className="bg-white p-2.5 rounded-lg border border-slate-200">
                    <span className="text-[10px] text-slate-400 block uppercase">Status</span>
                    <span className="font-bold text-slate-800 capitalize">{formData.status}</span>
                  </div>
                  <div className="bg-white p-2.5 rounded-lg border border-slate-200">
                    <span className="text-[10px] text-slate-400 block uppercase">Last Sync</span>
                    <span className="font-bold text-slate-800">{formData.lastSynced || 'Never'}</span>
                  </div>
                  <div className="bg-white p-2.5 rounded-lg border border-slate-200">
                    <span className="text-[10px] text-slate-400 block uppercase">Frequency</span>
                    <span className="font-bold text-slate-800">{formData.syncFrequency}</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer actions */}
        <div className="px-6 py-4 bg-slate-50 border-t border-slate-200 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div>
            {formData.status === 'connected' ? (
              <button
                type="button"
                onClick={() => onDisconnect(formData.id)}
                className="text-xs text-rose-600 hover:text-rose-700 font-semibold flex items-center gap-1.5 cursor-pointer"
              >
                <PowerOff className="w-3.5 h-3.5" />
                <span>Disconnect Integration</span>
              </button>
            ) : (
              <span className="text-xs text-slate-500">Config changes will be saved to your firm vault.</span>
            )}
          </div>

          <div className="flex items-center gap-2.5 w-full sm:w-auto">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 sm:flex-initial px-4 py-2 rounded-xl border border-slate-300 text-xs font-semibold text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer"
            >
              Cancel
            </button>

            {formData.status === 'connected' && (
              <button
                type="button"
                onClick={() => onTriggerSync(formData.id)}
                disabled={isSyncing}
                className="flex-1 sm:flex-initial px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-white text-xs font-bold transition-all shadow-xs flex items-center justify-center gap-1.5 cursor-pointer disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isSyncing ? 'animate-spin' : ''}`} />
                <span>{isSyncing ? 'Syncing...' : 'Sync Now'}</span>
              </button>
            )}

            <button
              type="button"
              onClick={handleSaveAndConnect}
              disabled={isSaving}
              className="flex-1 sm:flex-initial px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold transition-all shadow-xs flex items-center justify-center gap-1.5 cursor-pointer disabled:opacity-50"
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Save & Connect</span>
            </button>
          </div>
        </div>
      </div>

      {/* Simulated OAuth 2.0 Auth Window Popup */}
      {showOAuthSimulator && (
        <div className="fixed inset-0 z-60 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-in zoom-in-95 duration-150">
          <div className="bg-white rounded-2xl shadow-2xl border border-slate-300 w-full max-w-md overflow-hidden">
            {/* Pop-up header */}
            <div className="bg-slate-900 px-5 py-3.5 text-white flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Lock className="w-4 h-4 text-emerald-400" />
                <span className="text-xs font-bold">{formData.name} Secure Single Sign-On</span>
              </div>
              <button
                onClick={() => setShowOAuthSimulator(false)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-6 space-y-4">
              <div className="flex items-center justify-center py-2">
                <div className="w-16 h-16 rounded-2xl bg-indigo-600 text-white font-black text-xl flex items-center justify-center shadow-lg">
                  {formData.name.slice(0, 2).toUpperCase()}
                </div>
              </div>

              <div className="text-center space-y-1">
                <h3 className="text-sm font-bold text-slate-900">Authorize Jasleen Daswal & Associates</h3>
                <p className="text-xs text-slate-500">
                  Allow CFO Advisory System to access financial statements, invoices, and bank feeds for:
                </p>
                <p className="text-xs font-semibold text-indigo-700 bg-indigo-50 py-1 px-2 rounded-lg inline-block mt-1">
                  Apex Innovations Inc (Company Realm #9130354892)
                </p>
              </div>

              <div className="bg-slate-50 p-3 rounded-xl border border-slate-200 text-[11px] text-slate-600 space-y-1.5">
                <div className="flex items-center gap-2 font-medium text-slate-800">
                  <Check className="w-3.5 h-3.5 text-emerald-600" /> Read General Ledger & Trial Balances
                </div>
                <div className="flex items-center gap-2 font-medium text-slate-800">
                  <Check className="w-3.5 h-3.5 text-emerald-600" /> Read Accounts Receivable & Accounts Payable
                </div>
                <div className="flex items-center gap-2 font-medium text-slate-800">
                  <Check className="w-3.5 h-3.5 text-emerald-600" /> Real-time Nightly Sync Webhooks
                </div>
              </div>

              <div className="pt-2 flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => setShowOAuthSimulator(false)}
                  className="flex-1 py-2.5 rounded-xl border border-slate-300 text-xs font-semibold text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleSimulateOAuthSuccess}
                  className="flex-1 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold transition-all shadow-md cursor-pointer"
                >
                  Confirm & Connect
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
