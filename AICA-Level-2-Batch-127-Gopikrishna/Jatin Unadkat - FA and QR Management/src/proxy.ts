import { NextResponse } from "next/server";
import { auth } from "@/auth";

// Optimistic check only (Next.js Proxy is not a full auth solution) — every
// page and Server Action still calls requireSession/requireRole itself
// (design dossier, Section G / N).
const PUBLIC_PREFIXES = ["/login", "/forbidden", "/a/"];

// ⚠️ TEMPORARY, TESTING-ONLY BYPASS — see src/lib/rbac.ts for the matching
// half of this. Sidesteps a mobile-browser login issue over a Cloudflare
// quick tunnel. Every visitor becomes a full Admin, no login required.
// Set DISABLE_AUTH_FOR_TESTING=false (or delete the var) in .env to restore
// normal login before this app ever holds real data or goes anywhere
// non-ephemeral.
const AUTH_DISABLED = process.env.DISABLE_AUTH_FOR_TESTING === "true";

export default AUTH_DISABLED
  ? function bypassProxy() {
      return NextResponse.next();
    }
  : auth((req) => {
      const { pathname } = req.nextUrl;
      const isPublic = PUBLIC_PREFIXES.some((p) => pathname.startsWith(p));
      if (!req.auth && !isPublic) {
        const loginUrl = new URL("/login", req.nextUrl.origin);
        loginUrl.searchParams.set("callbackUrl", pathname);
        return NextResponse.redirect(loginUrl);
      }
    });

export const config = {
  matcher: ["/((?!api/auth|_next/static|_next/image|favicon.ico|uploads).*)"],
};
