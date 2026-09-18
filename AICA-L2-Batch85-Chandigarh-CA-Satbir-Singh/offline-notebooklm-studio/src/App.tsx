import React, { useState, useEffect } from 'react';
import { SourceItem, ChatMessageItem, LmStudioConfig, StudioNote, ArtifactType, SourceLocationInfo } from './types';
import { INITIAL_SAMPLE_SOURCES } from './utils/sampleSources';
import { INITIAL_SAMPLE_NOTES } from './utils/sampleNotes';
import { SourceManagerPanel } from './components/SourceManagerPanel';
import { GroundedChatPanel } from './components/GroundedChatPanel';
import { OutputStudioPanel } from './components/OutputStudioPanel';
import { ViewSourceModal } from './components/ViewSourceModal';
import { ConfigModal } from './components/ConfigModal';
import { PythonBundleModal } from './components/PythonBundleModal';
import { PromptSourcesModal } from './components/PromptSourcesModal';
import { QuizModal } from './components/QuizModal';
import { CreateReportModal } from './components/CreateReportModal';
import { DataTableModal } from './components/DataTableModal';
import { generateDocxBrowser, generatePptxBrowser } from './utils/documentBuilders';
import {
  synthesizeGroundedResponse,
  generateFormalReport,
  generateReportByFormat,
  generateQuiz,
  generateDataTable,
  generateStudyGuide
} from './utils/groundedSynthesizer';
import {
  BookOpenCheck,
  Settings2,
  Terminal,
  RefreshCw,
  Sparkles
} from 'lucide-react';
import confetti from 'canvas-confetti';

