import Link from "next/link";

export default function ForbiddenPage() {
  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="card p-8 max-w-sm text-center space-y-3">
        <p className="pill bg-bad-soft text-bad font-mono mx-auto">403</p>
        <h1 className="text-lg font-semibold">Not permitted</h1>
        <p className="text-sm text-muted">Your role doesn&apos;t have access to this page. If you believe this is wrong, contact your Admin.</p>
        <Link href="/dashboard" className="btn-primary inline-flex">Back to dashboard</Link>
      </div>
    </div>
  );
}
