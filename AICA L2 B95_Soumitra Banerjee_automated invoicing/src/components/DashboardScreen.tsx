import React from 'react';
import { 
  Users, 
  FileStack, 
  IndianRupee, 
  Clock, 
  CheckCircle, 
  FileCheck, 
  Send, 
  Calendar,
  ArrowRight,
  TrendingUp,
  FileSpreadsheet
} from 'lucide-react';

interface DashboardData {
  totalClients: number;
  currentQuarter: string;
  totalFilesProcessed: number;
  totalBillingAmount: number;
  pendingConfirmations: number;
  confirmedClients: number;
  invoicesGenerated: number;
  invoicesSent: number;
  recentActivity: Array<{
    id: string;
    action: string;
    entity: string;
    description: string;
    createdAt: string;
  }>;
}

interface DashboardScreenProps {
  data: DashboardData | null;
  loading: boolean;
  onNavigate: (tab: string) => void;
  onRefresh: () => void;
}

export const DashboardScreen: React.FC<DashboardScreenProps> = ({
  data,
  loading,
  onNavigate,
  onRefresh,
}) => {
  if (loading || !data) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[400px]">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-3 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
          <p className="text-sm text-slate-500 font-medium">Loading Dashboard Metrics...</p>
        </div>
      </div>
    );
  }

  const statCards = [
    {
      title: 'Clients',
      value: data.totalClients.toString(),
      subtext: 'Active enterprise clients',
      icon: Users,
      color: 'bg-blue-50 text-blue-700 border-blue-200',
      actionTab: 'clients',
    },
    {
      title: 'Files Processed',
      value: data.totalFilesProcessed.toLocaleString('en-IN'),
      subtext: 'Delivery log records',
      icon: FileStack,
      color: 'bg-indigo-50 text-indigo-700 border-indigo-200',
      actionTab: 'delivery-logs',
    },
    {
      title: 'Billing Amount',
      value: `₹${data.totalBillingAmount.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`,
      subtext: 'Subtotal + 18% GST',
      icon: IndianRupee,
      color: 'bg-emerald-50 text-emerald-700 border-emerald-200',
      actionTab: 'billing',
    },
    {
      title: 'Pending Confirmation',
      value: data.pendingConfirmations.toString(),
      subtext: 'Awaiting client response',
      icon: Clock,
      color: 'bg-amber-50 text-amber-700 border-amber-200',
      actionTab: 'confirmations',
    },
    {
      title: 'Confirmed',
      value: data.confirmedClients.toString(),
      subtext: 'Client approved',
      icon: CheckCircle,
      color: 'bg-teal-50 text-teal-700 border-teal-200',
      actionTab: 'confirmations',
    },
    {
      title: 'Invoices Generated',
      value: data.invoicesGenerated.toString(),
      subtext: 'Ready PDF tax invoices',
      icon: FileCheck,
      color: 'bg-purple-50 text-purple-700 border-purple-200',
      actionTab: 'invoices',
    },
    {
      title: 'Invoices Sent',
      value: data.invoicesSent.toString(),
      subtext: 'Dispatched via email',
      icon: Send,
      color: 'bg-cyan-50 text-cyan-700 border-cyan-200',
      actionTab: 'invoices',
    },
  ];

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      {/* Top Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-blue-950 to-slate-900 rounded-2xl p-6 text-white shadow-md flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-500/20 text-blue-300 border border-blue-400/30">
              Active Cycle: {data.currentQuarter}
            </span>
            <span className="text-xs text-slate-400">| FY 2026-27</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight">Quarterly Billing Dashboard</h1>
          <p className="text-sm text-slate-300">
            End-to-end automation from file processing logs to tax invoice dispatch.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={() => onNavigate('delivery-logs')}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition shadow-sm"
          >
            <FileSpreadsheet className="w-4 h-4" />
            <span>Upload Delivery Log</span>
          </button>
          <button
            onClick={() => onNavigate('billing')}
            className="flex items-center gap-2 px-4 py-2 bg-white/10 hover:bg-white/20 text-white border border-white/20 rounded-lg text-sm font-medium transition"
          >
            <span>Run Billing Calculation</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Metrics Grid */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-semibold text-slate-900">Current Quarter Overview</h2>
          <span className="text-xs font-medium text-slate-500 flex items-center gap-1.5">
            <Calendar className="w-3.5 h-3.5" /> Q1 (April - June 2026)
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {statCards.map((card, idx) => {
            const Icon = card.icon;
            return (
              <div
                key={idx}
                onClick={() => onNavigate(card.actionTab)}
                className="bg-white border border-slate-200 rounded-xl p-5 hover:border-blue-400 hover:shadow-md transition cursor-pointer group"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    {card.title}
                  </span>
                  <div className={`p-2 rounded-lg border ${card.color}`}>
                    <Icon className="w-4 h-4" />
                  </div>
                </div>
                <div className="mt-3">
                  <div className="text-2xl font-bold text-slate-900 tracking-tight group-hover:text-blue-600 transition">
                    {card.value}
                  </div>
                  <p className="text-xs text-slate-500 mt-1 flex items-center justify-between">
                    <span>{card.subtext}</span>
                    <ArrowRight className="w-3 h-3 text-slate-400 opacity-0 group-hover:opacity-100 transition" />
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Two Column Section: Quick Workflow Guide & Recent Audit Trail */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Workflow Steps Guide */}
        <div className="lg:col-span-2 bg-white border border-slate-200 rounded-xl p-6 shadow-xs space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <div>
              <h3 className="text-base font-semibold text-slate-900">Automated Pipeline Progress</h3>
              <p className="text-xs text-slate-500">Live state of the quarterly billing cycle</p>
            </div>
            <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
              <TrendingUp className="w-3.5 h-3.5 mr-1" /> Ready for Q1
            </span>
          </div>

          <div className="space-y-3">
            <div className="flex items-start gap-3 p-3 rounded-lg bg-slate-50 border border-slate-100">
              <div className="w-6 h-6 rounded-full bg-blue-600 text-white flex items-center justify-center text-xs font-bold shrink-0 mt-0.5">
                1
              </div>
              <div className="flex-1 text-xs">
                <span className="font-semibold text-slate-800">Upload Delivery Log:</span> Upload Excel with client file counts for April, May, and June.
              </div>
              <button
                onClick={() => onNavigate('delivery-logs')}
                className="text-xs font-medium text-blue-600 hover:text-blue-800 hover:underline"
              >
                Go to Upload →
              </button>
            </div>

            <div className="flex items-start gap-3 p-3 rounded-lg bg-slate-50 border border-slate-100">
              <div className="w-6 h-6 rounded-full bg-blue-600 text-white flex items-center justify-center text-xs font-bold shrink-0 mt-0.5">
                2
              </div>
              <div className="flex-1 text-xs">
                <span className="font-semibold text-slate-800">Calculate & Review:</span> System calculates subtotal and 18% GST per client rate.
              </div>
              <button
                onClick={() => onNavigate('billing')}
                className="text-xs font-medium text-blue-600 hover:text-blue-800 hover:underline"
              >
                Review Billing →
              </button>
            </div>

            <div className="flex items-start gap-3 p-3 rounded-lg bg-slate-50 border border-slate-100">
              <div className="w-6 h-6 rounded-full bg-blue-600 text-white flex items-center justify-center text-xs font-bold shrink-0 mt-0.5">
                3
              </div>
              <div className="flex-1 text-xs">
                <span className="font-semibold text-slate-800">Send Confirmation Email:</span> Dispatches breakdown to client finance contact.
              </div>
              <button
                onClick={() => onNavigate('emails')}
                className="text-xs font-medium text-blue-600 hover:text-blue-800 hover:underline"
              >
                View Emails →
              </button>
            </div>

            <div className="flex items-start gap-3 p-3 rounded-lg bg-slate-50 border border-slate-100">
              <div className="w-6 h-6 rounded-full bg-blue-600 text-white flex items-center justify-center text-xs font-bold shrink-0 mt-0.5">
                4
              </div>
              <div className="flex-1 text-xs">
                <span className="font-semibold text-slate-800">Simulate Response & Auto-Invoice:</span> Click confirmation; system instantly creates PDF and emails invoice.
              </div>
              <button
                onClick={() => onNavigate('confirmations')}
                className="text-xs font-medium text-blue-600 hover:text-blue-800 hover:underline"
              >
                Confirmations →
              </button>
            </div>
          </div>
        </div>

        {/* Right Col: Recent Audit Trail */}
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="text-base font-semibold text-slate-900">Recent Audit Trail</h3>
              <button
                onClick={() => onNavigate('audit')}
                className="text-xs text-blue-600 hover:text-blue-800 font-medium"
              >
                View All
              </button>
            </div>

            <div className="mt-4 space-y-3">
              {data.recentActivity && data.recentActivity.length > 0 ? (
                data.recentActivity.map((act) => (
                  <div key={act.id} className="text-xs border-l-2 border-blue-500 pl-3 py-0.5">
                    <p className="font-medium text-slate-800 line-clamp-2">{act.description}</p>
                    <span className="text-[10px] text-slate-400">
                      {new Date(act.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} • {new Date(act.createdAt).toLocaleDateString()}
                    </span>
                  </div>
                ))
              ) : (
                <p className="text-xs text-slate-400 py-4 text-center">No recent activity logged</p>
              )}
            </div>
          </div>

          <div className="pt-4 border-t border-slate-100 mt-4">
            <button
              onClick={onRefresh}
              className="w-full py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-medium rounded-lg transition"
            >
              Refresh Dashboard Data
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
