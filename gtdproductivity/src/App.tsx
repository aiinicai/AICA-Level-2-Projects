import React, { useState, useEffect, useMemo } from 'react';
import { useGTDStore } from './hooks/useGTDStore';
import { Header } from './components/Header';
import { InboxView } from './components/InboxView';
import { NextActionsView } from './components/NextActionsView';
import { ProjectsView } from './components/ProjectsView';
import { DailyReviewView } from './components/DailyReviewView';
import { SearchBar } from './components/SearchBar';
import { CaptureModal } from './components/CaptureModal';
import { ClarifyModal } from './components/ClarifyModal';
import { DataModelViewer } from './components/DataModelViewer';
import { SqlSchemaViewer } from './components/SqlSchemaViewer';
import { AvailabilityEngineDemo } from './components/AvailabilityEngineDemo';
import { DecisionsViewer } from './components/DecisionsViewer';
import { StackComparison } from './components/StackComparison';
import { MermaidDiagram } from './components/MermaidDiagram';
import { Plus, CheckSquare, Layers, Inbox, PlayCircle, RefreshCw, CalendarCheck } from 'lucide-react';

export default function App() {
  const {
    items,
    inboxItems,
    projects,
    nextActions,
    waitingForItems,
    somedayMaybeItems,
    lastDailyReview,
    completeDailyReview,
    activateSomedayMaybe,
    resolveWaitingFor,
    logWaitingForFollowUp,
    addWaitingForItem,
    addSomedayMaybeItem,
    captureItem,
    clarifyTrash,
    clarifySomedayMaybe,
    clarifyReference,
    clarifyDoNow,
    clarifyWaitingFor,
    clarifyConvertToProject,
    clarifyToNextAction,
    toggleComplete,
    toggleFlag,
    updateDueDate,
    updateContext,
    createProject,
    addActionToProject,
    resetAllData,
  } = useGTDStore();

  const [activeView, setActiveView] = useState<'inbox' | 'next_actions' | 'projects' | 'daily_review' | 'architecture'>('inbox');
  const [archTab, setArchTab] = useState<'overview' | 'schema' | 'sql' | 'availability' | 'decisions' | 'stack'>('overview');
  const [isCaptureOpen, setIsCaptureOpen] = useState(false);
  const [isClarifyOpen, setIsClarifyOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  // Global Keyboard Shortcuts (Press 'c' or 'n' to open capture)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger if user is actively typing in an input or textarea
      const target = e.target as HTMLElement;
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) {
        return;
      }

      if (e.key === 'c' || e.key === 'C' || e.key === 'n' || e.key === 'N') {
        e.preventDefault();
        setIsCaptureOpen(true);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Cross-view keyword search filtering
  const q = searchQuery.trim().toLowerCase();

  const matchingInboxItems = useMemo(() => {
    if (!q) return inboxItems;
    return inboxItems.filter(item =>
      item.title.toLowerCase().includes(q) ||
      (item.notes && item.notes.toLowerCase().includes(q))
    );
  }, [inboxItems, q]);

  const matchingNextActions = useMemo(() => {
    if (!q) return nextActions;
    return nextActions.filter(action => {
      const proj = projects.find(p => p.id === action.projectId);
      const projTitle = proj ? proj.title.toLowerCase() : '';
      const contextStr = (action.context || '').toLowerCase();
      const titleMatch = action.title.toLowerCase().includes(q);
      const notesMatch = action.notes ? action.notes.toLowerCase().includes(q) : false;
      const projMatch = projTitle.includes(q);
      const contextMatch = contextStr.includes(q);
      return titleMatch || notesMatch || projMatch || contextMatch;
    });
  }, [nextActions, projects, q]);

  const matchingProjects = useMemo(() => {
    if (!q) return projects;
    return projects.filter(project => {
      const titleMatch = project.title.toLowerCase().includes(q);
      const notesMatch = project.notes ? project.notes.toLowerCase().includes(q) : false;
      if (titleMatch || notesMatch) return true;
      return items.some(item =>
        item.projectId === project.id && !item.deletedAt && (
          item.title.toLowerCase().includes(q) ||
          (item.notes && item.notes.toLowerCase().includes(q))
        )
      );
    });
  }, [projects, items, q]);

  const isReviewedToday = useMemo(() => {
    if (!lastDailyReview) return false;
    const reviewDate = new Date(lastDailyReview);
    const today = new Date();
    return (
      reviewDate.getFullYear() === today.getFullYear() &&
      reviewDate.getMonth() === today.getMonth() &&
      reviewDate.getDate() === today.getDate()
    );
  }, [lastDailyReview]);

  const totalMatchesInActiveView = 
    activeView === 'inbox' 
      ? matchingInboxItems.length 
      : activeView === 'next_actions'
      ? matchingNextActions.length
      : activeView === 'projects'
      ? matchingProjects.length
      : activeView === 'daily_review'
      ? (waitingForItems.length + somedayMaybeItems.length + inboxItems.length)
      : (matchingInboxItems.length + matchingNextActions.length + matchingProjects.length);

  const totalItemsInActiveView =
    activeView === 'inbox'
      ? inboxItems.length
      : activeView === 'next_actions'
      ? nextActions.length
      : activeView === 'projects'
      ? projects.length
      : activeView === 'daily_review'
      ? (waitingForItems.length + somedayMaybeItems.length + inboxItems.length)
      : items.length;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-teal-50/15 to-blue-50/20 flex flex-col font-sans text-slate-800">
      {/* Top Navigation Bar */}
      <Header
        activeView={activeView}
        setActiveView={setActiveView}
        inboxCount={inboxItems.length}
        isReviewedToday={isReviewedToday}
        onOpenCapture={() => setIsCaptureOpen(true)}
        onStartClarify={() => setIsClarifyOpen(true)}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Navigation Indicator / Breadcrumb strip */}
        <div className="flex items-center justify-between text-xs text-slate-500 pb-2 border-b border-slate-200/80">
          <div className="flex items-center gap-2">
            <span className={`font-bold capitalize px-2 py-0.5 rounded text-[11px] ${
              activeView === 'inbox' 
                ? 'bg-rose-50 text-rose-800 border border-rose-200/80' 
                : activeView === 'next_actions'
                ? 'bg-teal-50 text-teal-800 border border-teal-200/80'
                : activeView === 'projects'
                ? 'bg-blue-50 text-blue-800 border border-blue-200/80'
                : activeView === 'daily_review'
                ? 'bg-emerald-50 text-emerald-800 border border-emerald-200/80'
                : 'bg-slate-100 text-slate-800'
            }`}>
              {activeView.replace('_', ' ')}
            </span>
            <span aria-hidden="true" className="text-slate-300">/</span>
            <span className="text-slate-500 font-medium">GTD Trusted System</span>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={resetAllData}
              title="Reset Sample Data"
              className="text-slate-400 hover:text-teal-700 flex items-center gap-1 cursor-pointer transition-colors"
            >
              <RefreshCw className="w-3 h-3" />
              <span>Reset Data</span>
            </button>
            <span className="hidden sm:inline text-slate-400">
              Shortcut: press <kbd className="px-1.5 py-0.5 bg-white border border-slate-200 rounded text-[10px] font-mono text-slate-600 shadow-2xs">c</kbd> to quick capture
            </span>
          </div>
        </div>

        {/* Universal Search Bar at the top of the main content area */}
        <SearchBar
          query={searchQuery}
          onQueryChange={setSearchQuery}
          activeView={activeView}
          totalMatches={totalMatchesInActiveView}
          totalItems={totalItemsInActiveView}
          viewMatchCounts={{
            inbox: matchingInboxItems.length,
            next_actions: matchingNextActions.length,
            projects: matchingProjects.length,
          }}
          onSelectView={(view) => setActiveView(view)}
        />

        {/* View 1: Inbox */}
        {activeView === 'inbox' && (
          <InboxView
            inboxItems={inboxItems}
            searchQuery={searchQuery}
            onClearSearch={() => setSearchQuery('')}
            onStartClarify={() => setIsClarifyOpen(true)}
            onOpenCapture={() => setIsCaptureOpen(true)}
            onToggleFlag={toggleFlag}
            onDelete={clarifyTrash}
          />
        )}

        {/* View 2: Next Actions */}
        {activeView === 'next_actions' && (
          <NextActionsView
            nextActions={nextActions}
            projects={projects}
            searchQuery={searchQuery}
            onClearSearch={() => setSearchQuery('')}
            onToggleComplete={toggleComplete}
            onToggleFlag={toggleFlag}
            onUpdateDueDate={updateDueDate}
            onUpdateContext={updateContext}
          />
        )}

        {/* View 3: Projects */}
        {activeView === 'projects' && (
          <ProjectsView
            projects={projects}
            allItems={items}
            searchQuery={searchQuery}
            onClearSearch={() => setSearchQuery('')}
            onCreateProject={createProject}
            onAddAction={addActionToProject}
            onToggleComplete={toggleComplete}
            onToggleFlag={toggleFlag}
          />
        )}

        {/* View 4: Daily Review */}
        {activeView === 'daily_review' && (
          <DailyReviewView
            inboxItems={inboxItems}
            waitingForItems={waitingForItems}
            somedayMaybeItems={somedayMaybeItems}
            nextActions={nextActions}
            projects={projects}
            lastDailyReview={lastDailyReview}
            onCompleteDailyReview={completeDailyReview}
            onStartClarify={() => setIsClarifyOpen(true)}
            onOpenCapture={() => setIsCaptureOpen(true)}
            onToggleComplete={toggleComplete}
            onActivateSomedayMaybe={activateSomedayMaybe}
            onResolveWaitingFor={resolveWaitingFor}
            onLogWaitingForFollowUp={logWaitingForFollowUp}
            onAddWaitingForItem={addWaitingForItem}
            onAddSomedayMaybeItem={addSomedayMaybeItem}
            onClarifyDoNow={clarifyDoNow}
            onClarifyTrash={clarifyTrash}
            onClarifySomedayMaybe={clarifySomedayMaybe}
            onClarifyConvertToProject={clarifyConvertToProject}
          />
        )}

        {/* View 5: Architecture & Specs Explorer */}
        {activeView === 'architecture' && (
          <div className="space-y-6">
            {/* Architecture Subnav */}
            <div className="flex flex-wrap gap-2 p-1 bg-slate-200/80 rounded-lg">
              <button
                onClick={() => setArchTab('overview')}
                className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors cursor-pointer ${
                  archTab === 'overview' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                10 Questions & ADRs
              </button>
              <button
                onClick={() => setArchTab('schema')}
                className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors cursor-pointer ${
                  archTab === 'schema' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Data Model & ER
              </button>
              <button
                onClick={() => setArchTab('sql')}
                className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors cursor-pointer ${
                  archTab === 'sql' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                SQL Schema & Indexes
              </button>
              <button
                onClick={() => setArchTab('availability')}
                className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors cursor-pointer ${
                  archTab === 'availability' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Availability Simulator
              </button>
              <button
                onClick={() => setArchTab('stack')}
                className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors cursor-pointer ${
                  archTab === 'stack' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Stack Comparison
              </button>
            </div>

            {archTab === 'overview' && <DecisionsViewer />}
            {archTab === 'schema' && (
              <div className="space-y-6">
                <DataModelViewer />
                <MermaidDiagram />
              </div>
            )}
            {archTab === 'sql' && <SqlSchemaViewer />}
            {archTab === 'availability' && <AvailabilityEngineDemo />}
            {archTab === 'stack' && <StackComparison />}
          </div>
        )}
      </main>

      {/* Floating Action Button for Quick Capture on Mobile */}
      <button
        onClick={() => setIsCaptureOpen(true)}
        className="fixed bottom-6 right-6 sm:hidden w-12 h-12 bg-gradient-to-r from-teal-600 to-teal-700 text-white rounded-full flex items-center justify-center shadow-lg shadow-teal-600/30 hover:from-teal-700 hover:to-teal-800 transition-all z-30 active:scale-95"
        title="Quick Capture"
      >
        <Plus className="w-5 h-5" />
      </button>

      {/* Capture Modal */}
      <CaptureModal
        isOpen={isCaptureOpen}
        onClose={() => setIsCaptureOpen(false)}
        onCapture={(title, notes, dueDate) => captureItem(title, notes, dueDate)}
      />

      {/* Guided Clarify Stepper Modal */}
      <ClarifyModal
        isOpen={isClarifyOpen}
        onClose={() => setIsClarifyOpen(false)}
        inboxItems={inboxItems}
        projects={projects}
        onTrash={clarifyTrash}
        onSomedayMaybe={clarifySomedayMaybe}
        onReference={clarifyReference}
        onDoNow={clarifyDoNow}
        onWaitingFor={clarifyWaitingFor}
        onConvertToProject={clarifyConvertToProject}
        onToNextAction={clarifyToNextAction}
      />

      {/* Quiet Footer */}
      <footer className="border-t border-slate-200 bg-white py-6 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-500">
          <div>
            GTDProductivity · Built faithfully on David Allen's Getting Things Done & OmniFocus
          </div>
          <div className="flex items-center gap-4">
            <span>Phase 1: Capture, Inbox, Clarify, Projects & Next Actions</span>
            <span aria-hidden="true">·</span>
            <span className="text-emerald-700 font-semibold">Functional & Tested</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
