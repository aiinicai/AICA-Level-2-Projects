import React from 'react';
import {
  Utensils,
  Car,
  ShoppingBag,
  Receipt,
  TrendingUp,
  HeartPulse,
  Film,
  HelpCircle,
} from 'lucide-react';
import { TransactionCategory } from '../types';

export const CATEGORY_CONFIG: Record<
  TransactionCategory,
  {
    label: string;
    icon: React.ComponentType<{ className?: string }>;
    color: string;
    bg: string;
    border: string;
    gradient: string;
    tagBg: string;
    tagText: string;
  }
> = {
  Food: {
    label: 'Food & Dining',
    icon: Utensils,
    color: 'text-orange-600 dark:text-orange-400',
    bg: 'bg-orange-50 dark:bg-orange-950/40',
    border: 'border-orange-200 dark:border-orange-800',
    gradient: 'bg-gradient-to-tr from-amber-500 to-orange-500 text-white',
    tagBg: 'bg-orange-100 dark:bg-orange-950/60',
    tagText: 'text-orange-800 dark:text-orange-300',
  },
  Travel: {
    label: 'Travel & Commute',
    icon: Car,
    color: 'text-sky-600 dark:text-sky-400',
    bg: 'bg-sky-50 dark:bg-sky-950/40',
    border: 'border-sky-200 dark:border-sky-800',
    gradient: 'bg-gradient-to-tr from-sky-500 to-cyan-500 text-white',
    tagBg: 'bg-sky-100 dark:bg-sky-950/60',
    tagText: 'text-sky-800 dark:text-sky-300',
  },
  Shopping: {
    label: 'Shopping & Groceries',
    icon: ShoppingBag,
    color: 'text-purple-600 dark:text-purple-400',
    bg: 'bg-purple-50 dark:bg-purple-950/40',
    border: 'border-purple-200 dark:border-purple-800',
    gradient: 'bg-gradient-to-tr from-purple-500 to-fuchsia-500 text-white',
    tagBg: 'bg-purple-100 dark:bg-purple-950/60',
    tagText: 'text-purple-800 dark:text-purple-300',
  },
  Bills: {
    label: 'Bills & Utilities',
    icon: Receipt,
    color: 'text-rose-600 dark:text-rose-400',
    bg: 'bg-rose-50 dark:bg-rose-950/40',
    border: 'border-rose-200 dark:border-rose-800',
    gradient: 'bg-gradient-to-tr from-rose-500 to-pink-500 text-white',
    tagBg: 'bg-rose-100 dark:bg-rose-950/60',
    tagText: 'text-rose-800 dark:text-rose-300',
  },
  Investment: {
    label: 'Investment',
    icon: TrendingUp,
    color: 'text-emerald-700 dark:text-emerald-400',
    bg: 'bg-emerald-50 dark:bg-emerald-950/40',
    border: 'border-emerald-200 dark:border-emerald-800',
    gradient: 'bg-gradient-to-tr from-emerald-600 to-teal-500 text-white',
    tagBg: 'bg-emerald-100 dark:bg-emerald-950/60',
    tagText: 'text-emerald-800 dark:text-emerald-300',
  },
  Healthcare: {
    label: 'Healthcare',
    icon: HeartPulse,
    color: 'text-teal-600 dark:text-teal-400',
    bg: 'bg-teal-50 dark:bg-teal-950/40',
    border: 'border-teal-200 dark:border-teal-800',
    gradient: 'bg-gradient-to-tr from-teal-500 to-emerald-500 text-white',
    tagBg: 'bg-teal-100 dark:bg-teal-950/60',
    tagText: 'text-teal-800 dark:text-teal-300',
  },
  Entertainment: {
    label: 'Entertainment',
    icon: Film,
    color: 'text-indigo-600 dark:text-indigo-400',
    bg: 'bg-indigo-50 dark:bg-indigo-950/40',
    border: 'border-indigo-200 dark:border-indigo-800',
    gradient: 'bg-gradient-to-tr from-indigo-500 to-blue-500 text-white',
    tagBg: 'bg-indigo-100 dark:bg-indigo-950/60',
    tagText: 'text-indigo-800 dark:text-indigo-300',
  },
  Other: {
    label: 'Other',
    icon: HelpCircle,
    color: 'text-slate-600 dark:text-slate-400',
    bg: 'bg-slate-50 dark:bg-slate-800/40',
    border: 'border-slate-200 dark:border-slate-700',
    gradient: 'bg-gradient-to-tr from-slate-500 to-zinc-600 text-white',
    tagBg: 'bg-slate-100 dark:bg-slate-800',
    tagText: 'text-slate-700 dark:text-slate-300',
  },
};

export const CategoryIcon: React.FC<{
  category: TransactionCategory;
  className?: string;
  size?: string;
  useGradient?: boolean;
}> = ({ category, className = '', size = 'w-4 h-4', useGradient = true }) => {
  const config = CATEGORY_CONFIG[category] || CATEGORY_CONFIG.Other;
  const Icon = config.icon;
  return (
    <div
      className={`inline-flex items-center justify-center rounded-xl p-2.5 shadow-sm transition-transform group-hover:scale-105 ${
        useGradient ? config.gradient : `${config.bg} ${config.color}`
      } ${className}`}
    >
      <Icon className={size} />
    </div>
  );
};
