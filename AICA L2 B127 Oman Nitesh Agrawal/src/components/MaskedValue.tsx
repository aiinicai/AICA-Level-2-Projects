import React, { useState } from 'react';
import { Info } from 'lucide-react';
import type { TraceableKpi } from '../types/mis';

interface MaskedValueProps {
  formatted: string;
  masked: boolean;
  maskedText?: string;
  className?: string;
}

export const MaskedValue: React.FC<MaskedValueProps> = ({
  formatted,
  masked,
  maskedText = '•••.•••',
  className = '',
}) => {
  const [hovered, setHovered] = useState(false);

  if (!masked) {
    return <span className={`font-mono-num tabular-nums ${className}`}>{formatted}</span>;
  }

  return (
    <span
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onFocus={() => setHovered(true)}
      onBlur={() => setHovered(false)}
      tabIndex={0}
      title="Hover or focus to reveal confidential figure"
      className={`font-mono-num tabular-nums cursor-help transition-opacity duration-150 ${className}`}
    >
      {hovered ? formatted : maskedText}
    </span>
  );
};

interface KpiCardProps {
  kpi: TraceableKpi;
  masked: boolean;
  isArabic?: boolean;
}

export const TraceableKpiCard: React.FC<KpiCardProps> = ({ kpi, masked, isArabic = false }) => {
  const [showLineage, setShowLineage] = useState(false);

  const ragStyles: Record<TraceableKpi['rag'], { dot: string; label: string }> = {
    green: { dot: 'text-emerald-600 dark:text-emerald-400', label: 'Nominal' },
    amber: { dot: 'text-amber-600 dark:text-amber-400', label: 'Watch' },
    red: { dot: 'text-rose-600 dark:text-rose-400', label: 'Action' },
    neutral: { dot: 'text-slate-500 dark:text-slate-400', label: 'Tracked' },
  };

  const ragInfo = ragStyles[kpi.rag];

  return (
    <div
      className="relative rounded-lg border p-4 transition-colors"
      style={{
        backgroundColor: 'var(--re-surface)',
        borderColor: 'var(--re-border)',
      }}
    >
      <div className="flex items-start justify-between gap-2">
        <span className="text-xs font-medium" style={{ color: 'var(--re-text-muted)' }}>
          {isArabic ? kpi.labelAr : kpi.label}
        </span>
        <button
          type="button"
          onClick={() => setShowLineage((v) => !v)}
          aria-label={`Inspect formula lineage for ${kpi.label}`}
          className="p-1 rounded hover:opacity-80 shrink-0"
          style={{ color: 'var(--re-text-muted)' }}
        >
          <Info className="w-3.5 h-3.5" />
        </button>
      </div>

      <div className="mt-2 text-xl font-semibold tracking-tight" style={{ color: 'var(--re-text)' }}>
        <MaskedValue formatted={kpi.formatted} masked={masked} maskedText="•••.•••" />
      </div>

      <div className="mt-2 flex items-center gap-2 text-xs">
        <span className={`font-medium ${ragInfo.dot}`}>{ragInfo.label}</span>
        <span aria-hidden="true" style={{ color: 'var(--re-text-muted)' }}>·</span>
        <span className="truncate" style={{ color: 'var(--re-text-muted)' }}>
          {kpi.period}
        </span>
      </div>

      {showLineage && (
        <div
          className="mt-3 pt-3 border-t text-xs space-y-1"
          style={{ borderColor: 'var(--re-border)', color: 'var(--re-text-muted)' }}
        >
          <div>
            <strong style={{ color: 'var(--re-text)' }}>Formula:</strong> {kpi.formula}
          </div>
          <div>
            <strong style={{ color: 'var(--re-text)' }}>Source:</strong> {kpi.source}
          </div>
          <div>
            <strong style={{ color: 'var(--re-text)' }}>Assumptions:</strong> {kpi.assumptions}
          </div>
        </div>
      )}
    </div>
  );
};
