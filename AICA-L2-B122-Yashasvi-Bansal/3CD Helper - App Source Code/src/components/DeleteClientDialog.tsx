import { useState } from "react";
import { Download, Trash2 } from "lucide-react";
import { supabase } from "@/integrations/supabase/client";
import { useFirm } from "@/contexts/FirmContext";
import { useToast } from "@/components/Toast";
import { Alert, Button, Field, Input, Modal } from "@/components/ui";
import { errMsg, fetchAll, logActivity } from "@/lib/db";
import { sheetFromAoa, writeWorkbook, safeFileName } from "@/lib/export";

const db = supabase as any;

/** Removes a client with all its years, entries, party master and files (storage too). Owner / Partner only. */
export async function deleteClientData(firmId: string, client: { id: string; name: string }, engagements: { id: string; assessment_year: string }[]) {
  const ids = engagements.map((e) => e.id);
  if (ids.length) {
    const ups = await fetchAll<any>((from, to) => db.from("uploads").select("storage_path").in("engagement_id", ids).range(from, to));
    const paths = ups.map((u) => u.storage_path).filter(Boolean);
    // reports shared on WhatsApp are kept under <firm>/<year>/shared/
    for (const id of ids) {
      const { data } = await supabase.storage.from("uploads").list(`${firmId}/${id}/shared`, { limit: 1000 });
      (data ?? []).forEach((f) => paths.push(`${firmId}/${id}/shared/${f.name}`));
    }
    for (let i = 0; i < paths.length; i += 100) await supabase.storage.from("uploads").remove(paths.slice(i, i + 100));
  }
  const { error } = await supabase.from("clients").delete().eq("id", client.id);
  if (error) throw error;
  await logActivity(firmId, "client.deleted", "client", client.id, { name: client.name, years: engagements.map((e) => e.assessment_year) });
}

/** Permanently delete a client with all its assessment years, uploads, entries and party master. Owner / Partner only. */
export function DeleteClientDialog({ client, engagements, onClose, onDeleted }: { client: { id: string; name: string; pan?: string | null }; engagements: any[]; onClose: () => void; onDeleted: () => void }) {
  const { firm } = useFirm();
  const toast = useToast();
  const [typed, setTyped] = useState("");
  const [busy, setBusy] = useState<"" | "backup" | "delete">("");
  const locked = engagements.filter((e) => e.locked);
  const ok = typed.trim().toLowerCase() === client.name.trim().toLowerCase();

  const backup = async () => {
    setBusy("backup");
    try {
      const ids = engagements.map((e) => e.id);
      const ay = Object.fromEntries(engagements.map((e) => [e.id, e.assessment_year]));
      const get = (t: string, cols: string) => ids.length ? fetchAll<any>((from, to) => db.from(t).select(cols).in("engagement_id", ids).order("engagement_id").range(from, to)) : Promise.resolve([]);
      const [exp, loans, parties] = await Promise.all([
        get("expense_rows", "engagement_id, party_name, gstin, expense_head, amount, txn_date, category, include"),
        get("loan_txns", "engagement_id, txn_date, party_name, pan, kind, amount, mode, voucher_no, include, remark"),
        fetchAll<any>((from, to) => db.from("party_master").select("party_name, gstin, pan, address, msme_category, udyam_no").eq("client_id", client.id).range(from, to)),
      ]);
      writeWorkbook([
        { name: "Clause 44 entries", ws: sheetFromAoa([["AY", "Party", "GSTIN", "Expense head", "Amount", "Date", "Category", "Included"], ...exp.map((r) => [ay[r.engagement_id], r.party_name, r.gstin, r.expense_head, Number(r.amount), r.txn_date, r.category, r.include ? "Yes" : "No"])]) },
        { name: "Clause 31 entries", ws: sheetFromAoa([["AY", "Date", "Party", "PAN", "Type", "Amount", "Mode", "Voucher", "Included", "Remark"], ...loans.map((r) => [ay[r.engagement_id], r.txn_date, r.party_name, r.pan, r.kind, Number(r.amount), r.mode, r.voucher_no, r.include ? "Yes" : "No", r.remark])]) },
        { name: "Party master", ws: sheetFromAoa([["Party", "GSTIN", "PAN", "Address", "MSME", "Udyam"], ...parties.map((p) => [p.party_name, p.gstin, p.pan, p.address, p.msme_category, p.udyam_no])]) },
      ], `Backup_${safeFileName(client.name)}.xlsx`);
    } catch (e) { toast(errMsg(e), "error"); }
    setBusy("");
  };

  const remove = async () => {
    setBusy("delete");
    try {
      await deleteClientData(firm!.id, client, engagements);
      toast(`${client.name} deleted`);
      onDeleted();
    } catch (e) { toast(errMsg(e), "error"); setBusy(""); }
  };

  return (
    <Modal open onClose={onClose} title="Delete client permanently?"
      footer={<><Button variant="ghost" onClick={onClose}>Cancel</Button>
        <Button variant="danger" icon={<Trash2 className="h-4 w-4" />} disabled={!ok || locked.length > 0} loading={busy === "delete"} onClick={remove}>Delete client</Button></>}>
      {locked.length > 0 ? (
        <Alert tone="warn">AY {locked.map((e) => e.assessment_year).join(", ")} {locked.length > 1 ? "are" : "is"} Final and locked. Unlock {locked.length > 1 ? "them" : "it"} first to delete this client.</Alert>
      ) : (
        <div className="space-y-4 text-sm">
          <p>This removes <b>{client.name}</b> with {engagements.length} assessment year(s), every uploaded file, all entries and the party master. It cannot be undone.</p>
          <Button variant="outline" size="sm" icon={<Download className="h-4 w-4" />} loading={busy === "backup"} onClick={backup}>Download a backup first (optional)</Button>
          <Field label={`Type the client name to confirm: ${client.name}`}><Input value={typed} onChange={(e) => setTyped(e.target.value)} autoFocus /></Field>
        </div>
      )}
    </Modal>
  );
}
