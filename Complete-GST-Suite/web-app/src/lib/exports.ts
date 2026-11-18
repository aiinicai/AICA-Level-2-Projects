import { toast } from "sonner";
import { noticeStatus } from "./gst/notices";
import { summarise } from "./gst/recon";
import { fmtDateTime } from "./gst/format";
import { decideRoute } from "./gst/gsp";
import { getState, latestRun, log, overridesFor, sessionOf, visibleClients } from "./store";

/** One-click client workbook (all working-paper sheets). */
export async function exportClientWorkbook(clientId: string) {
  const s = getState();
  const c = s.clients.find((x) => x.id === clientId);
  if (!c) return;
  const t = toast.loading(`Building the workbook for ${c.name}…`);
  try {
    const x = await import("./gst/excel");
    const run = latestRun(s.runs, clientId, true);
    const blob = await x.buildClientWorkbook({
      client: c,
      firmName: s.firm?.name ?? "",
      tolerance: s.prefs.tolerance,
      dueSoonDays: s.prefs.reminderDays,
      notices: s.notices.filter((n) => n.clientId === clientId),
      overrides9: overridesFor(s.draftOverrides, clientId, "GSTR-9"),
      overrides9c: overridesFor(s.draftOverrides, clientId, "GSTR-9C"),
      inputs9c: s.gstr9cInputs[clientId] ?? {},
      reasons: s.draftReasons,
      summary: run?.summary ?? summarise(clientId, s.prefs.tolerance),
    });
    const name = `GST_${c.name.replace(/[^A-Za-z0-9]+/g, "_")}_FY2025-26.xlsx`;
    x.downloadBlob(name, blob);
    log(`Exported client workbook ${name}`, clientId);
    toast.success("Workbook downloaded", { id: t });
  } catch (e) {
    toast.error(`Could not build the workbook: ${e instanceof Error ? e.message : e}`, { id: t });
  }
}

/** Firm dashboard workbook covering all (visible) clients. */
export async function exportFirmWorkbook() {
  const s = getState();
  const t = toast.loading("Building the firm workbook…");
  try {
    const x = await import("./gst/excel");
    const clients = visibleClients(s);
    const rows = clients.map((c) => {
      const run = latestRun(s.runs, c.id);
      const ns = s.notices.filter((n) => n.clientId === c.id);
      return {
        client: c,
        status: !c.active ? "Inactive" : !run ? "Not run" : run.status === "Failed" ? "Failed" : run.summary?.partialMonths.length ? "Partial data" : run.summary?.differences ? "Difference" : "Matched",
        route: run?.route ?? decideRoute(c, sessionOf(c.id)).route,
        summary: run?.summary,
        openNotices: ns.filter((n) => ["Open", "Due soon", "Overdue"].includes(noticeStatus(n, new Date(), s.prefs.reminderDays))).length,
        overdue: ns.filter((n) => noticeStatus(n, new Date(), s.prefs.reminderDays) === "Overdue").length,
        lastRun: run ? fmtDateTime(run.at) : "",
      };
    });
    const ids = new Set(clients.map((c) => c.id));
    const notices = s.notices.filter((n) => ids.has(n.clientId)).map((n) => ({ ...n, clientName: clients.find((c) => c.id === n.clientId)?.name ?? "" }));
    x.downloadBlob("Firm_Dashboard_FY2025-26.xlsx", await x.buildFirmWorkbook(s.firm?.name ?? "", rows, notices, s.prefs.tolerance, s.prefs.reminderDays));
    log("Exported firm dashboard workbook");
    toast.success("Firm workbook downloaded", { id: t });
  } catch (e) {
    toast.error(`Could not build the workbook: ${e instanceof Error ? e.message : e}`, { id: t });
  }
}

export async function downloadTemplate(kind: "client-master" | "gstr3b-summary" | "notices") {
  const x = await import("./gst/excel");
  x.downloadBlob(x.TEMPLATE_NAMES[kind], await x.buildTemplate(kind));
  log(`Downloaded template ${x.TEMPLATE_NAMES[kind]}`);
}
