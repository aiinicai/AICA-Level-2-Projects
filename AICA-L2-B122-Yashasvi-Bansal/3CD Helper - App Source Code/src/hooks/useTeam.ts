import { useCallback, useEffect, useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import { useFirm } from "@/contexts/FirmContext";
import type { Role } from "@/lib/db";

export interface Member { user_id: string; role: Role; full_name: string | null; email: string | null; joined_at: string }

/** Firm members + a helper to turn a user id into a display name ("who did what"). */
export function useTeam() {
  const { firm } = useFirm();
  const [members, setMembers] = useState<Member[]>([]);
  const [loading, setLoading] = useState(true);
  const load = useCallback(async () => {
    if (!firm) return;
    setLoading(true);
    const { data } = await supabase.rpc("firm_team", { p_firm: firm.id });
    setMembers((data as Member[]) ?? []);
    setLoading(false);
  }, [firm]);
  useEffect(() => { load(); }, [load]);
  const nameOf = useCallback((id?: string | null) => {
    if (!id) return "—";
    const m = members.find((x) => x.user_id === id);
    return m ? m.full_name || m.email || "Member" : "Former member";
  }, [members]);
  return { members, loading, reload: load, nameOf };
}
