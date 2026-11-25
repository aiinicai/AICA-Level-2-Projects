import Link from "next/link";
import { requireRole } from "@/lib/rbac";
import { prisma } from "@/lib/prisma";
import { format } from "date-fns";
import { createCampaign } from "@/actions/campaigns";

export default async function CampaignsPage() {
  await requireRole("ADMIN");
  const [campaigns, departments] = await Promise.all([
    prisma.verificationCampaign.findMany({ orderBy: { startDate: "desc" }, include: { _count: { select: { records: true } } } }),
    prisma.department.findMany({ where: { isActive: true }, orderBy: { name: "asc" } }),
  ]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Verification Campaigns</h1>
        <p className="text-sm text-muted mt-1">Organize periodic physical verification and track it to completion.</p>
      </div>

      <div className="card p-5">
        <h2 className="text-sm font-semibold mb-3">New campaign</h2>
        <form action={createCampaign} className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="md:col-span-2">
            <label className="label" htmlFor="name">Name</label>
            <input id="name" name="name" required className="input" placeholder="FY 2026-27 Annual Fixed Asset Verification" />
          </div>
          <div>
            <label className="label" htmlFor="startDate">Start date</label>
            <input id="startDate" name="startDate" type="date" required className="input" />
          </div>
          <div>
            <label className="label" htmlFor="endDate">End date</label>
            <input id="endDate" name="endDate" type="date" required className="input" />
          </div>
          <div className="md:col-span-2">
            <label className="label">Departments in scope (leave empty for all)</label>
            <div className="flex flex-wrap gap-3">
              {departments.map((d) => (
                <label key={d.id} className="flex items-center gap-1.5 text-sm">
                  <input type="checkbox" name="departmentIds" value={d.id} />
                  {d.name}
                </label>
              ))}
            </div>
          </div>
          <div className="md:col-span-2">
            <button type="submit" className="btn-primary">Create campaign</button>
          </div>
        </form>
      </div>

      <div className="card overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-wide text-muted border-b border-line">
              <th className="py-2 px-4">Name</th>
              <th className="py-2 px-4">Window</th>
              <th className="py-2 px-4">Status</th>
              <th className="py-2 px-4">Verifications logged</th>
            </tr>
          </thead>
          <tbody>
            {campaigns.map((c) => (
              <tr key={c.id} className="border-b border-line last:border-0">
                <td className="py-2 px-4"><Link href={`/campaigns/${c.id}`} className="text-steel hover:underline">{c.name}</Link></td>
                <td className="py-2 px-4 text-muted">{format(c.startDate, "dd MMM yyyy")} – {format(c.endDate, "dd MMM yyyy")}</td>
                <td className="py-2 px-4"><span className="pill bg-steel-soft text-steel">{c.status}</span></td>
                <td className="py-2 px-4">{c._count.records}</td>
              </tr>
            ))}
            {campaigns.length === 0 && <tr><td colSpan={4} className="py-8 text-center text-muted">No campaigns yet.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
