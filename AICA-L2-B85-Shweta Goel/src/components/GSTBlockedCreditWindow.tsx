import React, { useState, useMemo } from 'react';
import { GSTComplianceData, GSTLineItemITCClassification } from '../types';
import { 
  ShieldAlert, 
  ShieldCheck, 
  AlertOctagon, 
  CheckCircle2, 
  AlertTriangle, 
  Ban, 
  FileText, 
  Calendar, 
  Clock, 
  Sparkles,
  FileSpreadsheet,
  HelpCircle,
  Car,
  UtensilsCrossed,
  Building2,
  Lock,
  ArrowRight
} from 'lucide-react';

interface GSTBlockedCreditWindowProps {
  data: GSTComplianceData;
  onExportExcel: () => void;
}

export const GSTBlockedCreditWindow: React.FC<GSTBlockedCreditWindowProps> = ({
  data,
  onExportExcel
}) => {
  const totalGst = (data.cgstCharged || 0) + (data.sgstCharged || 0) + (data.igstCharged || 0);
  const isPosViolation = !data.isPoSCompliant;

  // Derive initial ITC data
  const itcData = data.itcEligibility;

  // Interactive items simulator state
  const defaultItems: GSTLineItemITCClassification[] = useMemo(() => {
    if (itcData?.itemClassifications && itcData.itemClassifications.length > 0) {
      return itcData.itemClassifications;
    }

    // Default item inferred from data
    const isBlocked = isPosViolation;
    return [
      {
        description: isPosViolation ? 'Interstate Logistics Transport Freight' : 'Commercial Supplies / B2B Services',
        hsnSac: '996511',
        taxableValue: data.taxableValue || 0,
        taxRatePercent: data.appliedTaxRates?.[0] || 18,
        totalTax: totalGst,
        nature: isPosViolation ? 'Input Services' : 'Input Goods',
        itcEligibility: isBlocked ? 'BLOCKED_POS' : 'ELIGIBLE',
        sectionRef: isBlocked 
          ? 'Section 7 IGST Act / Section 16(2) CGST Act: Wrong tax heads charged by vendor.' 
          : 'Section 16(1) of CGST Act: General Input Tax Credit eligibility.',
        eligibleTaxAmount: isBlocked ? 0 : totalGst,
        blockedTaxAmount: isBlocked ? totalGst : 0,
        reason: isBlocked 
          ? 'Wrong tax heads (CGST+SGST instead of IGST). Ineligible for credit in recipient state.'
          : 'Used in the furtherance of business. 100% Eligible under Section 16.',
        alertLevel: isBlocked ? '🔴 Critical Red (PoS Ineligible)' : '🟢 Compliant Green'
      }
    ];
  }, [itcData, data, totalGst, isPosViolation]);

  const [simulatedItems, setSimulatedItems] = useState<GSTLineItemITCClassification[]>(defaultItems);

  // Synchronize when data prop updates
  React.useEffect(() => {
    setSimulatedItems(defaultItems);
  }, [defaultItems]);

  // Dynamic simulation computation
  const simulatedSummary = useMemo(() => {
    let eligibleSum = 0;
    let blockedSum = 0;

    simulatedItems.forEach(item => {
      if (item.itcEligibility === 'ELIGIBLE') {
        eligibleSum += item.totalTax;
      } else {
        blockedSum += item.totalTax;
      }
    });

    const isFullyBlocked = eligibleSum === 0 && totalGst > 0;
    const isPartiallyBlocked = eligibleSum > 0 && blockedSum > 0;

    return {
      eligibleSum,
      blockedSum,
      isFullyBlocked,
      isPartiallyBlocked,
      eligiblePercent: totalGst > 0 ? Math.round((eligibleSum / totalGst) * 100) : 0,
      blockedPercent: totalGst > 0 ? Math.round((blockedSum / totalGst) * 100) : 0,
    };
  }, [simulatedItems, totalGst]);

  const handleNatureChange = (index: number, newNature: GSTLineItemITCClassification['nature']) => {
    setSimulatedItems(prev => {
      const updated = [...prev];
      const item = { ...updated[index] };
      item.nature = newNature;

      if (newNature === 'Motor Vehicle') {
        item.itcEligibility = 'BLOCKED_17_5';
        item.sectionRef = 'Section 17(5)(a) of CGST Act: ITC on motor vehicles for transportation of persons (≤ 13 seats) is blocked, unless the business is in vehicle reselling, passenger transport, or driving school operations.';
        item.eligibleTaxAmount = 0;
        item.blockedTaxAmount = item.totalTax;
        item.reason = 'Section 17(5)(a) of CGST Act: ITC on motor vehicles for transportation of persons (≤ 13 seats) is blocked, unless the business is in vehicle reselling, passenger transport, or driving school operations.';
        item.alertLevel = '🔴 Critical Red (Blocked Credit)';
      } else if (newNature === 'Food & Catering') {
        item.itcEligibility = 'BLOCKED_17_5';
        item.sectionRef = 'Section 17(5)(b)(i) of CGST Act: Food, beverages, and outdoor catering credits are strictly blocked unless mandated by law for employees or used for taxable outward supply of the same.';
        item.eligibleTaxAmount = 0;
        item.blockedTaxAmount = item.totalTax;
        item.reason = 'Section 17(5)(b)(i) of CGST Act: Food, beverages, and outdoor catering credits are strictly blocked unless mandated by law for employees or used for taxable outward supply of the same.';
        item.alertLevel = '🔴 Critical Red (Blocked Credit)';
      } else if (newNature === 'Works Contract') {
        item.itcEligibility = 'BLOCKED_17_5';
        item.sectionRef = 'Section 17(5)(c) of CGST Act: Works contract services for construction of immovable property (other than plant & machinery) are statutorily blocked.';
        item.eligibleTaxAmount = 0;
        item.blockedTaxAmount = item.totalTax;
        item.reason = 'Works contract for immovable property civil structure. Blocked under Sec 17(5)(c).';
        item.alertLevel = '🔴 Critical Red (Blocked Credit)';
      } else if (newNature === 'Personal / Non-Business' || newNature === 'Other Ineligible') {
        item.itcEligibility = 'BLOCKED_17_5';
        item.sectionRef = 'Section 17(5)(g) of CGST Act: Goods or services used for personal consumption or non-business purposes are disallowed.';
        item.eligibleTaxAmount = 0;
        item.blockedTaxAmount = item.totalTax;
        item.reason = 'Non-business / personal consumption. Blocked under Sec 17(5)(g).';
        item.alertLevel = '🔴 Critical Red (Blocked Credit)';
      } else {
        // Input Goods, Input Services, Capital Goods
        if (isPosViolation) {
          item.itcEligibility = 'BLOCKED_POS';
          item.sectionRef = 'Section 7 IGST Act / Section 16(2) CGST Act: Place of supply violation (CGST+SGST charged instead of IGST on inter-state supply).';
          item.eligibleTaxAmount = 0;
          item.blockedTaxAmount = item.totalTax;
          item.reason = 'Place of supply error (CGST+SGST charged on inter-state supply). Cannot be claimed in recipient state.';
          item.alertLevel = '🔴 Critical Red (PoS Ineligible)';
        } else {
          item.itcEligibility = 'ELIGIBLE';
          item.sectionRef = 'Section 16(1) of CGST Act: Tax invoice received, goods/services delivered & tax deposited. 100% Eligible.';
          item.eligibleTaxAmount = item.totalTax;
          item.blockedTaxAmount = 0;
          item.reason = 'Used in the course or furtherance of business. 100% Eligible under Section 16.';
          item.alertLevel = '🟢 Compliant Green';
        }
      }

      updated[index] = item;
      return updated;
    });
  };

  const isBlockedActive = simulatedSummary.blockedSum > 0;
  const isSec175Active = itcData?.blockedCreditClauses?.some(c => c.isTriggered) || simulatedItems.some(i => i.itcEligibility === 'BLOCKED_17_5');

  return (
    <div className="space-y-4">
      
      {/* Top Banner: ITC Eligibility & Blocked Credit Status */}
      <div className={`p-4 rounded-xl border shadow-xs transition-all ${
        isBlockedActive 
          ? 'bg-rose-50/70 border-rose-200 border-l-4 border-l-rose-600'
          : 'bg-emerald-50/70 border-emerald-200 border-l-4 border-l-emerald-600'
      }`}>
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div className="flex items-start gap-3">
            <div className={`p-2.5 rounded-lg shrink-0 ${
              isBlockedActive ? 'bg-rose-100 text-rose-700' : 'bg-emerald-100 text-emerald-700'
            }`}>
              {isBlockedActive ? <Ban className="w-5 h-5" /> : <ShieldCheck className="w-5 h-5" />}
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                  GST INPUT TAX CREDIT (ITC) AUDIT DETERMINATION
                </span>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                  isBlockedActive ? 'bg-rose-600 text-white' : 'bg-emerald-600 text-white'
                }`}>
                  {isBlockedActive ? (isSec175Active ? 'BLOCKED CREDIT - SEC 17(5)' : 'INELIGIBLE - POS ERROR') : '100% ELIGIBLE ITC'}
                </span>
              </div>
              <h3 className="text-base font-bold text-slate-900 mt-0.5">
                {isBlockedActive 
                  ? `₹${simulatedSummary.blockedSum.toLocaleString('en-IN')} is Blocked / Ineligible from GST Input Credit`
                  : `₹${simulatedSummary.eligibleSum.toLocaleString('en-IN')} is 100% Eligible for Input Tax Credit under Section 16`
                }
              </h3>
              <p className="text-xs text-slate-600 mt-0.5">
                {itcData?.caWorkpaperFinding || (isBlockedActive 
                  ? 'Statutory restriction applies. Credit cannot be utilized for discharge of output GST liability.' 
                  : 'All Section 16(2) statutory golden conditions satisfied. Eligible to be claimed in monthly GSTR-3B.')
                }
              </p>
            </div>
          </div>

          <button
            onClick={onExportExcel}
            className="self-start md:self-center px-3 py-1.5 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 shrink-0 transition-colors shadow-xs"
          >
            <FileSpreadsheet className="w-3.5 h-3.5" />
            <span>Export ITC Workpaper</span>
          </button>
        </div>
      </div>

      {/* 4-Card KPI Breakdown Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
        
        {/* Total GST Paid */}
        <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-2xs">
          <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block mb-1">
            Total GST Billed
          </span>
          <div className="flex items-baseline justify-between">
            <span className="text-xl font-bold font-mono text-slate-800">
              ₹{totalGst.toLocaleString('en-IN')}
            </span>
            <span className="text-[11px] font-bold text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded">
              100%
            </span>
          </div>
          <span className="text-[10px] text-slate-500 mt-1 block">
            CGST: ₹{data.cgstCharged?.toLocaleString('en-IN') || 0} • SGST: ₹{data.sgstCharged?.toLocaleString('en-IN') || 0} • IGST: ₹{data.igstCharged?.toLocaleString('en-IN') || 0}
          </span>
        </div>

        {/* Eligible ITC */}
        <div className="bg-white p-3.5 rounded-xl border border-slate-200 border-l-4 border-l-emerald-500 shadow-2xs">
          <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block mb-1">
            Eligible for GST Input
          </span>
          <div className="flex items-baseline justify-between">
            <span className="text-xl font-bold font-mono text-emerald-700">
              ₹{simulatedSummary.eligibleSum.toLocaleString('en-IN')}
            </span>
            <span className="text-[11px] font-bold text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200">
              {simulatedSummary.eligiblePercent}%
            </span>
          </div>
          <span className="text-[10px] text-emerald-800 font-semibold mt-1 block">
            GSTR-3B Table 4(A)(5) • All Other ITC
          </span>
        </div>

        {/* Blocked / Ineligible ITC */}
        <div className="bg-white p-3.5 rounded-xl border border-slate-200 border-l-4 border-l-rose-500 shadow-2xs">
          <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block mb-1">
            Blocked / Ineligible ITC
          </span>
          <div className="flex items-baseline justify-between">
            <span className={`text-xl font-bold font-mono ${simulatedSummary.blockedSum > 0 ? 'text-rose-600 font-extrabold' : 'text-slate-400'}`}>
              ₹{simulatedSummary.blockedSum.toLocaleString('en-IN')}
            </span>
            <span className={`text-[11px] font-bold px-1.5 py-0.5 rounded ${
              simulatedSummary.blockedSum > 0 ? 'text-rose-700 bg-rose-50 border border-rose-200' : 'text-slate-400 bg-slate-100'
            }`}>
              {simulatedSummary.blockedPercent}%
            </span>
          </div>
          <span className="text-[10px] text-rose-800 font-semibold mt-1 block truncate">
            {isSec175Active ? 'Sec 17(5) Negative List' : (isPosViolation ? 'PoS Inadmissibility' : 'Zero Ineligible')}
          </span>
        </div>

        {/* GSTR-3B Reporting Destination */}
        <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-2xs">
          <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block mb-1">
            GSTR-3B Return Table
          </span>
          <div className="text-sm font-bold text-slate-800 truncate">
            {isBlockedActive 
              ? (isSec175Active ? 'Table 4(B)(1) [Sec 17(5)]' : 'Table 4(B)(2) [Others]')
              : 'Table 4(A)(5) [All Other ITC]'
            }
          </div>
          <span className="text-[10px] text-slate-500 mt-1 block">
            {isBlockedActive ? 'Mandatory Reversal / Disallowance' : 'Direct Credit to Electronic Ledger'}
          </span>
        </div>

      </div>

      {/* KEY REQUESTED SECTION: Red Flags & ITC Ineligibility Reasons (Why the App Should Flag This) */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="px-4 py-3.5 border-b border-slate-200 bg-slate-50/80 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="flex items-center gap-2.5">
            <div className="p-1.5 rounded-lg bg-rose-100 text-rose-700">
              <ShieldAlert className="w-4 h-4 text-rose-600" />
            </div>
            <div>
              <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
                <span>Red Flags &amp; ITC Ineligibility Reasons</span>
                <span className="text-[11px] font-normal text-slate-500">(Why the App Should Flag This)</span>
              </h3>
              <p className="text-[11px] text-slate-500">
                Statutory audit compliance warnings extracted from document items under CGST Act Section 17(5) and Place of Supply rules.
              </p>
            </div>
          </div>
          <span className="text-[10px] font-bold text-rose-700 bg-rose-50 border border-rose-200 px-2 py-0.5 rounded self-start sm:self-center">
            Section 17(5) Compliance Warning Engine
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-slate-100/80 border-b border-slate-200 text-slate-700 text-[11px] font-bold uppercase tracking-wider">
                <th className="p-3.5 w-1/4">Item Description</th>
                <th className="p-3.5 text-right whitespace-nowrap">Charged GST (₹)</th>
                <th className="p-3.5 whitespace-nowrap text-center">ITC Status</th>
                <th className="p-3.5 w-1/3">Income Tax / GST Act Provision</th>
                <th className="p-3.5 whitespace-nowrap">Dashboard Alert Level</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {simulatedItems.map((item, idx) => {
                const isBlocked = item.itcEligibility !== 'ELIGIBLE';
                const statusBadge = isBlocked ? '🚫 Ineligible / Blocked' : '🟢 100% Eligible';
                const alertLevelBadge = item.alertLevel || (isBlocked ? '🔴 Critical Red (Blocked Credit)' : '🟢 Compliant Green');

                // Determine full statutory provision text
                let statutoryProvision = item.sectionRef || item.reason;
                if (item.nature === 'Motor Vehicle' || item.description.toLowerCase().includes('vehicle') || item.description.toLowerCase().includes('car')) {
                  statutoryProvision = 'Section 17(5)(a) of CGST Act: ITC on motor vehicles for transportation of persons (≤ 13 seats) is blocked, unless the business is in vehicle reselling, passenger transport, or driving school operations.';
                } else if (item.nature === 'Food & Catering' || item.description.toLowerCase().includes('catering') || item.description.toLowerCase().includes('food') || item.description.toLowerCase().includes('beverage')) {
                  statutoryProvision = 'Section 17(5)(b)(i) of CGST Act: Food, beverages, and outdoor catering credits are strictly blocked unless mandated by law for employees or used for taxable outward supply of the same.';
                } else if (item.nature === 'Works Contract') {
                  statutoryProvision = 'Section 17(5)(c) of CGST Act: Works contract services for construction of immovable property (other than plant & machinery) are strictly blocked.';
                } else if (item.nature === 'Personal / Non-Business') {
                  statutoryProvision = 'Section 17(5)(g) of CGST Act: Goods or services used for personal consumption or non-business purposes are disallowed.';
                } else if (isPosViolation) {
                  statutoryProvision = 'Section 7 IGST Act / Section 16(2) CGST Act: Erroneously charged intra-state CGST+SGST on inter-state supply. Credit legally inadmissible in recipient state.';
                }

                return (
                  <tr 
                    key={idx} 
                    className={`transition-colors ${
                      isBlocked ? 'bg-rose-50/30 hover:bg-rose-50/60' : 'bg-white hover:bg-slate-50/80'
                    }`}
                  >
                    {/* 1. Item Description */}
                    <td className="p-3.5 font-semibold text-slate-900 align-top">
                      <div className="flex items-start gap-2">
                        {isBlocked ? (
                          <AlertOctagon className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                        ) : (
                          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                        )}
                        <div>
                          <div className="font-bold text-slate-900 text-xs">{item.description}</div>
                          <div className="text-[10px] text-slate-500 font-mono mt-0.5">
                            {item.hsnSac ? `HSN/SAC: ${item.hsnSac}` : ''} {item.taxRatePercent ? `• GST Rate: ${item.taxRatePercent}%` : ''}
                          </div>
                        </div>
                      </div>
                    </td>

                    {/* 2. Charged GST (₹) */}
                    <td className="p-3.5 text-right font-mono font-bold text-slate-900 align-top whitespace-nowrap text-xs">
                      ₹{item.totalTax.toLocaleString('en-IN')}
                    </td>

                    {/* 3. ITC Status */}
                    <td className="p-3.5 text-center align-top whitespace-nowrap">
                      <span className={`px-2.5 py-1 rounded-md text-[11px] font-extrabold inline-flex items-center gap-1.5 shadow-2xs ${
                        isBlocked 
                          ? 'bg-rose-100 text-rose-800 border border-rose-300' 
                          : 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                      }`}>
                        {statusBadge}
                      </span>
                    </td>

                    {/* 4. Income Tax / GST Act Provision */}
                    <td className="p-3.5 text-slate-700 text-[11px] leading-relaxed align-top">
                      <div className={`p-2.5 rounded-lg border ${
                        isBlocked 
                          ? 'bg-rose-50/80 border-rose-200/80 text-rose-950 font-medium' 
                          : 'bg-slate-50 border-slate-200 text-slate-700'
                      }`}>
                        {statutoryProvision}
                      </div>
                    </td>

                    {/* 5. Dashboard Alert Level */}
                    <td className="p-3.5 align-top whitespace-nowrap">
                      {isBlocked ? (
                        <span className="px-2.5 py-1 rounded-md text-[11px] font-bold bg-rose-600 text-white shadow-2xs inline-flex items-center gap-1.5">
                          <span>🔴</span>
                          <span>Critical Red (Blocked Credit)</span>
                        </span>
                      ) : (
                        <span className="px-2.5 py-1 rounded-md text-[11px] font-bold bg-emerald-600 text-white shadow-2xs inline-flex items-center gap-1.5">
                          <span>🟢</span>
                          <span>Compliant Green</span>
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Section 17(5) Statutory Guidance Footnote */}
        <div className="p-3 bg-slate-900 text-slate-300 text-[11px] border-t border-slate-800 flex items-start gap-2">
          <Lock className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
          <div>
            <strong className="text-white">Why the App Flags This: </strong>
            Under Section 17(5) of the Central Goods and Services Tax (CGST) Act, 2017, Input Tax Credit cannot be availed on specified negative-list supplies (such as passenger motor vehicles $\le 13$ seats and food/outdoor catering) even when received for business purposes and supported by valid tax invoices. Claiming blocked ITC in GSTR-3B Table 4(A)(5) triggers automated scrutiny notices under Section 73/74 with mandatory 18% p.a. interest.
          </div>
        </div>
      </div>

      {/* Main Grid: Section 17(5) Negative List & Section 16 Conditions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        
        {/* Left Column: Section 17(5) Blocked Credit Auditor Checklist */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-xs flex flex-col overflow-hidden">
          <div className="px-4 py-3 border-b border-slate-100 bg-slate-50/70 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="w-1.5 h-4 bg-rose-600 rounded-full"></span>
              <h4 className="font-bold text-slate-800 text-xs uppercase tracking-wider flex items-center gap-1.5">
                <Ban className="w-3.5 h-3.5 text-rose-600" />
                <span>Section 17(5) Statutory Negative List Checklist</span>
              </h4>
            </div>
            <span className="text-[10px] font-bold text-slate-500 bg-white px-2 py-0.5 rounded border border-slate-200">
              CGST Act 2017
            </span>
          </div>

          <div className="p-4 space-y-3 flex-1 overflow-y-auto max-h-[460px]">
            {itcData?.blockedCreditClauses && itcData.blockedCreditClauses.length > 0 ? (
              itcData.blockedCreditClauses.map((clause, idx) => {
                const isBlocked = clause.isTriggered;
                return (
                  <div 
                    key={idx}
                    className={`p-3 rounded-lg border text-xs transition-all ${
                      isBlocked 
                        ? 'bg-rose-50/40 border-rose-200 border-l-4 border-l-rose-600' 
                        : 'bg-slate-50/50 border-slate-200 hover:border-slate-300'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2 mb-1">
                      <div className="flex items-center gap-1.5">
                        {isBlocked ? (
                          <AlertOctagon className="w-4 h-4 text-rose-600 shrink-0" />
                        ) : (
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                        )}
                        <span className="font-bold text-slate-800">
                          {clause.clause}: {clause.title}
                        </span>
                      </div>
                      <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold uppercase tracking-tight ${
                        isBlocked ? 'bg-rose-600 text-white' : 'bg-emerald-100 text-emerald-800'
                      }`}>
                        {isBlocked ? 'BLOCKED' : 'CLEAR'}
                      </span>
                    </div>

                    <p className="text-[11px] text-slate-500 italic mb-1.5">
                      "{clause.statutoryText}"
                    </p>

                    <div className={`p-2 rounded text-[11px] ${
                      isBlocked ? 'bg-rose-100/70 text-rose-900 font-semibold' : 'bg-slate-100 text-slate-600'
                    }`}>
                      <span className="font-bold block text-[10px] uppercase text-slate-500 mb-0.5">Auditor Assessment:</span>
                      {clause.reason}
                    </div>
                  </div>
                );
              })
            ) : (
              // Default Fallback Section 17(5) Clauses
              [
                { clause: '17(5)(a)', title: 'Motor Vehicles & Conveyances', desc: 'Passenger cars seating <= 13 unless used for taxable supply/driving school/resale.', blocked: false },
                { clause: '17(5)(b)(i)', title: 'Food, Beverages & Catering', desc: 'Outdoor catering, beauty, health services (unless statutory obligation).', blocked: false },
                { clause: '17(5)(b)(ii)', title: 'Club Memberships', desc: 'Club, gym and health fitness subscriptions.', blocked: false },
                { clause: '17(5)(c)', title: 'Works Contract Services', desc: 'Civil construction of immovable property (other than Plant & Machinery).', blocked: false },
                { clause: '17(5)(g)', title: 'Personal Consumption', desc: 'Goods or services used for non-business or personal use.', blocked: false },
                { clause: '17(5)(h)', title: 'Gifts & Free Samples', desc: 'Goods lost, stolen, written off or distributed as free gifts.', blocked: false },
              ].map((c, i) => (
                <div key={i} className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-800">{c.clause}: {c.title}</span>
                    <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-emerald-100 text-emerald-800">CLEAR</span>
                  </div>
                  <p className="text-[11px] text-slate-500 mt-1">{c.desc}</p>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right Column: Section 16(2) "Golden Conditions" + Statutory Limits */}
        <div className="space-y-4 flex flex-col">
          
          {/* Section 16 Golden Conditions Card */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-xs flex flex-col overflow-hidden">
            <div className="px-4 py-3 border-b border-slate-100 bg-slate-50/70 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="w-1.5 h-4 bg-indigo-600 rounded-full"></span>
                <h4 className="font-bold text-slate-800 text-xs uppercase tracking-wider flex items-center gap-1.5">
                  <ShieldCheck className="w-3.5 h-3.5 text-indigo-600" />
                  <span>Section 16(2) "Golden Four Conditions"</span>
                </h4>
              </div>
              <span className="text-[10px] font-bold text-slate-500 bg-white px-2 py-0.5 rounded border border-slate-200">
                Eligibility Mandates
              </span>
            </div>

            <div className="p-4 space-y-2.5">
              {itcData?.section16GoldenConditions && itcData.section16GoldenConditions.length > 0 ? (
                itcData.section16GoldenConditions.map((cond, idx) => (
                  <div 
                    key={idx}
                    className={`p-2.5 rounded-lg border text-xs flex items-start justify-between gap-3 ${
                      cond.isSatisfied 
                        ? 'bg-emerald-50/30 border-emerald-200' 
                        : 'bg-rose-50/40 border-rose-200 border-l-4 border-l-rose-600'
                    }`}
                  >
                    <div className="space-y-0.5">
                      <div className="flex items-center gap-1.5">
                        <span className="font-mono text-[10px] font-bold text-indigo-700 bg-indigo-50 px-1 rounded">
                          {cond.statutoryRef}
                        </span>
                        <span className="font-bold text-slate-800 text-[11px]">
                          {cond.title}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-600">
                        {cond.requirement}
                      </p>
                      <p className="text-[10px] font-semibold text-slate-500">
                        Note: {cond.notes}
                      </p>
                    </div>

                    <span className={`px-2 py-0.5 rounded text-[9px] font-bold uppercase shrink-0 ${
                      cond.isSatisfied ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-600 text-white'
                    }`}>
                      {cond.isSatisfied ? 'SATISFIED' : 'NOT MET'}
                    </span>
                  </div>
                ))
              ) : (
                <div className="text-xs text-slate-500 p-3">
                  All 4 Golden Conditions (Invoice, Receipt, Tax Deposited, GSTR-3B) verified.
                </div>
              )}
            </div>
          </div>

          {/* Statutory Timing & 180-Day Rule 37 Box */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            
            {/* Sec 16(4) Time Limit */}
            <div className="p-3 bg-white rounded-xl border border-slate-200 shadow-2xs text-xs space-y-1">
              <div className="flex items-center justify-between text-slate-500">
                <span className="font-bold uppercase text-[10px] flex items-center gap-1">
                  <Calendar className="w-3 h-3 text-indigo-600" />
                  Sec 16(4) Claim Deadline
                </span>
                <span className="text-[9px] font-bold bg-indigo-50 text-indigo-700 px-1 rounded">
                  CUT-OFF
                </span>
              </div>
              <p className="text-sm font-bold font-mono text-slate-800">
                {itcData?.timeLimitSection16_4?.maxAvailmentDate || '30th November'}
              </p>
              <p className="text-[10px] text-slate-500">
                ITC must be availed on or before 30th Nov following the end of financial year.
              </p>
            </div>

            {/* Rule 37 180-Day Reversal */}
            <div className="p-3 bg-white rounded-xl border border-slate-200 shadow-2xs text-xs space-y-1">
              <div className="flex items-center justify-between text-slate-500">
                <span className="font-bold uppercase text-[10px] flex items-center gap-1">
                  <Clock className="w-3 h-3 text-amber-600" />
                  Rule 37: 180-Day Payment
                </span>
                <span className="text-[9px] font-bold bg-amber-50 text-amber-700 px-1 rounded">
                  18% INT
                </span>
              </div>
              <p className="text-sm font-bold font-mono text-slate-800">
                {itcData?.rule37_180DaysReversal?.paymentDueDate180Days || '180 Days from Inv'}
              </p>
              <p className="text-[10px] text-slate-500">
                Unpaid invoices exceeding 180 days require ITC reversal with 18% p.a. interest.
              </p>
            </div>

          </div>

        </div>

      </div>

      {/* Interactive Line Item ITC Nature Classifier & Simulator */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="px-4 py-3 border-b border-slate-100 bg-slate-50/70 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h4 className="font-bold text-slate-800 text-xs uppercase tracking-wider flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
              <span>Interactive Line Item ITC Classification &amp; Auditor Simulator</span>
            </h4>
            <p className="text-[11px] text-slate-500 mt-0.5">
              Simulate how modifying line item expense categories recalculates eligible vs blocked ITC in real time.
            </p>
          </div>
          <span className="text-[10px] font-bold text-indigo-700 bg-indigo-50 border border-indigo-200 px-2 py-0.5 rounded self-start sm:self-center">
            Live CA Simulator
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-slate-100/70 border-b border-slate-200 text-slate-600 text-[11px] font-bold uppercase tracking-wider">
                <th className="p-3">Line Item Description</th>
                <th className="p-3">HSN/SAC</th>
                <th className="p-3 text-right">Taxable (₹)</th>
                <th className="p-3 text-right">Total GST (₹)</th>
                <th className="p-3">Expense Nature (Auditor Selector)</th>
                <th className="p-3">ITC Status</th>
                <th className="p-3 text-right">Eligible ITC (₹)</th>
                <th className="p-3 text-right">Blocked ITC (₹)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {simulatedItems.map((item, idx) => {
                const isBlocked = item.itcEligibility !== 'ELIGIBLE';
                return (
                  <tr key={idx} className="hover:bg-slate-50/60 transition-colors">
                    <td className="p-3 font-medium text-slate-800 max-w-[200px]">
                      <div>{item.description}</div>
                      <div className="text-[10px] text-slate-400 mt-0.5 truncate">{item.reason}</div>
                    </td>
                    <td className="p-3 font-mono text-slate-600">{item.hsnSac || 'N/A'}</td>
                    <td className="p-3 text-right font-mono text-slate-700">
                      ₹{item.taxableValue?.toLocaleString('en-IN') || 0}
                    </td>
                    <td className="p-3 text-right font-mono font-bold text-slate-800">
                      ₹{item.totalTax?.toLocaleString('en-IN') || 0}
                    </td>
                    <td className="p-3">
                      <select
                        value={item.nature}
                        onChange={(e) => handleNatureChange(idx, e.target.value as any)}
                        className="bg-white border border-slate-300 rounded px-2 py-1 text-xs font-semibold text-slate-800 focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500"
                      >
                        <option value="Input Goods">Input Goods (Raw Material / Consumable) [Eligible]</option>
                        <option value="Input Services">Input Services (Operational / Professional) [Eligible]</option>
                        <option value="Capital Goods">Capital Goods (Plant &amp; Machinery) [Eligible]</option>
                        <option value="Motor Vehicle">Motor Vehicle (Passenger &le; 13 Seater) [Sec 17(5)(a) Blocked]</option>
                        <option value="Food & Catering">Food, Beverages &amp; Outdoor Catering [Sec 17(5)(b)(i) Blocked]</option>
                        <option value="Works Contract">Works Contract for Immovable Civil Property [Sec 17(5)(c) Blocked]</option>
                        <option value="Personal / Non-Business">Personal / Non-Business Expense [Sec 17(5)(g) Blocked]</option>
                      </select>
                    </td>
                    <td className="p-3">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase inline-flex items-center gap-1 ${
                        isBlocked ? 'bg-rose-100 text-rose-800' : 'bg-emerald-100 text-emerald-800'
                      }`}>
                        {isBlocked ? <Ban className="w-3 h-3" /> : <CheckCircle2 className="w-3 h-3" />}
                        {isBlocked ? (item.itcEligibility === 'BLOCKED_POS' ? 'PoS Inadmissible' : 'Blocked 17(5)') : 'Eligible ITC'}
                      </span>
                    </td>
                    <td className="p-3 text-right font-mono font-bold text-emerald-700">
                      ₹{(!isBlocked ? item.totalTax : 0).toLocaleString('en-IN')}
                    </td>
                    <td className="p-3 text-right font-mono font-bold text-rose-600">
                      ₹{(isBlocked ? item.totalTax : 0).toLocaleString('en-IN')}
                    </td>
                  </tr>
                );
              })}
            </tbody>
            <tfoot>
              <tr className="bg-slate-900 text-white font-bold text-xs">
                <td colSpan={6} className="p-3 text-right uppercase tracking-wider">
                  Reconciled Total ITC Outcome:
                </td>
                <td className="p-3 text-right font-mono text-emerald-400 text-sm">
                  ₹{simulatedSummary.eligibleSum.toLocaleString('en-IN')}
                </td>
                <td className="p-3 text-right font-mono text-rose-400 text-sm">
                  ₹{simulatedSummary.blockedSum.toLocaleString('en-IN')}
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      {/* CA Audit Opinion & GSTR-3B Statutory Disclosure Workpaper */}
      <div className="p-4 rounded-xl bg-slate-900 text-slate-200 text-xs space-y-2.5 shadow-sm">
        <div className="flex items-center justify-between border-b border-slate-800 pb-2">
          <span className="font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
            <FileText className="w-4 h-4 text-indigo-400" />
            Chartered Accountant Statutory Audit Directive &amp; Workpaper Entry
          </span>
          <span className="text-[10px] font-mono text-indigo-300 bg-indigo-950 px-2 py-0.5 rounded border border-indigo-800">
            Form GSTR-3B &amp; GSTR-9
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-[11px] pt-1">
          <div className="p-3 rounded-lg bg-slate-800/80 border border-slate-700">
            <span className="font-bold text-amber-400 uppercase text-[10px] block mb-1">
              GSTR-3B Return Filing Instructions:
            </span>
            <p className="text-slate-300 leading-relaxed">
              {isBlockedActive
                ? (isSec175Active 
                    ? "Disclose the tax amount in Table 4(B)(1) as Ineligible ITC under Section 17(5). Do not populate in Table 4(A)(5) to prevent automated system notices under Section 73/74."
                    : "Do NOT claim in Table 4(A)(5). Due to Place of Supply violation, this must be disclosed under Table 4(B)(2) / Others pending supplier credit note.")
                : "Eligible for 100% claim in Table 4(A)(5) [All Other ITC] of Form GSTR-3B for the respective tax period."
              }
            </p>
          </div>

          <div className="p-3 rounded-lg bg-slate-800/80 border border-slate-700">
            <span className="font-bold text-emerald-400 uppercase text-[10px] block mb-1">
              Statutory Action Required:
            </span>
            <p className="text-slate-300 leading-relaxed">
              {itcData?.actionRequired || (isBlockedActive
                ? "Expense out the blocked GST amount directly to Profit & Loss Account under relevant expenditure head."
                : "Retain invoice in valid purchase register and verify monthly GSTR-2B reflection.")
              }
            </p>
          </div>
        </div>
      </div>

    </div>
  );
};
