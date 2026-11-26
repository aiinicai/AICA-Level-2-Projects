import { FormEvent, useEffect, useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import { useAuth } from "@/contexts/AuthContext";
import { useToast } from "@/components/Toast";
import { Alert, Button, Card, CardHeader, Field, Input, PageHeader } from "@/components/ui";
import { errMsg } from "@/lib/db";
import { formatDateTime } from "@/lib/format";

export default function Profile() {
  const { user, profile, refreshProfile, signOut } = useAuth();
  const toast = useToast();
  const [name, setName] = useState(profile?.full_name ?? "");
  const [mobile, setMobile] = useState(profile?.mobile ?? "");
  const [username, setUsername] = useState(profile?.username ?? "");
  const [curPw, setCurPw] = useState("");
  const [pw, setPw] = useState("");
  const [pw2, setPw2] = useState("");
  const [busy, setBusy] = useState("");
  const [logins, setLogins] = useState<any[]>([]);

  useEffect(() => { setName(profile?.full_name ?? ""); setMobile(profile?.mobile ?? ""); setUsername(profile?.username ?? ""); }, [profile?.id]);
  useEffect(() => { supabase.from("login_history").select("*").order("created_at", { ascending: false }).limit(10).then(({ data }) => setLogins(data ?? [])); }, []);

  const saveProfile = async (e: FormEvent) => {
    e.preventDefault(); setBusy("p");
    const { error } = await supabase.from("profiles").update({ full_name: name.trim(), mobile: mobile.trim() || null }).eq("id", user!.id);
    if (error) { setBusy(""); return toast(errMsg(error), "error"); }
    const u = username.trim().toLowerCase();
    if (u !== (profile?.username ?? "")) {
      const { error: ue } = await (supabase as any).rpc("set_my_username", { p_username: u });
      if (ue) { setBusy(""); return toast(errMsg(ue), "error"); }
    }
    setBusy("");
    toast("Profile saved"); refreshProfile();
  };
  const changePw = async (e: FormEvent) => {
    e.preventDefault();
    if (pw.length < 8) return toast("Use at least 8 characters", "error");
    if (pw !== pw2) return toast("Passwords do not match", "error");
    setBusy("pw");
    const { error } = await supabase.auth.updateUser({ password: pw, current_password: curPw || undefined } as { password: string });
    setBusy("");
    if (error) return toast(errMsg(error), "error");
    setCurPw(""); setPw(""); setPw2(""); toast("Password changed");
  };
  const device = (ua: string) => /iphone|ipad/i.test(ua) ? "iPhone / iPad" : /android/i.test(ua) ? "Android" : /windows/i.test(ua) ? "Windows" : /mac/i.test(ua) ? "Mac" : "Browser";

  return (
    <>
      <PageHeader title="My profile" subtitle={user?.email} />
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader title="Personal details" />
          <form onSubmit={saveProfile} className="space-y-4 p-5">
            <Field label="Full name"><Input value={name} onChange={(e) => setName(e.target.value)} required /></Field>
            <Field label="Mobile"><Input value={mobile} onChange={(e) => setMobile(e.target.value)} inputMode="tel" /></Field>
            <Field label="Username" hint="To sign in with the username instead of the email. 3–30 small letters, numbers, dot, dash or underscore. Leave empty for none.">
              <Input value={username} onChange={(e) => setUsername(e.target.value.toLowerCase().replace(/\s/g, ""))} autoCapitalize="none" spellCheck={false} placeholder="e.g. yash.demo" maxLength={30} />
            </Field>
            <Button type="submit" loading={busy === "p"}>Save</Button>
          </form>
        </Card>
        <Card>
          <CardHeader title="Change password" />
          <form onSubmit={changePw} className="space-y-4 p-5">
            <Field label="Current password"><Input type="password" value={curPw} onChange={(e) => setCurPw(e.target.value)} autoComplete="current-password" /></Field>
            <Field label="New password"><Input type="password" value={pw} onChange={(e) => setPw(e.target.value)} autoComplete="new-password" /></Field>
            <Field label="Confirm"><Input type="password" value={pw2} onChange={(e) => setPw2(e.target.value)} autoComplete="new-password" /></Field>
            <Button type="submit" loading={busy === "pw"}>Update password</Button>
          </form>
        </Card>
        <Card>
          <CardHeader title="Recent sign-ins" />
          <ul className="divide-y divide-slate-100 text-sm">
            {logins.map((l) => <li key={l.id} className="flex justify-between px-5 py-2.5"><span>{device(l.device ?? "")}</span><span className="text-slate-500">{formatDateTime(l.created_at)}</span></li>)}
            {!logins.length && <li className="px-5 py-4 text-slate-500">No sign-ins recorded yet.</li>}
          </ul>
        </Card>
        <Card>
          <CardHeader title="Security" />
          <div className="space-y-3 p-5">
            <Alert tone="info">Signed in on another device you don't recognise? Sign out everywhere and change your password.</Alert>
            <Button variant="outline" onClick={async () => { await supabase.auth.signOut({ scope: "global" }); await signOut(); }}>Sign out from all devices</Button>
          </div>
        </Card>
      </div>
    </>
  );
}
