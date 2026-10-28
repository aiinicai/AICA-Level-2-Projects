import React from 'react';
import { StoneBlock, MeasurementUnit, BlockCondition, InspectionStatus, MasterData } from '../../types/grn';
import { calculateBlockVolume } from '../../utils/calculations';
import { Plus, Copy, Trash2, Box, Sparkles, AlertCircle, Check, Info } from 'lucide-react';

interface Step2Props {
  blocks: StoneBlock[];
  errors: Record<string, string>;
  masters: MasterData;
  onChangeBlocks: (blocks: StoneBlock[]) => void;
}

export const Step2Blocks: React.FC<Step2Props> = ({
  blocks,
  errors,
  masters,
  onChangeBlocks,
}) => {

  const handleAddBlock = () => {
    const newBlock: StoneBlock = {
      id: `blk-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`,
      blockNumber: '',
      variety: masters.varieties[0] || 'मकराना वाइट (Makrana White)',
      pieces: 1,
      length: 0,
      width: 0,
      height: 0,
      unit: 'इंच (Inches)',
      estimatedVolume: 0,
      volumeUnit: 'घन फीट (CFT)',
      condition: 'ठीक',
      inspectionStatus: 'स्वीकृत',
      remarks: ''
    };
    onChangeBlocks([...blocks, newBlock]);
  };

  const handleDuplicateBlock = (index: number) => {
    const prev = blocks[index];
    const newBlock: StoneBlock = {
      ...prev,
      id: `blk-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`,
      blockNumber: '', // CRITICAL: Never duplicate unique block identifier!
      remarks: ''
    };
    onChangeBlocks([...blocks, newBlock]);
  };

  const handleRemoveBlock = (index: number) => {
    if (blocks.length <= 1) {
      alert('कम से कम एक ब्लॉक का विवरण होना अनिवार्य है।');
      return;
    }
    const updated = blocks.filter((_, i) => i !== index);
    onChangeBlocks(updated);
  };

  const handleUpdateBlockField = (index: number, field: keyof StoneBlock, value: any) => {
    const updated = [...blocks];
    const current = { ...updated[index], [field]: value };

    // Re-calculate volume if dimensions or unit change
    if (field === 'length' || field === 'width' || field === 'height' || field === 'unit') {
      const l = field === 'length' ? Number(value) : Number(current.length);
      const w = field === 'width' ? Number(value) : Number(current.width);
      const h = field === 'height' ? Number(value) : Number(current.height);
      const u = field === 'unit' ? (value as MeasurementUnit) : current.unit;

      const { volumeCft } = calculateBlockVolume(l, w, h, u);
      current.estimatedVolume = volumeCft;
      current.volumeUnit = 'घन फीट (CFT)';
    }

    updated[index] = current;
    onChangeBlocks(updated);
  };

  // Calculate summary totals
  const totalPieces = blocks.reduce((acc, b) => acc + (Number(b.pieces) || 1), 0);
  const totalVolumeCft = blocks.reduce((acc, b) => acc + (Number(b.estimatedVolume) || 0), 0);

  return (
    <div className="space-y-5">
      
      {/* Block Summary Bar */}
      <div className="bg-teal-900 text-white p-4 rounded-2xl shadow-sm flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="text-xs text-teal-300 font-bold uppercase tracking-wider">
            माल एवं ब्लॉक सारांश (Summary)
          </div>
          <div className="text-lg sm:text-xl font-black mt-0.5">
            कुल {blocks.length} ब्लॉक ({totalPieces} टुकड़े)
          </div>
        </div>
        <div className="text-right">
          <div className="text-xs text-teal-300 font-bold uppercase tracking-wider">
            कुल अनुमानित आयतन
          </div>
          <div className="text-lg sm:text-xl font-mono font-black text-amber-300">
            {totalVolumeCft.toFixed(2)} CFT
          </div>
        </div>
      </div>

      {errors.blocks && (
        <div className="p-3 bg-red-100 border border-red-400 rounded-xl text-red-800 text-xs font-bold flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{errors.blocks}</span>
        </div>
      )}

      {/* Block Cards List */}
      <div className="space-y-4">
        {blocks.map((block, index) => {
          const { formulaLabel } = calculateBlockVolume(
            Number(block.length),
            Number(block.width),
            Number(block.height),
            block.unit
          );

          return (
            <div
              key={block.id}
              className="bg-white rounded-3xl border-2 border-slate-300 p-4 sm:p-5 shadow-sm space-y-4 relative"
            >
              {/* Card Header */}
              <div className="flex items-center justify-between border-b border-slate-200 pb-3">
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-xl bg-teal-800 text-amber-300 font-black text-sm flex items-center justify-center shrink-0">
                    #{index + 1}
                  </div>
                  <div>
                    <h4 className="font-extrabold text-base text-slate-900">
                      ब्लॉक विवरण (Block #{index + 1})
                    </h4>
                    <span className="text-[11px] text-slate-500 font-medium">
                      मूल रसीद फील्ड
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-1.5">
                  <button
                    type="button"
                    onClick={() => handleDuplicateBlock(index)}
                    className="px-2.5 py-1.5 rounded-xl bg-slate-100 hover:bg-teal-50 border border-slate-200 text-xs font-bold text-teal-800 flex items-center gap-1 transition cursor-pointer"
                    title="पिछले जैसा ब्लॉक जोड़ें"
                  >
                    <Copy className="w-3.5 h-3.5" />
                    <span className="hidden sm:inline">पिछले जैसा</span>
                  </button>

                  {blocks.length > 1 && (
                    <button
                      type="button"
                      onClick={() => handleRemoveBlock(index)}
                      className="p-1.5 rounded-xl text-red-500 hover:bg-red-50 hover:text-red-700 transition cursor-pointer"
                      title="यह ब्लॉक हटाएं"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>

              {/* Block Number & Pieces */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {/* Block ID */}
                <div className="sm:col-span-2">
                  <label className="block text-xs font-bold text-slate-700 mb-1">
                    ब्लॉक नंबर / मार्क (Block No. / Mark) <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={block.blockNumber || ''}
                    onChange={(e) => handleUpdateBlockField(index, 'blockNumber', e.target.value.toUpperCase())}
                    placeholder="उदा. M-104 / BLK-78"
                    className="w-full p-3 rounded-xl border-2 border-slate-300 focus:border-teal-600 text-base font-mono font-bold uppercase text-slate-900 outline-none"
                    style={{ minHeight: '48px' }}
                  />
                </div>

                {/* Number of Pieces */}
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">
                    टुकड़े (Pieces) <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="number"
                    inputMode="numeric"
                    min="1"
                    value={block.pieces ?? 1}
                    onChange={(e) => handleUpdateBlockField(index, 'pieces', Math.max(1, parseInt(e.target.value) || 1))}
                    className="w-full p-3 rounded-xl border-2 border-slate-300 focus:border-teal-600 text-base font-mono font-bold text-slate-900 outline-none text-center"
                    style={{ minHeight: '48px' }}
                  />
                </div>
              </div>

              {/* Variety / Description */}
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  मार्बल / पत्थर की किस्म (Stone Variety) <span className="text-red-500">*</span>
                </label>
                <select
                  value={block.variety || ''}
                  onChange={(e) => handleUpdateBlockField(index, 'variety', e.target.value)}
                  className="w-full p-3 rounded-xl border-2 border-slate-300 focus:border-teal-600 text-sm font-semibold text-slate-900 outline-none bg-white"
                  style={{ minHeight: '48px' }}
                >
                  {masters.varieties.map((v) => (
                    <option key={v} value={v}>{v}</option>
                  ))}
                  <option value="अन्य किस्म">अन्य (अन्य किस्म)</option>
                </select>
              </div>

              {/* Measurement Unit Selector */}
              <div>
                <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-1">
                  नाप की इकाई (Measurement Unit)
                </label>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-1.5">
                  {(['इंच (Inches)', 'फीट (Feet)', 'सेमी (cm)', 'मीटर (m)'] as MeasurementUnit[]).map((u) => {
                    const isSelected = block.unit === u;
                    return (
                      <button
                        type="button"
                        key={u}
                        onClick={() => handleUpdateBlockField(index, 'unit', u)}
                        className={`py-2 px-2 rounded-xl text-xs font-bold border text-center transition cursor-pointer ${
                          isSelected
                            ? 'bg-teal-700 border-teal-800 text-white shadow-xs'
                            : 'bg-slate-50 border-slate-200 text-slate-700 hover:bg-slate-100'
                        }`}
                        style={{ minHeight: '40px' }}
                      >
                        {u}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Dimensions: Length, Width, Height */}
              <div className="grid grid-cols-3 gap-2">
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">
                    लंबाई (L)
                  </label>
                  <div className="relative">
                    <input
                      type="number"
                      inputMode="decimal"
                      step="any"
                      min="0"
                      value={block.length === 0 ? '' : (block.length ?? '')}
                      onChange={(e) => handleUpdateBlockField(index, 'length', Math.max(0, parseFloat(e.target.value) || 0))}
                      placeholder="0"
                      className="w-full p-2.5 rounded-xl border-2 border-slate-300 focus:border-teal-600 text-base font-mono font-bold text-slate-900 text-center outline-none"
                      style={{ minHeight: '48px' }}
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">
                    चौड़ाई (W)
                  </label>
                  <div className="relative">
                    <input
                      type="number"
                      inputMode="decimal"
                      step="any"
                      min="0"
                      value={block.width === 0 ? '' : (block.width ?? '')}
                      onChange={(e) => handleUpdateBlockField(index, 'width', Math.max(0, parseFloat(e.target.value) || 0))}
                      placeholder="0"
                      className="w-full p-2.5 rounded-xl border-2 border-slate-300 focus:border-teal-600 text-base font-mono font-bold text-slate-900 text-center outline-none"
                      style={{ minHeight: '48px' }}
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">
                    ऊंचाई / मोटाई (H)
                  </label>
                  <div className="relative">
                    <input
                      type="number"
                      inputMode="decimal"
                      step="any"
                      min="0"
                      value={block.height === 0 ? '' : (block.height ?? '')}
                      onChange={(e) => handleUpdateBlockField(index, 'height', Math.max(0, parseFloat(e.target.value) || 0))}
                      placeholder="0"
                      className="w-full p-2.5 rounded-xl border-2 border-slate-300 focus:border-teal-600 text-base font-mono font-bold text-slate-900 text-center outline-none"
                      style={{ minHeight: '48px' }}
                    />
                  </div>
                </div>
              </div>

              {/* Calculated Estimated Volume Display (Clearly labeled as ESTIMATE) */}
              <div className="bg-amber-50/80 border border-amber-300 rounded-2xl p-3 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
                <div className="flex items-center gap-2 text-amber-900">
                  <Info className="w-4 h-4 text-amber-600 shrink-0" />
                  <span className="text-xs font-bold">
                    अनुमानित आयतन (Estimated Vol.):
                  </span>
                </div>
                <div className="text-right">
                  <div className="font-mono font-black text-sm sm:text-base text-amber-950">
                    {block.estimatedVolume.toFixed(2)} घन फीट (CFT)
                  </div>
                  <div className="text-[10px] text-amber-700 font-mono">
                    सूत्र: {formulaLabel}
                  </div>
                </div>
              </div>

              {/* Block Condition Selector */}
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1.5">
                  माल की स्थिति (Condition) <span className="text-red-500">*</span>
                </label>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-1.5">
                  {(['ठीक', 'टूटा हुआ', 'दरार', 'अन्य'] as BlockCondition[]).map((cond) => {
                    const isSelected = block.condition === cond;
                    let colorStyle = 'border-slate-200 text-slate-700';
                    if (isSelected) {
                      if (cond === 'ठीक') colorStyle = 'bg-emerald-100 border-emerald-600 text-emerald-950 font-black';
                      else if (cond === 'दरार') colorStyle = 'bg-amber-100 border-amber-600 text-amber-950 font-black';
                      else colorStyle = 'bg-red-100 border-red-600 text-red-950 font-black';
                    }
                    return (
                      <button
                        type="button"
                        key={cond}
                        onClick={() => handleUpdateBlockField(index, 'condition', cond)}
                        className={`py-2 px-2 rounded-xl text-xs border-2 text-center transition cursor-pointer ${colorStyle}`}
                        style={{ minHeight: '44px' }}
                      >
                        {cond}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Inspection Status Selector */}
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1.5">
                  स्वीकृति स्थिति (Inspection Status) <span className="text-red-500">*</span>
                </label>
                <div className="grid grid-cols-3 gap-1.5">
                  {(['स्वीकृत', 'जांच बाकी', 'अस्वीकृत'] as InspectionStatus[]).map((status) => {
                    const isSelected = block.inspectionStatus === status;
                    let style = 'bg-slate-50 border-slate-200 text-slate-700';
                    if (isSelected) {
                      if (status === 'स्वीकृत') style = 'bg-emerald-600 border-emerald-700 text-white font-black';
                      else if (status === 'जांच बाकी') style = 'bg-amber-500 border-amber-600 text-slate-950 font-black';
                      else style = 'bg-red-600 border-red-700 text-white font-black';
                    }
                    return (
                      <button
                        type="button"
                        key={status}
                        onClick={() => handleUpdateBlockField(index, 'inspectionStatus', status)}
                        className={`py-2 px-2 rounded-xl text-xs border text-center transition cursor-pointer ${style}`}
                        style={{ minHeight: '44px' }}
                      >
                        {status}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Remarks for this block */}
              <div>
                <label className="block text-xs font-bold text-slate-600 mb-1">
                  ब्लॉक पर विशेष टिप्पणी (Remarks - यदि कोई हो)
                </label>
                <input
                  type="text"
                  value={block.remarks || ''}
                  onChange={(e) => handleUpdateBlockField(index, 'remarks', e.target.value)}
                  placeholder="उदा. कोने पर थोड़ा चिप, रफ कट, आदि"
                  className="w-full p-2.5 rounded-xl border border-slate-300 focus:border-teal-600 text-xs text-slate-900 outline-none"
                  style={{ minHeight: '42px' }}
                />
              </div>

            </div>
          );
        })}
      </div>

      {/* Action Buttons to Add More Blocks */}
      <div className="flex flex-col sm:flex-row gap-2 pt-2">
        <button
          type="button"
          onClick={handleAddBlock}
          className="flex-1 py-4 bg-teal-800 hover:bg-teal-900 text-white font-extrabold text-base rounded-2xl shadow-md transition active:scale-98 flex items-center justify-center gap-2 cursor-pointer"
          style={{ minHeight: '52px' }}
        >
          <Plus className="w-5 h-5 text-amber-300" />
          <span>+ एक और ब्लॉक जोड़ें</span>
        </button>

        {blocks.length > 0 && (
          <button
            type="button"
            onClick={() => handleDuplicateBlock(blocks.length - 1)}
            className="py-4 px-6 bg-slate-100 hover:bg-slate-200 border-2 border-slate-300 text-slate-800 font-bold text-sm rounded-2xl transition active:scale-98 flex items-center justify-center gap-2 cursor-pointer"
            style={{ minHeight: '52px' }}
          >
            <Copy className="w-4 h-4 text-teal-700" />
            <span>पिछले जैसा जोड़ें</span>
          </button>
        )}
      </div>

    </div>
  );
};
