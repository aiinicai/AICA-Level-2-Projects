import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import type { Session, User } from "@supabase/supabase-js";
import { supabase } from "@/integrations/supabase/client";
import type { Database } from "@/integrations/supabase/types";

export type AppRole = Database["public"]["Enums"]["app_role"];

type AuthState = {
  loading: boolean;
  session: Session | null;
  user: User | null;
  fullName: string;
  supplierAccount: boolean;
  roles: AppRole[];
  hasRole: (...roles: AppRole[]) => boolean;
  refreshRoles: () => Promise<void>;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [roles, setRoles] = useState<AppRole[]>([]);
  const [fullName, setFullName] = useState("");
  const [supplierAccount, setSupplierAccount] = useState(false);
  const [loading, setLoading] = useState(true);

  const loadProfile = async (userId: string) => {
    const [{ data: roleRows }, { data: profile }, { data: account }] = await Promise.all([
      supabase.from("user_roles").select("role").eq("user_id", userId),
      supabase.from("profiles").select("full_name").eq("id", userId).maybeSingle(),
      supabase.from("supplier_accounts").select("user_id").eq("user_id", userId).maybeSingle(),
    ]);
    setSupplierAccount(Boolean(account));
    setRoles((roleRows ?? []).map((r) => r.role));
    setFullName(profile?.full_name ?? "");
  };

  useEffect(() => {
    let active = true;

    const { data } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      if (!active) return;
      setSession(nextSession);
      if (nextSession?.user) {
        void loadProfile(nextSession.user.id);
      } else {
        setRoles([]);
        setSupplierAccount(false);
        setFullName("");
      }
    });

    void supabase.auth.getSession().then(async ({ data: { session: current } }) => {
      if (!active) return;
      setSession(current);
      if (current?.user) await loadProfile(current.user.id);
      setLoading(false);
    });

    return () => {
      active = false;
      data.subscription.unsubscribe();
    };
  }, []);

  const value = useMemo<AuthState>(
    () => ({
      loading,
      session,
      user: session?.user ?? null,
      fullName: fullName || session?.user?.email?.split("@")[0] || "",
      roles,
      supplierAccount: supplierAccount || session?.user?.user_metadata?.['account_type'] === "supplier",
      hasRole: (...wanted: AppRole[]) => wanted.some((r) => roles.includes(r)),
      refreshRoles: async () => {
        if (session?.user) await loadProfile(session.user.id);
      },
      signOut: async () => {
        await supabase.auth.signOut();
      },
    }),
    [loading, session, roles, fullName, supplierAccount],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
