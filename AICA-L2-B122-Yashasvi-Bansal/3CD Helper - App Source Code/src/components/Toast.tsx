import { createContext, useCallback, useContext, useState, ReactNode } from "react";
import { CheckCircle2, AlertTriangle, Info, X } from "lucide-react";
import { cn } from "./ui";

type Tone = "success" | "error" | "info";
interface T { id: number; tone: Tone; text: string }
const Ctx = createContext<(text: string, tone?: Tone) => void>(() => undefined);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [list, setList] = useState<T[]>([]);
  const push = useCallback((text: string, tone: Tone = "success") => {
    const id = Date.now() + Math.random();
    setList((l) => [...l, { id, tone, text }]);
    setTimeout(() => setList((l) => l.filter((x) => x.id !== id)), tone === "error" ? 7000 : 3500);
  }, []);
  return (
    <Ctx.Provider value={push}>
      {children}
      <div className="pointer-events-none fixed inset-x-0 bottom-20 z-[60] flex flex-col items-center gap-2 px-4 sm:bottom-6 sm:items-end">
        {list.map((t) => (
          <div key={t.id} className={cn("pointer-events-auto flex w-full max-w-sm items-start gap-3 rounded-xl border px-4 py-3 text-sm shadow-lg",
            t.tone === "success" && "border-emerald-200 bg-white text-slate-900",
            t.tone === "error" && "border-red-200 bg-red-50 text-red-900",
            t.tone === "info" && "border-navy-100 bg-white text-slate-900")}>
            {t.tone === "success" ? <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-600" /> : t.tone === "error" ? <AlertTriangle className="h-5 w-5 shrink-0 text-red-600" /> : <Info className="h-5 w-5 shrink-0 text-navy-600" />}
            <span className="flex-1">{t.text}</span>
            <button onClick={() => setList((l) => l.filter((x) => x.id !== t.id))} aria-label="Dismiss"><X className="h-4 w-4 text-slate-400" /></button>
          </div>
        ))}
      </div>
    </Ctx.Provider>
  );
}

export const useToast = () => useContext(Ctx);
