import React from 'react';
import { RiskLevel } from '../types';
import { CheckCircle2, AlertTriangle, AlertOctagon, Info } from 'lucide-react';

interface RiskBadgeProps {
  level: RiskLevel | 'pass' | 'fail' | 'warning' | 'info';
  label?: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export const RiskBadge: React.FC<RiskBadgeProps> = ({ 
  level, 
  label, 
  size = 'md',
  className = '' 
}) => {
  let normalized = level.toLowerCase();
  if (normalized === 'pass') normalized = 'compliant';
  if (normalized === 'fail') normalized = 'critical';

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-[10px] font-bold gap-1',
    md: 'px-2.5 py-1 text-xs font-bold gap-1.5',
    lg: 'px-3 py-1.5 text-xs font-bold gap-2',
  }[size];

  if (normalized === 'compliant') {
    return (
      <span 
        id="badge-compliant"
        className={`inline-flex items-center rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 tracking-tight uppercase ${sizeClasses} ${className}`}
      >
        <CheckCircle2 className={size === 'sm' ? 'w-3 h-3 text-emerald-600' : size === 'lg' ? 'w-4 h-4 text-emerald-600' : 'w-3.5 h-3.5 text-emerald-600'} />
        <span>{label || 'COMPLIANT'}</span>
      </span>
    );
  }

  if (normalized === 'warning') {
    return (
      <span 
        id="badge-warning"
        className={`inline-flex items-center rounded-full bg-amber-50 text-amber-700 border border-amber-200 tracking-tight uppercase ${sizeClasses} ${className}`}
      >
        <AlertTriangle className={size === 'sm' ? 'w-3 h-3 text-amber-600' : size === 'lg' ? 'w-4 h-4 text-amber-600' : 'w-3.5 h-3.5 text-amber-600'} />
        <span>{label || 'WARNING'}</span>
      </span>
    );
  }

  if (normalized === 'critical') {
    return (
      <span 
        id="badge-critical"
        className={`inline-flex items-center rounded-full bg-red-50 text-red-700 border border-red-200 tracking-tight uppercase ${sizeClasses} ${className}`}
      >
        <AlertOctagon className={size === 'sm' ? 'w-3 h-3 text-red-600' : size === 'lg' ? 'w-4 h-4 text-red-600' : 'w-3.5 h-3.5 text-red-600'} />
        <span>{label || 'ACTION REQ'}</span>
      </span>
    );
  }

  return (
    <span 
      id="badge-info"
      className={`inline-flex items-center rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200 tracking-tight uppercase ${sizeClasses} ${className}`}
    >
      <Info className={size === 'sm' ? 'w-3 h-3 text-indigo-600' : size === 'lg' ? 'w-4 h-4 text-indigo-600' : 'w-3.5 h-3.5 text-indigo-600'} />
      <span>{label || 'AUDIT NOTE'}</span>
    </span>
  );
};

