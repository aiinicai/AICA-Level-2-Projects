import { useMemo } from "react";
import { runQuery } from "@/lib/query/engine";
import { applyDashboardFilters } from "@/lib/query/filters";
import { useLiveData } from "@/lib/live-data";
import type { DashboardFilterDef, DataQuery, DataResult } from "@/lib/types";

export function useWidgetData(query?: DataQuery, filters: DashboardFilterDef[] = []): DataResult | null {
  const { version } = useLiveData();
  const key = JSON.stringify([query, filters.map((f) => [f.field, f.type, f.value]), version]);
  return useMemo(() => {
    if (!query) return null;
    try {
      return runQuery(applyDashboardFilters(query, filters));
    } catch {
      return null;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);
}
