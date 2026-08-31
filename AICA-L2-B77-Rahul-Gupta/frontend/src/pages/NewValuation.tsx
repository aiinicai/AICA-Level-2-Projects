import { useMemo, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import {
  Building2, Calendar, IndianRupee, Hash, Globe2, Target, User2, PieChart,
  ArrowRight, Check, Sparkles, ShieldCheck, Landmark, Tag, Percent,
  Scale, ClipboardCheck, Lightbulb, UploadCloud, FileText, CheckCircle2,
  AlertTriangle, Loader2,
} from "lucide-react";
import { api, fiscalYearFromFilename, fmtFileSize } from "../services/api";
import { useCase } from "../hooks/useCase";
import { ProgressRing } from "../components/ui";
import type { CaseSummary, DocumentInfo } from "../types";

const schema = z.object({
  company_name: z.string().min(2, "Company name is required"),
  industry: z.string().min(1),
  entity_type: z.string().min(1),
  valuation_date: z.string().min(1, "Valuation date is required"),
  currency: z.string().min(1),
  units: z.string().min(1),
  purpose: z.string().min(1),
  country: z.string().min(1),
  promoter_holding_pct: z.coerce.number().min(0).max(100),
  total_shares: z.coerce.number().min(1, "Total diluted shares are required"),
  notes: z.string().optional().default(""),
});
type FormData = z.infer<typeof schema>;

const INDUSTRIES = ["Food & Beverages", "Textiles", "Retail", "Renewable Energy",
  "Industrial Goods", "IT Services", "Pharmaceuticals", "Logistics", "Other"];
const PURPOSES = ["Internal Management Assessment", "Fund Raising", "Investment Assessment",
  "Strategic Planning", "Acquisition Analysis", "Other"];
const ENTITY_TYPES = ["Private Limited Company", "Public Limited Company", "LLP",
  "Partnership Firm", "Proprietorship"];

const STEPS = [
  { n: 1, title: "Basic Information", sub: "Company & Valuation Details" },
  { n: 2, title: "Financial Inputs", sub: "Upload or Connect Data" },
  { n: 3, title: "Valuation Methods", sub: "Select Approaches" },
  { n: 4, title: "Review & Create", sub: "Confirm and Create Case" },
];

export default function NewValuation() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { setActiveCaseId } = useCase();
  const [step, setStep] = useState(1);
  const [methods, setMethods] = useState({ dcf: true, market_multiple: true, adjusted_nav: true });

  const [caseId, setCaseId] = useState<string | null>(null);
  const [docs, setDocs] = useState<DocumentInfo[]>([]);
  const [processing, setProcessing] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  const { register, handleSubmit, watch, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      company_name: "", industry: "Food & Beverages", entity_type: "Private Limited Company",
      valuation_date: new Date().toISOString().slice(0, 10), currency: "INR", units: "crore",
      purpose: "Fund Raising", country: "India", promoter_holding_pct: 74.5,
      total_shares: 1000000, notes: "",
    },
  });
  const values = watch();

  // Case is created right after Step 1 (instead of at the end) so Step 2 has a
  // case id to upload documents against — the backend has no pre-case staging endpoint.
  const createCase = useMutation({
    mutationFn: (data: FormData) => api.post<CaseSummary>("/api/valuations", data),
    onSuccess: (created) => {
      // Push the new case into the cache synchronously (not just invalidate) so
      // useCase's reconciliation effect sees it immediately — otherwise it still
      // has the stale case list, decides the new id "doesn't exist", and reverts
      // activeCaseId back to the seeded demo case before the refetch lands.
      qc.setQueryData<CaseSummary[]>(["cases"], (old) => [...(old ?? []), created]);
      qc.invalidateQueries({ queryKey: ["cases"] });
      setCaseId(created.id);
      setActiveCaseId(created.id);
      setStep(2);
    },
  });

  const upload = useMutation({
    mutationFn: async (files: File[]) => {
      setUploadError("");
      setProcessing(true);
      const uploaded: DocumentInfo[] = [];
      const failures: string[] = [];
      // per-file try/catch: one bad file must not discard the others already uploaded
      for (const file of files) {
        const fy = fiscalYearFromFilename(file.name);
        const form = new FormData();
        form.append("file", file);
        form.append("fiscal_year_label", fy);
        try {
          const doc = await api.upload<DocumentInfo>(`/api/valuations/${caseId}/documents`, form);
          await api.post(`/api/documents/${doc.id}/process`);
          uploaded.push(doc);
        } catch (err) {
          failures.push(`${file.name}: ${(err as Error).message}`);
        }
      }
      return { uploaded, failures };
    },
    onSuccess: ({ uploaded, failures }) => {
      setDocs((prev) => [...prev, ...uploaded]);
      setUploadError(failures.join(" · "));
    },
    onSettled: () => setProcessing(false),
    onError: (e: Error) => setUploadError(e.message),
  });

  const finalize = useMutation({
    mutationFn: async () => {
      const w = {
        weight_dcf: methods.dcf ? 0.5 : 0,
        weight_market_multiple: methods.market_multiple ? 0.3 : 0,
        weight_adjusted_nav: methods.adjusted_nav ? 0.2 : 0,
      };
      const total = w.weight_dcf + w.weight_market_multiple + w.weight_adjusted_nav;
      if (total > 0 && total !== 1) {
        (Object.keys(w) as (keyof typeof w)[]).forEach((k) => (w[k] = w[k] / total));
      }
      await api.put(`/api/valuations/${caseId}/assumptions`, { values: w });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cases"] });
      navigate("/financials");
    },
  });

  const readinessPct = useMemo(() => {
    let filled = 0;
    const req = ["company_name", "industry", "valuation_date", "purpose", "total_shares"] as const;
    req.forEach((k) => { if (values[k]) filled += 1; });
    return Math.min(65, Math.round((filled / req.length) * 65));
  }, [values]);

  const saveAndContinue = handleSubmit((d) => {
    if (caseId) { setStep(2); return; }
    createCase.mutate(d);
  });

  const next = () => setStep((s) => Math.min(4, s + 1));

  const field = (
    name: keyof FormData, label: string, icon: React.ReactNode, help: string,
    input: React.ReactNode,
  ) => (
    <div>
      <label className="label">{label} <span className="text-risk">*</span></label>
      <div className="relative">
        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate3">{icon}</span>
        {input}
      </div>
      {errors[name] ? (
        <p className="help-text !text-risk-text">{String(errors[name]?.message)}</p>
      ) : (
        <p className="help-text">{help}</p>
      )}
    </div>
  );

  const selectCls = "input pl-9 appearance-none";

  return (
    <div className="grid grid-cols-12 gap-5 items-start">
      <div className="col-span-9 space-y-5">
        {/* stepper */}
        <div className="card px-6 py-5">
          <div className="flex items-center">
            {STEPS.map((s, i) => (
              <div key={s.n} className="flex items-center flex-1 last:flex-none">
                <div className="flex items-center gap-3">
                  <span className={`h-9 w-9 rounded-full flex items-center justify-center text-sm font-bold ${
                    step > s.n ? "bg-mint text-white" : step === s.n ? "bg-primary text-white" : "bg-page text-slate3 border border-line"}`}>
                    {step > s.n ? <Check size={16} /> : s.n}
                  </span>
                  <div>
                    <p className={`text-[13px] font-bold ${step >= s.n ? "text-primary" : "text-slate3"}`}>{s.title}</p>
                    <p className="text-[11px] text-slate3">{s.sub}</p>
                  </div>
                </div>
                {i < STEPS.length - 1 && (
                  <div className="flex-1 border-t-2 border-dashed border-line mx-4" />
                )}
              </div>
            ))}
          </div>
        </div>

        {step === 1 && (
          <div className="card p-6">
            <p className="text-xs font-semibold text-slate3">Step 1 of 4</p>
            <h2 className="text-lg font-extrabold text-navy mt-0.5">Basic Information</h2>
            <p className="text-sm text-slate2 mb-6">Provide key details about the company and valuation case.</p>

            <div className="grid grid-cols-3 gap-x-5 gap-y-5">
              {field("company_name", "Company Name", <Building2 size={15} />, "Legal name of the company",
                <input className="input pl-9" placeholder="ABC Food Pvt. Ltd." {...register("company_name")} />)}
              {field("industry", "Industry", <Tag size={15} />, "Primary industry classification",
                <select className={selectCls} {...register("industry")}>{INDUSTRIES.map((x) => <option key={x}>{x}</option>)}</select>)}
              {field("entity_type", "Entity Type", <Landmark size={15} />, "Legal structure of the entity",
                <select className={selectCls} {...register("entity_type")}>{ENTITY_TYPES.map((x) => <option key={x}>{x}</option>)}</select>)}
              {field("valuation_date", "Valuation Date", <Calendar size={15} />, "Valuation reference date",
                <input type="date" className="input pl-9" {...register("valuation_date")} />)}
              {field("currency", "Currency", <IndianRupee size={15} />, "Currency for valuation",
                <select className={selectCls} {...register("currency")}><option value="INR">Indian Rupee (INR)</option></select>)}
              {field("units", "Units", <Hash size={15} />, "Units for financials & output",
                <select className={selectCls} {...register("units")}>
                  <option value="crore">Crore (₹ Cr)</option><option value="lakh">Lakh (₹ L)</option>
                </select>)}
              {field("purpose", "Valuation Purpose", <Target size={15} />, "Primary purpose of valuation",
                <select className={selectCls} {...register("purpose")}>{PURPOSES.map((x) => <option key={x}>{x}</option>)}</select>)}
              {field("country", "Country of Operations", <Globe2 size={15} />, "Primary country of operations",
                <select className={selectCls} {...register("country")}><option>India</option><option>Other</option></select>)}
              {field("promoter_holding_pct", "Promoter Holding (%)", <User2 size={15} />, "Current promoter shareholding",
                <input type="number" step="0.01" className="input pl-9" {...register("promoter_holding_pct")} />)}
              {field("total_shares", "Total Shares (Fully Diluted)", <PieChart size={15} />, "Total diluted shares count",
                <input type="number" className="input pl-9" {...register("total_shares")} />)}
              <div className="col-span-2">
                <label className="label">Notes <span className="text-slate3 font-medium">(Optional)</span></label>
                <textarea rows={3} className="input resize-none"
                  placeholder="Additional context or special notes (optional)" {...register("notes")} />
                <p className="help-text">Additional context or special notes (optional)</p>
              </div>
            </div>

            {createCase.isError && (
              <p className="mt-4 text-sm text-risk-text">{(createCase.error as Error).message}</p>
            )}
            <div className="mt-6 flex items-center justify-between rounded-xl bg-primary-50/60 border border-primary-100/50 px-4 py-3">
              <p className="text-[12.5px] text-slate2 flex items-center gap-2">
                <Lightbulb size={14} className="text-warn" />
                <span><b className="text-navy">Tip</b> — Accurate inputs lead to more reliable valuations. You can update or refine these details later in the case settings.</span>
              </p>
              <button className="btn-primary" onClick={saveAndContinue} disabled={createCase.isPending}>
                {createCase.isPending ? "Creating…" : <>Save & Continue <ArrowRight size={15} /></>}
              </button>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="card p-6">
            <p className="text-xs font-semibold text-slate3">Step 2 of 4</p>
            <h2 className="text-lg font-extrabold text-navy mt-0.5">Financial Inputs</h2>
            <p className="text-sm text-slate2 mb-6">Upload the last 3 years of financial statements. Python extraction + Gemini visual verification run automatically after upload.</p>
            <button
              type="button"
              onClick={() => fileRef.current?.click()}
              disabled={processing}
              className="w-full rounded-xl border-2 border-dashed border-line bg-page/50 p-10 text-center hover:border-primary/60 hover:bg-primary-50/40 transition disabled:opacity-60"
            >
              {processing
                ? <Loader2 size={34} className="mx-auto text-primary animate-spin" />
                : <UploadCloud size={34} className="mx-auto text-primary" />}
              <p className="font-semibold text-navy mt-3">
                {processing ? "Processing documents…" : "Upload last 3 years of financial statements"}
              </p>
              <p className="text-sm text-slate2 mt-1">
                PDF, XLSX or XLS up to 25MB each. {!processing && <span className="text-primary">Click to browse.</span>}
              </p>
            </button>
            <input ref={fileRef} type="file" multiple accept=".pdf,.xlsx,.xls" className="hidden"
              onChange={(e) => {
                const picked = Array.from(e.target.files ?? []);
                // reset first (snapshot above) so re-picking the same filename still fires onChange
                e.target.value = "";
                if (picked.length) upload.mutate(picked);
              }} />
            {uploadError && <p className="mt-2 text-xs text-risk-text">{uploadError}</p>}

            {docs.length > 0 && (
              <div className="grid grid-cols-3 gap-2.5 mt-4">
                {docs.map((d) => (
                  <div key={d.id} className="rounded-lg border border-line bg-surface p-2.5">
                    <div className="flex items-center justify-between">
                      <FileText size={15} className="text-risk" />
                      {d.status === "failed"
                        ? <AlertTriangle size={14} className="text-risk" />
                        : <CheckCircle2 size={14} className="text-mint" />}
                    </div>
                    <p className="text-[11px] font-bold text-navy mt-1.5 truncate">{d.fiscal_year_label || d.original_filename}</p>
                    <p className="text-[10px] text-slate3 truncate">{d.original_filename}</p>
                    <p className="text-[10px] text-slate3">{fmtFileSize(d.size_bytes)}</p>
                  </div>
                ))}
              </div>
            )}
            <p className="text-xs text-slate3 mt-3">You can also skip this step and upload documents later from the Financials workspace.</p>
            <div className="mt-6 flex justify-between">
              <button className="btn-secondary" onClick={() => setStep(1)}>Back</button>
              <button className="btn-primary" onClick={next}>Continue <ArrowRight size={15} /></button>
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="card p-6">
            <p className="text-xs font-semibold text-slate3">Step 3 of 4</p>
            <h2 className="text-lg font-extrabold text-navy mt-0.5">Valuation Methods</h2>
            <p className="text-sm text-slate2 mb-6">Select the approaches for this case. Weights can be refined later; they must total 100%.</p>
            <div className="grid grid-cols-3 gap-4">
              {[
                { key: "dcf", title: "Discounted Cash Flow", sub: "5-year FCFF projection with Gordon terminal value", w: "50%", icon: <Scale size={18} /> },
                { key: "market_multiple", title: "Market Multiple", sub: "EV/EBITDA on normalised earnings", w: "30%", icon: <Percent size={18} /> },
                { key: "adjusted_nav", title: "Adjusted NAV", sub: "Book net worth with asset revaluations", w: "20%", icon: <Landmark size={18} /> },
              ].map((m) => {
                const on = methods[m.key as keyof typeof methods];
                return (
                  <button key={m.key}
                    onClick={() => setMethods((s) => ({ ...s, [m.key]: !on }))}
                    className={`text-left rounded-xl2 border-2 p-4 transition ${on ? "border-primary bg-primary-50/50" : "border-line bg-surface hover:bg-page"}`}>
                    <div className="flex items-center justify-between">
                      <span className={`h-10 w-10 rounded-xl flex items-center justify-center ${on ? "bg-primary text-white" : "bg-page text-slate2"}`}>{m.icon}</span>
                      {on && <Check size={17} className="text-primary" />}
                    </div>
                    <p className="font-bold text-navy mt-3">{m.title}</p>
                    <p className="text-xs text-slate2 mt-1">{m.sub}</p>
                    <p className="text-xs font-bold text-primary mt-2">Default weight {m.w}</p>
                  </button>
                );
              })}
            </div>
            <div className="mt-6 flex justify-between">
              <button className="btn-secondary" onClick={() => setStep(2)}>Back</button>
              <button className="btn-primary" onClick={next} disabled={!Object.values(methods).some(Boolean)}>
                Continue <ArrowRight size={15} />
              </button>
            </div>
          </div>
        )}

        {step === 4 && (
          <div className="card p-6">
            <p className="text-xs font-semibold text-slate3">Step 4 of 4</p>
            <h2 className="text-lg font-extrabold text-navy mt-0.5">Review & Create</h2>
            <p className="text-sm text-slate2 mb-6">Confirm the case details. Documents, verification, interview and valuation follow next.</p>
            <div className="grid grid-cols-2 gap-x-8 gap-y-3 text-sm max-w-2xl">
              {[
                ["Company", values.company_name || "—"], ["Industry", values.industry],
                ["Entity Type", values.entity_type], ["Valuation Date", values.valuation_date],
                ["Currency / Units", `${values.currency} · ${values.units === "crore" ? "₹ Crore" : "₹ Lakh"}`],
                ["Purpose", values.purpose], ["Country", values.country],
                ["Promoter Holding", `${values.promoter_holding_pct}%`],
                ["Total Shares (Diluted)", Number(values.total_shares).toLocaleString("en-IN")],
                ["Methods", Object.entries(methods).filter(([, v]) => v).map(([k]) =>
                  ({ dcf: "DCF", market_multiple: "Market Multiple", adjusted_nav: "Adjusted NAV" }[k])).join(", ")],
              ].map(([k, v]) => (
                <div key={k as string} className="flex justify-between gap-6 border-b border-line/60 pb-2">
                  <span className="text-slate2">{k}</span>
                  <span className="font-semibold text-navy text-right">{v}</span>
                </div>
              ))}
            </div>
            {finalize.isError && (
              <p className="mt-4 text-sm text-risk-text">{(finalize.error as Error).message}</p>
            )}
            <div className="mt-6 flex justify-between">
              <button className="btn-secondary" onClick={() => setStep(3)}>Back</button>
              <button className="btn-primary" onClick={() => finalize.mutate()} disabled={finalize.isPending}>
                <Sparkles size={15} /> {finalize.isPending ? "Finalizing…" : "Create Valuation"}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* right summary */}
      <div className="col-span-3 space-y-4">
        <div className="card-pad">
          <h3 className="section-title mb-1">Valuation Case Summary</h3>
          <p className="text-xs text-slate3 mb-4">Review your inputs before proceeding.</p>
          <ul className="space-y-2.5 text-[12.5px]">
            {[
              [<Building2 size={13} key="i" />, "Company", values.company_name || "—"],
              [<Tag size={13} key="i" />, "Industry", values.industry],
              [<Landmark size={13} key="i" />, "Entity Type", values.entity_type.replace(" Company", "")],
              [<Calendar size={13} key="i" />, "Valuation Date", values.valuation_date],
              [<IndianRupee size={13} key="i" />, "Currency", values.currency],
              [<Hash size={13} key="i" />, "Units", values.units === "crore" ? "₹ Crore" : "₹ Lakh"],
              [<Target size={13} key="i" />, "Purpose", values.purpose.split(" ")[0] + (values.purpose.includes(" ") ? " " + values.purpose.split(" ")[1] : "")],
              [<Globe2 size={13} key="i" />, "Country", values.country],
              [<User2 size={13} key="i" />, "Promoter Holding", `${values.promoter_holding_pct}%`],
              [<PieChart size={13} key="i" />, "Total Shares (Diluted)", Number(values.total_shares || 0).toLocaleString("en-IN")],
            ].map(([icon, k, v], i) => (
              <li key={i} className="flex items-center gap-2">
                <span className="text-slate3">{icon}</span>
                <span className="text-slate2">{k}</span>
                <span className="ml-auto font-semibold text-navy text-right truncate max-w-[120px]">{v}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="card-pad">
          <div className="flex items-center gap-3 mb-3">
            <ProgressRing value={readinessPct + (step - 1) * 10} size={54} stroke={6}>
              <span className="text-[11px] font-extrabold text-navy">{Math.min(readinessPct + (step - 1) * 10, 95)}%</span>
            </ProgressRing>
            <div>
              <p className="text-[13px] font-bold text-navy">Case Readiness</p>
              <p className="text-[11px] text-slate3">Complete the next steps to create your valuation case.</p>
            </div>
          </div>
          <ul className="space-y-2 text-[12.5px]">
            {STEPS.map((s) => (
              <li key={s.n} className="flex items-center gap-2">
                <span className={`h-4.5 w-4.5 h-[18px] w-[18px] rounded-full flex items-center justify-center ${step > s.n ? "bg-mint text-white" : "border-2 border-line"}`}>
                  {step > s.n && <Check size={11} />}
                </span>
                <span className={step >= s.n ? "text-navy font-semibold" : "text-slate3"}>{s.title}</span>
              </li>
            ))}
          </ul>
          <button className="btn-primary w-full mt-4" onClick={() => finalize.mutate()} disabled={finalize.isPending || step < 4}>
            <Sparkles size={15} /> Create Valuation
          </button>
          <p className="mt-3 text-[11px] text-slate3 flex items-center gap-1.5">
            <ShieldCheck size={13} className="text-mint-text" /> Your data is secure and encrypted end-to-end.
          </p>
        </div>
      </div>
    </div>
  );
}
