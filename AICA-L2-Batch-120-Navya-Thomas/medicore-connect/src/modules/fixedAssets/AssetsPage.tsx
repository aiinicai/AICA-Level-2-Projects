import React, { useState } from 'react';
import {
  Building2,
  Plus,
  Eye,
  CheckCircle,
  AlertTriangle,
  Clock,
  Sparkles,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
  XCircle,
} from 'lucide-react';
import { getDb, updateDb, addAuditLog } from '../../core/storage';
import { AssetSourceLine, FixedAsset, TransactionStatus } from '../../core/types';
import { DataTable, ColumnDef } from '../../components/DataTable';
import { SummaryTiles, SummaryTileItem } from '../../components/SummaryTiles';
import { RightRail } from '../../components/RightRail';
import { ViewAccountingModal } from '../../components/ViewAccountingModal';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import { formatAED } from '../../core/currency';
import { getActiveUser } from '../../core/auth';
import { getNextAssetTag } from '../../core/sequences';
import { buildAssetCapitalisationAccounting, postToGL } from '../../core/postingEngine';
import { BUSINESS_UNITS } from '../../data/businessUnits';

interface AssetsPageProps {
  onNavigate: (route: string) => void;
  initialTab?: 'register' | 'additions';
}

export const AssetsPage: React.FC<AssetsPageProps> = ({ onNavigate, initialTab = 'additions' }) => {
  const db = getDb();
  const currentUser = getActiveUser();

  const [activeTab, setActiveTab] = useState<'additions' | 'register'>(initialTab);
  const [selectedBU, setSelectedBU] = useState<string>('All');
  const [additionStatusFilter, setAdditionStatusFilter] = useState<string | null>(null);
  const [prepareTarget, setPrepareTarget] = useState<AssetSourceLine | null>(null);
  const [capitalizeTarget, setCapitalizeTarget] = useState<AssetSourceLine | null>(null);
  const [viewAccountingNumber, setViewAccountingNumber] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  // Filter Source Lines
  const sourceLines = db.assetSourceLines.filter((l) => {
    if (selectedBU !== 'All' && l.businessUnit !== selectedBU) return false;
    if (additionStatusFilter && l.status !== additionStatusFilter) return false;
    return true;
  });

  // Filter Assets
  const registeredAssets = db.fixedAssets.filter((a) => {
    if (selectedBU !== 'All' && a.businessUnit !== selectedBU) return false;
    return true;
  });

  // Summary counts
  const incompleteCount = db.assetSourceLines.filter((l) => l.status === 'Incomplete').length;
  const exceptionCount = db.assetSourceLines.filter((l) => l.status === 'Exception').length;
  const readyCount = db.assetSourceLines.filter((l) => l.status === 'Ready to Post').length;
  const totalAssetsCount = db.fixedAssets.length;
  const octDepRun = db.depreciationRuns.find((r) => r.period === 'Oct-26');

  const summaryTiles: SummaryTileItem[] = [
    { id: 'Incomplete', label: 'Additions: Incomplete', count: incompleteCount, color: 'plum' },
    { id: 'Exception', label: 'Additions: Exceptions', count: exceptionCount, color: 'rose' },
    { id: 'Ready to Post', label: 'Ready to Post', count: readyCount, color: 'emerald' },
    { id: 'Register', label: 'Active Asset Register', count: totalAssetsCount, color: 'slate' },
    { id: 'Depreciation', label: 'Oct-26 Depreciation', count: octDepRun ? 1 : 0, tooltip: octDepRun ? 'Oct-26 Posted' : 'Ready to Run' },
  ];

  const handleTileSelect = (id: string | null) => {
    if (id === 'Register') {
      setActiveTab('register');
      setAdditionStatusFilter(null);
    } else if (id === 'Depreciation') {
      onNavigate('#/fixed-assets/depreciation');
    } else {
      setActiveTab('additions');
      setAdditionStatusFilter(id);
    }
  };

  // Capitalize Ready-to-Post Source Line (Checker approval flow)
  const handleCapitalizeConfirm = () => {
    if (!capitalizeTarget) return;

    const cat = db.assetCategories.find((c) => c.name === capitalizeTarget.categoryName) || db.assetCategories[2];
    const tag = capitalizeTarget.tagNumber || getNextAssetTag();

    const newAsset: FixedAsset = {
      id: `FA-${Date.now()}`,
      tagNumber: tag,
      name: capitalizeTarget.description,
      businessUnit: capitalizeTarget.businessUnit,
      department: capitalizeTarget.department || 'Clinical',
      category: cat.name,
      costAccount: cat.costAccount,
      accumDepAccount: cat.accumDepAccount,
      cost: capitalizeTarget.cost,
      salvageValue: 0,
      usefulLifeYears: cat.usefulLifeYears,
      inServiceDate: capitalizeTarget.inServiceDate,
      accumulatedDepreciation: 0,
      netBookValue: capitalizeTarget.cost,
      status: 'Active',
      sourceInvoiceNumber: capitalizeTarget.apInvoiceNumber,
    };

    // Subledger Entry: Dr Cost Account / Cr 1610 Asset Clearing
    const subEntry = buildAssetCapitalisationAccounting(newAsset, currentUser.userId);
    const postRes = postToGL(subEntry, {
      createdBy: currentUser.userId,
      approvedBy: currentUser.userId,
      category: 'Capitalisation',
    });

    if (postRes.success && postRes.journal) {
      updateDb((state) => {
        state.fixedAssets.unshift(newAsset);
        const line = state.assetSourceLines.find((l) => l.id === capitalizeTarget.id);
        if (line) {
          line.status = 'Capitalized';
        }
      });

      addAuditLog({
        entityType: 'FixedAsset',
        entityId: newAsset.id,
        action: 'APPROVE',
        userId: currentUser.userId,
        userName: currentUser.name,
        comments: `Capitalised asset ${newAsset.tagNumber} (${newAsset.name}) and relieved 1610 clearing via GL ${postRes.journal.number}`,
      });

      setActionMessage(
        `Successfully capitalised asset ${newAsset.tagNumber} (${newAsset.name}) into Corporate Asset Register. GL Journal ${postRes.journal.number} posted (Dr ${newAsset.costAccount} / Cr 1610 Asset Clearing).`
      );
    } else {
      setActionMessage(`Capitalisation Failed: ${postRes.errors?.join('; ')}`);
    }

    setCapitalizeTarget(null);
  };

  // Prepare Source Line (Maker flow)
  const handlePrepareSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!prepareTarget) return;

    updateDb((state) => {
      const line = state.assetSourceLines.find((l) => l.id === prepareTarget.id);
      if (line) {
        line.status = 'Ready to Post';
        line.categoryName = prepareTarget.categoryName || 'Medical Equipment';
        line.tagNumber = prepareTarget.tagNumber || getNextAssetTag();
        line.inServiceDate = prepareTarget.inServiceDate;
        line.exceptionReason = undefined;
        line.comments = 'Prepared by FA accountant; ready for capitalization posting.';
      }
    });

    addAuditLog({
      entityType: 'AssetSourceLine',
      entityId: prepareTarget.id,
      action: 'UPDATE',
      userId: currentUser.userId,
      userName: currentUser.name,
      comments: `Prepared source line for ${prepareTarget.description}. Tag: ${prepareTarget.tagNumber || 'Auto'}`,
    });

    setActionMessage(`Source line ${prepareTarget.description} prepared and moved to 'Ready to Post'.`);
    setPrepareTarget(null);
  };

  // Additions Queue Columns
  const additionsColumns: ColumnDef<AssetSourceLine>[] = [
    {
      key: 'description',
      header: 'Description',
      render: (l) => (
        <div>
          <span className="font-semibold text-gray-900 block">{l.description}</span>
          <span className="text-[10px] text-gray-400">
            Invoice: <span className="font-mono text-[#5B2C83]">{l.apInvoiceNumber}</span> &bull; PO: {l.poNumber || '—'}
          </span>
        </div>
      ),
    },
    {
      key: 'businessUnit',
      header: 'BU',
      width: '60px',
      render: (l) => <span className="font-semibold text-gray-800">{l.businessUnit}</span>,
    },
    {
      key: 'cost',
      header: 'Cost (AED)',
      align: 'right',
      width: '130px',
      render: (l) => <span className="font-mono font-bold text-gray-900">{formatAED(l.cost)}</span>,
      exportValue: (l) => l.cost,
    },
    {
      key: 'inServiceDate',
      header: 'In-Service Date',
      width: '110px',
    },
    {
      key: 'categoryName',
      header: 'Asset Category',
      width: '140px',
      render: (l) => (
        <span className="text-gray-700 font-medium">
          {l.categoryName || <em className="text-rose-500">Unassigned</em>}
        </span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      width: '120px',
      align: 'center',
      render: (l) => {
        let bg = 'bg-gray-100 text-gray-800 border-gray-300';
        if (l.status === 'Ready to Post') bg = 'bg-emerald-50 text-emerald-800 border-emerald-300';
        else if (l.status === 'Exception') bg = 'bg-rose-50 text-rose-800 border-rose-300';
        else if (l.status === 'Incomplete') bg = 'bg-amber-50 text-amber-800 border-amber-300';
        return (
          <span className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold border ${bg}`}>
            {l.status === 'Exception' && <AlertTriangle className="w-3 h-3 mr-1 text-rose-600 inline" />}
            {l.status}
          </span>
        );
      },
    },
    {
      key: 'actions',
      header: 'Actions',
      width: '140px',
      align: 'center',
      sortable: false,
      render: (l) => {
        if (l.status === 'Incomplete' || l.status === 'Exception') {
          return (
            <button
              onClick={() => setPrepareTarget({ ...l })}
              className="px-2 py-0.5 rounded bg-plum-100 text-[#5B2C83] hover:bg-[#5B2C83] hover:text-white font-semibold text-[11px] transition-colors"
            >
              Prepare Line
            </button>
          );
        }
        if (l.status === 'Ready to Post') {
          return (
            <button
              onClick={() => setCapitalizeTarget(l)}
              className="px-2.5 py-0.5 rounded bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-[11px] transition-colors"
            >
              Capitalise & Post
            </button>
          );
        }
        return <span className="text-emerald-700 font-semibold text-[11px]">Capitalized</span>;
      },
    },
  ];

  // Asset Register Columns
  const registerColumns: ColumnDef<FixedAsset>[] = [
    {
      key: 'tagNumber',
      header: 'Tag Number',
      width: '120px',
      render: (a) => <span className="font-mono font-bold text-[#5B2C83]">{a.tagNumber}</span>,
    },
    {
      key: 'name',
      header: 'Asset Description',
      render: (a) => (
        <div>
          <span className="font-semibold text-gray-900 block">{a.name}</span>
          <span className="text-[10px] text-gray-500">
            Category: {a.category} &bull; Dept: {a.department}
          </span>
        </div>
      ),
    },
    {
      key: 'businessUnit',
      header: 'BU',
      width: '60px',
      render: (a) => <span className="font-semibold text-gray-800">{a.businessUnit}</span>,
    },
    {
      key: 'cost',
      header: 'Cost (AED)',
      align: 'right',
      width: '130px',
      render: (a) => <span className="font-mono font-medium">{formatAED(a.cost)}</span>,
      exportValue: (a) => a.cost,
    },
    {
      key: 'accumulatedDepreciation',
      header: 'Accum. Dep. (AED)',
      align: 'right',
      width: '140px',
      render: (a) => <span className="font-mono text-gray-600">{formatAED(a.accumulatedDepreciation)}</span>,
      exportValue: (a) => a.accumulatedDepreciation,
    },
    {
      key: 'netBookValue',
      header: 'Net Book Value (AED)',
      align: 'right',
      width: '150px',
      render: (a) => <span className="font-mono font-bold text-[#3F1D5C]">{formatAED(a.netBookValue)}</span>,
      exportValue: (a) => a.netBookValue,
    },
    {
      key: 'inServiceDate',
      header: 'In-Service',
      width: '100px',
    },
    {
      key: 'status',
      header: 'Status',
      width: '90px',
      align: 'center',
      render: (a) => (
        <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-50 text-emerald-800 border border-emerald-300">
          {a.status}
        </span>
      ),
    },
  ];

  return (
    <div className="flex-1 flex overflow-hidden">
      {/* Main Work Area */}
      <div className="flex-1 flex flex-col p-6 overflow-y-auto">
        {/* Header Bar */}
        <div className="flex flex-wrap items-center justify-between gap-4 mb-5">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-lg bg-[#5B2C83] text-white flex items-center justify-center shadow-xs">
              <Building2 className="w-5 h-5 text-amber-300" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h1 className="text-xl font-bold text-gray-900 tracking-tight">Fixed Assets: Assets</h1>
                <span className="text-[11px] bg-plum-100 text-[#5B2C83] font-semibold px-2 py-0.5 rounded">
                  Book: MERIDIAN CORPORATE ASSETS – AED
                </span>
              </div>
              <p className="text-xs text-gray-500">
                Manage capital asset source additions from AP, asset registration, and straight-line depreciation.
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <label className="text-xs font-semibold text-gray-600">Business Unit:</label>
            <select
              value={selectedBU}
              onChange={(e) => setSelectedBU(e.target.value)}
              className="bg-white border border-gray-300 rounded-lg px-3 py-1.5 text-xs text-gray-800 font-medium focus:ring-2 focus:ring-[#5B2C83] focus:outline-none shadow-xs"
            >
              <option value="All">All Business Units (Consolidated)</option>
              {BUSINESS_UNITS.map((bu) => (
                <option key={bu.code} value={bu.code}>
                  {bu.code} &bull; {bu.name}
                </option>
              ))}
            </select>

            <button
              onClick={() => onNavigate('#/fixed-assets/depreciation')}
              className="bg-[#5B2C83] hover:bg-[#3F1D5C] text-white px-3.5 py-1.5 rounded-lg text-xs font-semibold shadow-xs flex items-center space-x-1.5 transition-colors"
            >
              <Sparkles className="w-4 h-4 text-amber-300" />
              <span>Run Depreciation (Oct-26)</span>
            </button>
          </div>
        </div>

        {actionMessage && (
          <div className="mb-4 p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center justify-between">
            <span>{actionMessage}</span>
            <button onClick={() => setActionMessage(null)} className="text-emerald-700 font-bold ml-2">
              &times;
            </button>
          </div>
        )}

        {/* Summary Tiles */}
        <SummaryTiles
          tiles={summaryTiles}
          selectedId={additionStatusFilter}
          onSelect={handleTileSelect}
        />

        {/* Tab Switcher */}
        <div className="flex space-x-2 border-b border-gray-200 mb-4">
          <button
            onClick={() => setActiveTab('additions')}
            className={`pb-2.5 px-3 text-xs font-bold border-b-2 transition-colors ${
              activeTab === 'additions'
                ? 'border-[#5B2C83] text-[#5B2C83]'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            Additions Queue ({db.assetSourceLines.filter((l) => l.status !== 'Capitalized').length})
          </button>
          <button
            onClick={() => setActiveTab('register')}
            className={`pb-2.5 px-3 text-xs font-bold border-b-2 transition-colors ${
              activeTab === 'register'
                ? 'border-[#5B2C83] text-[#5B2C83]'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            Asset Register ({db.fixedAssets.length} Active Assets)
          </button>
        </div>

        {/* Content based on Tab */}
        {activeTab === 'additions' ? (
          <DataTable
            title="Asset Source Lines Awaiting Validation"
            data={sourceLines}
            columns={additionsColumns}
            keyField="id"
            filterPlaceholder="Search source lines, description, AP invoice..."
          />
        ) : (
          <DataTable
            title="Meridian Corporate Fixed Asset Register"
            data={registeredAssets}
            columns={registerColumns}
            keyField="id"
            onViewAccounting={(a) => setViewAccountingNumber(a.tagNumber)}
            filterPlaceholder="Search asset tag, description, category..."
          />
        )}
      </div>

      {/* Right Rail */}
      <RightRail
        tasks={[
          { label: 'Prepare Source Lines', onClick: () => setActiveTab('additions') },
          { label: 'Run Oct-26 Depreciation', onClick: () => onNavigate('#/fixed-assets/depreciation') },
          { label: 'Asset Register Report', onClick: () => onNavigate('#/reports/fixed-assets-register') },
          { label: 'FA to GL Reconciliation', onClick: () => onNavigate('#/reports/reconciliations') },
        ]}
      />

      {/* Prepare Source Line Dialog */}
      {prepareTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs" onClick={() => setPrepareTarget(null)} />

          <div className="relative bg-white rounded-xl shadow-2xl border border-gray-200 max-w-lg w-full p-6 z-10 animate-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between pb-3 border-b border-gray-100 mb-4">
              <h3 className="font-bold text-base text-gray-900">Prepare Asset Source Line</h3>
              <button onClick={() => setPrepareTarget(null)} className="text-gray-400 hover:text-gray-600">
                <XCircle className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handlePrepareSubmit} className="space-y-4 text-xs">
              <div>
                <label className="block font-semibold text-gray-700 mb-1">Asset Description</label>
                <input
                  type="text"
                  value={prepareTarget.description}
                  onChange={(e) => setPrepareTarget({ ...prepareTarget, description: e.target.value })}
                  className="w-full p-2 border border-gray-300 rounded font-medium"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-gray-700 mb-1">Asset Category</label>
                  <select
                    value={prepareTarget.categoryName || 'Medical Equipment'}
                    onChange={(e) => setPrepareTarget({ ...prepareTarget, categoryName: e.target.value })}
                    className="w-full p-2 border border-gray-300 rounded font-medium"
                  >
                    {db.assetCategories.map((c) => (
                      <option key={c.id} value={c.name}>
                        {c.name} ({c.usefulLifeYears}y)
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block font-semibold text-gray-700 mb-1">In-Service Date</label>
                  <input
                    type="date"
                    value={prepareTarget.inServiceDate}
                    onChange={(e) => setPrepareTarget({ ...prepareTarget, inServiceDate: e.target.value })}
                    className="w-full p-2 border border-gray-300 rounded font-medium"
                    required
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-gray-700 mb-1">Capital Cost (AED)</label>
                  <input
                    type="text"
                    disabled
                    value={formatAED(prepareTarget.cost)}
                    className="w-full p-2 bg-gray-100 border border-gray-300 rounded font-mono font-bold"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-gray-700 mb-1">Tag Number (Optional)</label>
                  <input
                    type="text"
                    placeholder="Auto-assigned if blank"
                    value={prepareTarget.tagNumber || ''}
                    onChange={(e) => setPrepareTarget({ ...prepareTarget, tagNumber: e.target.value })}
                    className="w-full p-2 border border-gray-300 rounded font-mono"
                  />
                </div>
              </div>

              <div className="pt-3 border-t border-gray-100 flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setPrepareTarget(null)}
                  className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-[#5B2C83] hover:bg-[#3F1D5C] text-white rounded-lg font-semibold"
                >
                  Ready for Posting &rarr;
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Capitalize Confirmation */}
      {capitalizeTarget && (
        <ConfirmDialog
          isOpen={Boolean(capitalizeTarget)}
          onClose={() => setCapitalizeTarget(null)}
          onConfirm={handleCapitalizeConfirm}
          title={`Capitalise Asset into Register?`}
          message={`Are you sure you want to capitalise "${capitalizeTarget.description}" for AED ${formatAED(
            capitalizeTarget.cost
          )}? This will register the asset and post a GL entry Dr Cost Account / Cr 1610 Asset Clearing.`}
          type="approve"
          confirmLabel="Capitalise & Post to GL"
        />
      )}

      {/* View Accounting */}
      {viewAccountingNumber && (
        <ViewAccountingModal
          isOpen={Boolean(viewAccountingNumber)}
          onClose={() => setViewAccountingNumber(null)}
          documentNumber={viewAccountingNumber}
          sourceModule="Fixed Assets"
          onNavigateToJournal={() => onNavigate('#/general-accounting/journals')}
        />
      )}
    </div>
  );
};
