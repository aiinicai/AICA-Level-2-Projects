import { createContext, useContext } from 'react';
import type { BlockedCredit, Datasets, Engagement, EngagementState, FirmDetails, Kind, Row, Supplier } from './types';
import type { Recon } from './lib/engine';

export type TabId = 'imp' | 'g2b' | 'dash' | 'recon' | 'smart' | 'cdn' | 'rcm' | 'blocked' | 'follow' | 'reports' | 'health' | 'audit';

export interface Ctx {
  eng: Engagement;
  ds: Datasets;
  info: EngagementState['datasetInfo'];
  blocked: BlockedCredit[];
  remarks: Record<string, string>;
  recon: Recon;
  suppliers: Record<string, Supplier>;
  firm: FirmDetails;
  goto: (t: TabId) => void;
  toast: (msg: string, kind?: 'ok' | 'error') => void;
  log: (tag: string, msg: string) => Promise<void>;
  reload: () => Promise<void>;
  startImport: (kind: Kind, file: File) => void;
  clearImport: (kind: Kind) => Promise<void>;
  openBlock: (row: Row) => void;
  unblock: (b: BlockedCredit) => Promise<void>;
  reblock: (b: BlockedCredit) => Promise<void>;
  openRemark: (key: string, label: string) => void;
  openSupplier: (gstin: string, name: string) => void;
  saveFirm: (f: FirmDetails) => Promise<void>;
  busy: (text: string | null) => void;
}

export const AppCtx = createContext<Ctx | null>(null);

export function useApp() {
  const c = useContext(AppCtx);
  if (!c) throw new Error('useApp outside provider');
  return c;
}
