import React, { useState } from 'react';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { DisclaimerBanner } from './components/DisclaimerBanner';
import { Dashboard } from './components/Dashboard';
import { FindingsTable } from './components/FindingsTable';
import { ContractViewer } from './components/ContractViewer';
import { CrossClauseAnalysis } from './components/CrossClauseAnalysis';
import { InvoiceComparison } from './components/InvoiceComparison';
import { ReportView } from './components/ReportView';
import { KnowledgeBaseView } from './components/KnowledgeBaseModal';
import { SettingsModal } from './components/SettingsModal';
import { NewAnalysis } from './components/NewAnalysis';
import { DEMO_CONTRACT_DOCUMENT } from './data/demoContract';
import { ContractDocument, Finding, FindingStatus, CAComment } from './types/contract';

export function App() {
  // Default to pre-loaded demo contract so the CA user instantly experiences the rich capabilities
  const [contract, setContract] = useState<ContractDocument | null>(DEMO_CONTRACT_DOCUMENT);
  const [activeTab, setActiveTab] = useState<string>('dashboard');
  const [selectedFinding, setSelectedFinding] = useState<Finding | null>(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState<boolean>(false);

  const handleLoadDemo = () => {
    setContract(DEMO_CONTRACT_DOCUMENT);
    setActiveTab('dashboard');
    setSelectedFinding(null);
  };

  const handleNewAnalysis = () => {
    setActiveTab('new-analysis');
    setSelectedFinding(null);
  };

  const handleAnalysisComplete = (newContract: ContractDocument) => {
    setContract(newContract);
    setActiveTab('dashboard');
    setSelectedFinding(null);
  };

  const handleSelectFinding = (finding: Finding | null) => {
    setSelectedFinding(finding);
  };

  const handleJumpToViewer = (finding: Finding) => {
    setSelectedFinding(finding);
    setActiveTab('viewer');
  };

  const handleUpdateFindingStatus = (findingId: string, status: FindingStatus) => {
    if (!contract) return;
    const updatedFindings = contract.findings.map(f => {
      if (f.id === findingId) {
        const comment: CAComment = {
          id: `c-${Date.now()}`,
          author: 'Lead Reviewer (CA)',
          text: `Status updated to: ${status}`,
          timestamp: new Date().toISOString()
        };
        return {
          ...f,
          status,
          comments: [...f.comments, comment]
        };
      }
      return f;
    });

    setContract({
      ...contract,
      findings: updatedFindings
    });

    if (selectedFinding && selectedFinding.id === findingId) {
      setSelectedFinding(prev => prev ? { ...prev, status } : null);
    }
  };

  const handleAddComment = (findingId: string, commentText: string) => {
    if (!contract) return;
    const newComment: CAComment = {
      id: `c-${Date.now()}`,
      author: 'Chartered Accountant',
      text: commentText,
      timestamp: new Date().toISOString()
    };

    const updatedFindings = contract.findings.map(f => {
      if (f.id === findingId) {
        return {
          ...f,
          comments: [...f.comments, newComment]
        };
      }
      return f;
    });

    setContract({
      ...contract,
      findings: updatedFindings
    });

    if (selectedFinding && selectedFinding.id === findingId) {
      setSelectedFinding(prev => prev ? {
        ...prev,
        comments: [...prev.comments, newComment]
      } : null);
    }
  };

  const handleRefreshCrossClause = async () => {
    if (!contract) return;
    try {
      const res = await fetch('/api/cross-clause-review', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ contract })
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.error || 'Failed to refresh cross-clause review.');
      }
      const data = await res.json();
      if (data.crossClauseInsights) {
        setContract({
          ...contract,
          crossClauseInsights: data.crossClauseInsights
        });
      }
    } catch (err: any) {
      console.error('Failed to refresh cross-clause pass:', err);
      throw err;
    }
  };

  const handleClearContract = () => {
    setContract(null);
    setActiveTab('new-analysis');
    setSelectedFinding(null);
  };

  return (
    <div className="flex h-screen w-full bg-[#F3F4F6] font-sans text-gray-900 overflow-hidden">
      {/* Left Bento Navigation Sidebar */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        contract={contract}
        mobileOpen={mobileMenuOpen}
        setMobileOpen={setMobileMenuOpen}
      />

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col overflow-hidden bg-[#F3F4F6]">
        {/* Top Header Bar */}
        <Header
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          contract={contract}
          onLoadDemo={handleLoadDemo}
          onNewAnalysis={handleNewAnalysis}
          onExportReport={() => setActiveTab('report')}
          onToggleMobileMenu={() => setMobileMenuOpen(true)}
        />

        {/* Statutory Disclaimer & Human-In-The-Loop Notice */}
        <DisclaimerBanner />

        {/* Scrollable Content View */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8">
          {activeTab === 'new-analysis' && (
            <NewAnalysis
              onAnalysisComplete={handleAnalysisComplete}
              onLoadDemo={handleLoadDemo}
            />
          )}

          {activeTab === 'dashboard' && (
            <Dashboard
              contract={contract}
              onSelectFinding={(f) => {
                setSelectedFinding(f);
                setActiveTab('findings');
              }}
              setActiveTab={setActiveTab}
              onNewAnalysis={handleNewAnalysis}
              onLoadDemo={handleLoadDemo}
            />
          )}

          {activeTab === 'findings' && contract && (
            <FindingsTable
              findings={contract.findings}
              selectedFinding={selectedFinding}
              onSelectFinding={handleSelectFinding}
              onUpdateFindingStatus={handleUpdateFindingStatus}
              onAddComment={handleAddComment}
              onJumpToViewer={handleJumpToViewer}
            />
          )}

          {activeTab === 'viewer' && contract && (
            <ContractViewer
              contract={contract}
              selectedFinding={selectedFinding}
              onSelectFinding={handleSelectFinding}
            />
          )}

          {activeTab === 'cross-clause' && contract && (
            <CrossClauseAnalysis
              contract={contract}
              onRefreshCrossClause={handleRefreshCrossClause}
            />
          )}

          {activeTab === 'comparison' && contract && (
            <InvoiceComparison
              contract={contract}
            />
          )}

          {activeTab === 'report' && contract && (
            <ReportView
              contract={contract}
            />
          )}

          {activeTab === 'knowledge' && (
            <KnowledgeBaseView />
          )}

          {activeTab === 'settings' && (
            <SettingsModal
              contract={contract}
              onClearContract={handleClearContract}
            />
          )}

          {/* Fallback if user is on contract-specific tabs without a loaded contract */}
          {!contract && activeTab !== 'new-analysis' && activeTab !== 'knowledge' && activeTab !== 'settings' && (
            <div className="max-w-md mx-auto my-16 text-center bg-white p-8 rounded-xl border border-gray-200 shadow-sm space-y-4">
              <h3 className="text-base font-bold text-gray-800">No Contract Loaded</h3>
              <p className="text-xs text-gray-500">
                Please analyze a new contract or load the demo agreement to view this section.
              </p>
              <div className="flex justify-center gap-2 pt-2">
                <button
                  onClick={handleLoadDemo}
                  className="px-4 py-2 rounded-md bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs transition"
                >
                  Load Demo Contract (₹5.2 Cr)
                </button>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;
