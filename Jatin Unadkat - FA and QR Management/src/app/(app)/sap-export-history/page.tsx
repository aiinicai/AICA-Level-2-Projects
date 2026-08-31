import { requireRole } from "@/lib/rbac";
import { prisma } from "@/lib/prisma";
import { format } from "date-fns";

export default async function SapExportHistoryPage() {
  await requireRole("ADMIN");
  const batches = await prisma.sapExportBatch.findMany({
    include: { generatedBy: true, _count: { select: { records: true } } },
    orderBy: { generatedAt: "desc" },
  });

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-semibold">SAP Export History</h1>
        <p className="text-sm text-muted mt-1">Every SAP upload file generated, who generated it, and which records were included.</p>
      </div>
      <div className="card overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-wide text-muted border-b border-line">
              <th className="py-2 px-4">File</th>
              <th className="py-2 px-4">Generated</th>
              <th className="py-2 px-4">By</th>
              <th className="py-2 px-4">Records</th>
              <th className="py-2 px-4">Status</th>
              <th className="py-2 px-4"></th>
            </tr>
          </thead>
          <tbody>
            {batches.map((b) => (
              <tr key={b.id} className="border-b border-line last:border-0">
                <td className="py-2 px-4 font-mono text-xs">{b.fileName}</td>
                <td className="py-2 px-4 text-muted">{format(b.generatedAt, "dd MMM yyyy, HH:mm")}</td>
                <td className="py-2 px-4">{b.generatedBy?.fullName ?? "—"}</td>
                <td className="py-2 px-4">{b._count.records}</td>
                <td className="py-2 px-4"><span className="pill bg-steel-soft text-steel">{b.status}</span></td>
                <td className="py-2 px-4"><a href={`/api/sap-export/${b.id}/download`} className="text-xs text-steel hover:underline">Download</a></td>
              </tr>
            ))}
            {batches.length === 0 && <tr><td colSpan={6} className="py-8 text-center text-muted">No exports yet.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
