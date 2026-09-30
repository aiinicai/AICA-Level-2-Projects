import React, { useState, useMemo } from 'react';
import {
  X,
  BookOpen,
  Search,
  Filter,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  Calculator,
  Calendar,
  Layers,
  ArrowRight
} from 'lucide-react';
import { TDS_SECTIONS_2025, TDSSection2025, calculateExpectedTDS } from '../../data/tdsSections2025';
import { formatINR } from '../../utils/formatters';

interface TDSSections2025ModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const TDSSections2025Modal: React.FC<TDSSections2025ModalProps> = ({
  isOpen,
  onClose
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('All');
  const [selectedSection, setSelectedSection] = useState<TDSSection2025 | null>(null);

  // Interactive Calculator State
  const [calcAmount, setCalcAmount] = useState<number>(100000);
  const [calcSectionCode, setCalcSectionCode] = useState<string>('194C');
  const [calcEntityType, setCalcEntityType] = useState<'Company' | 'Individual'>('Company');

  const categories = useMemo(() => {
    const set = new Set<string>();
    TDS_SECTIONS_2025.forEach(s => set.add(s.category));
    return ['All', ...Array.from(set)];
  }, []);

  const filteredSections = useMemo(() => {
    return TDS_SECTIONS_2025.filter(s => {
      const matchCat = selectedCategory === 'All' || s.category === selectedCategory;
      const matchSearch =
        s.section.toLowerCase().includes(searchTerm.toLowerCase()) ||
        s.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        s.natureOfPayment.toLowerCase().includes(searchTerm.toLowerCase()) ||
        s.keyNotes.toLowerCase().includes(searchTerm.toLowerCase());
      return matchCat && matchSearch;
    });
  }, [selectedCategory, searchTerm]);

  const calcResult = useMemo(() => {
    return calculateExpectedTDS(calcAmount, calcSectionCode, calcEntityType);
  }, [calcAmount, calcSectionCode, calcEntityType]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="bg-white w-full max-w-5xl rounded-2xl shadow-2xl border border-slate-200 overflow-hidden flex flex-col max-h-[92vh]">
        {/* Header */}
        <div className="p-4 sm:p-5 border-b border-slate-200 bg-linear-to-r from-emerald-900 to-slate-900 text-white flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-emerald-500/20 text-emerald-300 border border-emerald-400/30">
              <BookOpen className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-bold text-base sm:text-lg tracking-tight">Income Tax TDS Master Guide (FY 2026-27 Compliance)</h3>
                <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-400/30">
                  FY 2026-27 / AY 2027-28
                </span>
              </div>
              <p className="text-xs text-slate-300 mt-0.5">
                Full statutory coverage of all TDS sections under the Income-tax Act, 1961 with Budget 2024 & 2025 rationalizations.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-white/10 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6">
          {/* Quick Interactive TDS Calculator */}
          <div className="bg-linear-to-br from-emerald-50 to-teal-50 border border-emerald-200 rounded-xl p-4 sm:p-5">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-bold uppercase tracking-wider text-emerald-900 flex items-center gap-1.5">
                <Calculator className="w-4 h-4 text-emerald-700" />
                Live 2025 TDS Calculator & Section Validator
              </span>
              <span className="text-[11px] text-emerald-800 font-medium">Automatic threshold & rate deduction</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 text-xs">
              <div>
                <label className="font-bold text-slate-700 block mb-1">Taxable Amount (₹)</label>
                <input
                  type="number"
                  value={calcAmount}
                  onChange={(e) => setCalcAmount(parseFloat(e.target.value) || 0)}
                  className="w-full p-2 font-mono font-bold rounded-lg border border-emerald-300 bg-white focus:outline-hidden focus:ring-2 focus:ring-emerald-500/20"
                />
              </div>

              <div>
                <label className="font-bold text-slate-700 block mb-1">Select TDS Section</label>
                <select
                  value={calcSectionCode}
                  onChange={(e) => setCalcSectionCode(e.target.value)}
                  className="w-full p-2 font-semibold rounded-lg border border-emerald-300 bg-white"
                >
                  {TDS_SECTIONS_2025.map((s) => (
                    <option key={s.section} value={s.section}>
                      Sec {s.section} - {s.name.slice(0, 35)}...
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="font-bold text-slate-700 block mb-1">Deductee Entity Type</label>
                <select
                  value={calcEntityType}
                  onChange={(e) => setCalcEntityType(e.target.value as any)}
                  className="w-full p-2 font-semibold rounded-lg border border-emerald-300 bg-white"
                >
                  <option value="Company">Company / Corporate / LLP</option>
                  <option value="Individual">Individual / HUF / Proprietor</option>
                </select>
              </div>

              <div className="bg-white p-2.5 rounded-lg border border-emerald-200 flex flex-col justify-center">
                <span className="text-[10px] uppercase font-bold text-slate-400">Computed 2025 TDS</span>
                <div className="flex items-baseline gap-2 mt-0.5">
                  <span className="text-base font-bold font-mono text-emerald-800">
                    {formatINR(calcResult.tdsAmount)}
                  </span>
                  <span className="text-[11px] font-bold text-slate-500">
                    @{calcResult.rate}%
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Search & Category Filter */}
          <div className="flex flex-col sm:flex-row items-center gap-3">
            <div className="relative flex-1 w-full">
              <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
              <input
                type="text"
                placeholder="Search by section (e.g. 194C, 194J, 194Q, 194T), keywords, nature of payment..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-9 pr-4 py-2 text-xs rounded-xl border border-slate-200 focus:outline-hidden focus:border-emerald-600 bg-slate-50/50"
              />
            </div>

            <div className="flex items-center gap-2 w-full sm:w-auto">
              <Filter className="w-4 h-4 text-slate-400 shrink-0" />
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className="w-full sm:w-48 text-xs p-2 rounded-xl border border-slate-200 bg-white font-medium"
              >
                {categories.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
          </div>

          {/* TDS Sections Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filteredSections.map((sec) => (
              <div
                key={sec.section}
                className="bg-white p-4 rounded-xl border border-slate-200 hover:border-emerald-300 hover:shadow-md transition-all text-xs flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 rounded-md font-mono font-bold bg-emerald-100 text-emerald-900 border border-emerald-300 text-xs">
                        Sec {sec.section}
                      </span>
                      <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-600">
                        {sec.category}
                      </span>
                    </div>
                    <span className="text-[10px] text-emerald-800 font-semibold bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                      {sec.effectiveDate}
                    </span>
                  </div>

                  <h4 className="font-bold text-slate-900 text-sm">{sec.name}</h4>
                  <p className="text-slate-600 text-xs mt-1 leading-relaxed">{sec.natureOfPayment}</p>

                  <div className="grid grid-cols-3 gap-2 my-3 p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                    <div>
                      <span className="text-[10px] text-slate-400 block font-semibold">Ind / HUF</span>
                      <p className="font-mono font-bold text-slate-900 text-xs mt-0.5">{sec.rateIndHuf}%</p>
                    </div>
                    <div>
                      <span className="text-[10px] text-slate-400 block font-semibold">Corporate / Other</span>
                      <p className="font-mono font-bold text-slate-900 text-xs mt-0.5">{sec.rateOthers}%</p>
                    </div>
                    <div>
                      <span className="text-[10px] text-slate-400 block font-semibold">Threshold</span>
                      <p className="font-mono font-bold text-emerald-700 text-xs mt-0.5">
                        {sec.thresholdLimit > 0 ? formatINR(sec.thresholdLimit) : 'NIL'}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="pt-2 border-t border-slate-100">
                  <p className="text-[11px] text-slate-500 italic">
                    <strong className="text-slate-700 not-italic font-semibold">Compliance Note: </strong>
                    {sec.keyNotes}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-200 bg-slate-50 flex items-center justify-between">
          <p className="text-xs text-slate-500">
            Total Sections Covered: <strong>{TDS_SECTIONS_2025.length}</strong> • Income Tax Act & Finance (No. 2) Act 2024
          </p>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-900 text-white rounded-lg font-bold text-xs shadow-xs"
          >
            Close Guide
          </button>
        </div>
      </div>
    </div>
  );
};
