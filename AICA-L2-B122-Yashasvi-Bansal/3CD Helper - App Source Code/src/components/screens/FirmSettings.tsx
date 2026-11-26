import { FormEvent, useEffect, useState } from "react";
import { Copy, Download, ExternalLink, HardDrive } from "lucide-react";
import { DRIVE_MANIFEST, DRIVE_ROOT, OLD_SCRIPT_TEXT, driveScript, isDriveUrl, newDriveKey, testDrive } from "@/lib/driveScript";
import { supabase } from "@/integrations/supabase/client";
import { useFirm, Firm } from "@/contexts/FirmContext";
import { useToast } from "@/components/Toast";
import { Alert, Badge, Button, Card, CardHeader, Field, Input, PageHeader, Textarea } from "@/components/ui";
import { errMsg, isAdmin, logActivity } from "@/lib/db";
import { isValidGstin, isValidPan } from "@/lib/validators";
import { downloadClientTemplate, downloadExpenseTemplate } from "@/lib/export";
import { formatDate } from "@/lib/format";

export default function FirmSettings() {
  const { firm, role, refresh } = useFirm();
  const toast = useToast();
  const [f, setF] = useState<Partial<Firm>>({});
  const [busy, setBusy] = useState(false);
  useEffect(() => { if (firm) setF({ ...firm }); }, [firm?.id]);
  if (!firm) return null;
  const ro = !isAdmin(role);
  const set = (k: keyof Firm) => (e: { target: { value: string } }) => setF((s) => ({ ...s, [k]: e.target.value }));

  const save = async (e: FormEvent) => {
    e.preventDefault();
    if (f.gstin && !isValidGstin(f.gstin)) return toast("Firm GSTIN is not valid", "error");
    if (f.pan && !isValidPan(f.pan)) return toast("Firm PAN is not valid", "error");
    setBusy(true);
    const { error } = await supabase.from("firms").update({
      name: f.name, frn: f.frn || null, gstin: f.gstin || null, pan: f.pan || null, address: f.address || null, city: f.city || null,
      state: f.state || null, pincode: f.pincode || null, email: f.email || null, phone: f.phone || null,
      partner_name: f.partner_name || null, membership_no: f.membership_no || null,
    }).eq("id", firm.id);
    setBusy(false);
    if (error) return toast(errMsg(error), "error");
    await logActivity(firm.id, "firm.updated", "firm", firm.id);
    toast("Firm profile saved"); refresh();
  };

  return (
    <>
      <PageHeader title="Settings" subtitle="Firm profile shown on reports" />
      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader title="Firm profile" />
          <form onSubmit={save} className="grid gap-4 p-5 sm:grid-cols-2">
            {ro && <Alert tone="info" className="sm:col-span-2">Only the Owner or a Partner can edit firm details.</Alert>}
            <Field label="Firm name" required className="sm:col-span-2"><Input value={f.name ?? ""} onChange={set("name")} required disabled={ro} /></Field>
            <Field label="FRN"><Input value={f.frn ?? ""} onChange={set("frn")} disabled={ro} /></Field>
            <Field label="Firm PAN"><Input value={f.pan ?? ""} onChange={(e) => setF((s) => ({ ...s, pan: e.target.value.toUpperCase() }))} maxLength={10} disabled={ro} /></Field>
            <Field label="Firm GSTIN"><Input value={f.gstin ?? ""} onChange={(e) => setF((s) => ({ ...s, gstin: e.target.value.toUpperCase() }))} maxLength={15} disabled={ro} /></Field>
            <Field label="Phone"><Input value={f.phone ?? ""} onChange={set("phone")} disabled={ro} /></Field>
            <Field label="Partner / Proprietor"><Input value={f.partner_name ?? ""} onChange={set("partner_name")} disabled={ro} /></Field>
            <Field label="Membership No."><Input value={f.membership_no ?? ""} onChange={set("membership_no")} disabled={ro} /></Field>
            <Field label="Email" className="sm:col-span-2"><Input type="email" value={f.email ?? ""} onChange={set("email")} disabled={ro} /></Field>
            <Field label="Address" className="sm:col-span-2"><Textarea value={f.address ?? ""} onChange={set("address")} rows={2} disabled={ro} /></Field>
            <Field label="City"><Input value={f.city ?? ""} onChange={set("city")} disabled={ro} /></Field>
            <Field label="State"><Input value={f.state ?? ""} onChange={set("state")} disabled={ro} /></Field>
            <Field label="PIN code"><Input value={f.pincode ?? ""} onChange={set("pincode")} disabled={ro} /></Field>
            {!ro && <div className="sm:col-span-2"><Button type="submit" loading={busy}>Save changes</Button></div>}
          </form>
        </Card>
        <div className="space-y-6">
          <Card>
            <CardHeader title="Plan" />
            <div className="space-y-2 p-5 text-sm">
              <div className="flex items-center gap-2"><Badge className="bg-gold-400 text-navy-950">{firm.plan === "trial" ? "Pro trial" : firm.plan.toUpperCase()}</Badge></div>
              {firm.plan === "trial" && <p className="text-slate-600">Trial ends on {formatDate(firm.trial_ends_at)}.</p>}
              <p className="text-xs text-slate-500">Online billing (Razorpay) arrives in the next release.</p>
            </div>
          </Card>
          <DriveCard ro={ro} />
          <Card>
            <CardHeader title="Templates" />
            <div className="space-y-2 p-5">
              <Button variant="outline" className="w-full" icon={<Download className="h-4 w-4" />} onClick={downloadExpenseTemplate}>Clause 44 data template</Button>
              <Button variant="outline" className="w-full" icon={<Download className="h-4 w-4" />} onClick={downloadClientTemplate}>Client import template</Button>
            </div>
          </Card>
        </div>
      </div>
    </>
  );
}

