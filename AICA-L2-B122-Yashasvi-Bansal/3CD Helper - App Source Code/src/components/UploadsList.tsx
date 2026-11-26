import { useEffect, useState } from "react";
import { FileSpreadsheet, Download, Trash2 } from "lucide-react";
import { supabase } from "@/integrations/supabase/client";
import { useFirm } from "@/contexts/FirmContext";
import { useTeam } from "@/hooks/useTeam";
import { useToast } from "@/components/Toast";
import { Button, Card, CardHeader, Modal } from "@/components/ui";
import { errMsg, logActivity } from "@/lib/db";
import { formatDateTime } from "@/lib/format";

/** Files uploaded to an assessment year for one module. Deleting a file removes the rows imported from it. */
export function UploadsList({ engagementId, module, editable, onChanged }: { engagementId: string; module: string; editable: boolean; onChanged: () => void }) {
  const { firm } = useFirm();
  const { nameOf } = useTeam();
  const toast = useToast();
  const [list, setList] = useState<any[]>([]);
  const [del, setDel] = useState<any>(null);
  const load = () => supabase.from("uploads").select("*").eq("engagement_id", engagementId).eq("module", module).order("created_at", { ascending: false }).then(({ data }) => setList(data ?? []));
  useEffect(() => { load(); }, [engagementId, module]);
  if (!list.length) return null;
  return (
    <Card>
      <CardHeader title="Uploaded files" subtitle="Deleting a file removes the rows imported from it" />
      <ul className="divide-y divide-slate-100">
        {list.map((u) => (
          <li key={u.id} className="flex flex-wrap items-center gap-3 px-5 py-3 text-sm">
            <FileSpreadsheet className="h-5 w-5 text-navy-700" />
            <div className="min-w-0 flex-1">
              <div className="truncate font-medium">{u.file_name}</div>
              <div className="text-xs text-slate-500">{u.row_count.toLocaleString("en-IN")} rows · {u.software_detected} · by {nameOf(u.created_by)} · {formatDateTime(u.created_at)}</div>
            </div>
            {u.storage_path && (
              <Button size="sm" variant="ghost" icon={<Download className="h-4 w-4" />} onClick={async () => {
                const { data, error } = await supabase.storage.from("uploads").createSignedUrl(u.storage_path, 120);
                if (error || !data) return toast("Original file not available", "error");
                window.open(data.signedUrl, "_blank");
              }}>Original</Button>
            )}
            {editable && <Button size="sm" variant="ghost" className="text-red-600" icon={<Trash2 className="h-4 w-4" />} onClick={() => setDel(u)}>Delete</Button>}
          </li>
        ))}
      </ul>
      {del && (
        <Modal open onClose={() => setDel(null)} title="Delete upload?"
          footer={<><Button variant="ghost" onClick={() => setDel(null)}>Cancel</Button><Button variant="danger" onClick={async () => {
            const { error } = await supabase.from("uploads").delete().eq("id", del.id);
            if (error) return toast(errMsg(error), "error");
            if (del.storage_path) await supabase.storage.from("uploads").remove([del.storage_path]);
            await logActivity(firm!.id, "upload.deleted", "engagement", engagementId, { file: del.file_name });
            toast("Upload deleted"); setDel(null); load(); onChanged();
          }}>Delete</Button></>}>
          <p className="text-sm">This removes <b>{del.row_count}</b> rows imported from <b>{del.file_name}</b>, including any edits made to them.</p>
        </Modal>
      )}
    </Card>
  );
}
