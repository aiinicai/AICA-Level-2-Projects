import React, { useState, useMemo, useEffect } from 'react';
import { Navbar } from './components/Navbar';
import { ControlTower } from './components/ControlTower';
import { AssetRegister } from './components/AssetRegister';
import { AiCapitalisationReview } from './components/AiCapitalisationReview';
import { PhysicalVerification } from './components/PhysicalVerification';
import { RiskEngine } from './components/RiskEngine';
import { ExceptionsWorkflow } from './components/ExceptionsWorkflow';
import { PolicyCompliance } from './components/PolicyCompliance';
import { AuditReadiness } from './components/AuditReadiness';
import { UserManual } from './components/UserManual';
import { QuickStartGuideModal } from './components/QuickStartGuideModal';
import { AssetDetailModal } from './components/AssetDetailModal';
import { DemoAssetShowcase } from './components/DemoAssetShowcase';
import { CompanyModal } from './components/CompanyModal';
import { CompanyDataStudio } from './components/CompanyDataStudio';
import { calculateReliabilityScore } from './services/reliabilityScore';
import { 
  getStoredCompanies, 
  getActiveCompanyId, 
  setActiveCompanyId, 
  getCompanyData, 
  saveCompanyData, 
  createNewCompany as createCompanyService,
  deleteCompany as deleteCompanyService
} from './services/companyStorage';
import { Asset, CapexItem, RiskFinding, VerificationScanRecord, CapitalisationReviewResult, Company } from './types';

