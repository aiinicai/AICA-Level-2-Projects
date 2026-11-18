import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { validateGstin } from "@/lib/gst/gstin";
import type { Firm } from "@/lib/store";
import { Term } from "./common";

export function FirmForm({ value, onChange }: { value: Firm; onChange: (f: Firm) => void }) {
  const g = value.gstin ? validateGstin(value.gstin) : null;
  const field = (k: keyof Firm, label: string, ph: string) => (
    <div className="space-y-1.5">
      <Label htmlFor={k}>{label}</Label>
      <Input id={k} value={value[k]} placeholder={ph} onChange={(e) => onChange({ ...value, [k]: e.target.value })} />
    </div>
  );
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {field("name", "Firm name", "e.g. Shah & Co, Chartered Accountants")}
      {field("frn", "Firm registration number (FRN)", "e.g. 123456W")}
      {field("partner", "Your name", "e.g. CA Priya Shah")}
      {field("city", "City", "e.g. Ahmedabad")}
      <div className="space-y-1.5 sm:col-span-2">
        <Label htmlFor="gstin"><Term k="GSTIN">Firm GSTIN (optional)</Term></Label>
        <Input id="gstin" className="font-mono uppercase" value={value.gstin} maxLength={15} placeholder="15 characters" onChange={(e) => onChange({ ...value, gstin: e.target.value.toUpperCase() })} />
        {g && <p className={`text-xs ${g.valid ? "text-success" : "text-destructive"}`}>{g.valid ? "GSTIN looks valid (check digit matches)." : g.reason}</p>}
      </div>
    </div>
  );
}
