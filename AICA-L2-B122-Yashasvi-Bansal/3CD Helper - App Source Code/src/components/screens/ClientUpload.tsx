// Public page for a client: /u/<token>. No login – the link itself allows uploading for 7 days.
import { useCallback, useEffect, useRef, useState } from "react";
import { CheckCircle2, FileUp, UploadCloud } from "lucide-react";
import { supabase } from "@/integrations/supabase/client";
import { Alert, Button, Card, Spinner, cn } from "@/components/ui";
import { formatDate } from "@/lib/format";
import { errMsg } from "@/lib/db";
import { CLIENT_ACCEPT, CLIENT_MAX_FILE_MB, MODULE_LABEL, clientFilePath, type ClientLinkInfo } from "@/lib/clientLink";
import { TallyFetch } from "@/components/c31/TallyFetch";
import { zipDeflate } from "@/lib/import/bundle";
import { sendToDrive } from "@/lib/driveScript";

const db = supabase as any;

export function ClientUpload({ token }: { token: string }) {
  const [info, setInfo] = useState<ClientLinkInfo | null | undefined>(undefined);
  const [busy, setBusy] = useState("");
  const [err, setErr] = useState("");
  const [done, setDone] = useState<string[]>([]);
  const [drag, setDrag] = useState(false);
  const ref = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    const { data, error } = await db.rpc("client_link_info", { p_token: token });
    if (error) { setErr(errMsg(error)); setInfo(null); return; }
    setInfo(data ?? null);
  }, [token]);
  useEffect(() => { load(); }, [load]);

  const toDrive = info?.deliver_to === "drive" && !!info?.drive_url;

  /** A large Tally XML is sent as a ZIP (about ten times smaller). */
  const packed = async (f: File): Promise<File> => {
    if (/\.zip$/i.test(f.name) || f.size < 1048576) return f;
    setBusy(`Compressing ${f.name}…`);
    const z = await zipDeflate([{ name: f.name, data: new Uint8Array(await f.arrayBuffer()) }]);
    return new File([z as BlobPart], f.name.replace(/\.[^.]+$/, "") + ".zip", { type: "application/zip" });
  };

  const send = async (list: FileList | File[]) => {
    if (!info) return;
    const files = Array.from(list);
    setErr("");
    const sent: string[] = [];
    try {
      if (toDrive) {
        setBusy(`Sending ${files.length === 1 ? files[0].name : `${files.length} files`} to your CA's Google Drive…`);
        const base = `${info.client} AY ${info.ay}`.replace(/[^\w .-]+/g, "_");
        const r = await sendToDrive(info.drive_url!, token, files, base);
        sent.push(r.name);
      } else {
        for (let i = 0; i < files.length; i++) {
          const f = await packed(files[i]);
          if (f.size > CLIENT_MAX_FILE_MB * 1048576) throw new Error(`${f.name} is larger than ${CLIENT_MAX_FILE_MB} MB. Send a shorter period or split it.`);
          setBusy(`Uploading ${f.name} (${i + 1} of ${files.length})…`);
          const path = clientFilePath(info, token, f.name, Date.now() + i);
          const up = await supabase.storage.from("uploads").upload(path, f, { upsert: false, contentType: f.type || undefined });
          if (up.error) throw up.error;
          const r = await db.rpc("client_link_register", { p_token: token, p_path: path, p_file_name: f.name, p_size: f.size });
          if (r.error) throw r.error;
          sent.push(f.name);
        }
      }
    } catch (e) { setErr(errMsg(e)); }
    setDone((d) => [...d, ...sent]);
    setBusy("");
    if (!toDrive) load();
  };

  return (
    <div className="min-h-screen bg-slate-50 px-4 py-10">
      <div className="mx-auto max-w-xl space-y-4">
        <div className="text-center">
          <div className="text-xs font-semibold uppercase tracking-widest text-navy-700">3CD Helper</div>
          <h1 className="mt-1 text-xl font-bold text-slate-900">Upload data for your tax audit</h1>
        </div>

        {info === undefined && <div className="flex justify-center py-10"><Spinner /></div>}

        {info === null && (
          <Card className="p-6 text-center">
            <p className="font-semibold">This link has expired or is no longer valid.</p>
            <p className="mt-1 text-sm text-slate-500">Please ask your CA for a new link.</p>
            {err && <p className="mt-2 text-xs text-slate-400">{err}</p>}
          </Card>
        )}

        {info && (
          <>
            <Card className="p-5 text-sm">
              <div className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1">
                <span className="text-slate-500">From</span><span className="font-medium">{info.firm}</span>
                <span className="text-slate-500">For</span><span className="font-medium">{info.client}</span>
                <span className="text-slate-500">Year</span><span className="font-medium">AY {info.ay}</span>
                <span className="text-slate-500">Data</span><span className="font-medium">{MODULE_LABEL[info.module]}</span>
                <span className="text-slate-500">Link valid till</span><span className="font-medium">{formatDate(info.expires_at)}</span>
              </div>
            </Card>

            <div className={cn(busy && "pointer-events-none opacity-60")}>
              <div className="mb-2 text-sm font-semibold text-slate-700">Bring the data from Tally (recommended)</div>
              <TallyFetch ay={info.ay} clientName={info.client} modes={info.module === "clause31" ? ["loans", "daybook"] : ["daybook"]} onFile={(f) => send([f])} />
            </div>

            <Card className="p-5">
              <div className="mb-2 text-sm font-semibold text-slate-700">Or choose files</div>
              <div onClick={() => !busy && ref.current?.click()}
                onDragOver={(e) => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)}
                onDrop={(e) => { e.preventDefault(); setDrag(false); if (!busy && e.dataTransfer.files?.length) send(e.dataTransfer.files); }}
                className={cn("flex cursor-pointer flex-col items-center rounded-2xl border-2 border-dashed px-6 py-10 text-center", drag ? "border-navy-500 bg-navy-50" : "border-slate-300 hover:border-navy-400 hover:bg-slate-50")}>
                {busy ? <Spinner className="h-10 w-10" /> : <UploadCloud className="h-12 w-12 text-navy-600" />}
                <div className="mt-3 font-semibold">{busy || "Choose files or drop them here"}</div>
                <div className="mt-1 text-sm text-slate-500">
                  {info.module === "clause31" ? "Tally Day Book or loan ledgers (XML), or Excel / CSV." : info.module === "all" ? "Tally Day Book and Masters (XML), or Excel / CSV." : "Expense ledgers or purchase register – Excel, CSV or Tally XML."} Large files are compressed before sending.
                </div>
                <input ref={ref} type="file" multiple accept={CLIENT_ACCEPT} className="hidden" onChange={(e) => { if (e.target.files?.length) send(e.target.files); e.target.value = ""; }} />
              </div>
              {err && <Alert tone="error" className="mt-3">{err}</Alert>}
              {done.length > 0 && <Alert tone="success" className="mt-3"><CheckCircle2 className="mr-1 inline h-4 w-4" />Received: {done.join(", ")}. Thank you – {toDrive ? "it is saved in your CA's Google Drive." : "your CA can see the files now."}</Alert>}
            </Card>

            {!toDrive && info.files.length > 0 && (
              <Card className="p-5">
                <div className="mb-2 text-sm font-semibold">Files sent on this link</div>
                <ul className="space-y-1 text-sm">
                  {info.files.map((f, i) => <li key={i} className="flex items-center gap-2"><FileUp className="h-4 w-4 text-slate-400" /><span className="flex-1 truncate">{f.name}</span><span className="text-xs text-slate-400">{formatDate(f.at)}</span></li>)}
                </ul>
              </Card>
            )}
            <p className="text-center text-xs text-slate-400">{toDrive ? "The data goes only to your CA's own Google Drive." : "Files are stored privately and only your CA's firm can open them."}</p>
          </>
        )}
      </div>
    </div>
  );
}
