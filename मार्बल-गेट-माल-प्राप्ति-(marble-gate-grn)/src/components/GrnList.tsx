import React, { useState, useMemo } from 'react';
import { GoodsReceiptNote, MasterData, FactorySettings, UserAccount } from '../types/grn';
import { Search, Filter, Calendar, Truck, Building, FileText, ArrowLeft, Printer, Eye, Download, ShieldCheck, AlertCircle, RefreshCw } from 'lucide-react';

interface GrnListProps {
  grns: GoodsReceiptNote[];
  masters: MasterData;
  currentUser: UserAccount;
  onSelectGrn: (grn: GoodsReceiptNote) => void;
  onBack: () => void;
  onRefresh: () => void;
  isSyncing: boolean;
}

export const GrnList: React.FC<GrnListProps> = ({
  grns,
  masters,
  currentUser,
  onSelectGrn,
  onBack,
  onRefresh,
  isSyncing,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('सभी');
  const [supplierFilter, setSupplierFilter] = useState<string>('सभी');
  const [dateFilter, setDateFilter] = useState<string>(''); // YYYY-MM-DD
  const [showFilters, setShowFilters] = useState(false);

  // Filtered GRNs
  const filteredGrns = useMemo(() => {
    return grns.filter((g) => {
      // Search term matches GRN no, supplier, vehicle, challan, driver, or block numbers
      if (searchTerm.trim()) {
        const q = searchTerm.trim().toLowerCase();
        const matchGrn = g.grnNumber.toLowerCase().includes(q);
        const matchSupplier = g.supplierName.toLowerCase().includes(q);
        const matchVehicle = g.vehicleNumber.toLowerCase().includes(q);
        const matchChallan = g.challanNumber.toLowerCase().includes(q);
        const matchDriver = g.driverName.toLowerCase().includes(q);
        const matchBlocks = g.blocks.some(b => 
          b.blockNumber.toLowerCase().includes(q) ||
          b.variety.toLowerCase().includes(q)
        );

        if (!matchGrn && !matchSupplier && !matchVehicle && !matchChallan && !matchDriver && !matchBlocks) {
          return false;
        }
      }

      // Status filter
      if (statusFilter !== 'सभी' && g.status !== statusFilter) {
        return false;
      }

      // Supplier filter
      if (supplierFilter !== 'सभी' && g.supplierName !== supplierFilter) {
        return false;
      }

      // Date filter
      if (dateFilter && g.date !== dateFilter) {
        return false;
      }

      return true;
    });
  }, [grns, searchTerm, statusFilter, supplierFilter, dateFilter]);

  const clearAllFilters = () => {
    setSearchTerm('');
    setStatusFilter('सभी');
    setSupplierFilter('सभी');
    setDateFilter('');
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
      
      {/* Header & Back */}
      <div className="bg-white rounded-3xl p-4 sm:p-5 border border-slate-200 shadow-sm flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <button
            onClick={onBack}
            className="p-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-800 transition cursor-pointer"
            title="वापस जाएं"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h2 className="text-xl sm:text-2xl font-black text-slate-900">
              माल प्राप्ति रसीद रिकॉर्ड (GRN History)
            </h2>
            <p className="text-xs text-slate-500 font-medium">
              कुल {grns.length} रसीदें उपलब्ध हैं (खोजे गए: {filteredGrns.length})
            </p>
          </div>
        </div>

        <button
          onClick={onRefresh}
          disabled={isSyncing}
          className="flex items-center gap-1.5 px-3.5 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-xs rounded-xl transition cursor-pointer"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isSyncing ? 'animate-spin' : ''}`} />
          <span>ताजा करें</span>
        </button>
      </div>

      {/* Search & Filter Bar */}
      <div className="bg-white rounded-3xl p-4 border border-slate-200 shadow-sm space-y-3">
        
        {/* Search Input */}
        <div className="relative">
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="रसीद सं, गाड़ी नं, सप्लायर, चालान या ब्लॉक नंबर खोजें..."
            className="w-full pl-11 pr-4 py-3.5 rounded-2xl border-2 border-slate-300 focus:border-teal-600 text-base text-slate-900 outline-none"
            style={{ minHeight: '48px' }}
          />
          <Search className="w-5 h-5 text-slate-400 absolute left-4 top-1/2 -translate-y-1/2" />
        </div>

        {/* Quick Filter Buttons & Toggle */}
        <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
          <div className="flex flex-wrap gap-1.5">
            {['सभी', 'स्वीकृत', 'जांच बाकी', 'रद्द'].map((status) => {
              const isSelected = statusFilter === status;
              return (
                <button
                  key={status}
                  onClick={() => setStatusFilter(status)}
                  className={`px-3 py-1.5 rounded-xl text-xs font-bold transition cursor-pointer ${
                    isSelected
                      ? 'bg-teal-700 text-white shadow-xs'
                      : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                  }`}
                >
                  {status}
                </button>
              );
            })}
          </div>

          <button
            onClick={() => setShowFilters(!showFilters)}
            className="flex items-center gap-1 text-xs font-bold text-teal-800 hover:underline cursor-pointer"
          >
            <Filter className="w-3.5 h-3.5" />
            <span>{showFilters ? 'अतिरिक्त फ़िल्टर छुपाएं' : 'अतिरिक्त फ़िल्टर'}</span>
          </button>
        </div>

        {/* Extended Filter Dropdowns */}
        {showFilters && (
          <div className="pt-3 border-t border-slate-100 grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
            <div>
              <label className="block font-bold text-slate-600 mb-1">सप्लायर चुनें:</label>
              <select
                value={supplierFilter}
                onChange={(e) => setSupplierFilter(e.target.value)}
                className="w-full p-2.5 rounded-xl border border-slate-300 text-slate-800 bg-white"
              >
                <option value="सभी">सभी सप्लायर</option>
                {masters.suppliers.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block font-bold text-slate-600 mb-1">दिनांक चुनें:</label>
              <input
                type="date"
                value={dateFilter}
                onChange={(e) => setDateFilter(e.target.value)}
                className="w-full p-2.5 rounded-xl border border-slate-300 text-slate-800"
              />
            </div>

            {(supplierFilter !== 'सभी' || dateFilter || searchTerm) && (
              <div className="sm:col-span-2 text-right">
                <button
                  onClick={clearAllFilters}
                  className="text-xs font-bold text-red-600 hover:underline"
                >
                  सभी फ़िल्टर साफ़ करें
                </button>
              </div>
            )}
          </div>
        )}

      </div>

      {/* Receipts List */}
      <div className="space-y-3">
        {filteredGrns.length === 0 ? (
          <div className="bg-white rounded-3xl p-10 text-center border border-slate-200 shadow-sm space-y-3">
            <div className="w-16 h-16 rounded-full bg-slate-100 mx-auto flex items-center justify-center text-slate-400">
              <FileText className="w-8 h-8" />
            </div>
            <h3 className="text-lg font-bold text-slate-800">कोई रसीद नहीं मिली</h3>
            <p className="text-xs text-slate-500">
              दिए गए खोज या फ़िल्टर के अनुसार कोई माल प्राप्ति रसीद उपलब्ध नहीं है।
            </p>
          </div>
        ) : (
          filteredGrns.map((g) => {
            const isCancelled = g.status === 'रद्द';
            return (
              <div
                key={g.id}
                onClick={() => onSelectGrn(g)}
                className={`rounded-3xl p-5 border-2 transition cursor-pointer shadow-sm hover:shadow-md ${
                  isCancelled
                    ? 'bg-red-50/40 border-red-200 opacity-80'
                    : g.isProvisional
                    ? 'bg-amber-50/50 border-amber-300'
                    : 'bg-white border-slate-200 hover:border-teal-500'
                }`}
              >
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-slate-100 pb-3">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-teal-800 text-amber-300 font-mono font-black text-sm flex items-center justify-center shrink-0">
                      GRN
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-black text-base sm:text-lg text-slate-900">
                          {g.grnNumber}
                        </span>
                        {g.isProvisional && (
                          <span className="px-2 py-0.5 rounded-full bg-amber-500 text-slate-950 text-[10px] font-black uppercase">
                            अस्थायी — सिंक बाकी
                          </span>
                        )}
                        {g.revisions && g.revisions.length > 0 && (
                          <span className="px-2 py-0.5 rounded-full bg-purple-100 text-purple-800 border border-purple-200 text-[10px] font-bold">
                            संशोधित #{g.revisions.length}
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-slate-500 font-medium mt-0.5">
                        📅 {g.date} | ⏰ {g.time} | 📍 {g.gateName}
                      </div>
                    </div>
                  </div>

                  {/* Status Badge */}
                  <div>
                    <span className={`px-3 py-1 rounded-full text-xs font-black inline-block ${
                      isCancelled
                        ? 'bg-red-600 text-white'
                        : g.status === 'स्वीकृत'
                        ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                        : g.status === 'जांच बाकी'
                        ? 'bg-amber-100 text-amber-800 border border-amber-300'
                        : 'bg-slate-100 text-slate-800'
                    }`}>
                      {g.status}
                    </span>
                  </div>
                </div>

                {/* Body Details */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-3 text-xs">
                  <div>
                    <span className="text-slate-500 block">सप्लायर:</span>
                    <span className="font-bold text-slate-900 text-sm truncate block">
                      {g.supplierName}
                    </span>
                    <span className="text-slate-500">चालान नं: <strong>{g.challanNumber}</strong></span>
                  </div>

                  <div>
                    <span className="text-slate-500 block">वाहन एवं चालक:</span>
                    <span className="font-mono font-bold text-slate-900 text-sm block">
                      {g.vehicleNumber}
                    </span>
                    <span className="text-slate-500">{g.driverName}</span>
                  </div>

                  <div className="bg-slate-50 p-2.5 rounded-xl border border-slate-200">
                    <div className="flex justify-between">
                      <span className="text-slate-500">कुल ब्लॉक:</span>
                      <span className="font-black text-slate-900">{g.totalBlocks} ({g.totalPieces} टुकड़े)</span>
                    </div>
                    <div className="flex justify-between mt-0.5">
                      <span className="text-slate-500">अनुमानित आयतन:</span>
                      <span className="font-mono font-bold text-teal-800">{Number(g.totalVolumeEstimateCft).toFixed(2)} CFT</span>
                    </div>
                    {g.totalNetWeightTonnes > 0 && (
                      <div className="flex justify-between mt-0.5 text-slate-600">
                        <span>धर्मकांटा वजन:</span>
                        <span className="font-mono font-bold">{g.totalNetWeightTonnes} टन</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Bottom View & Reprint Button */}
                <div className="mt-3 pt-2.5 border-t border-slate-100 flex items-center justify-between">
                  <div className="text-[11px] text-slate-400">
                    दर्जकर्ता: {g.receiverName}
                  </div>
                  <button
                    type="button"
                    className="flex items-center gap-1.5 text-xs font-extrabold text-teal-700 hover:text-teal-900"
                  >
                    <Eye className="w-3.5 h-3.5" />
                    <span>रसीद देखें व प्रिंट करें ➜</span>
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
