import React, { useState, useMemo } from 'react';
import {
  Plus,
  FileUp,
  Printer,
  FolderArchive,
  Search,
  ShieldCheck,
  Paperclip,
  CalendarPlus,
  Eye,
  EyeOff,
  FileText,
  ShieldAlert,
  Car,
  HeartPulse,
  LifeBuoy,
  Home,
  UserCheck,
  CreditCard,
  Trash2,
  Edit2,
  Calendar,
  AlertTriangle,
  Receipt,
  Layers,
  Check,
  AlertCircle,
  Sparkles,
} from 'lucide-react';
import { AppRow, RecType, UserProfile } from '../types';
import { longD, normAll, REC, stateOf, inr } from '../utils/calculations';
import { ItemBadge } from '../components/ItemBadge';
import { PersonFilter } from '../components/PersonFilter';
import { triggerPrint } from '../utils/exportImport';
import { downloadCalendarEvent } from '../utils/calendarExport';
import {
  getDocumentValidityStatus,
  hasPrescribedExpiry,
  DocumentValidityStatus,
  DOCUMENT_VALIDITY_RULES,
} from '../utils/documentValidity';

interface Props {
  rows: AppRow[];
  profile: UserProfile;
  selectedPerson: string;
  onSelectPerson: (person: string) => void;
  onAdd: (kind: 'rec', defaultCategory?: 'identity' | 'insurance') => void;
  onUpload: (kind: 'rec') => void;
  onEdit: (row: AppRow) => void;
  onDelete: (id: string, name?: string) => void;
  onViewAttachment?: (rowId: string, itemName: string) => void;
}

