import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Sparkles, TrendingUp, ShieldAlert, Gauge, ListChecks, Lightbulb,
  RefreshCw, BadgeCheck, Target, ArrowRight,
} from "lucide-react";
import { api } from "../services/api";
import { useCase } from "../hooks/useCase";
import { CardTitle, EmptyState, Spinner, StatusChip } from "../components/ui";
import type { Insight } from "../types";

const SECTION_ORDER = [
  { key: "business_quality", title: "Overall Business Quality", icon: <Gauge size={16} className="text-primary" /> },
  { key: "key_insight", title: "AI-Generated Key Insights", icon: <Sparkles size={16} className="text-primary" /> },
  { key: "positive_driver", title: "Positive Drivers", icon: <TrendingUp size={16} className="text-mint-text" /> },
  { key: "risk_flag", title: "Risk Flags", icon: <ShieldAlert size={16} className="text-risk" /> },
  { key: "earnings_quality", title: "Earnings Quality", icon: <BadgeCheck size={16} className="text-teal2" /> },
  { key: "strength", title: "Business Strengths", icon: <Target size={16} className="text-violet2" /> },
  { key: "assumption_review", title: "Assumption Review", icon: <ListChecks size={16} className="text-warn-text" /> },
  { key: "explainability", title: "Explainability Highlights", icon: <Lightbulb size={16} className="text-warn" /> },
  { key: "next_action", title: "Recommended Next Actions", icon: <ArrowRight size={16} className="text-primary" /> },
];

export default function Insights() {
  const { activeCaseId } = useCase();
  const qc = useQueryClient();
  const { data: insights, isLoading } = useQuery({
    queryKey: ["insights", activeCaseId],
    queryFn: () => api.get<Insight[]>(`/api/valuations/${activeCaseId}/insights`),
    enabled: !!activeCaseId,
  });

  const refresh = useMutation({
    mutationFn: () => api.post(`/api/valuations/${activeCaseId}/insights/refresh`, { use_ai: true }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["insights", activeCaseId] }),
  });

  if (!activeCaseId || isLoading) return <Spinner label="Loading insights…" />;
  if (!insights?.length) {
    return <EmptyState title="No insights yet"
      body="Run a valuation to generate engine-grounded insights. Connect a Gemini API key in Settings to add AI narrative on top."
      action={<button className="btn-primary" onClick={() => refresh.mutate()} disabled={refresh.isPending}>
        <RefreshCw size={15} className={refresh.isPending ? "animate-spin" : ""} /> Generate Insights</button>} />;
  }

  const grouped = SECTION_ORDER
    .map((s) => ({ ...s, items: insights.filter((i) => i.section === s.key) }))
    .filter((s) => s.items.length > 0);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between card-pad !py-3.5 bg-gradient-to-r from-primary-50/70 to-surface">
        <p className="text-[13px] text-slate2 flex items-center gap-2">
          <Sparkles size={15} className="text-primary" />
          Every insight is grounded in the deterministic engine's stored data — the AI explains, it never invents numbers.
        </p>
        <button className="btn-secondary !py-2 text-xs" onClick={() => refresh.mutate()} disabled={refresh.isPending}>
          <RefreshCw size={13} className={refresh.isPending ? "animate-spin" : ""} />
          {refresh.isPending ? "Refreshing…" : "Refresh Insights"}
        </button>
      </div>

      <div className="grid grid-cols-3 gap-4 items-start">
        {grouped.map((section) => (
          <div key={section.key} className="card-pad break-inside-avoid">
            <CardTitle icon={section.icon}>{section.title}</CardTitle>
            <ul className="space-y-3.5">
              {section.items.map((i) => (
                <li key={i.id} className="border-l-2 pl-3 border-line">
                  <div className="flex items-start justify-between gap-2">
                    {i.title && <p className="text-[13px] font-bold text-navy leading-snug">{i.title}</p>}
                    {["high", "moderate", "positive", "low"].includes(i.severity) && (
                      <StatusChip status={i.severity} />
                    )}
                  </div>
                  <p className="text-[12.5px] text-slate2 leading-relaxed mt-0.5">{i.body}</p>
                  {i.source === "ai" && (
                    <span className="chip-violet mt-1.5 inline-flex items-center gap-1"><Sparkles size={10} /> AI narrative</span>
                  )}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}
