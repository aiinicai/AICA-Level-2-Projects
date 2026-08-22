import { useQuery } from "@tanstack/react-query";
import { services } from "@/services";

/**
 * Loads the cross-module option data the Stage 3 forms need for their
 * Engagement → Scope → Procedure → Requirement → Evidence cascades.
 */
export function useFieldworkOptions() {
  const engagements = useQuery({
    queryKey: ["engagements", "options"],
    queryFn: () => services.engagements.list({ pageSize: 500 }),
  });
  const scopes = useQuery({ queryKey: ["scopes", "options"], queryFn: () => services.scopes.list({}) });
  const procedures = useQuery({
    queryKey: ["procedures", "options"],
    queryFn: () => services.procedures.list({}),
  });
  const requirements = useQuery({
    queryKey: ["requirements", "options"],
    queryFn: () => services.requirements.list({}),
  });
  const evidence = useQuery({ queryKey: ["evidence", "options"], queryFn: () => services.evidence.list({}) });

  return {
    engagementOptions: (engagements.data?.items ?? []).map((row) => ({
      value: row.id,
      label: `${row.reference} · ${row.title}`,
    })),
    engagements: engagements.data?.items ?? [],
    scopes: scopes.data?.items ?? [],
    procedures: procedures.data?.items ?? [],
    requirements: requirements.data?.items ?? [],
    evidence: evidence.data?.items ?? [],
  };
}
