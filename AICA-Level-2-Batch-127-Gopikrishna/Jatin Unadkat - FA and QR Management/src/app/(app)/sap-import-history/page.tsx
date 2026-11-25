import { requireRole } from "@/lib/rbac";
import { prisma } from "@/lib/prisma";
import { format } from "date-fns";

export default async function SapImportHistoryPage() {
  await requireRole("ADMIN");
  const batches = await prisma.sapImportBatch.findMany({
    include: { importedBy: true, _count: { select: { errors: true } } },
    orderBy: { importedAt: "desc" },
  });

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-semibold">SAP Import History</h1>
        <p className="text-sm text-muted mt-1">Every import batch, append-only. Error details are downloadable per batch.</p>
      </div>
      <div className="card overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-wide text-muted border-b border-line">
              <th className="py-2 px-4">File</th>
              <th className="py-2 px-4">Imported</th>
              <th className="py-2 px-4">By</th>
              <th className="py-2 px-4">Total</th>
              <th className="py-2 px-4">New</th>
              <th className="py-2 px-4">Updated</th>
              <th className="py-2 px-4">Unchanged</th>
              <th className="py-2 px-4">Errors</th>
              <th className="py-2 px-4">Status</th>
              <th className="py-2 px-4"></th>
            </tr>
          </thead>
          <tbody>
            {batches.map((b) => (
              <tr key={b.id} className="border-b border-line last:border-0">
                <td className="py-2 px-4 font-mono text-xs">{b.fileName}</td>
                <td className="py-2 px-4 text-muted">{format(b.importedAt, "dd MMM yyyy, HH:mm")}</td>
                <td className="py-2 px-4">{b.importedBy?.fullName ?? "—"}</td>
                <td className="py-2 px-4">{b.totalRows}</td>
                <td className="py-2 px-4 text-good">{b.newRecords}</td>
                <td className="py-2 px-4 text-warn">{b.updatedRecords}</td>
                <td className="py-2 px-4 text-muted">{b.unchangedRecords}</td>
                <td className="py-2 px-4 text-bad">{b.errorRecords}</td>
                <td className="py-2 px-4"><span className="pill bg-steel-soft text-steel">{b.status.replaceAll("_", " ")}</span></td>
                <td className="py-2 px-4">
                  {b._count.errors > 0 && (
                    <a href={`/api/sap-import/${b.id}/errors`} className="text-xs text-steel hover:underline">Download errors</a>
                  )}
                </td>
              </tr>
            ))}
            {batches.length === 0 && <tr><td colSpan={10} className="py-8 text-center text-muted">No imports yet.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
