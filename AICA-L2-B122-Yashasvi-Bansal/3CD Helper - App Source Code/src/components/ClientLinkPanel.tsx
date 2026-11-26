// Firm side of the client upload link: make a 7-day link, send it on WhatsApp, see and use the files the client sent.
import { useCallback, useEffect, useState } from "react";
import { Copy, Link2, MessageCircle, Monitor, ExternalLink, Download } from "lucide-react";
import { supabase } from "@/integrations/supabase/client";
import { useFirm } from "@/contexts/FirmContext";
import { useToast } from "@/components/Toast";
import { Alert, Badge, Button, Card, Field, Input, Modal, Select, Textarea } from "@/components/ui";
import { canEdit, errMsg, logActivity } from "@/lib/db";
import { formatDate } from "@/lib/format";
import { normalizeIndianMobile, waLinks } from "@/lib/whatsapp";
import { CLIENT_LINK_DAYS, defaultLinkMessage, linkUrl, linksNotReady, type LinkModule, type UploadLink } from "@/lib/clientLink";

const db = supabase as any;
interface ClientFile { id: string; file_name: string; storage_path: string | null; file_size: number | null; created_at: string }

interface Props { engagement: any; client: any; module: LinkModule; editable: boolean; onUse?: (file: File) => void }

export function ClientLinkPanel({ engagement, client, module, editable, onUse }: Props) {
  const { firm, role } = useFirm();
  const toast = useToast();
  const [links, setLinks] = useState<UploadLink[]>([]);
  const [files, setFiles] = useState<ClientFile[]>([]);
  const [notReady, setNotReady] = useState(false);
  const [busy, setBusy] = useState("");
  const [send, setSend] = useState<UploadLink | null>(null);
  const [mobile, setMobile] = useState("");
  const [text, setText] = useState("");
  const driveReady = !!firm?.settings?.drive_url;
  const [to, setTo] = useState<"app" | "drive">("app");

  const load = useCallback(async () => {
    const l = await db.from("upload_links").select("*").eq("engagement_id", engagement.id).eq("module", module).order("created_at", { ascending: false });
    if (l.error) { if (linksNotReady(l.error)) setNotReady(true); return; }
    setNotReady(false);
    setLinks(l.data ?? []);
    const f = await db.from("uploads").select("id, file_name, storage_path, file_size, created_at").eq("engagement_id", engagement.id).eq("module", module).eq("source", "client_link").order("created_at", { ascending: false });
    setFiles(f.data ?? []);
  }, [engagement.id, module]);
  useEffect(() => { load(); }, [load]);

  const live = links.filter((l) => !l.revoked_at && new Date(l.expires_at) > new Date());
  const allowed = editable && canEdit(role);

  const openSend = (l: UploadLink) => {
    setSend(l);
    setMobile(client.mobile ?? "");
    setText(l.message || defaultLinkMessage({ name: client.contact_person || client.name, module, ay: engagement.assessment_year, firm: firm?.name ?? "" }));
  };

  const create = async () => {
    setBusy("create");
    try {
      const message = defaultLinkMessage({ name: client.contact_person || client.name, module, ay: engagement.assessment_year, firm: firm?.name ?? "" });
      const { data, error } = await db.from("upload_links").insert({ firm_id: firm!.id, engagement_id: engagement.id, module, deliver_to: to === "drive" && driveReady ? "drive" : "app", message, expires_at: new Date(Date.now() + CLIENT_LINK_DAYS * 86400000).toISOString() }).select("*").single();
      if (error) throw error;
      await logActivity(firm!.id, "client_link.created", "engagement", engagement.id, { module });
      await load();
      openSend(data);
    } catch (e) { if (linksNotReady(e)) setNotReady(true); else toast(errMsg(e), "error"); }
    setBusy("");
  };

  const revoke = async (l: UploadLink) => {
    const { error } = await db.from("upload_links").update({ revoked_at: new Date().toISOString() }).eq("id", l.id);
    if (error) toast(errMsg(error), "error"); else { toast("Link stopped", "success"); load(); }
  };

  const use = async (f: ClientFile) => {
    if (!f.storage_path || !onUse) return;
    setBusy(f.id);
    try {
      const { data, error } = await supabase.storage.from("uploads").download(f.storage_path);
      if (error || !data) throw error ?? new Error("Could not open the file");
      onUse(new File([data], f.file_name, { type: data.type }));
    } catch (e) { toast(errMsg(e), "error"); }
    setBusy("");
  };
  const download = async (f: ClientFile) => {
    if (!f.storage_path) return;
    const { data, error } = await supabase.storage.from("uploads").createSignedUrl(f.storage_path, 120, { download: f.file_name });
    if (error || !data) toast(errMsg(error), "error"); else window.open(data.signedUrl, "_blank");
  };

  const copy = async (s: string) => { try { await navigator.clipboard.writeText(s); toast("Copied", "success"); } catch { toast("Copy failed", "error"); } };

  if (notReady) return (
    <Card className="p-5">
      <div className="flex items-start gap-3 text-sm"><Link2 className="mt-0.5 h-5 w-5 shrink-0 text-slate-400" />
        <div><div className="font-semibold">Client upload link</div><p className="mt-1 text-slate-500">Waiting for a one-time database update (upload_links). Once it is done in Lovable, you can send clients a 7-day link to upload their data without logging in.</p></div></div>
    </Card>
  );

  const number = normalizeIndianMobile(mobile);
  const msg = send ? text.replace("{link}", linkUrl(send.token)) : "";
  const wa = number && send ? waLinks(number, msg) : null;

  return (
    <Card className="p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2 font-semibold"><Link2 className="h-5 w-5 text-navy-600" />Client upload link</div>
        {allowed && <span className="flex items-center gap-2">
          <Select aria-label="Send the data to" className="h-8 w-48 text-xs" value={to} onChange={(e) => setTo(e.target.value as "app" | "drive")}>
            <option value="app">Send to: this app</option>
            <option value="drive" disabled={!driveReady}>Send to: my Google Drive{driveReady ? "" : " (set up in Settings)"}</option>
          </Select>
          <Button size="sm" variant={live.length ? "outline" : "primary"} loading={busy === "create"} onClick={create}>{live.length ? "New link" : `Create ${CLIENT_LINK_DAYS}-day link`}</Button>
        </span>}
      </div>
      <p className="mt-1 text-xs text-slate-500">The client opens the link – no login – and brings the data from Tally with one button (Tally Connector) or uploads files. Data arrives here, or in your Google Drive if you choose that.</p>

      {live.length > 0 && (
        <div className="mt-3 space-y-2">
          {live.map((l) => (
            <div key={l.id} className="flex flex-wrap items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm">
              <code className="min-w-0 flex-1 truncate text-xs text-slate-600">{linkUrl(l.token)}</code>
              {l.deliver_to === "drive" && <Badge className="bg-navy-50 text-navy-800">→ Google Drive</Badge>}
              <Badge className="bg-emerald-50 text-emerald-700">till {formatDate(l.expires_at)}</Badge>
              <Button size="sm" variant="ghost" icon={<Copy className="h-4 w-4" />} onClick={() => copy(linkUrl(l.token))}>Copy</Button>
              {allowed && <Button size="sm" variant="ghost" icon={<MessageCircle className="h-4 w-4" />} onClick={() => openSend(l)}>WhatsApp</Button>}
              {allowed && <Button size="sm" variant="ghost" onClick={() => revoke(l)}>Stop</Button>}
            </div>
          ))}
        </div>
      )}

      {files.length > 0 && (
        <div className="mt-4">
          <div className="mb-1 text-sm font-semibold">Files from the client</div>
          <div className="divide-y divide-slate-100 rounded-lg border border-slate-200">
            {files.map((f) => (
              <div key={f.id} className="flex flex-wrap items-center gap-2 px-3 py-2 text-sm">
                <span className="min-w-0 flex-1 truncate font-medium">{f.file_name}</span>
                <span className="text-xs text-slate-400">{formatDate(f.created_at)}{f.file_size ? ` · ${(f.file_size / 1048576).toFixed(1)} MB` : ""}</span>
                <Button size="sm" variant="ghost" icon={<Download className="h-4 w-4" />} onClick={() => download(f)}>Download</Button>
                {onUse && allowed && <Button size="sm" loading={busy === f.id} onClick={() => use(f)}>Use this file</Button>}
              </div>
            ))}
          </div>
        </div>
      )}

      {send && (
        <Modal open onClose={() => setSend(null)} title="Send the upload link">
          <div className="space-y-3">
            <Field label="Client's WhatsApp number"><Input value={mobile} onChange={(e) => setMobile(e.target.value)} inputMode="tel" placeholder="98XXXXXXXX" /></Field>
            {mobile && !number && <p className="text-xs text-red-600">Enter a 10-digit mobile number (or with country code).</p>}
            <Field label="Message"><Textarea rows={8} value={text} onChange={(e) => setText(e.target.value)} /></Field>
            {wa ? (
              <div className="grid gap-2 sm:grid-cols-2">
                <a href={wa.desktop} className="inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-emerald-600 px-3 text-sm font-semibold text-white hover:bg-emerald-700"><Monitor className="h-4 w-4" />WhatsApp Desktop</a>
                <a href={wa.web} target="_blank" rel="noreferrer" className="inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-emerald-600 px-3 text-sm font-semibold text-emerald-700 hover:bg-emerald-50"><ExternalLink className="h-4 w-4" />WhatsApp Web</a>
              </div>
            ) : <Alert tone="info">Enter the client's number to open WhatsApp.</Alert>}
            {wa && <a href={wa.phone} target="_blank" rel="noreferrer" className="block text-center text-xs text-slate-500 underline">On a phone? Open WhatsApp</a>}
            <Button variant="outline" className="w-full" icon={<Copy className="h-4 w-4" />} onClick={() => copy(msg)}>Copy message with link</Button>
          </div>
        </Modal>
      )}
    </Card>
  );
}
