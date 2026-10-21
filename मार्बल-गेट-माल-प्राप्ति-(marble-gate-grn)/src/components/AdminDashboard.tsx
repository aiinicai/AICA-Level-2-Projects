import React, { useState, useMemo } from 'react';
import { GoodsReceiptNote, FactorySettings, MasterData, UserAccount } from '../types/grn';
import { 
  Building2, Users, Settings, Download, Plus, Trash2, CheckCircle2, 
  AlertTriangle, RefreshCw, BarChart3, Package, Truck, Scale, ShieldAlert, Edit2, X
} from 'lucide-react';

interface AdminDashboardProps {
  grns: GoodsReceiptNote[];
  settings: FactorySettings;
  masters: MasterData;
  currentUser: UserAccount;
  onUpdateSettings: (newSettings: FactorySettings) => Promise<void>;
  onUpdateMasters: (newMasters: MasterData) => Promise<void>;
  onCancelReceipt: (grnId: string, reason: string) => Promise<void>;
  onSelectGrn: (grn: GoodsReceiptNote) => void;
  onRefresh: () => void;
  isSyncing: boolean;
}

export const AdminDashboard: React.FC<AdminDashboardProps> = ({
  grns,
  settings,
  masters,
  currentUser,
  onUpdateSettings,
  onUpdateMasters,
  onCancelReceipt,
  onSelectGrn,
  onRefresh,
  isSyncing,
}) => {
  const [activeTab, setActiveTab] = useState<'stats' | 'receipts' | 'masters' | 'settings'>('stats');

  // Cancel Receipt Modal State
  const [cancellingGrn, setCancellingGrn] = useState<GoodsReceiptNote | null>(null);
  const [cancellationReason, setCancellationReason] = useState('');
  const [isCancelling, setIsCancelling] = useState(false);

  // New Supplier & Variety input states
  const [newSupplier, setNewSupplier] = useState('');
  const [newVariety, setNewVariety] = useState('');

  // Settings form state
  const [factoryForm, setFactoryForm] = useState<FactorySettings>({ ...settings });
  const [isSavingSettings, setIsSavingSettings] = useState(false);

  useEffect(() => {
    setFactoryForm({ ...settings });
  }, [settings]);

  // Today string YYYY-MM-DD
  const todayStr = new Date().toISOString().split('T')[0];

  // Dashboard Aggregates
  const stats = useMemo(() => {
    const todayGrns = grns.filter(g => g.date === todayStr && g.status !== 'रद्द');
    const validGrns = grns.filter(g => g.status !== 'रद्द');

    const totalBlocksAll = validGrns.reduce((sum, g) => sum + (g.totalBlocks || 0), 0);
    const totalVolumeCft = validGrns.reduce((sum, g) => sum + (Number(g.totalVolumeEstimateCft) || 0), 0);
    const totalWeightTonnes = validGrns.reduce((sum, g) => sum + (Number(g.totalNetWeightTonnes) || 0), 0);

    const pendingInspection = validGrns.filter(g => g.status === 'जांच बाकी' || g.blocks.some(b => b.inspectionStatus === 'जांच बाकी'));
    const pendingSync = grns.filter(g => g.syncStatus === 'सिंक बाकी' || g.isProvisional);

    // Variety distribution
    const varietyCount: Record<string, { blocks: number; volume: number }> = {};
    for (const g of validGrns) {
      for (const b of g.blocks) {
        const v = b.variety || 'अन्य';
        if (!varietyCount[v]) varietyCount[v] = { blocks: 0, volume: 0 };
        varietyCount[v].blocks += (b.pieces || 1);
        varietyCount[v].volume += Number(b.estimatedVolume || 0);
      }
    }

    return {
      todayCount: todayGrns.length,
      todayBlocks: todayGrns.reduce((sum, g) => sum + (g.totalBlocks || 0), 0),
      todayVolume: todayGrns.reduce((sum, g) => sum + (Number(g.totalVolumeEstimateCft) || 0), 0),
      totalGrns: validGrns.length,
      totalBlocksAll,
      totalVolumeCft: Number(totalVolumeCft.toFixed(2)),
      totalWeightTonnes: Number(totalWeightTonnes.toFixed(2)),
      pendingInspectionCount: pendingInspection.length,
      pendingSyncCount: pendingSync.length,
      varietyCount,
    };
  }, [grns, todayStr]);

  const handleDownloadCsv = () => {
    window.location.href = '/api/export-csv';
  };

  const handleAddSupplier = async () => {
    if (!newSupplier.trim()) return;
    const clean = newSupplier.trim();
    if (masters.suppliers.includes(clean)) return;
    const updated = { ...masters, suppliers: [...masters.suppliers, clean] };
    await onUpdateMasters(updated);
    setNewSupplier('');
  };

  const handleRemoveSupplier = async (sup: string) => {
    if (confirm(`क्या आप सप्लायर "${sup}" को सूची से हटाना चाहते हैं?`)) {
      const updated = { ...masters, suppliers: masters.suppliers.filter(s => s !== sup) };
      await onUpdateMasters(updated);
    }
  };

  const handleAddVariety = async () => {
    if (!newVariety.trim()) return;
    const clean = newVariety.trim();
    if (masters.varieties.includes(clean)) return;
    const updated = { ...masters, varieties: [...masters.varieties, clean] };
    await onUpdateMasters(updated);
    setNewVariety('');
  };

  const handleRemoveVariety = async (varName: string) => {
    if (confirm(`क्या आप मार्बल किस्म "${varName}" को सूची से हटाना चाहते हैं?`)) {
      const updated = { ...masters, varieties: masters.varieties.filter(v => v !== varName) };
      await onUpdateMasters(updated);
    }
  };

  const handleSaveFactorySettings = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setIsSavingSettings(true);
      await onUpdateSettings(factoryForm);
      alert('फैक्ट्री सेटिंग्स सफलतापूर्वक सुरक्षित हो गई हैं!');
    } catch (err: any) {
      alert('सेटिंग्स सेव करने में त्रुटि: ' + err.message);
    } finally {
      setIsSavingSettings(false);
    }
  };

  const executeCancel = async () => {
    if (!cancellingGrn) return;
    if (!cancellationReason.trim()) {
      alert('रद्द करने का कारण लिखना अनिवार्य है।');
      return;
    }
    try {
      setIsCancelling(true);
      await onCancelReceipt(cancellingGrn.id, cancellationReason.trim());
      setCancellingGrn(null);
      setCancellationReason('');
    } catch (err: any) {
      alert('रसीद रद्द करने में त्रुटि: ' + err.message);
    } finally {
      setIsCancelling(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto px-4 py-6 space-y-6">
      
      {/* Dashboard Header */}
      <div className="bg-slate-900 text-white rounded-3xl p-6 shadow-xl flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-teal-400 text-xs font-bold uppercase tracking-wider">
            <Building2 className="w-4 h-4" />
            <span>फैक्ट्री मालिक एवं एडमिन नियंत्रण कक्ष</span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-black mt-1">
            {settings.factoryName}
          </h2>
          <p className="text-xs sm:text-sm text-slate-400 mt-0.5">
            सभी गेटों के आवक रिकॉर्ड, धर्मकांटा वजन एवं सप्लायर प्रबंधन
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleDownloadCsv}
            className="flex items-center gap-2 px-4 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-extrabold text-xs sm:text-sm rounded-xl shadow-md transition active:scale-95 cursor-pointer"
            title="Excel/Sheets के लिए हिंदी CSV डाउनलोड करें"
          >
            <Download className="w-4 h-4" />
            <span>CSV एक्सपोर्ट (Excel)</span>
          </button>

          <button
            onClick={onRefresh}
            disabled={isSyncing}
            className="p-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl transition cursor-pointer"
            title="डेटा ताजा करें"
          >
            <RefreshCw className={`w-4 h-4 ${isSyncing ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1">
        {[
          { key: 'stats', label: '📊 व्यापार सांख्यिकी', icon: BarChart3 },
          { key: 'receipts', label: '📑 सभी रसीदें', icon: Package },
          { key: 'masters', label: '🏢 सप्लायर व किस्में', icon: Truck },
          { key: 'settings', label: '⚙️ फैक्ट्री सेटिंग्स', icon: Settings },
        ].map(({ key, label }) => {
          const isSelected = activeTab === key;
          return (
            <button
              key={key}
              onClick={() => setActiveTab(key as any)}
              className={`px-4 py-2.5 rounded-2xl font-bold text-xs sm:text-sm transition shrink-0 cursor-pointer ${
                isSelected
                  ? 'bg-teal-700 text-white shadow-md'
                  : 'bg-white text-slate-700 hover:bg-slate-100 border border-slate-200'
              }`}
            >
              {label}
            </button>
          );
        })}
      </div>

      {/* TAB 1: STATS & OVERVIEW */}
      {activeTab === 'stats' && (
        <div className="space-y-6">
          
          {/* Top 4 KPI Metrics */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4">
            
            <div className="bg-white p-4 sm:p-5 rounded-3xl border border-slate-200 shadow-xs">
              <span className="text-xs font-bold text-slate-500 block uppercase">आज की आवक (Today)</span>
              <div className="text-2xl sm:text-3xl font-black text-slate-900 mt-1 font-mono">
                {stats.todayCount} <span className="text-xs text-slate-500 font-normal">रसीदें</span>
              </div>
              <span className="text-xs text-teal-700 font-bold block mt-1">
                {stats.todayBlocks} ब्लॉक ({stats.todayVolume.toFixed(1)} CFT)
              </span>
            </div>

            <div className="bg-white p-4 sm:p-5 rounded-3xl border border-slate-200 shadow-xs">
              <span className="text-xs font-bold text-slate-500 block uppercase">कुल प्राप्त ब्लॉक</span>
              <div className="text-2xl sm:text-3xl font-black text-teal-900 mt-1 font-mono">
                {stats.totalBlocksAll} <span className="text-xs text-slate-500 font-normal">ब्लॉक</span>
              </div>
              <span className="text-xs text-slate-500 font-medium block mt-1">
                कुल {stats.totalGrns} GRN में
              </span>
            </div>

            <div className="bg-white p-4 sm:p-5 rounded-3xl border border-slate-200 shadow-xs">
              <span className="text-xs font-bold text-slate-500 block uppercase">कुल अनुमानित आयतन</span>
              <div className="text-2xl sm:text-3xl font-black text-amber-700 mt-1 font-mono">
                {stats.totalVolumeCft.toLocaleString('hi-IN')} <span className="text-xs text-slate-500 font-normal">CFT</span>
              </div>
              <span className="text-[11px] text-slate-500 block mt-1">
                (घनाकार नाप आधार पर)
              </span>
            </div>

            <div className="bg-white p-4 sm:p-5 rounded-3xl border border-slate-200 shadow-xs">
              <span className="text-xs font-bold text-slate-500 block uppercase">धर्मकांटा शुद्ध वजन</span>
              <div className="text-2xl sm:text-3xl font-black text-slate-900 mt-1 font-mono">
                {stats.totalWeightTonnes} <span className="text-xs text-slate-500 font-normal">टन</span>
              </div>
              <span className="text-xs text-emerald-700 font-bold block mt-1">
                सत्यापित वजन
              </span>
            </div>

          </div>

          {/* Attention Alerts if any */}
          {(stats.pendingInspectionCount > 0 || stats.pendingSyncCount > 0) && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {stats.pendingInspectionCount > 0 && (
                <div className="bg-amber-50 border-2 border-amber-400 rounded-3xl p-4 text-amber-950 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <AlertTriangle className="w-6 h-6 text-amber-600 shrink-0" />
                    <div>
                      <div className="font-extrabold text-sm sm:text-base">
                        {stats.pendingInspectionCount} रसीदें निरीक्षण बाकी हैं!
                      </div>
                      <div className="text-xs text-amber-800">
                        गेट पर दरार या संदिग्ध गुणवत्ता वाले ब्लॉक्स की जांच करें।
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {stats.pendingSyncCount > 0 && (
                <div className="bg-blue-50 border-2 border-blue-400 rounded-3xl p-4 text-blue-950 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <RefreshCw className="w-6 h-6 text-blue-600 shrink-0" />
                    <div>
                      <div className="font-extrabold text-sm sm:text-base">
                        {stats.pendingSyncCount} रसीदें ऑफलाइन कतार में हैं
                      </div>
                      <div className="text-xs text-blue-800">
                        गेट फोन के इंटरनेट से जुड़ते ही स्वतः आ जाएंगी।
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Material Variety Breakdown */}
          <div className="bg-white rounded-3xl p-6 border border-slate-200 shadow-sm space-y-4">
            <h3 className="font-extrabold text-base text-slate-900 flex items-center gap-2">
              <Package className="w-5 h-5 text-teal-700" />
              <span>मार्बल एवं पत्थर किस्म अनुसार आवक (Variety Breakdown):</span>
            </h3>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs sm:text-sm">
                <thead>
                  <tr className="bg-slate-100 text-slate-700 font-bold border-b border-slate-200">
                    <th className="p-3">किस्म का नाम (Variety)</th>
                    <th className="p-3 text-center">ब्लॉक संख्या</th>
                    <th className="p-3 text-right">कुल अनुमानित आयतन (CFT)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {Object.entries(stats.varietyCount).map(([variety, data]) => (
                    <tr key={variety} className="hover:bg-slate-50">
                      <td className="p-3 font-bold text-slate-900">{variety}</td>
                      <td className="p-3 text-center font-mono font-bold text-teal-900">{data.blocks}</td>
                      <td className="p-3 text-right font-mono font-black text-amber-900">
                        {data.volume.toFixed(2)} CFT
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

        </div>
      )}

      {/* TAB 2: ALL RECEIPTS WITH REVISE & CANCEL ACTIONS */}
      {activeTab === 'receipts' && (
        <div className="bg-white rounded-3xl p-5 border border-slate-200 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div>
              <h3 className="font-extrabold text-base text-slate-900">
                समस्त माल प्राप्ति रसीदें (Audit & Control)
              </h3>
              <p className="text-xs text-slate-500">
                रसीदों को देखें, प्रिंट करें, सुधारें या कारण सहित रद्द करें।
              </p>
            </div>
            <button
              onClick={handleDownloadCsv}
              className="text-xs font-bold text-teal-700 hover:underline flex items-center gap-1"
            >
              <Download className="w-3.5 h-3.5" />
              <span>CSV डाउनलोड</span>
            </button>
          </div>

          <div className="space-y-3">
            {grns.map((g) => {
              const isCancelled = g.status === 'रद्द';
              return (
                <div
                  key={g.id}
                  className={`p-4 rounded-2xl border-2 transition flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 ${
                    isCancelled ? 'bg-red-50/40 border-red-200' : 'bg-slate-50 border-slate-200 hover:border-teal-400'
                  }`}
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-black text-base text-slate-900">{g.grnNumber}</span>
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                        isCancelled
                          ? 'bg-red-600 text-white'
                          : g.status === 'स्वीकृत'
                          ? 'bg-emerald-100 text-emerald-800'
                          : 'bg-amber-100 text-amber-800'
                      }`}>
                        {g.status}
                      </span>
                      {g.revisions && g.revisions.length > 0 && (
                        <span className="text-[10px] font-bold text-purple-700 bg-purple-100 px-2 py-0.5 rounded-full">
                          संशोधन #{g.revisions.length}
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-slate-600">
                      <strong>{g.supplierName}</strong> | गाड़ी: <span className="font-mono font-bold">{g.vehicleNumber}</span> | चालान: {g.challanNumber}
                    </div>
                    <div className="text-[11px] text-slate-500">
                      दिनांक: {g.date} {g.time} | ब्लॉक: {g.totalBlocks} | आयतन: {Number(g.totalVolumeEstimateCft).toFixed(2)} CFT | वजन: {g.totalNetWeightTonnes || 0} टन
                    </div>
                  </div>

                  <div className="flex items-center gap-2 w-full sm:w-auto pt-2 sm:pt-0">
                    <button
                      onClick={() => onSelectGrn(g)}
                      className="flex-1 sm:flex-initial px-3.5 py-2 bg-teal-700 hover:bg-teal-800 text-white font-bold text-xs rounded-xl transition cursor-pointer"
                    >
                      रसीद देखें
                    </button>

                    {!isCancelled && (
                      <button
                        onClick={() => {
                          setCancellingGrn(g);
                          setCancellationReason('');
                        }}
                        className="px-3 py-2 bg-red-50 hover:bg-red-100 text-red-700 border border-red-300 font-bold text-xs rounded-xl transition cursor-pointer"
                        title="रसीद रद्द करें (कारण अनिवार्य)"
                      >
                        रद्द करें
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* TAB 3: MASTER LISTS (SUPPLIERS & VARIETIES) */}
      {activeTab === 'masters' && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
          
          {/* Suppliers Management */}
          <div className="bg-white rounded-3xl p-5 border border-slate-200 shadow-sm space-y-4">
            <h3 className="font-extrabold text-base text-slate-900 border-b border-slate-100 pb-2">
              सप्लायर सूची (Repeat Suppliers)
            </h3>

            <div className="flex gap-2">
              <input
                type="text"
                value={newSupplier || ''}
                onChange={(e) => setNewSupplier(e.target.value)}
                placeholder="नया सप्लायर नाम दर्ज करें..."
                className="flex-1 p-2.5 rounded-xl border border-slate-300 text-xs text-slate-900 outline-none"
              />
              <button
                type="button"
                onClick={handleAddSupplier}
                className="px-4 py-2.5 bg-teal-700 hover:bg-teal-800 text-white font-bold text-xs rounded-xl transition"
              >
                + जोड़ें
              </button>
            </div>

            <div className="space-y-1.5 max-h-80 overflow-y-auto">
              {masters.suppliers.map((s) => (
                <div key={s} className="flex items-center justify-between p-2.5 rounded-xl bg-slate-50 border border-slate-200 text-xs">
                  <span className="font-bold text-slate-800">{s}</span>
                  <button
                    type="button"
                    onClick={() => handleRemoveSupplier(s)}
                    className="text-red-500 hover:text-red-700 p-1"
                    title="हटाएं"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* Marble Varieties Management */}
          <div className="bg-white rounded-3xl p-5 border border-slate-200 shadow-sm space-y-4">
            <h3 className="font-extrabold text-base text-slate-900 border-b border-slate-100 pb-2">
              मार्बल एवं पत्थर की किस्में (Varieties)
            </h3>

            <div className="flex gap-2">
              <input
                type="text"
                value={newVariety || ''}
                onChange={(e) => setNewVariety(e.target.value)}
                placeholder="उदा. वियतनाम वाइट, राजनगर..."
                className="flex-1 p-2.5 rounded-xl border border-slate-300 text-xs text-slate-900 outline-none"
              />
              <button
                type="button"
                onClick={handleAddVariety}
                className="px-4 py-2.5 bg-teal-700 hover:bg-teal-800 text-white font-bold text-xs rounded-xl transition"
              >
                + जोड़ें
              </button>
            </div>

            <div className="space-y-1.5 max-h-80 overflow-y-auto">
              {masters.varieties.map((v) => (
                <div key={v} className="flex items-center justify-between p-2.5 rounded-xl bg-slate-50 border border-slate-200 text-xs">
                  <span className="font-bold text-slate-800">{v}</span>
                  <button
                    type="button"
                    onClick={() => handleRemoveVariety(v)}
                    className="text-red-500 hover:text-red-700 p-1"
                    title="हटाएं"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>
          </div>

        </div>
      )}

      {/* TAB 4: FACTORY SETTINGS */}
      {activeTab === 'settings' && (
        <form onSubmit={handleSaveFactorySettings} className="bg-white rounded-3xl p-6 border border-slate-200 shadow-sm space-y-4">
          <h3 className="font-extrabold text-lg text-slate-900 border-b border-slate-100 pb-2">
            फैक्ट्री प्रोफाइल एवं रसीद विन्यास (Voucher Settings)
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">फैक्ट्री का नाम</label>
              <input
                type="text"
                value={factoryForm.factoryName || ''}
                onChange={(e) => setFactoryForm({ ...factoryForm, factoryName: e.target.value })}
                className="w-full p-2.5 rounded-xl border border-slate-300 text-sm font-bold text-slate-900 outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">टैगलाइन / विवरण</label>
              <input
                type="text"
                value={factoryForm.factoryTagline || ''}
                onChange={(e) => setFactoryForm({ ...factoryForm, factoryTagline: e.target.value })}
                className="w-full p-2.5 rounded-xl border border-slate-300 text-sm text-slate-900 outline-none"
              />
            </div>

            <div className="sm:col-span-2">
              <label className="block text-xs font-bold text-slate-700 mb-1">फैक्ट्री का पूरा पता</label>
              <input
                type="text"
                value={factoryForm.factoryAddress || ''}
                onChange={(e) => setFactoryForm({ ...factoryForm, factoryAddress: e.target.value })}
                className="w-full p-2.5 rounded-xl border border-slate-300 text-sm text-slate-900 outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">फोन नंबर</label>
              <input
                type="text"
                value={factoryForm.factoryPhone || ''}
                onChange={(e) => setFactoryForm({ ...factoryForm, factoryPhone: e.target.value })}
                className="w-full p-2.5 rounded-xl border border-slate-300 text-sm text-slate-900 outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">GSTIN नंबर</label>
              <input
                type="text"
                value={factoryForm.factoryGstin || ''}
                onChange={(e) => setFactoryForm({ ...factoryForm, factoryGstin: e.target.value })}
                className="w-full p-2.5 rounded-xl border border-slate-300 text-sm font-mono text-slate-900 outline-none"
              />
            </div>

            <div className="sm:col-span-2">
              <label className="block text-xs font-bold text-slate-700 mb-1">रसीद का शीर्षक</label>
              <input
                type="text"
                value={factoryForm.receiptTitle || ''}
                onChange={(e) => setFactoryForm({ ...factoryForm, receiptTitle: e.target.value })}
                className="w-full p-2.5 rounded-xl border border-slate-300 text-sm text-slate-900 outline-none"
              />
            </div>

            <div className="sm:col-span-2">
              <label className="block text-xs font-bold text-slate-700 mb-1">घोषणा वाक्य (Declaration Text)</label>
              <textarea
                rows={2}
                value={factoryForm.declarationText || ''}
                onChange={(e) => setFactoryForm({ ...factoryForm, declarationText: e.target.value })}
                className="w-full p-2.5 rounded-xl border border-slate-300 text-xs text-slate-900 outline-none"
              />
            </div>
          </div>

          <div className="pt-3 border-t border-slate-100 flex justify-end">
            <button
              type="submit"
              disabled={isSavingSettings}
              className="px-6 py-3 bg-teal-700 hover:bg-teal-800 text-white font-extrabold text-sm rounded-xl shadow-md transition cursor-pointer"
            >
              {isSavingSettings ? 'सेव हो रहा है...' : 'सेटिंग्स सुरक्षित करें'}
            </button>
          </div>
        </form>
      )}

      {/* Mandatory Cancellation Modal */}
      {cancellingGrn && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl text-slate-900 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-2">
              <div className="flex items-center gap-2 text-red-600 font-extrabold text-base">
                <AlertTriangle className="w-5 h-5" />
                <span>रसीद रद्द करें (Cancel GRN)</span>
              </div>
              <button
                onClick={() => setCancellingGrn(null)}
                className="text-slate-400 hover:text-slate-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-xs text-slate-600">
              रसीद सं. <strong>{cancellingGrn.grnNumber}</strong> ({cancellingGrn.supplierName} - {cancellingGrn.vehicleNumber}) को रद्द किया जा रहा है। रद्द होने के बाद भी यह रिकॉर्ड ऑडिट ट्रेल में बना रहेगा और कभी भी स्थायी रूप से मिटाया नहीं जाएगा।
            </p>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                रद्द करने का कारण (अनिवार्य) <span className="text-red-500">*</span>:
              </label>
              <textarea
                rows={3}
                value={cancellationReason || ''}
                onChange={(e) => setCancellationReason(e.target.value)}
                placeholder="उदा. गलत गाड़ी नंबर दर्ज हो गया था, माल वापस लौटा दिया गया..."
                className="w-full p-2.5 rounded-xl border border-red-300 focus:border-red-600 text-xs text-slate-900 outline-none"
              />
            </div>

            <div className="flex gap-2 pt-2">
              <button
                type="button"
                onClick={() => setCancellingGrn(null)}
                className="flex-1 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-xs rounded-xl"
              >
                वापस जाएं
              </button>
              <button
                type="button"
                onClick={executeCancel}
                disabled={isCancelling || !cancellationReason.trim()}
                className="flex-1 py-2.5 bg-red-600 hover:bg-red-700 text-white font-bold text-xs rounded-xl shadow-md transition disabled:opacity-50"
              >
                {isCancelling ? 'रद्द हो रही है...' : 'पुष्टि करें एवं रद्द करें'}
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};
