import React from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { formatAED } from '../core/currency';

export interface SummaryTileItem {
  id: string;
  label: string;
  count: number;
  amount?: number;
  statusKey?: string;
  color?: 'plum' | 'amber' | 'emerald' | 'rose' | 'slate';
  tooltip?: string;
}

interface SummaryTilesProps {
  tiles: SummaryTileItem[];
  selectedId: string | null;
  onSelect: (id: string | null) => void;
}

export const SummaryTiles: React.FC<SummaryTilesProps> = ({ tiles, selectedId, onSelect }) => {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3 mb-5 select-none">
      {tiles.map((tile) => {
        const isSelected = selectedId === tile.id;
        return (
          <div
            key={tile.id}
            onClick={() => onSelect(isSelected ? null : tile.id)}
            title={tile.tooltip || `Filter by ${tile.label}`}
            className={`rounded-lg cursor-pointer transition-all duration-150 border flex flex-col justify-between overflow-hidden shadow-xs hover:shadow-md ${
              isSelected
                ? 'bg-[#EDE4F5] border-[#5B2C83] ring-2 ring-[#5B2C83]/30'
                : 'bg-white border-gray-200 hover:border-plum-300'
            }`}
          >
            {/* Main Content */}
            <div className="p-3">
              <div className="text-xs font-medium text-gray-500 uppercase tracking-wider truncate mb-1">
                {tile.label}
              </div>
              <div className="flex items-baseline space-x-2">
                <span
                  className={`text-2xl font-bold tracking-tight ${
                    isSelected ? 'text-[#3F1D5C]' : 'text-gray-900'
                  }`}
                >
                  {tile.count}
                </span>
                {tile.amount !== undefined && (
                  <span className="text-xs text-gray-600 font-medium truncate">
                    {formatAED(tile.amount, { showCurrency: true })}
                  </span>
                )}
              </div>
            </div>

            {/* Dark Footer Chevron Bar */}
            <div
              className={`h-5 px-2 flex items-center justify-between text-[10px] font-medium transition-colors ${
                isSelected
                  ? 'bg-[#5B2C83] text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              <span>{isSelected ? 'Active Filter' : 'Filter records'}</span>
              {isSelected ? (
                <ChevronUp className="w-3 h-3 text-amber-300" />
              ) : (
                <ChevronDown className="w-3 h-3 text-gray-400" />
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
};
