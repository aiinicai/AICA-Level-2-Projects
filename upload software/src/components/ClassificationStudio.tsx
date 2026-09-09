import React, { useState } from 'react';
import {
  CheckSquare,
  Search,
  Filter,
  Sparkles,
  CheckCircle,
  AlertCircle,
  HelpCircle,
  ArrowRight,
  RefreshCw,
  Trash2,
  Layers,
  ChevronDown,
  ArrowUpDown,
  Info,
  BookmarkCheck,
  Bookmark,
  ShieldCheck,
  X,
} from 'lucide-react';
import {
  BalanceSheetHeadConfig,
  LedgerItem,
  PLCategory,
  TargetStatementType,
} from '../types/accounting';
import {
  saveRuleFromLedger,
  bulkSaveRules,
  getSavedClassificationRules,
  formatClassificationNature,
  getSavedRulesMap,
  deleteSavedClassificationRule,
} from '../utils/classificationRulesService';
import { SavedRulesModal } from './SavedRulesModal';

interface ClassificationStudioProps {
  ledgers: LedgerItem[];
  heads: BalanceSheetHeadConfig[];
  onUpdateLedger: (updatedLedger: LedgerItem) => void;
  onBulkUpdateLedgers: (ledgerIds: string[], updates: Partial<LedgerItem>) => void;
  onReclassifyAll: () => void;
  onPurgeNonLedgers: () => void;
  onNavigateToTab: (tab: any) => void;
}

