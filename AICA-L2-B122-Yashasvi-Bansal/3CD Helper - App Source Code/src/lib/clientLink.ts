// Client upload link: a 7-day link the client opens without logging in to send data files.
// Needs the upload_links table and client_link_* functions (docs/database/client_upload_links.sql).

export const CLIENT_LINK_DAYS = 7;
export const CLIENT_MAX_FILE_MB = 50;
export const CLIENT_ACCEPT = ".xlsx,.xls,.xlsm,.csv,.xml,.json,.zip,.txt,.pdf";

export type LinkModule = "clause31" | "clause44" | "all";
export type DeliverTo = "app" | "drive";
export interface UploadLink { id: string; token: string; module: LinkModule; deliver_to?: DeliverTo; message: string | null; expires_at: string; revoked_at: string | null; created_at: string; created_by: string | null }
export interface ClientLinkInfo { firm: string; client: string; ay: string; module: LinkModule; deliver_to?: DeliverTo; drive_url?: string | null; message: string | null; expires_at: string; firm_id: string; engagement_id: string; files: { name: string; size: number | null; at: string }[] }

export const MODULE_LABEL: Record<LinkModule, string> = { clause31: "Clause 31 – loans and deposits", clause44: "Clause 44 – expenditure", all: "Tally data for the tax audit" };

export const linkUrl = (token: string, origin = typeof window !== "undefined" ? window.location.origin : "") => `${origin}/u/${token}`;

/** The database change for links has not been made yet. */
export function linksNotReady(e: unknown): boolean {
  const m = e as { code?: string; message?: string } | null;
  return !!m && (m.code === "42P01" || m.code === "PGRST205" || m.code === "PGRST202" || /upload_links|client_link_/i.test(m.message ?? "") && /not find|does not exist|schema cache/i.test(m.message ?? ""));
}

/** Storage path for a client's file. */
export function clientFilePath(info: Pick<ClientLinkInfo, "firm_id" | "engagement_id">, token: string, fileName: string, now = Date.now()) {
  const safe = fileName.replace(/[^\w.\- ]+/g, "_").replace(/\s+/g, "_").replace(/\.{2,}/g, ".").slice(-120) || "file";
  return `${info.firm_id}/${info.engagement_id}/client/${token}/${now}_${safe}`;
}

export function defaultLinkMessage(o: { name: string; module: LinkModule; ay: string; firm: string }) {
  const what = o.module === "clause31"
    ? "the Tally Day Book (or loan / unsecured loan ledgers) as XML, Excel or ZIP"
    : o.module === "all" ? "your Tally data (the button on the page brings it from Tally) or the exported files"
    : "the expense ledgers / purchase register as Excel, CSV, Tally XML or ZIP";
  return [`Dear ${o.name},`, "", `For your tax audit (AY ${o.ay}), please send ${what} at this link:`, "{link}", "", `No login is needed. The link works for ${CLIENT_LINK_DAYS} days.`, "", "Regards,", o.firm].join("\n");
}