export const RecordsView: React.FC<Props> = ({
  rows,
  profile,
  selectedPerson,
  onSelectPerson,
  onAdd,
  onUpload,
  onEdit,
  onDelete,
  onViewAttachment,
}) => {
  // Sub-navigation: 'identity' (Official Identity Documents) vs 'insurance' (Insurance Policies)
  const [activeTab, setActiveTab] = useState<'identity' | 'insurance'>('identity');
  const [selectedType, setSelectedType] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<DocumentValidityStatus | 'all'>('all');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [revealedIds, setRevealedIds] = useState<Record<string, boolean>>({});

  // Toggle reveal for sensitive numbers (Aadhaar, PAN, Passport, Policy)
  const toggleReveal = (id: string) => {
    setRevealedIds((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  // Helper to mask sensitive identifiers
  const maskIdentifier = (num: string = '', isRevealed: boolean = false): string => {
    if (!num) return '—';
    if (isRevealed) return num;
    const clean = String(num).trim();
    if (clean.length <= 4) return '••••';
    // Preserve last 4 characters
    const lastFour = clean.slice(-4);
    const maskedPrefix = '•'.repeat(Math.min(clean.length - 4, 8));
    return `${maskedPrefix} ${lastFour}`.trim();
  };

  // All records
  const allRecRows = useMemo(() => {
    return rows.filter((r) => r.kind === 'rec');
  }, [rows]);

  // Segregate into Identity vs Insurance
  const { identityRows, insuranceRows } = useMemo(() => {
    const identities: AppRow[] = [];
    const insurances: AppRow[] = [];

    allRecRows.forEach((r) => {
      const d = r.data || {};
      const isInsurance =
        d.category === 'insurance' ||
        d.type === 'policy' ||
        d.type === 'insurance' ||
        Boolean(d.policyNumber || d.insurer || d.sumInsured || d.premium);

      if (isInsurance) {
        insurances.push(r);
      } else {
        identities.push(r);
      }
    });

    return { identityRows: identities, insuranceRows: insurances };
  }, [allRecRows]);

  const currentTabRows = activeTab === 'identity' ? identityRows : insuranceRows;

  // Filter by person
  const personFilteredRows = useMemo(() => {
    if (!selectedPerson) return currentTabRows;
    return currentTabRows.filter((r) => {
      const d = r.data || {};
      const holder = d.holder || d.policyholder || d.personName || '';
      return holder.trim() === selectedPerson;
    });
  }, [currentTabRows, selectedPerson]);

  // Validity statistics across person-filtered items
  const validityCounts = useMemo(() => {
    const counts: Record<DocumentValidityStatus, number> = {
      valid: 0,
      expiring_soon: 0,
      expired: 0,
      no_prescribed_expiry: 0,
      date_missing: 0,
    };
    personFilteredRows.forEach((r) => {
      const d = r.data || {};
      const val = getDocumentValidityStatus(
        d.type || (activeTab === 'insurance' ? 'insurance' : 'other'),
        d.expires,
        d.issued
      );
      counts[val.status] = (counts[val.status] || 0) + 1;
    });
    return counts;
  }, [personFilteredRows, activeTab]);

  // Filter by search, type & validity status
  const filteredRows = useMemo(() => {
    return personFilteredRows.filter((r) => {
      const d = r.data || {};
      if (selectedType !== 'all') {
        const itemType = (d.type || d.insuranceType || 'other').toLowerCase();
        if (itemType !== selectedType.toLowerCase()) return false;
      }
      if (statusFilter !== 'all') {
        const val = getDocumentValidityStatus(
          d.type || (activeTab === 'insurance' ? 'insurance' : 'other'),
          d.expires,
          d.issued
        );
        if (val.status !== statusFilter) return false;
      }
      if (searchTerm.trim()) {
        const term = searchTerm.toLowerCase();
        const title = (d.title || d.name || '').toLowerCase();
        const num = (d.number || d.policyNumber || '').toLowerCase();
        const holder = (d.holder || d.policyholder || '').toLowerCase();
        const notes = (d.notes || '').toLowerCase();
        const insurer = (d.insurer || '').toLowerCase();
        if (
          !title.includes(term) &&
          !num.includes(term) &&
          !holder.includes(term) &&
          !notes.includes(term) &&
          !insurer.includes(term)
        ) {
          return false;
        }
      }
      return true;
    });
  }, [personFilteredRows, selectedType, statusFilter, searchTerm, activeTab]);

  // Aggregate stats
  const identityAlerts = useMemo(() => {
    return identityRows.flatMap(normAll);
  }, [identityRows]);

  const expiredIdentityDocs = identityAlerts.filter((a) => stateOf(a) === 'overdue');
  const expiringSoonIdentityDocs = identityAlerts.filter((a) => ['today', 'soon'].includes(stateOf(a)));

  const insuranceAlerts = useMemo(() => {
    return insuranceRows.flatMap(normAll);
  }, [insuranceRows]);

  const renewalAlerts = insuranceAlerts.filter((a) => a.vk === 'exp');
  const premiumAlerts = insuranceAlerts.filter((a) => a.vk === 'due');

  return (
    <div className="space-y-6 pb-12">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-[#0F1B2D] dark:text-[#E8EDF5]">
              Official Records &amp; Documents
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-300 border border-amber-200 dark:border-amber-800">
              {allRecRows.length} Total
            </span>
          </div>
          <p className="text-xs sm:text-sm text-[#6F7E92] dark:text-[#8594AA] mt-0.5">
            Structured repository for personal identity documents and insurance policies with privacy masking.
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap no-print">
          <button
            onClick={triggerPrint}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium border border-[#DCE2EA] dark:border-[#25324A] bg-white dark:bg-[#131C2E] hover:border-[#0E7C86] text-[#0F1B2D] dark:text-[#E8EDF5] transition"
            title="Print or Save as PDF"
          >
            <Printer className="w-4 h-4" />
            <span className="hidden sm:inline">Print / PDF</span>
          </button>

          {profile.showUpload !== false && (
            <button
              onClick={() => onUpload('rec')}
              className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold border border-teal-400/50 bg-teal-50 dark:bg-teal-950/60 hover:bg-teal-100 dark:hover:bg-teal-900 text-teal-800 dark:text-teal-200 transition shadow-2xs cursor-pointer"
            >
              <FileUp className="w-4 h-4 text-[#0E7C86] dark:text-[#38bdf8]" />
              <span>Add from file (auto-detect)</span>
            </button>
          )}

          <button
            onClick={() => onAdd('rec', activeTab)}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold bg-[#0E7C86] hover:bg-[#128e9a] text-white transition shadow-sm cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>{activeTab === 'identity' ? 'Add Identity Document' : 'Add Insurance Policy'}</span>
          </button>
        </div>
      </div>

      {/* Sub-Section Navigation Tabs */}
      <div className="flex items-center gap-2 border-b border-gray-200 dark:border-gray-800 pb-2">
        <button
          onClick={() => {
            setActiveTab('identity');
            setSelectedType('all');
          }}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-xl font-bold text-xs sm:text-sm transition cursor-pointer ${
            activeTab === 'identity'
              ? 'bg-[#0E7C86] text-white shadow-xs'
              : 'bg-gray-100 dark:bg-gray-800/60 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
          }`}
        >
          <UserCheck className="w-4 h-4" />
          <span>Identity &amp; Personal Documents</span>
          <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-white/20">
            {identityRows.length}
          </span>
        </button>

        <button
          onClick={() => {
            setActiveTab('insurance');
            setSelectedType('all');
          }}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-xl font-bold text-xs sm:text-sm transition cursor-pointer ${
            activeTab === 'insurance'
              ? 'bg-[#0E7C86] text-white shadow-xs'
              : 'bg-gray-100 dark:bg-gray-800/60 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
          }`}
        >
          <HeartPulse className="w-4 h-4" />
          <span>Insurance Policies</span>
          <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-white/20">
            {insuranceRows.length}
          </span>
        </button>
      </div>

      <PersonFilter
        rows={rows}
        selectedPerson={selectedPerson}
        onSelectPerson={onSelectPerson}
      />

      {/* KPI Cards based on active tab */}
      {activeTab === 'identity' ? (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4">
          <div
            onClick={() => setStatusFilter('all')}
            className={`bg-white dark:bg-[#131C2E] border rounded-2xl p-4 shadow-xs cursor-pointer transition ${
              statusFilter === 'all'
                ? 'border-[#0E7C86] ring-2 ring-[#0E7C86]/20'
                : 'border-gray-200 dark:border-gray-800 hover:border-gray-300'
            }`}
          >
            <div className="text-[11px] font-bold uppercase tracking-wider text-gray-500 dark:text-gray-400">
              Total Documents
            </div>
            <div className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white mt-1">
              {identityRows.length}
            </div>
            <div className="text-xs text-gray-500 mt-0.5 truncate">
              Passports, DL, PAN &amp; Aadhaar
            </div>
          </div>

          <div
            onClick={() => setStatusFilter('valid')}
            className={`bg-white dark:bg-[#131C2E] border rounded-2xl p-4 shadow-xs cursor-pointer transition ${
              statusFilter === 'valid'
                ? 'border-emerald-500 ring-2 ring-emerald-500/20'
                : 'border-gray-200 dark:border-gray-800 hover:border-emerald-300'
            }`}
          >
            <div className="text-[11px] font-bold uppercase tracking-wider text-emerald-700 dark:text-emerald-400">
              Valid &amp; Lifelong
            </div>
            <div className="text-xl sm:text-2xl font-bold text-emerald-700 dark:text-emerald-300 mt-1">
              {validityCounts.valid + validityCounts.no_prescribed_expiry}
            </div>
            <div className="text-xs text-gray-500 mt-0.5 truncate">
              Active statutory records
            </div>
          </div>

          <div
            onClick={() => setStatusFilter(validityCounts.expired > 0 ? 'expired' : 'expiring_soon')}
            className={`bg-white dark:bg-[#131C2E] border rounded-2xl p-4 shadow-xs cursor-pointer transition ${
              validityCounts.expired > 0
                ? 'border-rose-300 dark:border-rose-900 bg-rose-50/20'
                : validityCounts.expiring_soon > 0
                ? 'border-amber-300 dark:border-amber-900 bg-amber-50/20'
                : 'border-gray-200 dark:border-gray-800'
            }`}
          >
            <div className="text-[11px] font-bold uppercase tracking-wider text-amber-700 dark:text-amber-400">
              Expiry Alerts
            </div>
            <div className="text-xl sm:text-2xl font-bold text-amber-700 dark:text-amber-300 mt-1">
              {validityCounts.expired + validityCounts.expiring_soon}
            </div>
            <div className="text-xs text-gray-500 mt-0.5 truncate">
              {validityCounts.expired} expired · {validityCounts.expiring_soon} soon
            </div>
          </div>

          <div
            onClick={() => setStatusFilter('date_missing')}
            className={`bg-white dark:bg-[#131C2E] border rounded-2xl p-4 shadow-xs cursor-pointer transition ${
              validityCounts.date_missing > 0
                ? 'border-rose-400 dark:border-rose-800 bg-rose-50/40 dark:bg-rose-950/30'
                : 'border-gray-200 dark:border-gray-800'
            } ${statusFilter === 'date_missing' ? 'ring-2 ring-rose-500/30' : ''}`}
          >
            <div className="text-[11px] font-bold uppercase tracking-wider text-rose-700 dark:text-rose-400 flex items-center gap-1">
              {validityCounts.date_missing > 0 && <AlertTriangle className="w-3 h-3 text-rose-600" />}
              <span>Date Missing</span>
            </div>
            <div className="text-xl sm:text-2xl font-bold text-rose-700 dark:text-rose-300 mt-1">
              {validityCounts.date_missing}
            </div>
            <div className="text-xs text-gray-500 mt-0.5 truncate">
              {validityCounts.date_missing > 0 ? 'Expiry date required' : 'All dates captured'}
            </div>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4">
          <div className="bg-white dark:bg-[#131C2E] border border-gray-200 dark:border-gray-800 rounded-2xl p-4 shadow-xs">
            <div className="text-[11px] font-bold uppercase tracking-wider text-gray-500 dark:text-gray-400">
              Active Policies
            </div>
            <div className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white mt-1">
              {insuranceRows.length}
            </div>
            <div className="text-xs text-gray-500 mt-0.5">
              Health, Vehicle, Life &amp; Accident Protection
            </div>
          </div>

          <div className="bg-white dark:bg-[#131C2E] border border-gray-200 dark:border-gray-800 rounded-2xl p-4 shadow-xs">
            <div className="text-[11px] font-bold uppercase tracking-wider text-purple-700 dark:text-purple-400">
              Policy Renewals Tracked
            </div>
            <div className="text-xl sm:text-2xl font-bold text-purple-700 dark:text-purple-300 mt-1">
              {renewalAlerts.length}
            </div>
            <div className="text-xs text-gray-500 mt-0.5">
              Coverage continuity alerts (Annual)
            </div>
          </div>

          <div className="bg-white dark:bg-[#131C2E] border border-gray-200 dark:border-gray-800 rounded-2xl p-4 shadow-xs">
            <div className="text-[11px] font-bold uppercase tracking-wider text-[#0E7C86] dark:text-[#3CB7C2]">
              Net Worth Segregation
            </div>
            <div className="text-xl sm:text-2xl font-bold text-[#0E7C86] dark:text-[#3CB7C2] mt-1">
              Strictly Excluded
            </div>
            <div className="text-xs text-gray-500 mt-0.5">
              Sums insured &amp; premiums never inflate assets
            </div>
          </div>
        </div>
      )}

      {/* Filter Chips & Search Bar */}
      <div className="space-y-2.5 no-print">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 max-w-full">
            <button
              onClick={() => setSelectedType('all')}
              className={`px-3 py-1.5 text-xs font-semibold rounded-full transition whitespace-nowrap ${
                selectedType === 'all'
                  ? 'bg-[#0E7C86] text-white shadow-2xs'
                  : 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300 hover:bg-gray-200'
              }`}
            >
              All Types <span>({personFilteredRows.length})</span>
            </button>

            {activeTab === 'identity' ? (
              ['passport', 'licence', 'pan', 'aadhaar'].map((t) => {
                const count = personFilteredRows.filter((r) => r.data?.type === t).length;
                if (count === 0 && selectedType !== t) return null;
                return (
                  <button
                    key={t}
                    onClick={() => setSelectedType(t)}
                    className={`px-3 py-1.5 text-xs font-semibold rounded-full transition whitespace-nowrap ${
                      selectedType === t
                        ? 'bg-[#0E7C86] text-white shadow-2xs'
                        : 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300 hover:bg-gray-200'
                    }`}
                  >
                    {REC[t] || t.toUpperCase()} ({count})
                  </button>
                );
              })
            ) : (
              ['medical', 'vehicle', 'term', 'home'].map((t) => {
                const count = personFilteredRows.filter((r) => {
                  const sub = (r.data?.insuranceType || '').toLowerCase();
                  return sub.includes(t);
                }).length;
                if (count === 0 && selectedType !== t) return null;
                return (
                  <button
                    key={t}
                    onClick={() => setSelectedType(t)}
                    className={`px-3 py-1.5 text-xs font-semibold rounded-full transition whitespace-nowrap ${
                      selectedType === t
                        ? 'bg-[#0E7C86] text-white shadow-2xs'
                        : 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300 hover:bg-gray-200'
                    }`}
                  >
                    {t.toUpperCase()} ({count})
                  </button>
                );
              })
            )}
          </div>

          <div className="relative w-full sm:w-64 flex-shrink-0">
            <Search className="absolute left-3 top-2.5 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder={activeTab === 'identity' ? 'Search identity docs...' : 'Search insurance policies...'}
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-xs bg-white dark:bg-[#131C2E] border border-gray-200 dark:border-gray-800 rounded-xl focus:outline-none focus:ring-1 focus:ring-[#0E7C86]"
            />
          </div>
        </div>

        {/* Statutory Validity Status Filters */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 max-w-full text-xs pt-1 border-t border-gray-100 dark:border-gray-800">
          <span className="text-[11px] font-bold text-gray-500 mr-1 flex items-center gap-1 flex-shrink-0">
            <span>Validity Status:</span>
          </span>
          <button
            onClick={() => setStatusFilter('all')}
            className={`px-2.5 py-1 text-xs font-medium rounded-lg transition whitespace-nowrap ${
              statusFilter === 'all'
                ? 'bg-slate-800 text-white dark:bg-slate-200 dark:text-slate-900 font-bold shadow-2xs'
                : 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300 hover:bg-gray-200'
            }`}
          >
            All Statuses ({personFilteredRows.length})
          </button>
          <button
            onClick={() => setStatusFilter('valid')}
            className={`px-2.5 py-1 text-xs font-medium rounded-lg transition whitespace-nowrap flex items-center gap-1 ${
              statusFilter === 'valid'
                ? 'bg-emerald-600 text-white font-bold shadow-2xs'
                : 'bg-emerald-50 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300 hover:bg-emerald-100'
            }`}
          >
            <Check className="w-3 h-3" />
            <span>Valid ({validityCounts.valid})</span>
          </button>
          <button
            onClick={() => setStatusFilter('expiring_soon')}
            className={`px-2.5 py-1 text-xs font-medium rounded-lg transition whitespace-nowrap flex items-center gap-1 ${
              statusFilter === 'expiring_soon'
                ? 'bg-amber-600 text-white font-bold shadow-2xs'
                : 'bg-amber-50 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300 hover:bg-amber-100'
            }`}
          >
            <AlertCircle className="w-3 h-3" />
            <span>Expiring Soon ({validityCounts.expiring_soon})</span>
          </button>
          <button
            onClick={() => setStatusFilter('expired')}
            className={`px-2.5 py-1 text-xs font-medium rounded-lg transition whitespace-nowrap flex items-center gap-1 ${
              statusFilter === 'expired'
                ? 'bg-rose-600 text-white font-bold shadow-2xs'
                : 'bg-rose-50 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300 hover:bg-rose-100'
            }`}
          >
            <AlertTriangle className="w-3 h-3" />
            <span>Expired ({validityCounts.expired})</span>
          </button>
          <button
            onClick={() => setStatusFilter('date_missing')}
            className={`px-2.5 py-1 text-xs font-medium rounded-lg transition whitespace-nowrap flex items-center gap-1 ${
              statusFilter === 'date_missing'
                ? 'bg-rose-700 text-white font-bold ring-2 ring-rose-400 shadow-2xs'
                : validityCounts.date_missing > 0
                ? 'bg-rose-100 text-rose-900 dark:bg-rose-950 dark:text-rose-200 font-bold border border-rose-300 animate-pulse'
                : 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400'
            }`}
          >
            <AlertCircle className="w-3 h-3 text-rose-500" />
            <span>Date Missing ({validityCounts.date_missing})</span>
          </button>
          <button
            onClick={() => setStatusFilter('no_prescribed_expiry')}
            className={`px-2.5 py-1 text-xs font-medium rounded-lg transition whitespace-nowrap flex items-center gap-1 ${
              statusFilter === 'no_prescribed_expiry'
                ? 'bg-slate-700 text-white font-bold shadow-2xs'
                : 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300 hover:bg-slate-200'
            }`}
          >
            <ShieldCheck className="w-3 h-3 text-teal-600" />
            <span>No Prescribed Expiry ({validityCounts.no_prescribed_expiry})</span>
          </button>
        </div>
      </div>

      {/* Main Records List */}
      <div className="space-y-3">
        {filteredRows.length === 0 ? (
          <div className="text-center py-12 bg-white dark:bg-[#131C2E] border border-dashed border-gray-200 dark:border-gray-800 rounded-3xl text-gray-500">
            <FolderArchive className="w-10 h-10 mx-auto opacity-40 mb-2" />
            <p className="text-sm font-semibold">
              No {activeTab === 'identity' ? 'identity documents' : 'insurance policies'} found matching your criteria.
            </p>
          </div>
        ) : (
          filteredRows.map((r) => {
            const d = r.data || {};
            const isRevealed = Boolean(revealedIds[r.id]);
            const alert = normAll(r)[0];
            const isInsurance = activeTab === 'insurance';

            const docNumber = d.number || d.policyNumber || d.docNumber || '';
            const maskedNumber = maskIdentifier(docNumber, isRevealed);

            // Document statutory validity status
            const validity = getDocumentValidityStatus(
              d.type || (isInsurance ? 'insurance' : 'other'),
              d.expires,
              d.issued
            );

            return (
              <div
                key={r.id}
                className="p-4 sm:p-5 rounded-2xl bg-white dark:bg-[#131C2E] border border-gray-200 dark:border-gray-800 hover:border-[#0E7C86]/40 transition shadow-2xs flex flex-col md:flex-row items-start md:items-center justify-between gap-4"
              >
                {/* Left: Info */}
                <div className="flex items-start gap-3.5 flex-1 min-w-0">
                  <div className="w-10 h-10 rounded-xl bg-gray-100 dark:bg-gray-800 flex items-center justify-center flex-shrink-0 text-[#0E7C86]">
                    {isInsurance ? (
                      (d.insuranceType || '').includes('vehicle') ? (
                        <Car className="w-5 h-5 text-indigo-500" />
                      ) : (
                        <HeartPulse className="w-5 h-5 text-rose-500" />
                      )
                    ) : d.type === 'passport' ? (
                      <FolderArchive className="w-5 h-5 text-blue-600" />
                    ) : (
                      <UserCheck className="w-5 h-5 text-teal-600" />
                    )}
                  </div>

                  <div className="space-y-1 min-w-0 flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="font-bold text-sm sm:text-base text-gray-900 dark:text-white truncate">
                        {d.title || d.insurer || (isInsurance ? 'Insurance Policy' : 'Document')}
                      </h3>

                      {/* Person badge */}
                      {(d.holder || d.policyholder) && (
                        <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-900">
                          {d.holder || d.policyholder}
                        </span>
                      )}

                      {/* Alert badge if actively overdue/due soon */}
                      {alert && <ItemBadge alert={alert} />}

                      {/* Document Statutory Validity Badges (Never label a passport Permanent!) */}
                      {!isInsurance && (
                        <>
                          {validity.status === 'valid' && (
                            <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-50 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                              <Check className="w-3 h-3 text-emerald-600" />
                              Valid
                            </span>
                          )}
                          {validity.status === 'expiring_soon' && (
                            <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-50 dark:bg-amber-950/50 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800">
                              <AlertCircle className="w-3 h-3 text-amber-600" />
                              {validity.label}
                            </span>
                          )}
                          {validity.status === 'expired' && (
                            <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-rose-100 dark:bg-rose-950 text-rose-800 dark:text-rose-200 border border-rose-300 dark:border-rose-800">
                              <AlertTriangle className="w-3 h-3 text-rose-600" />
                              Expired
                            </span>
                          )}
                          {validity.status === 'no_prescribed_expiry' && (
                            <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-300 dark:border-slate-700">
                              <ShieldCheck className="w-3 h-3 text-teal-600" />
                              No Prescribed Expiry
                            </span>
                          )}
                          {validity.status === 'date_missing' && (
                            <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-rose-50 dark:bg-rose-950/60 text-rose-700 dark:text-rose-300 border border-rose-300 dark:border-rose-800">
                              <AlertCircle className="w-3 h-3 text-rose-600" />
                              Expiry Date Required
                            </span>
                          )}
                        </>
                      )}
                    </div>

                    {/* Sensitive Identifier with Reveal Toggle */}
                    <div className="flex items-center gap-2 text-xs text-gray-600 dark:text-gray-300 flex-wrap">
                      <span className="text-gray-400">
                        {isInsurance ? 'Policy Number:' : 'Document ID:'}
                      </span>
                      <strong className="font-mono text-gray-900 dark:text-gray-100 bg-gray-100 dark:bg-gray-800 px-2 py-0.5 rounded">
                        {maskedNumber}
                      </strong>

                      {docNumber && (
                        <button
                          type="button"
                          onClick={() => toggleReveal(r.id)}
                          className="p-1 text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition"
                          title={isRevealed ? 'Mask number' : 'Reveal full number'}
                          aria-label={isRevealed ? 'Mask number' : 'Reveal full number'}
                        >
                          {isRevealed ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                        </button>
                      )}

                      {/* Insurance coverage & premium tags */}
                      {isInsurance && d.sumInsured && (
                        <>
                          <span>·</span>
                          <span className="text-purple-700 dark:text-purple-300 font-semibold">
                            Sum Insured / IDV: {inr(d.sumInsured)}
                          </span>
                        </>
                      )}

                      {isInsurance && d.premium && (
                        <>
                          <span>·</span>
                          <span className="text-gray-700 dark:text-gray-300">
                            Annual Premium: {inr(d.premium)}
                          </span>
                        </>
                      )}

                      {isInsurance && d.insuredPersons && (
                        <>
                          <span>·</span>
                          <span>Covered: {d.insuredPersons}</span>
                        </>
                      )}

                      {/* Issue date */}
                      {d.issued && (
                        <>
                          <span>·</span>
                          <span>Issued: {longD(d.issued)}</span>
                        </>
                      )}

                      {/* Identity Expiry & Validity dates */}
                      {!isInsurance && (
                        <>
                          {hasPrescribedExpiry(d.type) ? (
                            d.expires && !/permanent|no expiry/i.test(d.expires) ? (
                              <>
                                <span>·</span>
                                <span className={validity.status === 'expired' ? 'text-rose-600 dark:text-rose-400 font-bold' : ''}>
                                  Expires: {longD(d.expires)}
                                </span>
                              </>
                            ) : (
                              <>
                                <span>·</span>
                                <span className="text-rose-600 dark:text-rose-400 font-semibold flex items-center gap-0.5">
                                  <AlertCircle className="w-3 h-3 inline" />
                                  Expiry Date Not Recorded
                                </span>
                              </>
                            )
                          ) : null}
                        </>
                      )}

                      {d.issuingAuthority && (
                        <>
                          <span>·</span>
                          <span>Issuer: {d.issuingAuthority}</span>
                        </>
                      )}
                    </div>

                    {d.notes && (
                      <p className="text-[11px] text-gray-400 dark:text-gray-500 line-clamp-1">
                        {d.notes}
                      </p>
                    )}
                  </div>
                </div>

                {/* Right: Actions */}
                <div className="flex items-center justify-end gap-1.5 w-full md:w-auto pt-3 md:pt-0 border-t md:border-t-0 border-gray-100 dark:border-gray-800">
                  {d.attachmentName && onViewAttachment && (
                    <button
                      type="button"
                      onClick={() => onViewAttachment(d.attachmentName!, d.title || 'Record')}
                      className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-xl text-xs font-semibold text-[#0E7C86] bg-teal-50 dark:bg-teal-950/60 hover:bg-teal-100 border border-teal-200 dark:border-teal-800 transition"
                      title="View document attachment"
                    >
                      <Receipt className="w-3.5 h-3.5" />
                      <span>Attachment</span>
                    </button>
                  )}

                  {alert && (
                    <button
                      type="button"
                      onClick={() => downloadCalendarEvent(alert)}
                      className="p-2 rounded-xl text-gray-400 hover:text-[#0E7C86] hover:bg-gray-100 dark:hover:bg-gray-800 transition"
                      title="Add reminder to Calendar"
                    >
                      <CalendarPlus className="w-4 h-4" />
                    </button>
                  )}

                  <button
                    onClick={() => onEdit(r)}
                    className="p-2 rounded-xl text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 transition"
                    title="Edit record"
                  >
                    <Edit2 className="w-4 h-4" />
                  </button>

                  <button
                    onClick={() => onDelete(r.id, d.title || 'Record')}
                    className="p-2 rounded-xl text-gray-400 hover:text-rose-600 hover:bg-gray-100 dark:hover:bg-gray-800 transition"
                    title="Delete record"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
