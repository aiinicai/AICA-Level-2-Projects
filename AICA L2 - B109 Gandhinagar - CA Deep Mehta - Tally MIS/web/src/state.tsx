import { createContext, useContext } from 'react';
import type { Role } from '@shared/types';

export interface CompanyInfo {
  id: number; name: string; is_demo: boolean; industry_profile: string; inventory_mode: string; base_currency: string;
  fy_start_month: number; books_from: string | null; data_from: string | null; data_to: string | null; last_sync: string | null; voucher_count: number;
  settings: Record<string, any>;
}

export interface SessionUser { id: number; email: string; name: string; role: Role }

export interface AppState {
  user: SessionUser;
  companies: CompanyInfo[];
  companyId: number | null;
  company: CompanyInfo | null;
  setCompanyId: (id: number) => void;
  /** Public read-only demo: no sign-out, no saving, no data-source pages. */
  demoMode: boolean;
  /** The hosted demo requires the operator-defined login (show Sign out). */
  demoLoginRequired: boolean;
  refreshCompanies: () => void;
}

export const AppContext = createContext<AppState | null>(null);

export function useApp(): AppState {
  const v = useContext(AppContext);
  if (!v) throw new Error('AppContext missing');
  return v;
}

export const useCompany = () => {
  const { companyId, company } = useApp();
  return { companyId, company };
};

const RANK: Record<Role, number> = { viewer: 1, analyst: 2, admin: 3 };
export const can = (user: SessionUser, min: Role) => RANK[user.role] >= RANK[min];

export function storedCompany(): number | null {
  try {
    const v = localStorage.getItem('mis.company');
    return v ? Number(v) : null;
  } catch {
    return null;
  }
}
export function storeCompany(id: number) {
  try {
    localStorage.setItem('mis.company', String(id));
  } catch {
    /* storage unavailable: selection just won't persist */
  }
}
