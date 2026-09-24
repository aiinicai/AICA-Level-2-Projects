import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { getLiveTables, listSources, type LiveSource } from "@/lib/accounting.functions";
import { setLiveTables } from "@/lib/query/engine";
import { useAuth } from "@/lib/auth";

interface LiveDataState {
  sources: LiveSource[];
  /** true once at least one connected source has records loaded */
  live: boolean;
  loading: boolean;
  version: number;
  refresh: () => Promise<void>;
}

const Ctx = createContext<LiveDataState>({
  sources: [],
  live: false,
  loading: false,
  version: 0,
  refresh: async () => {},
});

export function LiveDataProvider({ children }: { children: ReactNode }) {
  const { session } = useAuth();
  const [sources, setSources] = useState<LiveSource[]>([]);
  const [live, setLive] = useState(false);
  const [loading, setLoading] = useState(false);
  const [version, setVersion] = useState(0);

  const refresh = useCallback(async () => {
    if (!session) {
      setSources([]);
      setLive(false);
      setLiveTables(null);
      setVersion((v) => v + 1);
      return;
    }
    setLoading(true);
    try {
      const list = await listSources();
      setSources(list);
      const hasData = list.some((s) => s.records > 0);
      if (hasData) {
        const tables = await getLiveTables();
        setLiveTables(tables);
        setLive(true);
      } else {
        setLiveTables(null);
        setLive(false);
      }
    } catch {
      setLiveTables(null);
      setLive(false);
    } finally {
      setLoading(false);
      setVersion((v) => v + 1);
    }
  }, [session]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return <Ctx.Provider value={{ sources, live, loading, version, refresh }}>{children}</Ctx.Provider>;
}

export const useLiveData = () => useContext(Ctx);
