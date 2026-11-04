// Same-origin relative path only.
export function safeRedirect(v: unknown): string {
  if (typeof v !== "string") return "/";
  try {
    const u = new URL(v, "http://x");
    if (v.startsWith("http")) {
      if (typeof window === "undefined" || new URL(v).origin !== window.location.origin) return "/";
    } else if (!v.startsWith("/") || v.startsWith("//")) return "/";
    if (u.pathname === "/auth" || u.pathname.startsWith("/auth/")) return "/";
    return u.pathname + u.search + u.hash;
  } catch {
    return "/";
  }
}
export const REDIRECT_KEY = "fsrm_after_login";
