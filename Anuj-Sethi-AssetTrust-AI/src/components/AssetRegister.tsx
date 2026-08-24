import React, { useState, useMemo } from 'react';
import { 
  Search, 
  Download, 
  CheckCircle2, 
  AlertTriangle, 
  MapPin, 
  ChevronRight, 
  Layers, 
  Sparkles 
} from 'lucide-react';
import { Asset, RiskLevel } from '../types';
import { formatINR } from '../services/reliabilityScore';

interface AssetRegisterProps {
  assets: Asset[];
  currencyMode: 'Lakhs' | 'Crores' | 'Full';
  onSelectAsset: (asset: Asset) => void;
  openDemoShowcase?: () => void;
}

export const AssetRegister: React.FC<AssetRegisterProps> = ({
  assets,
  currencyMode,
  onSelectAsset,
  openDemoShowcase
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('All');
  const [selectedPlant, setSelectedPlant] = useState<string>('All');
  const [selectedVerification, setSelectedVerification] = useState<string>('All');
  const [selectedRisk, setSelectedRisk] = useState<string>('All');
  const [sortBy, setSortBy] = useState<'cost' | 'nbv' | 'id' | 'risk'>('cost');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  // Categories list
  const categories = ['All', ...Array.from(new Set(assets.map((a) => a.category)))];
  const plants = ['All', ...Array.from(new Set(assets.map((a) => a.plant)))];
  const verificationStatuses = ['All', 'Verified', 'Missing', 'Wrong Location', 'Suspected Ghost', 'Requires Inspection'];
  const riskLevels = ['All', 'Critical', 'High', 'Medium', 'Low', 'Clean'];

  // Filtered and Sorted Assets
  const filteredAssets = useMemo(() => {
    return assets.filter((asset) => {
      const matchSearch =
        asset.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        asset.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
        asset.serialNumber.toLowerCase().includes(searchTerm.toLowerCase()) ||
        asset.custodian.toLowerCase().includes(searchTerm.toLowerCase()) ||
        asset.subLocation.toLowerCase().includes(searchTerm.toLowerCase());

      const matchCategory = selectedCategory === 'All' || asset.category === selectedCategory;
      const matchPlant = selectedPlant === 'All' || asset.plant === selectedPlant;
      const matchVerification = selectedVerification === 'All' || asset.verificationStatus === selectedVerification;
      const matchRisk = selectedRisk === 'All' || asset.riskLevel === selectedRisk;

      return matchSearch && matchCategory && matchPlant && matchVerification && matchRisk;
    }).sort((a, b) => {
      let valA = 0;
      let valB = 0;
      if (sortBy === 'cost') {
        valA = a.costINR;
        valB = b.costINR;
      } else if (sortBy === 'nbv') {
        valA = a.nbvINR;
        valB = b.nbvINR;
      } else if (sortBy === 'risk') {
        const riskRank: Record<RiskLevel, number> = { Critical: 4, High: 3, Medium: 2, Low: 1, Clean: 0 };
        valA = riskRank[a.riskLevel];
        valB = riskRank[b.riskLevel];
      } else {
        return sortOrder === 'asc' ? a.id.localeCompare(b.id) : b.id.localeCompare(a.id);
      }
      return sortOrder === 'asc' ? valA - valB : valB - valA;
    });
  }, [assets, searchTerm, selectedCategory, selectedPlant, selectedVerification, selectedRisk, sortBy, sortOrder]);

  const exportCSV = () => {
    const headers = ['Asset ID', 'Name', 'Category', 'Plant', 'SubLocation', 'Cost (INR)', 'Accumulated Dep (INR)', 'NBV (INR)', 'Useful Life', 'Verification Status', 'Risk Level', 'Serial No', 'Custodian'];
    const rows = filteredAssets.map((a) => [
      a.id,
      `"${a.name}"`,
      `"${a.category}"`,
      `"${a.plant}"`,
      `"${a.subLocation}"`,
      a.costINR,
      a.accumulatedDepINR,
      a.nbvINR,
      a.usefulLifeYears,
      a.verificationStatus,
      a.riskLevel,
      a.serialNumber,
      `"${a.custodian}"`
    ]);

    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `AssetTrust_Fixed_Asset_Register_${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-5 pb-12">
      {/* Page Header */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2 text-xs font-bold uppercase tracking-wider text-blue-600">
            <Layers className="w-4 h-4 text-blue-600" />
            <span>Master Fixed Asset Subledger</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight mt-1">
            Enterprise Asset Register
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Complete inventory of capitalised Property, Plant & Equipment with Ind AS 16 component structures and physical tracking status.
          </p>
        </div>

        <div className="flex items-center space-x-3 shrink-0">
          {openDemoShowcase && (
            <button
              onClick={openDemoShowcase}
              className="px-3.5 py-2 rounded-lg bg-blue-50 border border-blue-200 text-blue-700 text-xs font-semibold flex items-center space-x-1.5 hover:bg-blue-100 transition-all shadow-2xs"
            >
              <Sparkles className="w-3.5 h-3.5 text-blue-600" />
              <span>Spotlight: ₹48.5L CNC Machine</span>
            </button>
          )}
          <button
            onClick={exportCSV}
            className="px-3.5 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold flex items-center space-x-2 transition-all shadow-2xs"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export CSV Register</span>
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm space-y-3">
        <div className="flex flex-col lg:flex-row lg:items-center gap-3">
          {/* Search Input */}
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 transform -translate-y-1/2" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search by Asset ID, Machine Name, Serial Number, Custodian, Bay..."
              className="w-full pl-9 pr-4 py-2 bg-white border border-slate-300 rounded-lg text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 shadow-2xs transition-colors"
            />
          </div>

          {/* Quick Filters */}
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="bg-white border border-slate-300 rounded-lg px-2.5 py-1.5 text-xs text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 shadow-2xs"
            >
              {categories.map((c) => (
                <option key={c} value={c}>Category: {c}</option>
              ))}
            </select>

            <select
              value={selectedPlant}
              onChange={(e) => setSelectedPlant(e.target.value)}
              className="bg-white border border-slate-300 rounded-lg px-2.5 py-1.5 text-xs text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 shadow-2xs"
            >
              {plants.map((p) => (
                <option key={p} value={p}>Plant: {p}</option>
              ))}
            </select>

            <select
              value={selectedVerification}
              onChange={(e) => setSelectedVerification(e.target.value)}
              className="bg-white border border-slate-300 rounded-lg px-2.5 py-1.5 text-xs text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 shadow-2xs"
            >
              {verificationStatuses.map((v) => (
                <option key={v} value={v}>Verification: {v}</option>
              ))}
            </select>

            <select
              value={selectedRisk}
              onChange={(e) => setSelectedRisk(e.target.value)}
              className="bg-white border border-slate-300 rounded-lg px-2.5 py-1.5 text-xs text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 shadow-2xs"
            >
              {riskLevels.map((r) => (
                <option key={r} value={r}>Risk: {r}</option>
              ))}
            </select>

            <select
              value={`${sortBy}-${sortOrder}`}
              onChange={(e) => {
                const [sb, so] = e.target.value.split('-') as ['cost' | 'nbv' | 'id' | 'risk', 'asc' | 'desc'];
                setSortBy(sb);
                setSortOrder(so);
              }}
              className="bg-white border border-slate-300 rounded-lg px-2.5 py-1.5 text-xs text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 shadow-2xs"
            >
              <option value="cost-desc">Sort: Gross Cost (High → Low)</option>
              <option value="cost-asc">Sort: Gross Cost (Low → High)</option>
              <option value="nbv-desc">Sort: Net Book Value (High → Low)</option>
              <option value="risk-desc">Sort: Risk Severity (High → Low)</option>
              <option value="id-asc">Sort: Asset ID (A → Z)</option>
            </select>
          </div>
        </div>

        {/* Filter Badges Summary */}
        <div className="flex items-center justify-between text-xs text-slate-500 pt-1 border-t border-slate-100">
          <span>Showing <strong className="text-slate-900 font-semibold">{filteredAssets.length}</strong> of {assets.length} fixed assets</span>
          {(selectedCategory !== 'All' || selectedPlant !== 'All' || selectedVerification !== 'All' || selectedRisk !== 'All' || searchTerm) && (
            <button
              onClick={() => {
                setSearchTerm('');
                setSelectedCategory('All');
                setSelectedPlant('All');
                setSelectedVerification('All');
                setSelectedRisk('All');
              }}
              className="text-blue-600 hover:text-blue-800 font-medium underline"
            >
              Reset all filters
            </button>
          )}
        </div>
      </div>

      {/* Asset Table */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50 text-slate-500 text-[10px] uppercase font-bold tracking-wider border-b border-slate-200">
                <th className="py-3 px-4">Asset ID & Tag</th>
                <th className="py-3 px-4">Description / Category</th>
                <th className="py-3 px-4">Plant & Sub-Location</th>
                <th className="py-3 px-4 text-right">Cost (Gross)</th>
                <th className="py-3 px-4 text-right">Net Book Value</th>
                <th className="py-3 px-4 text-center">Life (Yrs)</th>
                <th className="py-3 px-4 text-center">Physical Verification</th>
                <th className="py-3 px-4 text-center">Risk Level</th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-xs text-slate-700">
              {filteredAssets.map((asset) => {
                const hasComponents = asset.components && asset.components.length > 0;
                return (
                  <tr
                    key={asset.id}
                    onClick={() => onSelectAsset(asset)}
                    className="hover:bg-slate-50/80 transition-colors cursor-pointer group"
                  >
                    {/* Asset ID & Tag */}
                    <td className="py-3 px-4">
                      <div className="font-mono font-bold text-slate-900 group-hover:text-blue-600 transition-colors flex items-center space-x-1.5">
                        <span>{asset.id}</span>
                        {asset.id === 'AST-PUN-CNC-0042' && (
                          <span className="text-[9px] px-1.5 py-0.2 rounded bg-blue-50 text-blue-700 border border-blue-200 font-bold">
                            DEMO
                          </span>
                        )}
                      </div>
                      <div className="text-[11px] text-slate-400 font-mono mt-0.5">
                        {asset.serialNumber}
                      </div>
                    </td>

                    {/* Description & Category */}
                    <td className="py-3 px-4 max-w-xs">
                      <div className="font-semibold text-slate-900 line-clamp-1" title={asset.name}>
                        {asset.name}
                      </div>
                      <div className="flex items-center space-x-2 mt-0.5">
                        <span className="text-[11px] text-slate-500 font-medium">
                          {asset.category}
                        </span>
                        {hasComponents && (
                          <span className="text-[10px] px-1.5 py-0.2 rounded bg-blue-50 text-blue-700 border border-blue-200 font-semibold">
                            {asset.components.length} Components
                          </span>
                        )}
                      </div>
                    </td>

                    {/* Plant & Sub-Location */}
                    <td className="py-3 px-4">
                      <div className="text-slate-800 font-medium truncate" title={asset.plant}>
                        {asset.plant.split(' - ')[0]}
                      </div>
                      <div className="text-[11px] text-slate-400 truncate mt-0.5" title={asset.subLocation}>
                        {asset.subLocation}
                      </div>
                    </td>

                    {/* Gross Cost */}
                    <td className="py-3 px-4 text-right font-mono font-bold text-slate-900">
                      {formatINR(asset.costINR, currencyMode)}
                    </td>

                    {/* Net Book Value */}
                    <td className="py-3 px-4 text-right font-mono text-emerald-700 font-bold">
                      {formatINR(asset.nbvINR, currencyMode)}
                    </td>

                    {/* Useful Life */}
                    <td className="py-3 px-4 text-center">
                      <span className="text-slate-800 font-mono font-medium">{asset.usefulLifeYears}y</span>
                      {asset.usefulLifeYears !== asset.schIILifeYears && (
                        <div className="text-[10px] text-amber-700 font-mono font-semibold" title="Differs from Sch II">
                          (Sch II: {asset.schIILifeYears}y)
                        </div>
                      )}
                    </td>

                    {/* Verification Status */}
                    <td className="py-3 px-4 text-center">
                      <span className={`inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold ${
                        asset.verificationStatus === 'Verified'
                          ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                          : asset.verificationStatus === 'Wrong Location'
                          ? 'bg-amber-50 text-amber-700 border border-amber-200'
                          : asset.verificationStatus === 'Suspected Ghost' || asset.verificationStatus === 'Missing'
                          ? 'bg-rose-50 text-rose-700 border border-rose-200'
                          : 'bg-slate-100 text-slate-700 border border-slate-200'
                      }`}>
                        {asset.verificationStatus === 'Verified' && <CheckCircle2 className="w-3 h-3 text-emerald-600" />}
                        {asset.verificationStatus === 'Wrong Location' && <MapPin className="w-3 h-3 text-amber-600" />}
                        {(asset.verificationStatus === 'Suspected Ghost' || asset.verificationStatus === 'Missing') && <AlertTriangle className="w-3 h-3 text-rose-600" />}
                        <span>{asset.verificationStatus}</span>
                      </span>
                    </td>

                    {/* Risk Level */}
                    <td className="py-3 px-4 text-center">
                      <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                        asset.riskLevel === 'Critical'
                          ? 'bg-rose-50 text-rose-700 border border-rose-200'
                          : asset.riskLevel === 'High'
                          ? 'bg-amber-50 text-amber-700 border border-amber-200'
                          : asset.riskLevel === 'Medium'
                          ? 'bg-yellow-50 text-yellow-700 border border-yellow-200'
                          : 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                      }`}>
                        {asset.riskLevel}
                      </span>
                    </td>

                    {/* Action */}
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectAsset(asset);
                        }}
                        className="px-2.5 py-1 rounded-lg bg-slate-900 text-white hover:bg-slate-800 transition-all inline-flex items-center space-x-1 text-[11px] font-medium shadow-xs"
                      >
                        <span>Audit View</span>
                        <ChevronRight className="w-3 h-3" />
                      </button>
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