export default function App() {
  // State
  const [sources, setSources] = useState<SourceItem[]>(() => {
    const saved = localStorage.getItem('notebooklm_sources');
    return saved ? JSON.parse(saved) : INITIAL_SAMPLE_SOURCES;
  });

  const [selectedSourceIds, setSelectedSourceIds] = useState<Set<string>>(() => {
    return new Set(INITIAL_SAMPLE_SOURCES.map((s) => s.id));
  });

  const [notes, setNotes] = useState<StudioNote[]>(() => {
    const saved = localStorage.getItem('notebooklm_studio_notes');
    return saved ? JSON.parse(saved) : INITIAL_SAMPLE_NOTES;
  });

  const [activeNoteId, setActiveNoteId] = useState<string | null>(null);
  const [inspectPromptNote, setInspectPromptNote] = useState<StudioNote | null>(null);

  const [messages, setMessages] = useState<ChatMessageItem[]>(() => {
    try {
      const saved = localStorage.getItem('notebooklm_chat_messages');
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) {
          return parsed;
        }
      }
    } catch {
      // Fall back to default initial summary
    }

    return [
      {
        id: 'msg-welcome',
        role: 'assistant',
        content: `This is a comprehensive summary of the **Annual Tax Statement (Form 26AS)** for **Sh. Rajinder Kumar** for the **Financial Year 2023-24 (Assessment Year 2024-25)** [1] :

**1. Taxpayer Profile**
• **Assessee Name:** Sh. Rajinder Kumar [1]
• **PAN:** BULPK6349C (Active and Operative) [1]
• **Address:** 60 Phase 2, Bapu Dham Colony, Sector 26, Chandigarh - 160019 [1]

**2. Summary of Tax Deducted at Source (TDS) - Part-I**
A total of **Rs. 17,582.04** was paid or credited to the assessee across five deductors with total TDS deducted and deposited amounting to **Rs. 846.33** [1] :

| Sr. No. | Name of Deductor | TAN | Section(s) | Total Amount Paid/Credited (Rs.) | Total Deposited (Rs.) |
| :---: | :--- | :---: | :---: | :---: | :---: |
| 1 | CSC E-GOVERNANCE SERVICES INDIA LIMITED | DELC11375A | 194C | 3,876.88 | 196.00 | [1]
| 2 | POINT INDIA NETWORK PRIVATE LIMITED | DELP09821B | 194H | 4,210.00 | 210.50 | [1]
| 3 | FINO PAYMENTS BANK LIMITED | MUMF04918A | 194H | 6,120.16 | 306.00 | [1]
| 4 | SPICE MONEY DIGITAL SERVICES | NOIS02319C | 194C | 2,145.00 | 107.25 | [1]
| 5 | PAYTM PAYMENTS BANK LTD | DELP14902E | 194C | 1,230.00 | 26.58 | [1]

**3. Key Takeaways and Factual Insights**
• **Fiduciary & Business Model Verification:** The recurring TDS entries from digital service providers like **Point India Network Private Limited** [1] and **CSC E-Governance Services India Limited** [1] directly supports the business reality of digital CSP/kiosk operations operated by Sh. Rajinder Kumar and verified against the banking ledger [2].
• **Presumptive Taxation Alignment:** The low aggregate commission income figures of **Rs. 17,582.04** further establish that the actual net commission retained from these digital kiosk networks is very small [1], directly corroborating the legal appeal defense [3] that the high-value bank deposits of over Rs. 1.14 Crore represent gross revolving public funds and are not personal business income.
• **Other Sections:** No transactions were reported under other sections, such as those for the sale/rent of immovable property, virtual digital assets, or tax collected at source (TCS) [1].`,
        timestamp: new Date().toISOString(),
      },
    ];
  });

  const [config, setConfig] = useState<LmStudioConfig>({
    baseUrl: 'http://localhost:1234/v1',
    activeModel: 'Llama-3-8B-Instruct',
    temperature: 0.7,
    isConnected: false,
    statusMessage: 'Ready to connect to LM Studio (port 1234)',
  });

  const [isGenerating, setIsGenerating] = useState(false);
  const [isGeneratingArtifact, setIsGeneratingArtifact] = useState(false);
  const [activeViewSource, setActiveViewSource] = useState<SourceItem | null>(null);
  const [activeHighlightSnippet, setActiveHighlightSnippet] = useState<string | undefined>(undefined);
  const [activeLocationInfo, setActiveLocationInfo] = useState<SourceLocationInfo | null>(null);
  const [isConfigOpen, setIsConfigOpen] = useState(false);
  const [isPythonBundleOpen, setIsPythonBundleOpen] = useState(false);
  const [notification, setNotification] = useState<string | null>(null);


  // New Modals for Granular Source-Selected Generation
  const [isQuizModalOpen, setIsQuizModalOpen] = useState(false);
  const [isReportModalOpen, setIsReportModalOpen] = useState(false);
  const [isDataTableModalOpen, setIsDataTableModalOpen] = useState(false);

  // Persist sources, notes, & chat messages
  useEffect(() => {
    localStorage.setItem('notebooklm_sources', JSON.stringify(sources));
  }, [sources]);

  useEffect(() => {
    localStorage.setItem('notebooklm_studio_notes', JSON.stringify(notes));
  }, [notes]);

  useEffect(() => {
    localStorage.setItem('notebooklm_chat_messages', JSON.stringify(messages));
  }, [messages]);

  const showNotification = (msg: string) => {
    setNotification(msg);
    setTimeout(() => setNotification(null), 3500);
  };

  // Test LM Studio Connection
  const testLmStudioConnection = async () => {
    try {
      const target = config.baseUrl.replace(/\/v1$/, '') + '/v1/models';
      const res = await fetch(target, { method: 'GET', signal: AbortSignal.timeout(3000) });
      if (res.ok) {
        const data = await res.json();
        const modelName = data.data?.[0]?.id || 'Local Model';
        setConfig((prev) => ({
          ...prev,
          isConnected: true,
          activeModel: modelName,
          statusMessage: `Connected: ${modelName}`,
        }));
        showNotification(`Connected to LM Studio (${modelName})`);
      } else {
        throw new Error(`HTTP ${res.status}`);
      }
    } catch {
      setConfig((prev) => ({
        ...prev,
        isConnected: false,
        statusMessage: 'LM Studio: Standalone Ready (Port 1234)',
      }));
    }
  };

  useEffect(() => {
    testLmStudioConnection();
  }, [config.baseUrl]);

  // Source selection toggles
  const handleToggleSelect = (id: string) => {
    setSelectedSourceIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleSelectAll = () => {
    setSelectedSourceIds(new Set(sources.map((s) => s.id)));
  };

  const handleDeselectAll = () => {
    setSelectedSourceIds(new Set());
  };

  const handleAddSources = (newSources: SourceItem[]) => {
    setSources((prev) => [...newSources, ...prev]);
    setSelectedSourceIds((prev) => {
      const next = new Set(prev);
      newSources.forEach((s) => next.add(s.id));
      return next;
    });
    showNotification(`Added ${newSources.length} source(s) to context`);
  };

  const handleRenameSource = (id: string, newName: string) => {
    setSources((prev) =>
      prev.map((s) => (s.id === id ? { ...s, name: newName } : s))
    );
    showNotification('Source renamed');
  };

  const handleDeleteSource = (id: string) => {
    setSources((prev) => prev.filter((s) => s.id !== id));
    setSelectedSourceIds((prev) => {
      const next = new Set(prev);
      next.delete(id);
      return next;
    });
    showNotification('Source removed');
  };

  // Convert Note to Grounded Source (NotebookLM Recursive Loop)
  const handleConvertToSource = (note: StudioNote) => {
    const filename = note.title.toLowerCase().endsWith('.md')
      ? note.title
      : `${note.title.replace(/[^a-zA-Z0-9_-]/g, '_')}.md`;

    const preview =
      note.content.slice(0, 240).replace(/\n+/g, ' ').trim() +
      (note.content.length > 240 ? '...' : '');

    const newSource: SourceItem = {
      id: 'src-gen-' + Math.random().toString(36).substring(2, 9),
      name: filename,
      fileType: 'MD',
      sizeBytes: new Blob([note.content]).size,
      charCount: note.content.length,
      preview: preview,
      text: note.content,
      createdAt: new Date().toISOString(),
      isGenerated: true,
    };

    setSources((prev) => [newSource, ...prev]);
    setSelectedSourceIds((prev) => new Set([newSource.id, ...Array.from(prev)]));
    showNotification('✨ Converted to grounded source in Left Panel!');
  };

  // Granular Grounded Generation Handlers with Modal Source Selection
  const handleGenerateQuizModal = ({
    sources: chosenSources,
    numQuestions,
    difficulty,
    topic,
  }: {
    sources: SourceItem[];
    numQuestions: 'fewer' | 'standard' | 'more';
    difficulty: 'easy' | 'medium' | 'hard';
    topic: string;
  }) => {
    setIsGeneratingArtifact(true);
    const result = generateQuiz(chosenSources, { numQuestions, difficulty, topic });
    const promptDescription = `Grounded Quiz (${numQuestions} questions, ${difficulty} difficulty) on topic "${topic || 'Selected Corpus'}".`;

    const newNote: StudioNote = {
      id: 'note-quiz-' + Date.now(),
      title: result.title,
      content: result.content,
      type: 'quiz',
      sourcesCount: chosenSources.length,
      sourceNames: chosenSources.map((s) => s.name),
      promptUsed: promptDescription,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    setNotes((prev) => [newNote, ...prev]);
    setActiveNoteId(newNote.id);
    setIsGeneratingArtifact(false);
    setIsQuizModalOpen(false);
    confetti({
      particleCount: 60,
      spread: 60,
      origin: { y: 0.7 },
      colors: ['#0288d1', '#38bdf8', '#34d399'],
    });
    showNotification('Created Quiz in Studio Notes!');
  };

  const handleGenerateReportModal = ({
    sources: chosenSources,
    formatType,
    customTitle,
    customInstructions,
  }: {
    sources: SourceItem[];
    formatType: string;
    customTitle?: string;
    customInstructions?: string;
  }) => {
    setIsGeneratingArtifact(true);
    const result = generateReportByFormat(chosenSources, formatType, customTitle, customInstructions);
    const promptDescription = `Report (${formatType}): ${customInstructions || customTitle || 'Structured Briefing'}`;

    const newNote: StudioNote = {
      id: 'note-report-' + Date.now(),
      title: result.title,
      content: result.content,
      type: 'report',
      sourcesCount: chosenSources.length,
      sourceNames: chosenSources.map((s) => s.name),
      promptUsed: promptDescription,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    setNotes((prev) => [newNote, ...prev]);
    setActiveNoteId(newNote.id);
    setIsGeneratingArtifact(false);
    setIsReportModalOpen(false);
    confetti({
      particleCount: 60,
      spread: 60,
      origin: { y: 0.7 },
      colors: ['#f59e0b', '#34d399', '#38bdf8'],
    });
    showNotification('Created Report in Studio Notes!');
  };

  const handleGenerateDataTableModal = ({
    sources: chosenSources,
    language,
    prompt,
  }: {
    sources: SourceItem[];
    language: string;
    prompt: string;
  }) => {
    setIsGeneratingArtifact(true);
    const result = generateDataTable(chosenSources, { language, prompt });
    const promptDescription = `Data Table in ${language}: ${prompt || 'Quantitative metrics & tabular extraction'}`;

    const newNote: StudioNote = {
      id: 'note-table-' + Date.now(),
      title: result.title,
      content: result.content,
      type: 'datatable',
      sourcesCount: chosenSources.length,
      sourceNames: chosenSources.map((s) => s.name),
      promptUsed: promptDescription,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    setNotes((prev) => [newNote, ...prev]);
    setActiveNoteId(newNote.id);
    setIsGeneratingArtifact(false);
    setIsDataTableModalOpen(false);
    confetti({
      particleCount: 60,
      spread: 60,
      origin: { y: 0.7 },
      colors: ['#7c3aed', '#38bdf8', '#34d399'],
    });
    showNotification('Created Data Table in Studio Notes!');
  };

  // Quick Generation of Artifacts fallback
  const handleGenerateQuickArtifact = (type: ArtifactType) => {
    const activeSources = sources.filter((s) => selectedSourceIds.has(s.id));
    if (activeSources.length === 0) {
      showNotification('Please select at least 1 active source in the Left Panel.');
      return;
    }

    setIsGeneratingArtifact(true);
    let result: { title: string; content: string };
    let promptDescription = '';

    switch (type) {
      case 'report':
        result = generateFormalReport(activeSources);
        promptDescription = `Generate a structured formal briefing document with executive summary, findings, and metrics.`;
        break;
      case 'quiz':
        result = generateQuiz(activeSources);
        promptDescription = `Create a grounded self-assessment quiz with multiple-choice questions, citations, and explanations.`;
        break;
      case 'datatable':
        result = generateDataTable(activeSources);
        promptDescription = `Extract quantitative metrics and comparative tables grounded in the selected sources.`;
        break;
      case 'study_guide':
      default:
        result = generateStudyGuide(activeSources);
        promptDescription = `Synthesize a comprehensive study guide with glossary, core concepts, and essay prompts.`;
        break;
    }

    const newNote: StudioNote = {
      id: 'note-' + Date.now(),
      title: result.title,
      content: result.content,
      type,
      sourcesCount: activeSources.length,
      sourceNames: activeSources.map((s) => s.name),
      promptUsed: promptDescription,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    setNotes((prev) => [newNote, ...prev]);
    setActiveNoteId(newNote.id);
    setIsGeneratingArtifact(false);
    confetti({
      particleCount: 60,
      spread: 60,
      origin: { y: 0.7 },
      colors: ['#38bdf8', '#34d399', '#f59e0b'],
    });
    showNotification(`Generated ${type.replace('_', ' ')} in Studio!`);
  };

  // Add Manual Note
  const handleAddNote = (newNoteData: Partial<StudioNote>) => {
    const activeSources = sources.filter((s) => selectedSourceIds.has(s.id));
    const newNote: StudioNote = {
      id: 'note-' + Date.now(),
      title: newNoteData.title || `Note ${notes.length + 1}`,
      content: newNoteData.content || `# Note ${notes.length + 1}\n\nType your notes here...`,
      type: newNoteData.type || 'note',
      sourcesCount: activeSources.length,
      sourceNames: activeSources.map((s) => s.name),
      promptUsed: newNoteData.promptUsed || 'User authored note',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    setNotes((prev) => [newNote, ...prev]);
    setActiveNoteId(newNote.id);
    showNotification('Created new note in Studio');
  };

  const handleUpdateNote = (id: string, updates: Partial<StudioNote>) => {
    setNotes((prev) =>
      prev.map((n) => (n.id === id ? { ...n, ...updates, updatedAt: new Date().toISOString() } : n))
    );
  };

  const handleDeleteNote = (id: string) => {
    setNotes((prev) => prev.filter((n) => n.id !== id));
    if (activeNoteId === id) {
      setActiveNoteId(null);
    }
    showNotification('Note deleted');
  };

  // Send Chat Message
  const handleSendMessage = async (userPrompt: string) => {
    const userMsg: ChatMessageItem = {
      id: 'msg-' + Date.now(),
      role: 'user',
      content: userPrompt,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsGenerating(true);

    const activeSources = sources.filter((s) => selectedSourceIds.has(s.id));

    if (activeSources.length === 0) {
      const emptyMsg: ChatMessageItem = {
        id: 'msg-' + Date.now(),
        role: 'assistant',
        content: `⚠️ **No source document selected in the left panel.**\n\nPlease select at least one document checkbox from the left panel to search and ground your inquiry. Chat analysis is strictly confined only to your selected documents.`,
        timestamp: new Date().toISOString(),
        sourcesGrounded: [],
        sourceItemsGrounded: [],
      };
      setMessages((prev) => [...prev, emptyMsg]);
      setIsGenerating(false);
      return;
    }

    const contextBlocks = activeSources
      .map(
        (s, idx) =>
          `=== SOURCE [${idx + 1}]: ${s.name} (${s.fileType}) ===\n${s.text}\n=== END SOURCE [${idx + 1}] ===`
      )
      .join('\n\n');

    let assistantResponse = '';

    // Tier 1: Try Local LM Studio endpoint if configured and available
    let answered = false;
    if (config.baseUrl) {
      try {
        const targetUrl = config.baseUrl.replace(/\/v1$/, '') + '/v1/chat/completions';
        const promptSystem = `You are an expert research analyst and document synthesizer (NotebookLM style).
You have access to ONLY the following ${activeSources.length} grounded source(s):
${contextBlocks}

FORMATTING INSTRUCTIONS:
- Ground your entire response exclusively on the provided source documents.
- MANDATORY TABLE FORMATTING: If data in the source document is in table, spreadsheet (CSV/Excel sheets), matrix, tax slab, or columnar format, you MUST present and output that data in structured Markdown table format (| Col 1 | Col 2 | ... |) in the chat response. Never collapse tabular data into plain bullet paragraphs.
- If the user asks a specific question or topic (e.g. "key changes about income tax", "what are the tax slabs", "TDS rates", "clause 12"), answer THAT question directly using exact facts, quotes, sections, rates, and numbers found in the text. Present comparative or tabular findings in Markdown tables. Do not output a generic profile if a specific topic was asked.
- If summarizing or asking for an executive overview, start with an introductory summary followed by:
  1. Document / Subject Profile (with bold bullet points and citations)
  2. Summary of Key Data, Clauses & Metrics - Part-I (clean Markdown table with "Sr. No.")
  3. Key Takeaways and Factual Insights
  4. Strategic / Compliance Observations
- Cite sources using bracketed numbers [1], [2] directly corresponding to the sources above.`;

        const resp = await fetch(targetUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            model: config.activeModel || 'local-model',
            messages: [
              { role: 'system', content: promptSystem },
              ...messages.map((m) => ({ role: m.role, content: m.content })),
              { role: 'user', content: userPrompt },
            ],
            temperature: config.temperature,
            stream: false,
          }),
          signal: AbortSignal.timeout(5000),
        });

        if (resp.ok) {
          const data = await resp.json();
          assistantResponse =
            data.choices?.[0]?.message?.content || '';
          if (assistantResponse) answered = true;
        }
      } catch {
        // Fallback to Tier 2
      }
    }

    // Tier 2: Server-side Gemini AI
    if (!answered) {
      try {
        const serverResp = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            prompt: userPrompt,
            sources: activeSources.map((s) => ({
              id: s.id,
              name: s.name,
              fileType: s.fileType,
              charCount: s.charCount,
              text: s.text,
            })),
            messages: messages.map((m) => ({ role: m.role, content: m.content })),
          }),
          signal: AbortSignal.timeout(15000),
        });

        if (serverResp.ok) {
          const sData = await serverResp.json();
          if (sData.content) {
            assistantResponse = sData.content;
            answered = true;
          }
        }
      } catch {
        // Fallback to Tier 3
      }
    }

    // Tier 3: Local Grounded Synthesizer (Instant, Universal, 100% Deterministic)
    if (!answered || !assistantResponse) {
      assistantResponse = synthesizeGroundedResponse(userPrompt, activeSources);
    }

    const assistantMsg: ChatMessageItem = {
      id: 'msg-' + Date.now(),
      role: 'assistant',
      content: assistantResponse,
      timestamp: new Date().toISOString(),
      sourcesGrounded: activeSources.map((s) => s.name),
      sourceItemsGrounded: activeSources,
    };

    setMessages((prev) => [...prev, assistantMsg]);
    setIsGenerating(false);
  };

  // Handlers for action buttons from chat
  const handleSendToReport = (text: string) => {
    const activeSources = sources.filter((s) => selectedSourceIds.has(s.id));
    const title = text.split('\n')[0].replace(/^[#\s*]+/, '').trim() || 'Grounded Synthesis Note';

    const newNote: StudioNote = {
      id: 'note-' + Date.now(),
      title: title.slice(0, 60),
      content: text,
      type: 'report',
      sourcesCount: activeSources.length,
      sourceNames: activeSources.map((s) => s.name),
      promptUsed: 'Grounded chat response sent to Studio',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    setNotes((prev) => [newNote, ...prev]);
    setActiveNoteId(newNote.id);
    showNotification('Saved to Studio Notes!');
  };

  const handleCreateWordDoc = async (text: string, title?: string) => {
    let resolvedTitle = title || '';
    if (!resolvedTitle || resolvedTitle === 'Grounded Response Synthesis') {
      const headingMatch = text.match(/^#+\s*(.+)$/m);
      if (headingMatch) {
        resolvedTitle = headingMatch[1].replace(/[*_`]/g, '').trim();
      } else {
        const firstLine = text.split('\n')[0].replace(/[*#_`]/g, '').trim();
        resolvedTitle = firstLine ? firstLine.slice(0, 50) : 'Grounded Response Synthesis';
      }
    }
    showNotification('Generating Word document (.docx)...');
    await generateDocxBrowser(text, resolvedTitle);
    showNotification('Word document (.docx) downloaded!');
  };

  const handleCreatePresentation = async (text: string, title?: string) => {
    let resolvedTitle = title || '';
    if (!resolvedTitle || resolvedTitle === 'Executive Presentation') {
      const headingMatch = text.match(/^#+\s*(.+)$/m);
      if (headingMatch) {
        resolvedTitle = headingMatch[1].replace(/[*_`]/g, '').trim();
      } else {
        const firstLine = text.split('\n')[0].replace(/[*#_`]/g, '').trim();
        resolvedTitle = firstLine ? firstLine.slice(0, 50) : 'Executive Presentation';
      }
    }
    showNotification('Generating 16:9 Presentation (.pptx)...');
    await generatePptxBrowser(text, resolvedTitle);
    showNotification('PowerPoint deck (.pptx) downloaded!');
  };

  return (
    <div className="h-screen w-screen flex flex-col bg-[#f8f9fa] text-gray-900 font-sans overflow-hidden select-none">
      {/* Top Navigation Header */}
      <header className="h-14 border-b border-gray-200 bg-white flex items-center justify-between px-6 shrink-0 z-20 shadow-xs">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center text-white shadow-sm">
            <BookOpenCheck className="w-4 h-4 text-white" />
          </div>
          <div>
            <h1 className="text-base font-semibold tracking-tight text-gray-900 flex items-center gap-2">
              Offline NotebookLM Studio
              <span className="text-[10px] uppercase font-semibold tracking-wider px-2 py-0.5 rounded-full bg-blue-50 text-blue-600 border border-blue-100">
                LM Studio Grounded
              </span>
            </h1>
          </div>
        </div>

        {/* Status Bar & Actions */}
        <div className="flex items-center space-x-3">
          {/* LM Studio Connection Pill */}
          <div className="flex items-center bg-green-50 px-3 py-1 rounded-full border border-green-200 text-xs font-medium text-green-700">
            <span
              className={`w-2 h-2 rounded-full mr-2 ${
                config.isConnected ? 'bg-green-500' : 'bg-amber-500 animate-pulse'
              }`}
            />
            <span className="truncate max-w-[200px]">
              {config.isConnected ? `LM Studio: ${config.activeModel}` : 'LM Studio (Port 1234)'}
            </span>
            <button
              onClick={testLmStudioConnection}
              title="Test LM Studio Connection"
              className="ml-1.5 p-0.5 hover:text-green-900 rounded transition"
            >
              <RefreshCw className="w-3 h-3" />
            </button>
          </div>

          {/* Python Desktop Server Button */}
          <button
            onClick={() => setIsPythonBundleOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-gray-100 hover:bg-gray-200 text-gray-700 border border-gray-200 transition shadow-2xs"
          >
            <Terminal className="w-3.5 h-3.5 text-gray-600" />
            <span>Python Desktop Server</span>
          </button>

          {/* Config Modal Button */}
          <button
            onClick={() => setIsConfigOpen(true)}
            title="Settings & Model Setup"
            className="p-2 hover:bg-gray-100 rounded-lg text-gray-600 hover:text-gray-900 border border-gray-200 transition"
          >
            <Settings2 className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* Main 3-Panel Workspace */}
      <main className="flex-1 grid grid-cols-12 gap-0 overflow-hidden bg-[#f8f9fa]">
        {/* Left Panel: Source Manager (3 cols) */}
        <div className="col-span-3 h-full overflow-hidden border-r border-gray-200 bg-white">
          <SourceManagerPanel
            sources={sources}
            selectedSourceIds={selectedSourceIds}
            onToggleSelect={handleToggleSelect}
            onSelectAll={handleSelectAll}
            onDeselectAll={handleDeselectAll}
            onAddSources={handleAddSources}
            onViewSource={(s) => setActiveViewSource(s)}
            onRenameSource={handleRenameSource}
            onDeleteSource={handleDeleteSource}
          />
        </div>

        {/* Center Panel: Grounded Chat (5 cols) */}
        <div className="col-span-5 h-full overflow-hidden border-r border-gray-200 bg-white">
          <GroundedChatPanel
            sources={sources}
            selectedSourceIds={selectedSourceIds}
            messages={messages}
            config={config}
            onSendMessage={handleSendMessage}
            onClearChat={() => setMessages([])}
            onSendToReport={handleSendToReport}
            onCreateWordDoc={handleCreateWordDoc}
            onCreatePresentation={handleCreatePresentation}
            onOpenSource={(source, location, openInNewTab) => {
              if (openInNewTab) {
                const title = source.name;
                const locLabel = location?.locationLabel || 'Document Viewer';
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
                        .location-banner { background: #e8f0fe; border: 1px solid #c2e7ff; border-radius: 8px; padding: 12px 16px; margin-bottom: 16px; font-size: 13px; color: #174ea6; }
                        .container { background: #fff; padding: 24px; border-radius: 12px; border: 1px solid #e0e0e0; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, monospace; font-size: 12px; line-height: 1.65; white-space: pre-wrap; word-break: break-word; }
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
                      ${locLabel ? `<div class="location-banner"><strong>📍 Grounded Citation:</strong> ${locLabel}</div>` : ''}
                      <div class="container" id="content">${content}</div>
                    </body>
                    </html>
                  `);
                  newWindow.document.close();
                }
              } else {
                setActiveLocationInfo(location || null);
                setActiveHighlightSnippet(location?.snippet);
                setActiveViewSource(source);
              }
            }}
            isGenerating={isGenerating}
          />
        </div>

        {/* Right Panel: Output Studio & Document Generator (4 cols) */}
        <div className="col-span-4 h-full overflow-hidden bg-[#fafafa]">
          <OutputStudioPanel
            notes={notes}
            activeNoteId={activeNoteId}
            sources={sources}
            selectedSourceIds={selectedSourceIds}
            onSelectNote={(id) => setActiveNoteId(id)}
            onAddNote={handleAddNote}
            onUpdateNote={handleUpdateNote}
            onDeleteNote={handleDeleteNote}
            onConvertToSource={handleConvertToSource}
            onExportDocx={async (content, title) => {
              showNotification('Generating Word document (.docx)...');
              await generateDocxBrowser(content, title);
              showNotification('Word document downloaded!');
            }}
            onExportPptx={async (content, title) => {
              showNotification('Generating 16:9 presentation (.pptx)...');
              await generatePptxBrowser(content, title);
              showNotification('PowerPoint deck downloaded!');
            }}
            onOpenReportModal={() => setIsReportModalOpen(true)}
            onOpenQuizModal={() => setIsQuizModalOpen(true)}
            onOpenDataTableModal={() => setIsDataTableModalOpen(true)}
            onViewPromptAndSources={(note) => setInspectPromptNote(note)}
            isGeneratingArtifact={isGeneratingArtifact}
          />
        </div>
      </main>

      {/* Toast Notification */}
      {notification && (
        <div className="fixed bottom-5 right-5 z-50 px-4 py-2.5 rounded-xl bg-gray-900 text-white text-xs font-medium shadow-lg flex items-center gap-2 animate-in fade-in slide-in-from-bottom-2 duration-200">
          <Sparkles className="w-3.5 h-3.5 text-blue-400" />
          <span>{notification}</span>
        </div>
      )}

      {/* Modals */}
      <ViewSourceModal
        source={activeViewSource}
        highlightSnippet={activeHighlightSnippet}
        locationInfo={activeLocationInfo}
        onClose={() => {
          setActiveViewSource(null);
          setActiveHighlightSnippet(undefined);
          setActiveLocationInfo(null);
        }}
      />

      <PromptSourcesModal
        note={inspectPromptNote}
        onClose={() => setInspectPromptNote(null)}
      />

      <QuizModal
        isOpen={isQuizModalOpen}
        onClose={() => setIsQuizModalOpen(false)}
        sources={sources}
        selectedSourceIds={selectedSourceIds}
        onGenerate={handleGenerateQuizModal}
        isGenerating={isGeneratingArtifact}
      />

      <CreateReportModal
        isOpen={isReportModalOpen}
        onClose={() => setIsReportModalOpen(false)}
        sources={sources}
        selectedSourceIds={selectedSourceIds}
        onGenerateReport={handleGenerateReportModal}
        isGenerating={isGeneratingArtifact}
      />

      <DataTableModal
        isOpen={isDataTableModalOpen}
        onClose={() => setIsDataTableModalOpen(false)}
        sources={sources}
        selectedSourceIds={selectedSourceIds}
        onGenerateTable={handleGenerateDataTableModal}
        isGenerating={isGeneratingArtifact}
      />

      <ConfigModal
        config={config}
        isOpen={isConfigOpen}
        onClose={() => setIsConfigOpen(false)}
        onSave={(newCfg) => {
          setConfig(newCfg);
          showNotification('Configuration saved');
        }}
        onTestConnection={testLmStudioConnection}
      />

      <PythonBundleModal
        isOpen={isPythonBundleOpen}
        onClose={() => setIsPythonBundleOpen(false)}
      />
    </div>
  );
}
