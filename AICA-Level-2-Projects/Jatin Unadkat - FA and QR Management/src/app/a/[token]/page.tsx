import { redirect } from "next/navigation";
import { auth } from "@/auth";
import { prisma } from "@/lib/prisma";

export default async function ResolveQrPage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;
  const session = await auth();
  if (!session?.user) {
    redirect(`/login?callbackUrl=${encodeURIComponent(`/a/${token}`)}`);
  }

  const qr = await prisma.qrCode.findUnique({ where: { token }, include: { asset: true } });

  if (!qr || !qr.isActive || !qr.asset.isActive) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <div className="card p-8 max-w-sm text-center space-y-2">
          <p className="pill bg-bad-soft text-bad mx-auto">QR not recognized</p>
          <p className="text-sm text-muted">
            This code is unknown, inactive, or has been superseded by a reprinted label. Try searching for the asset instead.
          </p>
        </div>
      </div>
    );
  }

  if (session.user.role === "VERIFIER") {
    redirect(`/verify/${qr.assetId}`);
  }
  redirect(`/assets/${qr.assetId}`);
}
