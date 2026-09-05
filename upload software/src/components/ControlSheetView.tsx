import React, { useState } from 'react';
import {
  SlidersHorizontal,
  Plus,
  Trash2,
  ArrowUp,
  ArrowDown,
  Edit2,
  Check,
  RotateCcw,
  Sparkles,
  Info,
  Layers,
  FileSpreadsheet,
  Presentation,
} from 'lucide-react';
import {
  BalanceSheetHeadConfig,
  EntityDetails,
  HeadNature,
  MainHeadType,
} from '../types/accounting';
import { DEFAULT_HEAD_CONFIGS } from '../utils/defaultData';

interface ControlSheetViewProps {
  entity: EntityDetails;
  heads: BalanceSheetHeadConfig[];
  onUpdateHeads: (heads: BalanceSheetHeadConfig[]) => void;
  onOpenEntityModal: () => void;
  onNavigateToTab: (tab: any) => void;
  onOpenPptDeck?: () => void;
}

export const ControlSheetView: React.FC<ControlSheetViewProps> = ({
  entity,
  heads,
  onUpdateHeads,
  onOpenEntityModal,
  onNavigateToTab,
  onOpenPptDeck,
}) => {
  const [isAddingHead, setIsAddingHead] = useState(false);
  const [editingHeadId, setEditingHeadId] = useState<string | null>(null);

  // New Head Form State
  const [newCode, setNewCode] = useState('');
  const [newSubHead, setNewSubHead] = useState('');
  const [newScheduleNo, setNewScheduleNo] = useState<string | number>('');
  const [newNature, setNewNature] = useState<HeadNature>('Liability');
  const [newMainHead, setNewMainHead] = useState<MainHeadType>('Capital & Liabilities');

  const handleToggleActive = (id: string) => {
    const updated = heads.map(h => (h.id === id ? { ...h, active: !h.active } : h));
    onUpdateHeads(updated);
  };

  const handleMoveOrder = (index: number, direction: 'up' | 'down') => {
    const targetIndex = direction === 'up' ? index - 1 : index + 1;
    if (targetIndex < 0 || targetIndex >= heads.length) return;

    const newHeads = [...heads];
    const temp = newHeads[index];
    newHeads[index] = newHeads[targetIndex];
    newHeads[targetIndex] = temp;

    // Re-index display orders
    const reindexed = newHeads.map((h, idx) => ({ ...h, displayOrder: idx + 1 }));
    onUpdateHeads(reindexed);
  };

  const handleDeleteHead = (id: string) => {
    if (window.confirm('Are you sure you want to remove this Balance Sheet head? Any mapped ledgers will become unclassified.')) {
      const updated = heads.filter(h => h.id !== id);
      onUpdateHeads(updated);
    }
  };

  const handleAddNewHead = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newSubHead.trim()) return;

    const generatedCode = newCode.trim() || (newNature === 'Liability' ? `L${heads.length + 1}` : `A${heads.length + 1}`);
    const schedNo = newScheduleNo || (heads.length + 1);

    const newHeadItem: BalanceSheetHeadConfig = {
      id: `head-custom-${Date.now()}`,
      code: generatedCode,
      mainHead: newNature === 'Liability' ? 'Capital & Liabilities' : 'Assets',
      subHead: newSubHead.trim(),
      scheduleNo: schedNo,
      scheduleTitle: `Schedule ${schedNo} - ${newSubHead.trim()}`,
      nature: newNature,
      displayOrder: heads.length + 1,
      active: true,
      isSpecialSchedule: 'STANDARD',
    };

    onUpdateHeads([...heads, newHeadItem]);
    setIsAddingHead(false);
    setNewCode('');
    setNewSubHead('');
    setNewScheduleNo('');
  };

  const handleSaveInlineEdit = (headId: string, updatedFields: Partial<BalanceSheetHeadConfig>) => {
    const updated = heads.map(h => {
      if (h.id === headId) {
        const merged = { ...h, ...updatedFields };
        merged.mainHead = merged.nature === 'Liability' ? 'Capital & Liabilities' : 'Assets';
        merged.scheduleTitle = `Schedule ${merged.scheduleNo} - ${merged.subHead}`;
        return merged;
      }
      return h;
    });
    onUpdateHeads(updated);
    setEditingHeadId(null);
  };

  const handleResetToDefault = () => {
    if (window.confirm('Reset all Balance Sheet heads to default Indian GAAP structure? Custom changes will be restored.')) {
      onUpdateHeads(DEFAULT_HEAD_CONFIGS);
    }
  };

  return (
    <div className="space-y-4" id="control-sheet-container">
      {/* Top Banner Notice */}
      <div className="bg-[#141414] text-[#E4E3E0] p-4 border border-[#141414]">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2">
              <SlidersHorizontal className="w-4 h-4 text-[#A3A29E]" />
              <h2 className="text-sm font-bold font-mono uppercase tracking-wider text-white">Sheet 1: Central Control & Head Configuration</h2>
            </div>
            <p className="text-[11.5px] text-[#A3A29E] mt-1 max-w-3xl">
              Master architectural schema layer. Any modifications here (renaming heads, changing schedule numbers, reordering, adding custom heads) will <strong>dynamically propagate</strong> to the Trial Balance classification, Schedules, P&L, Balance Sheet, and the generated Excel workbook.
            </p>
          </div>
          <div className="flex items-center space-x-2 shrink-0">
            {onOpenPptDeck && (
              <button
                onClick={onOpenPptDeck}
                className="inline-flex items-center px-2.5 py-1 bg-[#2b2416] hover:bg-[#3d321d] text-[#fcd34d] text-[11px] font-mono border border-[#f59e0b]/40 transition"
                id="btn-control-ppt-deck"
                title="View & Download 5-Slide Presentation Deck"
              >
                <Presentation className="w-3.5 h-3.5 mr-1 text-[#f59e0b]" />
                PPT DECK (5 SLIDES)
              </button>
            )}
            <button
              onClick={handleResetToDefault}
              className="inline-flex items-center px-2.5 py-1 bg-[#222222] hover:bg-[#2e2e2e] text-[#E4E3E0] text-[11px] font-mono border border-white/20 transition"
              id="btn-reset-default-heads"
            >
              <RotateCcw className="w-3 h-3 mr-1" />
              RESET ICAI HEADS
            </button>
            <button
              onClick={() => setIsAddingHead(true)}
              className="inline-flex items-center px-3 py-1 bg-[#E4E3E0] hover:bg-white text-[#141414] text-[11px] font-mono font-bold border border-[#141414] transition"
              id="btn-add-new-head"
            >
              <Plus className="w-3.5 h-3.5 mr-1" />
              ADD CUSTOM HEAD
            </button>
          </div>
        </div>
      </div>

      {/* Entity Details Card */}
      <div className="bg-[#F5F4F0] border border-[#141414]/20 p-4" id="card-entity-master">
        <div className="flex items-center justify-between border-b border-[#141414]/15 pb-2.5 mb-3">
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 bg-[#141414]"></div>
            <h3 className="font-bold text-[#141414] text-xs uppercase font-mono tracking-wider">A. Entity Master Information</h3>
          </div>
          <button
            onClick={onOpenEntityModal}
            className="text-[11px] font-mono font-semibold text-[#141414] hover:underline flex items-center gap-1"
            id="btn-edit-master-info"
          >
            <Edit2 className="w-3 h-3" /> [EDIT MASTER DETAILS]
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
          <div className="space-y-1 bg-[#ECEAE5] p-3 border border-[#141414]/15">
            <span className="text-[#5E5E5E] text-[10.5px] font-mono uppercase">Entity Name & Constitution</span>
            <p className="font-bold text-[#141414] text-sm font-serif">{entity.name}</p>
            <p className="text-[#5E5E5E] font-medium text-[11.5px]">{entity.entityType}</p>
          </div>

          <div className="space-y-1 bg-[#ECEAE5] p-3 border border-[#141414]/15">
            <span className="text-[#5E5E5E] text-[10.5px] font-mono uppercase">Statutory Tax Registrations</span>
            <div className="flex items-center justify-between">
              <span className="text-[#141414] font-mono font-semibold text-[11.5px]">PAN: {entity.pan}</span>
              <span className="text-[#141414] font-mono font-semibold text-[11.5px]">GSTIN: {entity.gstin}</span>
            </div>
            <p className="text-[#5E5E5E] truncate text-[11.5px]">{entity.address}</p>
          </div>

          <div className="space-y-1 bg-[#ECEAE5] p-3 border border-[#141414]/15">
            <span className="text-[#5E5E5E] text-[10.5px] font-mono uppercase">Financial Year & Audit Dates</span>
            <div className="flex items-center justify-between font-semibold font-mono text-[#141414] text-[11.5px]">
              <span>FY: {entity.financialYear}</span>
              <span>BS Date: {entity.balanceSheetDate}</span>
            </div>
            <p className="text-[#5E5E5E] text-[11.5px]">Auditor: {entity.auditorName || 'Not specified'}</p>
          </div>
        </div>
      </div>

      {/* Add New Head Form Modal/Inline Card */}
      {isAddingHead && (
        <form
          onSubmit={handleAddNewHead}
          className="bg-[#ECEAE5] border-2 border-[#141414] p-4 shadow-sm"
          id="form-add-head"
        >
          <div className="flex items-center justify-between mb-3 border-b border-[#141414]/20 pb-2">
            <h4 className="font-bold text-xs font-mono uppercase text-[#141414] flex items-center gap-1.5">
              <Plus className="w-3.5 h-3.5 text-[#141414]" /> Add New Balance Sheet Head / Schedule
            </h4>
            <button
              type="button"
              onClick={() => setIsAddingHead(false)}
              className="text-[11px] font-mono text-[#5E5E5E] hover:text-[#141414] underline"
            >
              [CANCEL]
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-3 text-xs">
            <div>
              <label className="block font-mono text-[10.5px] uppercase text-[#141414] mb-1">Nature</label>
              <select
                value={newNature}
                onChange={e => setNewNature(e.target.value as HeadNature)}
                className="w-full bg-white border border-[#141414] p-1.5 text-xs font-semibold"
                id="select-head-nature"
              >
                <option value="Liability">Liability (Capital & Liabilities)</option>
                <option value="Asset">Asset (Assets)</option>
              </select>
            </div>

            <div>
              <label className="block font-mono text-[10.5px] uppercase text-[#141414] mb-1">Head Code</label>
              <input
                type="text"
                placeholder={newNature === 'Liability' ? 'e.g. L08' : 'e.g. A08'}
                value={newCode}
                onChange={e => setNewCode(e.target.value)}
                className="w-full bg-white border border-[#141414] p-1.5 text-xs uppercase font-mono"
                id="input-head-code"
              />
            </div>

            <div className="md:col-span-2">
              <label className="block font-mono text-[10.5px] uppercase text-[#141414] mb-1">Sub Head Name *</label>
              <input
                type="text"
                placeholder="e.g. Partner Current Accounts / Deferred Tax Asset"
                value={newSubHead}
                onChange={e => setNewSubHead(e.target.value)}
                required
                className="w-full bg-white border border-[#141414] p-1.5 text-xs font-medium"
                id="input-subhead-name"
              />
            </div>

            <div>
              <label className="block font-mono text-[10.5px] uppercase text-[#141414] mb-1">Schedule No. *</label>
              <input
                type="text"
                placeholder="e.g. 15 or 4A"
                value={newScheduleNo}
                onChange={e => setNewScheduleNo(e.target.value)}
                required
                className="w-full bg-white border border-[#141414] p-1.5 text-xs font-mono font-medium"
                id="input-schedule-no"
              />
            </div>
          </div>

          <div className="flex justify-end gap-2 mt-4">
            <button
              type="button"
              onClick={() => setIsAddingHead(false)}
              className="px-3 py-1 bg-white border border-[#141414] text-xs font-mono text-[#141414]"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-1 bg-[#141414] text-white text-xs font-mono font-bold hover:bg-[#2e2e2e]"
              id="btn-submit-add-head"
            >
              SAVE HEAD
            </button>
          </div>
        </form>
      )}

      {/* Balance Sheet Head Configuration Master Table */}
      <div className="bg-[#F5F4F0] border border-[#141414]/20 overflow-hidden" id="table-heads-config">
        <div className="p-3 border-b border-[#141414]/20 bg-[#ECEAE5] flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 bg-[#141414]"></div>
            <h3 className="font-bold text-[#141414] text-xs font-mono uppercase tracking-wider">B. Balance Sheet Head Configuration & Schedule Mapping</h3>
          </div>
          <span className="text-[11px] font-mono text-[#5E5E5E]">
            TOTAL HEADS: <strong className="text-[#141414]">{heads.length}</strong> (ACTIVE: {heads.filter(h => h.active).length})
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead className="bg-[#ECEAE5] text-[#141414] font-mono text-[11px] uppercase tracking-wider border-b border-[#141414]">
              <tr>
                <th className="py-2 px-2.5 w-12 text-center border-r border-[#141414]/20">Order</th>
                <th className="py-2 px-2.5 w-16 border-r border-[#141414]/20">Code</th>
                <th className="py-2 px-3 w-40 border-r border-[#141414]/20">Main Head</th>
                <th className="py-2 px-3 border-r border-[#141414]/20">Sub Head Name (Schedule Title)</th>
                <th className="py-2 px-2.5 w-24 text-center border-r border-[#141414]/20">Schedule</th>
                <th className="py-2 px-2.5 w-20 text-center border-r border-[#141414]/20">Nature</th>
                <th className="py-2 px-2.5 w-20 text-center border-r border-[#141414]/20">Status</th>
                <th className="py-2 px-3 w-24 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#141414]/15 bg-white">
              {heads.map((head, idx) => {
                const isEditing = editingHeadId === head.id;

                return (
                  <tr
                    key={head.id}
                    className={`hover:bg-[#ECEAE5]/60 transition-colors ${!head.active ? 'opacity-40 bg-[#ECEAE5]' : ''}`}
                    id={`head-row-${head.code}`}
                  >
                    {/* Order buttons */}
                    <td className="py-1.5 px-2 text-center border-r border-[#141414]/10">
                      <div className="flex items-center justify-center space-x-0.5">
                        <button
                          onClick={() => handleMoveOrder(idx, 'up')}
                          disabled={idx === 0}
                          className="p-0.5 text-[#5E5E5E] hover:text-[#141414] disabled:opacity-20"
                          title="Move Up"
                        >
                          <ArrowUp className="w-3 h-3" />
                        </button>
                        <button
                          onClick={() => handleMoveOrder(idx, 'down')}
                          disabled={idx === heads.length - 1}
                          className="p-0.5 text-[#5E5E5E] hover:text-[#141414] disabled:opacity-20"
                          title="Move Down"
                        >
                          <ArrowDown className="w-3 h-3" />
                        </button>
                      </div>
                    </td>

                    {/* Code */}
                    <td className="py-1.5 px-2.5 font-mono font-bold text-[#141414] border-r border-[#141414]/10">
                      {head.code}
                    </td>

                    {/* Main Head */}
                    <td className="py-1.5 px-3 font-medium border-r border-[#141414]/10">
                      <span
                        className={`inline-block px-1.5 py-0.2 font-mono text-[10px] font-bold border ${
                          head.nature === 'Liability'
                            ? 'bg-[#faf5ff] text-[#6b21a8] border-[#d8b4fe]'
                            : 'bg-[#f0fdf4] text-[#166534] border-[#86efac]'
                        }`}
                      >
                        {head.mainHead}
                      </span>
                    </td>

                    {/* Sub Head Name */}
                    <td className="py-1.5 px-3 border-r border-[#141414]/10">
                      {isEditing ? (
                        <input
                          type="text"
                          defaultValue={head.subHead}
                          id={`input-edit-subhead-${head.id}`}
                          className="w-full bg-white border border-[#141414] px-2 py-0.5 text-xs font-semibold focus:outline-none"
                          onKeyDown={e => {
                            if (e.key === 'Enter') {
                              handleSaveInlineEdit(head.id, { subHead: (e.target as HTMLInputElement).value });
                            }
                          }}
                          onBlur={e => {
                            handleSaveInlineEdit(head.id, { subHead: e.target.value });
                          }}
                          autoFocus
                        />
                      ) : (
                        <div className="flex items-center space-x-2">
                          <span className="font-semibold text-[#141414]">{head.subHead}</span>
                          {head.isSpecialSchedule === 'CAPITAL' && (
                            <span className="text-[9.5px] font-mono bg-[#E4E3E0] text-[#141414] font-bold px-1.5 py-0.2 border border-[#141414]/30">
                              AUTO P&L TRANSFER
                            </span>
                          )}
                          {head.isSpecialSchedule === 'FIXED_ASSETS' && (
                            <button
                              onClick={() => onNavigateToTab('depreciation')}
                              className="text-[9.5px] font-mono bg-[#fef3c7] hover:bg-[#fde68a] text-[#92400e] font-bold px-1.5 py-0.2 border border-[#fde68a] cursor-pointer transition flex items-center gap-1"
                              title="Open Depreciation Schedule Tab"
                            >
                              <span>GROSS BLOCK</span>
                              <span className="opacity-70">→ DEPR TAB</span>
                            </button>
                          )}
                        </div>
                      )}
                      {head.description && (
                        <p className="text-[10.5px] text-[#5E5E5E] mt-0.5 truncate">{head.description}</p>
                      )}
                    </td>

                    {/* Schedule No */}
                    <td className="py-1.5 px-2.5 text-center border-r border-[#141414]/10 font-mono font-bold text-[#141414]">
                      SCH {head.scheduleNo}
                    </td>

                    {/* Nature */}
                    <td className="py-1.5 px-2.5 text-center font-mono text-[11px] font-medium text-[#141414] border-r border-[#141414]/10">
                      {head.nature}
                    </td>

                    {/* Status Active/Inactive */}
                    <td className="py-1.5 px-2.5 text-center border-r border-[#141414]/10">
                      <button
                        onClick={() => handleToggleActive(head.id)}
                        className={`text-[10px] font-mono font-bold px-2 py-0.5 border transition ${
                          head.active
                            ? 'bg-[#dcfce7] text-[#166534] border-[#86efac]'
                            : 'bg-[#E4E3E0] text-[#5E5E5E] border-[#141414]/20'
                        }`}
                        title="Click to toggle Active / Inactive"
                      >
                        {head.active ? 'ACTIVE' : 'OFF'}
                      </button>
                    </td>

                    {/* Actions */}
                    <td className="py-1.5 px-3 text-right font-mono">
                      <div className="flex items-center justify-end space-x-1">
                        <button
                          onClick={() => setEditingHeadId(isEditing ? null : head.id)}
                          className="p-1 text-[#5E5E5E] hover:text-[#141414] hover:bg-[#ECEAE5]"
                          title="Rename Sub Head"
                          id={`btn-edit-head-${head.code}`}
                        >
                          <Edit2 className="w-3 h-3" />
                        </button>
                        <button
                          onClick={() => handleDeleteHead(head.id)}
                          className="p-1 text-[#5E5E5E] hover:text-red-700 hover:bg-red-50"
                          title="Delete Head"
                          id={`btn-delete-head-${head.code}`}
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
