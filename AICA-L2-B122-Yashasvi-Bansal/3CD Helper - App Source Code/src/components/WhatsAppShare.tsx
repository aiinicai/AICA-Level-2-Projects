// Share a report with the client on WhatsApp – no API, no cost.
// The report is saved in the private 'uploads' bucket, a link valid for 7 days is made, and WhatsApp
// (Desktop app, WhatsApp Web or the phone app) opens on the client's chat with the message filled in.
// The user only presses Send in WhatsApp.
import { useState } from "react";
import { Copy, ExternalLink, MessageCircle, Monitor } from "lucide-react";
import { supabase } from "@/integrations/supabase/client";
import { useFirm } from "@/contexts/FirmContext";
import { useToast } from "@/components/Toast";
import { Alert, Button, Field, Input, Modal, Textarea } from "@/components/ui";
import { canEdit, errMsg, logActivity } from "@/lib/db";
import { buildShareMessage, normalizeIndianMobile, waLinks, LINK_DAYS } from "@/lib/whatsapp";

interface Props {
  client: any;
  engagement: any;
  /** e.g. "Clause 31 report" */
  label: string;
  /** Builds the report file to share. */
  build: () => Promise<{ blob: Blob; fileName: string }> | { blob: Blob; fileName: string };
  disabled?: boolean;
}

export function WhatsAppShare({ client, engagement, label, build, disabled }: Props) {
  const { firm, role } = useFirm();
  const toast = useToast();
  const [open, setOpen] = useState(false);
  const [mobile, setMobile] = useState("");
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [link, setLink] = useState<string | null>(null);

  const start = () => {
    setMobile(client.mobile ?? "");
    setText(buildShareMessage({ name: client.contact_person || client.name, report: label, ay: engagement.assessment_year, firm: firm?.name ?? "" }));
    setLink(null);
    setOpen(true);
  };

  const number = normalizeIndianMobile(mobile);

  const makeLink = async () => {
    setBusy(true);
    try {
      const { blob, fileName } = await build();
      const path = `${firm!.id}/${engagement.id}/shared/${Date.now()}_${fileName}`;
      const up = await supabase.storage.from("uploads").upload(path, blob, { upsert: false, contentType: blob.type || undefined });
      if (up.error) throw up.error;
      const { data, error } = await supabase.storage.from("uploads").createSignedUrl(path, LINK_DAYS * 24 * 3600, { download: fileName });
      if (error || !data) throw error ?? new Error("Could not create the link");
      setLink(data.signedUrl);
      // keep the client's number for next time when it was typed here
      if (number && !client.mobile) await supabase.from("clients").update({ mobile: mobile.trim() }).eq("id", client.id);
      await logActivity(firm!.id, "report.shared", "engagement", engagement.id, { report: label, file: fileName, to: number ? `+${number}` : null });
    } catch (e) { toast(errMsg(e), "error"); }
    setBusy(false);
  };

  const message = link ? text.replace("{link}", link) : text;
  const links = number && link ? waLinks(number, message) : null;
  const copy = async () => { try { await navigator.clipboard.writeText(message); toast("Message copied", "success"); } catch { toast("Copy failed – select the text and copy", "error"); } };

  return (
    <>
      <Button variant="outline" icon={<MessageCircle className="h-4 w-4" />} onClick={start} disabled={disabled || !canEdit(role)} title={canEdit(role) ? "Send the report link on WhatsApp" : "Viewers cannot share reports"}>WhatsApp</Button>
      {open && (
        <Modal open onClose={() => setOpen(false)} title={`Send ${label} on WhatsApp`}>
          <div className="space-y-3">
            <Field label="Client's WhatsApp number">
              <Input value={mobile} onChange={(e) => { setMobile(e.target.value); }} inputMode="tel" placeholder="98XXXXXXXX" />
            </Field>
            {mobile && !number && <p className="text-xs text-red-600">Enter a 10-digit mobile number (or with country code).</p>}
            <Field label="Message">
              <Textarea rows={7} value={text} onChange={(e) => setText(e.target.value)} />
            </Field>
            <p className="text-xs text-slate-500">{"{link}"} is replaced by the report link. The link works for {LINK_DAYS} days; anyone with the link can download the file.</p>

            {!link ? (
              <Button className="w-full" onClick={makeLink} loading={busy} disabled={!number || !text.includes("{link}")}>Create link</Button>
            ) : (
              <div className="space-y-2">
                <Alert tone="success">Link ready. Open WhatsApp and press Send.</Alert>
                <div className="grid gap-2 sm:grid-cols-2">
                  <a href={links!.desktop} className="inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-emerald-600 px-3 text-sm font-semibold text-white hover:bg-emerald-700"><Monitor className="h-4 w-4" />WhatsApp Desktop</a>
                  <a href={links!.web} target="_blank" rel="noreferrer" className="inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-emerald-600 px-3 text-sm font-semibold text-emerald-700 hover:bg-emerald-50"><ExternalLink className="h-4 w-4" />WhatsApp Web</a>
                </div>
                <a href={links!.phone} target="_blank" rel="noreferrer" className="block text-center text-xs text-slate-500 underline">On a phone? Open WhatsApp</a>
                <Button variant="outline" className="w-full" icon={<Copy className="h-4 w-4" />} onClick={copy}>Copy message with link</Button>
              </div>
            )}
          </div>
        </Modal>
      )}
    </>
  );
}
