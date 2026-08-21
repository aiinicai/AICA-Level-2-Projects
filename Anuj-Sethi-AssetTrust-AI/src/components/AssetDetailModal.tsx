import React, { useState } from 'react';
import { 
  X, 
  ShieldCheck, 
  QrCode, 
  MapPin, 
  FileText, 
  Layers, 
  AlertTriangle, 
  CheckCircle2, 
  ArrowRight,
  Printer,
  FileCheck
} from 'lucide-react';
import { Asset } from '../types';
import { formatINR } from '../services/reliabilityScore';

interface AssetDetailModalProps {
  asset: Asset | null;
  onClose: () => void;
  currencyMode: 'Lakhs' | 'Crores' | 'Full';
  onNavigateToRisk?: (assetId: string) => void;
}

export const AssetDetailModal: React.FC<AssetDetailModalProps> = ({
  asset,
  onClose,
  currencyMode,
  onNavigateToRisk
}) => {
  const [activeTab, setActiveTab] = useState<'overview' | 'components' | 'procurement' | 'verification' | 'governance'>('overview');

  if (!asset) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 sm:p-6">
      <div className="bg-white border border-slate-200 rounded-2xl w-full max-w-4xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden text-slate-800 animate-in fade-in zoom-in-95 duration-200">
        
        {/* Header */}
        <div className="p-5 border-b border-slate-200 bg-slate-50 flex items-start justify-between gap-4">
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-xs font-bold text-blue-700 bg-blue-50 border border-blue-200 px-2.5 py-0.5 rounded">
                {asset.id}
              </span>
              <span className="text-xs text-slate-500 font-mono">
                SN: {asset.serialNumber}
              </span>
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider ${
                asset.riskLevel === 'Critical'
                  ? 'bg-rose-50 text-rose-700 border border-rose-200'
                  : asset.riskLevel === 'High'
                  ? 'bg-amber-50 text-amber-700 border border-amber-200'
                  : 'bg-emerald-50 text-emerald-700 border border-emerald-200'
              }`}>
                {asset.riskLevel} Risk
              </span>
              <span className={`text-[11px] font-semibold px-2.5 py-0.5 rounded-full flex items-center space-x-1 ${
                asset.verificationStatus === 'Verified'
                  ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                  : 'bg-amber-50 text-amber-700 border border-amber-200'
              }`}>
                <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                <span>{asset.verificationStatus}</span>
              </span>
            </div>
            <h2 className="text-xl font-bold text-slate-900 tracking-tight mt-1">
              {asset.name}
            </h2>
            <p className="text-xs text-slate-500">
              {asset.plant} • {asset.subLocation} • Custodian: <strong className="text-slate-700">{asset.custodian}</strong>
            </p>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => window.print()}
              className="p-2 rounded-lg bg-white border border-slate-200 hover:bg-slate-100 text-slate-600 transition-colors shadow-2xs"
              title="Print Asset Dossier"
            >
              <Printer className="w-4 h-4" />
            </button>
            <button
              onClick={onClose}
              className="p-2 rounded-lg bg-white border border-slate-200 hover:bg-slate-100 text-slate-500 hover:text-slate-800 transition-colors shadow-2xs"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Financial Highlights Bar */}
        <div className="grid grid-cols-2 sm:grid-cols-4 bg-slate-50/70 border-b border-slate-200 px-5 py-3 gap-4 text-xs">
          <div>
            <span className="text-slate-500 block text-[11px] uppercase font-semibold">Original Cost (Gross Block)</span>
            <span className="text-base font-bold text-slate-900 font-mono">{formatINR(asset.costINR, currencyMode)}</span>
          </div>
          <div>
            <span className="text-slate-500 block text-[11px] uppercase font-semibold">Accumulated Depreciation</span>
            <span className="text-base font-bold text-slate-700 font-mono">{formatINR(asset.accumulatedDepINR, currencyMode)}</span>
          </div>
          <div>
            <span className="text-slate-500 block text-[11px] uppercase font-semibold">Net Book Value (NBV)</span>
            <span className="text-base font-bold text-emerald-700 font-mono">{formatINR(asset.nbvINR, currencyMode)}</span>
          </div>
          <div>
            <span className="text-slate-500 block text-[11px] uppercase font-semibold">Useful Life (Ind AS 16)</span>
            <span className="text-base font-bold text-slate-900 font-mono">{asset.usefulLifeYears} Years</span>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-slate-200 px-5 bg-white overflow-x-auto scrollbar-none text-xs">
          {[
            { id: 'overview', label: 'Overview & Technical Specs' },
            { id: 'components', label: `Ind AS 16 Components (${asset.components?.length || 0})` },
            { id: 'procurement', label: 'Procurement & Capex Chain' },
            { id: 'verification', label: 'Physical Verification & GPS' },
            { id: 'governance', label: `Governance & Exceptions (${asset.anomalies?.length || 0})` }
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`py-3 px-3 font-semibold border-b-2 whitespace-nowrap transition-all ${
                activeTab === tab.id
                  ? 'border-blue-600 text-blue-600 bg-blue-50/40'
                  : 'border-transparent text-slate-500 hover:text-slate-800'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto space-y-5 text-xs text-slate-700 flex-1">
          {/* TAB 1: OVERVIEW */}
          {activeTab === 'overview' && (
            <div className="space-y-5">
              {/* Description */}
              <div className="bg-slate-50 border border-slate-200 rounded-xl p-4">
                <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider mb-1.5 flex items-center space-x-1.5">
                  <FileText className="w-3.5 h-3.5 text-blue-600" />
                  <span>Asset Description & Purpose</span>
                </h4>
                <p className="text-slate-700 leading-relaxed">{asset.description}</p>
              </div>

              {/* Technical Specifications & Attributes */}
              {asset.specifications && (
                <div className="bg-slate-50 border border-slate-200 rounded-xl p-4">
                  <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider mb-2 flex items-center space-x-1.5">
                    <Layers className="w-3.5 h-3.5 text-blue-600" />
                    <span>Technical Specifications</span>
                  </h4>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                    {Object.entries(asset.specifications).map(([key, val]) => (
                      <div key={key} className="bg-white border border-slate-200 rounded-lg p-2.5 flex justify-between shadow-2xs">
                        <span className="text-slate-500">{key}:</span>
                        <span className="font-semibold text-slate-800">{val}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Custody & Location Details */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-2">
                  <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider mb-2 flex items-center space-x-1.5">
                    <MapPin className="w-3.5 h-3.5 text-amber-600" />
                    <span>Physical Location & Custody</span>
                  </h4>
                  <div className="space-y-1.5">
                    <div className="flex justify-between py-1 border-b border-slate-200">
                      <span className="text-slate-500">Operating Plant:</span>
                      <span className="font-semibold text-slate-800">{asset.plant}</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-slate-200">
                      <span className="text-slate-500">Sub-Location / Bay:</span>
                      <span className="font-semibold text-slate-800">{asset.subLocation}</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-slate-200">
                      <span className="text-slate-500">Primary Custodian:</span>
                      <span className="font-semibold text-slate-800">{asset.custodian}</span>
                    </div>
                    <div className="flex justify-between py-1">
                      <span className="text-slate-500">Department / CC:</span>
                      <span className="font-semibold text-slate-800">{asset.department}</span>
                    </div>
                  </div>
                </div>

                {/* QR Code & Digital Tagging */}
                <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 flex flex-col justify-between">
                  <div>
                    <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider mb-2 flex items-center space-x-1.5">
                      <QrCode className="w-3.5 h-3.5 text-blue-600" />
                      <span>Digital Identification Tag</span>
                    </h4>
                    <p className="text-slate-500 mb-3">Tamper-evident 2D Matrix tag linked to SAP ERP & AssetTrust AI.</p>
                  </div>
                  <div className="flex items-center space-x-4 bg-white p-3 rounded-lg border border-slate-200 shadow-2xs">
                    <div className="w-14 h-14 bg-slate-900 text-white rounded-lg flex items-center justify-center p-1 shrink-0">
                      <QrCode className="w-10 h-10 text-white" />
                    </div>
                    <div>
                      <span className="font-mono text-xs font-bold text-blue-700 block">{asset.qrCode}</span>
                      <span className="text-[11px] text-slate-500 block">Serial: {asset.serialNumber}</span>
                      <span className="text-[10px] text-emerald-700 font-semibold font-mono">Status: Synced & Active</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: IND AS 16 COMPONENTS */}
          {activeTab === 'components' && (
            <div className="space-y-4">
              <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 flex items-start space-x-3">
                <ShieldCheck className="w-5 h-5 text-blue-600 shrink-0 mt-0.5" />
                <div>
                  <h4 className="text-xs font-bold text-blue-900 uppercase tracking-wider">
                    Ind AS 16 / AS 10 Component Accounting Compliance
                  </h4>
                  <p className="text-xs text-blue-700 mt-0.5 leading-relaxed">
                    Under Ind AS 16 para 43–47, each part of an item of PPE with a cost that is significant in relation to the total cost must be depreciated separately over its specific estimated economic life.
                  </p>
                </div>
              </div>

              {asset.components && asset.components.length > 0 ? (
                <div className="space-y-3">
                  {asset.components.map((comp, idx) => {
                    const costSharePct = Math.round((comp.costINR / asset.costINR) * 100);
                    return (
                      <div key={comp.id} className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-3">
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                          <div className="flex items-center space-x-2">
                            <span className="w-6 h-6 rounded-full bg-slate-900 text-white font-mono text-xs font-bold flex items-center justify-center">
                              {idx + 1}
                            </span>
                            <span className="font-bold text-slate-900 text-sm">{comp.name}</span>
                          </div>
                          <span className="text-xs font-mono font-semibold text-blue-700 bg-white px-2.5 py-1 rounded border border-slate-200 shadow-2xs">
                            {formatINR(comp.costINR, currencyMode)} ({costSharePct}% of Asset)
                          </span>
                        </div>

                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-white p-3 rounded-lg border border-slate-200 text-xs shadow-2xs">
                          <div>
                            <span className="text-slate-500 text-[11px] block">Component ID</span>
                            <span className="font-mono font-semibold text-slate-800">{comp.id}</span>
                          </div>
                          <div>
                            <span className="text-slate-500 text-[11px] block">Useful Life</span>
                            <span className="font-mono font-bold text-emerald-700">{comp.usefulLifeYears} Years</span>
                          </div>
                          <div>
                            <span className="text-slate-500 text-[11px] block">Depreciation Method</span>
                            <span className="font-semibold text-slate-800">{comp.depreciationMethod}</span>
                          </div>
                          <div>
                            <span className="text-slate-500 text-[11px] block">Net Book Value</span>
                            <span className="font-mono font-semibold text-slate-800">{formatINR(comp.nbvINR, currencyMode)}</span>
                          </div>
                        </div>

                        <p className="text-xs text-slate-500 italic">
                          Rationale: {comp.notes}
                        </p>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="bg-slate-50 border border-slate-200 rounded-xl p-6 text-center text-slate-500">
                  <Layers className="w-8 h-8 text-slate-400 mx-auto mb-2" />
                  <p className="font-medium text-slate-700">Single Monolithic Asset Unit</p>
                  <p className="text-xs text-slate-500 mt-1">
                    This asset does not contain distinct sub-components exceeding individual materiality thresholds.
                  </p>
                </div>
              )}
            </div>
          )}

          {/* TAB 3: PROCUREMENT & CAPEX CHAIN */}
          {activeTab === 'procurement' && (
            <div className="space-y-4">
              <div className="bg-slate-50 border border-slate-200 rounded-xl p-4">
                <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider mb-3 flex items-center space-x-1.5">
                  <FileCheck className="w-3.5 h-3.5 text-blue-600" />
                  <span>3-Way Match & Procurement Trail</span>
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                  <div className="bg-white border border-slate-200 p-3 rounded-lg shadow-2xs">
                    <span className="text-slate-500 text-[11px] block">Purchase Order (PO)</span>
                    <span className="font-mono font-bold text-slate-900 block mt-0.5">{asset.poNumber || 'N/A'}</span>
                    <span className="text-[10px] text-emerald-700 font-semibold mt-1 block">PO Approved</span>
                  </div>
                  <div className="bg-white border border-slate-200 p-3 rounded-lg shadow-2xs">
                    <span className="text-slate-500 text-[11px] block">Goods Receipt (GRN)</span>
                    <span className="font-mono font-bold text-slate-900 block mt-0.5">{asset.grnNumber || 'Pending / Missing'}</span>
                    <span className={`text-[10px] font-semibold mt-1 block ${asset.grnNumber ? 'text-emerald-700' : 'text-rose-700'}`}>
                      {asset.grnNumber ? 'Goods Received' : 'Missing Documentation'}
                    </span>
                  </div>
                  <div className="bg-white border border-slate-200 p-3 rounded-lg shadow-2xs">
                    <span className="text-slate-500 text-[11px] block">Tax Invoice No.</span>
                    <span className="font-mono font-bold text-slate-900 block mt-0.5">{asset.invoiceNumber || 'N/A'}</span>
                    <span className="text-[10px] text-slate-500 mt-1 block">Vendor: {asset.vendor}</span>
                  </div>
                  <div className="bg-white border border-slate-200 p-3 rounded-lg shadow-2xs">
                    <span className="text-slate-500 text-[11px] block">Put-to-Use Date</span>
                    <span className="font-mono font-bold text-slate-900 block mt-0.5">{asset.capitalisationDate}</span>
                    <span className="text-[10px] text-blue-700 font-semibold mt-1 block">Capitalisation Memo On File</span>
                  </div>
                </div>
              </div>

              {/* Tax & GST Analysis */}
              <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-2">
                <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider mb-2 flex items-center space-x-1.5">
                  <ShieldCheck className="w-3.5 h-3.5 text-blue-600" />
                  <span>GST & Income Tax Section 32 Assessment</span>
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="bg-white border border-slate-200 p-3 rounded-lg shadow-2xs">
                    <span className="text-slate-500 text-[11px] block">GST Input Tax Credit (ITC)</span>
                    <div className="flex items-center space-x-2 mt-1">
                      <span className="font-bold text-emerald-700 text-sm">
                        {asset.itcClaimed ? 'Claimed & Eligible' : 'Blocked / Not Claimed'}
                      </span>
                      {asset.gstPaidINR && (
                        <span className="text-xs font-mono text-slate-600">
                          (₹{(asset.gstPaidINR / 100000).toFixed(2)}L @ 18%)
                        </span>
                      )}
                    </div>
                    <p className="text-[11px] text-slate-500 mt-1">
                      Goods used in course or furtherance of business under CGST Act Section 16(1).
                    </p>
                  </div>
                  <div className="bg-white border border-slate-200 p-3 rounded-lg shadow-2xs">
                    <span className="text-slate-500 text-[11px] block">Income Tax 180-Day Rule</span>
                    <span className="font-bold text-slate-900 text-sm block mt-1">
                      Full Year 100% Tax Depreciation
                    </span>
                    <p className="text-[11px] text-slate-500 mt-1">
                      Put to use prior to October 4th; eligible for full annual block depreciation rate.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 4: PHYSICAL VERIFICATION & GPS */}
          {activeTab === 'verification' && (
            <div className="space-y-4">
              <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 flex items-center justify-between">
                <div>
                  <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                    CARO 2020 Clause 3(i)(b) Physical Count Status
                  </h4>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Last Verified: <strong className="text-slate-900 font-mono">{asset.lastVerifiedDate || 'Not Verified in Current Period'}</strong>
                  </p>
                </div>
                <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                  asset.verificationStatus === 'Verified'
                    ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                    : 'bg-rose-50 text-rose-700 border border-rose-200'
                }`}>
                  {asset.verificationStatus}
                </span>
              </div>

              {/* Verification History Timeline */}
              <div className="space-y-3">
                {asset.historyEvents?.filter((e) => e.type === 'Physical Verification').map((evt) => (
                  <div key={evt.id} className="bg-slate-50 border border-slate-200 rounded-xl p-3.5 flex items-start space-x-3">
                    <div className="p-2 rounded-lg bg-white text-emerald-600 mt-0.5 border border-slate-200 shadow-2xs">
                      <QrCode className="w-4 h-4" />
                    </div>
                    <div className="space-y-1 flex-1">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-slate-900 text-xs">{evt.description}</span>
                        <span className="font-mono text-slate-500 text-[11px]">{evt.date}</span>
                      </div>
                      <p className="text-xs text-slate-500">
                        Auditor / Inspector: <span className="text-slate-800 font-medium">{evt.actor}</span>
                        {evt.referenceDoc && ` • Ref: ${evt.referenceDoc}`}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 5: GOVERNANCE & EXCEPTIONS */}
          {activeTab === 'governance' && (
            <div className="space-y-4">
              {asset.anomalies && asset.anomalies.length > 0 ? (
                <div className="space-y-3">
                  <div className="bg-rose-50 border border-rose-200 rounded-xl p-4">
                    <h4 className="text-xs font-bold text-rose-900 uppercase tracking-wider mb-2 flex items-center space-x-2">
                      <AlertTriangle className="w-4 h-4 text-rose-600" />
                      <span>Identified Internal Control Anomalies ({asset.anomalies.length})</span>
                    </h4>
                    <ul className="space-y-2">
                      {asset.anomalies.map((anom, i) => (
                        <li key={i} className="flex items-start space-x-2 text-xs text-rose-800">
                          <span className="text-rose-600 font-bold">•</span>
                          <span>{anom}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  {onNavigateToRisk && (
                    <button
                      onClick={() => {
                        onClose();
                        onNavigateToRisk(asset.id);
                      }}
                      className="w-full py-2.5 bg-rose-600 hover:bg-rose-700 text-white font-semibold text-xs rounded-xl flex items-center justify-center space-x-2 transition-all shadow-sm"
                    >
                      <span>Investigate in Risk & Exceptions Engine</span>
                      <ArrowRight className="w-4 h-4" />
                    </button>
                  )}
                </div>
              ) : (
                <div className="bg-slate-50 border border-slate-200 rounded-xl p-8 text-center space-y-2">
                  <CheckCircle2 className="w-10 h-10 text-emerald-600 mx-auto" />
                  <h4 className="font-bold text-slate-900 text-sm">Clean Fixed Asset Record</h4>
                  <p className="text-xs text-slate-500 max-w-md mx-auto">
                    Zero open control exceptions or documentation discrepancies detected. This asset satisfies all Ind AS 16, Schedule II, and CARO 2020 criteria.
                  </p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="p-4 border-t border-slate-200 bg-slate-50 flex items-center justify-between text-xs text-slate-500">
          <span>AssetTrust AI Fixed Asset Dossier • Synced with SAP Subledger</span>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white font-semibold rounded-lg transition-colors shadow-2xs"
          >
            Close Dossier
          </button>
        </div>

      </div>
    </div>
  );
};