/** Google Drive for client data: the script to put in the firm's Google account, and its address. */
function DriveCard({ ro }: { ro: boolean }) {
  const { firm, refresh } = useFirm();
  const toast = useToast();
  const [url, setUrl] = useState(firm?.settings?.drive_url ?? "");
  const [busy, setBusy] = useState("");
  const [open, setOpen] = useState(false);
  useEffect(() => { setUrl(firm?.settings?.drive_url ?? ""); }, [firm?.id, firm?.settings?.drive_url]);
  if (!firm) return null;
  const saved = firm.settings?.drive_url ?? "";
  const copyScript = async () => {
    // the firm's own read key goes into the script, so only this app can list and fetch the files
    let key = String(firm.settings?.drive_key ?? "");
    if (!key) {
      key = newDriveKey();
      const { error } = await supabase.from("firms").update({ settings: { ...(firm.settings ?? {}), drive_key: key } } as any).eq("id", firm.id);
      if (error) return toast(errMsg(error), "error");
      refresh();
    }
    const script = driveScript(String(import.meta.env.VITE_SUPABASE_URL ?? ""), String(import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY ?? ""), key);
    try { await navigator.clipboard.writeText(script); toast("Script copied", "success"); } catch { toast("Copy failed", "error"); }
  };
  const copyManifest = async () => { try { await navigator.clipboard.writeText(DRIVE_MANIFEST); toast("Settings file copied", "success"); } catch { toast("Copy failed", "error"); } };
  const save = async (value: string) => {
    const v = value.trim();
    if (v && !isDriveUrl(v)) return toast("Paste the Web app URL that ends with /exec", "error");
    setBusy("save");
    const t = v ? await testDrive(v) : "ok";
    if (t === "no") { setBusy(""); return toast("The script does not answer. Check that it is deployed as a Web app with access for Anyone.", "error"); }
    if (t === "old") { setBusy(""); return toast(OLD_SCRIPT_TEXT, "error"); }
    if (t === "no-drive") { setBusy(""); return toast("Drive access is not allowed yet: in the script editor choose \"setup\", press Run and allow access, then Deploy → Manage deployments → Edit → New version.", "error"); }
    const { error } = await supabase.from("firms").update({ settings: { ...(firm.settings ?? {}), drive_url: v || null } } as any).eq("id", firm.id);
    setBusy("");
    if (error) return toast(errMsg(error), "error");
    toast(v ? "Google Drive connected" : "Google Drive removed"); refresh();
  };
  return (
    <Card>
      <CardHeader title={<span className="inline-flex items-center gap-2"><HardDrive className="h-4 w-4 text-navy-600" />Google Drive for client data</span>} />
      <div className="space-y-3 p-5 text-sm">
        <p className="text-slate-600">Clients' Tally data can go straight to your own Google Drive (folder "{DRIVE_ROOT}"), instead of this app's storage. Free – no Cloud Console. The script can only reach the files it creates itself.</p>
        {saved ? <Badge className="bg-emerald-50 text-emerald-700">Connected</Badge> : <Badge className="bg-slate-100 text-slate-600">Not connected</Badge>}
        {!ro && <>
          <Button size="sm" variant="outline" onClick={() => setOpen(!open)}>{open ? "Hide the steps" : saved ? "Show the steps again" : "Set up (5 minutes)"}</Button>
          {open && (
            <ol className="list-decimal space-y-2 pl-5 text-slate-700">
              <li>Open <a className="font-medium text-navy-700 underline" href="https://script.google.com/home/projects/create" target="_blank" rel="noreferrer">script.google.com <ExternalLink className="inline h-3 w-3" /></a> with the Google account whose Drive should get the data. A new project opens.</li>
              <li>Delete what is in the editor, then <button type="button" className="font-medium text-navy-700 underline" onClick={copyScript}><Copy className="inline h-3 w-3" /> copy this script</button> and paste it there. Name the project "3CD Helper Drive" and save (Ctrl+S).</li>
              <li>Left side: <b>Project Settings</b> (gear) → tick "Show appsscript.json manifest file in editor". Back in the Editor open <b>appsscript.json</b>, delete what is in it, <button type="button" className="font-medium text-navy-700 underline" onClick={copyManifest}><Copy className="inline h-3 w-3" /> copy this settings file</button>, paste and save. It limits the script to <b>only the files it creates</b> – it cannot see or delete any other file in your Drive.</li>
              <li>Back in Code.gs, next to the Run button choose <b>setup</b> and press <b>Run</b>. Google asks for two permissions (files this app creates; connect to an external service): Review permissions → your account → Advanced → Go to 3CD Helper Drive → <b>Allow</b>.</li>
              <li>Deploy → New deployment → gear icon → Web app. Execute as: <b>Me</b>. Who has access: <b>Anyone</b>. Deploy. (After any change to the script: Deploy → Manage deployments → Edit → Version: New version → Deploy; the URL stays the same.)</li>
              <li>Copy the <b>Web app URL</b> (ends with /exec), paste it below and Save.</li>
            </ol>
          )}
          <Field label="Web app URL"><Input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://script.google.com/macros/s/…/exec" /></Field>
          <div className="flex gap-2">
            <Button size="sm" loading={busy === "save"} onClick={() => save(url)}>Save</Button>
            {saved && <Button size="sm" variant="ghost" onClick={() => save("")}>Remove</Button>}
          </div>
          <p className="text-xs text-slate-500">Then, on a client link, choose "Send to: my Google Drive". When a client sends data, the year's page shows "New data in Google Drive" – one click brings it in.</p>
        </>}
      </div>
    </Card>
  );
}
