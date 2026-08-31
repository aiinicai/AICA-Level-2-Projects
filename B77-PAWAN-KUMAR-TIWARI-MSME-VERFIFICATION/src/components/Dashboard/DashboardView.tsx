import React from 'react';
import {
  Users,
  Building,
  ShieldCheck,
  Clock,
  AlertOctagon,
  IndianRupee,
  FileCheck2,
  TrendingUp,
  AlertTriangle,
  ArrowUpRight,
  ShieldAlert,
  Download,
  PlusCircle,
  FileSpreadsheet,
  CheckCircle2,
  Percent,
  ChevronRight,
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { formatINR, formatINRCompact, formatDate } from '../../utils/formatters';

export const DashboardView: React.FC = () => {
  const {
    metrics,
    vendors,
    invoiceCalculations,
    ageingSummary,
    setActiveTab,
    exceptionAlerts,
    asOfDate,
    rateMaster,
    statutoryRules,
  } = useApp();

  // Top 10 Vendors by Interest Exposure
  const vendorInterestMap = new Map<
    string,
    { id: string; name: string; category: string; interest: number; outstanding: number; overdueCount: number; udyam: string }
  >();

  invoiceCalculations.forEach((calc) => {
    if (!calc.vendorId) return;
    const vendorObj = vendors.find((v) => v.id === calc.vendorId);
    const current = vendorInterestMap.get(calc.vendorId) || {
      id: calc.vendorId,
      name: calc.vendorName,
      category: calc.msmeCategory,
      interest: 0,
      outstanding: 0,
      overdueCount: 0,
      udyam: vendorObj?.udyamRegistrationNumber || 'UDYAM-REG-000',
    };
    current.interest += calc.totalInterestPayable;
    current.outstanding += calc.outstandingPrincipal;
    if (calc.isOverdue) current.overdueCount += 1;
    vendorInterestMap.set(calc.vendorId, current);
  });

  const topVendorsByInterest = Array.from(vendorInterestMap.values())
    .sort((a, b) => b.interest - a.interest)
    .slice(0, 5);

  const currentRate = rateMaster[0] || { referenceRate: 6.5, applicableMSMERate: 19.5 };

  // Calculate compliance percentage
  const compliancePct =
    metrics.totalVendors > 0
      ? Math.round((metrics.verifiedMSMECount / metrics.totalVendors) * 100)
      : 0;

  // Ageing bucket maximums for bar chart scaling
  const maxBucketPrincipal = Math.max(
    ...ageingSummary.buckets.map((b) => b.totalPrincipal),
    1
  );

  return (
    <div className="space-y-6 pb-6">
      {/* KPI Row matching Theme */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 shrink-0">
        {/* KPI 1: Total Vendors */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs hover:border-slate-300 transition-all">
          <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1">
            Total Vendors
          </div>
          <div className="text-2xl font-bold text-slate-900">{metrics.totalVendors}</div>
          <div className="text-[10px] text-slate-400 mt-1 flex items-center justify-between">
            <span className="text-emerald-600 font-semibold flex items-center gap-0.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
              {metrics.msmeCount} MSME ({metrics.microCount} Micro / {metrics.smallCount} Small)
            </span>
          </div>
        </div>

        {/* KPI 2: Verified MSME */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs hover:border-slate-300 transition-all">
          <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1">
            Verified MSME
          </div>
          <div className="text-2xl font-bold text-slate-900">{metrics.verifiedMSMECount}</div>
          <div className="text-[10px] text-blue-600 mt-1 uppercase font-semibold flex items-center justify-between">
            <span>{compliancePct}% Compliance</span>
            <span className="text-slate-400 lowercase font-normal">{metrics.pendingVerificationCount} pending check</span>
          </div>
        </div>

        {/* KPI 3: Overdue Outstanding */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs hover:border-slate-300 transition-all">
          <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1">
            Overdue Outstanding
          </div>
          <div className="text-2xl font-bold text-red-600">
            {formatINR(metrics.overdueOutstanding)}
          </div>
          <div className="text-[10px] text-slate-400 mt-1 italic flex items-center justify-between">
            <span>{metrics.overdueInvoicesCount} Pending Overdue Invoices</span>
            <span className="text-slate-500">Total: {formatINRCompact(metrics.totalMSMEOutstanding)}</span>
          </div>
        </div>

        {/* KPI 4: Interest Liability */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs border-l-4 border-l-amber-500 hover:border-slate-300 transition-all">
          <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1">
            Interest Liability (Sec 16)
          </div>
          <div className="text-2xl font-bold text-amber-600">
            {formatINR(metrics.estimatedInterestLiability)}
          </div>
          <div className="text-[10px] text-slate-400 mt-1 font-medium flex items-center justify-between">
            <span>RBI {currentRate.referenceRate}% × 3 = {currentRate.applicableMSMERate}%</span>
            <span className="text-amber-700 font-bold">Monthly Rest</span>
          </div>
        </div>
      </div>

      {/* Middle Section: Charts & Ageing */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Ageing Analysis Chart (8 Cols) */}
        <div className="lg:col-span-8 bg-white rounded-xl border border-slate-200 shadow-xs p-5 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold text-slate-800 uppercase tracking-tight">
                Ageing Analysis (Outstanding + Interest)
              </h3>
              <p className="text-[11px] text-slate-400">
                Statutory delay buckets as per MSMED Act Section 15
              </p>
            </div>
            <div className="flex items-center gap-3 text-[10px] font-medium">
              <span className="flex items-center gap-1 text-slate-600">
                <div className="w-2 h-2 bg-blue-500 rounded-full" /> Not Due
              </span>
              <span className="flex items-center gap-1 text-slate-600">
                <div className="w-2 h-2 bg-emerald-500 rounded-full" /> 0-30 Days
              </span>
              <span className="flex items-center gap-1 text-slate-600">
                <div className="w-2 h-2 bg-amber-400 rounded-full" /> 31-45 Days
              </span>
              <span className="flex items-center gap-1 text-slate-600">
                <div className="w-2 h-2 bg-red-500 rounded-full" /> 46-90 Days
              </span>
              <span className="flex items-center gap-1 text-slate-600">
                <div className="w-2 h-2 bg-red-700 rounded-full" /> 91+ Days
              </span>
            </div>
          </div>

          {/* Vertical Bar Visualization */}
          <div className="h-44 flex items-end gap-4 sm:gap-6 px-2 pt-4">
            {ageingSummary.buckets.map((b) => {
              const heightPct = Math.max(15, Math.round((b.totalPrincipal / maxBucketPrincipal) * 100));

              let barColor = 'bg-blue-500';
              let lightBg = 'bg-blue-50';
              if (b.bucketKey === '0_30') {
                barColor = 'bg-emerald-500';
                lightBg = 'bg-emerald-50';
              } else if (b.bucketKey === '31_45') {
                barColor = 'bg-amber-400';
                lightBg = 'bg-amber-50';
              } else if (b.bucketKey === '46_90') {
                barColor = 'bg-red-500';
                lightBg = 'bg-red-50';
              } else if (b.bucketKey === '91_180' || b.bucketKey === 'above_180') {
                barColor = 'bg-red-700';
                lightBg = 'bg-red-50';
              }

              return (
                <div key={b.bucketKey} className="flex-1 flex flex-col items-center gap-2 h-full justify-end group">
                  <div className="text-[10px] font-bold text-slate-700 opacity-90 group-hover:scale-105 transition-transform text-center truncate w-full">
                    {formatINRCompact(b.totalPrincipal)}
                  </div>
                  <div className={`w-full ${lightBg} rounded-t-lg relative h-28 overflow-hidden flex items-end`}>
                    <div
                      className={`w-full ${barColor} rounded-t-lg transition-all duration-500 group-hover:opacity-90`}
                      style={{ height: `${heightPct}%` }}
                    />
                  </div>
                  <div className="text-center">
                    <span className="text-[10px] font-semibold text-slate-600 block">
                      {b.bucketName}
                    </span>
                    <span className="text-[9px] text-slate-400 block font-mono">
                      {b.invoiceCount} inv
                    </span>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
            <span className="text-slate-500">
              Total Exposure under Review: <strong className="text-slate-900">{formatINR(ageingSummary.totalPrincipal)}</strong>
            </span>
            <button
              onClick={() => setActiveTab('ageing')}
              className="text-blue-600 hover:text-blue-700 font-bold text-xs flex items-center gap-1 cursor-pointer"
            >
              Open Full Ageing Schedule <ArrowUpRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Verification Status (4 Cols) */}
        <div className="lg:col-span-4 bg-white rounded-xl border border-slate-200 shadow-xs p-5 flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-bold text-slate-800 uppercase tracking-tight mb-1">
              Verification Status
            </h3>
            <p className="text-[11px] text-slate-400 mb-4">
              Udyam registration validation breakdown
            </p>

            <div className="space-y-4">
              {/* Verified */}
              <div>
                <div className="flex justify-between items-center text-xs mb-1">
                  <span className="flex items-center gap-2 text-slate-700">
                    <div className="w-2 h-2 bg-emerald-500 rounded-full" /> Verified MSME
                  </span>
                  <span className="font-bold text-slate-900">{metrics.verifiedMSMECount}</span>
                </div>
                <div className="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden">
                  <div
                    className="bg-emerald-500 h-full rounded-full transition-all"
                    style={{
                      width: `${
                        metrics.totalVendors > 0
                          ? (metrics.verifiedMSMECount / metrics.totalVendors) * 100
                          : 0
                      }%`,
                    }}
                  />
                </div>
              </div>

              {/* Pending */}
              <div>
                <div className="flex justify-between items-center text-xs mb-1">
                  <span className="flex items-center gap-2 text-slate-700">
                    <div className="w-2 h-2 bg-amber-400 rounded-full" /> Pending Verification
                  </span>
                  <span className="font-bold text-slate-900">{metrics.pendingVerificationCount}</span>
                </div>
                <div className="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden">
                  <div
                    className="bg-amber-400 h-full rounded-full transition-all"
                    style={{
                      width: `${
                        metrics.totalVendors > 0
                          ? (metrics.pendingVerificationCount / metrics.totalVendors) * 100
                          : 0
                      }%`,
                    }}
                  />
                </div>
              </div>

              {/* Mismatch */}
              <div>
                <div className="flex justify-between items-center text-xs mb-1">
                  <span className="flex items-center gap-2 text-slate-700">
                    <div className="w-2 h-2 bg-red-500 rounded-full" /> PAN/GSTIN Mismatch
                  </span>
                  <span className="font-bold text-slate-900">{metrics.mismatchVerificationCount}</span>
                </div>
                <div className="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden">
                  <div
                    className="bg-red-500 h-full rounded-full transition-all"
                    style={{
                      width: `${
                        metrics.totalVendors > 0
                          ? (metrics.mismatchVerificationCount / metrics.totalVendors) * 100
                          : 0
                      }%`,
                    }}
                  />
                </div>
              </div>

              {/* Not Verified */}
              <div>
                <div className="flex justify-between items-center text-xs mb-1">
                  <span className="flex items-center gap-2 text-slate-700">
                    <div className="w-2 h-2 bg-slate-400 rounded-full" /> Not Verified / Non-MSME
                  </span>
                  <span className="font-bold text-slate-900">{metrics.notVerifiedCount}</span>
                </div>
                <div className="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden">
                  <div
                    className="bg-slate-400 h-full rounded-full transition-all"
                    style={{
                      width: `${
                        metrics.totalVendors > 0
                          ? (metrics.notVerifiedCount / metrics.totalVendors) * 100
                          : 0
                      }%`,
                    }}
                  />
                </div>
              </div>
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between">
            <button
              onClick={() => setActiveTab('verification')}
              className="w-full py-2 bg-slate-50 hover:bg-slate-100 border border-slate-200 text-slate-700 text-xs font-semibold rounded-lg transition-colors text-center cursor-pointer flex items-center justify-center gap-1.5"
            >
              <ShieldCheck className="w-3.5 h-3.5 text-blue-600" />
              Launch Udyam Verification Hub
            </button>
          </div>
        </div>
      </div>

      {/* Critical Exception Alerts Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs flex flex-col overflow-hidden">
        <div className="px-5 py-3.5 border-b border-slate-100 flex items-center justify-between bg-slate-50/50 shrink-0">
          <div>
            <div className="text-sm font-bold text-slate-800 uppercase tracking-tight">
              Critical Exception Alerts
            </div>
            <div className="text-[11px] text-slate-400">
              Live statutory risk triggers requiring immediate accounting action
            </div>
          </div>
          <button
            onClick={() => setActiveTab('invoices')}
            className="text-blue-600 text-xs font-bold cursor-pointer hover:underline uppercase tracking-wider"
          >
            VIEW ALL INVOICES
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead className="bg-slate-50 text-[10px] text-slate-500 font-bold uppercase tracking-wider border-b border-slate-100">
              <tr>
                <th className="px-5 py-3">Vendor Details</th>
                <th className="px-5 py-3">Issue Type</th>
                <th className="px-5 py-3">Exposure</th>
                <th className="px-5 py-3">Compliance Days</th>
                <th className="px-5 py-3 text-right">Status</th>
              </tr>
            </thead>
            <tbody className="text-xs divide-y divide-slate-50">
              {exceptionAlerts.slice(0, 5).map((alert) => (
                <tr key={alert.id} className="hover:bg-slate-50/70 transition-colors">
                  <td className="px-5 py-3">
                    <div className="font-semibold text-slate-900">{alert.vendorName}</div>
                    <div className="text-[10px] text-slate-400 font-mono">
                      {alert.invoiceNumber ? `Inv: ${alert.invoiceNumber}` : alert.vendorCode || 'VENDOR'}
                    </div>
                  </td>
                  <td className="px-5 py-3 text-slate-600">
                    <div>{alert.title}</div>
                    <div className="text-[10px] text-slate-400">{alert.description}</div>
                  </td>
                  <td className="px-5 py-3 font-semibold text-slate-900">
                    {formatINR(alert.amount || 0)}
                  </td>
                  <td className="px-5 py-3">
                    {alert.daysOverdue !== undefined && alert.daysOverdue > 0 ? (
                      <div>
                        <span className="text-red-600 font-bold">{alert.daysOverdue} Days</span>{' '}
                        <span className="text-slate-400">(Limit 45)</span>
                      </div>
                    ) : (
                      <span className="text-slate-400 italic">--</span>
                    )}
                  </td>
                  <td className="px-5 py-3 text-right">
                    {alert.severity === 'HIGH' ? (
                      <span className="bg-red-100 text-red-700 px-2.5 py-0.5 rounded-full font-bold text-[10px] inline-flex items-center gap-1">
                        🔴 HIGH RISK
                      </span>
                    ) : alert.severity === 'MEDIUM' ? (
                      <span className="bg-amber-100 text-amber-700 px-2.5 py-0.5 rounded-full font-bold text-[10px] inline-flex items-center gap-1">
                        🟡 ATTENTION
                      </span>
                    ) : (
                      <span className="bg-blue-100 text-blue-700 px-2.5 py-0.5 rounded-full font-bold text-[10px] inline-flex items-center gap-1">
                        🔵 APPROACHING
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Accounting Disallowance & Section 22 Summary Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                Interest Provided in Books
              </span>
              <FileCheck2 className="w-4 h-4 text-emerald-600" />
            </div>
            <div className="text-2xl font-bold mt-2 text-emerald-600">
              {formatINR(metrics.interestAlreadyProvided)}
            </div>
            <p className="text-xs text-slate-400 mt-1">Accrued in P&L accounts (Section 22 Disclosure)</p>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-100 text-[11px] text-slate-400 flex items-center justify-between">
            <span>Provision Coverage:</span>
            <span className="font-bold text-slate-700">~35% of calculated</span>
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs border-l-4 border-l-amber-500 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                Unprovided Interest Gap
              </span>
              <AlertTriangle className="w-4 h-4 text-amber-500" />
            </div>
            <div className="text-2xl font-bold mt-2 text-amber-600">
              {formatINR(metrics.interestYetToBeProvided)}
            </div>
            <p className="text-xs text-slate-400 mt-1">Non-deductible under Section 23 of MSMED Act</p>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-100 text-[11px] text-slate-400 flex items-center justify-between">
            <span>Tax Treatment:</span>
            <span className="font-bold text-rose-600">100% Non-Deductible</span>
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs border-l-4 border-l-red-500 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                Section 43B(h) Tax Disallowance
              </span>
              <AlertOctagon className="w-4 h-4 text-red-500" />
            </div>
            <div className="text-2xl font-bold mt-2 text-red-600">
              {formatINR(metrics.section43BHTaxExposure)}
            </div>
            <p className="text-xs text-slate-400 mt-1">Micro/Small unpaid dues at FY end subject to disallowance</p>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-100 text-[11px] text-slate-400 flex items-center justify-between">
            <span>Tax Form Schedule:</span>
            <span className="font-bold text-slate-700">Form 3CD Clause 22</span>
          </div>
        </div>
      </div>
    </div>
  );
};
