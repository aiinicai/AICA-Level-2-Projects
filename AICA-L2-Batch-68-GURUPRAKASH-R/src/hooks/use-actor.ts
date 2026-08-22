import { useMemo } from "react";
import { useRole } from "@/context/role-context";
import { ROLE_DISPLAY_NAME } from "@/lib/permissions";
import type { Actor } from "@/types/activity";

/** Derives the acting user from the role selector (front-end demonstration only). */
export function useActor(): Actor {
  const { role } = useRole();
  return useMemo(() => ({ user: ROLE_DISPLAY_NAME[role], role }), [role]);
}
