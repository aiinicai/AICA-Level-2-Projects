import React, { useState, useEffect } from 'react';
import {
  Archive,
  Save,
  Download,
  Trash2,
  ExternalLink,
  CheckCircle2,
  AlertTriangle,
  Calendar,
  User,
  Clock,
  Building2,
  Search,
  X,
  FileSpreadsheet,
  Tag,
  RefreshCw,
} from 'lucide-react';
import {
  AppUser,
  EntityDetails,
  SavedEntitySummary,
  SavedEntityWorkspace,
  BalanceSheetSummary,
} from '../types/accounting';
import { entityVaultService } from '../utils/entityVaultService';

interface EntityVaultModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentUser: AppUser;
  // Current active workspace details to allow saving
  currentEntity: EntityDetails;
  currentBalanceSheetSummary: BalanceSheetSummary;
  onSaveCurrentWorkspace: (versionTag: string, notes: string) => Promise<{ success: boolean; error?: string }>;
  onFetchAndReview: (workspace: SavedEntityWorkspace) => void;
  isSavingCurrent?: boolean;
}

export const EntityVaultModal: React.FC<EntityVaultModalProps> = ({
  isOpen,
  onClose,
  currentUser,
  currentEntity,
  currentBalanceSheetSummary,
  onSaveCurrentWorkspace,
  onFetchAndReview,
  isSavingCurrent = false,
}) => {
  const [savedEntities, setSavedEntities] = useState<SavedEntitySummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [isSavingMode, setIsSavingMode] = useState(false);
  const [versionTag, setVersionTag] = useState('Final Audit Review');
  const [saveNotes, setSaveNotes] = useState('');
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const fetchList = async () => {
    setLoading(true);
    try {
      const list = await entityVaultService.listSavedEntities();
      setSavedEntities(list);
    } catch (e) {
      console.error('Failed to list saved entities:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchList();
      setFeedback(null);
      setIsSavingMode(false);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSaveCurrent = async (e: React.FormEvent) => {
    e.preventDefault();
    setFeedback(null);
    try {
      const res = await onSaveCurrentWorkspace(versionTag, saveNotes);
      if (res.success) {
        setFeedback({
          type: 'success',
          text: `Entity "${currentEntity.name}" data saved successfully to Vault! It can be fetched anytime for review.`,
        });
        setIsSavingMode(false);
        await fetchList();
      } else {
        setFeedback({ type: 'error', text: res.error || 'Failed to save entity data.' });
      }
    } catch (err: any) {
      setFeedback({ type: 'error', text: err.message || 'Error saving entity.' });
    }
  };

  const handleFetchEntity = async (id: string, entityName: string) => {
    setLoading(true);
    setFeedback(null);
    try {
      const fullWorkspace = await entityVaultService.fetchEntityWorkspace(id);
      if (fullWorkspace) {
        onFetchAndReview(fullWorkspace);
        onClose();
      } else {
        setFeedback({ type: 'error', text: `Could not retrieve data for ${entityName}.` });
      }
    } catch (err: any) {
      setFeedback({ type: 'error', text: err.message || 'Failed to fetch entity.' });
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteEntity = async (id: string, name: string) => {
    if (!confirm(`Are you sure you want to remove saved entity "${name}" from the Vault?`)) return;

    setLoading(true);
    try {
      await entityVaultService.deleteEntityWorkspace(id);
      setFeedback({ type: 'success', text: `Saved record for "${name}" removed from Vault.` });
      await fetchList();
    } catch (err: any) {
      setFeedback({ type: 'error', text: err.message });
    } finally {
      setLoading(false);
    }
  };

  const filteredEntities = savedEntities.filter(
    (e) =>
      e.entityName.toLowerCase().includes(searchQuery.toLowerCase()) ||
      e.entityType.toLowerCase().includes(searchQuery.toLowerCase()) ||
      e.financialYear.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (e.savedBy && e.savedBy.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-xs p-4">
      <div className="bg-[#141414] text-[#E4E3E0] border border-[#333333] w-full max-w-5xl max-h-[92vh] flex flex-col shadow-2xl rounded-none">
        {/* Header */}
        <div className="px-6 py-4 border-b border-[#262626] flex items-center justify-between bg-[#1a1a1a]">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-[#1b2a1e] border border-[#4ade80]/40 text-[#4ade80]">
              <Archive className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold font-mono tracking-tight text-white flex items-center gap-2">
                ENTITY AUDIT VAULT: SAVED CLIENT WORKSPACES
                <span className="px-2 py-0.5 bg-[#262626] text-[#A3A29E] text-[10.5px] font-mono border border-white/10">
                  {savedEntities.length} ENTITIES SAVED
                </span>
              </h2>
              <p className="text-[11px] font-mono text-[#8E8C85]">
                Feed entity data once and fetch it anytime for multi-year review, tax audits, or comparative analysis
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => setIsSavingMode(!isSavingMode)}
              className={`px-3 py-1.5 text-xs font-mono font-bold flex items-center gap-1.5 transition cursor-pointer border ${
                isSavingMode
                  ? 'bg-[#333] text-white border-white/20'
                  : 'bg-[#166534] hover:bg-[#15803d] text-white border-[#4ade80]/50'
              }`}
              id="btn-toggle-save-current"
            >
              <Save className="w-3.5 h-3.5" />
              <span>{isSavingMode ? 'CANCEL SAVE' : 'SAVE CURRENT ENTITY'}</span>
            </button>

            <button
              onClick={onClose}
              className="p-1.5 text-[#8E8C85] hover:text-white hover:bg-[#262626] transition cursor-pointer"
              id="btn-close-vault-modal"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Feedback Alert */}
        {feedback && (
          <div
            className={`mx-6 mt-4 p-3 text-xs font-mono border flex items-center gap-2 ${
              feedback.type === 'success'
                ? 'bg-[#1b2a1e] border-[#4ade80]/40 text-[#4ade80]'
                : 'bg-[#2d1b1b] border-[#f87171]/40 text-[#f87171]'
            }`}
          >
            {feedback.type === 'success' ? (
              <CheckCircle2 className="w-4 h-4 shrink-0" />
            ) : (
              <AlertTriangle className="w-4 h-4 shrink-0" />
            )}
            <span>{feedback.text}</span>
          </div>
        )}

        {/* Save Current Entity Form Drawer */}
        {isSavingMode && (
          <form
            onSubmit={handleSaveCurrent}
            className="mx-6 mt-4 p-4 bg-[#1a1a1a] border border-[#166534] space-y-3"
            id="form-save-current-entity"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono font-bold text-white flex items-center gap-2">
                <Save className="w-4 h-4 text-[#4ade80]" />
                SAVING ACTIVE ENTITY: {currentEntity.name.toUpperCase()} ({currentEntity.financialYear})
              </span>
              <span className="text-[10px] font-mono text-[#4ade80] bg-[#142918] px-2 py-0.5 border border-[#4ade80]/30">
                TOTAL ASSETS: ₹{currentBalanceSheetSummary.totalAssets.toLocaleString('en-IN')}
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <label className="block text-[10.5px] font-mono uppercase text-[#A3A29E] mb-1">
                  Version Tag / Audit Stage
                </label>
                <input
                  type="text"
                  value={versionTag}
                  onChange={(e) => setVersionTag(e.target.value)}
                  placeholder="e.g. Final Audit Signed, Draft Review 1"
                  required
                  className="w-full bg-[#111] border border-[#333] px-3 py-1.5 text-xs font-mono text-white focus:border-[#4ade80] focus:outline-none"
                  id="input-version-tag"
                />
              </div>

              <div>
                <label className="block text-[10.5px] font-mono uppercase text-[#A3A29E] mb-1">
                  Audit Notes / Remarks (Optional)
                </label>
                <input
                  type="text"
                  value={saveNotes}
                  onChange={(e) => setSaveNotes(e.target.value)}
                  placeholder="e.g. Verified with bank confirmation and physical stock sheets"
                  className="w-full bg-[#111] border border-[#333] px-3 py-1.5 text-xs font-mono text-white focus:border-[#4ade80] focus:outline-none"
                  id="input-save-notes"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-1">
              <button
                type="button"
                onClick={() => setIsSavingMode(false)}
                className="px-3 py-1 bg-[#262626] text-xs font-mono text-white hover:bg-[#333] cursor-pointer"
              >
                CANCEL
              </button>
              <button
                type="submit"
                disabled={isSavingCurrent}
                className="px-4 py-1 bg-[#166534] hover:bg-[#15803d] text-white text-xs font-mono font-bold flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
                id="btn-confirm-save-workspace"
              >
                <CheckCircle2 className="w-3.5 h-3.5" />
                {isSavingCurrent ? 'SAVING...' : 'CONFIRM & SAVE TO VAULT'}
              </button>
            </div>
          </form>
        )}

        {/* Search & Stats Bar */}
        <div className="px-6 py-3 border-b border-[#262626] flex flex-col sm:flex-row items-center justify-between gap-3 bg-[#171717]">
          <div className="relative w-full sm:w-80">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-[#8E8C85]" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search saved entities by name, type, or FY..."
              className="w-full bg-[#111] border border-[#333] pl-9 pr-3 py-1.5 text-xs font-mono text-white focus:border-[#4ade80] focus:outline-none"
              id="input-search-vault"
            />
          </div>

          <div className="flex items-center gap-3 text-xs font-mono text-[#8E8C85]">
            <span>Active User: <strong className="text-white">{currentUser.id}</strong> ({currentUser.role})</span>
            <button
              onClick={fetchList}
              className="p-1 hover:text-white transition cursor-pointer"
              title="Refresh Vault List"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-[#4ade80]' : ''}`} />
            </button>
          </div>
        </div>

        {/* Main List Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-3">
          {filteredEntities.length === 0 ? (
            <div className="text-center py-16 border border-dashed border-[#333333] bg-[#171717] p-8">
              <Archive className="w-10 h-10 text-[#8E8C85] mx-auto mb-3 opacity-60" />
              <h3 className="text-sm font-bold font-mono text-white">NO SAVED ENTITY RECORDS FOUND</h3>
              <p className="text-xs font-mono text-[#8E8C85] mt-1 max-w-md mx-auto">
                {searchQuery
                  ? 'No saved entities match your search query.'
                  : 'You have not saved any client workspaces yet. Click "SAVE CURRENT ENTITY" above to store the active entity, its trial balance, adjustments, depreciation schedule, and notes so you can fetch it again for review at any time.'}
              </p>
            </div>
          ) : (
            filteredEntities.map((ent) => (
              <div
                key={ent.id}
                className="bg-[#181818] hover:bg-[#1c1c1c] border border-[#2a2a2a] hover:border-[#444] p-4 transition flex flex-col md:flex-row items-start md:items-center justify-between gap-4"
                id={`vault-entity-card-${ent.id}`}
              >
                {/* Left: Entity Info & Tag */}
                <div className="space-y-1.5">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm font-bold font-mono text-white">{ent.entityName}</span>
                    <span className="px-2 py-0.5 bg-[#262626] text-[#A3A29E] text-[10px] font-mono uppercase font-bold border border-white/10">
                      {ent.entityType}
                    </span>
                    <span className="px-2 py-0.5 bg-[#172554] text-[#93c5fd] text-[10px] font-mono font-bold border border-[#3b82f6]/40">
                      F.Y. {ent.financialYear}
                    </span>
                    {ent.versionTag && (
                      <span className="px-2 py-0.5 bg-[#2e1065] text-[#d8b4fe] text-[10px] font-mono border border-[#a855f7]/40 flex items-center gap-1">
                        <Tag className="w-2.5 h-2.5" />
                        {ent.versionTag}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-4 text-xs font-mono text-[#8E8C85] flex-wrap">
                    <span className="flex items-center gap-1">
                      <Calendar className="w-3.5 h-3.5 text-[#A3A29E]" />
                      B/S Date: {ent.balanceSheetDate}
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5 text-[#A3A29E]" />
                      Saved: {new Date(ent.savedAt).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })}
                    </span>
                    <span className="flex items-center gap-1">
                      <User className="w-3.5 h-3.5 text-[#A3A29E]" />
                      Saved by: <strong className="text-[#E4E3E0]">{ent.savedBy}</strong>
                    </span>
                  </div>

                  {/* Financial Highlights */}
                  <div className="pt-1 flex items-center gap-4 text-xs font-mono">
                    <span className="text-[#A3A29E]">
                      Total Assets: <strong className="text-white">₹{ent.totalAssets.toLocaleString('en-IN')}</strong>
                    </span>
                    <span className="text-[#A3A29E]">
                      Net Profit: <strong className={ent.netProfit >= 0 ? 'text-[#4ade80]' : 'text-[#f87171]'}>
                        ₹{ent.netProfit.toLocaleString('en-IN')}
                      </strong>
                    </span>
                    <span className="text-[#A3A29E]">
                      Ledgers: <strong className="text-white">{ent.ledgersCount}</strong>
                    </span>
                    <span
                      className={`px-1.5 py-0.5 text-[10px] font-bold border flex items-center gap-1 ${
                        ent.isBalanced
                          ? 'bg-[#142918] text-[#4ade80] border-[#4ade80]/30'
                          : 'bg-[#331c1c] text-[#f87171] border-[#f87171]/30'
                      }`}
                    >
                      {ent.isBalanced ? <CheckCircle2 className="w-3 h-3" /> : <AlertTriangle className="w-3 h-3" />}
                      {ent.isBalanced ? 'BALANCED' : `DIFF: ₹${ent.difference.toLocaleString('en-IN')}`}
                    </span>
                  </div>
                </div>

                {/* Right: Actions (Fetch & Review) */}
                <div className="flex items-center gap-2 shrink-0 self-end md:self-center">
                  <button
                    onClick={() => handleFetchEntity(ent.id, ent.entityName)}
                    disabled={loading}
                    className="px-3.5 py-2 bg-[#1e40af] hover:bg-[#1d4ed8] text-white text-xs font-mono font-bold flex items-center gap-1.5 cursor-pointer transition shadow-sm disabled:opacity-50"
                    title="Load complete entity data into workspace for review"
                    id={`btn-fetch-review-${ent.id}`}
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                    FETCH & REVIEW
                  </button>

                  <button
                    onClick={() => handleDeleteEntity(ent.id, ent.entityName)}
                    disabled={loading}
                    className="p-2 text-[#8E8C85] hover:text-[#f87171] hover:bg-[#262626] transition cursor-pointer"
                    title="Remove snapshot from vault"
                    id={`btn-delete-vault-${ent.id}`}
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-[#262626] bg-[#1a1a1a] flex justify-between items-center text-xs font-mono text-[#8E8C85]">
          <div>
            Data is persisted securely per entity and can be reviewed anytime by authorized team members.
          </div>
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-[#262626] hover:bg-[#333333] text-white text-xs font-mono cursor-pointer transition"
          >
            CLOSE
          </button>
        </div>
      </div>
    </div>
  );
};