export const ClassificationStudio: React.FC<ClassificationStudioProps> = ({
  ledgers,
  heads,
  onUpdateLedger,
  onBulkUpdateLedgers,
  onReclassifyAll,
  onPurgeNonLedgers,
  onNavigateToTab,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState<string>('ALL');
  const [selectedLedgerIds, setSelectedLedgerIds] = useState<string[]>([]);
  const [isAiClassifying, setIsAiClassifying] = useState(false);
  const [isSavedRulesModalOpen, setIsSavedRulesModalOpen] = useState(false);
  const [savedRulesCount, setSavedRulesCount] = useState<number>(() => getSavedClassificationRules().length);
  const [ruleSavedToast, setRuleSavedToast] = useState<{
    ledgerName: string;
    nature: string;
    head: string;
  } | null>(null);

  const [rulesMap, setRulesMap] = useState<Record<string, any>>(() => getSavedRulesMap());

  const refreshSavedRules = () => {
    const count = getSavedClassificationRules().length;
    setSavedRulesCount(count);
    setRulesMap(getSavedRulesMap());
  };

  // Bulk actions state
  const [bulkHeadCode, setBulkHeadCode] = useState<string>('');
  const [bulkPLCategory, setBulkPLCategory] = useState<PLCategory | ''>('');

  const activeHeads = heads.filter(h => h.active).sort((a, b) => a.displayOrder - b.displayOrder);

  // Filter ledgers
  const filteredLedgers = ledgers.filter(l => {
    const matchesSearch =
      l.ledgerName.toLowerCase().includes(searchTerm.toLowerCase()) ||
      l.originalGroup.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (l.subHead && l.subHead.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (l.savedRuleNature && l.savedRuleNature.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (l.confidenceReason && l.confidenceReason.toLowerCase().includes(searchTerm.toLowerCase()));

    if (!matchesSearch) return false;

    if (filterType === 'SAVED_RULES') {
      return !!l.hasSavedRule || !!rulesMap[l.ledgerName.toLowerCase().trim()];
    }
    if (filterType === 'NEEDS_REVIEW') {
      return l.status === 'REVIEW_NEEDED' || l.confidence === 'LOW' || l.targetType === 'UNCLASSIFIED';
    }
    if (filterType === 'BALANCE_SHEET') return l.targetType === 'BALANCE_SHEET';
    if (filterType === 'PROFIT_AND_LOSS') return l.targetType === 'PROFIT_AND_LOSS';
    if (filterType === 'DIRECT_EXPENSE') return l.targetType === 'PROFIT_AND_LOSS' && l.plCategory === 'DIRECT_EXPENSE';
    if (filterType === 'INDIRECT_EXPENSE') return l.targetType === 'PROFIT_AND_LOSS' && l.plCategory === 'INDIRECT_EXPENSE';
    if (filterType === 'DIRECT_INCOME') return l.targetType === 'PROFIT_AND_LOSS' && l.plCategory === 'DIRECT_INCOME';
    if (filterType === 'INDIRECT_INCOME') return l.targetType === 'PROFIT_AND_LOSS' && l.plCategory === 'INDIRECT_INCOME';
    if (filterType === 'LIABILITY') return l.natureDrCr === 'Cr' && l.targetType === 'BALANCE_SHEET';
    if (filterType === 'ASSET') return l.natureDrCr === 'Dr' && l.targetType === 'BALANCE_SHEET';

    return true;
  });

  const toggleSelectAll = () => {
    if (selectedLedgerIds.length === filteredLedgers.length) {
      setSelectedLedgerIds([]);
    } else {
      setSelectedLedgerIds(filteredLedgers.map(l => l.id));
    }
  };

  const toggleSelectLedger = (id: string) => {
    if (selectedLedgerIds.includes(id)) {
      setSelectedLedgerIds(selectedLedgerIds.filter(i => i !== id));
    } else {
      setSelectedLedgerIds([...selectedLedgerIds, id]);
    }
  };

  const handleHeadChange = (ledger: LedgerItem, newHeadCode: string) => {
    if (!newHeadCode) {
      onUpdateLedger({
        ...ledger,
        targetType: 'UNCLASSIFIED',
        headCode: undefined,
        mainHead: undefined,
        subHead: undefined,
        scheduleNo: undefined,
        status: 'REVIEW_NEEDED',
        confidence: 'LOW',
        confidenceReason: 'Manually marked as unclassified',
        hasSavedRule: false,
        savedRuleNature: undefined,
        isUserModified: true,
      });
      deleteSavedClassificationRule(ledger.ledgerName);
      refreshSavedRules();
      return;
    }

    const selectedHead = heads.find(h => h.code === newHeadCode);
    if (!selectedHead) return;

    const natureStr = formatClassificationNature('BALANCE_SHEET', selectedHead);

    const updated: LedgerItem = {
      ...ledger,
      targetType: 'BALANCE_SHEET',
      headCode: selectedHead.code,
      mainHead: selectedHead.mainHead,
      subHead: selectedHead.subHead,
      scheduleNo: selectedHead.scheduleNo,
      plCategory: undefined,
      status: 'CONFIRMED',
      confidence: 'HIGH',
      confidenceReason: `Manually mapped to Schedule ${selectedHead.scheduleNo} - ${selectedHead.subHead} (${selectedHead.nature})`,
      hasSavedRule: true,
      savedRuleNature: natureStr,
      isUserModified: true,
    };

    onUpdateLedger(updated);
    saveRuleFromLedger(updated, heads);
    refreshSavedRules();

    setRuleSavedToast({
      ledgerName: ledger.ledgerName,
      nature: selectedHead.nature,
      head: `Schedule ${selectedHead.scheduleNo} (${selectedHead.subHead})`,
    });
    setTimeout(() => {
      setRuleSavedToast(null);
    }, 5000);
  };

  const handlePLCategoryChange = (ledger: LedgerItem, plCat: PLCategory) => {
    const natureStr = formatClassificationNature('PROFIT_AND_LOSS', undefined, plCat);

    const updated: LedgerItem = {
      ...ledger,
      targetType: 'PROFIT_AND_LOSS',
      plCategory: plCat,
      headCode: undefined,
      mainHead: undefined,
      subHead: undefined,
      scheduleNo: undefined,
      status: 'CONFIRMED',
      confidence: 'HIGH',
      confidenceReason: `Manually mapped to P&L ${plCat.replace('_', ' ')}`,
      hasSavedRule: true,
      savedRuleNature: natureStr,
      isUserModified: true,
    };

    onUpdateLedger(updated);
    saveRuleFromLedger(updated, heads);
    refreshSavedRules();

    setRuleSavedToast({
      ledgerName: ledger.ledgerName,
      nature: plCat.replace(/_/g, ' '),
      head: 'Profit & Loss Statement',
    });
    setTimeout(() => {
      setRuleSavedToast(null);
    }, 5000);
  };

  const handleApplyBulkHead = () => {
    if (!bulkHeadCode || selectedLedgerIds.length === 0) return;
    const selectedHead = heads.find(h => h.code === bulkHeadCode);
    if (!selectedHead) return;

    const natureStr = formatClassificationNature('BALANCE_SHEET', selectedHead);

    const updates: Partial<LedgerItem> = {
      targetType: 'BALANCE_SHEET',
      headCode: selectedHead.code,
      mainHead: selectedHead.mainHead,
      subHead: selectedHead.subHead,
      scheduleNo: selectedHead.scheduleNo,
      plCategory: undefined,
      status: 'CONFIRMED',
      confidence: 'HIGH',
      confidenceReason: `Bulk mapped to Schedule ${selectedHead.scheduleNo} - ${selectedHead.subHead} (${selectedHead.nature})`,
      hasSavedRule: true,
      savedRuleNature: natureStr,
      isUserModified: true,
    };

    onBulkUpdateLedgers(selectedLedgerIds, updates);

    const updatedLedgers = ledgers
      .filter(l => selectedLedgerIds.includes(l.id))
      .map(l => ({ ...l, ...updates } as LedgerItem));
    bulkSaveRules(updatedLedgers, heads);
    refreshSavedRules();

    setRuleSavedToast({
      ledgerName: `${selectedLedgerIds.length} Selected Ledgers`,
      nature: selectedHead.nature,
      head: `Schedule ${selectedHead.scheduleNo} (${selectedHead.subHead})`,
    });
    setTimeout(() => {
      setRuleSavedToast(null);
    }, 5000);

    setSelectedLedgerIds([]);
  };

  const handleApplyBulkPL = () => {
    if (!bulkPLCategory || selectedLedgerIds.length === 0) return;
    const cat = bulkPLCategory as PLCategory;
    const natureStr = formatClassificationNature('PROFIT_AND_LOSS', undefined, cat);

    const updates: Partial<LedgerItem> = {
      targetType: 'PROFIT_AND_LOSS',
      plCategory: cat,
      headCode: undefined,
      mainHead: undefined,
      subHead: undefined,
      scheduleNo: undefined,
      status: 'CONFIRMED',
      confidence: 'HIGH',
      confidenceReason: `Bulk mapped to P&L ${cat.replace('_', ' ')}`,
      hasSavedRule: true,
      savedRuleNature: natureStr,
      isUserModified: true,
    };

    onBulkUpdateLedgers(selectedLedgerIds, updates);

    const updatedLedgers = ledgers
      .filter(l => selectedLedgerIds.includes(l.id))
      .map(l => ({ ...l, ...updates } as LedgerItem));
    bulkSaveRules(updatedLedgers, heads);
    refreshSavedRules();

    setRuleSavedToast({
      ledgerName: `${selectedLedgerIds.length} Selected Ledgers`,
      nature: cat.replace(/_/g, ' '),
      head: 'Profit & Loss Statement',
    });
    setTimeout(() => {
      setRuleSavedToast(null);
    }, 5000);

    setSelectedLedgerIds([]);
  };

  const handleRemoveSavedRule = (ledger: LedgerItem) => {
    deleteSavedClassificationRule(ledger.ledgerName);
    onUpdateLedger({
      ...ledger,
      hasSavedRule: false,
      savedRuleNature: undefined,
    });
    refreshSavedRules();
  };

  const handleRunAiClassification = async () => {
    const unclassified = ledgers.filter(
      l => l.targetType === 'UNCLASSIFIED' || l.status === 'REVIEW_NEEDED' || l.confidence === 'LOW'
    );

    if (unclassified.length === 0) {
      alert('All ledgers are already classified with high confidence!');
      return;
    }

    setIsAiClassifying(true);
    try {
      const response = await fetch('/api/ai/classify-assistant', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ledgers: unclassified,
          heads: activeHeads,
        }),
      });

      if (!response.ok) throw new Error('AI Classification server error');
      const data = await response.json();

      if (data.suggestions && Array.isArray(data.suggestions)) {
        data.suggestions.forEach((sug: any) => {
          const original = ledgers.find(l => l.ledgerName === sug.ledgerName || l.id === sug.ledgerId);
          if (original) {
            if (sug.suggestedHeadCode) {
              const matchedHead = heads.find(h => h.code === sug.suggestedHeadCode);
              if (matchedHead) {
                onUpdateLedger({
                  ...original,
                  targetType: 'BALANCE_SHEET',
                  headCode: matchedHead.code,
                  mainHead: matchedHead.mainHead,
                  subHead: matchedHead.subHead,
                  scheduleNo: matchedHead.scheduleNo,
                  status: 'CONFIRMED',
                  confidence: (sug.confidence?.toUpperCase() as any) || 'MEDIUM',
                  confidenceReason: `AI CA Engine: ${sug.reasoning || 'Mapped per ICAI Non-Corporate Guidance'}`,
                });
              }
            } else if (sug.nature === 'Income' || sug.nature === 'Expense') {
              const plCat: PLCategory = sug.nature === 'Income' ? 'INDIRECT_INCOME' : 'INDIRECT_EXPENSE';
              onUpdateLedger({
                ...original,
                targetType: 'PROFIT_AND_LOSS',
                plCategory: plCat,
                status: 'CONFIRMED',
                confidence: (sug.confidence?.toUpperCase() as any) || 'MEDIUM',
                confidenceReason: `AI CA Engine: ${sug.reasoning || 'Mapped per ICAI Non-Corporate Guidance'}`,
              });
            }
          }
        });
      }
    } catch (err) {
      console.error('AI classify error:', err);
    } finally {
      setIsAiClassifying(false);
    }
  };

  const unclassifiedCount = ledgers.filter(
    l => l.targetType === 'UNCLASSIFIED' || l.status === 'REVIEW_NEEDED' || l.confidence === 'LOW'
  ).length;

  return (
    <div className="space-y-4" id="classification-studio-container">
      {/* Studio Header Card */}
      <div className="bg-[#141414] text-[#E4E3E0] p-4 border border-[#141414]">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2">
              <CheckSquare className="w-4 h-4 text-[#A3A29E]" />
              <h2 className="text-sm font-bold font-mono uppercase tracking-wider text-white">
                Sheet 3: TB Classification & ICAI Schedule Mapping Studio
              </h2>
            </div>
            <p className="text-[11.5px] text-[#A3A29E] mt-1 max-w-2xl">
              Every trial balance ledger is mapped to an ICAI Non-Corporate statutory schedule (Schedules 1 to 14) or Trading & Profit & Loss category. Automatic rule matching classifies accounts seamlessly.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => setIsSavedRulesModalOpen(true)}
              title="View and manage saved ledger classification rules & statutory natures"
              className="inline-flex items-center px-2.5 py-1 bg-[#1c2921] hover:bg-[#25392d] text-[#86efac] text-[11px] font-mono border border-[#86efac]/40 transition shadow-xs"
              id="btn-manage-saved-rules"
            >
              <BookmarkCheck className="w-3.5 h-3.5 mr-1 text-[#86efac]" />
              <span>SAVED RULES ({savedRulesCount})</span>
            </button>

            <button
              onClick={onReclassifyAll}
              title="Re-run the enhanced ICAI classification rule engine on all ledgers"
              className="inline-flex items-center px-2.5 py-1 bg-[#222222] hover:bg-[#333333] text-white text-[11px] font-mono border border-white/20 transition"
              id="btn-studio-reclassify-all"
            >
              <RefreshCw className="w-3 h-3 mr-1 text-[#A3A29E]" />
              <span>RE-RUN ENGINE</span>
            </button>

            <button
              onClick={onPurgeNonLedgers}
              title="Remove non-ledger rows or general particulars from the ledger list"
              className="inline-flex items-center px-2.5 py-1 bg-[#222222] hover:bg-[#fee2e2] hover:text-[#991b1b] text-[#A3A29E] text-[11px] font-mono border border-white/20 transition"
              id="btn-studio-purge"
            >
              <Trash2 className="w-3 h-3 mr-1" />
              <span>PURGE NON-LEDGERS</span>
            </button>

            <button
              onClick={handleRunAiClassification}
              disabled={isAiClassifying}
              className="inline-flex items-center px-3 py-1 bg-[#262135] hover:bg-[#342d48] text-[#c4b5fd] text-[11px] font-mono border border-[#a78bfa]/40 transition disabled:opacity-50"
              id="btn-ai-auto-classify"
            >
              <Sparkles className="w-3.5 h-3.5 mr-1 text-[#a78bfa]" />
              {isAiClassifying ? 'ANALYZING...' : 'AI CLASSIFIER'}
            </button>

            <button
              onClick={() => onNavigateToTab('profit-and-loss')}
              className="inline-flex items-center px-3 py-1 bg-[#E4E3E0] hover:bg-white text-[#141414] text-[11px] font-mono font-bold border border-[#141414] transition"
            >
              <span>P&L STATEMENT</span>
              <ArrowRight className="w-3 h-3 ml-1" />
            </button>
          </div>
        </div>

        {/* Filter Pills */}
        <div className="flex flex-wrap gap-1.5 mt-3 pt-3 border-t border-white/10 text-xs">
          {[
            { id: 'ALL', label: `ALL LEDGERS (${ledgers.length})` },
            {
              id: 'SAVED_RULES',
              label: `SAVED RULES (${ledgers.filter(l => l.hasSavedRule || rulesMap[l.ledgerName.toLowerCase().trim()]).length})`,
              highlight: true,
            },
            {
              id: 'NEEDS_REVIEW',
              label: `NEEDS REVIEW (${unclassifiedCount})`,
              badge: unclassifiedCount > 0 ? 'alert' : 'ok',
            },
            { id: 'BALANCE_SHEET', label: `BALANCE SHEET (${ledgers.filter(l => l.targetType === 'BALANCE_SHEET').length})` },
            { id: 'PROFIT_AND_LOSS', label: `P&L STATEMENT (${ledgers.filter(l => l.targetType === 'PROFIT_AND_LOSS').length})` },
            { id: 'DIRECT_EXPENSE', label: `DIRECT EXPENSES / PURCHASES (${ledgers.filter(l => l.plCategory === 'DIRECT_EXPENSE').length})` },
            { id: 'INDIRECT_EXPENSE', label: `INDIRECT EXPENSES (${ledgers.filter(l => l.plCategory === 'INDIRECT_EXPENSE').length})` },
            { id: 'DIRECT_INCOME', label: `SALES / REVENUE (${ledgers.filter(l => l.plCategory === 'DIRECT_INCOME').length})` },
          ].map(f => (
            <button
              key={f.id}
              onClick={() => setFilterType(f.id)}
              className={`px-2.5 py-1 text-[10.5px] font-mono border transition ${
                filterType === f.id
                  ? 'bg-[#E4E3E0] text-[#141414] border-[#E4E3E0] font-bold'
                  : f.highlight
                  ? 'bg-[#1e293b] border-[#86efac]/40 text-[#86efac] hover:bg-[#334155]'
                  : 'bg-[#222222] border-white/10 text-[#A3A29E] hover:text-white'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {/* Auto-Save & Rule Confirmation Banner */}
      {ruleSavedToast && (
        <div className="bg-[#f0fdf4] border border-[#86efac] text-[#166534] p-3 flex items-center justify-between text-xs font-mono animate-in fade-in">
          <div className="flex items-center space-x-2">
            <BookmarkCheck className="w-4 h-4 text-[#166534] shrink-0" />
            <span>
              <strong>Rule Persisted:</strong> Classification nature for &quot;{ruleSavedToast.ledgerName}&quot; saved as <strong>{ruleSavedToast.nature}</strong> against <strong>{ruleSavedToast.head}</strong>. Subsequent imports will automatically respect this mapping.
            </span>
          </div>
          <button
            onClick={() => setRuleSavedToast(null)}
            className="text-[#166534] hover:text-[#14532d] p-0.5 ml-2"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Bulk Action Toolbar if selected */}
      {selectedLedgerIds.length > 0 && (
        <div className="bg-[#141414] text-white p-3 flex flex-wrap items-center justify-between gap-3 border border-[#141414]">
          <div className="flex items-center space-x-2 text-xs">
            <span className="font-bold bg-[#E4E3E0] text-[#141414] font-mono px-2 py-0.5 text-[11px]">
              {selectedLedgerIds.length} SELECTED
            </span>
            <span className="text-[#A3A29E] font-mono text-[11px]">BULK MAP SELECTED ITEMS:</span>
          </div>

          <div className="flex flex-wrap items-center gap-2 text-xs">
            {/* Map to BS Head */}
            <div className="flex items-center space-x-1">
              <select
                value={bulkHeadCode}
                onChange={e => setBulkHeadCode(e.target.value)}
                className="bg-[#222222] border border-white/20 px-2 py-1 text-xs font-mono text-white"
              >
                <option value="">SELECT BS SCHEDULE...</option>
                {activeHeads.map(h => (
                  <option key={h.code} value={h.code}>
                    SCH {h.scheduleNo} - {h.subHead} ({h.nature})
                  </option>
                ))}
              </select>
              <button
                onClick={handleApplyBulkHead}
                disabled={!bulkHeadCode}
                className="px-2.5 py-1 bg-[#15803d] hover:bg-[#16a34a] text-white text-xs font-mono font-bold disabled:opacity-40"
              >
                ASSIGN BS
              </button>
            </div>

            <span className="text-[#5E5E5E] font-mono">|</span>

            {/* Map to P&L Category */}
            <div className="flex items-center space-x-1">
              <select
                value={bulkPLCategory}
                onChange={e => setBulkPLCategory(e.target.value as any)}
                className="bg-[#222222] border border-white/20 px-2 py-1 text-xs font-mono text-white"
              >
                <option value="">SELECT P&L CATEGORY...</option>
                <option value="DIRECT_INCOME">DIRECT INCOME (SALES/TURNOVER)</option>
                <option value="DIRECT_EXPENSE">DIRECT EXPENSE (PURCHASE/MFG)</option>
                <option value="INDIRECT_INCOME">INDIRECT INCOME (INTEREST/DISCOUNT)</option>
                <option value="INDIRECT_EXPENSE">INDIRECT EXPENSE (ADMIN/SALARIES)</option>
              </select>
              <button
                onClick={handleApplyBulkPL}
                disabled={!bulkPLCategory}
                className="px-2.5 py-1 bg-[#1d4ed8] hover:bg-[#2563eb] text-white text-xs font-mono font-bold disabled:opacity-40"
              >
                ASSIGN P&L
              </button>
            </div>

            <button
              onClick={() => setSelectedLedgerIds([])}
              className="text-[11px] font-mono text-[#A3A29E] hover:text-white underline ml-2"
            >
              [CLEAR]
            </button>
          </div>
        </div>
      )}

      {/* Main Classification Table */}
      <div className="bg-[#F5F4F0] border border-[#141414]/20 overflow-hidden" id="table-classification">
        {/* Table Search Header */}
        <div className="p-3 border-b border-[#141414]/20 bg-[#ECEAE5] flex items-center justify-between">
          <div className="relative w-72">
            <Search className="w-3 h-3 absolute left-2.5 top-2.5 text-[#5E5E5E]" />
            <input
              type="text"
              placeholder="Search ledger name, group, schedule, or reason..."
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              className="pl-7 pr-2.5 py-1 bg-white border border-[#141414] text-xs font-mono w-full focus:outline-none"
            />
          </div>
          <span className="text-[11px] font-mono text-[#5E5E5E]">
            SHOWING <strong className="text-[#141414]">{filteredLedgers.length}</strong> OF {ledgers.length}
          </span>
        </div>

        <div className="overflow-x-auto max-h-[640px]">
          <table className="w-full text-left text-xs border-collapse">
            <thead className="bg-[#ECEAE5] text-[#141414] font-mono text-[11px] uppercase tracking-wider sticky top-0 z-10 border-b border-[#141414]">
              <tr>
                <th className="py-2 px-2.5 w-10 text-center border-r border-[#141414]/20">
                  <input
                    type="checkbox"
                    checked={selectedLedgerIds.length === filteredLedgers.length && filteredLedgers.length > 0}
                    onChange={toggleSelectAll}
                    className="accent-[#141414]"
                  />
                </th>
                <th className="py-2 px-3 border-r border-[#141414]/20">Ledger Name</th>
                <th className="py-2 px-3 w-36 border-r border-[#141414]/20">ERP Group</th>
                <th className="py-2 px-3 w-28 text-right border-r border-[#141414]/20">TB Net (₹)</th>
                <th className="py-2 px-3 w-14 text-center border-r border-[#141414]/20">Dr/Cr</th>
                <th className="py-2 px-3 w-36 border-r border-[#141414]/20">Target Statement</th>
                <th className="py-2 px-3 w-60 border-r border-[#141414]/20">Assigned Head / Schedule</th>
                <th className="py-2 px-3">Classification Rationale</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#141414]/15 bg-white">
              {filteredLedgers.map(l => {
                const isSelected = selectedLedgerIds.includes(l.id);
                const netAmt = Math.abs(l.debit - l.credit);

                return (
                  <tr
                    key={l.id}
                    className={`hover:bg-[#ECEAE5]/60 transition-colors ${
                      isSelected ? 'bg-[#ECEAE5]' : l.status === 'REVIEW_NEEDED' ? 'bg-[#fffbeb]' : ''
                    }`}
                  >
                    <td className="py-1.5 px-2.5 text-center border-r border-[#141414]/10">
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => toggleSelectLedger(l.id)}
                        className="accent-[#141414]"
                      />
                    </td>

                    <td className="py-1.5 px-3 font-semibold text-[#141414] border-r border-[#141414]/10">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        <span>{l.ledgerName}</span>
                        {(l.hasSavedRule || rulesMap[l.ledgerName.toLowerCase().trim()]) && (
                          <span
                            className="inline-flex items-center px-1.5 py-0.2 text-[9px] font-mono font-bold bg-[#dcfce7] text-[#166534] border border-[#86efac] rounded-xs shadow-2xs"
                            title={l.savedRuleNature || 'Persistent classification rule active for this ledger'}
                          >
                            <BookmarkCheck className="w-2.5 h-2.5 mr-0.5 text-[#166534]" />
                            RULE SAVED
                          </span>
                        )}
                      </div>
                      {l.aiSuggestion && (
                        <div className="text-[10px] font-mono text-[#6b21a8] flex items-center gap-1 mt-0.5">
                          <Sparkles className="w-2.5 h-2.5" />
                          <span>AI: {l.aiSuggestion.rationale}</span>
                        </div>
                      )}
                    </td>

                    <td className="py-1.5 px-3 text-[#5E5E5E] truncate border-r border-[#141414]/10">{l.originalGroup}</td>

                    <td className="py-1.5 px-3 text-right font-mono font-bold text-[#141414] border-r border-[#141414]/10">
                      ₹{netAmt.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </td>

                    <td className="py-1.5 px-3 text-center font-bold border-r border-[#141414]/10">
                      <span
                        className={`text-[10px] px-1.5 py-0.2 font-mono border ${
                          l.natureDrCr === 'Dr'
                            ? 'bg-[#eff6ff] text-[#1d4ed8] border-[#bfdbfe]'
                            : 'bg-[#faf5ff] text-[#6b21a8] border-[#d8b4fe]'
                        }`}
                      >
                        {l.natureDrCr}
                      </span>
                    </td>

                    {/* Target Statement Switcher */}
                    <td className="py-1.5 px-3 border-r border-[#141414]/10">
                      <select
                        value={l.targetType}
                        onChange={e => {
                          const newTarget = e.target.value as TargetStatementType;
                          if (newTarget === 'BALANCE_SHEET') {
                            const defaultH = l.natureDrCr === 'Dr' ? activeHeads.find(h => h.nature === 'Asset') || activeHeads[0] : activeHeads.find(h => h.nature === 'Liability') || activeHeads[0];
                            handleHeadChange(l, defaultH.code);
                          } else if (newTarget === 'PROFIT_AND_LOSS') {
                            handlePLCategoryChange(l, l.natureDrCr === 'Dr' ? 'INDIRECT_EXPENSE' : 'INDIRECT_INCOME');
                          } else {
                            onUpdateLedger({
                              ...l,
                              targetType: 'UNCLASSIFIED',
                              headCode: undefined,
                              mainHead: undefined,
                              subHead: undefined,
                              scheduleNo: undefined,
                              status: 'REVIEW_NEEDED',
                              confidence: 'LOW',
                              confidenceReason: 'Marked as unclassified',
                              hasSavedRule: false,
                              savedRuleNature: undefined,
                              isUserModified: true,
                            });
                            deleteSavedClassificationRule(l.ledgerName);
                            refreshSavedRules();
                          }
                        }}
                        className="w-full bg-white border border-[#141414] px-1.5 py-1 text-xs font-mono font-semibold text-[#141414] focus:outline-none"
                      >
                        <option value="BALANCE_SHEET">Balance Sheet</option>
                        <option value="PROFIT_AND_LOSS">Profit & Loss</option>
                        <option value="UNCLASSIFIED">Unclassified</option>
                      </select>
                    </td>

                    {/* Assigned Head / Category Selector & Saved Nature Display */}
                    <td className="py-1.5 px-3 border-r border-[#141414]/10">
                      {l.targetType === 'BALANCE_SHEET' ? (
                        <div>
                          <select
                            value={l.headCode || ''}
                            onChange={e => handleHeadChange(l, e.target.value)}
                            className="w-full bg-white border border-[#141414] px-2 py-1 text-xs font-mono font-medium text-[#166534] focus:outline-none"
                          >
                            <option value="">Select Schedule Head...</option>
                            {activeHeads.map(h => (
                              <option key={h.code} value={h.code}>
                                Sch {h.scheduleNo} - {h.subHead} ({h.nature})
                              </option>
                            ))}
                          </select>
                          {(() => {
                            const curHead = activeHeads.find(h => h.code === l.headCode);
                            return (
                              <div className="flex items-center justify-between text-[10px] font-mono mt-0.5 px-0.5">
                                <span
                                  className={`font-semibold ${
                                    curHead?.nature === 'Asset' ? 'text-[#166534]' : 'text-[#6b21a8]'
                                  }`}
                                >
                                  Nature: {curHead?.nature || 'Asset/Liability'}
                                </span>
                                {(l.hasSavedRule || rulesMap[l.ledgerName.toLowerCase().trim()]) && (
                                  <button
                                    onClick={() => handleRemoveSavedRule(l)}
                                    className="text-[#991b1b] hover:underline text-[9.5px] cursor-pointer"
                                    title="Clear saved rule for this account and revert to auto-matching"
                                  >
                                    Reset Rule
                                  </button>
                                )}
                              </div>
                            );
                          })()}
                        </div>
                      ) : l.targetType === 'PROFIT_AND_LOSS' ? (
                        <div>
                          <select
                            value={l.plCategory || 'INDIRECT_EXPENSE'}
                            onChange={e => handlePLCategoryChange(l, e.target.value as PLCategory)}
                            className="w-full bg-white border border-[#141414] px-2 py-1 text-xs font-mono font-medium text-[#1d4ed8] focus:outline-none"
                          >
                            <option value="DIRECT_INCOME">Direct Income (Sales/Turnover)</option>
                            <option value="DIRECT_EXPENSE">Direct Expense (Purchases/Trading)</option>
                            <option value="INDIRECT_INCOME">Indirect Income (Interest/Discount)</option>
                            <option value="INDIRECT_EXPENSE">Indirect Expense (Salaries/Admin)</option>
                          </select>
                          <div className="flex items-center justify-between text-[10px] font-mono mt-0.5 px-0.5">
                            <span className="text-[#1d4ed8] font-semibold">
                              Nature: {(l.plCategory || 'Expense').replace(/_/g, ' ')}
                            </span>
                            {(l.hasSavedRule || rulesMap[l.ledgerName.toLowerCase().trim()]) && (
                              <button
                                onClick={() => handleRemoveSavedRule(l)}
                                className="text-[#991b1b] hover:underline text-[9.5px] cursor-pointer"
                                title="Clear saved rule for this account and revert to auto-matching"
                              >
                                Reset Rule
                              </button>
                            )}
                          </div>
                        </div>
                      ) : (
                        <span className="text-[#92400e] font-mono font-semibold text-xs italic">Select target above</span>
                      )}
                    </td>

                    {/* Classification Rationale & Confidence Badge */}
                    <td className="py-1.5 px-3">
                      <div className="flex items-center gap-1.5">
                        <span
                          className={`inline-flex items-center px-1.5 py-0.2 font-mono text-[9px] font-bold border shrink-0 ${
                            l.hasSavedRule || rulesMap[l.ledgerName.toLowerCase().trim()]
                              ? 'bg-[#dcfce7] text-[#166534] border-[#86efac]'
                              : l.confidence === 'HIGH'
                              ? 'bg-[#dcfce7] text-[#166534] border-[#86efac]'
                              : l.confidence === 'MEDIUM'
                              ? 'bg-[#eff6ff] text-[#1d4ed8] border-[#bfdbfe]'
                              : 'bg-[#fef3c7] text-[#92400e] border-[#fde68a]'
                          }`}
                        >
                          {l.hasSavedRule || rulesMap[l.ledgerName.toLowerCase().trim()] ? 'SAVED' : l.confidence || 'LOW'}
                        </span>
                        <span className="text-[11px] text-[#5E5E5E] truncate" title={l.savedRuleNature || l.confidenceReason}>
                          {l.savedRuleNature || l.confidenceReason || 'Rule Engine Auto-Match'}
                        </span>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Saved Rules Manager Modal */}
      <SavedRulesModal
        isOpen={isSavedRulesModalOpen}
        onClose={() => setIsSavedRulesModalOpen(false)}
        heads={heads}
        onRulesChanged={() => {
          refreshSavedRules();
          onReclassifyAll();
        }}
      />
    </div>
  );
};
