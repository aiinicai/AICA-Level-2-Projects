import { useCallback, useEffect, useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import { Clause44Summary, EMPTY_SUMMARY, toSummary } from "@/lib/clause44";

export function useClause44Summary(engagementId: string | undefined) {
  const [summary, setSummary] = useState<Clause44Summary>(EMPTY_SUMMARY);
  const [loading, setLoading] = useState(true);
  const reload = useCallback(async () => {
    if (!engagementId) return;
    const { data } = await supabase.rpc("clause44_summary", { p_eng: engagementId });
    setSummary(toSummary(Array.isArray(data) ? data[0] : data));
    setLoading(false);
  }, [engagementId]);
  useEffect(() => { reload(); }, [reload]);
  return { summary, loading, reload };
}
