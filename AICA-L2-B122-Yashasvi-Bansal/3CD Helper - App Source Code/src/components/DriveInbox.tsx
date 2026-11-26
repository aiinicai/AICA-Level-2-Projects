// Data a client sent to the firm's Google Drive (through a client link): the year's page finds it on its own
// and brings it in with one click. Files are matched to this client and year by the link they came from.
import { useEffect, useState } from "react";
import { CheckCircle2, HardDrive, RefreshCw } from "lucide-react";
import { supabase } from "@/integrations/supabase/client";
import { useFirm } from "@/contexts/FirmContext";
import { useToast } from "@/components/Toast";
import { Badge, Button, Modal, cn } from "@/components/ui";
import { type DriveFile, getDrive, listDrive } from "@/lib/driveScript";
import { formatDateTime } from "@/lib/format";

const mb = (n: number) => (n >= 1048576 ? `${(n / 1048576).toFixed(1)} MB` : `${Math.max(1, Math.round(n / 1024))} KB`);

interface Props { eng: any; client: any; onFile: (f: File) => void }

export function DriveInbox({ eng, client, onFile }: Props) {
  const { firm } = useFirm();
  const toast = useToast();
  const url = String(firm?.settings?.drive_url ?? "");
  const key = String(firm?.settings?.drive_key ?? "");
  const [files, setFiles] = useState<DriveFile[] | null>(null);
  const [err, setErr] = useState("");
  const [taken, setTaken] = useState<string[]>(eng.clause_answers?.drive_taken ?? []);
  const [busy, setBusy] = useState("");
  const [all, setAll] = useState(false);

  const load = async () => {
    if (!url || !key) return;
    setErr("");
    try { setFiles(await listDrive(url, key, { eng: eng.id, client: client?.name ?? "", ay: eng.assessment_year })); }
    catch (e: any) { setErr(e?.message ?? String(e)); }
  };
  useEffect(() => { load(); }, [eng.id, url, key]);
  if (!url || !key) return null;
  if (err) return <div className="mb-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-2 text-xs text-amber-800">Google Drive: {err}</div>;
  if (!files?.length) return null;

  const bring = async (f: DriveFile) => {
    setBusy(f.id);
    try {
      const file = await getDrive(url, key, f);
      // remember it as taken (merged into the latest answers, so nothing else is overwritten)
      const { data } = await supabase.from("engagements").select("clause_answers").eq("id", eng.id).maybeSingle();
      const ans = ((data as any)?.clause_answers ?? {}) as Record<string, unknown>;
      const list = Array.from(new Set([...((ans.drive_taken as string[]) ?? []), f.id]));
      await supabase.from("engagements").update({ clause_answers: { ...ans, drive_taken: list } } as any).eq("id", eng.id);
      setTaken(list); setAll(false);
      onFile(file);
    } catch (e: any) { toast(e?.message ?? String(e), "error"); }
    setBusy("");
  };

  const newest = files[0];
  const fresh = !taken.includes(newest.id);
  return (
    <>
      <div className={cn("mb-4 flex flex-wrap items-center gap-3 rounded-xl border px-4 py-3 text-sm", fresh ? "border-emerald-300 bg-emerald-50" : "border-slate-200 bg-white")}>
        <HardDrive className={cn("h-5 w-5", fresh ? "text-emerald-700" : "text-slate-400")} />
        <div className="min-w-0">
          <div className="font-semibold">{fresh ? "New data from the client in Google Drive" : "Client data in Google Drive"}</div>
          <div className="text-xs text-slate-600">Latest: {formatDateTime(newest.at)} · {mb(newest.size)}{files.length > 1 && <> · {files.length} files in all</>}{!fresh && <> · already brought in</>}</div>
        </div>
        <div className="ml-auto flex gap-2">
          <Button size="sm" variant="ghost" icon={<RefreshCw className="h-3.5 w-3.5" />} onClick={load}>Check</Button>
          {files.length > 1 && <Button size="sm" variant="outline" onClick={() => setAll(true)}>All files</Button>}
          <Button size="sm" variant={fresh ? "gold" : "outline"} loading={busy === newest.id} onClick={() => bring(newest)}>{fresh ? "Bring it in" : "Bring again"}</Button>
        </div>
      </div>
      {all && (
        <Modal open title="Client data in Google Drive" onClose={() => setAll(false)}>
          <p className="mb-3 text-sm text-slate-600">Files this client sent for AY {eng.assessment_year}, newest first. Bringing a file in replaces the data brought earlier – it is not added twice.</p>
          <div className="divide-y divide-slate-100 rounded-xl border border-slate-200">
            {files.map((f, i) => (
              <div key={f.id} className="flex items-center gap-3 px-3 py-2 text-sm">
                <div className="min-w-0 flex-1">
                  <div className="truncate font-medium">{f.name}</div>
                  <div className="text-xs text-slate-500">{formatDateTime(f.at)} · {mb(f.size)}</div>
                </div>
                {i === 0 && <Badge className="bg-emerald-50 text-emerald-700">Newest</Badge>}
                {taken.includes(f.id) && <Badge className="bg-slate-100 text-slate-600"><CheckCircle2 className="h-3 w-3" />Taken</Badge>}
                <Button size="sm" variant={i === 0 ? "gold" : "outline"} loading={busy === f.id} onClick={() => bring(f)}>Bring in</Button>
              </div>
            ))}
          </div>
        </Modal>
      )}
    </>
  );
}
