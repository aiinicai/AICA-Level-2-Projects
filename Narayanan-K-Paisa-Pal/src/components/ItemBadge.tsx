import React from 'react';
import { AlertCircle, Clock, CheckCircle2, Calendar } from 'lucide-react';
import { NormalizedAlert } from '../types';
import { daysTo, stateOf } from '../utils/calculations';

interface Props {
  alert: NormalizedAlert;
}

export const ItemBadge: React.FC<Props> = ({ alert }) => {
  const s = stateOf(alert);
  const d = daysTo(alert);

  let label = 'Upcoming';
  let icon = Calendar;
  let colorCls = 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-700';

  if (alert.vk === 'exp') {
    if (s === 'overdue') {
      label = `Expired ${-d}d`;
      icon = AlertCircle;
      colorCls = 'bg-rose-100 dark:bg-rose-950/70 text-rose-700 dark:text-rose-300 border-rose-300 dark:border-rose-900';
    } else if (s === 'today') {
      label = 'Expires today';
      icon = Clock;
      colorCls = 'bg-amber-100 dark:bg-amber-950/70 text-amber-800 dark:text-amber-300 border-amber-300 dark:border-amber-900';
    } else if (s === 'soon') {
      label = `Expiring ${d}d`;
      icon = Clock;
      colorCls = 'bg-amber-100 dark:bg-amber-950/70 text-amber-800 dark:text-amber-300 border-amber-300 dark:border-amber-900';
    } else {
      label = 'Valid';
      icon = CheckCircle2;
      colorCls = 'bg-emerald-100 dark:bg-emerald-950/70 text-emerald-800 dark:text-emerald-300 border-emerald-300 dark:border-emerald-900';
    }
  } else if (alert.vk === 'mat') {
    if (s === 'overdue') {
      label = `Matured ${-d}d`;
      icon = AlertCircle;
      colorCls = 'bg-rose-100 dark:bg-rose-950/70 text-rose-700 dark:text-rose-300 border-rose-300 dark:border-rose-900';
    } else if (s === 'today') {
      label = 'Matures today';
      icon = Clock;
      colorCls = 'bg-amber-100 dark:bg-amber-950/70 text-amber-800 dark:text-amber-300 border-amber-300 dark:border-amber-900';
    } else if (s === 'soon') {
      label = `Maturing ${d}d`;
      icon = Clock;
      colorCls = 'bg-amber-100 dark:bg-amber-950/70 text-amber-800 dark:text-amber-300 border-amber-300 dark:border-amber-900';
    } else {
      label = 'Active';
      icon = Calendar;
      colorCls = 'bg-blue-100 dark:bg-blue-950/70 text-blue-800 dark:text-blue-300 border-blue-300 dark:border-blue-900';
    }
  } else {
    // Due date
    if (s === 'paid') {
      label = 'Paid';
      icon = CheckCircle2;
      colorCls = 'bg-emerald-100 dark:bg-emerald-950/70 text-emerald-800 dark:text-emerald-300 border-emerald-300 dark:border-emerald-900';
    } else if (s === 'overdue') {
      label = `Overdue ${-d}d`;
      icon = AlertCircle;
      colorCls = 'bg-rose-100 dark:bg-rose-950/70 text-rose-700 dark:text-rose-300 border-rose-300 dark:border-rose-900 font-bold';
    } else if (s === 'today') {
      label = 'Due today';
      icon = Clock;
      colorCls = 'bg-amber-100 dark:bg-amber-950/70 text-amber-800 dark:text-amber-300 border-amber-300 dark:border-amber-900 font-bold';
    } else if (s === 'soon') {
      label = `Due soon ${d}d`;
      icon = Clock;
      colorCls = 'bg-amber-50 dark:bg-amber-950/50 text-amber-800 dark:text-amber-300 border-amber-200 dark:border-amber-900';
    } else {
      label = `Upcoming ${d}d`;
      icon = Calendar;
      colorCls = 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-700';
    }
  }

  const IconComp = icon;

  return (
    <span
      className={`inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full border ${colorCls} whitespace-nowrap`}
    >
      <IconComp className="w-3.5 h-3.5 flex-shrink-0" />
      <span>{label}</span>
    </span>
  );
};
