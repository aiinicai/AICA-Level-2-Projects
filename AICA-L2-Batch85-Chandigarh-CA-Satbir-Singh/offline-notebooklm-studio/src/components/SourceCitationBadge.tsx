import React, { useState, useRef, useEffect, useMemo } from 'react';
import { SourceItem, SourceLocationInfo } from '../types';
import { FileText, ExternalLink, MapPin, Sparkles } from 'lucide-react';
import { findExactSourceLocation } from '../utils/sourceLocationFinder';

interface Props {
  sourceNumber: number;
  sources: SourceItem[];
  claimContext?: string;
  snippet?: string;
  onOpenSource: (source: SourceItem, location?: SourceLocationInfo, openInNewTab?: boolean) => void;
}

export const SourceCitationBadge: React.FC<Props> = ({
  sourceNumber,
  sources,
  claimContext,
  snippet,
  onOpenSource,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const popoverRef = useRef<HTMLDivElement | null>(null);
  const badgeRef = useRef<HTMLButtonElement | null>(null);

  const sourceIndex = sourceNumber - 1;
  const source = sources[sourceIndex] || sources[0] || null;

  // Compute exact location info based on claim context / snippet
  const locationInfo: SourceLocationInfo | null = useMemo(() => {
    if (!source) return null;
    return findExactSourceLocation(source, claimContext || snippet);
  }, [source, claimContext, snippet]);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        popoverRef.current &&
        !popoverRef.current.contains(e.target as Node) &&
        badgeRef.current &&
        !badgeRef.current.contains(e.target as Node)
      ) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  if (!source) {
    return (
      <span className="inline-flex items-center justify-center min-w-[16px] h-4 px-1 rounded-full bg-gray-100 text-[10px] font-semibold text-gray-500 mx-0.5 select-none">
        {sourceNumber}
      </span>
    );
  }

  const displaySnippet = locationInfo?.snippet || snippet || source.text.slice(0, 160) + '...';
  const pageLabel = locationInfo?.pageNumber
    ? typeof locationInfo.pageNumber === 'number'
      ? `Page ${locationInfo.pageNumber}`
      : String(locationInfo.pageNumber)
    : 'Page 1';

  const locationBadge = locationInfo?.locationLabel || pageLabel;

  const handleOpenModal = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsOpen(false);
    onOpenSource(source, locationInfo || undefined, false);
  };

  const handleOpenNewWindow = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsOpen(false);
    onOpenSource(source, locationInfo || undefined, true);
  };

  // Helper to render snippet with matched keywords highlighted
  const renderHighlightedSnippet = () => {
    const text = displaySnippet;
    const keywords = locationInfo?.matchedKeywords || [];
    if (keywords.length === 0) return text;

    // Filter valid keywords
    const validKw = keywords
      .filter((k) => k && k.length > 2)
      .sort((a, b) => b.length - a.length);

    if (validKw.length === 0) return text;

    try {
      const escaped = validKw.map((k) => k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|');
      const regex = new RegExp(`(${escaped})`, 'gi');
      const parts = text.split(regex);

      return parts.map((part, i) =>
        regex.test(part) ? (
          <mark key={i} className="bg-yellow-200 text-yellow-950 font-semibold px-0.5 rounded">
            {part}
          </mark>
        ) : (
          part
        )
      );
    } catch {
      return text;
    }
  };

  return (
    <span className="relative inline-block align-baseline mx-0.5">
      {/* Citation Pill matching Screenshot */}
      <button
        ref={badgeRef}
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          setIsOpen((prev) => !prev);
        }}
        className={`inline-flex items-center justify-center min-w-[17px] h-[17px] px-1 rounded-full text-[10px] font-semibold transition select-none shadow-2xs cursor-pointer ${
          isOpen
            ? 'bg-blue-600 text-white ring-2 ring-blue-400/30'
            : 'bg-[#e8eaed] hover:bg-[#d2e3fc] text-[#3c4043] hover:text-[#1a73e8]'
        }`}
        title={`Source [${sourceNumber}]: ${source.name} • ${locationBadge} (Click to inspect exact passage)`}
      >
        {sourceNumber}
      </button>

      {/* Floating Citation Popover with Exact Location */}
      {isOpen && (
        <div
          ref={popoverRef}
          className="absolute z-50 left-1/2 -translate-x-1/2 bottom-full mb-2 w-80 sm:w-96 bg-white rounded-xl shadow-2xl border border-gray-200 text-left overflow-hidden animate-in fade-in zoom-in-95 duration-100"
          style={{ maxWidth: 'calc(100vw - 32px)' }}
        >
          {/* Popover Header with Document Title & Exact Location Badge */}
          <div className="px-3.5 py-2.5 bg-[#f8f9fa] border-b border-gray-100 flex items-center justify-between gap-2">
            <div className="flex items-center space-x-1.5 min-w-0 pr-2">
              <FileText className="w-3.5 h-3.5 text-blue-600 shrink-0" />
              <span className="text-xs font-semibold text-gray-900 truncate" title={source.name}>
                {source.name}
              </span>
            </div>
            
            <div className="flex items-center gap-1.5 shrink-0">
              {/* Exact Location Tag (e.g. Page 2 / TDS Section) */}
              <span className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full bg-blue-100/80 text-blue-800 border border-blue-200/70 shadow-2xs">
                <MapPin className="w-2.5 h-2.5 text-blue-600 shrink-0" />
                <span>{pageLabel}</span>
              </span>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-200/70 text-gray-600 font-mono">
                #{sourceNumber}
              </span>
            </div>
          </div>

          {/* Section Breadcrumb if available */}
          {locationInfo?.sectionTitle && locationInfo.sectionTitle !== source.name && (
            <div className="px-3.5 py-1.5 bg-blue-50/50 border-b border-blue-100/60 flex items-center gap-1.5 text-[11px] text-blue-900 font-medium truncate">
              <Sparkles className="w-3 h-3 text-blue-600 shrink-0" />
              <span className="truncate">Section: {locationInfo.sectionTitle}</span>
            </div>
          )}

          {/* Popover Body: Exact Grounded Document Passage */}
          <div className="p-3.5 max-h-48 overflow-y-auto text-xs text-gray-800 leading-relaxed font-sans select-text bg-white">
            <p className="whitespace-pre-wrap">{renderHighlightedSnippet()}</p>
          </div>

          {/* Popover Footer: "View source" (scrolls to exact location) and "Separate window" */}
          <div className="px-3.5 py-2.5 bg-[#fafafa] border-t border-gray-100 flex items-center justify-between">
            <button
              type="button"
              onClick={handleOpenModal}
              className="text-xs font-medium text-blue-600 hover:text-blue-800 flex items-center gap-1.5 hover:underline transition cursor-pointer"
            >
              <span>View exact location</span>
              <FileText className="w-3 h-3" />
            </button>

            <button
              type="button"
              onClick={handleOpenNewWindow}
              className="text-[11px] text-gray-500 hover:text-gray-800 flex items-center gap-1 hover:underline transition cursor-pointer"
              title="Open source in separate window"
            >
              <span>Separate window</span>
              <ExternalLink className="w-3 h-3" />
            </button>
          </div>
        </div>
      )}
    </span>
  );
};

