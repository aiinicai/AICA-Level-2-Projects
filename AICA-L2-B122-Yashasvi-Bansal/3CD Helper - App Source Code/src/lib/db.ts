import { supabase } from "@/integrations/supabase/client";
import type { Json } from "@/integrations/supabase/types";

export type Role = "owner" | "partner" | "staff" | "viewer";

export const ROLE_LABEL: Record<Role, string> = {
  owner: "Owner",
  partner: "Partner",
  staff: "Staff",
  viewer: "Viewer (read-only)",
};

export const canEdit = (r?: Role | null) => r === "owner" || r === "partner" || r === "staff";
export const isAdmin = (r?: Role | null) => r === "owner" || r === "partner";

export const CLIENT_STATUSES = ["Individual", "HUF", "Firm", "LLP", "Company", "AOP", "BOI", "Trust", "Other"];

export const ENGAGEMENT_STATUS: Record<string, { label: string; cls: string }> = {
  draft: { label: "Draft", cls: "bg-slate-100 text-slate-700" },
  in_review: { label: "In review", cls: "bg-amber-100 text-amber-800" },
  final: { label: "Final", cls: "bg-emerald-100 text-emerald-800" },
};

export function errMsg(e: unknown): string {
  if (!e) return "Something went wrong";
  if (typeof e === "string") return e;
  const m = (e as { message?: string }).message;
  return m || "Something went wrong";
}

/** Fetch all rows of a query in pages of 1000 (PostgREST limit). */
export async function fetchAll<T>(build: (from: number, to: number) => PromiseLike<{ data: T[] | null; error: unknown }>, pageSize = 1000): Promise<T[]> {
  const out: T[] = [];
  for (let from = 0; ; from += pageSize) {
    const { data, error } = await build(from, from + pageSize - 1);
    if (error) throw error;
    out.push(...(data ?? []));
    if (!data || data.length < pageSize) break;
  }
  return out;
}

export async function logActivity(firmId: string, action: string, entity?: string, entityId?: string, details?: Record<string, unknown>) {
  const { data } = await supabase.auth.getUser();
  if (!data.user) return;
  await supabase.from("activity_log").insert({
    firm_id: firmId,
    user_id: data.user.id,
    action,
    entity: entity ?? null,
    entity_id: entityId ?? null,
    details: (details ?? null) as Json,
  });
}

export const ACTION_LABEL: Record<string, string> = {
  "firm.created": "created the firm workspace",
  "firm.updated": "updated firm profile",
  "member.joined": "joined the firm",
  "member.invited": "invited a member",
  "member.role_changed": "changed a member's role",
  "member.removed": "removed a member",
  "client.created": "added a client",
  "client.updated": "updated a client",
  "client.archived": "archived a client",
  "client.deleted": "deleted a client",
  "report.shared": "shared a report on WhatsApp",
  "client_link.created": "made a client upload link",
  "client.imported": "imported clients from Excel",
  "engagement.created": "created an assessment year",
  "engagement.status": "changed status",
  "engagement.locked": "marked Final (locked)",
  "engagement.unlocked": "unlocked",
  "upload.created": "uploaded data",
  "upload.deleted": "deleted an upload",
  "rows.bulk_include": "changed inclusion in bulk",
  "party.merged": "merged parties",
  "party.updated": "updated party master",
  "report.exported": "exported a report",
};
