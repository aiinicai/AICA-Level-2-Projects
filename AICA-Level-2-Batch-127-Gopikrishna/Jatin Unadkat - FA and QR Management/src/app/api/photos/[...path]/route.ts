import { NextResponse } from "next/server";
import path from "path";
import { requireRoleApi } from "@/lib/rbac";
import { readVarFile } from "@/lib/fileStorage";

export async function GET(_request: Request, { params }: { params: Promise<{ path: string[] }> }) {
  // Every role can view photographs (design dossier, Section G) — just needs
  // a real session, no role restriction.
  const auth = await requireRoleApi("ADMIN", "LOCATION_HEAD", "VERIFIER", "READ_ONLY");
  if (!auth.ok) return NextResponse.json({ error: "Unauthorized" }, { status: auth.status });

  const { path: segments } = await params;
  // Reject any segment that could escape the photos/ directory.
  if (segments.some((s) => s.includes("..") || s.includes("/") || s.includes("\\"))) {
    return NextResponse.json({ error: "Invalid path" }, { status: 400 });
  }

  try {
    const buffer = await readVarFile(path.join("photos", ...segments));
    return new NextResponse(new Uint8Array(buffer), {
      headers: {
        "Content-Type": "image/webp",
        "Cache-Control": "private, max-age=86400",
      },
    });
  } catch {
    return NextResponse.json({ error: "Not found" }, { status: 404 });
  }
}
