import React, { useState, useRef, useEffect } from 'react';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { SourceItem, ChatMessageItem, LmStudioConfig, SourceLocationInfo } from '../types';
import { SourceCitationBadge } from './SourceCitationBadge';
import {
  MessageSquareCode,
  Trash2,
  Sparkles,
  Pin,
  Copy,
  Check,
  ThumbsUp,
  ThumbsDown,
  Square,
  CheckSquare,
  ArrowRight,
  ArrowDown,
  Loader2,
  FileText,
  Presentation,
  CheckCircle2,
  Download,
  BookOpen,
} from 'lucide-react';
import confetti from 'canvas-confetti';

interface Props {
  sources: SourceItem[];
  selectedSourceIds: Set<string>;
  messages: ChatMessageItem[];
  config: LmStudioConfig;
  onSendMessage: (text: string) => Promise<void>;
  onClearChat: () => void;
  onSendToReport: (text: string) => void;
  onCreateWordDoc: (text: string, title?: string) => void | Promise<void>;
  onCreatePresentation: (text: string, title?: string) => void | Promise<void>;
  onOpenSource?: (source: SourceItem, location?: SourceLocationInfo, openInNewTab?: boolean) => void;
  isGenerating: boolean;
}

export const GroundedChatPanel: React.FC<Props> = ({
  sources,
  selectedSourceIds,
  messages,
  config,
  onSendMessage,
  onClearChat,
  onSendToReport,
  onCreateWordDoc,
  onCreatePresentation,
  onOpenSource,
  isGenerating,
}) => {
  const [input, setInput] = useState('');
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [savedNotesMap, setSavedNotesMap] = useState<{ [msgId: string]: boolean }>({});
  const [likedMap, setLikedMap] = useState<{ [msgId: string]: boolean | null }>({});
  const [selectedMsgMap, setSelectedMsgMap] = useState<{ [msgId: string]: boolean }>({});
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [showScrollBottom, setShowScrollBottom] = useState(false);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  // Auto-scroll on new messages when at bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: 'smooth',
      });
    }
  }, [messages.length, isGenerating]);

  // Track scroll position to show "Jump to Latest" button
  const handleScroll = () => {
    if (!scrollRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
    const isScrolledUp = scrollHeight - scrollTop - clientHeight > 180;
    setShowScrollBottom(isScrolledUp);
  };

  const scrollToBottom = () => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: 'smooth',
      });
    }
  };

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 2500);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isGenerating) return;
    const text = input.trim();
    if (selectedSourceIds.size === 0) {
      showToast('⚠️ Please select at least one document in the left panel');
    }
    setInput('');
    onSendMessage(text);
  };

  const handleCopy = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    showToast('Copied to clipboard');
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleSaveToNote = (msgId: string, content: string) => {
    onSendToReport(content);
    setSavedNotesMap((prev) => ({ ...prev, [msgId]: true }));
    confetti({
      particleCount: 50,
      spread: 60,
      origin: { y: 0.75 },
      colors: ['#38bdf8', '#34d399', '#f59e0b'],
    });
    showToast('Saved to Studio Notes on the right!');
  };

  const handleSaveAllToNotes = () => {
    if (messages.length === 0) return;
    const fullTranscript = messages
      .map((m, idx) => {
        const roleLabel = m.role === 'user' ? '### 👤 User Inquiry' : '### 🤖 Grounded Synthesis';
        return `${roleLabel} (${new Date(m.timestamp).toLocaleTimeString()})\n\n${m.content}`;
      })
      .join('\n\n---\n\n');

    onSendToReport(`# Consolidated Grounded Chat Transcript\n\n${fullTranscript}`);
    confetti({
      particleCount: 70,
      spread: 70,
      origin: { y: 0.7 },
      colors: ['#38bdf8', '#34d399', '#f59e0b'],
    });
    showToast('All chat conversations saved to Studio Notes!');
  };

  const handleToggleLike = (msgId: string, isLike: boolean) => {
    setLikedMap((prev) => ({
      ...prev,
      [msgId]: prev[msgId] === isLike ? null : isLike,
    }));
  };

  const handleToggleSelect = (msgId: string) => {
    setSelectedMsgMap((prev) => ({
      ...prev,
      [msgId]: !prev[msgId],
    }));
  };

  const formatTimestamp = (dateStr?: string) => {
    const d = dateStr ? new Date(dateStr) : new Date();
    const timeStr = d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
    const isToday = new Date().toDateString() === d.toDateString();
    return isToday ? `Today • ${timeStr}` : `${d.toLocaleDateString()} • ${timeStr}`;
  };

  const quickPrompts = [
    '📊 Executive Summary',
    '🔍 Extract Key Insights',
    '📑 Outline Presentation Deck',
    '⚖️ Statutory Precedents',
    '⚡ Action Items & Next Steps',
  ];

  // Extract clean text from React nodes for citation context matching
  const extractTextFromReactNode = (node: React.ReactNode): string => {
    if (node === null || node === undefined || typeof node === 'boolean') {
      return '';
    }
    if (typeof node === 'string' || typeof node === 'number') {
      return String(node);
    }
    if (Array.isArray(node)) {
      return node.map(extractTextFromReactNode).join(' ');
    }
    if (React.isValidElement<{ children?: React.ReactNode }>(node) && node.props && node.props.children) {
      return extractTextFromReactNode(node.props.children);
    }
    return '';
  };

  // Helper to parse citations like [1], [2], [1, 2] in strings/React children
  const renderWithCitations = (
    children: React.ReactNode,
    targetSources?: SourceItem[],
    parentContext?: string
  ): React.ReactNode => {
    if (!children) return children;
    const effectiveSources = targetSources && targetSources.length > 0 ? targetSources : sources;
    const currentContext = parentContext || extractTextFromReactNode(children);

    if (typeof children === 'string') {
      const citationRegex = /(\[(?:Source\s*)?\d+(?:\s*,\s*(?:Source\s*)?\d+)*\])/g;
      const parts = children.split(citationRegex);

      if (parts.length === 1) return children;

      const claimContext = currentContext || children;

      return parts.map((part, index) => {
        if (/^\[(?:Source\s*)?\d+(?:\s*,\s*(?:Source\s*)?\d+)*\]$/.test(part)) {
          const numbers = part.match(/\d+/g);
          if (numbers && numbers.length > 0) {
            return (
              <span key={index} className="inline-flex items-center align-baseline mx-0.5">
                {numbers.map((numStr, nIdx) => {
                  const num = parseInt(numStr, 10);
                  return (
                    <SourceCitationBadge
                      key={nIdx}
                      sourceNumber={num}
                      sources={effectiveSources}
                      claimContext={claimContext}
                      onOpenSource={onOpenSource || (() => {})}
                    />
                  );
                })}
              </span>
            );
          }
        }
        return part;
      });
    }

    if (Array.isArray(children)) {
      const arrayText = extractTextFromReactNode(children).trim();
      return React.Children.map(children, (child) =>
        renderWithCitations(child, targetSources, arrayText || currentContext)
      );
    }

    if (React.isValidElement<{ children?: React.ReactNode }>(children) && children.props && children.props.children) {
      return React.cloneElement(
        children,
        {},
        renderWithCitations(children.props.children, targetSources, currentContext)
      );
    }

    return children;
  };

  // Count user questions for turn numbering
  let userQueryCount = 0;
  let assistantResponseCount = 0;

  return (
    <section className="h-full flex flex-col bg-white overflow-hidden relative">
      {/* Center Panel Header */}
      <div className="p-3.5 border-b border-gray-100 bg-white flex items-center justify-between shrink-0">
        <div className="flex items-center space-x-2">
          <div className="w-7 h-7 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
            <MessageSquareCode className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xs font-semibold text-gray-900">
                Grounded Chat
              </h2>
              <span className="text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-gray-100 text-gray-600 border border-gray-200">
                {messages.length} message{messages.length !== 1 ? 's' : ''}
              </span>
            </div>
            <p className="text-[11px] text-gray-400">
              Grounded on {selectedSourceIds.size} selected source{selectedSourceIds.size !== 1 ? 's' : ''}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-1.5">
          {messages.length > 1 && (
            <>
              <button
                onClick={() => {
                  let fullTranscript = `# Offline NotebookLM Studio - Grounded Chat Transcript\n\n**Generated:** ${new Date().toLocaleString()}\n\n---\n\n`;
                  let qNum = 1;
                  messages.forEach((m) => {
                    if (m.role === 'user') {
                      fullTranscript += `## Question #${qNum++}: ${m.content}\n\n`;
                    } else {
                      fullTranscript += `### Grounded Response\n\n${m.content}\n\n---\n\n`;
                    }
                  });
                  onCreateWordDoc(fullTranscript, 'NotebookLM Full Chat Transcript');
                }}
                title="Export full chat transcript as Word document (.docx)"
                className="text-xs text-blue-600 hover:text-blue-800 px-2.5 py-1 rounded-md hover:bg-blue-50 transition flex items-center gap-1 font-medium border border-blue-100"
              >
                <FileText className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Export All (.docx)</span>
              </button>

              <button
                onClick={handleSaveAllToNotes}
                title="Save all chat questions & answers into Studio Notes"
                className="text-xs text-gray-700 hover:text-gray-900 px-2.5 py-1 rounded-md hover:bg-gray-100 transition flex items-center gap-1 font-medium border border-gray-200"
              >
                <Download className="w-3.5 h-3.5 text-gray-500" />
                <span className="hidden sm:inline">Save All to Notes</span>
              </button>
            </>
          )}

          <button
            onClick={onClearChat}
            title="Clear Chat History"
            className="text-xs text-gray-400 hover:text-gray-700 px-2.5 py-1 rounded-md hover:bg-gray-100 transition flex items-center gap-1 font-medium"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>Clear</span>
          </button>
        </div>
      </div>

      {/* Quick Prompt Pills Bar */}
      <div className="px-4 py-2 border-b border-gray-100 bg-[#fafafa] flex gap-2 overflow-x-auto text-xs scrollbar-none shrink-0">
        {quickPrompts.map((qp, idx) => (
          <button
            key={idx}
            onClick={() => {
              setInput(qp.replace(/^[^\s]+\s/, ''));
            }}
            className="whitespace-nowrap px-3 py-1 rounded-full bg-white border border-gray-200/90 hover:border-gray-300 hover:bg-gray-50 text-gray-700 text-xs font-medium transition shadow-2xs shrink-0 cursor-pointer"
          >
            {qp}
          </button>
        ))}
      </div>

      {/* Chat Messages Container - Full scrollable history of all past chats */}
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto p-6 space-y-7 scroll-smooth"
      >
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center p-8 space-y-4">
            <div className="w-12 h-12 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center shadow-xs">
              <Sparkles className="w-6 h-6" />
            </div>
            <div className="max-w-sm space-y-1.5">
              <h3 className="text-sm font-semibold text-gray-900">Ask your sources anything</h3>
              <p className="text-xs text-gray-500 leading-relaxed">
                All questions and grounded answers will be preserved in this middle panel. Synthesis is strictly grounded on the {selectedSourceIds.size} checked documents.
              </p>
            </div>
          </div>
        ) : (
          messages.map((msg, index) => {
            const isUser = msg.role === 'user';
            if (isUser) userQueryCount++;
            else assistantResponseCount++;

            const currentTurnNum = isUser ? userQueryCount : assistantResponseCount;
            const isSaved = savedNotesMap[msg.id] || false;
            const isLiked = likedMap[msg.id];
            const isSelected = selectedMsgMap[msg.id] || false;

            const msgSources: SourceItem[] =
              msg.sourceItemsGrounded && msg.sourceItemsGrounded.length > 0
                ? msg.sourceItemsGrounded
                : msg.sourcesGrounded && msg.sourcesGrounded.length > 0
                ? (msg.sourcesGrounded.map((name) => sources.find((s) => s.name === name || s.id === name)).filter(Boolean) as SourceItem[])
                : sources.filter((s) => selectedSourceIds.has(s.id));

            return (
              <div
                key={msg.id || index}
                className={`flex flex-col ${isUser ? 'items-end' : 'items-start'} space-y-2`}
              >
                {isUser ? (
                  <div className="max-w-[90%] space-y-1">
                    <div className="flex items-center justify-end gap-1.5 text-[11px] text-gray-400 font-medium mr-1">
                      <span className="px-1.5 py-0.2 rounded bg-gray-200/70 text-gray-700 text-[10px] font-bold">
                        Q#{currentTurnNum}
                      </span>
                      <span>You</span>
                    </div>
                    <div className="bg-blue-600 text-white rounded-2xl rounded-tr-xs px-4 py-3 text-sm leading-relaxed shadow-xs">
                      <p className="whitespace-pre-wrap select-text font-normal">{msg.content}</p>
                      <div className="text-[10px] text-blue-100 text-right mt-1.5 font-mono opacity-80">
                        {new Date(msg.timestamp).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="w-full rounded-2xl border border-gray-200/80 bg-white p-4 space-y-3.5 shadow-2xs">
                    {/* Header indicating Turn and which sources were searched */}
                    <div className="flex flex-wrap items-center justify-between gap-2 border-b border-gray-100 pb-2.5">
                      <div className="flex flex-wrap items-center gap-1.5 text-[11px]">
                        <span className="font-semibold text-gray-800 flex items-center gap-1">
                          <span className="px-1.5 py-0.2 rounded bg-blue-100 text-blue-800 text-[10px] font-bold">
                            Response #{currentTurnNum}
                          </span>
                          Searched from:
                        </span>
                        {msgSources.length > 0 ? (
                          msgSources.map((src, sIdx) => (
                            <button
                              key={src.id || sIdx}
                              onClick={() => onOpenSource && onOpenSource(src, undefined, false)}
                              className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-blue-50 hover:bg-blue-100 text-blue-700 font-medium text-[11px] border border-blue-200/60 transition cursor-pointer"
                              title={`Click to view ${src.name}`}
                            >
                              <span className="font-bold text-blue-800">[{sIdx + 1}]</span>
                              <span className="truncate max-w-[180px]">{src.name}</span>
                            </button>
                          ))
                        ) : (
                          <span className="text-gray-400 italic">Corpus Analysis</span>
                        )}
                      </div>

                      <span className="text-[10px] text-gray-400 font-mono">
                        {formatTimestamp(msg.timestamp)}
                      </span>
                    </div>

                    {/* Assistant Message Body with Markdown and Grounded Citations */}
                    <div className="text-sm text-gray-800 leading-relaxed select-text space-y-3 font-sans">
                      <div className="prose prose-sm max-w-none text-gray-800 space-y-2">
                        <Markdown
                          remarkPlugins={[remarkGfm]}
                          components={{
                            h1: ({ children }) => (
                              <h1 className="text-base font-bold text-gray-900 mt-3 mb-1.5">
                                {renderWithCitations(children, msgSources)}
                              </h1>
                            ),
                            h2: ({ children }) => (
                              <h2 className="text-sm font-bold text-gray-900 mt-3 mb-1.5">
                                {renderWithCitations(children, msgSources)}
                              </h2>
                            ),
                            h3: ({ children }) => (
                              <h3 className="text-sm font-semibold text-gray-900 mt-2 mb-1">
                                {renderWithCitations(children, msgSources)}
                              </h3>
                            ),
                            p: ({ children }) => (
                              <p className="leading-relaxed mb-2.5">
                                {renderWithCitations(children, msgSources)}
                              </p>
                            ),
                            strong: ({ children }) => (
                              <strong className="font-semibold text-gray-900">
                                {renderWithCitations(children, msgSources)}
                              </strong>
                            ),
                            code: ({ children }) => (
                              <code className="bg-gray-100 text-gray-800 px-1.5 py-0.5 rounded text-xs font-mono border border-gray-200">
                                {children}
                              </code>
                            ),
                            ul: ({ children }) => (
                              <ul className="list-disc pl-5 space-y-1.5 mb-2.5">
                                {children}
                              </ul>
                            ),
                            ol: ({ children }) => (
                              <ol className="list-decimal pl-5 space-y-1.5 mb-2.5">
                                {children}
                              </ol>
                            ),
                            li: ({ children }) => (
                              <li className="leading-relaxed text-gray-800">
                                {renderWithCitations(children, msgSources)}
                              </li>
                            ),
                            blockquote: ({ children }) => (
                              <blockquote className="border-l-2 border-blue-500 pl-3 italic text-gray-600 my-2">
                                {renderWithCitations(children, msgSources)}
                              </blockquote>
                            ),
                            table: ({ children }) => (
                              <div className="my-3 overflow-x-auto rounded-xl border border-gray-200 shadow-2xs bg-white">
                                <table className="w-full text-left border-collapse text-xs">
                                  {children}
                                </table>
                              </div>
                            ),
                            thead: ({ children }) => (
                              <thead className="bg-[#f8f9fa] border-b border-gray-200 font-medium">
                                {children}
                              </thead>
                            ),
                            tbody: ({ children }) => (
                              <tbody className="divide-y divide-gray-100 bg-white">
                                {children}
                              </tbody>
                            ),
                            tr: ({ children }) => (
                              <tr className="hover:bg-blue-50/30 transition">
                                {children}
                              </tr>
                            ),
                            th: ({ children }) => (
                              <th className="px-3.5 py-2.5 font-semibold text-gray-900 text-xs border-r border-gray-200 last:border-r-0 whitespace-nowrap bg-gray-50/80">
                                {renderWithCitations(children, msgSources)}
                              </th>
                            ),
                            td: ({ children }) => (
                              <td className="px-3.5 py-2.5 text-gray-700 text-xs border-r border-gray-100 last:border-r-0 align-top leading-relaxed">
                                {renderWithCitations(children, msgSources)}
                              </td>
                            ),
                          }}
                        >
                          {msg.content}
                        </Markdown>
                      </div>
                    </div>

                    {/* Exact requested Toolbar below Output */}
                    <div className="pt-2 flex items-center gap-2 text-xs flex-wrap border-t border-gray-100">
                      {/* 1. Save to Note Pill Button */}
                      <button
                        onClick={() => handleSaveToNote(msg.id, msg.content)}
                        className={`flex items-center gap-1.5 px-3 py-1 rounded-full border text-xs font-medium transition cursor-pointer shadow-2xs ${
                          isSaved
                            ? 'bg-blue-50 border-blue-200 text-blue-700 font-semibold'
                            : 'bg-white hover:bg-gray-50 border-gray-300 text-gray-700 hover:text-gray-900'
                        }`}
                        title="Save chat output directly to Studio Notes on the right"
                      >
                        {isSaved ? (
                          <Check className="w-3.5 h-3.5 text-blue-600" />
                        ) : (
                          <Pin className="w-3.5 h-3.5 text-gray-600 rotate-45" />
                        )}
                        <span>{isSaved ? 'Saved to note' : 'Save to note'}</span>
                      </button>

                      {/* 2. Select / Square Box */}
                      <button
                        onClick={() => handleToggleSelect(msg.id)}
                        className={`p-1.5 rounded-lg border transition ${
                          isSelected
                            ? 'bg-blue-50 border-blue-300 text-blue-600'
                            : 'bg-white hover:bg-gray-50 border-transparent hover:border-gray-200 text-gray-500 hover:text-gray-800'
                        }`}
                        title="Toggle selection box"
                      >
                        {isSelected ? (
                          <CheckSquare className="w-4 h-4 text-blue-600" />
                        ) : (
                          <Square className="w-4 h-4" />
                        )}
                      </button>

                      {/* 3. Copy to Clipboard Button */}
                      <button
                        onClick={() => handleCopy(msg.id, msg.content)}
                        className="p-1.5 rounded-lg border border-transparent hover:border-gray-200 hover:bg-gray-50 text-gray-500 hover:text-gray-800 transition"
                        title="Copy to clipboard"
                      >
                        {copiedId === msg.id ? (
                          <Check className="w-4 h-4 text-emerald-600" />
                        ) : (
                          <Copy className="w-4 h-4" />
                        )}
                      </button>

                      {/* 4. Thumbs Up Button */}
                      <button
                        onClick={() => handleToggleLike(msg.id, true)}
                        className={`p-1.5 rounded-lg border transition ${
                          isLiked === true
                            ? 'bg-emerald-50 border-emerald-200 text-emerald-600'
                            : 'bg-white hover:bg-gray-50 border-transparent hover:border-gray-200 text-gray-500 hover:text-gray-800'
                        }`}
                        title="Good response"
                      >
                        <ThumbsUp className="w-4 h-4" />
                      </button>

                      {/* 5. Thumbs Down Button */}
                      <button
                        onClick={() => handleToggleLike(msg.id, false)}
                        className={`p-1.5 rounded-lg border transition ${
                          isLiked === false
                            ? 'bg-red-50 border-red-200 text-red-600'
                            : 'bg-white hover:bg-gray-50 border-transparent hover:border-gray-200 text-gray-500 hover:text-gray-800'
                        }`}
                        title="Needs improvement"
                      >
                        <ThumbsDown className="w-4 h-4" />
                      </button>

                      {/* Document & Presentation Export Shortcuts */}
                      <div className="ml-auto flex items-center gap-1.5 text-gray-400">
                        <button
                          onClick={() => {
                            const prevUserMsg = index > 0 && messages[index - 1]?.role === 'user' ? messages[index - 1].content : '';
                            const docTitle = prevUserMsg ? `Q: ${prevUserMsg.slice(0, 45)}` : `Response #${currentTurnNum} Synthesis`;
                            onCreateWordDoc(msg.content, docTitle);
                          }}
                          title="Export as Word document (.docx)"
                          className="p-1.5 hover:text-blue-600 hover:bg-gray-100 rounded-md transition"
                        >
                          <FileText className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => {
                            const prevUserMsg = index > 0 && messages[index - 1]?.role === 'user' ? messages[index - 1].content : '';
                            const deckTitle = prevUserMsg ? `Analysis: ${prevUserMsg.slice(0, 40)}` : `Response #${currentTurnNum} Presentation`;
                            onCreatePresentation(msg.content, deckTitle);
                          }}
                          title="Export as PowerPoint presentation (.pptx)"
                          className="p-1.5 hover:text-amber-600 hover:bg-gray-100 rounded-md transition"
                        >
                          <Presentation className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}

        {isGenerating && (
          <div className="w-full space-y-3 animate-in fade-in duration-150">
            <div className="flex items-center space-x-2 text-xs text-blue-600 font-medium">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Synthesizing grounded response from {selectedSourceIds.size} source(s)...</span>
            </div>
            <div className="h-16 rounded-2xl bg-gray-50 border border-gray-200/60 animate-pulse" />
          </div>
        )}
      </div>

      {/* Floating "Jump to Latest" Button */}
      {showScrollBottom && (
        <button
          onClick={scrollToBottom}
          className="absolute bottom-20 right-8 z-20 px-3 py-1.5 bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 rounded-full shadow-lg text-xs font-semibold flex items-center gap-1.5 transition animate-in fade-in slide-in-from-bottom-2 cursor-pointer"
        >
          <ArrowDown className="w-3.5 h-3.5 text-blue-600" />
          <span>Jump to Latest</span>
        </button>
      )}

      {/* Toast Notification */}
      {toastMessage && (
        <div className="absolute top-14 left-1/2 -translate-x-1/2 z-30 px-3.5 py-1.5 bg-gray-900 text-white rounded-full text-xs font-medium shadow-md flex items-center gap-1.5 animate-in fade-in slide-in-from-top-2">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Chat Input Bar */}
      <div className="p-4 border-t border-gray-100 bg-white shrink-0">
        <form
          onSubmit={handleSubmit}
          className="relative flex items-center rounded-2xl border border-gray-300 bg-white px-4 py-2.5 shadow-xs focus-within:ring-2 focus-within:ring-blue-500/20 focus-within:border-blue-500 transition"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question or create something"
            className="flex-1 bg-transparent text-sm text-gray-900 placeholder-gray-400 focus:outline-none pr-3"
          />

          {/* Inline Right Side: Sources Count & Circular Send Arrow Button */}
          <div className="flex items-center gap-3 shrink-0">
            <span className="text-xs text-gray-400 font-medium select-none">
              {selectedSourceIds.size} source{selectedSourceIds.size !== 1 ? 's' : ''}
            </span>

            <button
              type="submit"
              disabled={!input.trim() || isGenerating}
              className="w-8 h-8 rounded-full bg-blue-600 hover:bg-blue-700 text-white flex items-center justify-center transition disabled:opacity-40 disabled:hover:bg-gray-100 disabled:hover:text-gray-400 disabled:bg-gray-100 disabled:text-gray-400 disabled:cursor-not-allowed shadow-2xs active:scale-95 cursor-pointer"
              title="Send Prompt"
            >
              {isGenerating ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <ArrowRight className="w-4 h-4" />
              )}
            </button>
          </div>
        </form>
      </div>
    </section>
  );
};
