import React, { useState } from 'react';
import { X, Calculator, Plus, Trash2, CheckCircle2 } from 'lucide-react';
import { ManualAdjustment } from '../types/accounting';

interface AdjustmentsModalProps {
  adjustments: ManualAdjustment[];
  isOpen: boolean;
  onClose: () => void;
  onSaveAdjustments: (adjustments: ManualAdjustment[]) => void;
}

export const AdjustmentsModal: React.FC<AdjustmentsModalProps> = ({
  adjustments,
  isOpen,
  onClose,
  onSaveAdjustments,
}) => {
  const [list, setList] = useState<ManualAdjustment[]>(adjustments);
  const [stockAmount, setStockAmount] = useState<number>(() => {
    const existing = adjustments.find(a => a.type === 'CLOSING_STOCK');
    return existing ? existing.amount : 0;
  });

  if (!isOpen) return null;

  const handleSave = () => {
    const filtered = list.filter(a => a.type !== 'CLOSING_STOCK');
    if (stockAmount > 0) {
      filtered.push({
        id: 'adj-stock',
        type: 'CLOSING_STOCK',
        description: 'Closing Inventory (Stock in hand as at balance sheet date)',
        debitHead: 'A03', // Inventories (Asset)
        creditHead: 'PL_DIRECT_INCOME', // Trading Credit
        amount: stockAmount,
      });
    }
    onSaveAdjustments(filtered);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#141414]/70 backdrop-blur-xs p-4 animate-in fade-in" id="modal-adjustments">
      <div className="bg-[#F5F4F0] max-w-lg w-full shadow-2xl border border-[#141414] overflow-hidden">
        
        {/* Header */}
        <div className="bg-[#141414] text-[#E4E3E0] p-4 flex items-center justify-between border-b border-[#141414]">
          <div className="flex items-center space-x-2.5">
            <Calculator className="w-4 h-4 text-[#A3A29E]" />
            <h3 className="font-bold text-xs uppercase tracking-wider font-mono text-white">Year-End Closing Stock & Audit Adjustments</h3>
          </div>
          <button onClick={onClose} className="text-[#A3A29E] hover:text-white p-1">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="p-5 space-y-4 text-xs bg-white">
          <div className="bg-[#F5F4F0] border border-[#141414]/20 p-3.5">
            <label className="block font-bold font-mono text-[11px] uppercase text-[#141414] mb-1">
              1. Closing Stock (Valued at lower of Cost or NRV)
            </label>
            <p className="text-[11px] text-[#5E5E5E] font-mono mb-2.5">
              Credited to Trading Account (P&L) and debited to Current Assets / Inventories (Schedule 10).
            </p>
            <div className="relative">
              <span className="absolute left-3 top-2 font-bold text-[#5E5E5E] font-mono">₹</span>
              <input
                type="number"
                value={stockAmount}
                onChange={e => setStockAmount(parseFloat(e.target.value) || 0)}
                placeholder="Enter Closing Stock value"
                className="w-full pl-8 pr-3 py-1.5 bg-white border border-[#141414]/30 text-sm font-mono font-bold text-[#141414] focus:outline-none focus:border-[#141414]"
              />
            </div>
          </div>

          <div className="flex items-center justify-end space-x-2 pt-3 border-t border-[#141414]/20">
            <button
              onClick={onClose}
              className="px-3 py-1.5 bg-[#ECEAE5] hover:bg-[#E4E3E0] text-[#141414] font-mono font-bold text-xs border border-[#141414]/30"
            >
              CANCEL
            </button>
            <button
              onClick={handleSave}
              className="inline-flex items-center px-4 py-1.5 bg-[#141414] hover:bg-[#282828] text-white font-mono font-bold text-xs border border-[#141414]"
            >
              <CheckCircle2 className="w-3.5 h-3.5 mr-1" />
              APPLY ADJUSTMENTS
            </button>
          </div>
        </div>

      </div>
    </div>
  );
};
