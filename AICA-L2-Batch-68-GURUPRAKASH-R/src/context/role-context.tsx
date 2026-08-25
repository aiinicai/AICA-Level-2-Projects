import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { USER_ROLES, type UserRole } from "@/types/common";

const STORAGE_KEY = "auditflow.role";
const DEFAULT_ROLE: UserRole = "Auditor";

interface RoleContextValue {
  role: UserRole;
  setRole: (role: UserRole) => void;
  roles: readonly UserRole[];
}

const RoleContext = createContext<RoleContextValue | null>(null);

export function RoleProvider({ children }: { children: React.ReactNode }) {
  const [role, setRoleState] = useState<UserRole>(DEFAULT_ROLE);

  useEffect(() => {
    const stored = window.localStorage.getItem(STORAGE_KEY) as UserRole | null;
    if (stored && (USER_ROLES as readonly string[]).includes(stored)) {
      setRoleState(stored);
    }
  }, []);

  const setRole = useCallback((next: UserRole) => {
    setRoleState(next);
    window.localStorage.setItem(STORAGE_KEY, next);
  }, []);

  const value = useMemo(() => ({ role, setRole, roles: USER_ROLES }), [role, setRole]);

  return <RoleContext.Provider value={value}>{children}</RoleContext.Provider>;
}

export function useRole() {
  const ctx = useContext(RoleContext);
  if (!ctx) throw new Error("useRole must be used within a RoleProvider");
  return ctx;
}
