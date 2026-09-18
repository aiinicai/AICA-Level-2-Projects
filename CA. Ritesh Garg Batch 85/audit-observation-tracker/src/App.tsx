import React, { useState, useEffect, useCallback } from 'react';
import { Navbar } from './components/layout/Navbar';
import { Sidebar, NavView } from './components/layout/Sidebar';
import { DashboardView } from './components/dashboard/DashboardView';
import { EngagementList } from './components/engagements/EngagementList';
import { EngagementFormModal } from './components/engagements/EngagementFormModal';
import { EngagementDetailModal } from './components/engagements/EngagementDetailModal';
import { ObservationList } from './components/observations/ObservationList';
import { ObservationFormModal } from './components/observations/ObservationFormModal';
import { ObservationDetailModal } from './components/observations/ObservationDetailModal';
import { ChecklistsView } from './components/checklists/ChecklistsView';
import { ReportsView } from './components/reports/ReportsView';
import { SettingsView } from './components/settings/SettingsView';

import { 
  Engagement, 
  Observation, 
  AuditType, 
  AuditChecklistItem,
  FirmProfile, 
  ObservationStatus, 
  SeverityLevel 
} from './types/audit';
import { storageService, DEFAULT_FIRM_PROFILE } from './services/apiStorage';

export default function App() {
  // Navigation
  const [currentView, setCurrentView] = useState<NavView>('dashboard');

  // Core Data
  const [engagements, setEngagements] = useState<Engagement[]>([]);
  const [observations, setObservations] = useState<Observation[]>([]);
  const [auditTypes, setAuditTypes] = useState<AuditType[]>([]);
  const [checklistItems, setChecklistItems] = useState<AuditChecklistItem[]>([]);
  const [firmProfile, setFirmProfile] = useState<FirmProfile>(DEFAULT_FIRM_PROFILE);

  // Quick Filter passthrough for Observation register
  const [observationFilters, setObservationFilters] = useState<any>(null);

  // Engagement Modals
  const [isEngagementFormOpen, setIsEngagementFormOpen] = useState(false);
  const [engagementToEdit, setEngagementToEdit] = useState<Engagement | null>(null);
  const [isEngagementDetailOpen, setIsEngagementDetailOpen] = useState(false);
  const [selectedEngagement, setSelectedEngagement] = useState<Engagement | null>(null);

  // Observation Modals
  const [isObservationFormOpen, setIsObservationFormOpen] = useState(false);
  const [observationToEdit, setObservationToEdit] = useState<Observation | null>(null);
  const [isObservationDetailOpen, setIsObservationDetailOpen] = useState(false);
  const [selectedObservation, setSelectedObservation] = useState<Observation | null>(null);
  const [preselectedEngagementIdForObs, setPreselectedEngagementIdForObs] = useState<string | undefined>(undefined);

  // Reload data from storage
  const reloadData = useCallback(async () => {
    try {
      const [engs, obs, types, items, profile] = await Promise.all([
        storageService.getEngagements(),
        storageService.getObservations(),
        storageService.getAuditTypes(),
        storageService.getChecklistItems(),
        storageService.getFirmProfile(),
      ]);
      setEngagements(engs || []);
      setObservations(obs || []);
      setAuditTypes(types || []);
      setChecklistItems(items || []);
      if (profile) setFirmProfile(profile);
    } catch (err) {
      console.error('Failed to load data from server:', err);
    }
  }, []);

  useEffect(() => {
    reloadData();
  }, [reloadData]);

  // Engagement Handlers
  const handleOpenNewEngagement = () => {
    setEngagementToEdit(null);
    setIsEngagementFormOpen(true);
  };

  const handleEditEngagement = (eng: Engagement) => {
    setEngagementToEdit(eng);
    setIsEngagementFormOpen(true);
  };

  const handleViewEngagement = (eng: Engagement) => {
    setSelectedEngagement(eng);
    setIsEngagementDetailOpen(true);
  };

  const handleSaveEngagement = async (engData: Partial<Engagement> & { clientName: string; auditTypeId: string; financialYear: string }) => {
    await storageService.saveEngagement(engData);
    await reloadData();
  };

  const handleDeleteEngagement = async (engId: string) => {
    await storageService.deleteEngagement(engId);
    await reloadData();
  };

  const handleImportEngagements = async (newEngagements: Engagement[]) => {
    await storageService.bulkAddEngagements(newEngagements);
    await reloadData();
  };

  // Observation Handlers
  const handleOpenNewObservation = (preselectedEngId?: string) => {
    setObservationToEdit(null);
    setPreselectedEngagementIdForObs(preselectedEngId);
    setIsObservationFormOpen(true);
  };

  const handleEditObservation = (obs: Observation) => {
    setObservationToEdit(obs);
    setIsObservationFormOpen(true);
  };

  const handleViewObservation = (obs: Observation) => {
    setSelectedObservation(obs);
    setIsObservationDetailOpen(true);
  };

  const handleSaveObservation = async (obsData: Partial<Observation> & { engagementId: string; description: string; severity: SeverityLevel; status: ObservationStatus }) => {
    await storageService.saveObservation(obsData);
    await reloadData();
  };

  const handleDeleteObservation = async (obsId: string) => {
    await storageService.deleteObservation(obsId);
    await reloadData();
  };

  const handleQuickUpdateStatus = async (obsId: string, newStatus: ObservationStatus) => {
    await storageService.updateObservationStatus(obsId, newStatus);
    await reloadData();
  };

  // Checklist Handlers
  const handleSaveChecklistItem = async (itemData: Partial<AuditChecklistItem> & { checkPoint: string; auditTypeId: string }) => {
    await storageService.saveChecklistItem(itemData);
    await reloadData();
  };

  const handleDeleteChecklistItem = async (id: string) => {
    await storageService.deleteChecklistItem(id);
    await reloadData();
  };

  const handleImportChecklistItems = async (items: AuditChecklistItem[], replace: boolean) => {
    await storageService.bulkSaveChecklistItems(items, replace);
    await reloadData();
  };

  // Audit Type Handlers
  const handleSaveAuditType = async (typeData: Partial<AuditType> & { name: string; code: string }) => {
    await storageService.saveAuditType(typeData);
    await reloadData();
  };

  const handleDeleteAuditType = async (id: string) => {
    await storageService.deleteAuditType(id);
    await reloadData();
  };

  // Firm Profile Handlers
  const handleSaveFirmProfile = async (profile: FirmProfile) => {
    await storageService.saveFirmProfile(profile);
    await reloadData();
  };

  // Backup & Reset Handlers
  const handleExportJsonBackup = async () => {
    const data = await storageService.exportAllDataJson();
    const blob = new Blob([data], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `CA_Audit_Tracker_Backup_${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleImportJsonBackup = async (jsonStr: string): Promise<boolean> => {
    const success = await storageService.importDataJson(jsonStr);
    if (success) {
      await reloadData();
    }
    return success;
  };

  const handleResetSampleData = async () => {
    await storageService.resetToSampleData();
    await reloadData();
  };

  const handleClearClientData = async () => {
    await storageService.clearAllClientData();
    await reloadData();
  };

  // Dashboard Drilldown Helper
  const handleDashboardDrilldown = (filterOptions: any) => {
    setObservationFilters(filterOptions);
    setCurrentView('observations');
  };

  return (
    <div id="audit-app-root" className="min-h-screen bg-[#F5F5F0] flex flex-col antialiased text-stone-800 font-sans">
      {/* Top Navbar */}
      <Navbar
        firmProfile={firmProfile}
        engagements={engagements}
        observations={observations}
        currentView={currentView}
        onNavigate={(view) => {
          setObservationFilters(null);
          setCurrentView(view);
        }}
        onOpenNewEngagement={handleOpenNewEngagement}
        onOpenNewObservation={() => handleOpenNewObservation()}
      />

      {/* Main Layout Container */}
      <div className="flex-1 flex max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 gap-6">
        {/* Sidebar */}
        <Sidebar
          currentView={currentView}
          onNavigate={(view) => {
            setObservationFilters(null);
            setCurrentView(view);
          }}
          engagementsCount={engagements.length}
          observationsCount={observations.length}
          auditTypesCount={auditTypes.length}
          checklistItemsCount={checklistItems.length}
          openObservationsCount={observations.filter(o => o.status !== 'Closed' && o.status !== 'Rectified').length}
          partnerName={firmProfile?.partnerName || 'CA Ritesh Garg, FCA'}
        />

        {/* Dynamic Main Content View */}
        <main className="flex-1 min-w-0">
          {currentView === 'dashboard' && (
            <DashboardView
              engagements={engagements}
              observations={observations}
              auditTypes={auditTypes}
              firmProfile={firmProfile}
              onNavigate={(view) => {
                setObservationFilters(null);
                setCurrentView(view);
              }}
              onNavigateToObservations={handleDashboardDrilldown}
              onNavigateToEngagements={() => {
                setObservationFilters(null);
                setCurrentView('engagements');
              }}
              onOpenNewEngagement={handleOpenNewEngagement}
              onOpenNewObservation={() => handleOpenNewObservation()}
              onViewObservation={handleViewObservation}
              onEditObservation={handleEditObservation}
              onViewEngagement={handleViewEngagement}
              onQuickUpdateStatus={handleQuickUpdateStatus}
              onFilterObservations={handleDashboardDrilldown}
            />
          )}

          {currentView === 'engagements' && (
            <EngagementList
              engagements={engagements}
              observations={observations}
              auditTypes={auditTypes}
              firmProfile={firmProfile}
              onOpenNewEngagement={handleOpenNewEngagement}
              onViewEngagement={handleViewEngagement}
              onEditEngagement={handleEditEngagement}
              onDeleteEngagement={handleDeleteEngagement}
              onAddObservationForEngagement={(engId) => handleOpenNewObservation(engId)}
              onImportEngagements={handleImportEngagements}
            />
          )}

          {currentView === 'observations' && (
            <ObservationList
              observations={observations}
              engagements={engagements}
              auditTypes={auditTypes}
              firmProfile={firmProfile}
              initialFilters={observationFilters}
              onOpenNewObservation={() => handleOpenNewObservation()}
              onViewObservation={handleViewObservation}
              onEditObservation={handleEditObservation}
              onDeleteObservation={handleDeleteObservation}
              onQuickUpdateStatus={handleQuickUpdateStatus}
            />
          )}

          {currentView === 'checklists' && (
            <ChecklistsView
              auditTypes={auditTypes}
              checklistItems={checklistItems}
              firmProfile={firmProfile}
              onSaveChecklistItem={handleSaveChecklistItem}
              onDeleteChecklistItem={handleDeleteChecklistItem}
              onImportChecklistItems={handleImportChecklistItems}
            />
          )}

          {currentView === 'reports' && (
            <ReportsView
              engagements={engagements}
              observations={observations}
              auditTypes={auditTypes}
              firmProfile={firmProfile}
            />
          )}

          {currentView === 'settings' && (
            <SettingsView
              auditTypes={auditTypes}
              firmProfile={firmProfile}
              onSaveAuditType={handleSaveAuditType}
              onDeleteAuditType={handleDeleteAuditType}
              onSaveFirmProfile={handleSaveFirmProfile}
              onExportJsonBackup={handleExportJsonBackup}
              onImportJsonBackup={handleImportJsonBackup}
              onResetSampleData={handleResetSampleData}
              onClearClientData={handleClearClientData}
            />
          )}
        </main>
      </div>

      {/* MODALS */}
      {/* 1. Engagement Create/Edit Modal */}
      <EngagementFormModal
        isOpen={isEngagementFormOpen}
        onClose={() => setIsEngagementFormOpen(false)}
        onSave={handleSaveEngagement}
        engagementToEdit={engagementToEdit}
        auditTypes={auditTypes}
      />

      {/* 2. Engagement Detail Modal */}
      <EngagementDetailModal
        isOpen={isEngagementDetailOpen}
        onClose={() => setIsEngagementDetailOpen(false)}
        engagement={selectedEngagement}
        observations={observations.filter(o => o.engagementId === selectedEngagement?.id)}
        auditType={selectedEngagement ? auditTypes.find(at => at.id === selectedEngagement.auditTypeId) : undefined}
        firmProfile={firmProfile}
        onEditEngagement={handleEditEngagement}
        onAddObservation={(engId) => handleOpenNewObservation(engId)}
        onViewObservation={handleViewObservation}
        onEditObservation={handleEditObservation}
        onDeleteObservation={handleDeleteObservation}
      />

      {/* 3. Observation Create/Edit Modal */}
      <ObservationFormModal
        isOpen={isObservationFormOpen}
        onClose={() => setIsObservationFormOpen(false)}
        onSave={handleSaveObservation}
        observationToEdit={observationToEdit}
        engagements={engagements}
        auditTypes={auditTypes}
        preselectedEngagementId={preselectedEngagementIdForObs}
      />

      {/* 4. Observation Detail / Letterhead Modal */}
      <ObservationDetailModal
        isOpen={isObservationDetailOpen}
        onClose={() => setIsObservationDetailOpen(false)}
        observation={selectedObservation}
        engagement={selectedObservation ? engagements.find(e => e.id === selectedObservation.engagementId) : undefined}
        auditType={
          selectedObservation
            ? auditTypes.find(at => at.id === (engagements.find(e => e.id === selectedObservation.engagementId)?.auditTypeId))
            : undefined
        }
        firmProfile={firmProfile}
        onEditObservation={handleEditObservation}
        onQuickUpdateStatus={handleQuickUpdateStatus}
      />
    </div>
  );
}
