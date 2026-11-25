import { requireRole } from "@/lib/rbac";
import { prisma } from "@/lib/prisma";
import { createUser, setUserActive } from "@/actions/users";

export default async function UsersPage() {
  const session = await requireRole("ADMIN");
  const users = await prisma.user.findMany({ include: { role: true }, orderBy: { createdAt: "asc" } });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">User Management</h1>
        <p className="text-sm text-muted mt-1">Create accounts and assign roles.</p>
      </div>

      <div className="card p-5">
        <h2 className="text-sm font-semibold mb-3">Add user</h2>
        <form action={createUser} className="grid grid-cols-1 md:grid-cols-4 gap-3 items-end">
          <div>
            <label className="label" htmlFor="fullName">Full name</label>
            <input id="fullName" name="fullName" required className="input" />
          </div>
          <div>
            <label className="label" htmlFor="email">Email</label>
            <input id="email" name="email" type="email" required className="input" />
          </div>
          <div>
            <label className="label" htmlFor="password">Password</label>
            <input id="password" name="password" type="password" required minLength={8} className="input" />
          </div>
          <div>
            <label className="label" htmlFor="roleName">Role</label>
            <select id="roleName" name="roleName" className="input">
              <option value="VERIFIER">Verifier</option>
              <option value="LOCATION_HEAD">Location Head</option>
              <option value="READ_ONLY">Read-only</option>
              <option value="ADMIN">Admin</option>
            </select>
          </div>
          <div className="md:col-span-4">
            <button type="submit" className="btn-primary">Create user</button>
          </div>
        </form>
      </div>

      <div className="card overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-wide text-muted border-b border-line">
              <th className="py-2 px-4">Name</th>
              <th className="py-2 px-4">Email</th>
              <th className="py-2 px-4">Role</th>
              <th className="py-2 px-4">Status</th>
              <th className="py-2 px-4 text-right">Action</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id} className="border-b border-line last:border-0">
                <td className="py-2 px-4">{u.fullName}</td>
                <td className="py-2 px-4 text-muted">{u.email}</td>
                <td className="py-2 px-4"><span className="pill bg-steel-soft text-steel">{u.role.name.replace("_", " ")}</span></td>
                <td className="py-2 px-4">
                  <span className={`pill ${u.isActive ? "bg-good-soft text-good" : "bg-bad-soft text-bad"}`}>{u.isActive ? "Active" : "Inactive"}</span>
                </td>
                <td className="py-2 px-4 text-right">
                  {u.id !== session.user.id && (
                    <form action={async () => { "use server"; await setUserActive(u.id, !u.isActive); }}>
                      <button type="submit" className="text-xs text-steel hover:underline">{u.isActive ? "Deactivate" : "Reactivate"}</button>
                    </form>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
