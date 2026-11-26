import { FormEvent, useState } from "react";
import { Navigate, useNavigate } from "@tanstack/react-router";
import { Building2 } from "lucide-react";
import { supabase } from "@/integrations/supabase/client";
import { useFirm } from "@/contexts/FirmContext";
import { useAuth } from "@/contexts/AuthContext";
import { Alert, Button, Card, Field, Input, PageLoader } from "@/components/ui";
import { Logo } from "@/components/Logo";
import { errMsg } from "@/lib/db";
import { isValidGstin } from "@/lib/validators";

export default function Onboarding() {
  const { firm, loading, refresh, switchFirm } = useFirm();
  const { user, signOut } = useAuth();
  const nav = useNavigate();
  const [f, setF] = useState({ name: "", frn: "", partner_name: "", membership_no: "", gstin: "", city: "", state: "", phone: "" });
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");

  if (loading) return <PageLoader />;
  if (firm && !saving) return <Navigate to="/app" replace />;

  const set = (k: keyof typeof f) => (e: { target: { value: string } }) => setF((s) => ({ ...s, [k]: e.target.value }));

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (f.gstin && !isValidGstin(f.gstin)) { setErr("Firm GSTIN is not valid."); return; }
    setSaving(true); setErr("");
    const { data, error } = await supabase.rpc("create_firm", {
      p_name: f.name, p_frn: f.frn || undefined, p_gstin: f.gstin || undefined, p_address: undefined, p_city: f.city || undefined,
      p_state: f.state || undefined, p_email: user?.email ?? undefined, p_phone: f.phone || undefined,
      p_partner_name: f.partner_name || undefined, p_membership_no: f.membership_no || undefined,
    });
    if (error) { setErr(errMsg(error)); setSaving(false); return; }
    switchFirm(data as string);
    await refresh();
    nav({ to: "/app", replace: true });
  };

  return (
    <div className="min-h-screen bg-[#f6f8fc] px-4 py-10">
      <div className="mx-auto max-w-2xl">
        <div className="mb-8 flex items-center justify-between"><Logo /><button onClick={signOut} className="text-sm text-slate-500 hover:text-slate-800">Sign out</button></div>
        <Card className="p-6 sm:p-8">
          <div className="mb-6 flex items-center gap-4">
            <div className="rounded-2xl bg-navy-50 p-3 text-navy-800"><Building2 className="h-7 w-7" /></div>
            <div>
              <h1 className="text-xl font-bold">Set up your firm</h1>
              <p className="text-sm text-slate-500">This creates your private workspace. You can invite your team next.</p>
            </div>
          </div>
          <Alert tone="info" className="mb-6">Joining an existing firm? Ask the firm owner to invite <b>{user?.email}</b> from the Team page, then sign in again.</Alert>
          <form onSubmit={submit} className="grid gap-4 sm:grid-cols-2">
            <Field label="Firm name" required className="sm:col-span-2"><Input value={f.name} onChange={set("name")} required placeholder="Sharma & Associates, Chartered Accountants" /></Field>
            <Field label="Firm Registration No. (FRN)"><Input value={f.frn} onChange={set("frn")} placeholder="012345C" /></Field>
            <Field label="Firm GSTIN"><Input value={f.gstin} onChange={(e) => setF((s) => ({ ...s, gstin: e.target.value.toUpperCase() }))} maxLength={15} /></Field>
            <Field label="Partner / Proprietor name"><Input value={f.partner_name} onChange={set("partner_name")} /></Field>
            <Field label="Membership No."><Input value={f.membership_no} onChange={set("membership_no")} /></Field>
            <Field label="City"><Input value={f.city} onChange={set("city")} /></Field>
            <Field label="State"><Input value={f.state} onChange={set("state")} /></Field>
            <Field label="Phone"><Input value={f.phone} onChange={set("phone")} inputMode="tel" /></Field>
            {err && <Alert tone="error" className="sm:col-span-2">{err}</Alert>}
            <div className="sm:col-span-2"><Button type="submit" size="lg" className="w-full" loading={saving}>Create workspace</Button></div>
          </form>
        </Card>
      </div>
    </div>
  );
}
