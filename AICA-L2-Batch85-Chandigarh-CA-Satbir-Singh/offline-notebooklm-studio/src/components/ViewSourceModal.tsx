import React, { useState, useEffect, useRef, useMemo } from 'react';
import { SourceItem, SourceLocationInfo } from '../types';
import {
  X,
  Copy,
  Check,
  FileText,
  ExternalLink,
  Search,
  Sparkles,
  MapPin,
  BookOpen,
  ArrowDown,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';

interface Props {
  source: SourceItem | null;
  highlightSnippet?: string;
  locationInfo?: SourceLocationInfo | null;
  onClose: () => void;
}

interface ParsedPage {
  pageNumber: number | string;
  label: string;
  text: string;
  startLine: number;
}

export const ViewSourceModal: React.FC<Props> = ({
  source,
  highlightSnippet,
  locationInfo,
  onClose,
}) => {
  const [copied, setCopied] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [activePageTab, setActivePageTab] = useState<number | string | 'ALL'>('ALL');

  const textContainerRef = useRef<HTMLDivElement | null>(null);
  const targetHighlightRef = useRef<HTMLDivElement | null>(null);

  // Parse document into structured pages / sections
  const pages: ParsedPage[] = useMemo(() => {
    if (!source || !source.text) return [];
    const raw = source.text;
    const lines = raw.split(/\r?\n/);

    const result: ParsedPage[] = [];
    let currentPageNum: number | string = 1;
    let currentLines: string[] = [];
    let startLine = 1;

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const pageMatch =
        line.match(/^---\s*Page\s*(\d+)\s*---/i) ||
        line.match(/^Page\s*(\d+)(?:\s*of\s*\d+)?$/i);
      const sheetMatch = line.match(/^###\s*Sheet:\s*(.+)$/i);

      if (pageMatch) {
        if (currentLines.length > 0) {
          result.push({
            pageNumber: currentPageNum,
            label: typeof currentPageNum === 'number' ? `Page ${currentPageNum}` : String(currentPageNum),
            text: currentLines.join('\n'),
            startLine,
          });
          currentLines = [];
        }
        currentPageNum = parseInt(pageMatch[1], 10);
        startLine = i + 1;
      } else if (sheetMatch) {
        if (currentLines.length > 0) {
          result.push({
            pageNumber: currentPageNum,
            label: typeof currentPageNum === 'number' ? `Page ${currentPageNum}` : String(currentPageNum),
            text: currentLines.join('\n'),
            startLine,
          });
          currentLines = [];
        }
        currentPageNum = `Sheet: ${sheetMatch[1].trim()}`;
        startLine = i + 1;
      } else {
        currentLines.push(line);
      }
    }

    if (currentLines.length > 0) {
      result.push({
        pageNumber: currentPageNum,
        label: typeof currentPageNum === 'number' ? `Page ${currentPageNum}` : String(currentPageNum),
        text: currentLines.join('\n'),
        startLine,
      });
    }

    // If only 1 page was found and text is long (> 3000 chars), create virtual pages
    if (result.length <= 1 && raw.length > 2500) {
      const virtualPages: ParsedPage[] = [];
      const chunkSize = 2000;
      let charIdx = 0;
      let pNum = 1;
      while (charIdx < raw.length) {
        let endIdx = Math.min(raw.length, charIdx + chunkSize);
        const nextNl = raw.indexOf('\n', endIdx);
        if (nextNl !== -1 && nextNl - endIdx < 300) {
          endIdx = nextNl;
        }
        virtualPages.push({
          pageNumber: pNum,
          label: `Page ${pNum}`,
          text: raw.slice(charIdx, endIdx).trim(),
          startLine: Math.floor(charIdx / 60) + 1,
        });
        charIdx = endIdx + 1;
        pNum++;
      }
      return virtualPages;
    }

    return result.length > 0
      ? result
      : [{ pageNumber: 1, label: 'Page 1', text: raw, startLine: 1 }];
  }, [source]);

  // When locationInfo arrives, initialize page tab and search terms
  useEffect(() => {
    if (locationInfo) {
      // If we have a specific page number, default to ALL or that specific page
      if (locationInfo.pageNumber && pages.some((p) => String(p.pageNumber) === String(locationInfo.pageNumber))) {
        setActivePageTab(locationInfo.pageNumber);
      } else {
        setActivePageTab('ALL');
      }

      if (locationInfo.matchedKeywords && locationInfo.matchedKeywords.length > 0) {
        setSearchQuery(locationInfo.matchedKeywords[0]);
      } else if (locationInfo.snippet) {
        const words = locationInfo.snippet
          .replace(/[^\w\s]/g, '')
          .trim()
          .split(/\s+/)
          .slice(0, 3)
          .join(' ');
        setSearchQuery(words);
      }
    } else if (highlightSnippet) {
      setActivePageTab('ALL');
      const cleanWords = highlightSnippet
        .replace(/[^\w\s]/g, '')
        .trim()
        .split(/\s+/)
        .slice(0, 3)
        .join(' ');
      setSearchQuery(cleanWords);
    } else {
      setActivePageTab('ALL');
      setSearchQuery('');
    }
  }, [highlightSnippet, locationInfo, source, pages]);

  // Auto-scroll to spotlight cited passage on open or tab change
  useEffect(() => {
    const timer = setTimeout(() => {
      if (targetHighlightRef.current && textContainerRef.current) {
        targetHighlightRef.current.scrollIntoView({
          behavior: 'smooth',
          block: 'center',
        });
      }
    }, 150);
    return () => clearTimeout(timer);
  }, [source, locationInfo, activePageTab]);

  if (!source) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(source.text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleJumpToCitation = () => {
    // If target is on another page tab, switch to that page first
    if (locationInfo?.pageNumber && activePageTab !== locationInfo.pageNumber && activePageTab !== 'ALL') {
      setActivePageTab(locationInfo.pageNumber);
      setTimeout(() => {
        targetHighlightRef.current?.scrollIntoView({
          behavior: 'smooth',
          block: 'center',
        });
      }, 100);
      return;
    }

    if (targetHighlightRef.current) {
      targetHighlightRef.current.scrollIntoView({
        behavior: 'smooth',
        block: 'center',
      });
    }
  };

  const handleOpenSeparateWindow = () => {
    const title = source.name;
    const locLabel = locationInfo?.locationLabel || 'Document Viewer';
    const content = source.text.replace(/</g, '&lt;').replace(/>/g, '&gt;');

    const newWindow = window.open('', '_blank', 'width=950,height=800,scrollbars=yes,resizable=yes');
    if (newWindow) {
      newWindow.document.write(`
        <!DOCTYPE html>
        <html>
        <head>
          <title>${title} - Grounded Source Viewer</title>
          <meta charset="utf-8">
          <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f8f9fa; margin: 0; padding: 24px; color: #202124; }
            .header { background: #fff; padding: 18px 24px; border-radius: 12px; border: 1px solid #e0e0e0; margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
            .title { font-size: 16px; font-weight: 700; margin: 0; color: #1a73e8; }
            .meta { font-size: 12px; color: #5f6368; margin-top: 4px; }
            .location-banner { background: #e8f0fe; border: 1px solid #c2e7ff; border-radius: 8px; padding: 12px 16px; margin-bottom: 16px; font-size: 13px; color: #174ea6; display: flex; align-items: center; justify-content: space-between; }
            .container { background: #fff; padding: 24px; border-radius: 12px; border: 1px solid #e0e0e0; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, monospace; font-size: 12px; line-height: 1.65; white-space: pre-wrap; word-break: break-word; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
            .spotlight { background-color: #fef08a; border-left: 4px solid #ca8a04; padding: 8px 12px; border-radius: 0 8px 8px 0; margin: 12px 0; display: block; font-weight: 600; }
          </style>
        </head>
        <body>
          <div class="header">
            <div>
              <h1 class="title">${title}</h1>
              <div class="meta">${source.fileType} • ${(source.sizeBytes / 1024).toFixed(1)} KB • ${source.charCount.toLocaleString()} characters</div>
            </div>
            <button onclick="navigator.clipboard.writeText(document.getElementById('content').innerText); alert('Copied to clipboard!');" style="padding: 8px 16px; border-radius: 8px; background: #1a73e8; color: #fff; border: none; font-weight: 600; cursor: pointer;">Copy Text</button>
          </div>
          ${
            locLabel
              ? `<div class="location-banner">
                  <div><strong>📍 Grounded Citation:</strong> ${locLabel}</div>
                  <div style="font-size: 11px; opacity: 0.8;">Offline NotebookLM Studio</div>
                </div>`
              : ''
          }
          <div class="container" id="content">${content}</div>
        </body>
        </html>
      `);
      newWindow.document.close();
    }
  };

  // Text rendering with spotlight on exact cited passage and keyword highlighting
  const renderDocumentContent = () => {
    const activeText =
      activePageTab === 'ALL'
        ? source.text
        : pages.find((p) => String(p.pageNumber) === String(activePageTab))?.text || source.text;

    const lines = activeText.split(/\r?\n/);
    const targetSnippetClean = (locationInfo?.snippet || highlightSnippet || '').replace(/\s+/g, ' ').toLowerCase().trim();
    const keywords = locationInfo?.matchedKeywords || (searchQuery.trim() ? [searchQuery.trim()] : []);

    const elements: React.ReactNode[] = [];
    let hasFoundBestSpotlight = false;

    // Find the single line or paragraph that best matches the snippet to spotlight it
    let bestLineIndex = -1;
    let bestLineScore = 0;

    if (targetSnippetClean.length > 10) {
      lines.forEach((line, idx) => {
        const lineLower = line.toLowerCase().replace(/\s+/g, ' ');
        if (lineLower.length < 5 || lineLower.startsWith('--- page') || lineLower.startsWith('### sheet:')) return;

        let score = 0;
        // Direct substring check
        if (lineLower.includes(targetSnippetClean.slice(0, 30)) || targetSnippetClean.includes(lineLower.slice(0, 30))) {
          score += 100;
        }

        // Keywords check
        for (const kw of keywords) {
          if (kw && kw.length > 2 && lineLower.includes(kw.toLowerCase())) {
            score += 20;
          }
        }

        if (score > bestLineScore) {
          bestLineScore = score;
          bestLineIndex = idx;
        }
      });
    }

    lines.forEach((line, idx) => {
      const trimmed = line.trim();
      const isPageHeader = trimmed.startsWith('--- Page') || trimmed.startsWith('### Sheet:');
      const cleanLineLower = trimmed.toLowerCase().replace(/\s+/g, ' ');

      if (isPageHeader) {
        elements.push(
          <div
            key={`header-${idx}`}
            className="my-3.5 py-2 px-3.5 rounded-lg bg-blue-50/90 border border-blue-200 text-blue-900 font-sans font-semibold text-xs flex items-center justify-between shadow-2xs"
          >
            <div className="flex items-center gap-1.5">
              <BookOpen className="w-3.5 h-3.5 text-blue-600" />
              <span>{trimmed.replace(/^[#\-\s]+/, '').replace(/[\-\s]+$/, '')}</span>
            </div>
            <span className="text-[10px] text-blue-600/80 font-mono">Line {idx + 1}</span>
          </div>
        );
        return;
      }

      // Check if this line is the spotlighted match
      const isSpotlightLine =
        (bestLineIndex !== -1 && idx === bestLineIndex) ||
        (!hasFoundBestSpotlight &&
          targetSnippetClean.length > 20 &&
          (cleanLineLower.includes(targetSnippetClean.slice(0, 35)) ||
            (cleanLineLower.length > 20 && targetSnippetClean.includes(cleanLineLower.slice(0, 30)))));

      if (isSpotlightLine) {
        hasFoundBestSpotlight = true;
      }

      // Render line with keyword highlighting
      let renderedLine: React.ReactNode = line;
      if (keywords.length > 0) {
        try {
          const validKw = keywords
            .filter((k) => k && k.length > 2)
            .sort((a, b) => b.length - a.length);
          if (validKw.length > 0) {
            const escaped = validKw.map((k) => k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|');
            const regex = new RegExp(`(${escaped})`, 'gi');
            const parts = line.split(regex);
            renderedLine = parts.map((part, pIdx) =>
              regex.test(part) ? (
                <mark
                  key={pIdx}
                  className="bg-yellow-200 text-yellow-950 font-bold px-0.5 rounded shadow-2xs"
                >
                  {part}
                </mark>
              ) : (
                part
              )
            );
          }
        } catch {
          renderedLine = line;
        }
      }

      if (isSpotlightLine) {
        elements.push(
          <div
            key={`line-${idx}`}
            ref={targetHighlightRef}
            className="my-3 p-3.5 rounded-xl bg-amber-50 border-2 border-amber-400 shadow-sm transition-all animate-in fade-in duration-200"
          >
            <div className="flex items-center gap-1.5 text-[11px] font-sans font-bold uppercase tracking-wider text-amber-900 mb-1.5">
              <MapPin className="w-3.5 h-3.5 text-amber-600" />
              <span>Exact Cited Passage Grounded in Chat</span>
              {locationInfo?.locationLabel && (
                <span className="font-normal text-amber-800 lowercase ml-1">
                  ({locationInfo.locationLabel})
                </span>
              )}
            </div>
            <div className="font-mono text-xs text-gray-950 leading-relaxed font-semibold">
              {renderedLine}
            </div>
          </div>
        );
      } else {
        elements.push(
          <div key={`line-${idx}`} className="py-0.5 leading-relaxed text-gray-800">
            {renderedLine || '\u00A0'}
          </div>
        );
      }
    });

    return elements;
  };

  const currentPageIndex = pages.findIndex((p) => String(p.pageNumber) === String(activePageTab));

  return (
    <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-3 sm:p-4 animate-in fade-in duration-150">
      <div className="bg-white border border-gray-200 rounded-2xl w-full max-w-5xl h-[90vh] flex flex-col shadow-2xl overflow-hidden animate-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="p-4 border-b border-gray-100 flex items-center justify-between bg-white shrink-0">
          <div className="flex items-center space-x-3 min-w-0 pr-4">
            <div className="w-9 h-9 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center shrink-0 shadow-2xs">
              <FileText className="w-5 h-5" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-bold text-gray-900 truncate" title={source.name}>
                  {source.name}
                </h3>
                <span className="px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 text-[10px] font-semibold uppercase">
                  {source.fileType}
                </span>
              </div>
              <p className="text-[11px] text-gray-500 mt-0.5">
                {(source.sizeBytes / 1024).toFixed(1)} KB • {source.charCount.toLocaleString()} characters • {pages.length} page{pages.length !== 1 ? 's' : ''}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleOpenSeparateWindow}
              className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-200 bg-white hover:bg-gray-50 text-gray-700 text-xs font-medium transition shadow-2xs cursor-pointer"
              title="Pop out into separate standalone window"
            >
              <span>Open in window</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </button>

            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-700 p-2 rounded-lg hover:bg-gray-100 transition cursor-pointer"
              title="Close viewer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Citation Location Banner if opened from grounded citation */}
        {locationInfo && (
          <div className="px-4 py-2.5 bg-gradient-to-r from-blue-50 via-indigo-50 to-blue-50 border-b border-blue-100 flex items-center justify-between gap-3 text-xs shrink-0">
            <div className="flex items-center gap-2 text-blue-900 min-w-0">
              <span className="flex items-center justify-center w-5 h-5 rounded-full bg-blue-600 text-white font-bold text-[10px] shrink-0">
                📍
              </span>
              <div className="truncate">
                <span className="font-semibold">Grounded Location: </span>
                <span className="font-bold text-blue-800">{locationInfo.locationLabel}</span>
                {locationInfo.sectionTitle && locationInfo.sectionTitle !== source.name && (
                  <span className="text-blue-600 ml-1.5">({locationInfo.sectionTitle})</span>
                )}
              </div>
            </div>

            <button
              onClick={handleJumpToCitation}
              className="px-3 py-1 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-medium flex items-center gap-1.5 shrink-0 shadow-2xs transition cursor-pointer"
            >
              <span>Jump to passage</span>
              <ArrowDown className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        {/* Page / Sheet Navigation Strip */}
        {pages.length > 1 && (
          <div className="px-4 py-2 border-b border-gray-100 bg-[#f8f9fa] flex items-center gap-1.5 overflow-x-auto text-xs shrink-0 scrollbar-none">
            <span className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mr-1 shrink-0">
              Pages:
            </span>
            <button
              onClick={() => setActivePageTab('ALL')}
              className={`px-2.5 py-1 rounded-md text-xs font-medium transition cursor-pointer shrink-0 ${
                activePageTab === 'ALL'
                  ? 'bg-blue-600 text-white shadow-2xs'
                  : 'bg-white text-gray-700 hover:bg-gray-100 border border-gray-200'
              }`}
            >
              All Pages ({pages.length})
            </button>

            {pages.map((p) => {
              const isTargetPage =
                locationInfo &&
                String(locationInfo.pageNumber) === String(p.pageNumber);

              return (
                <button
                  key={String(p.pageNumber)}
                  onClick={() => setActivePageTab(p.pageNumber)}
                  className={`px-2.5 py-1 rounded-md text-xs font-medium transition cursor-pointer shrink-0 flex items-center gap-1 ${
                    activePageTab === p.pageNumber
                      ? 'bg-blue-600 text-white shadow-2xs'
                      : isTargetPage
                      ? 'bg-amber-100 text-amber-900 border border-amber-300 font-semibold'
                      : 'bg-white text-gray-700 hover:bg-gray-100 border border-gray-200'
                  }`}
                >
                  {isTargetPage && <span className="w-1.5 h-1.5 rounded-full bg-amber-600" />}
                  <span>{p.label}</span>
                </button>
              );
            })}
          </div>
        )}

        {/* Search & Filter Toolbar */}
        <div className="px-4 py-2 border-b border-gray-100 bg-[#fafafa] flex items-center justify-between gap-3 shrink-0 text-xs">
          <div className="relative flex-1 max-w-md">
            <Search className="w-3.5 h-3.5 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search in document..."
              className="w-full pl-8 pr-3 py-1 bg-white rounded-lg border border-gray-200 text-xs text-gray-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          <div className="flex items-center gap-3">
            {pages.length > 1 && activePageTab !== 'ALL' && (
              <div className="flex items-center gap-1 text-xs text-gray-500">
                <button
                  disabled={currentPageIndex <= 0}
                  onClick={() => {
                    if (currentPageIndex > 0) {
                      setActivePageTab(pages[currentPageIndex - 1].pageNumber);
                    }
                  }}
                  className="p-1 rounded hover:bg-gray-200 disabled:opacity-30 cursor-pointer"
                  title="Previous Page"
                >
                  <ChevronLeft className="w-3.5 h-3.5" />
                </button>
                <span className="text-[11px] font-mono">
                  {currentPageIndex + 1} / {pages.length}
                </span>
                <button
                  disabled={currentPageIndex >= pages.length - 1}
                  onClick={() => {
                    if (currentPageIndex < pages.length - 1) {
                      setActivePageTab(pages[currentPageIndex + 1].pageNumber);
                    }
                  }}
                  className="p-1 rounded hover:bg-gray-200 disabled:opacity-30 cursor-pointer"
                  title="Next Page"
                >
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </div>
            )}

            <div className="flex items-center gap-1.5 text-[11px] text-gray-500 font-medium">
              <Sparkles className="w-3.5 h-3.5 text-blue-600" />
              <span>Exact passage matching active</span>
            </div>
          </div>
        </div>

        {/* Document Body */}
        <div
          ref={textContainerRef}
          className="flex-1 p-5 overflow-y-auto bg-[#fafafa] font-mono text-xs text-gray-800 whitespace-pre-wrap leading-relaxed select-text border-y border-gray-100"
        >
          {renderDocumentContent()}
        </div>

        {/* Footer */}
        <div className="p-3.5 bg-white flex justify-between items-center text-xs text-gray-500 shrink-0">
          <div className="flex items-center gap-2">
            <span>Captured on {new Date(source.createdAt).toLocaleString()}</span>
            {locationInfo && (
              <span className="hidden sm:inline-block text-blue-700 font-medium">
                • Grounded at offset {locationInfo.charOffset}
              </span>
            )}
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleOpenSeparateWindow}
              className="sm:hidden px-3 py-1.5 bg-white hover:bg-gray-50 text-gray-700 rounded-lg flex items-center gap-1.5 transition font-semibold border border-gray-200 shadow-2xs cursor-pointer"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              <span>Separate Window</span>
            </button>
            <button
              onClick={handleCopy}
              className="px-3.5 py-1.5 bg-white hover:bg-gray-50 text-gray-700 rounded-lg flex items-center gap-1.5 transition font-semibold border border-gray-200 shadow-2xs cursor-pointer"
            >
              {copied ? (
                <Check className="w-3.5 h-3.5 text-emerald-600" />
              ) : (
                <Copy className="w-3.5 h-3.5 text-gray-500" />
              )}
              <span>{copied ? 'Copied to Clipboard' : 'Copy Full Text'}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
