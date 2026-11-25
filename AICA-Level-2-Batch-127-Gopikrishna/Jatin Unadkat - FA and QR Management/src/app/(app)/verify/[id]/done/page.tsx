import Link from "next/link";
import { requireRole } from "@/lib/rbac";

export default async function VerificationDonePage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ result?: string }>;
}) {
  await requireRole("ADMIN", "VERIFIER", "LOCATION_HEAD");
  const { id } = await params;
  const { result } = await searchParams;

  return (
    <div className="max-w-sm mx-auto space-y-4 text-center">
      <div className="card p-8 space-y-3">
        <p className="pill bg-good-soft text-good mx-auto">Submitted</p>
        <h1 className="text-lg font-semibold">Verification recorded</h1>
        <p className="text-sm text-muted">Result: {result?.replaceAll("_", " ") ?? "—"}. Timestamp and your identity were captured automatically.</p>
      </div>
      <div className="flex gap-2 justify-center">
        <Link href={`/assets/${id}`} className="btn-secondary">View asset</Link>
        <Link href="/scan" className="btn-primary">Scan next</Link>
      </div>
    </div>
  );
}
