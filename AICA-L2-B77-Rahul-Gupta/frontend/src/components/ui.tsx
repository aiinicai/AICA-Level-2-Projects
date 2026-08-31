/** Small shared UI primitives styled to the CompanyVal AI design system. */
import { Info } from "lucide-react";
import type { ReactNode } from "react";

export function InfoDot({ tip }: { tip?: string }) {
  return (
    <span title={tip} className="inline-flex text-slate3 cursor-help align-middle">
      <Info size={13} strokeWidth={2} />
    </span>
  );
}

export function CardTitle({
  icon,
  children,
  right,
  tip,
}: {
  icon?: ReactNode;
  children: ReactNode;
  right?: ReactNode;
  tip?: string;
}) {
  return (
    <div className="flex items-center justify-between mb-4">
      <div className="flex items-center gap-2">
        {icon}
        <h3 className="section-title">{children}</h3>
        {tip && <InfoDot tip={tip} />}
      </div>
      {right}
    </div>
  );
}

export function ProgressRing({
  value,
  size = 96,
  stroke = 9,
  color = "#2563EB",
  track = "#E5EAF2",
  gradient = false,
  children,
}: {
  value: number; // 0-100
  size?: number;
  stroke?: number;
  color?: string;
  track?: string;
  gradient?: boolean;
  children?: ReactNode;
}) {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const off = c * (1 - Math.min(Math.max(value, 0), 100) / 100);
  const gid = `rg-${Math.round(value)}-${size}`;
  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        {gradient && (
          <defs>
            <linearGradient id={gid} x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#2563EB" />
              <stop offset="100%" stopColor="#10B981" />
            </linearGradient>
          </defs>
        )}
        <circle cx={size / 2} cy={size / 2} r={r} stroke={track} strokeWidth={stroke} fill="none" />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          stroke={gradient ? `url(#${gid})` : color}
          strokeWidth={stroke}
          fill="none"
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={off}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">{children}</div>
    </div>
  );
}

export function Toggle({
  checked,
  onChange,
  disabled,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={`cv-toggle ${checked ? "bg-primary" : "bg-line"} ${disabled ? "opacity-50" : ""}`}
    >
      <span className={`knob ${checked ? "translate-x-[23px]" : "translate-x-[3px]"}`} />
    </button>
  );
}

export function StatusChip({ status }: { status: string }) {
  const map: Record<string, { cls: string; label: string }> = {
    completed: { cls: "chip-mint", label: "Completed" },
    interview: { cls: "chip-warn", label: "In Progress" },
    valuation: { cls: "chip-warn", label: "In Progress" },
    documents: { cls: "chip-warn", label: "In Progress" },
    review: { cls: "chip-warn", label: "In Progress" },
    draft: { cls: "chip-blue", label: "Draft" },
    verified: { cls: "chip-mint", label: "Verified" },
    needs_review: { cls: "chip-warn", label: "Needs Review" },
    low_confidence: { cls: "chip-violet", label: "Low Confidence" },
    unverified: { cls: "chip-blue", label: "Unverified" },
    high: { cls: "chip-risk", label: "High" },
    moderate: { cls: "chip-warn", label: "Moderate" },
    medium: { cls: "chip-warn", label: "Moderate" },
    low: { cls: "chip-mint", label: "Low" },
    positive: { cls: "chip-mint", label: "Positive" },
  };
  const m = map[status] ?? { cls: "chip-blue", label: status };
  return <span className={m.cls}>{m.label}</span>;
}

export function Spinner({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-3 py-16 text-slate2 text-sm">
      <span className="h-5 w-5 rounded-full border-2 border-primary border-t-transparent animate-spin" />
      {label}
    </div>
  );
}

export function EmptyState({ title, body, action }: { title: string; body?: string; action?: ReactNode }) {
  return (
    <div className="card p-10 text-center">
      <p className="font-semibold text-navy">{title}</p>
      {body && <p className="text-sm text-slate2 mt-1.5 max-w-md mx-auto">{body}</p>}
      {action && <div className="mt-4 flex justify-center">{action}</div>}
    </div>
  );
}
