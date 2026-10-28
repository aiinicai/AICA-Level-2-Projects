import React from 'react';
import { 
  Activity, 
  Droplets, 
  TrendingUp, 
  Scale, 
  Zap, 
  Award, 
  Info, 
  CheckCircle2, 
  AlertCircle 
} from 'lucide-react';
import { FinancialHealthScore, HealthScoreCategory } from '../types/financial';

interface HealthScoreCardProps {
  healthScore: FinancialHealthScore;
}

export const HealthScoreCard: React.FC<HealthScoreCardProps> = ({ healthScore }) => {
  const { totalScore, rating, categories } = healthScore;

  // Grade color scheme
  const getRatingStyle = (r: string) => {
    switch (r) {
      case 'Excellent':
        return {
          badge: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
          gradient: 'from-emerald-500 to-teal-600',
          ring: 'text-emerald-500',
          text: 'text-emerald-400'
        };
      case 'Good':
        return {
          badge: 'bg-blue-500/10 text-blue-400 border-blue-500/30',
          gradient: 'from-blue-500 to-cyan-600',
          ring: 'text-blue-500',
          text: 'text-blue-400'
        };
      case 'Average':
        return {
          badge: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
          gradient: 'from-amber-500 to-yellow-600',
          ring: 'text-amber-500',
          text: 'text-amber-400'
        };
      case 'Weak':
        return {
          badge: 'bg-orange-500/10 text-orange-400 border-orange-500/30',
          gradient: 'from-orange-500 to-amber-600',
          ring: 'text-orange-500',
          text: 'text-orange-400'
        };
      default: // High Risk
        return {
          badge: 'bg-rose-500/10 text-rose-400 border-rose-500/30',
          gradient: 'from-rose-500 to-red-600',
          ring: 'text-rose-500',
          text: 'text-rose-400'
        };
    }
  };

  const style = getRatingStyle(rating);

  const getCategoryIcon = (cat: string) => {
    switch (cat) {
      case 'Liquidity': return <Droplets className="w-5 h-5 text-cyan-400" />;
      case 'Profitability': return <TrendingUp className="w-5 h-5 text-emerald-400" />;
      case 'Solvency': return <Scale className="w-5 h-5 text-indigo-400" />;
      case 'Efficiency': return <Zap className="w-5 h-5 text-amber-400" />;
      default: return <Activity className="w-5 h-5 text-blue-400" />;
    }
  };

  const getProgressColor = (score: number) => {
    if (score >= 80) return 'bg-emerald-500';
    if (score >= 65) return 'bg-blue-500';
    if (score >= 50) return 'bg-amber-500';
    if (score >= 35) return 'bg-orange-500';
    return 'bg-rose-500';
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 lg:p-6 shadow-xl relative overflow-hidden">
      {/* Decorative gradient glow */}
      <div className="absolute top-0 right-0 -mr-16 -mt-16 w-64 h-64 bg-blue-600/10 rounded-full blur-3xl pointer-events-none" />

      <div className="flex flex-col md:flex-row items-start md:items-center justify-between pb-6 border-b border-slate-800/80 gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <h2 className="text-lg font-bold text-white tracking-tight">Institutional Financial Health Score</h2>
            <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
              Model V2.4
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Engineered scoring across 4 core prudential pillars (25% weight each) calibrated to RBI/Basel banking norms.
          </p>
        </div>

        {/* Big Total Score Badge */}
        <div className="flex items-center space-x-4 bg-slate-800/70 p-3 rounded-xl border border-slate-700/80">
          <div className="relative flex items-center justify-center">
            {/* SVG circular progress */}
            <svg className="w-20 h-20 transform -rotate-90">
              <circle
                cx="40"
                cy="40"
                r="34"
                stroke="currentColor"
                strokeWidth="6"
                className="text-slate-750"
                fill="transparent"
              />
              <circle
                cx="40"
                cy="40"
                r="34"
                stroke="currentColor"
                strokeWidth="6"
                strokeDasharray={`${2 * Math.PI * 34}`}
                strokeDashoffset={`${2 * Math.PI * 34 * (1 - totalScore / 100)}`}
                strokeLinecap="round"
                className={style.ring}
                fill="transparent"
              />
            </svg>
            <div className="absolute flex flex-col items-center justify-center text-center">
              <span className="text-2xl font-black text-white">{totalScore}</span>
              <span className="text-[10px] text-slate-400 uppercase tracking-widest font-semibold">/100</span>
            </div>
          </div>

          <div>
            <div className="text-[11px] uppercase tracking-wider text-slate-400 font-semibold">Health Grade</div>
            <div className="text-base font-bold text-white flex items-center space-x-1.5 mt-0.5">
              <span>{rating}</span>
            </div>
            <span className={`inline-block text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full mt-1 border ${style.badge}`}>
              {totalScore >= 75 ? 'Low Credit Risk' : totalScore >= 50 ? 'Moderate Risk' : 'High Credit Risk'}
            </span>
          </div>
        </div>
      </div>

      {/* 4 Pillars Breakdown (25% each) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mt-6">
        {categories.map((cat: HealthScoreCategory) => (
          <div 
            key={cat.category}
            className="bg-slate-800/50 hover:bg-slate-800 border border-slate-700/70 hover:border-slate-600 rounded-xl p-4 transition-all duration-200"
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center space-x-2">
                <div className="p-1.5 rounded-lg bg-slate-900 border border-slate-700">
                  {getCategoryIcon(cat.category)}
                </div>
                <div>
                  <h3 className="text-xs font-bold text-slate-200">{cat.category}</h3>
                  <span className="text-[10px] text-slate-400 font-medium">Weight: {cat.weight}%</span>
                </div>
              </div>
              <div className="text-right">
                <span className="text-base font-extrabold text-white">{cat.score}</span>
                <span className="text-[10px] text-slate-400">/100</span>
              </div>
            </div>

            {/* Progress Bar */}
            <div className="w-full bg-slate-700/70 rounded-full h-2 mb-2.5 overflow-hidden">
              <div 
                className={`h-2 rounded-full transition-all duration-500 ${getProgressColor(cat.score)}`}
                style={{ width: `${Math.min(100, Math.max(5, cat.score))}%` }}
              />
            </div>

            <div className="flex items-center justify-between text-[11px] mb-1.5">
              <span className="text-slate-400">Weighted:</span>
              <span className="font-semibold text-cyan-300">{cat.weightedScore} / 25 pts</span>
            </div>

            <div className="text-[10px] text-slate-400 line-clamp-2 bg-slate-900/60 p-1.5 rounded border border-slate-800">
              <span className="font-medium text-slate-300">Drivers: </span>
              {cat.keyDriver}
            </div>
          </div>
        ))}
      </div>

      {/* Scoring Benchmark Scale Legend */}
      <div className="mt-5 pt-4 border-t border-slate-800/80 flex flex-wrap items-center justify-between text-[11px] text-slate-400 gap-2">
        <span className="font-medium text-slate-300">Prudential Rating Tiers:</span>
        <div className="flex flex-wrap items-center gap-3">
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-emerald-500"></span> 90-100: Excellent</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-blue-500"></span> 75-89: Good</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-amber-500"></span> 60-74: Average</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-orange-500"></span> 40-59: Weak</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-rose-500"></span> &lt; 40: High Risk</span>
        </div>
      </div>
    </div>
  );
};
