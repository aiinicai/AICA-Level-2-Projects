import type { Role } from '@shared/types';
import type { SessionUser } from '../state';
import type { AppIconName } from './icons';

export interface NavItem { to: string; label: string; icon: AppIconName; min?: Role }
export interface NavGroup { key: string; label: string; icon: AppIconName; items: NavItem[] }

// Inventory, insights and data quality come in a later version.
const GROUPS: NavGroup[] = [
  { key: 'overview', label: 'Overview', icon: 'overview', items: [
    { to: '/overview', label: 'Executive overview', icon: 'overview' },
  ] },
  { key: 'analysis', label: 'Analysis', icon: 'pnl', items: [
    { to: '/pnl', label: 'Profit & loss', icon: 'pnl' },
    { to: '/balance-sheet', label: 'Balance sheet', icon: 'balance' },
    { to: '/receivables-payables', label: 'Receivables & payables', icon: 'arap' },
  ] },
  { key: 'data', label: 'Data', icon: 'sources', items: [
    { to: '/sources', label: 'Data sources & sync', icon: 'sources' },
  ] },
  { key: 'configure', label: 'Settings', icon: 'company', items: [
    { to: '/settings', label: 'Appearance & assistant', icon: 'company' },
  ] },
];

export function visibleGroups(_user: SessionUser, _demoMode: boolean): NavGroup[] {
  return GROUPS;
}

/** The group a page belongs to; ledger and voucher drill-downs sit under Analysis. */
export function locate(groups: NavGroup[], pathname: string) {
  for (const group of groups) {
    const current = group.items.find((n) => n.to === pathname);
    if (current) return { group, current };
  }
  return { group: groups.find((g) => g.key === 'analysis') ?? groups[0], current: undefined };
}

/** The filters that follow you from page to page. */
export function filterQuery(sp: URLSearchParams) {
  const q = new URLSearchParams([...sp].filter(([k]) => ['from', 'to', 'compare', 'costCentre'].includes(k))).toString();
  return q ? `?${q}` : '';
}
