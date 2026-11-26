import { FormEvent, useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import { useFirm } from "@/contexts/FirmContext";
import { useToast } from "@/components/Toast";
import { Alert, Button, Field, Input, Modal, Select, Textarea } from "@/components/ui";
import { CLIENT_STATUSES, errMsg, logActivity } from "@/lib/db";
import { cleanGstin, isValidGstin, isValidPan, panFromGstin } from "@/lib/validators";

export interface ClientRecord {
  id?: string;
  name: string;
  pan: string | null;
  gstins: string[];
  status: string;
  address: string | null;
  contact_person: string | null;
  email: string | null;
  mobile: string | null;
  notes: string | null;
  archived?: boolean;
  created_by?: string;
  created_at?: string;
  updated_by?: string;
  updated_at?: string;
}

export const emptyClient = (): ClientRecord => ({ name: "", pan: "", gstins: [], status: "Individual", address: "", contact_person: "", email: "", mobile: "", notes: "" });

export function ClientForm({ client, onClose, onSaved }: { client: ClientRecord; onClose: () => void; onSaved: (id: string, isNew: boolean) => void }) {
  const { firm } = useFirm();
  const toast = useToast();
  const [c, setC] = useState<ClientRecord>({ ...client });
  const [gstText, setGstText] = useState((client.gstins ?? []).join(", "));
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");
  const set = (k: keyof ClientRecord) => (e: { target: { value: string } }) => setC((s) => ({ ...s, [k]: e.target.value }));

  const gstins = gstText.split(/[,;\s]+/).map(cleanGstin).filter(Boolean);
  const badGst = gstins.filter((g) => !isValidGstin(g));
  const pan = (c.pan ?? "").toUpperCase().trim();
  const panMismatch = pan && gstins.some((g) => isValidGstin(g) && panFromGstin(g) !== pan);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!firm) return;
    if (pan && !isValidPan(pan)) { setErr("PAN must be in the format AAAAA9999A."); return; }
    setSaving(true); setErr("");
    const payload = {
      name: c.name.trim(), pan: pan || null, gstins, status: c.status, address: c.address || null,
      contact_person: c.contact_person || null, email: c.email || null, mobile: c.mobile || null, notes: c.notes || null,
    };
    const isNew = !c.id;
    const res = isNew
      ? await supabase.from("clients").insert({ ...payload, firm_id: firm.id }).select("id").single()
      : await supabase.from("clients").update(payload).eq("id", c.id!).select("id").single();
    setSaving(false);
    if (res.error) { setErr(errMsg(res.error)); return; }
    await logActivity(firm.id, isNew ? "client.created" : "client.updated", "client", res.data.id, { name: payload.name });
    toast(isNew ? "Client added" : "Client updated");
    onSaved(res.data.id, isNew);
  };

  return (
    <Modal open onClose={onClose} title={c.id ? "Edit client" : "Add client"} wide
      footer={<><Button variant="ghost" onClick={onClose}>Cancel</Button><Button type="submit" form="client-form" loading={saving}>{c.id ? "Save changes" : "Add client"}</Button></>}>
      <form id="client-form" onSubmit={submit} className="grid gap-4 sm:grid-cols-2">
        <Field label="Client / Assessee name" required className="sm:col-span-2"><Input value={c.name} onChange={set("name")} required autoFocus /></Field>
        <Field label="PAN" error={pan && !isValidPan(pan) ? "Format: AAAAA9999A" : undefined}>
          <Input value={c.pan ?? ""} onChange={(e) => setC((s) => ({ ...s, pan: e.target.value.toUpperCase() }))} maxLength={10} className="font-mono uppercase" />
        </Field>
        <Field label="Status">
          <Select value={c.status} onChange={set("status")}>{CLIENT_STATUSES.map((s) => <option key={s}>{s}</option>)}</Select>
        </Field>
        <Field label="GSTIN(s)" hint="Separate multiple GSTINs with commas" className="sm:col-span-2"
          error={badGst.length ? `Invalid: ${badGst.join(", ")}` : panMismatch ? "GSTIN does not match the PAN" : undefined}>
          <Input value={gstText} onChange={(e) => setGstText(e.target.value.toUpperCase())} className="font-mono uppercase" />
        </Field>
        <Field label="Contact person"><Input value={c.contact_person ?? ""} onChange={set("contact_person")} /></Field>
        <Field label="Mobile"><Input value={c.mobile ?? ""} onChange={set("mobile")} inputMode="tel" /></Field>
        <Field label="Email" className="sm:col-span-2"><Input type="email" value={c.email ?? ""} onChange={set("email")} /></Field>
        <Field label="Address" className="sm:col-span-2"><Textarea value={c.address ?? ""} onChange={set("address")} rows={2} /></Field>
        <Field label="Notes" className="sm:col-span-2"><Textarea value={c.notes ?? ""} onChange={set("notes")} rows={2} /></Field>
        {err && <Alert tone="error" className="sm:col-span-2">{err}</Alert>}
      </form>
    </Modal>
  );
}
