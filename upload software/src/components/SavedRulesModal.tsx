import React, { useState } from 'react';
import {
  X,
  BookmarkCheck,
  Trash2,
  Search,
  Download,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  RefreshCw,
} from 'lucide-react';
import { BalanceSheetHeadConfig, SavedClassificationRule } from '../types/accounting';
import {
  deleteSavedClassificationRule,
  clearAllSavedClassificationRules,
  getSavedClassificationRules,
} from '../utils/classificationRulesService';

interface SavedRulesModalProps {
  isOpen: boolean;
  onClose: () => void;
  heads: BalanceSheetHeadConfig[];
  onRulesChanged: () => void;
}

export const SavedRulesModal: React.FC<SavedRulesModalProps> = ({
  isOpen,
  onClose,
  heads,
  onRulesChanged,
}) => {
  const [rules, setRules] = useState<SavedClassificationRule[]>(() => getSavedClassificationRules());
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState<string>('ALL');

  if (!isOpen) return null;

  const refreshRules = () => {
    const updated = getSavedClassificationRules();
    setRules(updated);
    onRulesChanged();
  };

  const handleDeleteRule = (id: string, name: string) => {
    if (window.confirm(`Delete saved classification rule for "${name}"?\nThe account will revert to standard ICAI automatic matching.`)) {
      const remaining = deleteSavedClassificationRule(id);
      setRules(remaining);
      onRulesChanged();
    }
  };

  const handleClearAll = () => {
    if (window.confirm('Are you sure you want to CLEAR ALL saved classification rules? This cannot be undone.')) {
      clearAllSavedClassificationRules();
      setRules([]);
      onRulesChanged();
    }
  };

  const handleExportJson = () => {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(rules, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute('download', `classification_rules_${Date.now()}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  const filteredRules = rules.filter(r => {
    const matchSearch =
      r.ledgerName.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (r.originalGroup || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (r.subHead || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      r.classificationNature.toLowerCase().includes(searchTerm.toLowerCase());

    if (!matchSearch) return false;

    if (filterType === 'ASSETS') {
      return r.targetType === 'BALANCE_SHEET' && r.headNature === 'Asset';
    }
    if (filterType === 'LIABILITIES') {
      return r.targetType === 'BALANCE_SHEET' && r.headNature === 'Liability';
    }
    if (filterType === 'PL') {
      return r.targetType === 'PROFIT_AND_LOSS';
    }

    return true;
  });

  const assetRulesCount = rules.filter(r => r.targetType === 'BALANCE_SHEET' && r.headNature === 'Asset').length;
  const liabilityRulesCount = rules.filter(r => r.targetType === 'BALANCE_SHEET' && r.headNature === 'Liability').length;
  const plRulesCount = rules.filter(r => r.targetType === 'PROFIT_AND_LOSS').length;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#141414]/75 backdrop-blur-xs p-4 animate-in fade-in" id="modal-saved-rules">
      <div className="bg-[#F5F4F0] max-w-4xl w-full shadow-2xl border border-[#141414] overflow-hidden flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="bg-[#141414] text-[#E4E3E0] p-4 flex items-center justify-between border-b border-[#141414] shrink-0">
          <div className="flex items-center space-x-2.5">
            <BookmarkCheck className="w-4 h-4 text-[#86efac]" />
            <div>
              <h3 className="font-bold text-xs uppercase tracking-wider font-mono text-white flex items-center gap-2">
                <span>Saved Classification Rules & Head Nature Memory</span>
                <span className="bg-[#222222] text-[#86efac] px-2 py-0.5 text-[10.5px] border border-white/20 font-mono">
                  {rules.length} RULES PERSISTED
                </span>
              </h3>
              <p className="text-[11px] text-[#A3A29E] mt-0.5">
                The statutory nature of classification (Asset / Liability / Direct / Indirect) and chosen head are automatically remembered across trial balance imports and browser sessions.
              </p>
            </div>
          </div>
          <button onClick={onClose} className="text-[#A3A29E] hover:text-white p-1">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Stats Strip & Controls */}
        <div className="bg-[#ECEAE5] p-3 border-b border-[#141414]/20 flex flex-wrap items-center justify-between gap-3 shrink-0">
          <div className="flex items-center space-x-2">
            <div className="relative w-64">
              <Search className="w-3 h-3 absolute left-2.5 top-2.5 text-[#5E5E5E]" />
              <input
                type="text"
                placeholder="Search ledger, head, or nature..."
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
                className="pl-7 pr-2.5 py-1 bg-white border border-[#141414] text-xs font-mono w-full focus:outline-none"
              />
            </div>

            <div className="flex space-x-1">
              {[
                { id: 'ALL', label: `ALL (${rules.length})` },
                { id: 'ASSETS', label: `ASSETS (${assetRulesCount})` },
                { id: 'LIABILITIES', label: `LIABILITIES (${liabilityRulesCount})` },
                { id: 'PL', label: `P&L (${plRulesCount})` },
              ].map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setFilterType(tab.id)}
                  className={`px-2 py-1 text-[10.5px] font-mono border transition ${
                    filterType === tab.id
                      ? 'bg-[#141414] text-white border-[#141414] font-bold'
                      : 'bg-white border-[#141414]/20 text-[#5E5E5E] hover:text-[#141414]'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={handleExportJson}
              disabled={rules.length === 0}
              className="inline-flex items-center px-2.5 py-1 bg-white hover:bg-[#ECEAE5] text-[#141414] text-[11px] font-mono border border-[#141414] transition disabled:opacity-40"
              title="Download backup of classification rules"
            >
              <Download className="w-3 h-3 mr-1" />
              EXPORT JSON
            </button>
            <button
              onClick={handleClearAll}
              disabled={rules.length === 0}
              className="inline-flex items-center px-2.5 py-1 bg-[#fee2e2] hover:bg-[#fecaca] text-[#991b1b] text-[11px] font-mono border border-[#f87171] transition disabled:opacity-40"
              title="Delete all saved user rules"
            >
              <Trash2 className="w-3 h-3 mr-1" />
              CLEAR ALL
            </button>
          </div>
        </div>

        {/* Table Content */}
        <div className="overflow-y-auto flex-1 p-0 bg-white">
          {filteredRules.length === 0 ? (
            <div className="p-8 text-center text-[#5E5E5E] space-y-2">
              <ShieldCheck className="w-8 h-8 mx-auto text-[#A3A29E]" />
              <p className="font-mono text-xs font-semibold text-[#141414]">No saved rules found</p>
              <p className="text-[11px] max-w-md mx-auto text-[#5E5E5E]">
                Whenever you change a ledger&apos;s classification in Classification Studio or bulk map accounts, the app will automatically save the chosen head and nature here.
              </p>
            </div>
          ) : (
            <table className="w-full text-left text-xs border-collapse">
              <thead className="bg-[#ECEAE5] text-[#141414] font-mono text-[11px] uppercase tracking-wider sticky top-0 z-10 border-b border-[#141414]">
                <tr>
                  <th className="py-2 px-2.5 w-10 text-center border-r border-[#141414]/20">SR.</th>
                  <th className="py-2 px-3 border-r border-[#141414]/20">Ledger Name</th>
                  <th className="py-2 px-3 w-36 border-r border-[#141414]/20">ERP Group</th>
                  <th className="py-2 px-3 w-32 border-r border-[#141414]/20">Statement</th>
                  <th className="py-2 px-3 w-52 border-r border-[#141414]/20">Chosen Head / Schedule</th>
                  <th className="py-2 px-3 w-40 border-r border-[#141414]/20">Nature of Classification</th>
                  <th className="py-2 px-3 w-28 text-center border-r border-[#141414]/20">Saved Date</th>
                  <th className="py-2 px-2.5 w-16 text-center">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#141414]/15 font-mono">
                {filteredRules.map((rule, idx) => (
                  <tr key={rule.id} className="hover:bg-[#ECEAE5]/50 transition-colors">
                    <td className="py-1.5 px-2.5 text-center text-[#5E5E5E] border-r border-[#141414]/10">
                      {idx + 1}
                    </td>

                    <td className="py-1.5 px-3 font-semibold text-[#141414] border-r border-[#141414]/10">
                      {rule.ledgerName}
                    </td>

                    <td className="py-1.5 px-3 text-[#5E5E5E] truncate border-r border-[#141414]/10">
                      {rule.originalGroup || '-'}
                    </td>

                    <td className="py-1.5 px-3 border-r border-[#141414]/10">
                      <span
                        className={`inline-block px-1.5 py-0.2 text-[10px] font-bold border ${
                          rule.targetType === 'BALANCE_SHEET'
                            ? 'bg-[#f0fdf4] text-[#166534] border-[#86efac]'
                            : 'bg-[#eff6ff] text-[#1d4ed8] border-[#bfdbfe]'
                        }`}
                      >
                        {rule.targetType === 'BALANCE_SHEET' ? 'Balance Sheet' : 'Profit & Loss'}
                      </span>
                    </td>

                    <td className="py-1.5 px-3 font-medium text-[#141414] border-r border-[#141414]/10">
                      {rule.targetType === 'BALANCE_SHEET' ? (
                        <span>
                          Sch {rule.scheduleNo} - {rule.subHead}
                        </span>
                      ) : (
                        <span className="text-[#1d4ed8]">
                          {(rule.plCategory || '').replace(/_/g, ' ')}
                        </span>
                      )}
                    </td>

                    {/* Saved Nature */}
                    <td className="py-1.5 px-3 border-r border-[#141414]/10">
                      {rule.headNature === 'Asset' ? (
                        <span className="inline-block px-2 py-0.5 text-[10.5px] font-bold bg-[#dcfce7] text-[#166534] border border-[#86efac]">
                          Asset (Dr)
                        </span>
                      ) : rule.headNature === 'Liability' ? (
                        <span className="inline-block px-2 py-0.5 text-[10.5px] font-bold bg-[#faf5ff] text-[#6b21a8] border border-[#d8b4fe]">
                          Liability (Cr)
                        </span>
                      ) : rule.plCategory?.includes('INCOME') ? (
                        <span className="inline-block px-2 py-0.5 text-[10.5px] font-bold bg-[#ecfdf5] text-[#047857] border border-[#a7f3d0]">
                          {rule.plCategory.replace(/_/g, ' ')}
                        </span>
                      ) : rule.plCategory?.includes('EXPENSE') ? (
                        <span className="inline-block px-2 py-0.5 text-[10.5px] font-bold bg-[#fff7ed] text-[#c2410c] border border-[#fed7aa]">
                          {rule.plCategory.replace(/_/g, ' ')}
                        </span>
                      ) : (
                        <span className="text-[#5E5E5E]">{rule.classificationNature}</span>
                      )}
                    </td>

                    <td className="py-1.5 px-3 text-center text-[10px] text-[#5E5E5E] border-r border-[#141414]/10">
                      {rule.savedAt ? new Date(rule.savedAt).toLocaleDateString('en-GB') : '-'}
                    </td>

                    <td className="py-1.5 px-2.5 text-center">
                      <button
                        onClick={() => handleDeleteRule(rule.id, rule.ledgerName)}
                        className="p-1 text-[#5E5E5E] hover:text-red-700 hover:bg-red-50 transition"
                        title="Delete rule and revert to auto-classification"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Footer */}
        <div className="bg-[#ECEAE5] p-3 border-t border-[#141414]/20 flex items-center justify-between shrink-0">
          <div className="flex items-center space-x-1.5 text-[11px] text-[#5E5E5E]">
            <CheckCircle2 className="w-3.5 h-3.5 text-[#166534]" />
            <span>Classification rules are automatically synced to your browser storage.</span>
          </div>
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-[#141414] hover:bg-[#222222] text-white text-xs font-mono font-bold transition"
          >
            DONE
          </button>
        </div>
      </div>
    </div>
  );
};
