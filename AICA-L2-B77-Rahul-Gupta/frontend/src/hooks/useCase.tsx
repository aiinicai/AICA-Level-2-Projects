/** Active-case context: selected company/case persisted across reloads. */
import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../services/api";
import type { CaseSummary } from "../types";

interface CaseCtx {
  cases: CaseSummary[];
  activeCase: CaseSummary | null;
  activeCaseId: string | null;
  setActiveCaseId: (id: string) => void;
  isLoading: boolean;
}

const Ctx = createContext<CaseCtx>({
  cases: [],
  activeCase: null,
  activeCaseId: null,
  setActiveCaseId: () => {},
  isLoading: true,
});

const LS_KEY = "companyval.activeCaseId";

export function CaseProvider({ children }: { children: React.ReactNode }) {
  const { data: cases = [], isLoading } = useQuery({
    queryKey: ["cases"],
    queryFn: () => api.get<CaseSummary[]>("/api/valuations"),
  });
  const [activeCaseId, setActiveCaseIdState] = useState<string | null>(
    () => localStorage.getItem(LS_KEY),
  );

  useEffect(() => {
    if (!isLoading && cases.length > 0) {
      const exists = cases.some((c) => c.id === activeCaseId);
      if (!exists) {
        const preferred =
          cases.find((c) => c.company_name === "ABC Food Pvt. Ltd.") ?? cases[0];
        setActiveCaseIdState(preferred.id);
        localStorage.setItem(LS_KEY, preferred.id);
      }
    }
  }, [isLoading, cases, activeCaseId]);

  const setActiveCaseId = (id: string) => {
    setActiveCaseIdState(id);
    localStorage.setItem(LS_KEY, id);
  };

  const activeCase = useMemo(
    () => cases.find((c) => c.id === activeCaseId) ?? null,
    [cases, activeCaseId],
  );

  return (
    <Ctx.Provider value={{ cases, activeCase, activeCaseId, setActiveCaseId, isLoading }}>
      {children}
    </Ctx.Provider>
  );
}

export const useCase = () => useContext(Ctx);
