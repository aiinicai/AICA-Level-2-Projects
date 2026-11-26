// One place to bring a year's data: choose the clauses, fetch from Tally once (or choose files), then each
// clause takes what it needs from the same file, one after the other.
import { useRef, useState } from "react";
import { CheckCircle2, Database, UploadCloud, X } from "lucide-react";
import { Alert, Button, Card, cn } from "@/components/ui";
import { TallyFetch } from "@/components/c31/TallyFetch";
import { UploadWizard } from "@/components/c44/UploadWizard";
import { C31Upload } from "@/components/c31/C31Upload";
import { useParties, useRows } from "@/hooks/useModuleData";
import { ACCEPTED_FILES } from "@/lib/import/parseFile";
import { bundleFiles } from "@/lib/import/bundle";

type Clause = "c44" | "c31";
const CLAUSES: [Clause, string, string][] = [
  ["c44", "Clause 44", "GST break-up of expenditure"],
  ["c31", "Clause 31", "Loans and deposits · 269SS / 269T"],
];

interface Props { eng: any; client: any; initialFile?: File | null; onClose: () => void; onDone: (last: Clause) => void }

export function YearImport({ eng, client, initialFile, onClose, onDone }: Props) {
  const [pick, setPick] = useState<Record<Clause, boolean>>({ c44: true, c31: true });
  const [file, setFile] = useState<File | null>(initialFile ?? null);
  const [step, setStep] = useState(0);
  const [result, setResult] = useState<Record<string, "done" | "skipped">>({});
  const [drag, setDrag] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const { ensure } = useParties(eng.client_id);
  const bals = useRows<{ id: string; normalized_name: string }>("loan_balances", eng.id, "party_name");
  const chosen = CLAUSES.map(([k]) => k).filter((k) => pick[k]);
  const current = chosen[step];

  const next = (how: "done" | "skipped") => {
    const r = { ...result, [current]: how };
    setResult(r);
    if (step + 1 < chosen.length) setStep(step + 1);
    else onDone(([...chosen].reverse().find((c) => r[c] === "done") ?? chosen[0]) as Clause);
  };
  const take = async (list: File[] | FileList) => { const f = await bundleFiles(list); if (f) { setFile(f); setStep(0); setResult({}); } };

  return (
    <Card className="p-5">
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 text-lg font-semibold"><Database className="h-5 w-5 text-navy-600" />Bring data for AY {eng.assessment_year}</div>
          <p className="text-sm text-slate-600">Choose the clauses, then bring the data once – from Tally or from files. Each clause takes what it needs from it.</p>
        </div>
        <Button variant="ghost" size="sm" icon={<X className="h-4 w-4" />} onClick={onClose}>Close</Button>
      </div>

      {!file ? (
        <div className="space-y-4">
          <div>
            <div className="mb-2 text-sm font-semibold">Which clauses do you want to prepare?</div>
            <div className="grid gap-2 sm:grid-cols-2">
              {CLAUSES.map(([k, t, d]) => (
                <label key={k} className={cn("flex cursor-pointer items-start gap-3 rounded-xl border p-3", pick[k] ? "border-navy-900 bg-navy-50 ring-1 ring-navy-900" : "border-slate-200")}>
                  <input type="checkbox" className="mt-0.5 h-4 w-4 accent-navy-900" checked={pick[k]} onChange={(e) => setPick({ ...pick, [k]: e.target.checked })} />
                  <span><span className="block text-sm font-semibold">{t}</span><span className="text-xs text-slate-500">{d}</span></span>
                </label>
              ))}
            </div>
          </div>
          {!chosen.length ? <Alert tone="warn">Choose at least one clause.</Alert> : (<>
            <TallyFetch key={chosen.join()} ay={eng.assessment_year} clientName={client?.name ?? ""} modes={pick.c44 ? ["daybook"] : ["loans", "daybook"]} onFile={(f) => take([f])} />
            <div onClick={() => fileRef.current?.click()} onDragOver={(e) => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)}
              onDrop={(e) => { e.preventDefault(); setDrag(false); take(e.dataTransfer.files); }}
              className={cn("flex cursor-pointer flex-col items-center rounded-2xl border-2 border-dashed px-6 py-8 text-center", drag ? "border-navy-500 bg-navy-50" : "border-slate-300 hover:border-navy-400 hover:bg-slate-50")}>
              <UploadCloud className="h-10 w-10 text-navy-600" />
              <div className="mt-2 font-semibold">Or choose files</div>
              <div className="mt-1 max-w-xl text-sm text-slate-500">Tally Day Book and Masters XML (together), a ZIP, or Excel / CSV ledgers – several files at once.</div>
              <input ref={fileRef} type="file" multiple accept={ACCEPTED_FILES} className="hidden" onChange={(e) => { const l: File[] = e.target.files ? Array.from(e.target.files) : []; e.target.value = ""; take(l); }} />
            </div>
          </>)}
        </div>
      ) : (
        <div>
          <div className="mb-4 flex flex-wrap items-center gap-2">
            {chosen.map((c, i) => {
              const r = result[c];
              return (
                <span key={c} className={cn("inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold",
                  i === step ? "border-navy-900 bg-navy-950 text-white" : r === "done" ? "border-emerald-200 bg-emerald-50 text-emerald-800" : "border-slate-200 text-slate-500")}>
                  {r === "done" && <CheckCircle2 className="h-3.5 w-3.5" />}{i + 1}. {CLAUSES.find(([k]) => k === c)![1]}{r === "skipped" ? " (skipped)" : ""}
                </span>);
            })}
            <span className="ml-auto text-xs text-slate-500">{file.name}</span>
            <Button variant="ghost" size="sm" onClick={() => next("skipped")}>Skip this clause</Button>
          </div>
          {current === "c44" && <UploadWizard key={`c44-${file.name}`} engagement={eng} clientId={eng.client_id} clientName={client?.name ?? ""} incoming={file} onDone={() => next("done")} />}
          {current === "c31" && <C31Upload key={`c31-${file.name}`} eng={eng} clientId={eng.client_id} clientName={client?.name ?? ""} incoming={file} ensureParties={ensure}
            existingOpenings={Object.fromEntries(bals.rows.map((b) => [b.normalized_name, b.id]))} onDone={() => next("done")} />}
        </div>
      )}
    </Card>
  );
}
