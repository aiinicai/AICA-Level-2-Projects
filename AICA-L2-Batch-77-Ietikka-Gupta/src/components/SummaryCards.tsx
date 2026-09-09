import React from 'react';
import { 
  AlertTriangle, 
  CheckCircle2, 
  Coins, 
  Receipt,
  AlertCircle,
  TrendingUp,
  Scale
} from 'lucide-react';
import { ChallanRecord } from '../types';

interface SummaryCardsProps {
  records: ChallanRecord[];
}

export const SummaryCards: React.FC<SummaryCardsProps> = ({ records }) => {
  const totalChallans = records.length;
  
  const totalChallanAmount = records.reduce((acc, r) => acc + r.totalChallanAmount, 0);
  const totalEmployeeShare = records.reduce((acc, r) => acc + r.employeeContribution, 0);
  const totalEmployerShare = records.reduce((acc, r) => acc + r.employerContribution, 0);
  const totalAdminCharges = records.reduce((acc, r) => acc + r.adminOtherCharges, 0);
  
  const delayedRecords = records.filter(r => r.status === 'DELAYED');
  const onTimeRecords = records.filter(r => r.status === 'ON_TIME');
  
  const totalDisallowed = records.reduce((acc, r) => acc + r.disallowableAmount, 0);
  const totalComplied = totalEmployeeShare - totalDisallowed;

  const pfRecords = records.filter(r => r.fundType === 'PF');
  const esiRecords = records.filter(r => r.fundType === 'ESI');

  // Estimated Tax Impact (Assuming corporate/firm tax rate of 30% + 4% cess = 31.2%)
  const estimatedTaxLiability = Math.round(totalDisallowed * 0.312);

  return (
    <div className="space-y-4">
      {/* Primary Bento KPI Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        
        {/* Bento Card 1: Total Deposited */}
        <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs relative overflow-hidden flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Total Challan Value</span>
              <span className="p-2 bg-slate-100 text-slate-700 rounded-xl">
                <Receipt className="w-4 h-4" />
              </span>
            </div>
            <div className="mt-3">
              <div className="text-2xl font-black text-slate-900 tracking-tight">
                ₹ {totalChallanAmount.toLocaleString('en-IN')}
              </div>
              <div className="text-xs text-slate-500 mt-1 flex items-center justify-between">
                <span>{totalChallans} Challan(s) Processed</span>
                <span className="text-[11px] font-semibold text-slate-700 bg-slate-100 px-2 py-0.5 rounded-md">
                  PF: {pfRecords.length} | ESI: {esiRecords.length}
                </span>
              </div>
            </div>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500 font-medium">
            <span>Employer: ₹{totalEmployerShare.toLocaleString('en-IN')}</span>
            <span>Admin: ₹{totalAdminCharges.toLocaleString('en-IN')}</span>
          </div>
        </div>

        {/* Bento Card 2: Total Employee Contribution */}
        <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs relative overflow-hidden flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Employee Contribution</span>
              <span className="p-2 bg-indigo-50 text-indigo-600 rounded-xl">
                <Coins className="w-4 h-4" />
              </span>
            </div>
            <div className="mt-3">
              <div className="text-2xl font-black text-slate-900 tracking-tight">
                ₹ {totalEmployeeShare.toLocaleString('en-IN')}
              </div>
              <div className="text-xs text-indigo-700 font-medium mt-1">
                Clause 20(b) & Sec 36(1)(va) Base
              </div>
            </div>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500 font-medium">
            <span>PF EE: ₹{pfRecords.reduce((s, r) => s + r.employeeContribution, 0).toLocaleString('en-IN')}</span>
            <span>ESI EE: ₹{esiRecords.reduce((s, r) => s + r.employeeContribution, 0).toLocaleString('en-IN')}</span>
          </div>
        </div>

        {/* Bento Card 3: Paid On/Before Due Date (Allowed) */}
        <div className="bg-white rounded-2xl border border-emerald-200 p-5 shadow-xs relative overflow-hidden bg-gradient-to-b from-white to-emerald-50/20 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-emerald-800 uppercase tracking-wider">Complied On Time</span>
              <span className="p-2 bg-emerald-100 text-emerald-700 rounded-xl">
                <CheckCircle2 className="w-4 h-4" />
              </span>
            </div>
            <div className="mt-3">
              <div className="text-2xl font-black text-emerald-700 tracking-tight">
                ₹ {totalComplied.toLocaleString('en-IN')}
              </div>
              <div className="text-xs text-emerald-600 mt-1 flex items-center gap-1 font-semibold">
                <span>{onTimeRecords.length} on-time payment(s)</span>
                <span>• Allowed deduction</span>
              </div>
            </div>
          </div>
          <div className="mt-4 pt-3 border-t border-emerald-100 text-[11px] text-emerald-700 font-bold">
            {totalEmployeeShare > 0 
              ? `${((totalComplied / totalEmployeeShare) * 100).toFixed(1)}% statutory compliance rate`
              : 'No records loaded'}
          </div>
        </div>

        {/* Bento Card 4: Disallowed u/s 36(1)(va) */}
        <div className={`rounded-2xl border p-5 shadow-xs transition flex flex-col justify-between ${
          totalDisallowed > 0 
            ? 'bg-rose-50/70 border-rose-200' 
            : 'bg-white border-slate-200'
        }`}>
          <div>
            <div className="flex items-center justify-between">
              <span className={`text-xs font-bold uppercase tracking-wider ${
                totalDisallowed > 0 ? 'text-rose-800' : 'text-slate-500'
              }`}>
                Disallowed u/s 36(1)(va)
              </span>
              <span className={`p-2 rounded-xl ${
                totalDisallowed > 0 ? 'bg-rose-100 text-rose-700' : 'bg-slate-100 text-slate-500'
              }`}>
                <AlertTriangle className="w-4 h-4" />
              </span>
            </div>
            <div className="mt-3">
              <div className={`text-2xl font-black tracking-tight ${
                totalDisallowed > 0 ? 'text-rose-700' : 'text-slate-800'
              }`}>
                ₹ {totalDisallowed.toLocaleString('en-IN')}
              </div>
              <div className={`text-xs mt-1 font-semibold ${
                totalDisallowed > 0 ? 'text-rose-600' : 'text-slate-500'
              }`}>
                {delayedRecords.length > 0 
                  ? `${delayedRecords.length} delayed challan(s) flagged`
                  : 'Zero disallowance (100% On-Time)'}
              </div>
            </div>
          </div>
          <div className={`mt-4 pt-3 border-t text-[11px] ${
            totalDisallowed > 0 ? 'border-rose-200 text-rose-900 font-bold' : 'border-slate-100 text-slate-500'
          }`}>
            {totalDisallowed > 0 
              ? `Est. Tax Addition: +₹${estimatedTaxLiability.toLocaleString('en-IN')} (@31.2%)`
              : 'No additions to taxable income'}
          </div>
        </div>

      </div>

      {/* Disallowance Alert Bento Banner */}
      {totalDisallowed > 0 && (
        <div className="bg-amber-50/90 border border-amber-200 rounded-2xl p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs text-amber-950 shadow-2xs">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-amber-700 shrink-0 mt-0.5" />
            <div>
              <span className="font-bold text-amber-950">Tax Audit Alert (Form 3CD Clause 20(b)): </span>
              <span className="text-amber-900">
                Employee contribution of <strong>₹{totalDisallowed.toLocaleString('en-IN')}</strong> was deposited after the 15th of the succeeding month across {delayedRecords.length} wage month(s). Under the Supreme Court ruling in <em>Checkmate Services</em>, this sum is disallowed under Section 36(1)(va) and must be added back to Business Income.
              </span>
            </div>
          </div>
          <div className="shrink-0 bg-white px-3.5 py-2 rounded-xl border border-amber-200 font-bold text-amber-900 text-center shadow-2xs">
            3CD Add-back: ₹{totalDisallowed.toLocaleString('en-IN')}
          </div>
        </div>
      )}
    </div>
  );
};
