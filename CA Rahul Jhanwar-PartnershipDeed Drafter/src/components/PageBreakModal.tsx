import React from 'react';
import { 
  Scissors, 
  X, 
  RotateCcw, 
  Check, 
  FileText, 
  Layers, 
  Type, 
  Sparkles,
  Info,
  CheckCircle2,
  BookOpen,
  Hash,
  ShieldCheck
} from 'lucide-react';
import { DeedFormData } from '../types';
import { getDeedClauseList } from '../utils/deedEngine';

interface PageBreakModalProps {
  isOpen: boolean;
  onClose: () => void;
  formData: DeedFormData;
  onUpdateFormData: (updates: Partial<DeedFormData>) => void;
}

export const PageBreakModal: React.FC<PageBreakModalProps> = ({
  isOpen,
  onClose,
  formData,
  onUpdateFormData,
}) => {
  if (!isOpen) return null;

  const clauses = getDeedClauseList(formData);
  const activeBreaks = formData.pageBreakBeforeClauses || [];
  const sigPlacement = formData.signaturePageBreak || 'continuous';
  const density = formData.documentDensity || 'compact';
  const fontSize = formData.fontSize || '12pt';

  const handleToggleClauseBreak = (clauseId: string) => {
    let nextBreaks: string[];
    if (activeBreaks.includes(clauseId)) {
      nextBreaks = activeBreaks.filter(id => id !== clauseId);
    } else {
      nextBreaks = [...activeBreaks, clauseId];
    }
    onUpdateFormData({ pageBreakBeforeClauses: nextBreaks });
  };

  const handleSignaturePlacementChange = (mode: 'continuous' | 'newPage') => {
    onUpdateFormData({ 
      signaturePageBreak: mode,
      pageBreakBeforeClauses: mode === 'continuous' 
        ? activeBreaks.filter(id => id !== 'signatures')
        : activeBreaks
    });
  };

  const handleClearAllBreaks = () => {
    onUpdateFormData({
      pageBreakBeforeClauses: [],
      signaturePageBreak: 'continuous'
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4 overflow-y-auto">
      <div className="bg-white w-full max-w-2xl rounded-2xl shadow-2xl border border-slate-200 overflow-hidden flex flex-col max-h-[90vh] animate-in fade-in zoom-in-95 duration-150">
        
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 bg-slate-50/80">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-100 text-blue-700 flex items-center justify-center font-bold">
              <Scissors className="w-5 h-5 text-blue-700" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">
                Page Breaks & Document Pagination
              </h3>
              <p className="text-xs text-slate-500">
                Determine exact page changes, eliminate blank gaps & control stamp paper fit
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-200/60 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Scrollable Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          
          {/* 0. Front Cover Page Setting */}
          <div className="space-y-3 bg-indigo-50/50 p-4 rounded-xl border border-indigo-100">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold text-indigo-950 uppercase tracking-wider flex items-center gap-1.5">
                <BookOpen className="w-3.5 h-3.5 text-indigo-600" />
                <span>Front Cover Page (Title Page)</span>
              </label>
              <button
                type="button"
                onClick={() => onUpdateFormData({ includeCoverPage: formData.includeCoverPage === false ? true : false })}
                className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-hidden ${
                  formData.includeCoverPage !== false ? 'bg-indigo-600' : 'bg-slate-300'
                }`}
              >
                <span
                  className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow-sm ring-0 transition duration-200 ease-in-out ${
                    formData.includeCoverPage !== false ? 'translate-x-4' : 'translate-x-0'
                  }`}
                />
              </button>
            </div>

            <p className="text-[11px] text-indigo-900/80 leading-relaxed">
              Generates a formal front cover page containing <b>PARTNERSHIP DEED OF {formData.firmName || 'M/S. [FIRM NAME]'}</b>, partner names, commencement date & place before the first deed clause.
            </p>

            {formData.includeCoverPage !== false && (
              <div className="space-y-3 pt-2 text-xs">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                      Cover Page Title Heading
                    </label>
                    <input
                      type="text"
                      value={formData.coverPageTitle || 'PARTNERSHIP DEED'}
                      onChange={(e) => onUpdateFormData({ coverPageTitle: e.target.value.toUpperCase() })}
                      placeholder="PARTNERSHIP DEED"
                      className="w-full px-3 py-1.5 bg-white border border-slate-300 rounded-lg text-xs font-semibold text-slate-900 uppercase focus:ring-2 focus:ring-indigo-500 outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                      Drafted / Prepared By Note
                    </label>
                    <input
                      type="text"
                      value={formData.coverPagePreparedBy || ''}
                      onChange={(e) => onUpdateFormData({ coverPagePreparedBy: e.target.value.toUpperCase() })}
                      placeholder="ADVOCATE / CHARTERED ACCOUNTANT"
                      className="w-full px-3 py-1.5 bg-white border border-slate-300 rounded-lg text-xs text-slate-900 uppercase focus:ring-2 focus:ring-indigo-500 outline-none"
                    />
                  </div>
                </div>

                <div className="flex items-center justify-between pt-1 border-t border-indigo-100">
                  <div className="text-[11px] text-slate-700">
                    <span className="font-semibold">Official Registrar / RoF Filing Box</span>
                    <span className="text-slate-500 block text-[10px]">Include blank Book/Volume/Reg No footer box</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => onUpdateFormData({ includeCoverRegistrationBox: !formData.includeCoverRegistrationBox })}
                    className={`relative inline-flex h-4 w-8 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-hidden ${
                      formData.includeCoverRegistrationBox ? 'bg-indigo-600' : 'bg-slate-300'
                    }`}
                  >
                    <span
                      className={`pointer-events-none inline-block h-3 w-3 transform rounded-full bg-white shadow-sm ring-0 transition duration-200 ease-in-out ${
                        formData.includeCoverRegistrationBox ? 'translate-x-4' : 'translate-x-0'
                      }`}
                    />
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Mandatory Page Numbering ("Page 1 of 2") Setting */}
          <div className="space-y-3 bg-emerald-50/50 p-4 rounded-xl border border-emerald-200">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold text-emerald-950 uppercase tracking-wider flex items-center gap-1.5">
                <Hash className="w-3.5 h-3.5 text-emerald-600" />
                <span>Page Numbering (Mandatory on Deed Pages)</span>
              </label>
              <span className="text-[10px] font-bold bg-emerald-600 text-white px-2 py-0.5 rounded-full uppercase tracking-wider">
                {formData.includeCoverInPageNumbering ? 'Cover + Deed Counted' : 'Deed Text Counted'}
              </span>
            </div>

            <p className="text-[11px] text-emerald-900/80 leading-relaxed">
              {formData.includeCoverInPageNumbering
                ? 'Front cover is counted as Page 1. Deed pages continue numbering through to the final signatures/annexure page (e.g., Page 5 of 5).'
                : `Front cover title sheet is excluded from numbering. Deed clauses start from Page 1, continuing through all clauses and signatures.`}
            </p>

            <div className="flex items-center justify-between pt-1 pb-1 px-3 bg-white/70 rounded-lg border border-emerald-200/80 text-xs">
              <span className="text-[11px] font-semibold text-emerald-900">
                Include Cover Page in Page Count & Numbering
              </span>
              <button
                type="button"
                onClick={() => onUpdateFormData({ includeCoverInPageNumbering: !Boolean(formData.includeCoverInPageNumbering) })}
                className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-hidden ${
                  Boolean(formData.includeCoverInPageNumbering) ? 'bg-emerald-600' : 'bg-slate-300'
                }`}
              >
                <span
                  className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow-sm ring-0 transition duration-200 ease-in-out ${
                    Boolean(formData.includeCoverInPageNumbering) ? 'translate-x-4' : 'translate-x-0'
                  }`}
                />
              </button>
            </div>

            <div className="space-y-3 pt-2 text-xs">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                    Numbering Format
                  </label>
                  <select
                    value={formData.pageNumberFormat || 'page_x_of_y'}
                    onChange={(e) => onUpdateFormData({ pageNumberFormat: e.target.value as any })}
                    className="w-full px-2.5 py-1.5 bg-white border border-slate-300 rounded-lg text-xs font-semibold text-slate-900 focus:ring-2 focus:ring-emerald-500 outline-none"
                  >
                    <option value="page_x_of_y">Page 1 of {formData.customTotalPages || 'Auto'}</option>
                    <option value="page_x">Page 1</option>
                    <option value="hyphen_x">- 1 -</option>
                  </select>
                </div>

                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label className="block text-[11px] font-semibold text-slate-700">
                      Total Deed Pages
                    </label>
                    {formData.customTotalPages && (
                      <button
                        type="button"
                        onClick={() => onUpdateFormData({ customTotalPages: '' })}
                        className="text-[10px] text-emerald-700 font-bold hover:underline"
                      >
                        Reset to Auto
                      </button>
                    )}
                  </div>
                  <input
                    type="text"
                    value={formData.customTotalPages || ''}
                    onChange={(e) => onUpdateFormData({ customTotalPages: e.target.value.replace(/[^0-9]/g, '') })}
                    placeholder="Auto (Calculated)"
                    className="w-full px-3 py-1.5 bg-white border border-slate-300 rounded-lg text-xs font-bold text-slate-900 text-center focus:ring-2 focus:ring-emerald-500 outline-none placeholder:text-slate-400 placeholder:font-normal"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                    Start Page No.
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="99"
                    value={formData.startPageNumber || 1}
                    onChange={(e) => onUpdateFormData({ startPageNumber: parseInt(e.target.value, 10) || 1 })}
                    className="w-full px-3 py-1.5 bg-white border border-slate-300 rounded-lg text-xs font-bold text-slate-900 text-center focus:ring-2 focus:ring-emerald-500 outline-none"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Partner ID Proof Copies Annexure */}
          <div className="space-y-3 bg-teal-50/50 p-4 rounded-xl border border-teal-200">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold text-teal-950 uppercase tracking-wider flex items-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5 text-teal-700" />
                <span>Annexure: Compiled Partner ID Proof Copies (PAN & Aadhaar)</span>
              </label>
              <button
                type="button"
                onClick={() => onUpdateFormData({ includeKycAnnexure: !Boolean(formData.includeKycAnnexure) })}
                className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-hidden ${
                  Boolean(formData.includeKycAnnexure) ? 'bg-teal-600' : 'bg-slate-300'
                }`}
              >
                <span
                  className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow-sm ring-0 transition duration-200 ease-in-out ${
                    Boolean(formData.includeKycAnnexure) ? 'translate-x-4' : 'translate-x-0'
                  }`}
                />
              </button>
            </div>

            <p className="text-[11px] text-teal-900/80 leading-relaxed">
              Appends a single compiled document page containing only the copies of PAN Card and Aadhaar Card (front & back) for all partners, scaled down to fit on ONE single page. Statutory Notary Attestation and endorsement boxes are excluded.
            </p>
          </div>

          {/* 1. Signature Flow Setting */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
                <FileText className="w-3.5 h-3.5 text-blue-600" />
                <span>1. Signature & Partner Photo Placement</span>
              </label>
              {sigPlacement === 'continuous' && (
                <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                  <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                  Zero Blank Gap
                </span>
              )}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {/* Continuous Flow Option */}
              <div 
                onClick={() => handleSignaturePlacementChange('continuous')}
                className={`cursor-pointer p-3.5 rounded-xl border transition flex flex-col justify-between ${
                  sigPlacement === 'continuous'
                    ? 'border-blue-600 bg-blue-50/50 shadow-xs'
                    : 'border-slate-200 hover:border-slate-300 bg-white'
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="space-y-1">
                    <span className="font-bold text-xs text-slate-900 flex items-center gap-1.5">
                      Continuous Flow
                      <span className="text-[10px] bg-blue-100 text-blue-700 px-1.5 py-0.2 rounded font-medium">Recommended</span>
                    </span>
                    <p className="text-[11px] text-slate-600 leading-relaxed">
                      Signatures and partner photos immediately follow Point 13 / last clause without forcing a new page. Eliminates the blank space on legal paper.
                    </p>
                  </div>
                  <div className={`w-4 h-4 rounded-full border flex items-center justify-center mt-0.5 shrink-0 ${
                    sigPlacement === 'continuous' ? 'border-blue-600 bg-blue-600 text-white' : 'border-slate-300'
                  }`}>
                    {sigPlacement === 'continuous' && <Check className="w-3 h-3 stroke-[3]" />}
                  </div>
                </div>
              </div>

              {/* Force New Page Option */}
              <div 
                onClick={() => handleSignaturePlacementChange('newPage')}
                className={`cursor-pointer p-3.5 rounded-xl border transition flex flex-col justify-between ${
                  sigPlacement === 'newPage'
                    ? 'border-blue-600 bg-blue-50/50 shadow-xs'
                    : 'border-slate-200 hover:border-slate-300 bg-white'
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="space-y-1">
                    <span className="font-bold text-xs text-slate-900">
                      Force onto New Page
                    </span>
                    <p className="text-[11px] text-slate-600 leading-relaxed">
                      Always forces the execution block, partner photo boxes, and witness signatures to start cleanly on a fresh new page.
                    </p>
                  </div>
                  <div className={`w-4 h-4 rounded-full border flex items-center justify-center mt-0.5 shrink-0 ${
                    sigPlacement === 'newPage' ? 'border-blue-600 bg-blue-600 text-white' : 'border-slate-300'
                  }`}>
                    {sigPlacement === 'newPage' && <Check className="w-3 h-3 stroke-[3]" />}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* 2. Document Spacing Density & Font Size */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2 border-t border-slate-100">
            {/* Spacing Density */}
            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5 text-blue-600" />
                <span>2. Line Spacing Density</span>
              </label>
              <div className="grid grid-cols-3 gap-1.5 bg-slate-100 p-1 rounded-xl border border-slate-200">
                {[
                  { key: 'tight', label: 'Tight', desc: 'Max fit' },
                  { key: 'compact', label: 'Compact', desc: 'Standard' },
                  { key: 'standard', label: 'Spacious', desc: 'Open' }
                ].map(item => (
                  <button
                    key={item.key}
                    type="button"
                    onClick={() => onUpdateFormData({ documentDensity: item.key as any })}
                    className={`py-1.5 px-2 rounded-lg text-xs font-bold transition flex flex-col items-center justify-center ${
                      density === item.key 
                        ? 'bg-white text-blue-700 shadow-xs' 
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    <span>{item.label}</span>
                    <span className="text-[9px] font-normal opacity-75">{item.desc}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Font Size */}
            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
                <Type className="w-3.5 h-3.5 text-blue-600" />
                <span>3. Typography Scale</span>
              </label>
              <div className="grid grid-cols-3 gap-1.5 bg-slate-100 p-1 rounded-xl border border-slate-200">
                {[
                  { key: '11pt', label: '11 pt', desc: 'Dense' },
                  { key: '12pt', label: '12 pt', desc: 'Standard' },
                  { key: '13pt', label: '13 pt', desc: 'Large' }
                ].map(item => (
                  <button
                    key={item.key}
                    type="button"
                    onClick={() => onUpdateFormData({ fontSize: item.key as any })}
                    className={`py-1.5 px-2 rounded-lg text-xs font-bold transition flex flex-col items-center justify-center ${
                      fontSize === item.key 
                        ? 'bg-white text-blue-700 shadow-xs' 
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    <span>{item.label}</span>
                    <span className="text-[9px] font-normal opacity-75">{item.desc}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* 3. Clause-by-Clause Page Break Selector */}
          <div className="space-y-3 pt-2 border-t border-slate-100">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
                <Scissors className="w-3.5 h-3.5 text-blue-600" />
                <span>4. Manual Clause Page Breaks (Where to Split)</span>
              </label>
              {activeBreaks.length > 0 && (
                <button
                  type="button"
                  onClick={handleClearAllBreaks}
                  className="text-[11px] text-red-600 hover:text-red-800 font-semibold flex items-center gap-1 hover:underline"
                >
                  <RotateCcw className="w-3 h-3" />
                  Clear all breaks ({activeBreaks.length})
                </button>
              )}
            </div>

            <p className="text-xs text-slate-500">
              Click the switch next to any clause below to force that clause to start at the top of a new page.
            </p>

            <div className="divide-y divide-slate-100 border border-slate-200 rounded-xl overflow-hidden bg-white max-h-64 overflow-y-auto">
              {clauses.map((clause) => {
                const isSignatures = clause.id === 'signatures';
                const isSelected = isSignatures 
                  ? (sigPlacement === 'newPage' || activeBreaks.includes('signatures'))
                  : activeBreaks.includes(clause.id);

                return (
                  <div 
                    key={clause.id}
                    className={`flex items-center justify-between px-3.5 py-2.5 transition text-xs ${
                      isSelected ? 'bg-blue-50/60 font-semibold text-blue-900' : 'hover:bg-slate-50 text-slate-700'
                    }`}
                  >
                    <div className="flex items-center gap-2.5 truncate pr-2">
                      <span className={`text-xs ${isSelected ? 'text-blue-600 font-bold' : 'text-slate-400'}`}>
                        {isSelected ? '✂️ [BREAK]' : '•'}
                      </span>
                      <span className="truncate">{clause.title}</span>
                    </div>

                    <button
                      type="button"
                      onClick={() => {
                        if (isSignatures) {
                          handleSignaturePlacementChange(sigPlacement === 'newPage' ? 'continuous' : 'newPage');
                        } else {
                          handleToggleClauseBreak(clause.id);
                        }
                      }}
                      className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-hidden ${
                        isSelected ? 'bg-blue-600' : 'bg-slate-200'
                      }`}
                    >
                      <span
                        className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow-sm ring-0 transition duration-200 ease-in-out ${
                          isSelected ? 'translate-x-4' : 'translate-x-0'
                        }`}
                      />
                    </button>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Legal Paper Tip */}
          <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5 text-xs text-slate-600 flex items-start gap-2.5">
            <Info className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <p className="font-semibold text-slate-800">
                Indian Stamp Paper Compliance Note:
              </p>
              <p className="leading-relaxed">
                By setting <b>Continuous Flow</b> and <b>Compact</b> spacing, your Deed of Partnership flows naturally without blank gaps before signatures, making it easy to fit into 2-3 standard Non-Judicial stamp sheets.
              </p>
            </div>
          </div>

        </div>

        {/* Footer */}
        <div className="px-6 py-3.5 bg-slate-50 border-t border-slate-200 flex items-center justify-between">
          <div className="text-xs text-slate-500 font-medium">
            {activeBreaks.length === 0 && sigPlacement === 'continuous' ? (
              <span className="text-emerald-700 font-semibold">✓ Continuous flow (No manual breaks)</span>
            ) : (
              <span>{activeBreaks.length + (sigPlacement === 'newPage' ? 1 : 0)} page breaks configured</span>
            )}
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-xs font-bold text-white transition shadow-xs"
            >
              Apply & Update Preview
            </button>
          </div>
        </div>

      </div>
    </div>
  );
};
