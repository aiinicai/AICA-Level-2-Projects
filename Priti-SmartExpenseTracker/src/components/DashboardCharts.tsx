import React, { useState } from 'react';
import { TransactionCategory } from '../types';
import { CATEGORY_CONFIG } from './CategoryIcon';
import { formatINR } from '../utils/formatters';

interface CategoryBreakdownProps {
  categoryTotals: Record<TransactionCategory, number>;
  totalSpend: number;
}

export const CategoryDonutChart: React.FC<CategoryBreakdownProps> = ({ categoryTotals, totalSpend }) => {
  const [hoveredCategory, setHoveredCategory] = useState<TransactionCategory | null>(null);

  const categories = (Object.keys(categoryTotals) as TransactionCategory[])
    .filter((cat) => cat !== 'Investment' && categoryTotals[cat] > 0)
    .sort((a, b) => categoryTotals[b] - categoryTotals[a]);

  if (categories.length === 0 || totalSpend === 0) {
    return (
      <div className="h-64 flex flex-col items-center justify-center text-slate-400 text-xs">
        <p>No expenses recorded for this period</p>
      </div>
    );
  }

  // Vivid vibrant color palette
  const SVG_COLORS: Record<TransactionCategory, { solid: string; glow: string; gradient: string }> = {
    Food: { solid: '#f97316', glow: 'rgba(249, 115, 22, 0.4)', gradient: 'from-orange-500 to-amber-500' },
    Travel: { solid: '#0ea5e9', glow: 'rgba(14, 165, 233, 0.4)', gradient: 'from-sky-500 to-cyan-500' },
    Shopping: { solid: '#a855f7', glow: 'rgba(168, 85, 247, 0.4)', gradient: 'from-purple-500 to-fuchsia-500' },
    Bills: { solid: '#f43f5e', glow: 'rgba(244, 63, 94, 0.4)', gradient: 'from-rose-500 to-pink-500' },
    Investment: { solid: '#10b981', glow: 'rgba(16, 185, 129, 0.4)', gradient: 'from-emerald-500 to-teal-500' },
    Healthcare: { solid: '#14b8a6', glow: 'rgba(20, 184, 166, 0.4)', gradient: 'from-teal-500 to-emerald-500' },
    Entertainment: { solid: '#6366f1', glow: 'rgba(99, 102, 241, 0.4)', gradient: 'from-indigo-500 to-blue-500' },
    Other: { solid: '#64748b', glow: 'rgba(100, 116, 139, 0.4)', gradient: 'from-slate-500 to-gray-500' },
  };

  // Build SVG arc slices
  let cumulativeAngle = 0;
  const radius = 78;
  const strokeWidth = 30;
  const center = 110;
  const circumference = 2 * Math.PI * radius;

  const slices = categories.map((cat) => {
    const amount = categoryTotals[cat];
    const percentage = (amount / totalSpend) * 100;
    const strokeDasharray = `${(percentage / 100) * circumference} ${circumference}`;
    const strokeDashoffset = -((cumulativeAngle / 100) * circumference);
    cumulativeAngle += percentage;

    return {
      category: cat,
      amount,
      percentage,
      strokeDasharray,
      strokeDashoffset,
      color: SVG_COLORS[cat]?.solid || '#64748b',
      glow: SVG_COLORS[cat]?.glow || 'rgba(100,116,139,0.3)',
    };
  });

  const activeCategory = hoveredCategory || (categories.length > 0 ? categories[0] : null);
  const activeAmount = activeCategory ? categoryTotals[activeCategory] : totalSpend;
  const activePercent = activeCategory && totalSpend > 0 ? ((activeAmount / totalSpend) * 100).toFixed(1) : '100';

  return (
    <div className="flex flex-col sm:flex-row items-center gap-6">
      {/* SVG Donut Circle with Vibrant Styling & Hover Glow */}
      <div className="relative w-56 h-56 shrink-0 flex items-center justify-center">
        <svg viewBox="0 0 220 220" className="w-full h-full -rotate-90 transform drop-shadow-md">
          <circle
            cx={center}
            cy={center}
            r={radius}
            fill="none"
            stroke="currentColor"
            strokeWidth={strokeWidth}
            className="text-slate-100 dark:text-slate-800"
          />
          {slices.map((slice) => {
            const isHovered = hoveredCategory === slice.category;
            return (
              <circle
                key={slice.category}
                cx={center}
                cy={center}
                r={radius}
                fill="none"
                stroke={slice.color}
                strokeWidth={isHovered ? strokeWidth + 6 : strokeWidth}
                strokeDasharray={slice.strokeDasharray}
                strokeDashoffset={slice.strokeDashoffset}
                strokeLinecap="round"
                onMouseEnter={() => setHoveredCategory(slice.category)}
                onMouseLeave={() => setHoveredCategory(null)}
                className="transition-all duration-200 cursor-pointer"
                style={{
                  filter: isHovered ? `drop-shadow(0 0 8px ${slice.glow})` : undefined,
                }}
              />
            );
          })}
        </svg>

        {/* Center Text inside Donut with Glow Accent */}
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none text-center px-4">
          <span className="text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider truncate max-w-[120px]">
            {activeCategory || 'Total Spend'}
          </span>
          <span className="text-xl font-extrabold text-slate-900 dark:text-white tracking-tight mt-0.5">
            {formatINR(activeAmount)}
          </span>
          {activeCategory && (
            <span
              className="text-[11px] font-extrabold px-2 py-0.5 rounded-full mt-1 text-white shadow-xs"
              style={{ backgroundColor: SVG_COLORS[activeCategory]?.solid }}
            >
              {activePercent}% of total
            </span>
          )}
        </div>
      </div>

      {/* Legend & Breakdown List with Mini Progress Bars */}
      <div className="flex-1 w-full space-y-2.5">
        {categories.map((cat) => {
          const amount = categoryTotals[cat];
          const pct = ((amount / totalSpend) * 100).toFixed(0);
          const config = CATEGORY_CONFIG[cat];
          const isHovered = hoveredCategory === cat;
          const colorObj = SVG_COLORS[cat];

          return (
            <div
              key={cat}
              onMouseEnter={() => setHoveredCategory(cat)}
              onMouseLeave={() => setHoveredCategory(null)}
              className={`p-2.5 rounded-xl border transition-all cursor-pointer ${
                isHovered
                  ? 'border-emerald-400 dark:border-emerald-600 bg-white dark:bg-slate-800 shadow-md scale-[1.02]'
                  : 'border-slate-100 dark:border-slate-800/80 bg-slate-50/60 dark:bg-slate-800/40 hover:bg-white dark:hover:bg-slate-800 hover:border-slate-200'
              }`}
            >
              <div className="flex items-center justify-between text-xs mb-1.5">
                <div className="flex items-center gap-2 min-w-0">
                  <span
                    className="w-3 h-3 rounded-full shrink-0 shadow-xs"
                    style={{ backgroundColor: colorObj.solid }}
                  />
                  <span className="font-bold text-slate-800 dark:text-slate-200 truncate">
                    {config.label}
                  </span>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <span
                    className="text-[10px] font-extrabold px-1.5 py-0.5 rounded-md text-white"
                    style={{ backgroundColor: colorObj.solid }}
                  >
                    {pct}%
                  </span>
                  <span className="font-extrabold text-slate-900 dark:text-white">
                    {formatINR(amount)}
                  </span>
                </div>
              </div>

              {/* Progress bar */}
              <div className="w-full bg-slate-200/70 dark:bg-slate-700/60 h-1.5 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{
                    width: `${pct}%`,
                    backgroundColor: colorObj.solid,
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

interface SpendingTrendChartProps {
  dailySpending: Array<{ date: string; dayLabel: string; amount: number }>;
}

export const SpendingTrendChart: React.FC<SpendingTrendChartProps> = ({ dailySpending }) => {
  const [hoveredPoint, setHoveredPoint] = useState<{
    date: string;
    dayLabel: string;
    amount: number;
    x: number;
    y: number;
  } | null>(null);

  if (dailySpending.length === 0) {
    return (
      <div className="h-52 flex items-center justify-center text-slate-400 text-xs">
        No spending data for trend chart
      </div>
    );
  }

  const maxAmount = Math.max(...dailySpending.map((d) => d.amount), 500);
  const chartHeight = 160;
  const chartWidth = 560;
  const paddingX = 30;
  const paddingY = 24;

  const innerWidth = chartWidth - paddingX * 2;
  const innerHeight = chartHeight - paddingY * 2;

  const points = dailySpending.map((item, idx) => {
    const x = paddingX + (idx / Math.max(dailySpending.length - 1, 1)) * innerWidth;
    const y = paddingY + innerHeight - (item.amount / maxAmount) * innerHeight;
    return { ...item, x, y };
  });

  const pathD = points.reduce((acc, pt, idx) => {
    return idx === 0 ? `M ${pt.x},${pt.y}` : `${acc} L ${pt.x},${pt.y}`;
  }, '');

  const areaD = `${pathD} L ${points[points.length - 1].x},${paddingY + innerHeight} L ${points[0].x},${paddingY + innerHeight} Z`;

  return (
    <div className="relative w-full overflow-hidden">
      <div className="w-full overflow-x-auto">
        <svg
          viewBox={`0 0 ${chartWidth} ${chartHeight}`}
          className="w-full h-44 overflow-visible"
          preserveAspectRatio="none"
        >
          <defs>
            <linearGradient id="trendGradient" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#06b6d4" stopOpacity="0.4" />
              <stop offset="50%" stopColor="#10b981" stopOpacity="0.2" />
              <stop offset="100%" stopColor="#6366f1" stopOpacity="0.0" />
            </linearGradient>

            <linearGradient id="lineGradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#06b6d4" />
              <stop offset="50%" stopColor="#10b981" />
              <stop offset="100%" stopColor="#6366f1" />
            </linearGradient>
          </defs>

          {/* Grid horizontal guideline */}
          <line
            x1={paddingX}
            y1={paddingY}
            x2={chartWidth - paddingX}
            y2={paddingY}
            stroke="currentColor"
            strokeDasharray="4 4"
            className="text-slate-200 dark:text-slate-800"
          />
          <line
            x1={paddingX}
            y1={paddingY + innerHeight / 2}
            x2={chartWidth - paddingX}
            y2={paddingY + innerHeight / 2}
            stroke="currentColor"
            strokeDasharray="4 4"
            className="text-slate-200 dark:text-slate-800"
          />
          <line
            x1={paddingX}
            y1={paddingY + innerHeight}
            x2={chartWidth - paddingX}
            y2={paddingY + innerHeight}
            stroke="currentColor"
            className="text-slate-200 dark:text-slate-800"
          />

          {/* Glowing Area Fill */}
          <path d={areaD} fill="url(#trendGradient)" />

          {/* Multicolored Gradient Trend Line */}
          <path
            d={pathD}
            fill="none"
            stroke="url(#lineGradient)"
            strokeWidth="3.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* Vibrant Points */}
          {points.map((pt, idx) => (
            <g key={idx}>
              <circle
                cx={pt.x}
                cy={pt.y}
                r="4.5"
                fill="#ffffff"
                stroke="#10b981"
                strokeWidth="2.5"
                className="cursor-pointer hover:scale-175 transition-transform"
                onMouseEnter={() => setHoveredPoint(pt)}
                onMouseLeave={() => setHoveredPoint(null)}
              />
            </g>
          ))}
        </svg>
      </div>

      {/* Floating Tooltip */}
      {hoveredPoint && (
        <div
          className="absolute z-20 pointer-events-none rounded-xl bg-gradient-to-r from-slate-900 to-indigo-950 text-white text-[11px] px-3 py-1.5 shadow-xl border border-indigo-500/30 -translate-x-1/2 -translate-y-full mb-2 animate-in fade-in"
          style={{
            left: `${(hoveredPoint.x / chartWidth) * 100}%`,
            top: `${(hoveredPoint.y / chartHeight) * 100}%`,
          }}
        >
          <p className="font-bold text-emerald-400">{hoveredPoint.dayLabel}</p>
          <p className="font-extrabold text-white text-xs">{formatINR(hoveredPoint.amount)}</p>
        </div>
      )}

      {/* Day Labels along bottom */}
      <div className="flex justify-between items-center px-4 pt-1 text-[11px] font-bold text-slate-400">
        <span className="text-cyan-600 dark:text-cyan-400">{dailySpending[0]?.dayLabel || 'Day 1'}</span>
        <span className="text-emerald-600 dark:text-emerald-400">
          {dailySpending[Math.floor(dailySpending.length / 2)]?.dayLabel || 'Mid Month'}
        </span>
        <span className="text-indigo-600 dark:text-indigo-400">{dailySpending[dailySpending.length - 1]?.dayLabel || 'Today'}</span>
      </div>
    </div>
  );
};
