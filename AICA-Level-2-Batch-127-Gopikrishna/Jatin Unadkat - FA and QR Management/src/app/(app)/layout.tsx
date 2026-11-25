import Link from "next/link";
import { requireSession } from "@/lib/rbac";
import SignOutButton from "@/components/SignOutButton";

type Role = "ADMIN" | "LOCATION_HEAD" | "READ_ONLY" | "VERIFIER";

const NAV: { href: string; label: string; roles: Role[] }[] = [
  { href: "/dashboard", label: "Dashboard", roles: ["ADMIN", "LOCATION_HEAD", "READ_ONLY", "VERIFIER"] },
  { href: "/scan", label: "Scan QR", roles: ["ADMIN", "LOCATION_HEAD", "READ_ONLY", "VERIFIER"] },
  { href: "/assets", label: "Assets", roles: ["ADMIN", "LOCATION_HEAD", "READ_ONLY", "VERIFIER"] },
  { href: "/mismatches", label: "Mismatches", roles: ["ADMIN", "LOCATION_HEAD"] },
  { href: "/exceptions", label: "Exceptions", roles: ["ADMIN", "LOCATION_HEAD"] },
  { href: "/locations", label: "Locations", roles: ["ADMIN", "LOCATION_HEAD"] },
  { href: "/qr/bulk", label: "Bulk QR", roles: ["ADMIN", "LOCATION_HEAD"] },
  { href: "/campaigns", label: "Campaigns", roles: ["ADMIN"] },
  { href: "/reports", label: "Reports", roles: ["ADMIN", "LOCATION_HEAD"] },
  { href: "/sap-import", label: "SAP Import", roles: ["ADMIN"] },
  { href: "/sap-import-history", label: "SAP Import History", roles: ["ADMIN"] },
  { href: "/sap-export", label: "SAP Export", roles: ["ADMIN", "LOCATION_HEAD"] },
  { href: "/sap-export-history", label: "SAP Export History", roles: ["ADMIN"] },
  { href: "/sap-export-template", label: "SAP Export Template", roles: ["ADMIN"] },
  { href: "/sap-custom-fields", label: "SAP Custom Fields", roles: ["ADMIN"] },
  { href: "/location-heads", label: "Location Heads", roles: ["ADMIN"] },
  { href: "/users", label: "Users", roles: ["ADMIN"] },
  { href: "/audit-logs", label: "Audit Logs", roles: ["ADMIN"] },
];

const ROLE_LABEL: Record<string, string> = {
  ADMIN: "Admin",
  LOCATION_HEAD: "Location Head",
  READ_ONLY: "Read-only",
  VERIFIER: "Verifier",
};

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const session = await requireSession();
  const role = session.user.role;
  const items = NAV.filter((item) => item.roles.includes(role));

  return (
    <div className="min-h-screen flex flex-col md:flex-row">
      <aside className="md:w-60 border-b md:border-b-0 md:border-r border-line bg-card">
        <div className="p-4 border-b border-line">
          <div className="flex items-center gap-2">
            <span className="pill bg-accent-soft text-accent font-mono text-[10px]">FA-QR</span>
            <span className="font-semibold">AssetTrace</span>
          </div>
        </div>
        <nav className="p-2 flex md:flex-col gap-1 overflow-x-auto md:overflow-visible">
          {items.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="px-3 py-2 rounded-md text-sm text-foreground/80 hover:bg-accent-soft hover:text-accent whitespace-nowrap"
            >
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="p-4 border-t border-line mt-2 text-xs text-muted hidden md:block">
          <p className="font-medium text-foreground">{session.user.name}</p>
          <p className="pill bg-steel-soft text-steel mt-1">{ROLE_LABEL[role]}</p>
          <SignOutButton />
        </div>
      </aside>
      <main className="flex-1 p-5 md:p-8 max-w-6xl">{children}</main>
    </div>
  );
}
