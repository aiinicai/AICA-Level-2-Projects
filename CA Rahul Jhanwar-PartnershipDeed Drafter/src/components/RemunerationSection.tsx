import React from 'react';
import { Landmark, Scale, Info, CheckCircle2 } from 'lucide-react';
import { DeedFormData, Partner } from '../types';

interface RemunerationSectionProps {
  remunType: 'it_act_2025' | 'fixed_salary' | 'fixed_ratio';
  onUpdateRemunType: (type: 'it_act_2025' | 'fixed_salary' | 'fixed_ratio') => void;
  remunDistribution: 'ratio' | 'equal';
  onUpdateDistribution: (dist: 'ratio' | 'equal') => void;
  interestRate: string;
  onUpdateInterestRate: (rate: string) => void;
  partners?: Partner[];
  onUpdatePartnerSalary?: (partnerId: string, salaryMonthly: string) => void;
}

export const RemunerationSection: React.FC<RemunerationSectionProps> = ({
  remunType,
  onUpdateRemunType,
  remunDistribution,
  onUpdateDistribution,
  interestRate,
  onUpdateInterestRate,
  partners,
  onUpdatePartnerSalary,
}) => {
  return (
    <div className="space-y-4">
      
      {/* Remuneration & Tax Framework Controls */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
        
        {/* Remuneration Legal Scheme */}
        <div className="space-y-1">
          <label className="block text-xs font-semibold text-slate-700 mb-1 uppercase tracking-wider">
            Remuneration Legal Framework
          </label>
          <select
            value={remunType}
            onChange={(e) => onUpdateRemunType(e.target.value as any)}
            className="w-full px-3.5 py-2 bg-white border border-slate-300 rounded-lg text-slate-900 font-semibold focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-shadow text-xs"
          >
            <option value="it_act_2025">SEC 35(e) OF IT ACT, 2025 (STATUTORY SLABS 90% / 60%)</option>
            <option value="fixed_salary">SPECIFIC FIXED SALARY PER WORKING PARTNER (e.g. Rs. 50,000/MONTH)</option>
            <option value="fixed_ratio">CUSTOM / FIXED DETERMINATION AS PER CONSENT</option>
          </select>
        </div>

        {/* Remuneration Distribution Basis */}
        <div className="space-y-1">
          <label className="block text-xs font-semibold text-slate-700 mb-1 uppercase tracking-wider">
            Remuneration Distribution Basis
          </label>
          <select
            value={remunDistribution}
            onChange={(e) => onUpdateDistribution(e.target.value as any)}
            className="w-full px-3.5 py-2 bg-white border border-slate-300 rounded-lg text-slate-900 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-shadow text-xs"
          >
            <option value="ratio">IN MUTUAL PROFIT SHARING RATIO AMONG WORKING PARTNERS</option>
            <option value="equal">EQUAL SHARE AMONG ALL WORKING PARTNERS</option>
          </select>
        </div>

        {/* Max Capital Interest Rate */}
        <div className="space-y-1">
          <label className="block text-xs font-semibold text-slate-700 mb-1 uppercase tracking-wider">
            Max Capital Interest (% p.a.)
          </label>
          <input
            type="text"
            value={interestRate}
            onChange={(e) => onUpdateInterestRate(e.target.value.toUpperCase())}
            placeholder="12%"
            className="w-full px-3.5 py-2 bg-white border border-slate-300 rounded-lg text-slate-900 font-bold focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-shadow uppercase text-xs"
          />
        </div>

      </div>

      {/* Statutory Section 35(e) Breakdown Visual Box */}
      {remunType === 'it_act_2025' && (
        <div className="bg-slate-50 border border-slate-200 rounded-xl p-4.5 text-xs space-y-3">
          <div className="flex items-center gap-2 text-slate-900 font-bold">
            <Scale className="w-4 h-4 text-blue-700" />
            <span>Statutory Remuneration Limit Structure under Sec 35(e) Income-tax Act, 2025</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
            <div className="p-3.5 bg-white rounded-lg border border-slate-200 shadow-2xs">
              <div className="font-semibold text-slate-800 text-[11px] uppercase">
                First Rs. 6,00,000/- Book Profit (or in case of Loss):
              </div>
              <div className="text-blue-700 font-bold mt-1 text-sm">
                Rs. 3,00,000/- or 90% of Book Profit
              </div>
              <div className="text-[11px] text-slate-500 mt-0.5">
                Whichever is higher is allowed as deductible remuneration.
              </div>
            </div>

            <div className="p-3.5 bg-white rounded-lg border border-slate-200 shadow-2xs">
              <div className="font-semibold text-slate-800 text-[11px] uppercase">
                Balance Book Profit (above Rs. 6,00,000/-):
              </div>
              <div className="text-blue-700 font-bold mt-1 text-sm">
                60% of Balance Book Profit
              </div>
              <div className="text-[11px] text-slate-500 mt-0.5">
                Automatically indexed with statutory IT Act amendments.
              </div>
            </div>
          </div>

          <div className="flex items-center gap-1.5 text-[11px] text-slate-500 pt-0.5">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
            <span>Working partners are subject to applicable TDS deduction and statutory compliance under the Act.</span>
          </div>
        </div>
      )}

      {/* Fixed Salary Schedule for Working Partners */}
      {remunType === 'fixed_salary' && partners && partners.length > 0 && (
        <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 text-xs space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-slate-900 font-bold">
              <span>💵</span>
              <span>Individual Working Partner Remuneration / Salary Schedule</span>
            </div>
            <span className="text-[10px] font-bold text-blue-700 bg-blue-100 px-2 py-0.5 rounded">
              Subject to Section 40(b) / 35(e) Ceilings
            </span>
          </div>

          <div className="overflow-x-auto border border-slate-200 rounded-lg bg-white shadow-2xs">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-100/75 border-b border-slate-200 text-slate-700 uppercase text-[10px] font-bold">
                <tr>
                  <th className="py-2 px-3">#</th>
                  <th className="py-2 px-3">Partner Name</th>
                  <th className="py-2 px-3 text-center">Status</th>
                  <th className="py-2 px-3 text-right">Monthly Salary (Rs.)</th>
                  <th className="py-2 px-3 text-right">Annual Equivalent</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {partners.map((p, idx) => {
                  const mVal = parseInt(p.salaryMonthly || '0', 10);
                  return (
                    <tr key={p.id || idx} className="hover:bg-slate-50/50">
                      <td className="py-2.5 px-3 text-slate-400 font-medium">{idx + 1}</td>
                      <td className="py-2.5 px-3 font-bold text-slate-800">
                        {p.name ? `${p.titlePrefix || ''} ${p.name}`.trim() : `Partner ${idx + 1}`}
                      </td>
                      <td className="py-2.5 px-3 text-center">
                        {p.isWorking ? (
                          <span className="text-[10px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                            Working
                          </span>
                        ) : (
                          <span className="text-[10px] font-medium text-slate-500 bg-slate-100 px-2 py-0.5 rounded">
                            Sleeping
                          </span>
                        )}
                      </td>
                      <td className="py-2.5 px-3 text-right">
                        {p.isWorking ? (
                          <div className="inline-flex items-center gap-1.5 justify-end">
                            <span className="text-slate-400 font-medium">Rs.</span>
                            <input
                              type="text"
                              value={p.salaryMonthly || ''}
                              onChange={(e) => {
                                const val = e.target.value.replace(/[^0-9]/g, '');
                                if (onUpdatePartnerSalary) onUpdatePartnerSalary(p.id, val);
                              }}
                              placeholder="e.g. 50000"
                              className="w-28 px-2 py-1 text-right border border-slate-300 rounded font-bold text-slate-900 focus:ring-1 focus:ring-blue-500 outline-none"
                            />
                            <span className="text-slate-500 text-[11px]">/ mo</span>
                          </div>
                        ) : (
                          <span className="text-slate-400 italic text-[11px]">N/A (Sleeping)</span>
                        )}
                      </td>
                      <td className="py-2.5 px-3 text-right font-semibold text-slate-700">
                        {p.isWorking && mVal > 0 ? (
                          <span className="text-emerald-700 font-bold">
                            Rs. {(mVal * 12).toLocaleString('en-IN')}/- p.a.
                          </span>
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <p className="text-[11px] text-slate-500 italic">
            Note: You can also specify or update each partner&apos;s salary individually inside their respective Partner Cards in Step 4.
          </p>
        </div>
      )}

    </div>
  );
};
