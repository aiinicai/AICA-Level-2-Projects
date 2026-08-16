// Client record store — localStorage now, swapped for the LAN-server API later.
import type { ProjectConfig, SimParams } from '../types/cma';
import { DEFAULT_BLOCKS, defaultSimParams, makeEmptyActual, fyLabel } from '../engine/cmaEngine';

export interface ClientRecord {
  id: string;
  name: string;
  config: ProjectConfig;
  sim: SimParams;
  updatedAt: string;
}

const LS_KEY = 'cma-pro-clients-v1';

export function loadClients(): ClientRecord[] {
  try {
    const raw = localStorage.getItem(LS_KEY);
    if (!raw) return [];
    return JSON.parse(raw) as ClientRecord[];
  } catch {
    return [];
  }
}

export function saveClients(clients: ClientRecord[]): void {
  localStorage.setItem(LS_KEY, JSON.stringify(clients));
}

export function makeDefaultConfig(name: string): ProjectConfig {
  const startYear = new Date().getFullYear() - 2;
  return {
    clientName: name,
    startYear,
    actualYears: 1,
    estimatedYears: 1,
    projectedYears: 5,
    unit: 'lakhs',
    assetBlocks: DEFAULT_BLOCKS.map(b => ({ ...b })),
    customHeads: [],
    loan: {
      loanType: 'both',
      ccLimit: 0, ccRate: 10.5,
      ccStockMarginPct: 25, ccDebtorMarginPct: 40, ccDebtorCoverDays: 90,
      tlAmount: 0, tlRate: 11, tlTenureMonths: 60, tlMoratoriumMonths: 0,
      grantMonthIndex: 0, emiDay: 10, grantDay: 1,
    },
    actuals: [makeEmptyActual(fyLabel(startYear, 0))],
  };
}

export function makeClient(name: string): ClientRecord {
  return {
    id: `c${Date.now()}${Math.floor(Math.random() * 1e4)}`,
    name,
    config: makeDefaultConfig(name),
    sim: defaultSimParams(),
    updatedAt: new Date().toISOString(),
  };
}

/** Keep actuals array length in sync with actualYears, labels correct */
export function normalizeConfig(config: ProjectConfig): ProjectConfig {
  const c = { ...config };
  c.customHeads = c.customHeads || [];
  c.actualYears = Math.max(1, Math.min(4, c.actualYears || 1));
  c.estimatedYears = 1;
  c.projectedYears = Math.max(1, Math.min(10, c.projectedYears || 5));
  const actuals = [...c.actuals];
  while (actuals.length < c.actualYears) {
    actuals.push(makeEmptyActual(fyLabel(c.startYear, actuals.length)));
  }
  c.actuals = actuals.slice(0, c.actualYears).map((a, i) => ({ ...a, label: fyLabel(c.startYear, i), customValues: a.customValues || {} }));
  return c;
}
