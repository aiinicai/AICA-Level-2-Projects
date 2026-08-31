import { requireRole } from "@/lib/rbac";
import { prisma } from "@/lib/prisma";
import { getLocationOptions } from "@/lib/locations";
import { assignLocationHead, removeLocationHeadAssignment } from "@/actions/locationHeads";

export default async function LocationHeadsPage() {
  await requireRole("ADMIN");
  const [assignments, locationHeadUsers, locations] = await Promise.all([
    prisma.locationHeadAssignment.findMany({ include: { user: true, location: true }, orderBy: { assignedAt: "desc" } }),
    prisma.user.findMany({ where: { role: { name: "LOCATION_HEAD" }, isActive: true } }),
    getLocationOptions(),
  ]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Location Head Assignments</h1>
        <p className="text-sm text-muted mt-1">
          Scope cascades to every sub-location beneath the assigned location — a Location Head cannot see or manage
          anything outside their assignment(s).
        </p>
      </div>

      <div className="card p-5">
        <h2 className="text-sm font-semibold mb-3">Assign a scope</h2>
        <form action={assignLocationHead} className="flex flex-wrap gap-3 items-end">
          <div className="flex-1 min-w-[200px]">
            <label className="label" htmlFor="userId">Location Head</label>
            <select id="userId" name="userId" required className="input">
              <option value="" disabled>Select a user…</option>
              {locationHeadUsers.map((u) => <option key={u.id} value={u.id}>{u.fullName}</option>)}
            </select>
          </div>
          <div className="flex-1 min-w-[220px]">
            <label className="label" htmlFor="locationId">Location</label>
            <select id="locationId" name="locationId" required className="input">
              <option value="" disabled>Select a location…</option>
              {locations.map((l) => <option key={l.id} value={l.id}>{l.label}</option>)}
            </select>
          </div>
          <button type="submit" className="btn-primary">Assign</button>
        </form>
        {locationHeadUsers.length === 0 && (
          <p className="text-xs text-muted mt-3">No Location Head users yet — create one on the <a href="/users" className="text-steel hover:underline">Users</a> page first.</p>
        )}
      </div>

      <div className="card overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-wide text-muted border-b border-line">
              <th className="py-2 px-4">Location Head</th>
              <th className="py-2 px-4">Location</th>
              <th className="py-2 px-4">Assigned</th>
              <th className="py-2 px-4 text-right">Action</th>
            </tr>
          </thead>
          <tbody>
            {assignments.map((a) => (
              <tr key={a.id} className="border-b border-line last:border-0">
                <td className="py-2 px-4">{a.user.fullName}</td>
                <td className="py-2 px-4">{a.location.fullPath}</td>
                <td className="py-2 px-4 text-muted">{a.assignedAt.toLocaleDateString()}</td>
                <td className="py-2 px-4 text-right">
                  <form action={async () => { "use server"; await removeLocationHeadAssignment(a.id); }}>
                    <button type="submit" className="text-xs text-bad hover:underline">Remove</button>
                  </form>
                </td>
              </tr>
            ))}
            {assignments.length === 0 && <tr><td colSpan={4} className="py-8 text-center text-muted">No assignments yet.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
