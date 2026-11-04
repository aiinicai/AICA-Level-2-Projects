import { useQuery, useQueryClient } from "@tanstack/react-query";
import { all, getSettings, one } from "./db";
import type { AppSettings } from "./db";
import type { Client, ReconItem, Txn } from "./types";

export function useClients() {
  return useQuery({
    queryKey: ["clients"],
    queryFn: () => all<Client>("SELECT * FROM clients ORDER BY name"),
  });
}

export function useClient(id: string) {
  return useQuery({
    queryKey: ["client", id],
    queryFn: () => one<Client>("SELECT * FROM clients WHERE id=?", [id]),
  });
}

export function useTxns(clientId: string) {
  return useQuery({
    queryKey: ["txns", clientId],
    queryFn: () => all<Txn>("SELECT * FROM txns WHERE client_id=?", [clientId]),
  });
}

export function useImports(clientId: string) {
  return useQuery({
    queryKey: ["imports", clientId],
    queryFn: () =>
      all<{ id: string; source: string; filename: string; row_count: number; created_at: string }>(
        "SELECT * FROM imports WHERE client_id=? ORDER BY created_at DESC",
        [clientId],
      ),
  });
}

export function useReconItems(clientId: string) {
  return useQuery({
    queryKey: ["recon", clientId],
    queryFn: () => all<ReconItem>("SELECT * FROM recon_items WHERE client_id=?", [clientId]),
  });
}

export function useAudit(clientId: string) {
  return useQuery({
    queryKey: ["audit", clientId],
    queryFn: () =>
      all<{ id: string; ts: string; action: string; detail: string }>(
        "SELECT * FROM audit WHERE client_id=? ORDER BY ts DESC LIMIT 300",
        [clientId],
      ),
  });
}

export function useSettings() {
  return useQuery<AppSettings>({ queryKey: ["settings"], queryFn: getSettings });
}

export function useRefresh() {
  const qc = useQueryClient();
  return (keys: string[]) => keys.forEach((k) => qc.invalidateQueries({ queryKey: [k] }));
}
