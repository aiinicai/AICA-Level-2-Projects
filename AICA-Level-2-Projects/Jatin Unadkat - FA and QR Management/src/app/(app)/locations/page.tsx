import { requireRole } from "@/lib/rbac";
import { getLocationTree, getLocationOptions, type LocationNode } from "@/lib/locations";
import { getLocationHeadScopeRoots, isInScope } from "@/lib/locationScope";
import { createLocation, setLocationActive } from "@/actions/locations";

function pruneToScope(nodes: LocationNode[], roots: string[]): LocationNode[] {
  return nodes
    .map((n) => ({ ...n, children: pruneToScope(n.children, roots) }))
    .filter((n) => isInScope(n.fullPath, roots) || n.children.length > 0);
}

function LocationRow({ node, depth, canManage }: { node: LocationNode; depth: number; canManage: boolean }) {
  return (
    <>
      <tr className="border-b border-line last:border-0">
        <td className="py-2 pr-4" style={{ paddingLeft: `${depth * 20}px` }}>
          <span className={depth === 0 ? "font-semibold" : ""}>{node.name}</span>
        </td>
        <td className="py-2 pr-4 text-muted font-mono text-xs">L{node.levelNumber}</td>
        <td className="py-2 pr-4">
          <span className={`pill ${node.isActive ? "bg-good-soft text-good" : "bg-bad-soft text-bad"}`}>
            {node.isActive ? "Active" : "Inactive"}
          </span>
        </td>
        <td className="py-2 text-right">
          {canManage && (
            <form
              action={async () => {
                "use server";
                await setLocationActive(node.id, !node.isActive);
              }}
            >
              <button type="submit" className="text-xs text-steel hover:underline">
                {node.isActive ? "Deactivate" : "Reactivate"}
              </button>
            </form>
          )}
        </td>
      </tr>
      {node.children.map((child) => (
        <LocationRow key={child.id} node={child} depth={depth + 1} canManage={canManage} />
      ))}
    </>
  );
}

export default async function LocationsPage() {
  const session = await requireRole("ADMIN", "LOCATION_HEAD");
  const isLocationHead = session.user.role === "LOCATION_HEAD";

  const [fullTree, allOptions] = await Promise.all([getLocationTree(), getLocationOptions()]);
  const roots = isLocationHead ? await getLocationHeadScopeRoots(session.user.id) : [];

  const tree = isLocationHead ? pruneToScope(fullTree, roots) : fullTree;
  const options = isLocationHead ? allOptions.filter((o) => isInScope(o.label, roots)) : allOptions;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Location Management</h1>
        <p className="text-sm text-muted mt-1">
          {isLocationHead
            ? "Your assigned location and its sub-locations. Deactivating a node is blocked while active assets are assigned to it."
            : "Configure your own hierarchy — any depth, any labels. Deactivating a node is blocked while active assets are assigned to it."}
        </p>
      </div>

      <div className="card p-5">
        <h2 className="text-sm font-semibold mb-3">Add a {isLocationHead ? "sub-location" : "location"}</h2>
        <form action={createLocation} className="flex flex-wrap gap-3 items-end">
          <div className="flex-1 min-w-[180px]">
            <label className="label" htmlFor="name">Name</label>
            <input id="name" name="name" required className="input" placeholder="e.g. Room 210" />
          </div>
          <div className="flex-1 min-w-[220px]">
            <label className="label" htmlFor="parentLocationId">
              Parent {!isLocationHead && "(optional — leave blank for a top level)"}
            </label>
            <select id="parentLocationId" name="parentLocationId" required={isLocationHead} className="input">
              {!isLocationHead && <option value="">— Top level —</option>}
              {options.map((o) => (
                <option key={o.id} value={o.id}>{o.label}</option>
              ))}
            </select>
          </div>
          <button type="submit" className="btn-primary">Add location</button>
        </form>
      </div>

      <div className="card p-5 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-wide text-muted border-b border-line">
              <th className="py-2 pr-4">Name</th>
              <th className="py-2 pr-4">Level</th>
              <th className="py-2 pr-4">Status</th>
              <th className="py-2 text-right">Action</th>
            </tr>
          </thead>
          <tbody>
            {tree.map((node) => (
              <LocationRow key={node.id} node={node} depth={0} canManage={true} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
