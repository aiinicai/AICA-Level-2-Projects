import { requireRole } from "@/lib/rbac";
import { prisma } from "@/lib/prisma";
import { format } from "date-fns";

export default async function AuditLogsPage({
  searchParams,
}: {
  searchParams: Promise<{ entityType?: string }>;
}) {
  await requireRole("ADMIN");
  const { entityType } = await searchParams;

  const logs = await prisma.auditLog.findMany({
    where: entityType ? { entityType } : undefined,
    include: { user: true },
    orderBy: { occurredAt: "desc" },
    take: 200,
  });

  const entityTypes = [
    "Asset",
    "Location",
    "QrCode",
    "BulkQrJob",
    "VerificationRecord",
    "VerificationCampaign",
    "Exception",
    "User",
    "SapImportBatch",
    "SapExportBatch",
    "SapCustomFieldConfig",
    "LocationHeadAssignment",
  ];

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-semibold">Audit Logs</h1>
        <p className="text-sm text-muted mt-1">Append-only — every create, update, and status change, with old/new values.</p>
      </div>

      <form className="card p-4 flex flex-wrap gap-3 items-end">
        <div>
          <label className="label" htmlFor="entityType">Entity</label>
          <select id="entityType" name="entityType" defaultValue={entityType ?? ""} className="input">
            <option value="">All</option>
            {entityTypes.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
        </div>
        <button type="submit" className="btn-secondary">Filter</button>
      </form>

      <div className="card overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-wide text-muted border-b border-line">
              <th className="py-2 px-4">When</th>
              <th className="py-2 px-4">User</th>
              <th className="py-2 px-4">Action</th>
              <th className="py-2 px-4">Entity</th>
              <th className="py-2 px-4">Old → New</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((l) => (
              <tr key={l.id} className="border-b border-line last:border-0 align-top">
                <td className="py-2 px-4 text-muted whitespace-nowrap font-mono text-xs">{format(l.occurredAt, "dd MMM yyyy, HH:mm:ss")}</td>
                <td className="py-2 px-4">{l.user?.fullName ?? "System"}</td>
                <td className="py-2 px-4"><span className="pill bg-steel-soft text-steel">{l.action}</span></td>
                <td className="py-2 px-4 font-mono text-xs">{l.entityType}<br /><span className="text-muted">{l.entityId.slice(0, 10)}…</span></td>
                <td className="py-2 px-4 font-mono text-[11px] max-w-md">
                  <div className="max-h-20 overflow-y-auto">
                    {l.oldValueJson && <div className="text-bad break-all">– {l.oldValueJson}</div>}
                    {l.newValueJson && <div className="text-good break-all">+ {l.newValueJson}</div>}
                  </div>
                </td>
              </tr>
            ))}
            {logs.length === 0 && <tr><td colSpan={5} className="py-8 text-center text-muted">No audit entries yet.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
