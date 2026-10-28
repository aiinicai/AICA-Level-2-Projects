import React, { useState, useMemo } from 'react';
import {
  Zap,
  Droplets,
  Phone,
  Wifi,
  Flame,
  Tv,
  Home,
  Plus,
  Search,
  Filter,
  CheckCircle2,
  AlertCircle,
  Clock,
  Calendar,
  DollarSign,
  Receipt,
  Eye,
  Trash2,
  Edit2,
  FileUp,
  RefreshCw,
  Bell,
  ArrowRight,
  ShieldCheck,
  ChevronRight,
  Info,
  X,
} from 'lucide-react';
import { AppRow, UtilityRowData, UtilityType } from '../types';
import {
  inr,
  longD,
  todayIST,
  toDay,
  DAY,
  rollForward,
  uid,
} from '../utils/calculations';
import { PersonFilter } from '../components/PersonFilter';

interface Props {
  rows: AppRow[];
  selectedPerson: string;
  onSelectPerson: (person: string) => void;
  onAdd: () => void;
  onEdit: (row: AppRow) => void;
  onDelete: (id: string, name: string) => void;
  onUpdateRow: (row: AppRow) => void;
  onViewAttachment?: (attachmentName: string, title: string) => void;
}

export const UtilitiesView: React.FC<Props> = ({
  rows,
  selectedPerson,
  onSelectPerson,
  onAdd,
  onEdit,
  onDelete,
  onUpdateRow,
  onViewAttachment,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all'); // all, overdue, today, upcoming, partial, paid
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [paymentModalRow, setPaymentModalRow] = useState<AppRow | null>(null);
  const [paymentAmount, setPaymentAmount] = useState<string>('');
  const [paymentDate, setPaymentDate] = useState<string>(todayIST());
  const [paymentNotes, setPaymentNotes] = useState<string>('');
  const [notificationInfoOpen, setNotificationInfoOpen] = useState(false);

  // Extract utility rows (kind === 'util' OR kind === 'due' with category === 'utility')
  const utilityRows = useMemo(() => {
    return rows.filter((r) => {
      if (r.kind === 'util') return true;
      if (r.kind === 'due' && (r.data?.category === 'utility' || r.data?.category === 'lpg')) return true;
      return false;
    });
  }, [rows]);

  const today = todayIST();
  const todayMs = toDay(today);

  // Helper to get status of a utility bill
  const getUtilityStatus = (row: AppRow) => {
    const d = row.data as UtilityRowData;
    const dueDate = d.dueDate || d.due || '';
    const dueMs = toDay(dueDate);
    const diffDays = Math.round((dueMs - todayMs) / DAY);

    const isPaid = d.status === 'paid';
    const isPartial = d.status === 'partially_paid';

    if (isPaid) {
      return { status: 'paid', label: 'Paid in Full', color: 'emerald', days: 0 };
    }
    if (diffDays < 0) {
      return {
        status: isPartial ? 'partial_overdue' : 'overdue',
        label: isPartial ? `Partially Paid (${Math.abs(diffDays)}d Overdue)` : `${Math.abs(diffDays)} Days Overdue`,
        color: 'rose',
        days: diffDays,
      };
    }
    if (diffDays === 0) {
      return {
        status: isPartial ? 'partial_today' : 'today',
        label: isPartial ? 'Partially Paid (Due Today)' : 'Due Today',
        color: 'amber',
        days: 0,
      };
    }
    if (isPartial) {
      return {
        status: 'partial',
        label: `Partially Paid (Due in ${diffDays}d)`,
        color: 'blue',
        days: diffDays,
      };
    }
    return {
      status: 'upcoming',
      label: `Due in ${diffDays} Days`,
      color: 'slate',
      days: diffDays,
    };
  };

  // Filtered rows
  const filteredRows = useMemo(() => {
    return utilityRows.filter((r) => {
      const d = r.data || {};
      const holder = d.holder || d.property || '';
      if (selectedPerson && holder !== selectedPerson) {
        return false;
      }

      const info = getUtilityStatus(r);

      if (statusFilter === 'overdue' && !['overdue', 'partial_overdue'].includes(info.status)) return false;
      if (statusFilter === 'today' && !['today', 'partial_today'].includes(info.status)) return false;
      if (statusFilter === 'upcoming' && info.status !== 'upcoming') return false;
      if (statusFilter === 'partial' && !info.status.startsWith('partial')) return false;
      if (statusFilter === 'paid' && info.status !== 'paid') return false;

      const utilType = (d.utilityType || d.category || 'other').toLowerCase();
      if (typeFilter !== 'all' && utilType !== typeFilter) return false;

      if (searchTerm.trim()) {
        const q = searchTerm.toLowerCase();
        const match =
          (d.name || '').toLowerCase().includes(q) ||
          (d.provider || '').toLowerCase().includes(q) ||
          (d.accountNumber || d.ref || '').toLowerCase().includes(q) ||
          (d.holder || '').toLowerCase().includes(q) ||
          (d.property || '').toLowerCase().includes(q);
        if (!match) return false;
      }

      return true;
    });
  }, [utilityRows, selectedPerson, statusFilter, typeFilter, searchTerm, todayMs]);

  // Aggregate Metrics
  const metrics = useMemo(() => {
    let totalUnpaid = 0;
    let totalOverdue = 0;
    let overdueCount = 0;
    let dueTodayCount = 0;
    let upcomingCount = 0;
    let paidCount = 0;

    for (const r of utilityRows) {
      const d = r.data || {};
      const billAmount = Number(d.billAmount || d.amount) || 0;
      const outstanding =
        d.balanceOutstanding != null && d.balanceOutstanding !== ''
          ? Number(d.balanceOutstanding)
          : d.status === 'paid'
          ? 0
          : billAmount;

      const info = getUtilityStatus(r);

      if (info.status === 'paid') {
        paidCount++;
      } else {
        totalUnpaid += Math.max(0, outstanding);
        if (['overdue', 'partial_overdue'].includes(info.status)) {
          totalOverdue += Math.max(0, outstanding);
          overdueCount++;
        } else if (['today', 'partial_today'].includes(info.status)) {
          dueTodayCount++;
        } else {
          upcomingCount++;
        }
      }
    }

    return { totalUnpaid, totalOverdue, overdueCount, dueTodayCount, upcomingCount, paidCount };
  }, [utilityRows, todayMs]);

  // Icon mapping for utility types
  const getUtilityIcon = (type: string) => {
    switch ((type || '').toLowerCase()) {
      case 'electricity':
      case 'power':
        return <Zap className="w-4 h-4 text-amber-500" />;
      case 'water':
        return <Droplets className="w-4 h-4 text-cyan-500" />;
      case 'broadband':
      case 'wifi':
        return <Wifi className="w-4 h-4 text-indigo-500" />;
      case 'mobile':
      case 'landline':
        return <Phone className="w-4 h-4 text-emerald-500" />;
      case 'gas':
      case 'lpg':
      case 'piped_gas':
        return <Flame className="w-4 h-4 text-rose-500" />;
      case 'dth':
        return <Tv className="w-4 h-4 text-purple-500" />;
      default:
        return <Home className="w-4 h-4 text-[#0E7C86]" />;
    }
  };

  // Open Record Payment modal
  const handleOpenPayment = (row: AppRow) => {
    const d = row.data as UtilityRowData;
    const outstanding =
      d.balanceOutstanding != null && d.balanceOutstanding !== ''
        ? d.balanceOutstanding
        : d.billAmount || d.amount || 0;

    setPaymentModalRow(row);
    setPaymentAmount(String(outstanding));
    setPaymentDate(todayIST());
    setPaymentNotes('');
  };

  // Submit Payment
  const handleSubmitPayment = () => {
    if (!paymentModalRow) return;
    const d = paymentModalRow.data as UtilityRowData;
    const payAmt = Number(paymentAmount) || 0;
    const currentOutstanding =
      d.balanceOutstanding != null && d.balanceOutstanding !== ''
        ? Number(d.balanceOutstanding)
        : Number(d.billAmount || d.amount || 0);

    const newOutstanding = Math.max(0, currentOutstanding - payAmt);
    const isFullSettlement = newOutstanding <= 0;

    const newPaymentRecord = {
      id: uid(),
      date: paymentDate,
      amount: payAmt,
      notes: paymentNotes || (isFullSettlement ? 'Full bill settlement' : 'Partial payment'),
    };

    const existingHistory = Array.isArray(d.paymentHistory) ? d.paymentHistory : [];

    const updatedData: Record<string, any> = {
      ...d,
      paidAmount: (Number(d.paidAmount) || 0) + payAmt,
      balanceOutstanding: newOutstanding,
      lastPaymentDate: paymentDate,
      paymentHistory: [newPaymentRecord, ...existingHistory],
      status: isFullSettlement ? 'paid' : 'partially_paid',
    };

    onUpdateRow({
      ...paymentModalRow,
      data: updatedData,
    });

    setPaymentModalRow(null);
  };

  // Roll forward to next billing cycle
  const handleRollForward = (row: AppRow) => {
    const updated = rollForward(row.data, todayIST());
    onUpdateRow({
      ...row,
      data: updated,
    });
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white tracking-tight">
              Utilities &amp; Household Bills
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-teal-100 dark:bg-teal-950 text-teal-800 dark:text-teal-300 border border-teal-200 dark:border-teal-800">
              {utilityRows.length} Bills
            </span>
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            Track electricity, water, broadband, gas, and household dues. Calculate in IST with configurable reminders.
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={() => setNotificationInfoOpen(!notificationInfoOpen)}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 transition"
            title="Notification alert delivery settings"
          >
            <Bell className="w-3.5 h-3.5 text-[#0E7C86] dark:text-[#3CB7C2]" />
            <span>Reminder Rules</span>
          </button>

          <button
            onClick={onAdd}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold bg-[#0E7C86] hover:bg-[#128e9a] text-white transition shadow-sm cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>Add Utility Bill</span>
          </button>
        </div>
      </div>

      {/* Notification Transparency Banner */}
      {notificationInfoOpen && (
        <div className="p-4 rounded-2xl bg-blue-50/80 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-800 text-xs text-blue-950 dark:text-blue-200 space-y-2 animate-in fade-in">
          <div className="flex items-center gap-2 font-bold text-blue-900 dark:text-blue-300">
            <Info className="w-4 h-4 text-blue-600 dark:text-blue-400" />
            <span>Notification &amp; Reminder Transparency (Indian Standard Time)</span>
          </div>
          <p>
            <strong>In-App Alerts:</strong> Calculated continuously using IST. Visual badges highlight bills at <strong>7 days before</strong>, <strong>3 days before</strong>, <strong>on the due date</strong>, and <strong>daily when overdue</strong>.
          </p>
          <p>
            <strong>Background Notifications:</strong> Standalone web browsers and PWAs deliver background notifications only when browser notification permissions are explicitly granted and the PWA service worker is active. Paisa Pal never falsely claims that undelivered external notifications were sent.
          </p>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <div className="p-4 rounded-2xl bg-white dark:bg-[#0F1B2D] border border-gray-200 dark:border-gray-800 shadow-2xs">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
            Total Outstanding
          </div>
          <div className="text-xl sm:text-2xl font-black text-gray-900 dark:text-white mt-1">
            {inr(metrics.totalUnpaid)}
          </div>
          <div className="text-[11px] text-gray-500 mt-1">
            Across {utilityRows.length - metrics.paidCount} unsettled bills
          </div>
        </div>

        <div className="p-4 rounded-2xl bg-rose-50/60 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-900 shadow-2xs">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-rose-700 dark:text-rose-400">
            Overdue Amount
          </div>
          <div className="text-xl sm:text-2xl font-black text-rose-700 dark:text-rose-300 mt-1">
            {inr(metrics.totalOverdue)}
          </div>
          <div className="text-[11px] text-rose-600 dark:text-rose-400 font-semibold mt-1">
            {metrics.overdueCount} bills past due date ⚠
          </div>
        </div>

        <div className="p-4 rounded-2xl bg-amber-50/60 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-900 shadow-2xs">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-amber-800 dark:text-amber-400">
            Due Today / Soon
          </div>
          <div className="text-xl sm:text-2xl font-black text-amber-800 dark:text-amber-300 mt-1">
            {metrics.dueTodayCount + metrics.upcomingCount} Bills
          </div>
          <div className="text-[11px] text-amber-700 dark:text-amber-400 mt-1">
            {metrics.dueTodayCount} due today · {metrics.upcomingCount} coming up
          </div>
        </div>

        <div className="p-4 rounded-2xl bg-emerald-50/60 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-900 shadow-2xs">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-emerald-800 dark:text-emerald-400">
            Settled / Paid
          </div>
          <div className="text-xl sm:text-2xl font-black text-emerald-800 dark:text-emerald-300 mt-1">
            {metrics.paidCount}
          </div>
          <div className="text-[11px] text-emerald-700 dark:text-emerald-400 mt-1">
            Zero outstanding balance
          </div>
        </div>
      </div>

      <PersonFilter
        rows={rows}
        selectedPerson={selectedPerson}
        onSelectPerson={onSelectPerson}
      />

      {/* Filter & Search Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-white dark:bg-[#0F1B2D] p-3 rounded-2xl border border-gray-200 dark:border-gray-800 shadow-2xs">
        <div className="relative flex-1">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search by provider, consumer #, property, holder..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 rounded-xl text-xs bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-[#0E7C86]"
          />
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-1.5 rounded-xl text-xs bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 font-medium"
          >
            <option value="all">All Statuses</option>
            <option value="overdue">Overdue Bills</option>
            <option value="today">Due Today</option>
            <option value="upcoming">Upcoming</option>
            <option value="partial">Partially Paid</option>
            <option value="paid">Settled / Paid</option>
          </select>

          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="px-3 py-1.5 rounded-xl text-xs bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 font-medium"
          >
            <option value="all">All Utilities</option>
            <option value="electricity">Electricity</option>
            <option value="water">Water</option>
            <option value="broadband">Broadband / WiFi</option>
            <option value="mobile">Mobile / Phone</option>
            <option value="gas">Piped Gas / LPG</option>
            <option value="dth">DTH / TV</option>
          </select>
        </div>
      </div>

      {/* Bills List */}
      <div className="space-y-3">
        {filteredRows.length === 0 ? (
          <div className="p-12 text-center bg-white dark:bg-[#0F1B2D] border border-dashed border-gray-200 dark:border-gray-800 rounded-3xl">
            <Zap className="w-8 h-8 text-gray-300 dark:text-gray-600 mx-auto mb-2" />
            <p className="text-sm font-semibold text-gray-600 dark:text-gray-400">
              No utility bills found matching the current filters.
            </p>
            <p className="text-xs text-gray-400 mt-1">
              Add a new recurring bill or adjust your status/person filter.
            </p>
          </div>
        ) : (
          filteredRows.map((row) => {
            const d = row.data as UtilityRowData;
            const info = getUtilityStatus(row);
            const billAmount = Number(d.billAmount || d.amount) || 0;
            const outstanding =
              d.balanceOutstanding != null && d.balanceOutstanding !== ''
                ? Number(d.balanceOutstanding)
                : d.status === 'paid'
                ? 0
                : billAmount;

            const isPaid = d.status === 'paid';
            const isPartial = d.status === 'partially_paid';
            const dueDate = d.dueDate || d.due || '';

            return (
              <div
                key={row.id}
                className="p-4 sm:p-5 rounded-2xl bg-white dark:bg-[#0F1B2D] border border-gray-200 dark:border-gray-800 hover:border-[#0E7C86]/40 transition shadow-2xs flex flex-col md:flex-row items-start md:items-center justify-between gap-4"
              >
                {/* Left: Info */}
                <div className="flex items-start gap-3.5 flex-1 min-w-0">
                  <div className="w-10 h-10 rounded-xl bg-gray-100 dark:bg-gray-800 flex items-center justify-center flex-shrink-0">
                    {getUtilityIcon(d.utilityType || d.category || '')}
                  </div>

                  <div className="space-y-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="font-bold text-sm sm:text-base text-gray-900 dark:text-white truncate">
                        {d.name || d.provider || 'Utility Bill'}
                      </h3>
                      {/* Status Badge */}
                      <span
                        className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                          info.color === 'rose'
                            ? 'bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300 border border-rose-300 dark:border-rose-800'
                            : info.color === 'amber'
                            ? 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300 border border-amber-300 dark:border-amber-800'
                            : info.color === 'blue'
                            ? 'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300 border border-blue-300 dark:border-blue-800'
                            : info.color === 'emerald'
                            ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800'
                            : 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300'
                        }`}
                      >
                        {info.label}
                      </span>
                    </div>

                    <div className="flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400 flex-wrap">
                      {d.accountNumber && (
                        <span>
                          Account / Consumer: <strong className="font-mono text-gray-700 dark:text-gray-200">{d.accountNumber}</strong>
                        </span>
                      )}
                      <span>·</span>
                      <span>
                        Person: <strong className="text-gray-700 dark:text-gray-200">{d.holder || 'Family'}</strong>
                      </span>
                      {d.property && (
                        <>
                          <span>·</span>
                          <span>Property: {d.property}</span>
                        </>
                      )}
                      {d.billingPeriod && (
                        <>
                          <span>·</span>
                          <span>Period: {d.billingPeriod}</span>
                        </>
                      )}
                    </div>

                    {d.notes && (
                      <p className="text-[11px] text-gray-400 dark:text-gray-500 line-clamp-1">
                        {d.notes}
                      </p>
                    )}
                  </div>
                </div>

                {/* Right: Amounts & Actions */}
                <div className="flex items-center justify-between md:justify-end gap-5 w-full md:w-auto pt-3 md:pt-0 border-t md:border-t-0 border-gray-100 dark:border-gray-800">
                  <div className="text-left md:text-right">
                    <div className="text-xs text-gray-400 font-medium">
                      Due: {dueDate ? longD(dueDate) : '—'}
                    </div>
                    <div className="text-base sm:text-lg font-black text-gray-900 dark:text-white">
                      {isPaid ? (
                        <span className="text-emerald-600 dark:text-emerald-400 font-bold">Paid ({inr(billAmount)})</span>
                      ) : isPartial ? (
                        <div>
                          <span className="text-rose-600 dark:text-rose-400">{inr(outstanding)} bal</span>
                          <span className="text-xs text-gray-400 block font-normal">of {inr(billAmount)} bill</span>
                        </div>
                      ) : (
                        <span>{inr(billAmount)}</span>
                      )}
                    </div>
                  </div>

                  {/* Action Buttons */}
                  <div className="flex items-center gap-1.5">
                    {!isPaid && (
                      <button
                        onClick={() => handleOpenPayment(row)}
                        className="px-3 py-1.5 rounded-xl text-xs font-bold bg-[#0E7C86] hover:bg-[#128e9a] text-white transition shadow-2xs"
                        title="Record full or partial payment"
                      >
                        Record Payment
                      </button>
                    )}

                    {isPaid && d.freq && d.freq !== 'once' && (
                      <button
                        onClick={() => handleRollForward(row)}
                        className="flex items-center gap-1 px-3 py-1.5 rounded-xl text-xs font-semibold bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 transition"
                        title="Roll forward to next billing cycle"
                      >
                        <RefreshCw className="w-3.5 h-3.5 text-[#0E7C86]" />
                        <span>Next Cycle</span>
                      </button>
                    )}

                    {d.attachmentName && onViewAttachment && (
                      <button
                        onClick={() => onViewAttachment(d.attachmentName!, d.name)}
                        className="p-2 rounded-xl text-gray-400 hover:text-teal-600 hover:bg-gray-100 dark:hover:bg-gray-800 transition"
                        title="View bill receipt attachment"
                      >
                        <Receipt className="w-4 h-4" />
                      </button>
                    )}

                    <button
                      onClick={() => onEdit(row)}
                      className="p-2 rounded-xl text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 transition"
                      title="Edit bill details"
                    >
                      <Edit2 className="w-4 h-4" />
                    </button>

                    <button
                      onClick={() => onDelete(row.id, d.name || 'Utility Bill')}
                      className="p-2 rounded-xl text-gray-400 hover:text-rose-600 hover:bg-gray-100 dark:hover:bg-gray-800 transition"
                      title="Delete bill"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Record Payment Modal */}
      {paymentModalRow && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs"
        >
          <div className="bg-white dark:bg-[#0F1B2D] border border-gray-200 dark:border-gray-800 rounded-3xl p-6 w-full max-w-md shadow-2xl space-y-4 animate-in fade-in zoom-in-95">
            <div className="flex items-center justify-between border-b border-gray-100 dark:border-gray-800 pb-3">
              <h3 className="text-base font-bold text-gray-900 dark:text-white">
                Record Bill Payment
              </h3>
              <button
                onClick={() => setPaymentModalRow(null)}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="text-gray-500 font-semibold block mb-1">Bill Name</label>
                <div className="font-bold text-gray-800 dark:text-gray-200">
                  {paymentModalRow.data?.name || paymentModalRow.data?.provider}
                </div>
              </div>

              <div>
                <label className="text-gray-500 font-semibold block mb-1">
                  Amount Paying (₹)
                </label>
                <input
                  type="number"
                  value={paymentAmount}
                  onChange={(e) => setPaymentAmount(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-gray-50 dark:bg-gray-800 border border-gray-300 dark:border-gray-700 text-gray-900 dark:text-white font-bold text-sm"
                  placeholder="Enter amount paid"
                />
                <span className="text-[11px] text-gray-400 mt-1 block">
                  Paying less than total outstanding will mark this bill as <strong>Partially Paid</strong>.
                </span>
              </div>

              <div>
                <label className="text-gray-500 font-semibold block mb-1">
                  Payment Date (IST)
                </label>
                <input
                  type="date"
                  value={paymentDate}
                  onChange={(e) => setPaymentDate(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-gray-50 dark:bg-gray-800 border border-gray-300 dark:border-gray-700 text-gray-900 dark:text-white text-xs"
                />
              </div>

              <div>
                <label className="text-gray-500 font-semibold block mb-1">
                  Payment Reference / Transaction ID / Notes
                </label>
                <input
                  type="text"
                  value={paymentNotes}
                  onChange={(e) => setPaymentNotes(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-gray-50 dark:bg-gray-800 border border-gray-300 dark:border-gray-700 text-gray-900 dark:text-white text-xs"
                  placeholder="e.g. UPI Ref 4029104928"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-gray-100 dark:border-gray-800">
              <button
                onClick={() => setPaymentModalRow(null)}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-gray-600 dark:text-gray-400 hover:bg-gray-100"
              >
                Cancel
              </button>
              <button
                onClick={handleSubmitPayment}
                className="px-5 py-2 rounded-xl text-xs font-bold bg-[#0E7C86] hover:bg-[#128e9a] text-white transition shadow-sm"
              >
                Save Payment
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
