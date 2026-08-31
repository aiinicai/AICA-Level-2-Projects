import { requireRole } from "@/lib/rbac";

const REPORTS: { type: string; label: string }[] = [
  { type: "asset-master", label: "Asset Master Report" },
  { type: "verification", label: "Verification Report" },
  { type: "location-mismatch", label: "Location Mismatch Report" },
  { type: "missing", label: "Missing Asset Report" },
  { type: "damaged", label: "Damaged Asset Report" },
  { type: "pending", label: "Verification Pending Report" },
  { type: "movement-history", label: "Asset Movement / Location History" },
  { type: "audit-trail", label: "Verification Audit Trail" },
  { type: "qr-register", label: "QR Code Register" },
];

export default async function ReportsPage() {
  const session = await requireRole("ADMIN", "LOCATION_HEAD");
  const reports = session.user.role === "LOCATION_HEAD" ? REPORTS.filter((r) => r.type !== "audit-trail") : REPORTS;
  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-semibold">Reports</h1>
        <p className="text-sm text-muted mt-1">
          Exports as CSV, ready to open in Excel. PDF/formatted exports are a Phase 2 enhancement.
          {session.user.role === "LOCATION_HEAD" && " Scoped to your assigned location(s)."}
        </p>
      </div>
      <div className="card divide-y divide-line">
        {reports.map((r) => (
          <div key={r.type} className="p-4 flex items-center justify-between">
            <span className="text-sm font-medium">{r.label}</span>
            <a href={`/api/reports/${r.type}`} className="btn-secondary text-xs px-3 py-1.5">Export CSV</a>
          </div>
        ))}
      </div>
    </div>
  );
}
