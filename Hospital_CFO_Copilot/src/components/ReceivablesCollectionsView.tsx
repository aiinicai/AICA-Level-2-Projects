import React, { useState } from 'react';
import {
  Billing,
  Claim,
  Collection,
  Encounter,
} from '../types';
import { ArWorkingCapitalView } from './ArWorkingCapitalView';
import { TpaCollectionsView } from './TpaCollectionsView';
import { Clock, UserCheck } from 'lucide-react';

interface ReceivablesCollectionsViewProps {
  encounters: Encounter[];
  billings: Billing[];
  claims: Claim[];
  collections: Collection[];
  onSelectEncounter: (encounterId: string) => void;
  onNavigateToTab?: (tab: string) => void;
}

export const ReceivablesCollectionsView: React.FC<ReceivablesCollectionsViewProps> = ({
  encounters,
  billings,
  claims,
  collections,
  onSelectEncounter,
  onNavigateToTab,
}) => {
  const [activeTab, setActiveTab] = useState<'working-capital' | 'tpa-claims'>('working-capital');

  return (
    <div className="space-y-5">
      {/* Consolidated Module Header & Switcher */}
      <div className="bg-white p-4 sm:p-5 rounded-xl border border-slate-200 shadow-2xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight text-slate-900">
                Receivables &amp; Collections
              </h1>
              <span className="rounded bg-teal-50 px-2 py-0.5 text-[10px] font-bold tracking-wider text-teal-800 border border-teal-200 uppercase">
                Receivables &amp; Collections Desk
              </span>
            </div>
            <p className="mt-1 text-xs text-slate-500">
              Unified operational oversight covering trade receivables ageing, cash collection velocity, Insurance / TPA claim adjudication, and disallowance recovery.
            </p>
          </div>

          {/* Sub-tab navigation */}
          <div className="flex rounded-lg border border-slate-200 bg-slate-50 p-1 text-xs font-semibold">
            <button
              onClick={() => setActiveTab('working-capital')}
              className={`flex items-center gap-1.5 rounded-md px-3.5 py-1.5 transition cursor-pointer ${
                activeTab === 'working-capital'
                  ? 'bg-white text-teal-800 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Clock className="h-3.5 w-3.5" />
              <span>Receivables Ageing</span>
            </button>
            <button
              onClick={() => setActiveTab('tpa-claims')}
              className={`flex items-center gap-1.5 rounded-md px-3.5 py-1.5 transition cursor-pointer ${
                activeTab === 'tpa-claims'
                  ? 'bg-white text-teal-800 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <UserCheck className="h-3.5 w-3.5" />
              <span>Insurance / TPA &amp; Collections</span>
            </button>
          </div>
        </div>
      </div>

      {/* Render Consolidated Sub-view */}
      {activeTab === 'working-capital' ? (
        <ArWorkingCapitalView
          encounters={encounters}
          billings={billings}
          claims={claims}
          collections={collections}
          onSelectEncounter={onSelectEncounter}
          onNavigateToTab={onNavigateToTab}
        />
      ) : (
        <TpaCollectionsView
          encounters={encounters}
          billings={billings}
          claims={claims}
          collections={collections}
          onSelectEncounter={onSelectEncounter}
          onNavigateToTab={onNavigateToTab}
        />
      )}
    </div>
  );
};
