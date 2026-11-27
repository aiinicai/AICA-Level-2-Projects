import React, { useState, useMemo } from 'react';
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer
} from 'recharts';
import {
  Calendar,
  PieChart as PieIcon,
  BarChart3,
  TrendingUp,
  ShoppingBag,
  Utensils,
  Fuel,
  Stethoscope,
  Shirt,
  Home,
  Zap,
  Smartphone,
  Car,
  Plane,
  GraduationCap,
  Sparkles,
  HelpCircle,
  Banknote,
  Filter
} from 'lucide-react';
import { ExpenseCategory, Transaction } from '../types/finance';

interface DashboardChartsProps {
  transactions: Transaction[];
  onSelectCategory?: (category: ExpenseCategory) => void;
}

type TimePeriod = 'DAILY' | 'WEEKLY' | 'MONTHLY' | 'YEAR';
type ChartType = 'donut' | 'bar' | 'line';

// Curated modern palette matching the high-contrast screenshot
const CATEGORY_COLORS: Record<string, string> = {
  'Food & Groceries': '#ef4444', // Coral / Red
  Food: '#ef4444',
  Groceries: '#f97316',
  Restaurant: '#ef4444',
  Salary: '#2563eb', // Royal Blue
  Healthcare: '#10b981', // Emerald / Mint Teal
  Medicine: '#10b981',
  Fuel: '#8b5cf6', // Violet / Purple
  Petrol: '#8b5cf6',
  Clothing: '#f59e0b', // Amber / Gold
  Shopping: '#f59e0b',
  Transport: '#06b6d4', // Cyan
  'Rent & Housing': '#64748b',
  Utilities: '#3b82f6',
  Telecom: '#a855f7',
  Entertainment: '#ec4899',
  Travel: '#14b8a6',
  Education: '#84cc16',
  Other: '#94a3b8'
};

const CATEGORY_ICONS: Record<string, React.ReactNode> = {
  'Food & Groceries': <Utensils className="w-5 h-5" />,
  Food: <Utensils className="w-5 h-5" />,
  Groceries: <ShoppingBag className="w-5 h-5" />,
  Restaurant: <Utensils className="w-5 h-5" />,
  Salary: <Banknote className="w-5 h-5" />,
  Healthcare: <Stethoscope className="w-5 h-5" />,
  Medicine: <Stethoscope className="w-5 h-5" />,
  Fuel: <Fuel className="w-5 h-5" />,
  Petrol: <Fuel className="w-5 h-5" />,
  Clothing: <Shirt className="w-5 h-5" />,
  Shopping: <Shirt className="w-5 h-5" />,
  Transport: <Car className="w-5 h-5" />,
  'Rent & Housing': <Home className="w-5 h-5" />,
  Utilities: <Zap className="w-5 h-5" />,
  Telecom: <Smartphone className="w-5 h-5" />,
  Entertainment: <Sparkles className="w-5 h-5" />,
  Travel: <Plane className="w-5 h-5" />,
  Education: <GraduationCap className="w-5 h-5" />,
  Other: <HelpCircle className="w-5 h-5" />
};

