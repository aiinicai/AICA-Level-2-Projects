import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { supabase } from "@/integrations/supabase/client";
import { useAuth } from "./AuthContext";
import type { Role } from "@/lib/db";

export interface Firm {
  id: string;
  name: string;
  frn: string | null;
  gstin: string | null;
  pan: string | null;
  address: string | null;
  city: string | null;
  state: string | null;
  pincode: string | null;
  email: string | null;
  phone: string | null;
  logo_url: string | null;
  partner_name: string | null;
  membership_no: string | null;
  plan: string;
  trial_ends_at: string;
  status: string;
  /** Firm-level settings, e.g. drive_url (the firm's Google Drive script). */
  settings?: { drive_url?: string | null; drive_key?: string | null; [k: string]: unknown } | null;
}

interface FirmState {
  firms: (Firm & { role: Role })[];
  firm: (Firm & { role: Role }) | null;
  role: Role | null;
  loading: boolean;
  switchFirm: (id: string) => void;
  refresh: () => Promise<void>;
}

const FirmCtx = createContext<FirmState | undefined>(undefined);
const KEY = "3cd.currentFirm";

export function FirmProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const [firms, setFirms] = useState<(Firm & { role: Role })[]>([]);
  const [currentId, setCurrentId] = useState<string | null>(null);
  // Read the remembered firm after mount (browser storage is not available during server render).
  useEffect(() => {
    try { setCurrentId(localStorage.getItem(KEY)); } catch { /* ignore */ }
  }, []);
  const [loadedFor, setLoadedFor] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    if (!user) { setFirms([]); setLoadedFor(null); return; }
    setBusy(true);
    await supabase.rpc("accept_my_invitations");
    const { data, error } = await supabase
      .from("firm_members")
      .select("role, firms(*)")
      .eq("user_id", user.id);
    if (!error && data) {
      const list = (data as any[])
        .filter((r) => r.firms)
        .map((r) => ({ ...(r.firms as Firm), role: r.role as Role }))
        .sort((a, b) => a.name.localeCompare(b.name));
      setFirms(list);
    }
    setLoadedFor(user.id);
    setBusy(false);
  }, [user]);

  useEffect(() => { refresh(); }, [refresh]);

  // Loading until firms are fetched for the *current* user (avoids a redirect flash after login).
  const loading = !!user && (loadedFor !== user.id || (busy && firms.length === 0));
  const firm = firms.find((f) => f.id === currentId) ?? firms[0] ?? null;

  const switchFirm = (id: string) => {
    setCurrentId(id);
    try { localStorage.setItem(KEY, id); } catch { /* ignore */ }
  };

  return (
    <FirmCtx.Provider value={{ firms, firm, role: firm?.role ?? null, loading, switchFirm, refresh }}>
      {children}
    </FirmCtx.Provider>
  );
}

export function useFirm() {
  const v = useContext(FirmCtx);
  if (!v) throw new Error("useFirm must be used inside FirmProvider");
  return v;
}
