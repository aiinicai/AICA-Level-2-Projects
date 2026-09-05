import React, { useState, useMemo } from 'react';
import { useApp } from '../context/AppContext';
import { Department, Priority, LineItem } from '../types';
import {
  formatINR,
  formatAUD,
  convertInrToAud,
  formatVariance,
  formatIST,
} from '../utils/formatters';
import { HISTORICAL_12_MONTHS } from '../data/initialData';
import {
  TrendingUp,
  DollarSign,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  FileCheck,
  Search,
  Filter,
  ArrowUpDown,
  Building,
  Users,
  Server,
  IndianRupee,
  Layers,
  ChevronDown,
  ChevronUp,
  Download,
  Printer,
  ShieldCheck,
  Edit2,
  Check,
  MessageSquare,
  HelpCircle,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import confetti from 'canvas-confetti';

interface ManagementDashboardProps {
  onOpenApprovalSummary: () => void;
}

export const ManagementDashboard: React.FC<ManagementDashboardProps> = ({
  onOpenApprovalSummary,
}) => {
  const {
    currentUser,
    activeMonth,
    activeMonthId,
    submissions,
    currencyMode,
    executeApprovalDecision,
  } = useApp();

  // Active view tab: 'overview' | 'line-items' | 'variance'
  const [activeTab, setActiveTab] = useState<'overview' | 'line-items' | 'variance'>('overview');

  // Filters & Search for line items table
  const [selectedDeptFilter, setSelectedDeptFilter] = useState<string>('ALL');
  const [selectedPriorityFilter, setSelectedPriorityFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [sortBy, setSortBy] = useState<'amount' | 'department' | 'priority' | 'category'>('amount');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  // Approval Modal state
  const [isApprovalModalOpen, setIsApprovalModalOpen] = useState<boolean>(false);
  const [approvalDecisionType, setApprovalDecisionType] = useState<
    'Approved' | 'Approved with Adjustments' | 'Rejected' | 'Changes Requested'
  >('Approved');
  const [approvalComments, setApprovalComments] = useState<string>('');
  const [lineItemAdjustments, setLineItemAdjustments] = useState<
    Record<string, { approvedAmountInr: number; adjustmentNote: string }>
  >({});

  // Submissions for active month
  const currentSubs = submissions[activeMonthId] || [];

  // Flattened all line items across all departments
  const allLineItems: LineItem[] = useMemo(() => {
    const items: LineItem[] = [];
    currentSubs.forEach((sub) => {
      items.push(...sub.lineItems);
    });
    return items;
  }, [currentSubs]);

  // Grand totals
  const totalInr = allLineItems.reduce((acc, i) => acc + (Number(i.amountInr) || 0), 0);
  const totalAud = convertInrToAud(totalInr, activeMonth.exchangeRate);

  const criticalInr = allLineItems
    .filter((i) => i.priority === 'Critical')
    .reduce((acc, i) => acc + (Number(i.amountInr) || 0), 0);
  const criticalAud = convertInrToAud(criticalInr, activeMonth.exchangeRate);

  const importantInr = allLineItems
    .filter((i) => i.priority === 'Important')
    .reduce((acc, i) => acc + (Number(i.amountInr) || 0), 0);
  const importantAud = convertInrToAud(importantInr, activeMonth.exchangeRate);

  const optionalInr = allLineItems
    .filter((i) => i.priority === 'Optional')
    .reduce((acc, i) => acc + (Number(i.amountInr) || 0), 0);
  const optionalAud = convertInrToAud(optionalInr, activeMonth.exchangeRate);

  // Department Breakdown data for Charts
  const departmentChartData = useMemo(() => {
    const depts: Department[] = ['HR', 'Admin', 'IT', 'Finance'];
    return depts.map((dept) => {
      const sub = currentSubs.find((s) => s.department === dept);
      const inr = sub?.lineItems.reduce((acc, i) => acc + i.amountInr, 0) || 0;
      const aud = convertInrToAud(inr, activeMonth.exchangeRate);
      const crit = sub?.lineItems.filter((i) => i.priority === 'Critical').reduce((acc, i) => acc + i.amountInr, 0) || 0;
      const imp = sub?.lineItems.filter((i) => i.priority === 'Important').reduce((acc, i) => acc + i.amountInr, 0) || 0;
      const opt = sub?.lineItems.filter((i) => i.priority === 'Optional').reduce((acc, i) => acc + i.amountInr, 0) || 0;

      return {
        name: dept,
        inr,
        inrLakhs: parseFloat((inr / 100000).toFixed(2)),
        aud,
        audThousands: parseFloat((aud / 1000).toFixed(1)),
        critical: crit,
        important: imp,
        optional: opt,
      };
    });
  }, [currentSubs, activeMonth.exchangeRate]);

  // Priority Pie Chart Data
  const priorityChartData = [
    { name: 'Critical', value: criticalInr, color: '#ef4444' },
    { name: 'Important', value: importantInr, color: '#f59e0b' },
    { name: 'Optional', value: optionalInr, color: '#94a3b8' },
  ];

  // Variance Analysis (MoM & YoY)
  const varianceAnalysisData = useMemo(() => {
    const priorMonthSummary = HISTORICAL_12_MONTHS.find((h) => h.monthId === '2026-09');
    const yoySummary = HISTORICAL_12_MONTHS.find((h) => h.monthId === '2025-10');

    const depts: Department[] = ['HR', 'Admin', 'IT', 'Finance'];

    const rows = depts.map((dept) => {
      const currentDeptData = departmentChartData.find((d) => d.name === dept);
      const currInr = currentDeptData?.inr || 0;

      let priorInr = 0;
      let yoyInr = 0;

      if (dept === 'HR') {
        priorInr = priorMonthSummary?.hrInr || 0;
        yoyInr = yoySummary?.hrInr || 0;
      } else if (dept === 'Admin') {
        priorInr = priorMonthSummary?.adminInr || 0;
        yoyInr = yoySummary?.adminInr || 0;
      } else if (dept === 'IT') {
        priorInr = priorMonthSummary?.itInr || 0;
        yoyInr = yoySummary?.itInr || 0;
      } else if (dept === 'Finance') {
        priorInr = priorMonthSummary?.financeInr || 0;
        yoyInr = yoySummary?.financeInr || 0;
      }

      const momVar = formatVariance(currInr, priorInr);
      const yoyVar = formatVariance(currInr, yoyInr);

      return {
        department: dept,
        currentInr: currInr,
        currentAud: convertInrToAud(currInr, activeMonth.exchangeRate),
        priorInr,
        priorAud: convertInrToAud(priorInr, priorMonthSummary?.exchangeRate || 0.01815),
        momVariance: momVar,
        yoyInr,
        yoyAud: convertInrToAud(yoyInr, yoySummary?.exchangeRate || 0.01850),
        yoyVariance: yoyVar,
      };
    });

    const totalPriorInr = priorMonthSummary?.totalInr || 0;
    const totalYoyInr = yoySummary?.totalInr || 0;

    return {
      rows,
      totals: {
        currentInr: totalInr,
        currentAud: totalAud,
        priorInr: totalPriorInr,
        priorAud: convertInrToAud(totalPriorInr, 0.01815),
        momVariance: formatVariance(totalInr, totalPriorInr),
        yoyInr: totalYoyInr,
        yoyAud: convertInrToAud(totalYoyInr, 0.01850),
        yoyVariance: formatVariance(totalInr, totalYoyInr),
      },
    };
  }, [departmentChartData, totalInr, totalAud, activeMonth.exchangeRate]);

  // Filtered & Sorted Line Items
  const filteredLineItems = useMemo(() => {
    return allLineItems
      .filter((item) => {
        if (selectedDeptFilter !== 'ALL' && item.department !== selectedDeptFilter) return false;
        if (selectedPriorityFilter !== 'ALL' && item.priority !== selectedPriorityFilter) return false;
        if (searchQuery.trim() !== '') {
          const q = searchQuery.toLowerCase();
          const matchesDesc = item.description.toLowerCase().includes(q);
          const matchesCat = item.category.toLowerCase().includes(q);
          const matchesNote = (item.notes || '').toLowerCase().includes(q);
          if (!matchesDesc && !matchesCat && !matchesNote) return false;
        }
        return true;
      })
      .sort((a, b) => {
        let comp = 0;
        if (sortBy === 'amount') {
          comp = a.amountInr - b.amountInr;
        } else if (sortBy === 'department') {
          comp = a.department.localeCompare(b.department);
        } else if (sortBy === 'priority') {
          const pOrder = { Critical: 3, Important: 2, Optional: 1 };
          comp = (pOrder[a.priority] || 0) - (pOrder[b.priority] || 0);
        } else if (sortBy === 'category') {
          comp = a.category.localeCompare(b.category);
        }
        return sortOrder === 'asc' ? comp : -comp;
      });
  }, [allLineItems, selectedDeptFilter, selectedPriorityFilter, searchQuery, sortBy, sortOrder]);

  // Open Approval Modal
  const handleOpenApprovalModal = (
    type: 'Approved' | 'Approved with Adjustments' | 'Rejected' | 'Changes Requested'
  ) => {
    setApprovalDecisionType(type);
    setApprovalComments(
      type === 'Approved'
        ? 'Approved full cash allocation pack. Approved for Sydney corporate treasury remittance.'
        : type === 'Approved with Adjustments'
        ? 'Approved with selective line item reductions as noted below.'
        : type === 'Changes Requested'
        ? 'Please revise IT hardware replacement schedules and resubmit for review.'
        : 'Budget pack rejected. Over standard operating envelope.'
    );

    // Populate initial adjustments map
    const initialAdjustments: Record<string, { approvedAmountInr: number; adjustmentNote: string }> = {};
    allLineItems.forEach((item) => {
      initialAdjustments[item.id] = {
        approvedAmountInr: item.approvedAmountInr !== undefined ? item.approvedAmountInr : item.amountInr,
        adjustmentNote: item.adjustmentNote || '',
      };
    });
    setLineItemAdjustments(initialAdjustments);
    setIsApprovalModalOpen(true);
  };

  // Submit Decision
  const handleConfirmDecision = () => {
    const adjustmentsList = Object.entries(lineItemAdjustments).map(([id, val]: [string, { approvedAmountInr: number; adjustmentNote: string }]) => ({
      id,
      approvedAmountInr: val.approvedAmountInr,
      adjustmentNote: val.adjustmentNote,
    }));

    executeApprovalDecision(
      activeMonthId,
      approvalDecisionType,
      approvalComments,
      approvalDecisionType === 'Approved with Adjustments' ? adjustmentsList : undefined
    );

    setIsApprovalModalOpen(false);

    if (approvalDecisionType === 'Approved' || approvalDecisionType === 'Approved with Adjustments') {
      try {
        confetti({
          particleCount: 80,
          spread: 70,
          origin: { y: 0.6 },
        });
      } catch {}
    }
  };

  const getPriorityBadge = (priority: Priority) => {
    switch (priority) {
      case 'Critical':
        return 'bg-red-50 text-red-700 border-red-200';
      case 'Important':
        return 'bg-amber-50 text-amber-700 border-amber-200';
      case 'Optional':
        return 'bg-slate-100 text-slate-700 border-slate-200';
    }
  };

  return (
    <div id="management-dashboard-container" className="space-y-6">
      
      {/* Executive Overview Header */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5">
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-800 border border-blue-200 uppercase tracking-widest">
                Management Executive Review
              </span>
              <h2 className="text-xl font-black text-slate-900 tracking-tight">
                Consolidated Cash Requirements Pack
              </h2>
            </div>
            <p className="text-xs text-slate-500 mt-1 flex flex-wrap items-center gap-2">
              <span>Target Month: <strong className="text-slate-800">{activeMonth.label}</strong></span>
              <span>•</span>
              <span>Conversion Rate: <strong className="text-slate-800 font-mono">1 INR = {activeMonth.exchangeRate} AUD</strong></span>
              <span>•</span>
              <span>Pack Status: <strong className="text-slate-800">{activeMonth.status}</strong></span>
            </p>
          </div>

          {/* Action Buttons for Management */}
          <div className="flex flex-wrap items-center gap-2.5">
            <button
              type="button"
              onClick={onOpenApprovalSummary}
              className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-bold text-slate-700 bg-white hover:bg-slate-50 border border-slate-300 rounded-lg shadow-xs transition-colors"
            >
              <Printer className="w-3.5 h-3.5 text-blue-600" />
              <span>Print Sign-off Sheet</span>
            </button>

            {currentUser.role === 'management' && (
              <>
                <button
                  type="button"
                  id="btn-request-changes"
                  onClick={() => handleOpenApprovalModal('Changes Requested')}
                  className="flex items-center gap-1 px-3.5 py-2 text-xs font-bold text-amber-800 bg-amber-50 hover:bg-amber-100 border border-amber-300 rounded-lg shadow-xs transition-colors"
                >
                  <MessageSquare className="w-3.5 h-3.5 text-amber-600" />
                  <span>Request Changes</span>
                </button>

                <button
                  type="button"
                  id="btn-approve-adjustments"
                  onClick={() => handleOpenApprovalModal('Approved with Adjustments')}
                  className="flex items-center gap-1 px-3.5 py-2 text-xs font-bold text-blue-700 bg-blue-50 hover:bg-blue-100 border border-blue-200 rounded-lg shadow-xs transition-colors"
                >
                  <Edit2 className="w-3.5 h-3.5 text-blue-600" />
                  <span>Approve with Adjustments</span>
                </button>

                <button
                  type="button"
                  id="btn-approve-all"
                  onClick={() => handleOpenApprovalModal('Approved')}
                  className="flex items-center gap-1.5 px-5 py-2 text-xs font-bold text-white bg-[#0F172A] hover:bg-black rounded-lg shadow-sm transition-all"
                >
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Approve Entire Pack</span>
                </button>
              </>
            )}
          </div>
        </div>

        {/* Existing Approval Banner if already approved */}
        {activeMonth.approvalRecord && (
          <div className="mt-4 p-3.5 bg-emerald-50 border border-emerald-200 rounded-lg flex items-start gap-3 text-xs text-emerald-900">
            <ShieldCheck className="w-5 h-5 text-emerald-600 mt-0.5 shrink-0" />
            <div className="space-y-0.5">
              <div className="flex items-center gap-2 font-bold">
                <span>Decision: {activeMonth.approvalRecord.decision}</span>
                <span>•</span>
                <span>By {activeMonth.approvalRecord.approverName} ({activeMonth.approvalRecord.approverRole})</span>
                <span>•</span>
                <span className="font-normal font-mono">{formatIST(activeMonth.approvalRecord.decidedAt)}</span>
              </div>
              <p className="text-emerald-800 italic">
                "{activeMonth.approvalRecord.comments || 'Pack approved as requested.'}"
              </p>
              <div className="text-[11px] text-emerald-700 font-semibold pt-1">
                Total Approved: {formatINR(activeMonth.approvalRecord.totalApprovedInr)} ({formatAUD(activeMonth.approvalRecord.totalApprovedAud)}) at locked rate {activeMonth.approvalRecord.exchangeRate}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Primary KPI Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        
        {/* Total Cash Requirement */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
          <div className="text-[10px] uppercase font-bold tracking-wider text-slate-500 mb-1">
            Total Cash Requirement (AUD)
          </div>
          <div className="text-2xl font-black text-slate-900 font-mono">
            {formatAUD(totalAud)}
          </div>
          <div className="mt-2 text-xs text-slate-500 flex items-center justify-between pt-2 border-t border-slate-100">
            <span>INR Conversion:</span>
            <span className="font-bold font-mono text-slate-800">{formatINR(totalInr)}</span>
          </div>
          <div className="mt-1 text-[11px] text-slate-400 flex justify-between">
            <span>MoM Growth:</span>
            <span className="font-semibold text-slate-700">{varianceAnalysisData.totals.momVariance.formatted}</span>
          </div>
        </div>

        {/* Critical Must-Fund Baseline */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm border-l-4 border-l-red-500">
          <div className="text-[10px] uppercase font-bold tracking-wider text-slate-500 mb-1 flex items-center justify-between">
            <span>Critical Priority (MVM)</span>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-red-100 text-red-700 font-bold">Must Fund</span>
          </div>
          <div className="text-2xl font-black text-red-600 font-mono">
            {formatINR(criticalInr)}
          </div>
          <div className="mt-2 text-xs text-emerald-700 font-bold font-mono flex items-center justify-between pt-2 border-t border-slate-100">
            <span>AUD Equivalent:</span>
            <span>{formatAUD(criticalAud)}</span>
          </div>
          <div className="mt-1 text-[11px] text-slate-400 flex justify-between">
            <span>Minimum Viable Envelope:</span>
            <span className="font-semibold text-slate-700">{((criticalInr / (totalInr || 1)) * 100).toFixed(0)}%</span>
          </div>
        </div>

        {/* Important Operational Allocation */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm border-l-4 border-l-amber-500">
          <div className="text-[10px] uppercase font-bold tracking-wider text-slate-500 mb-1 flex items-center justify-between">
            <span>Important Operations</span>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-100 text-amber-700 font-bold">Standard</span>
          </div>
          <div className="text-2xl font-bold text-amber-600 font-mono">
            {formatINR(importantInr)}
          </div>
          <div className="mt-2 text-xs text-emerald-700 font-bold font-mono flex items-center justify-between pt-2 border-t border-slate-100">
            <span>AUD Equivalent:</span>
            <span>{formatAUD(importantAud)}</span>
          </div>
          <div className="mt-1 text-[11px] text-slate-400 flex justify-between">
            <span>Share of Total:</span>
            <span className="font-semibold text-slate-700">{((importantInr / (totalInr || 1)) * 100).toFixed(0)}%</span>
          </div>
        </div>

        {/* Optional & Discretionary */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
          <div className="text-[10px] uppercase font-bold tracking-wider text-slate-500 mb-1 flex items-center justify-between">
            <span>Optional / Discretionary</span>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 font-bold">Adjustable</span>
          </div>
          <div className="text-2xl font-bold text-slate-700 font-mono">
            {formatINR(optionalInr)}
          </div>
          <div className="mt-2 text-xs text-emerald-700 font-bold font-mono flex items-center justify-between pt-2 border-t border-slate-100">
            <span>AUD Equivalent:</span>
            <span>{formatAUD(optionalAud)}</span>
          </div>
          <div className="mt-1 text-[11px] text-slate-400 flex justify-between">
            <span>Adjustment Opportunity:</span>
            <span className="font-semibold text-slate-700">{((optionalInr / (totalInr || 1)) * 100).toFixed(0)}%</span>
          </div>
        </div>

      </div>

      {/* Navigation Sub-Tabs */}
      <div className="flex border-b border-slate-200 gap-2">
        <button
          id="tab-mgmt-overview"
          onClick={() => setActiveTab('overview')}
          className={`pb-2.5 px-4 text-xs font-bold transition-all border-b-2 ${
            activeTab === 'overview'
              ? 'border-blue-600 text-blue-700'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          Executive Visual Analytics
        </button>
        <button
          id="tab-mgmt-line-items"
          onClick={() => setActiveTab('line-items')}
          className={`pb-2.5 px-4 text-xs font-bold transition-all border-b-2 flex items-center gap-1.5 ${
            activeTab === 'line-items'
              ? 'border-blue-600 text-blue-700'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <span>Consolidated Line Items Table</span>
          <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-slate-100 text-slate-700 font-mono">
            {allLineItems.length}
          </span>
        </button>
        <button
          id="tab-mgmt-variance"
          onClick={() => setActiveTab('variance')}
          className={`pb-2.5 px-4 text-xs font-bold transition-all border-b-2 ${
            activeTab === 'variance'
              ? 'border-blue-600 text-blue-700'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          MoM & YoY Variance Analysis
        </button>
      </div>

      {/* TAB 1: Visual Analytics Overview */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          
          {/* Charts Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            
            {/* Chart 1: Cash Requirement by Department */}
            <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-sm font-bold text-slate-900">
                    Cash Allocation by Department
                  </h3>
                  <p className="text-xs text-slate-500">
                    Department requested subtotal in ₹ Lakhs & A$ Thousands
                  </p>
                </div>
                <span className="text-xs font-mono text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                  Rate: {activeMonth.exchangeRate}
                </span>
              </div>

              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={departmentChartData} margin={{ top: 10, right: 20, left: 0, bottom: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                    <XAxis dataKey="name" tick={{ fontSize: 12, fill: '#475569' }} />
                    <YAxis tick={{ fontSize: 11, fill: '#64748b' }} tickFormatter={(val) => `₹${val}L`} />
                    <Tooltip
                      formatter={(value: any, name: any) => {
                        if (name === 'inrLakhs') return [`₹${value} Lakhs`, 'Amount (INR)'];
                        if (name === 'audThousands') return [`A$${value}k`, 'Amount (AUD)'];
                        return [value, name];
                      }}
                      contentStyle={{ backgroundColor: '#ffffff', borderRadius: '8px', border: '1px solid #e2e8f0', fontSize: '12px' }}
                    />
                    <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
                    <Bar dataKey="inrLakhs" name="INR (₹ in Lakhs)" fill="#2563eb" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="audThousands" name="AUD (A$ in Thousands)" fill="#059669" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Chart 2: Priority Split Donut */}
            <div className="lg:col-span-1 bg-white rounded-xl border border-slate-200 p-5 shadow-xs flex flex-col justify-between">
              <div>
                <h3 className="text-sm font-bold text-slate-900">
                  Priority Allocation
                </h3>
                <p className="text-xs text-slate-500 mb-2">
                  Critical vs Important vs Optional split
                </p>

                <div className="h-48 w-full flex items-center justify-center">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={priorityChartData}
                        cx="50%"
                        cy="50%"
                        innerRadius={50}
                        outerRadius={75}
                        paddingAngle={4}
                        dataKey="value"
                      >
                        {priorityChartData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip
                        formatter={(val: any) => [formatINR(Number(val)), 'Total']}
                        contentStyle={{ fontSize: '12px', borderRadius: '8px' }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Priority Legend */}
              <div className="space-y-2 pt-2 border-t border-slate-100 text-xs">
                <div className="flex justify-between items-center">
                  <span className="flex items-center gap-1.5 text-slate-700 font-medium">
                    <span className="w-2.5 h-2.5 rounded-full bg-red-500"></span>
                    Critical:
                  </span>
                  <span className="font-bold text-slate-900 font-mono">
                    {formatINR(criticalInr)} ({((criticalInr / (totalInr || 1)) * 100).toFixed(0)}%)
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="flex items-center gap-1.5 text-slate-700 font-medium">
                    <span className="w-2.5 h-2.5 rounded-full bg-amber-500"></span>
                    Important:
                  </span>
                  <span className="font-bold text-slate-900 font-mono">
                    {formatINR(importantInr)} ({((importantInr / (totalInr || 1)) * 100).toFixed(0)}%)
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="flex items-center gap-1.5 text-slate-700 font-medium">
                    <span className="w-2.5 h-2.5 rounded-full bg-slate-400"></span>
                    Optional:
                  </span>
                  <span className="font-bold text-slate-900 font-mono">
                    {formatINR(optionalInr)} ({((optionalInr / (totalInr || 1)) * 100).toFixed(0)}%)
                  </span>
                </div>
              </div>
            </div>

          </div>

          {/* Chart 3: 12-Month Historical Trend Line */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
              <div>
                <h3 className="text-sm font-bold text-slate-900">
                  12-Month Total Cash Requirements Trajectory
                </h3>
                <p className="text-xs text-slate-500">
                  Monthly trend for Maropost India in INR (₹ Lakhs) and AUD (A$ Thousands)
                </p>
              </div>
              <div className="text-xs font-semibold text-slate-600 bg-slate-50 px-3 py-1 rounded-lg border border-slate-200">
                Oct 2025 – Oct 2026
              </div>
            </div>

            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart
                  data={HISTORICAL_12_MONTHS.map((h) => ({
                    ...h,
                    inrLakhs: parseFloat((h.totalInr / 100000).toFixed(2)),
                    audThousands: parseFloat((h.totalAud / 1000).toFixed(1)),
                  }))}
                  margin={{ top: 10, right: 20, left: 0, bottom: 20 }}
                >
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                  <XAxis dataKey="shortLabel" tick={{ fontSize: 11, fill: '#475569' }} />
                  <YAxis yAxisId="left" tick={{ fontSize: 11, fill: '#2563eb' }} tickFormatter={(val) => `₹${val}L`} />
                  <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11, fill: '#059669' }} tickFormatter={(val) => `A$${val}k`} />
                  <Tooltip
                    formatter={(value: any, name: any) => {
                      if (name === 'inrLakhs') return [`₹${value} Lakhs`, 'Cash Total (INR)'];
                      if (name === 'audThousands') return [`A$${value}k`, 'Cash Total (AUD)'];
                      return [value, name];
                    }}
                    contentStyle={{ borderRadius: '8px', fontSize: '12px' }}
                  />
                  <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
                  <Line yAxisId="left" type="monotone" dataKey="inrLakhs" name="INR Total (₹ Lakhs)" stroke="#2563eb" strokeWidth={2.5} dot={{ r: 3 }} activeDot={{ r: 5 }} />
                  <Line yAxisId="right" type="monotone" dataKey="audThousands" name="AUD Total (A$ Thousands)" stroke="#059669" strokeWidth={2.5} strokeDasharray="4 4" dot={{ r: 3 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

        </div>
      )}

      {/* TAB 2: Consolidated Line Items Table */}
      {activeTab === 'line-items' && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden space-y-0">
          
          {/* Filters Bar */}
          <div className="p-4 bg-slate-50/90 border-b border-slate-200 flex flex-wrap items-center justify-between gap-3 text-xs">
            <div className="flex flex-wrap items-center gap-2.5">
              
              {/* Search Bar */}
              <div className="relative w-56">
                <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search line items..."
                  className="w-full pl-8 pr-2.5 py-1.5 bg-white border border-slate-300 rounded-lg text-xs focus:ring-1 focus:ring-blue-500 focus:outline-none"
                />
              </div>

              {/* Department Filter */}
              <div className="flex items-center gap-1 bg-white border border-slate-300 rounded-lg px-2 py-1">
                <span className="text-slate-400 font-medium">Dept:</span>
                <select
                  value={selectedDeptFilter}
                  onChange={(e) => setSelectedDeptFilter(e.target.value)}
                  className="bg-transparent font-semibold text-slate-800 focus:outline-none cursor-pointer"
                >
                  <option value="ALL">All Departments</option>
                  <option value="HR">HR</option>
                  <option value="Admin">Admin</option>
                  <option value="IT">IT</option>
                  <option value="Finance">Finance</option>
                </select>
              </div>

              {/* Priority Filter */}
              <div className="flex items-center gap-1 bg-white border border-slate-300 rounded-lg px-2 py-1">
                <span className="text-slate-400 font-medium">Priority:</span>
                <select
                  value={selectedPriorityFilter}
                  onChange={(e) => setSelectedPriorityFilter(e.target.value)}
                  className="bg-transparent font-semibold text-slate-800 focus:outline-none cursor-pointer"
                >
                  <option value="ALL">All Priorities</option>
                  <option value="Critical">Critical</option>
                  <option value="Important">Important</option>
                  <option value="Optional">Optional</option>
                </select>
              </div>

            </div>

            {/* Sort Controls */}
            <div className="flex items-center gap-2">
              <span className="text-slate-500">Sort by:</span>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as any)}
                className="bg-white border border-slate-300 rounded-lg px-2 py-1 font-semibold text-slate-800 focus:outline-none cursor-pointer"
              >
                <option value="amount">Amount</option>
                <option value="priority">Priority</option>
                <option value="department">Department</option>
                <option value="category">Category</option>
              </select>

              <button
                onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
                className="p-1.5 bg-white border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 transition-colors"
                title={`Sort ${sortOrder === 'asc' ? 'Descending' : 'Ascending'}`}
              >
                <ArrowUpDown className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-100/80 border-b border-slate-200 text-slate-600 font-semibold">
                  <th className="py-2.5 px-3 w-10 text-center">#</th>
                  <th className="py-2.5 px-3 w-28">Department</th>
                  <th className="py-2.5 px-3 w-44">Category</th>
                  <th className="py-2.5 px-3 min-w-[200px]">Description</th>
                  <th className="py-2.5 px-3 w-24 text-center">Priority</th>
                  <th className="py-2.5 px-3 w-32 text-right">Requested (₹ INR)</th>
                  <th className="py-2.5 px-3 w-32 text-right">Requested (A$ AUD)</th>
                  <th className="py-2.5 px-3 w-32 text-right">Approved (₹ INR)</th>
                  <th className="py-2.5 px-3 min-w-[180px]">Justification / Notes</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredLineItems.map((item, index) => {
                  const aud = convertInrToAud(item.amountInr, activeMonth.exchangeRate);
                  const approvedInr = item.approvedAmountInr !== undefined ? item.approvedAmountInr : item.amountInr;
                  const approvedAud = convertInrToAud(approvedInr, activeMonth.exchangeRate);
                  const isAdjusted = item.approvedAmountInr !== undefined && item.approvedAmountInr !== item.amountInr;

                  return (
                    <tr key={item.id} className="hover:bg-slate-50/80 transition-colors">
                      <td className="py-2.5 px-3 text-center text-slate-400 font-mono">
                        {index + 1}
                      </td>
                      <td className="py-2.5 px-3">
                        <span className="font-bold text-slate-800">
                          {item.department}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-slate-700 font-medium">
                        {item.category}
                      </td>
                      <td className="py-2.5 px-3 text-slate-900 font-normal">
                        {item.description}
                      </td>
                      <td className="py-2.5 px-3 text-center">
                        <span className={`inline-block px-2 py-0.5 rounded text-[10px] border ${getPriorityBadge(item.priority)}`}>
                          {item.priority}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono font-bold text-slate-900">
                        {formatINR(item.amountInr)}
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono font-semibold text-emerald-700 bg-emerald-50/20">
                        {formatAUD(aud)}
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono">
                        {isAdjusted ? (
                          <div>
                            <span className="font-bold text-blue-700">{formatINR(approvedInr)}</span>
                            <div className="text-[10px] text-red-600 line-through">{formatINR(item.amountInr)}</div>
                          </div>
                        ) : (
                          <span className="font-bold text-slate-800">{formatINR(approvedInr)}</span>
                        )}
                      </td>
                      <td className="py-2.5 px-3 text-slate-600 text-[11px] italic">
                        {item.notes || '—'}
                        {item.adjustmentNote && (
                          <div className="text-blue-600 font-semibold not-italic text-[10px] mt-0.5">
                            Adjustment: {item.adjustmentNote}
                          </div>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
              <tfoot>
                <tr className="bg-slate-100 border-t-2 border-slate-300 font-bold text-slate-900 text-xs">
                  <td colSpan={5} className="py-3 px-4 text-right">
                    Total Filtered ({filteredLineItems.length} items):
                  </td>
                  <td className="py-3 px-3 text-right font-mono text-blue-900 text-sm">
                    {formatINR(filteredLineItems.reduce((acc, i) => acc + i.amountInr, 0))}
                  </td>
                  <td className="py-3 px-3 text-right font-mono text-emerald-800 bg-emerald-100/50">
                    {formatAUD(convertInrToAud(filteredLineItems.reduce((acc, i) => acc + i.amountInr, 0), activeMonth.exchangeRate))}
                  </td>
                  <td colSpan={2} className="py-3 px-3 text-xs text-slate-500 font-normal">
                    Converts using {activeMonth.exchangeRate} AUD/INR
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>
      )}

      {/* TAB 3: Variance Analysis (MoM & YoY) */}
      {activeTab === 'variance' && (
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-4">
          <div>
            <h3 className="text-sm font-bold text-slate-900">
              Department Variance Comparison
            </h3>
            <p className="text-xs text-slate-500">
              Current Month ({activeMonth.label}) vs Prior Month (Sep 2026) vs Same Month Last Year (Oct 2025)
            </p>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left border-collapse">
              <thead>
                <tr className="bg-slate-100 border-b border-slate-200 text-slate-700 font-bold">
                  <th className="py-3 px-3">Department</th>
                  <th className="py-3 px-3 text-right">This Month (₹ INR)</th>
                  <th className="py-3 px-3 text-right">This Month (A$ AUD)</th>
                  <th className="py-3 px-3 text-right">Last Month (₹ INR)</th>
                  <th className="py-3 px-3 text-center">MoM %</th>
                  <th className="py-3 px-3 text-right">Last Year (₹ INR)</th>
                  <th className="py-3 px-3 text-center">YoY %</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {varianceAnalysisData.rows.map((row) => (
                  <tr key={row.department} className="hover:bg-slate-50">
                    <td className="py-3 px-3 font-bold text-slate-900">
                      {row.department}
                    </td>
                    <td className="py-3 px-3 text-right font-mono font-bold text-slate-900">
                      {formatINR(row.currentInr)}
                    </td>
                    <td className="py-3 px-3 text-right font-mono text-emerald-700 font-semibold">
                      {formatAUD(row.currentAud)}
                    </td>
                    <td className="py-3 px-3 text-right font-mono text-slate-600">
                      {formatINR(row.priorInr)}
                    </td>
                    <td className="py-3 px-3 text-center">
                      <span
                        className={`px-2 py-0.5 rounded-full text-[11px] font-bold ${
                          row.momVariance.isNeutral
                            ? 'bg-slate-100 text-slate-700'
                            : row.momVariance.isPositive
                            ? 'bg-amber-50 text-amber-700 border border-amber-200'
                            : 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                        }`}
                      >
                        {row.momVariance.formatted}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-right font-mono text-slate-600">
                      {formatINR(row.yoyInr)}
                    </td>
                    <td className="py-3 px-3 text-center">
                      <span
                        className={`px-2 py-0.5 rounded-full text-[11px] font-bold ${
                          row.yoyVariance.isNeutral
                            ? 'bg-slate-100 text-slate-700'
                            : row.yoyVariance.isPositive
                            ? 'bg-amber-50 text-amber-700 border border-amber-200'
                            : 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                        }`}
                      >
                        {row.yoyVariance.formatted}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr className="bg-slate-100/90 border-t-2 border-slate-300 font-bold text-slate-900 text-xs">
                  <td className="py-3 px-3">Total Consolidated:</td>
                  <td className="py-3 px-3 text-right font-mono text-blue-900 text-sm">
                    {formatINR(varianceAnalysisData.totals.currentInr)}
                  </td>
                  <td className="py-3 px-3 text-right font-mono text-emerald-800">
                    {formatAUD(varianceAnalysisData.totals.currentAud)}
                  </td>
                  <td className="py-3 px-3 text-right font-mono">
                    {formatINR(varianceAnalysisData.totals.priorInr)}
                  </td>
                  <td className="py-3 px-3 text-center">
                    <span className="px-2.5 py-0.5 rounded-full bg-slate-200 text-slate-800 text-xs font-black">
                      {varianceAnalysisData.totals.momVariance.formatted}
                    </span>
                  </td>
                  <td className="py-3 px-3 text-right font-mono">
                    {formatINR(varianceAnalysisData.totals.yoyInr)}
                  </td>
                  <td className="py-3 px-3 text-center">
                    <span className="px-2.5 py-0.5 rounded-full bg-slate-200 text-slate-800 text-xs font-black">
                      {varianceAnalysisData.totals.yoyVariance.formatted}
                    </span>
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>
      )}

      {/* APPROVAL WORKFLOW MODAL */}
      {isApprovalModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-2xl w-full p-6 space-y-4 max-h-[90vh] overflow-y-auto">
            
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <span className="text-xs uppercase font-bold text-slate-500 tracking-wider">
                  Management Sign-off Action
                </span>
                <h3 className="text-lg font-bold text-slate-900">
                  {approvalDecisionType === 'Approved'
                    ? 'Approve Entire Monthly Cash Pack'
                    : approvalDecisionType === 'Approved with Adjustments'
                    ? 'Approve with Line Item Adjustments'
                    : approvalDecisionType === 'Changes Requested'
                    ? 'Request Changes / Resubmission'
                    : 'Reject Monthly Cash Pack'}
                </h3>
              </div>
              <button
                onClick={() => setIsApprovalModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 p-1"
              >
                ✕
              </button>
            </div>

            {/* Total summary */}
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 flex items-center justify-between text-xs">
              <div>
                <span className="text-slate-500">Cycle:</span>{' '}
                <strong className="text-slate-900">{activeMonth.label}</strong>
              </div>
              <div>
                <span className="text-slate-500">Total Requested:</span>{' '}
                <strong className="text-blue-900 font-mono">{formatINR(totalInr)}</strong> (
                <span className="text-emerald-700 font-semibold">{formatAUD(totalAud)}</span>)
              </div>
              <div>
                <span className="text-slate-500">FX Rate:</span>{' '}
                <strong className="font-mono">{activeMonth.exchangeRate}</strong>
              </div>
            </div>

            {/* Adjustments Editor if Approved with Adjustments */}
            {approvalDecisionType === 'Approved with Adjustments' && (
              <div className="space-y-2">
                <label className="block text-xs font-bold text-slate-800">
                  Adjust Line Item Amounts (INR):
                </label>
                <div className="max-h-60 overflow-y-auto border border-slate-200 rounded-lg divide-y divide-slate-100 text-xs">
                  {allLineItems.map((item) => {
                    const currentAdj = lineItemAdjustments[item.id] || {
                      approvedAmountInr: item.amountInr,
                      adjustmentNote: '',
                    };

                    return (
                      <div key={item.id} className="p-2.5 flex items-center justify-between gap-3 hover:bg-slate-50">
                        <div className="max-w-[240px]">
                          <span className="font-semibold text-slate-800 block truncate">
                            [{item.department}] {item.description}
                          </span>
                          <span className="text-[10px] text-slate-500">
                            Requested: {formatINR(item.amountInr)} ({item.priority})
                          </span>
                        </div>

                        <div className="flex items-center gap-2">
                          <input
                            type="number"
                            step="1000"
                            value={currentAdj.approvedAmountInr}
                            onChange={(e) => {
                              const val = Math.max(0, parseFloat(e.target.value) || 0);
                              setLineItemAdjustments({
                                ...lineItemAdjustments,
                                [item.id]: {
                                  ...currentAdj,
                                  approvedAmountInr: val,
                                },
                              });
                            }}
                            className="w-28 text-right bg-white border border-slate-300 rounded px-2 py-1 font-mono font-bold text-xs"
                          />
                          <input
                            type="text"
                            placeholder="Adjustment note..."
                            value={currentAdj.adjustmentNote}
                            onChange={(e) => {
                              setLineItemAdjustments({
                                ...lineItemAdjustments,
                                [item.id]: {
                                  ...currentAdj,
                                  adjustmentNote: e.target.value,
                                },
                              });
                            }}
                            className="w-36 bg-white border border-slate-300 rounded px-2 py-1 text-xs"
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Mandatory Decision Comments */}
            <div>
              <label className="block text-xs font-bold text-slate-800 mb-1">
                Executive Comments & Approval Rationale:
              </label>
              <textarea
                rows={3}
                value={approvalComments}
                onChange={(e) => setApprovalComments(e.target.value)}
                placeholder="Mandatory notes for the Controller & Department submitters..."
                className="w-full bg-white border border-slate-300 rounded-lg p-2.5 text-xs text-slate-800 focus:ring-1 focus:ring-blue-500 focus:outline-none"
              />
            </div>

            {/* Modal Actions */}
            <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setIsApprovalModalOpen(false)}
                className="px-4 py-2 text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 border border-slate-300 rounded-lg"
              >
                Cancel
              </button>

              <button
                type="button"
                id="btn-confirm-management-decision"
                onClick={handleConfirmDecision}
                className={`px-5 py-2 text-xs font-bold text-white rounded-lg shadow-sm transition-colors ${
                  approvalDecisionType === 'Approved' || approvalDecisionType === 'Approved with Adjustments'
                    ? 'bg-emerald-600 hover:bg-emerald-700'
                    : approvalDecisionType === 'Changes Requested'
                    ? 'bg-amber-600 hover:bg-amber-700'
                    : 'bg-red-600 hover:bg-red-700'
                }`}
              >
                Confirm Sign-off: {approvalDecisionType}
              </button>
            </div>

          </div>
        </div>
      )}

    </div>
  );
};
