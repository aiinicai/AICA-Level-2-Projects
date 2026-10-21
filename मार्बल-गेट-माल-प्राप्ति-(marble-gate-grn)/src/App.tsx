import React, { useState, useEffect, useCallback } from 'react';
import { Header } from './components/Header';
import { LoginScreen } from './components/LoginScreen';
import { WorkerHome } from './components/WorkerHome';
import { GrnWizard } from './components/GrnForm/GrnWizard';
import { GrnReceipt } from './components/GrnReceipt';
import { GrnList } from './components/GrnList';
import { AdminDashboard } from './components/AdminDashboard';

import type { GoodsReceiptNote, FactorySettings, MasterData, UserAccount } from './types/grn';
import { useNetworkSync } from './hooks/useNetworkSync';
import { getLocalDraft, clearLocalDraft, cacheGrns, getCachedGrns } from './utils/offlineDb';

export default function App() {
  const [currentUser, setCurrentUser] = useState<UserAccount | null>(() => {
    try {
      const saved = localStorage.getItem('marble_gate_user');
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });

  const [users, setUsers] = useState<UserAccount[]>([
    { id: 'usr-1', name: 'रामेश्वर जाट (गेट ऑपरेटर)', role: 'worker', gateName: 'गेट नंबर 1 (मुख्य गेट)', pin: '1234' },
    { id: 'usr-2', name: 'सुरेश कुमावत (गेट ऑपरेटर)', role: 'worker', gateName: 'गेट नंबर 2 (ब्लॉक यार्ड)', pin: '5678' },
    { id: 'usr-3', name: 'मुकेश शर्मा (मालिक / एडमिन)', role: 'admin', gateName: 'मुख्यालय / ऑफिस', pin: '9999' }
  ]);

  const [settings, setSettings] = useState<FactorySettings>({
    factoryName: 'श्री बालाजी मार्बल एवं ग्रेनाइट इंडस्ट्रीज',
    factoryTagline: 'उच्च गुणवत्ता मार्बल, ग्रेनाइट एवं सैंडस्टोन ब्लॉक्स',
    factoryAddress: 'रीको इंडस्ट्रियल एरिया, फेज़-2, मकराना रोड, किशनगढ़ (राज.) 305801',
    factoryPhone: '+91 98290 12345 / 0145-265432',
    factoryGstin: '08AABCS1429B1ZX',
    receiptTitle: 'माल प्राप्ति रसीद (GOODS RECEIPT NOTE - GRN)',
    declarationText: 'प्रमाणित किया जाता है कि उपरोक्त सामग्री का गेट पर भौतिक निरीक्षण किया गया एवं विवरण अनुसार सही पाई गई।',
    defaultMeasurementUnit: 'इंच (Inches)',
    defaultWeightUnit: 'टन (Tonnes)',
    requireWeighbridge: true,
    requirePhotos: false,
    requireReceiverSignature: true,
    gates: ['गेट नंबर 1 (मुख्य गेट)', 'गेट नंबर 2 (ब्लॉक यार्ड)']
  });

  const [masters, setMasters] = useState<MasterData>({
    suppliers: [
      'मकराना मार्बल माइन्स प्राइवेट लिमिटेड',
      'अंबिका स्टोन सप्लायर्स, राजसमंद',
      'भवानी मार्बल एंड मिनरल्स, उदयपुर',
      'श्री राम ग्रेनाइट क्वेरीज़, जालौर',
      'गुजरात सैंडस्टोन ट्रेडिंग कॉर्पोरेशन'
    ],
    varieties: [
      'मकराना वाइट (Makrana White)',
      'राजनगर वाइट (Rajnagar White)',
      'अम्बाजी वाइट (Ambaji White)',
      'वियतनाम वाइट (Vietnam White)',
      'ग्रीन मार्बल (Green Marble)',
      'जालौर ब्लैक ग्रेनाइट (Black Granite)',
      'आर कट मार्बल ब्लॉक (R-Cut Block)',
      'सैंडस्टोन रफ ब्लॉक (Sandstone Rough)'
    ],
    frequentDrivers: [
      { name: 'रामनिवास गुर्जर', mobile: '9828112233', vehicle: 'RJ-01-GA-4589' },
      { name: 'बलवंत सिंह राठौड़', mobile: '9414223344', vehicle: 'RJ-14-GH-7812' }
    ],
    frequentVehicles: ['RJ-01-GA-4589', 'RJ-14-GH-7812', 'RJ-21-GB-3321']
  });

  const [grns, setGrns] = useState<GoodsReceiptNote[]>([]);
  const [selectedGrn, setSelectedGrn] = useState<GoodsReceiptNote | null>(null);

  // Draft state
  const [hasDraft, setHasDraft] = useState<boolean>(false);
  const [draftSavedAt, setDraftSavedAt] = useState<string | null>(null);
  const [initialDraftData, setInitialDraftData] = useState<any>(null);

  // Active view: 'home' | 'wizard' | 'list' | 'receipt' | 'admin'
  const [currentView, setCurrentView] = useState<'home' | 'wizard' | 'list' | 'receipt' | 'admin'>('home');

  // Network & Sync hook
  const handleSyncComplete = useCallback((count: number) => {
    if (count > 0) {
      fetchGrns();
    }
  }, []);

  const { isOnline, pendingSyncCount, isSyncing, syncNow, refreshPendingCount } = useNetworkSync(handleSyncComplete);

  // Check Draft in IndexedDB
  const checkDraft = useCallback(async () => {
    const draft = await getLocalDraft();
    if (draft && draft.data) {
      setHasDraft(true);
      setDraftSavedAt(draft.savedAt);
      setInitialDraftData(draft.data);
    } else {
      setHasDraft(false);
      setDraftSavedAt(null);
      setInitialDraftData(null);
    }
  }, []);

  // Fetch GRNs
  const fetchGrns = useCallback(async () => {
    try {
      if (navigator.onLine) {
        const res = await fetch('/api/grn');
        if (res.ok) {
          const data = await res.json();
          setGrns(data);
          await cacheGrns(data);
          return;
        }
      }
    } catch (err) {
      console.warn('Network fetch failed, falling back to cache:', err);
    }

    // Fallback to IndexedDB cache
    const cached = await getCachedGrns();
    if (cached.length > 0) {
      setGrns(cached);
    }
  }, []);

  // Fetch Settings & Masters
  useEffect(() => {
    const loadInitData = async () => {
      try {
        const [settingsRes, mastersRes, usersRes] = await Promise.all([
          fetch('/api/settings').then(r => r.ok ? r.json() : null),
          fetch('/api/masters').then(r => r.ok ? r.json() : null),
          fetch('/api/users').then(r => r.ok ? r.json() : null),
        ]);

        if (settingsRes) setSettings(settingsRes);
        if (mastersRes) setMasters(mastersRes);
        if (usersRes) setUsers(usersRes);
      } catch (err) {
        console.warn('Init data load error, using fallback defaults:', err);
      }

      await checkDraft();
      await fetchGrns();
    };

    loadInitData();
  }, [checkDraft, fetchGrns]);

  // Login handler
  const handleLoginSuccess = (user: UserAccount, token: string) => {
    setCurrentUser(user);
    try {
      localStorage.setItem('marble_gate_user', JSON.stringify(user));
      localStorage.setItem('marble_gate_token', token);
    } catch {}
    if (user.role === 'admin') {
      setCurrentView('admin');
    } else {
      setCurrentView('home');
    }
  };

  // Logout handler
  const handleLogout = () => {
    setCurrentUser(null);
    try {
      localStorage.removeItem('marble_gate_user');
      localStorage.removeItem('marble_gate_token');
    } catch {}
    setCurrentView('home');
  };

  // New GRN wizard trigger
  const handleStartNewGrn = () => {
    setInitialDraftData(null);
    setCurrentView('wizard');
  };

  // Resume Draft
  const handleResumeDraft = () => {
    setCurrentView('wizard');
  };

  // Discard Draft
  const handleDiscardDraft = async () => {
    if (confirm('क्या आप अधूरी रसीद (ड्राफ्ट) को हटाना चाहते हैं?')) {
      await clearLocalDraft();
      await checkDraft();
    }
  };

  // On GRN Created
  const handleGrnCreated = async (newGrn: GoodsReceiptNote) => {
    setGrns(prev => [newGrn, ...prev]);
    setSelectedGrn(newGrn);
    setCurrentView('receipt');
    await checkDraft();
    await refreshPendingCount();
  };

  // On Select GRN from list or admin
  const handleSelectGrn = (grn: GoodsReceiptNote) => {
    setSelectedGrn(grn);
    setCurrentView('receipt');
  };

  // Cancel Receipt (Admin action)
  const handleCancelReceipt = async (grnId: string, reason: string) => {
    try {
      const res = await fetch(`/api/grn/${grnId}/cancel`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          cancellationReason: reason,
          cancelledBy: currentUser?.name || 'मालिक'
        })
      });
      if (!res.ok) throw new Error('रसीद रद्द करने में त्रुटि');
      await fetchGrns();
      alert('रसीद सफलतापूर्वक रद्द कर दी गई है।');
    } catch (err: any) {
      alert(err.message || 'त्रुटि हुई');
    }
  };

  // Update Settings
  const handleUpdateSettings = async (newSettings: FactorySettings) => {
    const res = await fetch('/api/settings', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(newSettings)
    });
    if (!res.ok) throw new Error('सेटिंग्स सेव नहीं हो सकी');
    const updated = await res.json();
    setSettings(updated);
  };

  // Update Masters
  const handleUpdateMasters = async (newMasters: MasterData) => {
    const res = await fetch('/api/masters', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(newMasters)
    });
    if (!res.ok) throw new Error('मास्टर डेटा सेव नहीं हो सका');
    const updated = await res.json();
    setMasters(updated);
  };

  // Gate Worker metrics for today
  const todayStr = new Date().toISOString().split('T')[0];
  const todayGrns = grns.filter(g => g.date === todayStr && g.status !== 'रद्द');
  const todayBlocks = todayGrns.reduce((sum, g) => sum + (g.totalBlocks || 0), 0);

  // If user is not logged in, show clean authentication screen
  if (!currentUser) {
    return (
      <LoginScreen
        users={users}
        settings={settings}
        onLoginSuccess={handleLoginSuccess}
      />
    );
  }

  return (
    <div className="min-h-screen bg-slate-100 flex flex-col font-sans">
      
      {/* Global Header */}
      <Header
        currentUser={currentUser}
        settings={settings}
        isOnline={isOnline}
        pendingSyncCount={pendingSyncCount}
        isSyncing={isSyncing}
        onSyncNow={syncNow}
        onLogout={handleLogout}
        activeTab={currentView === 'admin' ? 'admin' : 'worker'}
        setActiveTab={(tab) => {
          if (tab === 'admin') setCurrentView('admin');
          else setCurrentView('home');
        }}
      />

      {/* Main Content Area */}
      <main className="flex-1 pb-16">
        
        {/* VIEW 1: WORKER HOME */}
        {currentView === 'home' && (
          <WorkerHome
            currentUser={currentUser}
            hasDraft={hasDraft}
            draftSavedAt={draftSavedAt}
            pendingSyncCount={pendingSyncCount}
            isOnline={isOnline}
            isSyncing={isSyncing}
            todayCount={todayGrns.length}
            todayBlocks={todayBlocks}
            onNewGrn={handleStartNewGrn}
            onViewOld={() => setCurrentView('list')}
            onResumeDraft={handleResumeDraft}
            onDiscardDraft={handleDiscardDraft}
            onSyncNow={syncNow}
          />
        )}

        {/* VIEW 2: GUIDED GRN WIZARD */}
        {currentView === 'wizard' && (
          <GrnWizard
            currentUser={currentUser}
            masters={masters}
            settings={settings}
            isOnline={isOnline}
            initialDraftData={initialDraftData}
            onGrnCreated={handleGrnCreated}
            onCancel={() => {
              checkDraft();
              setCurrentView('home');
            }}
          />
        )}

        {/* VIEW 3: GRN RECEIPT / PRINT VIEW */}
        {currentView === 'receipt' && selectedGrn && (
          <GrnReceipt
            grn={selectedGrn}
            settings={settings}
            currentUser={currentUser}
            onBack={() => {
              if (currentUser.role === 'admin') setCurrentView('admin');
              else setCurrentView('home');
            }}
          />
        )}

        {/* VIEW 4: SEARCH & LIST VIEW */}
        {currentView === 'list' && (
          <GrnList
            grns={grns}
            masters={masters}
            currentUser={currentUser}
            onSelectGrn={handleSelectGrn}
            onBack={() => setCurrentView('home')}
            onRefresh={fetchGrns}
            isSyncing={isSyncing}
          />
        )}

        {/* VIEW 5: OWNER / ADMIN DASHBOARD */}
        {currentView === 'admin' && (
          <AdminDashboard
            grns={grns}
            settings={settings}
            masters={masters}
            currentUser={currentUser}
            onUpdateSettings={handleUpdateSettings}
            onUpdateMasters={handleUpdateMasters}
            onCancelReceipt={handleCancelReceipt}
            onSelectGrn={handleSelectGrn}
            onRefresh={fetchGrns}
            isSyncing={isSyncing}
          />
        )}

      </main>

    </div>
  );
}