export const DashboardCharts: React.FC<DashboardChartsProps> = ({
  transactions,
  onSelectCategory
}) => {
  const [period, setPeriod] = useState<TimePeriod>('MONTHLY');
  const [chartType, setChartType] = useState<ChartType>('donut');
  const [activeSliceIndex, setActiveSliceIndex] = useState<number | null>(null);
  const [selectedDayOffset, setSelectedDayOffset] = useState<number>(0);

  // Generate 7-day selector dates around today (matching screenshot top date picker)
  const datePickerDays = useMemo(() => {
    const list = [];
    const today = new Date();
    for (let i = -3; i <= 3; i++) {
      const d = new Date(today);
      d.setDate(today.getDate() + i);
      list.push({
        offset: i,
        dayNum: d.getDate(),
        monthShort: d.toLocaleString('en-US', { month: 'short' }),
        weekdayShort: d.toLocaleString('en-US', { weekday: 'short' }),
        fullDateStr: d.toISOString().split('T')[0]
      });
    }
    return list;
  }, []);

  // Filter transactions according to selected period
  const filteredTransactions = useMemo(() => {
    const now = new Date();

    return transactions.filter(tx => {
      const txDate = new Date(tx.date);

      if (period === 'DAILY') {
        const selectedDay = datePickerDays.find(d => d.offset === selectedDayOffset);
        if (!selectedDay) return true;
        const txIso = txDate.toISOString().split('T')[0];
        return txIso === selectedDay.fullDateStr;
      }

      if (period === 'WEEKLY') {
        const diffMs = now.getTime() - txDate.getTime();
        const diffDays = diffMs / (1000 * 60 * 60 * 24);
        return diffDays >= 0 && diffDays <= 7;
      }

      if (period === 'MONTHLY') {
        return (
          txDate.getMonth() === now.getMonth() &&
          txDate.getFullYear() === now.getFullYear()
        );
      }

      if (period === 'YEAR') {
        return txDate.getFullYear() === now.getFullYear();
      }

      return true;
    });
  }, [transactions, period, selectedDayOffset, datePickerDays]);

  // Aggregate category metrics strictly for expenses
  const categoryData = useMemo(() => {
    const map: Record<string, { total: number; count: number; category: string }> = {};

    filteredTransactions.forEach(tx => {
      // Strictly include ONLY expense transactions (never transfers, deposits, or card payments)
      if (tx.type === 'expense') {
        if (tx.categorySplits && tx.categorySplits.length > 0) {
          for (const split of tx.categorySplits) {
            const cat = split.category || 'Other';
            if (!map[cat]) {
              map[cat] = { total: 0, count: 0, category: cat };
            }
            map[cat].total += split.amount;
            map[cat].count += 1;
          }
        } else {
          const cat = tx.category || 'Other';
          if (!map[cat]) {
            map[cat] = { total: 0, count: 0, category: cat };
          }
          map[cat].total += tx.amount;
          map[cat].count += 1;
        }
      }
    });

    const list = Object.values(map).sort((a, b) => b.total - a.total);
    return list;
  }, [filteredTransactions]);

  const totalPeriodAmount = useMemo(() => {
    return categoryData.reduce((sum, item) => sum + item.total, 0);
  }, [categoryData]);

  // Daily timeline data for Bar and Area charts
  const timelineData = useMemo(() => {
    const dayMap: Record<string, { label: string; expense: number; income: number }> = {};

    // Group transactions by day
    filteredTransactions.forEach(tx => {
      const d = new Date(tx.date);
      const key = `${d.getDate()} ${d.toLocaleString('en-US', { month: 'short' })}`;
      if (!dayMap[key]) {
        dayMap[key] = { label: key, expense: 0, income: 0 };
      }
      if (tx.type === 'expense') {
        dayMap[key].expense += tx.amount;
      } else if (tx.type === 'income') {
        dayMap[key].income += tx.amount;
      }
    });

    const entries = Object.values(dayMap);
    if (entries.length === 0) {
      return [
        { label: 'Week 1', expense: 0, income: 0 },
        { label: 'Week 2', expense: 0, income: 0 },
        { label: 'Week 3', expense: 0, income: 0 },
        { label: 'Week 4', expense: 0, income: 0 }
      ];
    }
    return entries.slice(-10);
  }, [filteredTransactions]);

  const currentMonthYear = useMemo(() => {
    const d = new Date();
    return d.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
  }, []);

  return (
    <div className="bg-gradient-to-b from-slate-900 via-slate-900 to-slate-950 border border-slate-800 rounded-3xl p-4 sm:p-6 shadow-2xl space-y-5">
      {/* Top Header: Billing Reports Title & Period Picker */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800/80">
        <div className="flex items-center justify-between sm:justify-start gap-3">
          <div className="flex items-center gap-2.5">
            <div className="w-10 h-10 rounded-2xl bg-teal-500/20 text-teal-400 border border-teal-500/30 flex items-center justify-center font-bold">
              <PieIcon className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base sm:text-lg font-bold text-white tracking-tight">
                Billing Reports &amp; Analytics
              </h2>
              <p className="text-xs text-slate-400 font-medium">Interactive Financial Allocation</p>
            </div>
          </div>
        </div>

        {/* Date / Month Indicator & Chart Type Switcher */}
        <div className="flex items-center justify-between sm:justify-end gap-2">
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-950/80 border border-slate-800 text-xs text-slate-300">
            <Calendar className="w-3.5 h-3.5 text-teal-400" />
            <span className="font-semibold">{currentMonthYear}</span>
          </div>

          {/* Chart View Switcher */}
          <div className="flex items-center bg-slate-950 p-1 rounded-xl border border-slate-800">
            <button
              type="button"
              onClick={() => setChartType('donut')}
              className={`p-1.5 rounded-lg transition cursor-pointer ${
                chartType === 'donut'
                  ? 'bg-teal-500 text-slate-950 font-bold shadow'
                  : 'text-slate-400 hover:text-white'
              }`}
              title="Donut Allocation Chart"
            >
              <PieIcon className="w-4 h-4" />
            </button>
            <button
              type="button"
              onClick={() => setChartType('bar')}
              className={`p-1.5 rounded-lg transition cursor-pointer ${
                chartType === 'bar'
                  ? 'bg-teal-500 text-slate-950 font-bold shadow'
                  : 'text-slate-400 hover:text-white'
              }`}
              title="Bar Comparison Chart"
            >
              <BarChart3 className="w-4 h-4" />
            </button>
            <button
              type="button"
              onClick={() => setChartType('line')}
              className={`p-1.5 rounded-lg transition cursor-pointer ${
                chartType === 'line'
                  ? 'bg-teal-500 text-slate-950 font-bold shadow'
                  : 'text-slate-400 hover:text-white'
              }`}
              title="Trajectory Trend Chart"
            >
              <TrendingUp className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Top 7-Day Date Selector Strip (Matching Screenshot Top Carousel) */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-none">
        {datePickerDays.map(item => {
          const isSelected = selectedDayOffset === item.offset;
          return (
            <button
              key={item.offset}
              type="button"
              onClick={() => {
                setSelectedDayOffset(item.offset);
                setPeriod('DAILY');
              }}
              className={`flex-1 min-w-[58px] py-2 px-1.5 rounded-2xl flex flex-col items-center transition cursor-pointer border ${
                isSelected && period === 'DAILY'
                  ? 'bg-rose-500 border-rose-400 text-white shadow-lg shadow-rose-500/30'
                  : 'bg-slate-950/70 border-slate-800/80 text-slate-400 hover:bg-slate-850 hover:text-white'
              }`}
            >
              <span className="text-[10px] uppercase font-bold tracking-wider opacity-80">
                {item.monthShort}
              </span>
              <span className="text-base font-black tracking-tight leading-none my-0.5">
                {item.dayNum}
              </span>
              <span className="text-[10px] font-semibold opacity-75">{item.weekdayShort}</span>
            </button>
          );
        })}
      </div>

      {/* Time Filter Tabs: DAILY, WEEKLY, MONTHLY, YEAR (Matching Screenshot Tab Navigation) */}
      <div className="flex items-center justify-between border-b border-slate-800/80 pb-2">
        <div className="text-xs font-bold text-slate-300">
          <span>Billing Reports</span>
        </div>
        <div className="flex items-center gap-1 sm:gap-2">
          {(['DAILY', 'WEEKLY', 'MONTHLY', 'YEAR'] as TimePeriod[]).map(p => {
            const isActive = period === p;
            return (
              <button
                key={p}
                type="button"
                onClick={() => setPeriod(p)}
                className={`px-3 py-1 text-xs font-bold transition-all relative cursor-pointer ${
                  isActive
                    ? 'text-white'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <span>{p}</span>
                {isActive && (
                  <span className="absolute bottom-[-9px] left-0 right-0 h-0.5 bg-rose-500 rounded-full" />
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Main Chart Canvas Area */}
      <div className="py-2">
        {chartType === 'donut' && (
          <div className="relative flex flex-col items-center justify-center pt-2 pb-4">
            {/* 3D Ambient Backdrop Glow & Elevated Ring Platter */}
            <div className="relative w-full h-72 sm:h-80 flex items-center justify-center">
              {/* Outer atmospheric neon pulse */}
              <div className="absolute w-64 h-64 sm:w-72 sm:h-72 rounded-full bg-gradient-to-tr from-rose-500/15 via-teal-500/15 to-indigo-500/20 blur-3xl pointer-events-none animate-pulse" />

              {/* 3D Recessed Dark Platter Base */}
              <div className="absolute w-60 h-60 sm:w-68 sm:h-68 rounded-full border border-slate-700/60 bg-gradient-to-b from-slate-900/90 via-slate-950 to-[#030712] shadow-[inset_0_4px_16px_rgba(0,0,0,0.9),0_20px_35px_-8px_rgba(0,0,0,0.8)] pointer-events-none flex items-center justify-center">
                {/* Secondary Inset Bevel Ring */}
                <div className="w-52 h-52 sm:w-60 sm:h-60 rounded-full border border-slate-800/80 shadow-[inset_0_2px_8px_rgba(0,0,0,0.8)]" />
              </div>

              {/* Responsive SVG Pie Canvas */}
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <defs>
                    {/* 3D Volumetric Drop Shadow for Slices */}
                    <filter id="donut3dShadow" x="-20%" y="-20%" width="150%" height="150%">
                      <feDropShadow dx="0" dy="12" stdDeviation="8" floodColor="#000000" floodOpacity="0.8" />
                      <feDropShadow dx="0" dy="4" stdDeviation="3" floodColor="#000000" floodOpacity="0.5" />
                    </filter>

                    {/* Gradient Definitions for Categories */}
                    <linearGradient id="grad-Food" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor="#ff6b6b" />
                      <stop offset="60%" stopColor="#ef4444" />
                      <stop offset="100%" stopColor="#991b1b" />
                    </linearGradient>
                    <linearGradient id="grad-Food & Groceries" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor="#ff6b6b" />
                      <stop offset="60%" stopColor="#ef4444" />
                      <stop offset="100%" stopColor="#991b1b" />
                    </linearGradient>
                    <linearGradient id="grad-Groceries" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor="#fb923c" />
                      <stop offset="60%" stopColor="#f97316" />
                      <stop offset="100%" stopColor="#c2410c" />
                    </linearGradient>
                    <linearGradient id="grad-Restaurant" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor="#ff5252" />
                      <stop offset="60%" stopColor="#dc2626" />
                      <stop offset="100%" stopColor="#7f1d1d" />
                    </linearGradient>
                    <linearGradient id="grad-Salary" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor="#60a5fa" />
                      <stop offset="60%" stopColor="#2563eb" />
                      <stop offset="100%" stopColor="#1e3a8a" />
                    </linearGradient>
                    <linearGradient id="grad-Healthcare" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor="#34d399" />
                      <stop offset="60%" stopColor="#10b981" />
                      <stop offset="100%" stopColor="#047857" />
                    </linearGradient>
                    <linearGradient id="grad-Medicine" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor="#34d399" />
                      <stop offset="60%" stopColor="#10b981" />
                      <stop offset="100%" stopColor="#047857" />
                    </linearGradient>
                    <linearGradient id="grad-Fuel" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor="#c084fc" />
                      <stop offset="60%" stopColor="#8b5cf6" />
                      <stop offset="100%" stopColor="#5b21b6" />
                    </linearGradient>
                    <linearGradient id="grad-Petrol" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor="#c084fc" />
                      <stop offset="60%" stopColor="#8b5cf6" />
                      <stop offset="100%" stopColor="#5b21b6" />
                    </linearGradient>
                    <linearGradient id="grad-Clothing" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor="#fde047" />
                      <stop offset="60%" stopColor="#f59e0b" />
                      <stop offset="100%" stopColor="#b45309" />
                    </linearGradient>
                    <linearGradient id="grad-Shopping" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor="#fde047" />
                      <stop offset="60%" stopColor="#f59e0b" />
                      <stop offset="100%" stopColor="#b45309" />
                    </linearGradient>
                    <linearGradient id="grad-Transport" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor="#22d3ee" />
                      <stop offset="60%" stopColor="#06b6d4" />
                      <stop offset="100%" stopColor="#0e7490" />
                    </linearGradient>
                    <linearGradient id="grad-Utilities" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor="#93c5fd" />
                      <stop offset="60%" stopColor="#3b82f6" />
                      <stop offset="100%" stopColor="#1d4ed8" />
                    </linearGradient>
                    <linearGradient id="grad-Telecom" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor="#e879f9" />
                      <stop offset="60%" stopColor="#c026d3" />
                      <stop offset="100%" stopColor="#86198f" />
                    </linearGradient>
                    <linearGradient id="grad-Entertainment" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor="#f472b6" />
                      <stop offset="60%" stopColor="#db2777" />
                      <stop offset="100%" stopColor="#9d174d" />
                    </linearGradient>
                    <linearGradient id="grad-Travel" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor="#2dd4bf" />
                      <stop offset="60%" stopColor="#0d9488" />
                      <stop offset="100%" stopColor="#115e59" />
                    </linearGradient>
                    <linearGradient id="grad-default" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor="#94a3b8" />
                      <stop offset="60%" stopColor="#64748b" />
                      <stop offset="100%" stopColor="#334155" />
                    </linearGradient>
                  </defs>


                  <Pie
                    data={categoryData.length > 0 ? categoryData : [{ category: 'No Expenses', total: 1, count: 0 }]}
                    dataKey="total"
                    nameKey="category"
                    cx="50%"
                    cy="50%"
                    innerRadius={76}
                    outerRadius={114}
                    paddingAngle={3}
                    cornerRadius={6}
                    onMouseEnter={(_, index) => setActiveSliceIndex(index)}
                    onMouseLeave={() => setActiveSliceIndex(null)}
                    onClick={(entry: any) => {
                      const category = entry?.category || entry?.payload?.category;
                      if (onSelectCategory && category && category !== 'No Expenses') {
                        onSelectCategory(category as ExpenseCategory);
                      }
                    }}
                  >
                    {categoryData.length > 0 ? (
                      categoryData.map((entry, index) => {
                        const isHovered = activeSliceIndex === index;
                        const gradId = `url(#grad-${entry.category})` || 'url(#grad-default)';
                        const baseColor = CATEGORY_COLORS[entry.category] || '#06b6d4';
                        return (
                          <Cell
                            key={`cell-${entry.category}-${index}`}
                            fill={gradId}
                            stroke={isHovered ? '#ffffff' : '#090d16'}
                            strokeWidth={isHovered ? 2.5 : 1.5}
                            filter="url(#donut3dShadow)"
                            className="transition-all duration-300 cursor-pointer outline-none"
                            style={{
                              transform: isHovered ? 'scale(1.05)' : 'scale(1)',
                              transformOrigin: 'center center',
                              filter: isHovered ? `drop-shadow(0 0 10px ${baseColor})` : 'url(#donut3dShadow)'
                            }}
                          />
                        );
                      })
                    ) : (
                      <Cell fill="url(#grad-default)" />
                    )}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>

              {/* Floating 3D Specular Center Core (High-Depth Cylinder) */}
              <div className="absolute w-36 h-36 sm:w-42 sm:h-42 rounded-full flex flex-col items-center justify-center pointer-events-none bg-gradient-to-b from-slate-800/95 via-slate-900/98 to-[#020617] border border-white/15 shadow-[0_18px_36px_-6px_rgba(0,0,0,0.95),inset_0_2px_5px_rgba(255,255,255,0.25),inset_0_-4px_8px_rgba(0,0,0,0.85)] backdrop-blur-xl z-10 transition-transform duration-300">
                {/* 3D Curved Light Reflection Arc */}
                <div className="absolute top-1.5 w-24 h-10 rounded-full bg-gradient-to-b from-white/20 to-transparent blur-[1px] pointer-events-none" />

                <span className="text-[10px] font-black uppercase tracking-widest text-slate-400 flex items-center gap-1.5 mb-0.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-teal-400 animate-ping shadow-[0_0_8px_#2dd4bf]" />
                  Total Spent
                </span>
                <span className="text-2xl sm:text-3xl font-black text-white tabular-nums tracking-tight drop-shadow-[0_4px_12px_rgba(0,0,0,0.9)]">
                  AED {totalPeriodAmount.toLocaleString('en-AE', { minimumFractionDigits: 0 })}
                </span>
                <span className="text-[10px] font-bold text-teal-300 bg-teal-500/20 border border-teal-500/40 px-2.5 py-0.5 rounded-full mt-1.5 shadow-sm">
                  {categoryData.length} {categoryData.length === 1 ? 'Category' : 'Categories'}
                </span>
              </div>
            </div>
          </div>
        )}

        {chartType === 'bar' && (
          <div className="w-full h-64 sm:h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={timelineData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <XAxis dataKey="label" stroke="#64748b" fontSize={11} tickLine={false} />
                <YAxis stroke="#64748b" fontSize={11} tickLine={false} />
                <Tooltip
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      const data = payload[0].payload;
                      return (
                        <div className="bg-slate-900 border border-slate-700 rounded-xl p-3 shadow-xl">
                          <p className="text-xs font-bold text-white mb-1">{data.label}</p>
                          <p className="text-xs text-rose-400 font-bold tabular-nums">
                            Expenses: AED {data.expense.toLocaleString()}
                          </p>
                          {data.income > 0 && (
                            <p className="text-xs text-emerald-400 font-bold tabular-nums">
                              Income: AED {data.income.toLocaleString()}
                            </p>
                          )}
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                <Bar dataKey="expense" fill="#ef4444" radius={[6, 6, 0, 0]} />
                <Bar dataKey="income" fill="#2563eb" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {chartType === 'line' && (
          <div className="w-full h-64 sm:h-72">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={timelineData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="expenseGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#14b8a6" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#14b8a6" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="label" stroke="#64748b" fontSize={11} tickLine={false} />
                <YAxis stroke="#64748b" fontSize={11} tickLine={false} />
                <Tooltip
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      const data = payload[0].payload;
                      return (
                        <div className="bg-slate-900 border border-slate-700 rounded-xl p-3 shadow-xl">
                          <p className="text-xs font-bold text-white mb-1">{data.label}</p>
                          <p className="text-xs text-teal-400 font-bold tabular-nums">
                            Spend: AED {data.expense.toLocaleString()}
                          </p>
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="expense"
                  stroke="#14b8a6"
                  strokeWidth={3}
                  fillOpacity={1}
                  fill="url(#expenseGradient)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Category Breakdown Cards List (Exact layout of screenshot bottom list) */}
      <div className="space-y-2.5 pt-2 border-t border-slate-800/80">
        <div className="flex items-center justify-between text-xs text-slate-400 font-semibold px-1">
          <span>Category Breakdown</span>
          <span>{categoryData.length} Active Categories</span>
        </div>

        {categoryData.length > 0 ? (
          categoryData.map(item => {
            const color = CATEGORY_COLORS[item.category] || '#06b6d4';
            const icon = CATEGORY_ICONS[item.category] || <Banknote className="w-5 h-5" />;

            return (
              <div
                key={item.category}
                onClick={() => onSelectCategory && onSelectCategory(item.category as ExpenseCategory)}
                className="p-3.5 rounded-2xl bg-slate-950/80 border border-slate-800/80 hover:border-slate-700 flex items-center justify-between gap-3 transition cursor-pointer hover:bg-slate-900/90 shadow-sm"
              >
                {/* Left Icon Box with category-specific icon */}
                <div className="flex items-center gap-3 min-w-0">
                  <div
                    className="w-11 h-11 rounded-2xl flex items-center justify-center shrink-0 shadow-md"
                    style={{
                      backgroundColor: `${color}25`,
                      color: color,
                      border: `1px solid ${color}40`
                    }}
                  >
                    {icon}
                  </div>
                  <div className="min-w-0">
                    <p className="font-bold text-white text-sm truncate">{item.category}</p>
                    <p className="text-[11px] text-slate-400">
                      {item.count} transaction{item.count !== 1 ? 's' : ''}
                    </p>
                  </div>
                </div>

                {/* Right Amount Display (Tabular AED formatted) */}
                <div className="text-right shrink-0">
                  <p className="text-base font-bold text-white tabular-nums tracking-tight">
                    AED {item.total.toLocaleString('en-AE', { minimumFractionDigits: 0 })}
                  </p>
                  <p className="text-[10px] text-slate-400 font-medium">
                    {totalPeriodAmount > 0 ? Math.round((item.total / totalPeriodAmount) * 100) : 0}% share
                  </p>
                </div>
              </div>
            );
          })
        ) : (
          <div className="p-6 text-center text-slate-500 text-xs">
            No transactions found for the selected {period.toLowerCase()} period.
          </div>
        )}
      </div>
    </div>
  );
};
