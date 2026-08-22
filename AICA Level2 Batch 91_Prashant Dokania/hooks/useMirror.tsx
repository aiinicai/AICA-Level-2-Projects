import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import type { Session } from "@supabase/supabase-js";
import { supabase } from "@/integrations/supabase/client";
import { getDevice } from "@/lib/device";
import { getMirrorState } from "@/lib/mirror.functions";

type StateShape = Awaited<ReturnType<typeof getMirrorState>>;

type MirrorValue = {
  loading: boolean;
  device: { deviceId: string; deviceSecret: string };
  state: StateShape | null;
  session: Session | null;
  isAdmin: boolean;
  refresh: () => Promise<void>;
  signOut: () => Promise<void>;
};

const MirrorContext = createContext<MirrorValue>({
  loading: true,
  device: { deviceId: "", deviceSecret: "" },
  state: null,
  session: null,
  isAdmin: false,
  refresh: async () => {},
  signOut: async () => {},
});

export function MirrorProvider({ children }: { children: ReactNode }) {
  const [device, setDevice] = useState({ deviceId: "", deviceSecret: "" });
  const [state, setState] = useState<StateShape | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [isAdmin, setIsAdmin] = useState(false);
  const [loading, setLoading] = useState(true);

  // The anonymous device identity is minted here, the moment the app opens.
  useEffect(() => {
    setDevice(getDevice());
  }, []);

  const load = useCallback(async (creds: { deviceId: string; deviceSecret: string }) => {
    if (!creds.deviceId) return;
    try {
      setState(await getMirrorState({ data: { device: creds } }));
    } catch {
      setState(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!device.deviceId) return;
    void load(device);
  }, [device, load]);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => setSession(data.session));
    const { data: sub } = supabase.auth.onAuthStateChange((event, next) => {
      setSession(next);
      if (event === "SIGNED_IN" || event === "SIGNED_OUT" || event === "USER_UPDATED") {
        void load(getDevice());
      }
    });
    return () => sub.subscription.unsubscribe();
  }, [load]);

  useEffect(() => {
    if (!session) {
      setIsAdmin(false);
      return;
    }
    void supabase
      .from("user_roles")
      .select("role")
      .eq("user_id", session.user.id)
      .then(({ data }) => setIsAdmin((data ?? []).some((r) => r.role === "admin")));
  }, [session]);

  const refresh = useCallback(async () => load(getDevice()), [load]);

  const signOut = useCallback(async () => {
    await supabase.auth.signOut();
    await load(getDevice());
  }, [load]);

  const value = useMemo<MirrorValue>(
    () => ({ loading, device, state, session, isAdmin, refresh, signOut }),
    [loading, device, state, session, isAdmin, refresh, signOut],
  );

  return <MirrorContext.Provider value={value}>{children}</MirrorContext.Provider>;
}

export function useMirror() {
  return useContext(MirrorContext);
}