export default function App() {
  const [activeTab, setActiveTab] = useState('control-tower');
  const [currencyMode, setCurrencyMode] = useState<'Lakhs' | 'Crores' | 'Full'>('Crores');
  
  // Multi-Company State
  const [allCompanies, setAllCompanies] = useState<Company[]>(() => getStoredCompanies());
  const [activeCompanyId, setActiveCompanyIdState] = useState<string>(() => getActiveCompanyId());
  const [showCreateCompanyModal, setShowCreateCompanyModal] = useState(false);

  const activeCompany = useMemo(() => {
    return allCompanies.find((c) => c.id === activeCompanyId) || allCompanies[0];
  }, [allCompanies, activeCompanyId]);

  // Primary State Data Stores for the Active Company
  const initialCompanyData = useMemo(() => {
    return getCompanyData(activeCompanyId, activeCompany);
  }, [activeCompanyId]);

  const [assets, setAssets] = useState<Asset[]>(initialCompanyData.assets);
  const [capexQueue, setCapexQueue] = useState<CapexItem[]>(initialCompanyData.capexQueue);
  const [risks, setRisks] = useState<RiskFinding[]>(initialCompanyData.risks);
  const [scanLogs, setScanLogs] = useState<VerificationScanRecord[]>(initialCompanyData.scanLogs);

  // Sync state whenever activeCompanyId changes
  const handleSwitchCompany = (companyId: string) => {
    // Save current active company data before switching
    saveCompanyData(activeCompanyId, {
      company: activeCompany,
      assets,
      capexQueue,
      risks,
      scanLogs
    });

    const targetCompany = allCompanies.find((c) => c.id === companyId) || allCompanies[0];
    const targetData = getCompanyData(companyId, targetCompany);

    setActiveCompanyId(companyId);
    setActiveCompanyIdState(companyId);
    setAssets(targetData.assets);
    setCapexQueue(targetData.capexQueue);
    setRisks(targetData.risks);
    setScanLogs(targetData.scanLogs);
  };

  // Persist changes to active company dataset
  useEffect(() => {
    if (activeCompanyId && activeCompany) {
      saveCompanyData(activeCompanyId, {
        company: activeCompany,
        assets,
        capexQueue,
        risks,
        scanLogs
      });
    }
  }, [assets, capexQueue, risks, scanLogs, activeCompanyId, activeCompany]);

  // Modals & Navigation state
  const [selectedAssetForModal, setSelectedAssetForModal] = useState<Asset | null>(null);
  const [showDemoShowcase, setShowDemoShowcase] = useState(false);
  const [showQuickTour, setShowQuickTour] = useState(false);
  const [targetRiskForWorkflow, setTargetRiskForWorkflow] = useState<string | null>(null);

  // Dynamic Reliability Score calculation
  const reliabilityScore = useMemo(() => {
    return calculateReliabilityScore(assets, risks);
  }, [assets, risks]);

  // Handlers for Data Ingestion & Company Creation
  const handleCreateCompany = (
    companyInput: Omit<Company, 'id' | 'createdAt'>,
    mode: 'blank' | 'template' | 'custom_assets'
  ) => {
    const { newCompany, companyData } = createCompanyService(companyInput, mode);
    const updatedCompanies = getStoredCompanies();
    setAllCompanies(updatedCompanies);
    setActiveCompanyIdState(newCompany.id);
    setAssets(companyData.assets);
    setCapexQueue(companyData.capexQueue);
    setRisks(companyData.risks);
    setScanLogs(companyData.scanLogs);
    setActiveTab('data-studio');
  };

  const handleDeleteCompany = (companyId: string) => {
    const updated = deleteCompanyService(companyId);
    setAllCompanies(updated);
    const fallbackId = updated[0]?.id || 'comp-assettrust';
    handleSwitchCompany(fallbackId);
  };

  const handleImportAssets = (newAssets: Asset[], mode: 'append' | 'overwrite') => {
    if (mode === 'overwrite') {
      setAssets(newAssets);
    } else {
      setAssets((prev) => [...newAssets, ...prev]);
    }
  };

  const handleImportCapex = (newCapex: CapexItem[]) => {
    setCapexQueue((prev) => [...newCapex, ...prev]);
  };

  const handleAddManualAsset = (newAsset: Asset) => {
    setAssets((prev) => [newAsset, ...prev]);
  };

  // Handler for adding newly approved capitalised asset from Capex Review into Asset Register
  const handleAddCapitalisedAsset = (item: CapexItem, review: CapitalisationReviewResult) => {
    const newAssetId = `AST-${item.plant.substring(0, 3).toUpperCase()}-NEW-${Date.now().toString().slice(-4)}`;
    const newAsset: Asset = {
      id: newAssetId,
      name: item.description.substring(0, 60),
      category: (review.recommendedCategory as any) || item.suggestedCategory,
      plant: item.plant,
      subLocation: 'Inbound Project Zone / Bay 1',
      costINR: item.amountINR,
      accumulatedDepINR: 0,
      nbvINR: item.amountINR,
      capitalisationDate: new Date().toISOString().split('T')[0],
      usefulLifeYears: review.usefulLifeYears,
      schIILifeYears: review.usefulLifeYears,
      depreciationMethod: 'SLM',
      status: 'Active',
      verificationStatus: 'Verified',
      riskLevel: 'Low',
      lastVerifiedDate: new Date().toISOString().split('T')[0],
      serialNumber: `SN-${Date.now().toString().slice(-6)}`,
      qrCode: `QR-${newAssetId}`,
      vendor: item.vendor,
      invoiceNumber: item.invoiceNumber,
      poNumber: item.poNumber,
      grnNumber: `GRN-${Date.now().toString().slice(-5)}`,
      itcClaimed: review.gstItcEligibility === 'Eligible',
      gstPaidINR: review.gstItcEligibility === 'Eligible' ? item.amountINR * 0.18 : undefined,
      description: item.description,
      custodian: 'Project Manager / Plant Lead',
      department: item.department,
      components: review.componentisationDetails?.map((cmp, idx) => ({
        id: `${newAssetId}-CMP-${idx + 1}`,
        name: cmp.name,
        costINR: Math.round((item.amountINR * cmp.costRatioPct) / 100),
        accumulatedDepINR: 0,
        nbvINR: Math.round((item.amountINR * cmp.costRatioPct) / 100),
        usefulLifeYears: cmp.usefulLifeYears,
        depreciationMethod: 'SLM',
        notes: cmp.justification
      })) || [],
      anomalies: [],
      historyEvents: [
        {
          id: `EVT-${Date.now()}`,
          date: new Date().toISOString().split('T')[0],
          type: 'Capitalisation',
          description: `Capitalised under Ind AS 16 upon formal AI Review & Controller approval (${item.humanApproval?.approver || 'Controller'}).`,
          actor: item.humanApproval?.approver || 'Finance Controller',
          status: 'Completed'
        }
      ]
    };

    setAssets((prev) => [newAsset, ...prev]);
  };

  // Quick navigation helpers
  const handleNavigateToAsset = (assetId: string) => {
    const found = assets.find((a) => a.id === assetId);
    if (found) {
      setSelectedAssetForModal(found);
    } else {
      setActiveTab('register');
    }
  };

  const handleNavigateToExceptions = (riskId?: string) => {
    if (riskId) {
      setTargetRiskForWorkflow(riskId);
    }
    setActiveTab('exceptions');
  };

  // Find demo CNC asset for spotlight
  const demoCncAsset = assets.find((a) => a.id === 'AST-PUN-CNC-0042') || assets[0];

  return (
    <div className="min-h-screen bg-[#F1F5F9] text-slate-800 flex flex-col font-sans selection:bg-blue-600 selection:text-white">
      {/* Global Navigation Header with Multi-Company Selector */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        currencyMode={currencyMode}
        setCurrencyMode={setCurrencyMode}
        reliabilityScore={reliabilityScore}
        onOpenDemoSpotlight={() => setShowDemoShowcase(true)}
        onOpenQuickTour={() => setShowQuickTour(true)}
        openRiskCount={risks.filter(r => r.status !== 'Closed').length}
        activeCompany={activeCompany}
        allCompanies={allCompanies}
        onSwitchCompany={handleSwitchCompany}
        onOpenCreateCompanyModal={() => setShowCreateCompanyModal(true)}
      />

      {/* Main View Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {activeTab === 'control-tower' && (
          <ControlTower
            assets={assets}
            risks={risks}
            capexQueue={capexQueue}
            reliabilityScore={reliabilityScore}
            currencyMode={currencyMode}
            onNavigateTab={setActiveTab}
            onSelectAsset={setSelectedAssetForModal}
            onOpenDemoSpotlight={() => setShowDemoShowcase(true)}
          />
        )}

        {activeTab === 'data-studio' && (
          <CompanyDataStudio
            activeCompany={activeCompany}
            allCompanies={allCompanies}
            assets={assets}
            capexQueue={capexQueue}
            currencyMode={currencyMode}
            onSwitchCompany={handleSwitchCompany}
            onOpenCreateCompanyModal={() => setShowCreateCompanyModal(true)}
            onDeleteCompany={handleDeleteCompany}
            onImportAssets={handleImportAssets}
            onImportCapex={handleImportCapex}
            onAddManualAsset={handleAddManualAsset}
          />
        )}

        {activeTab === 'register' && (
          <AssetRegister
            assets={assets}
            currencyMode={currencyMode}
            onSelectAsset={setSelectedAssetForModal}
            openDemoShowcase={() => setShowDemoShowcase(true)}
          />
        )}

        {activeTab === 'capex-review' && (
          <AiCapitalisationReview
            capexQueue={capexQueue}
            setCapexQueue={setCapexQueue}
            currencyMode={currencyMode}
            onAddCapitalisedAsset={handleAddCapitalisedAsset}
          />
        )}

        {activeTab === 'physical-verification' && (
          <PhysicalVerification
            assets={assets}
            setAssets={setAssets}
            scanLogs={scanLogs}
            setScanLogs={setScanLogs}
            risks={risks}
            setRisks={setRisks}
            currencyMode={currencyMode}
            onNavigateToAsset={handleNavigateToAsset}
          />
        )}

        {activeTab === 'risk-radar' && (
          <RiskEngine
            risks={risks}
            setRisks={setRisks}
            currencyMode={currencyMode}
            onNavigateToAsset={handleNavigateToAsset}
            onNavigateToExceptions={handleNavigateToExceptions}
          />
        )}

        {activeTab === 'exceptions' && (
          <ExceptionsWorkflow
            risks={risks}
            setRisks={setRisks}
            currencyMode={currencyMode}
            onNavigateToAsset={handleNavigateToAsset}
            targetRiskId={targetRiskForWorkflow}
          />
        )}

        {activeTab === 'policy' && (
          <PolicyCompliance />
        )}

        {activeTab === 'audit-readiness' && (
          <AuditReadiness
            assets={assets}
            risks={risks}
            reliabilityScore={reliabilityScore}
            currencyMode={currencyMode}
          />
        )}

        {activeTab === 'user-manual' && (
          <UserManual
            onNavigateTab={setActiveTab}
            onOpenDemoSpotlight={() => setShowDemoShowcase(true)}
          />
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200 bg-white py-4 text-xs text-slate-500 shadow-2xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-2">
          <div className="flex items-center space-x-2">
            <span className="font-medium text-slate-600">
              {activeCompany.name} ({activeCompany.shortCode}) • AssetTrust AI™ Multi-Entity Subledger & Ingestion Platform
            </span>
          </div>
          <div className="flex items-center space-x-4">
            <button
              onClick={() => setActiveTab('data-studio')}
              className="text-purple-600 hover:text-purple-800 font-semibold"
            >
              Data Ingestion & PDF AI Studio
            </button>
            <span className="text-slate-300">|</span>
            <button
              onClick={() => setActiveTab('user-manual')}
              className="text-blue-600 hover:text-blue-800 font-semibold underline"
            >
              Operating Manual & FAQs
            </button>
            <span className="text-slate-300">|</span>
            <button
              onClick={() => setShowQuickTour(true)}
              className="text-slate-600 hover:text-slate-900 font-medium"
            >
              Interactive Quick Tour
            </button>
          </div>
        </div>
      </footer>

      {/* Create Company Modal */}
      <CompanyModal
        isOpen={showCreateCompanyModal}
        onClose={() => setShowCreateCompanyModal(false)}
        onCreateCompany={handleCreateCompany}
      />

      {/* Quick Start Guide Modal */}
      <QuickStartGuideModal
        isOpen={showQuickTour}
        onClose={() => setShowQuickTour(false)}
        onNavigateTab={setActiveTab}
        onOpenManual={() => {
          setShowQuickTour(false);
          setActiveTab('user-manual');
        }}
      />

      {/* 360-Degree Asset Dossier Modal */}
      {selectedAssetForModal && (
        <AssetDetailModal
          asset={selectedAssetForModal}
          onClose={() => setSelectedAssetForModal(null)}
          currencyMode={currencyMode}
          onNavigateToRisk={(assetId) => {
            setSelectedAssetForModal(null);
            const r = risks.find((rk) => rk.assetId === assetId);
            if (r) {
              handleNavigateToExceptions(r.id);
            } else {
              setActiveTab('risk-radar');
            }
          }}
        />
      )}

      {/* ₹48.5L CNC Machine Demo Spotlight Showcase Modal */}
      {demoCncAsset && (
        <DemoAssetShowcase
          asset={demoCncAsset}
          isOpen={showDemoShowcase}
          onClose={() => setShowDemoShowcase(false)}
          currencyMode={currencyMode}
          onOpenFullDossier={(ast) => {
            setShowDemoShowcase(false);
            setSelectedAssetForModal(ast);
          }}
        />
      )}
    </div>
  );
}

