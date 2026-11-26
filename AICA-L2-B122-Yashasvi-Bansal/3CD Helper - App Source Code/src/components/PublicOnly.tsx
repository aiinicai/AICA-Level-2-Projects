import { useEffect, type ReactNode } from "react";
import { useNavigate } from "@tanstack/react-router";
import { useAuth } from "@/contexts/AuthContext";

/** Sign-in pages: forward signed-in users to the app (also completes Google / email-link sign-in). */
export function PublicOnly({ children }: { children: ReactNode }) {
  const { session, loading } = useAuth();
  const nav = useNavigate();
  useEffect(() => {
    if (!loading && session) nav({ to: "/app", replace: true });
  }, [loading, session, nav]);
  return <>{children}</>;
}
