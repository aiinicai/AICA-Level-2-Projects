import React, { useState } from 'react';
import { GSTComplianceData } from '../types';
import { RiskBadge } from './RiskBadge';
import { GSTBlockedCreditWindow } from './GSTBlockedCreditWindow';
import { 
  Scale, 
  MapPin, 
  AlertTriangle, 
  CheckCircle2, 
  AlertOctagon, 
  FileCheck2, 
  ArrowRight, 
  Building, 
  ShieldAlert, 
  FileSpreadsheet,
  Ban,
  Layers,
  Sparkles,
  Compass
} from 'lucide-react';

interface GSTComplianceModuleProps {
  data: GSTComplianceData;
  onExportExcel: () => void;
}

type GSTSubTab = 'blocked_credit' | 'pos_routing' | 'rules_matrix' | 'full_view';

export const GSTComplianceModule: React.FC<GSTComplianceModuleProps> = ({
  data,
  onExportExcel,
}) => {
  const [activeSubTab, setActiveSubTab] = useState<GSTSubTab>('blocked_credit');
  const isPosViolation = !data.isPoSCompliant;
  const totalGst = (data.cgstCharged || 0) + (data.sgstCharged || 0) + (data.igstCharged || 0);
  const itcData = data.itcEligibility;
  const isBlocked = itcData ? itcData.blockedITCAmount > 0 : isPosViolation;

  return (
    <div className="space-y-4">
      
      {/* Module Sub-Tabs Bar: Dedicated Blocked Credit / Eligible GST Input Window */}
      <div className="bg-white p-1.5 rounded-xl border border-slate-200 shadow-2xs flex items-center gap-1.5 overflow-x-auto">
        <button
          onClick={() => setActiveSubTab('blocked_credit')}
          className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-bold transition-all whitespace-nowrap ${
            activeSubTab === 'blocked_credit'
              ? 'bg-indigo-600 text-white shadow-xs'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
          }`}
        >
          <Ban className="w-3.5 h-3.5" />
          <span>Blocked Credit / Eligible for GST Input</span>
          {isBlocked ? (
            <span className={`px-1.5 py-0.2 rounded text-[9px] font-extrabold uppercase ${
              activeSubTab === 'blocked_credit' ? 'bg-rose-500 text-white' : 'bg-rose-100 text-rose-700'
            }`}>
              BLOCKED
            </span>
          ) : (
            <span className={`px-1.5 py-0.2 rounded text-[9px] font-extrabold uppercase ${
              activeSubTab === 'blocked_credit' ? 'bg-emerald-500 text-white' : 'bg-emerald-100 text-emerald-700'
            }`}>
              ELIGIBLE
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveSubTab('pos_routing')}
          className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-bold transition-all whitespace-nowrap ${
            activeSubTab === 'pos_routing'
              ? 'bg-indigo-600 text-white shadow-xs'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
          }`}
        >
          <Compass className="w-3.5 h-3.5" />
          <span>Place of Supply &amp; Tax Determination</span>
          {isPosViolation && (
            <span className={`px-1.5 py-0.2 rounded text-[9px] font-extrabold uppercase ${
              activeSubTab === 'pos_routing' ? 'bg-rose-500 text-white' : 'bg-rose-100 text-rose-700'
            }`}>
              FAIL
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveSubTab('rules_matrix')}
          className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-bold transition-all whitespace-nowrap ${
            activeSubTab === 'rules_matrix'
              ? 'bg-indigo-600 text-white shadow-xs'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
          }`}
        >
          <ShieldAlert className="w-3.5 h-3.5" />
          <span>Statutory Rules Matrix</span>
          <span className={`px-1.5 py-0.2 rounded text-[9px] font-bold ${
            activeSubTab === 'rules_matrix' ? 'bg-indigo-700 text-white' : 'bg-slate-100 text-slate-600'
          }`}>
            {data.complianceFlags?.length || 0}
          </span>
        </button>

        <button
          onClick={() => setActiveSubTab('full_view')}
          className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-bold transition-all whitespace-nowrap ml-auto ${
            activeSubTab === 'full_view'
              ? 'bg-slate-900 text-white shadow-xs'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
          }`}
        >
          <Layers className="w-3.5 h-3.5" />
          <span>Full Audit Dossier</span>
        </button>
      </div>

      {/* VIEW 1: Dedicated Blocked Credit / Eligible for GST Input Window */}
      {(activeSubTab === 'blocked_credit' || activeSubTab === 'full_view') && (
        <GSTBlockedCreditWindow data={data} onExportExcel={onExportExcel} />
      )}

      {/* VIEW 2: Place of Supply & Tax Determination Routing */}
      {(activeSubTab === 'pos_routing' || activeSubTab === 'full_view') && (
        <div className="space-y-4">
          
          {/* Main Reconciliation Dashboard Card */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-xs flex flex-col overflow-hidden">
            <div className="px-5 py-3.5 border-b border-slate-100 flex items-center justify-between bg-slate-50/60">
              <h2 className="font-bold text-slate-700 flex items-center gap-2 text-sm">
                <span className="w-1.5 h-4 bg-indigo-600 rounded-full"></span>
                GST Compliance &amp; Place of Supply (PoS) Inspector
              </h2>
              <button 
                onClick={onExportExcel}
                className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded text-xs font-bold flex items-center gap-1.5 shadow-xs transition-colors"
              >
                <FileSpreadsheet className="w-3.5 h-3.5" />
                <span>Export to Excel (.xlsx)</span>
              </button>
            </div>

            {/* Place of Supply Routing Visual Card */}
            <div className="p-5 border-b border-slate-100 bg-white">
              <h4 className="text-xs font-bold text-slate-600 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                <MapPin className="w-3.5 h-3.5 text-indigo-600" />
                <span>Place of Supply (PoS) Determination Path</span>
              </h4>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 items-center">
                
                {/* Origin: Supplier */}
                <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 space-y-1">
                  <span className="text-[10px] uppercase font-bold text-slate-500">Supplier Origin State:</span>
                  <p className="text-sm font-bold text-slate-800">{data.vendorState || 'Unknown'}</p>
                  <div className="flex items-center gap-1.5 text-xs">
                    <span className="text-slate-500">State Code:</span>
                    <span className="font-mono font-bold text-indigo-700 bg-indigo-50 px-1.5 py-0.5 rounded border border-indigo-200">
                      {data.vendorStateCode || 'N/A'}
                    </span>
                  </div>
                </div>

                {/* Direction Indicator */}
                <div className="flex flex-col items-center justify-center p-2 text-center">
                  <span className="text-[10px] font-bold text-slate-500 mb-1">
                    {data.transactionType === 'INTRA_STATE' ? 'INTRA-STATE SUPPLY' : 'INTER-STATE SUPPLY'}
                  </span>
                  <div className="flex items-center gap-2 text-indigo-600">
                    <span className="h-[2px] w-8 bg-indigo-200" />
                    <ArrowRight className="w-5 h-5" />
                    <span className="h-[2px] w-8 bg-indigo-200" />
                  </div>
                  <span className="text-[11px] font-bold text-slate-700 mt-1">
                    Mandated: <strong className={isPosViolation ? 'text-red-600' : 'text-emerald-700'}>{data.expectedTaxType}</strong>
                  </span>
                </div>

                {/* Destination: Place of Supply */}
                <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 space-y-1">
                  <span className="text-[10px] uppercase font-bold text-slate-500">Place of Supply (PoS):</span>
                  <p className="text-sm font-bold text-slate-800">{data.placeOfSupply || 'Destination'}</p>
                  <div className="flex items-center gap-1.5 text-xs">
                    <span className="text-slate-500">PoS State Code:</span>
                    <span className="font-mono font-bold text-indigo-700 bg-indigo-50 px-1.5 py-0.5 rounded border border-indigo-200">
                      {data.placeOfSupplyStateCode || data.receiverStateCode || 'N/A'}
                    </span>
                  </div>
                </div>

              </div>

              {/* GSTIN 15-Char Inspector */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-3 pt-3 border-t border-slate-100 text-xs">
                <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-between">
                  <div>
                    <span className="text-[10px] text-slate-500 font-bold block">Supplier GSTIN (15-digit):</span>
                    <span className="font-mono font-bold text-slate-800">{data.vendorGSTIN || 'N/A'}</span>
                  </div>
                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                    data.isVendorGSTINValid ? 'bg-emerald-100 text-emerald-800' : 'bg-red-100 text-red-700'
                  }`}>
                    {data.isVendorGSTINValid ? 'VALID SYNTAX' : 'INVALID GSTIN'}
                  </span>
                </div>

                <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-between">
                  <div>
                    <span className="text-[10px] text-slate-500 font-bold block">Recipient GSTIN (15-digit):</span>
                    <span className="font-mono font-bold text-slate-800">{data.receiverGSTIN || 'N/A'}</span>
                  </div>
                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                    data.isReceiverGSTINValid ? 'bg-emerald-100 text-emerald-800' : 'bg-red-100 text-red-700'
                  }`}>
                    {data.isReceiverGSTINValid ? 'VALID SYNTAX' : 'INVALID GSTIN'}
                  </span>
                </div>
              </div>
            </div>

            {/* Sleek Summary Bottom Bar */}
            <div className="p-3 bg-slate-900 flex items-center justify-between text-white text-xs">
              <div className="flex items-center gap-3">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">SUMMARY</span>
                <span className="text-[11px] text-slate-300">
                  {isPosViolation ? 'PoS Rule Violation Detected • Ineligible ITC Flagged' : 'PoS Verified • All GST Rules Pass'}
                </span>
              </div>
              <button 
                onClick={onExportExcel}
                className="bg-indigo-600 text-white px-3 py-1 rounded text-[10px] font-bold uppercase hover:bg-indigo-500 transition-colors shadow-2xs"
              >
                Save Audit Workpaper
              </button>
            </div>
          </div>

          {/* Tax Rates Breakdown Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            <div className="p-3.5 rounded-xl bg-white border border-slate-200 shadow-2xs">
              <span className="text-slate-500 block text-[11px] font-bold mb-1">Taxable Value</span>
              <p className="text-base font-bold font-mono text-slate-800">
                ₹{data.taxableValue?.toLocaleString('en-IN') || '0'}
              </p>
            </div>

            <div className="p-3.5 rounded-xl bg-white border border-slate-200 shadow-2xs">
              <span className="text-slate-500 block text-[11px] font-bold mb-1">CGST Charged</span>
              <p className={`text-base font-bold font-mono ${data.cgstCharged > 0 && isPosViolation ? 'text-red-600 font-extrabold' : 'text-slate-800'}`}>
                ₹{data.cgstCharged?.toLocaleString('en-IN') || '0'}
              </p>
            </div>

            <div className="p-3.5 rounded-xl bg-white border border-slate-200 shadow-2xs">
              <span className="text-slate-500 block text-[11px] font-bold mb-1">SGST Charged</span>
              <p className={`text-base font-bold font-mono ${data.sgstCharged > 0 && isPosViolation ? 'text-red-600 font-extrabold' : 'text-slate-800'}`}>
                ₹{data.sgstCharged?.toLocaleString('en-IN') || '0'}
              </p>
            </div>

            <div className="p-3.5 rounded-xl bg-white border border-slate-200 shadow-2xs">
              <span className="text-slate-500 block text-[11px] font-bold mb-1">IGST Charged</span>
              <p className={`text-base font-bold font-mono ${data.igstCharged > 0 ? 'text-emerald-700' : 'text-slate-400'}`}>
                ₹{data.igstCharged?.toLocaleString('en-IN') || '0'}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* VIEW 3: Statutory Rules Matrix */}
      {(activeSubTab === 'rules_matrix' || activeSubTab === 'full_view') && (
        <div className="space-y-4">
          <div className="space-y-2.5">
            <h4 className="text-xs font-bold text-slate-600 uppercase tracking-wider flex items-center gap-1.5">
              <ShieldAlert className="w-3.5 h-3.5 text-indigo-600" />
              <span>Statutory Rule Verification Matrix ({data.complianceFlags?.length || 0})</span>
            </h4>

            <div className="space-y-2.5">
              {data.complianceFlags && data.complianceFlags.length > 0 ? (
                data.complianceFlags.map((flag, idx) => (
                  <div 
                    key={idx}
                    className={`p-4 rounded-xl border transition-all text-xs bg-white shadow-2xs ${
                      flag.status === 'FAIL'
                        ? 'border-red-200 bg-red-50/20 border-l-4 border-l-red-500'
                        : flag.status === 'WARNING'
                        ? 'border-amber-200 bg-amber-50/20 border-l-4 border-l-amber-500'
                        : 'border-slate-200'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3 mb-2">
                      <div className="flex items-center gap-2">
                        {flag.status === 'FAIL' ? (
                          <AlertOctagon className="w-4 h-4 text-red-600 shrink-0" />
                        ) : flag.status === 'WARNING' ? (
                          <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
                        ) : (
                          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                        )}
                        <span className="font-bold text-slate-800 text-xs sm:text-sm">
                          {flag.rule}
                        </span>
                      </div>
                      <RiskBadge 
                        level={flag.status === 'FAIL' ? 'critical' : flag.status === 'WARNING' ? 'warning' : 'compliant'}
                        label={flag.status}
                        size="sm"
                      />
                    </div>

                    <p className="text-slate-600 text-xs leading-relaxed mb-2.5">
                      {flag.message}
                    </p>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-2 border-t border-slate-100 text-[11px]">
                      <div className="p-2 rounded bg-slate-50 border border-slate-200">
                        <span className="font-bold text-red-700 block mb-0.5">Statutory Impact:</span>
                        <span className="text-slate-600">{flag.impact}</span>
                      </div>
                      <div className="p-2 rounded bg-slate-50 border border-slate-200">
                        <span className="font-bold text-emerald-700 block mb-0.5">Recommended Remedy:</span>
                        <span className="text-slate-600">{flag.remedy}</span>
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                <div className="p-4 rounded-xl bg-white border border-slate-200 text-center text-slate-400 text-xs">
                  No statutory compliance flags.
                </div>
              )}
            </div>
          </div>

          {/* CA Audit Notes */}
          <div className="p-3.5 rounded-xl bg-white border border-slate-200 text-xs text-slate-600 shadow-2xs">
            <span className="font-bold text-slate-800 block mb-1">CA GST Audit Workpaper Note:</span>
            <p className="leading-relaxed">{data.auditNotes}</p>
          </div>
        </div>
      )}

    </div>
  );
};


