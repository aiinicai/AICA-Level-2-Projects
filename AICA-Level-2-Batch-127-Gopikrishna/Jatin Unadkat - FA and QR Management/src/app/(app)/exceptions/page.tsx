import Link from "next/link";
import { requireRole } from "@/lib/rbac";
import { prisma } from "@/lib/prisma";
import { getLocationHeadScopeRoots, locationScopeWhereClause } from "@/lib/locationScope";
import { format } from "date-fns";
import { assignException, resolveException, reviewException } from "@/actions/exceptions";

const STATUS_STYLE: Record<string, string> = {
  OPEN: "bg-warn-soft text-warn",
  ASSIGNED: "bg-steel-soft text-steel",
  RESOLVED: "bg-good-soft text-good",
};

export default async function ExceptionsPage() {
  const session = await requireRole("ADMIN", "LOCATION_HEAD");
  const isLocationHead = session.user.role === "LOCATION_HEAD";

  const assetFilter = isLocationHead
    ? { currentLocation: { is: locationScopeWhereClause(await getLocationHeadScopeRoots(session.user.id)) } }
    : {};

  const [exceptions, assignees] = await Promise.all([
    prisma.exception.findMany({
      where: { status: { not: "RESOLVED" }, asset: assetFilter },
      include: { asset: true, assignedTo: true, reviewedBy: true },
      orderBy: { createdAt: "desc" },
    }),
    prisma.user.findMany({ where: { role: { name: { in: ["ADMIN", "LOCATION_HEAD"] } }, isActive: true } }),
  ]);

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-semibold">Exception Queue</h1>
        <p className="text-sm text-muted mt-1">Open items raised by verification: not found, damaged, found elsewhere, and more.</p>
      </div>

      <div className="card divide-y divide-line">
        {exceptions.map((e) => (
          <div key={e.id} className="p-4 space-y-2">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <div>
                <Link href={`/assets/${e.assetId}`} className="font-mono text-sm text-steel hover:underline">{e.asset.assetNumber}</Link>
                <span className="text-sm ml-2">{e.asset.description}</span>
              </div>
              <div className="flex items-center gap-2">
                {e.reviewDecision && (
                  <span className={`pill ${e.reviewDecision === "APPROVED" ? "bg-good-soft text-good" : "bg-bad-soft text-bad"}`}>{e.reviewDecision}</span>
                )}
                <span className={`pill ${STATUS_STYLE[e.status]}`}>{e.status}</span>
              </div>
            </div>
            <p className="text-sm text-muted">{e.type.replaceAll("_", " ")} · raised {format(e.createdAt, "dd MMM yyyy")}</p>
            <div className="flex flex-wrap gap-3 items-center pt-1">
              {!e.reviewDecision && (
                <div className="flex gap-2">
                  <form action={async () => { "use server"; await reviewException(e.id, "APPROVED"); }}>
                    <button type="submit" className="btn-secondary text-xs px-2 py-1 text-good">Approve</button>
                  </form>
                  <form action={async () => { "use server"; await reviewException(e.id, "REJECTED"); }}>
                    <button type="submit" className="btn-secondary text-xs px-2 py-1 text-bad">Reject</button>
                  </form>
                </div>
              )}
              <form
                action={async (formData: FormData) => {
                  "use server";
                  await assignException(e.id, String(formData.get("assignedToId")));
                }}
                className="flex items-center gap-2"
              >
                <select name="assignedToId" defaultValue={e.assignedTo?.id ?? ""} className="input text-xs py-1">
                  <option value="" disabled>Assign to…</option>
                  {assignees.map((a) => <option key={a.id} value={a.id}>{a.fullName}</option>)}
                </select>
                <button type="submit" className="btn-secondary text-xs px-2 py-1">Assign</button>
              </form>
              <form
                action={async (formData: FormData) => {
                  "use server";
                  await resolveException(e.id, formData);
                }}
                className="flex items-center gap-2 flex-1 min-w-[220px]"
              >
                <input name="resolutionNotes" className="input text-xs py-1" placeholder="Resolution note" />
                <button type="submit" className="btn-primary text-xs px-2 py-1">Resolve</button>
              </form>
            </div>
          </div>
        ))}
        {exceptions.length === 0 && <p className="p-8 text-center text-muted text-sm">No open exceptions in scope. Clean sheet.</p>}
      </div>
    </div>
  );
}
