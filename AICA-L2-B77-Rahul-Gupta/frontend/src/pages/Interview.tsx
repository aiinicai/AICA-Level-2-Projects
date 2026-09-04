import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import {
  MessageSquareText, ShieldCheck, Clock, TrendingUp, ArrowLeft, ArrowRight,
  Save, Sparkles, ChevronRight, LineChart, Minus, TrendingDown, CircleDot,
  Landmark, ClipboardList, HelpCircle, CheckCircle2,
} from "lucide-react";
import { api, fmtCr, fmtPct } from "../services/api";
import { useCase } from "../hooks/useCase";
import { CardTitle, EmptyState, Spinner } from "../components/ui";
import type { InterviewState } from "../types";

const OPTION_ICONS = [TrendingUp, LineChart, Minus, TrendingDown, CircleDot, Landmark, ClipboardList];

const PRIORITY_CHIP: Record<string, string> = {
  critical: "chip-risk", high: "chip-blue", medium: "chip-warn", low: "chip-mint",
};

export default function Interview() {
  const { activeCaseId } = useCase();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [selected, setSelected] = useState<string>("");
  const [textValue, setTextValue] = useState("");
  const [elaboration, setElaboration] = useState("");

  const { data: state, isLoading } = useQuery({
    queryKey: ["interview", activeCaseId],
    queryFn: () => api.get<InterviewState>(`/api/valuations/${activeCaseId}/interview/state`),
    enabled: !!activeCaseId,
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["interview", activeCaseId] });
    qc.invalidateQueries({ queryKey: ["case", activeCaseId] });
  };

  const start = useMutation({
    mutationFn: () => api.post(`/api/valuations/${activeCaseId}/interview/start`),
    onSuccess: invalidate,
  });

  const answer = useMutation({
    mutationFn: (body: { question_id: string; value: string; elaboration: string }) =>
      api.post(`/api/valuations/${activeCaseId}/interview/answer`, body),
    onSuccess: () => { setSelected(""); setTextValue(""); setElaboration(""); invalidate(); },
  });

  useEffect(() => { setSelected(""); setTextValue(""); }, [state?.current_question?.id]);

  if (!activeCaseId || isLoading) return <Spinner label="Loading interview…" />;

  if (!state?.session) {
    return (
      <EmptyState
        title="Start the adaptive AI interview"
        body="The rules engine analyses the locked financials, flags what matters (growth spikes, margin swings, cash conversion) and plans 8–15 targeted questions. Every question explains why it is being asked."
        action={
          <button className="btn-primary" onClick={() => start.mutate()} disabled={start.isPending}>
            <Sparkles size={15} /> {start.isPending ? "Planning questions…" : "Start AI Interview"}
          </button>
        }
      />
    );
  }

  const s = state.session;
  const q = state.current_question;
  const pctDone = s.total ? Math.round((s.answered / s.total) * 100) : 0;
  const remainingMin = Math.max(1, Math.round((s.total - s.answered) * 1.5));
  const fc = state.financial_context;
  const value = q?.type === "single_choice" || q?.type === "yes_no" ? selected : textValue;

  return (
    <div className="space-y-5">
      {/* stat row */}
      <div className="grid grid-cols-4 gap-4">
        <div className="card-pad flex items-center gap-4">
          <span className="h-11 w-11 rounded-xl bg-primary-50 text-primary flex items-center justify-center"><MessageSquareText size={19} /></span>
          <div className="flex-1">
            <p className="text-xs font-semibold text-slate2">Interview Progress</p>
            <p className="text-xl font-extrabold text-navy">{s.answered} / {s.total}</p>
            <div className="h-1.5 rounded-full bg-line mt-1.5 overflow-hidden">
              <div className="h-full bg-primary rounded-full" style={{ width: `${pctDone}%` }} />
            </div>
            <p className="text-[10.5px] text-slate3 mt-1">{pctDone}% Complete</p>
          </div>
        </div>
        <div className="card-pad flex items-center gap-4">
          <span className="h-11 w-11 rounded-xl bg-mint-bg text-mint-text flex items-center justify-center"><ShieldCheck size={19} /></span>
          <div>
            <p className="text-xs font-semibold text-slate2">Valuation Readiness</p>
            <p className="text-xl font-extrabold text-navy">{state.readiness.score}%</p>
            <p className="text-[11px] font-bold text-mint-text flex items-center gap-1">{state.readiness.band} <ChevronRight size={11} /></p>
          </div>
        </div>
        <div className="card-pad flex items-center gap-4">
          <span className="h-11 w-11 rounded-xl bg-warn-bg text-warn-text flex items-center justify-center"><Clock size={19} /></span>
          <div>
            <p className="text-xs font-semibold text-slate2">Est. Time Remaining</p>
            <p className="text-xl font-extrabold text-navy">{s.status === "completed" ? "Done" : `${remainingMin} min`}</p>
            <p className="text-[11px] text-slate3">Based on your pace</p>
          </div>
        </div>
        <div className="card-pad flex items-center gap-4">
          <span className="h-11 w-11 rounded-xl bg-violet2-bg text-violet2 flex items-center justify-center"><TrendingUp size={19} /></span>
          <div>
            <p className="text-xs font-semibold text-slate2">Question Priority</p>
            <p className="text-xl font-extrabold text-navy capitalize">{q ? (q.priority === "critical" ? "Critical" : q.priority === "high" ? "High Impact" : q.priority) : "—"}</p>
            <p className="text-[11px] text-slate3">Focusing on key drivers</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-12 gap-5 items-start">
        {/* question card */}
        <div className="col-span-8 card p-6">
          {s.status === "completed" || !q ? (
            <div className="text-center py-14">
              <CheckCircle2 size={44} className="mx-auto text-mint" />
              <h2 className="text-xl font-extrabold text-navy mt-4">AI Interview Complete</h2>
              <p className="text-sm text-slate2 mt-1.5">
                Valuation Readiness: <b className="text-mint-text">{state.readiness.score}%</b> — all
                critical and high-priority questions are resolved.
              </p>
              <button className="btn-primary mt-6" onClick={() => navigate("/valuations")}>
                Proceed to Valuation <ArrowRight size={15} />
              </button>
            </div>
          ) : (
            <>
              <div className="flex items-center gap-3">
                <p className="text-sm font-bold text-navy">Question {state.current_number} of {s.total}</p>
                <span className="chip-mint">{q.category_label}</span>
                {q.valuation_impact.slice(0, 1).map((vi) => (
                  <span key={vi} className="chip-violet">{vi.replace(/_/g, " ").replace(/\b\w/g, (m) => m.toUpperCase())}</span>
                ))}
                <span className={`ml-auto ${PRIORITY_CHIP[q.priority] ?? "chip-blue"} flex items-center gap-1`}>
                  <Sparkles size={11} /> {q.priority === "high" ? "High Impact" : q.priority.charAt(0).toUpperCase() + q.priority.slice(1)}
                </span>
              </div>

              <h2 className="text-[22px] font-extrabold text-navy leading-snug mt-4 max-w-2xl">{q.question}</h2>

              {q.reason && (
                <div className="mt-4">
                  <p className="text-[13px] font-bold text-primary flex items-center gap-1.5">
                    <HelpCircle size={14} /> Why am I asking this?
                  </p>
                  <p className="text-[13px] text-slate2 mt-1 max-w-2xl">{q.reason}</p>
                </div>
              )}
              {q.trigger_rule && (
                <div className="mt-3 rounded-lg bg-primary-50/60 border border-primary-100/50 px-3.5 py-2.5 text-[12.5px] text-primary-700 flex items-center gap-2">
                  <CircleDot size={13} />
                  <span><b>Triggered Rule:</b> {q.trigger_rule} — this answer directly shapes the valuation assumptions.</span>
                </div>
              )}

              {(q.type === "single_choice" || q.type === "yes_no") ? (
                <div className={`grid gap-3 mt-5 ${q.options.length > 4 ? "grid-cols-4" : `grid-cols-${Math.max(q.options.length, 2)}`}`}
                  style={{ gridTemplateColumns: `repeat(${Math.min(q.options.length, 4)}, minmax(0, 1fr))` }}>
                  {q.options.map((opt, i) => {
                    const Icon = OPTION_ICONS[i % OPTION_ICONS.length];
                    const on = selected === opt;
                    const [main, ...rest] = opt.split(" (");
                    return (
                      <button key={opt} onClick={() => setSelected(opt)}
                        className={`relative rounded-xl2 border-2 p-4 text-center transition ${on ? "border-primary bg-primary-50/60" : "border-line bg-surface hover:bg-page"}`}>
                        {on && <span className="absolute top-2.5 left-2.5 h-4 w-4 rounded-full bg-primary text-white flex items-center justify-center"><CheckCircle2 size={11} /></span>}
                        <span className={`mx-auto h-10 w-10 rounded-xl flex items-center justify-center ${on ? "bg-primary text-white" : "bg-page text-slate2"}`}>
                          <Icon size={18} />
                        </span>
                        <p className="text-[13px] font-bold text-navy mt-2.5 leading-tight">{main}</p>
                        {rest.length > 0 && <p className="text-[11px] text-slate3 mt-0.5">({rest.join(" (")}</p>}
                      </button>
                    );
                  })}
                </div>
              ) : (
                <div className="mt-5">
                  <input className="input max-w-md" value={textValue}
                    placeholder={q.type === "percentage" ? "e.g. 15 (%)" : q.type === "currency" ? "e.g. ₹1.2 Cr or 120 Lakhs" : "Type your answer…"}
                    onChange={(e) => setTextValue(e.target.value)} />
                </div>
              )}

              <div className="mt-5">
                <label className="label !text-slate2 !font-medium">Elaborate (optional)</label>
                <div className="relative">
                  <textarea rows={3} maxLength={500} className="input resize-none"
                    placeholder="Add any context or details that may help our analysis..."
                    value={elaboration} onChange={(e) => setElaboration(e.target.value)} />
                  <span className="absolute bottom-2.5 right-3 text-[11px] text-slate3">{elaboration.length} / 500</span>
                </div>
              </div>

              {answer.isError && <p className="text-xs text-risk-text mt-2">{(answer.error as Error).message}</p>}

              <div className="mt-5 flex items-center justify-between">
                <button className="btn-secondary" disabled><ArrowLeft size={15} /> Previous</button>
                <button className="btn-secondary" onClick={() => navigate("/")}><Save size={15} /> Save & Exit</button>
                <button className="btn-primary" disabled={!value || answer.isPending}
                  onClick={() => answer.mutate({ question_id: q.id, value, elaboration })}>
                  {answer.isPending ? "Interpreting…" : "Next"} <ArrowRight size={15} />
                </button>
              </div>
            </>
          )}
        </div>

        {/* right rail */}
        <div className="col-span-4 space-y-4">
          <div className="card-pad">
            <CardTitle right={<span className="text-xs font-semibold text-primary flex items-center gap-1">View all <ArrowRight size={11} /></span>}>
              Interview Progress by Category
            </CardTitle>
            <ul className="space-y-2.5">
              {state.categories.map((cat) => (
                <li key={cat.category} className="flex items-center gap-2.5 text-[12.5px]">
                  <span className="text-slate2 w-36 truncate">{cat.category}</span>
                  <div className="flex-1 h-1.5 rounded-full bg-line overflow-hidden">
                    <div className="h-full bg-primary rounded-full"
                      style={{ width: `${cat.total ? (cat.answered / cat.total) * 100 : 0}%` }} />
                  </div>
                  <span className="font-bold text-navy w-9 text-right">{cat.answered} / {cat.total}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="card-pad">
            <CardTitle tip="Verified figures from your locked financial statements.">Financial Context <span className="text-xs text-slate3 font-medium">(from locked financials)</span></CardTitle>
            <div className="grid grid-cols-2 gap-3">
              {[
                [`Revenue (${fc.latest_period ?? "latest"})`, fmtCr(fc.revenue_latest)],
                ["Revenue CAGR (3Y)", fmtPct(fc.revenue_cagr)],
                ["EBITDA Margin", fmtPct(fc.ebitda_margin)],
                ["Net Profit", fmtCr(fc.pat_latest)],
              ].map(([label, v]) => (
                <div key={label as string} className="rounded-xl border border-line bg-page/50 p-3">
                  <p className="text-[11px] text-slate3">{label}</p>
                  <p className="text-[15px] font-extrabold text-navy mt-0.5">{v}</p>
                  <svg viewBox="0 0 60 14" className="mt-1.5 w-16 h-3.5 text-primary">
                    <polyline fill="none" stroke="currentColor" strokeWidth="1.6"
                      points="0,12 10,10 20,11 30,7 40,8 50,4 60,2" />
                  </svg>
                </div>
              ))}
            </div>
          </div>

          <div className="card-pad bg-gradient-to-br from-primary-50/70 to-surface">
            <CardTitle icon={<Sparkles size={15} className="text-primary" />}>AI Interpretation <span className="text-xs text-slate3 font-medium">(so far)</span></CardTitle>
            <p className="text-[13px] text-slate2 leading-relaxed">{state.interpretation_so_far}</p>
            {state.answers.length > 0 && (
              <span className={`mt-3 ${state.answers[state.answers.length - 1].signal === "positive" ? "chip-mint" : state.answers[state.answers.length - 1].signal === "negative" ? "chip-risk" : "chip-blue"} flex w-fit items-center gap-1`}>
                <TrendingUp size={11} /> {state.answers[state.answers.length - 1].signal.charAt(0).toUpperCase() + state.answers[state.answers.length - 1].signal.slice(1)} Signal
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
