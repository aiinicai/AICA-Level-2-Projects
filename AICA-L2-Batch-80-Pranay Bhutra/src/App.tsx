import React, { useState, useEffect } from 'react';
import {
  Package,
  Truck,
  BarChart3,
  Bell,
  Palette,
  Smartphone,
  ShieldCheck,
  Plus,
  RefreshCw,
  Search,
  Building2,
  UserCheck,
  Sparkles,
  Info
} from 'lucide-react';
import {
  InwardShipment,
  OutwardShipment,
  UserProfile,
  ThemeStyle,
  IconConcept
} from './types';
import { ParcelStorageService } from './services/storage';
import { THEMES } from './utils/theme';
import { Navbar } from './components/Navbar';
import { TrackingLookup } from './components/TrackingLookup';
import { InwardRegister } from './components/InwardRegister';
import { OutwardRegister } from './components/OutwardRegister';
import { AnalyticsReports } from './components/AnalyticsReports';
import { NotificationCenter } from './components/NotificationCenter';
import { ThemeSelectorModal } from './components/ThemeSelectorModal';
import { NewInwardModal } from './components/NewInwardModal';
import { NewOutwardModal } from './components/NewOutwardModal';
import { ProofOfDeliveryModal } from './components/ProofOfDeliveryModal';
import { UpdateStatusModal } from './components/UpdateStatusModal';
import { ShipmentDetailModal } from './components/ShipmentDetailModal';
import { PWAInstallBanner } from './components/PWAInstallBanner';
import { UserGuideModal } from './components/UserGuideModal';
import { AuthModal } from './components/AuthModal';
import { EditProfileModal } from './components/EditProfileModal';

export default function App() {
  const [currentUser, setCurrentUser] = useState<UserProfile>(ParcelStorageService.getCurrentUser());
  const [currentTheme, setCurrentTheme] = useState<ThemeStyle>(ParcelStorageService.getTheme());
  const [currentIcon, setCurrentIcon] = useState<IconConcept>(ParcelStorageService.getIconConcept());

  const [inwardList, setInwardList] = useState<InwardShipment[]>(ParcelStorageService.getInwardShipments());
  const [outwardList, setOutwardList] = useState<OutwardShipment[]>(ParcelStorageService.getOutwardShipments());

  const [activeTab, setActiveTab] = useState<'inward' | 'outward' | 'analytics' | 'notifications'>('inward');

  // Modals
  const [isThemeModalOpen, setIsThemeModalOpen] = useState(false);
  const [isGuideModalOpen, setIsGuideModalOpen] = useState(false);
  const [isPWAModalOpen, setIsPWAModalOpen] = useState(false);
  const [isNewInwardOpen, setIsNewInwardOpen] = useState(false);
  const [isNewOutwardOpen, setIsNewOutwardOpen] = useState(false);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [authModalMode, setAuthModalMode] = useState<'login' | 'signup' | 'change_password'>('login');
  const [isEditProfileOpen, setIsEditProfileOpen] = useState(false);

  // Detail & Action Modals
  const [selectedShipment, setSelectedShipment] = useState<InwardShipment | OutwardShipment | null>(null);
  const [selectedShipmentType, setSelectedShipmentType] = useState<'inward' | 'outward'>('inward');
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);
  const [isPODModalOpen, setIsPODModalOpen] = useState(false);
  const [isUpdateStatusOpen, setIsUpdateStatusOpen] = useState(false);

  // Sync Listeners
  useEffect(() => {
    const handleInward = (e: any) => setInwardList(e.detail || []);
    const handleOutward = (e: any) => setOutwardList(e.detail || []);
    const handleUser = (e: any) => setCurrentUser(e.detail);
    const handleLogout = () => {
      setAuthModalMode('login');
      setIsAuthModalOpen(true);
    };
    const handleTheme = (e: any) => setCurrentTheme(e.detail);
    const handleIcon = (e: any) => setCurrentIcon(e.detail);

    window.addEventListener('inward_updated', handleInward);
    window.addEventListener('outward_updated', handleOutward);
    window.addEventListener('user_changed', handleUser);
    window.addEventListener('user_logged_out', handleLogout);
    window.addEventListener('theme_changed', handleTheme);
    window.addEventListener('icon_changed', handleIcon);

    return () => {
      window.removeEventListener('inward_updated', handleInward);
      window.removeEventListener('outward_updated', handleOutward);
      window.removeEventListener('user_changed', handleUser);
      window.removeEventListener('user_logged_out', handleLogout);
      window.removeEventListener('theme_changed', handleTheme);
      window.removeEventListener('icon_changed', handleIcon);
    };
  }, []);

  // Sync body styles with active theme
  useEffect(() => {
    const theme = THEMES[currentTheme] || THEMES.navy;
    document.body.style.backgroundColor = theme.pageStyle.backgroundColor as string;
    const metaTheme = document.getElementById('meta-theme-color');
    if (metaTheme) {
      metaTheme.setAttribute('content', theme.pageStyle.backgroundColor as string);
    }
  }, [currentTheme]);

  const handleSelectTheme = (theme: ThemeStyle) => {
    setCurrentTheme(theme);
    ParcelStorageService.setTheme(theme);
  };

  const handleSelectIcon = (icon: IconConcept) => {
    setCurrentIcon(icon);
    ParcelStorageService.setIconConcept(icon);
  };

  const handleRefreshData = () => {
    setInwardList(ParcelStorageService.getInwardShipments());
    setOutwardList(ParcelStorageService.getOutwardShipments());
  };

  const handleOpenDetail = (shipment: InwardShipment | OutwardShipment, type: 'inward' | 'outward') => {
    setSelectedShipment(shipment);
    setSelectedShipmentType(type);
    setIsDetailModalOpen(true);
  };

  const handleOpenPOD = (shipment: InwardShipment | OutwardShipment, type: 'inward' | 'outward') => {
    setSelectedShipment(shipment);
    setSelectedShipmentType(type);
    setIsPODModalOpen(true);
  };

  const handleOpenUpdateStatus = (shipment: InwardShipment | OutwardShipment, type: 'inward' | 'outward') => {
    setSelectedShipment(shipment);
    setSelectedShipmentType(type);
    setIsUpdateStatusOpen(true);
  };

  const handleNavigateFromNotification = (referenceNumber: string, trackingNumber: string, type: 'inward' | 'outward') => {
    setActiveTab(type);
    const list = type === 'inward' ? inwardList : outwardList;
    const found = list.find(
      (item) =>
        (referenceNumber && item.referenceNumber.toLowerCase() === referenceNumber.toLowerCase()) ||
        (trackingNumber && item.trackingNumber.toLowerCase() === trackingNumber.toLowerCase())
    );
    if (found) {
      handleOpenDetail(found, type);
    }
  };

  const themeConfig = THEMES[currentTheme] || THEMES.navy;

  return (
    <div
      className={`min-h-screen ${themeConfig.pageBg} ${themeConfig.textPrimary} font-sans flex flex-col transition-colors duration-300`}
      style={{
        backgroundColor: themeConfig.pageStyle.backgroundColor,
        backgroundImage: themeConfig.pageStyle.backgroundImage
      }}
    >
      {/* Top Navbar */}
      <Navbar
        currentUser={currentUser}
        onChangeUser={(user) => {
          setCurrentUser(user);
          ParcelStorageService.setCurrentUser(user);
        }}
        currentTheme={currentTheme}
        currentIcon={currentIcon}
        onOpenThemeModal={() => setIsThemeModalOpen(true)}
        onOpenGuideModal={() => setIsGuideModalOpen(true)}
        onOpenNewInward={() => setIsNewInwardOpen(true)}
        onOpenNewOutward={() => setIsNewOutwardOpen(true)}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onOpenPWAModal={() => setIsPWAModalOpen(true)}
        onNavigateToShipment={handleNavigateFromNotification}
        onOpenAuthModal={(mode) => {
          setAuthModalMode(mode);
          setIsAuthModalOpen(true);
        }}
        onOpenEditProfile={() => setIsEditProfileOpen(true)}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* On-The-Fly Theme & Role Prompt Banner */}
        <div className={`flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3.5 rounded-xl ${themeConfig.cardBg} border ${themeConfig.cardBorder} text-xs backdrop-blur-md shadow-sm transition-colors duration-300`}>
          <div className="flex items-center gap-2.5">
            <span className="flex h-2 w-2 rounded-full bg-emerald-500 animate-ping" />
            <span className={`font-semibold ${themeConfig.textPrimary}`}>
              Active Persona: <span className={themeConfig.textAccent}>{currentUser?.name || 'Authorized Staff'}</span> ({currentUser?.designation || 'Chartered Accountancy Desk'})
            </span>
            <span className={`${themeConfig.textMuted} hidden md:inline`}>•</span>
            <span className={`${themeConfig.textMuted} hidden md:inline`}>
              Active Theme: <span className="text-amber-500 font-semibold">{themeConfig.name}</span>
            </span>
          </div>

          <div className="flex items-center flex-wrap gap-2">
            <button
              onClick={() => setIsEditProfileOpen(true)}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg ${themeConfig.badgeBg} ${themeConfig.badgeText} border ${themeConfig.borderAccent} font-semibold hover:brightness-105 transition-all`}
            >
              <UserCheck className="w-3.5 h-3.5" />
              <span>Edit Profile</span>
            </button>

            <button
              onClick={() => {
                setAuthModalMode('login');
                setIsAuthModalOpen(true);
              }}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg ${themeConfig.secondaryBtn} font-medium transition-colors`}
            >
              <span>Sign In / Switch</span>
            </button>

            <button
              onClick={() => setIsThemeModalOpen(true)}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg ${themeConfig.secondaryBtn} font-medium transition-colors`}
            >
              <Palette className="w-3.5 h-3.5 text-amber-500" />
              <span>Theme & Icon</span>
            </button>

            <button
              onClick={() => setIsPWAModalOpen(true)}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg ${themeConfig.badgeBg} ${themeConfig.badgeText} border ${themeConfig.borderAccent} font-semibold hover:brightness-105 transition-all`}
              title="Install Mobile & Desktop PWA Application"
            >
              <Smartphone className="w-3.5 h-3.5" />
              <span>Install PWA</span>
            </button>

            <button
              onClick={() => {
                ParcelStorageService.resetToDefault();
                handleRefreshData();
              }}
              className={`p-1 rounded-lg ${themeConfig.secondaryBtn} transition-colors`}
              title="Reset All Default App Data"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* 1. Real-Time Tracking Reference & Docket Tracker */}
        <TrackingLookup
          currentUser={currentUser}
          currentTheme={currentTheme}
          onOpenShipmentDetail={handleOpenDetail}
          onOpenUpdateStatus={handleOpenUpdateStatus}
          onOpenPODModal={handleOpenPOD}
        />

        {/* 2. Primary Tab Views */}
        {activeTab === 'inward' && (
          <InwardRegister
            inwardList={inwardList}
            currentUser={currentUser}
            currentTheme={currentTheme}
            onOpenNewInward={() => setIsNewInwardOpen(true)}
            onOpenShipmentDetail={(shipment) => handleOpenDetail(shipment, 'inward')}
            onOpenPODModal={(shipment) => handleOpenPOD(shipment, 'inward')}
            onOpenUpdateStatus={(shipment) => handleOpenUpdateStatus(shipment, 'inward')}
          />
        )}

        {activeTab === 'outward' && (
          <OutwardRegister
            outwardList={outwardList}
            currentUser={currentUser}
            currentTheme={currentTheme}
            onOpenNewOutward={() => setIsNewOutwardOpen(true)}
            onOpenShipmentDetail={(shipment) => handleOpenDetail(shipment, 'outward')}
            onOpenPODModal={(shipment) => handleOpenPOD(shipment, 'outward')}
            onOpenUpdateStatus={(shipment) => handleOpenUpdateStatus(shipment, 'outward')}
          />
        )}

        {activeTab === 'analytics' && (
          <AnalyticsReports
            inwardList={inwardList}
            outwardList={outwardList}
            currentTheme={currentTheme}
          />
        )}

        {activeTab === 'notifications' && (
          <NotificationCenter
            currentUser={currentUser}
            currentTheme={currentTheme}
            onNavigateToShipment={handleNavigateFromNotification}
          />
        )}
      </main>

      {/* Footer */}
      <footer className={`border-t ${themeConfig.cardBorder} ${themeConfig.cardBg} py-4 mt-12 text-center text-xs ${themeConfig.textMuted} transition-colors duration-300`}>
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className={`font-semibold ${themeConfig.textPrimary}`}>ParcelDesk</span>
            <span>•</span>
            <button
              onClick={() => setIsGuideModalOpen(true)}
              className="text-emerald-600 dark:text-emerald-400 hover:underline font-medium cursor-pointer transition-colors"
            >
              How to Use App Guide & Tutorials
            </button>
          </div>
          <div className={`flex items-center gap-3 font-mono text-[11px] ${themeConfig.textMuted}`}>
            <span>Client Cost Recovery</span>
            <span>•</span>
            <span>Scanned Proof of Delivery</span>
            <span>•</span>
            <span>Audit Trail Logs</span>
          </div>
        </div>
      </footer>

      {/* Modals */}
      <UserGuideModal
        isOpen={isGuideModalOpen}
        onClose={() => setIsGuideModalOpen(false)}
      />

      <ThemeSelectorModal
        isOpen={isThemeModalOpen}
        onClose={() => setIsThemeModalOpen(false)}
        currentTheme={currentTheme}
        onSelectTheme={handleSelectTheme}
        currentIcon={currentIcon}
        onSelectIcon={handleSelectIcon}
      />

      <PWAInstallBanner
        isOpen={isPWAModalOpen}
        onClose={() => setIsPWAModalOpen(false)}
        currentTheme={currentTheme}
        currentIcon={currentIcon}
      />

      <NewInwardModal
        isOpen={isNewInwardOpen}
        onClose={() => setIsNewInwardOpen(false)}
        currentUser={currentUser}
        onSuccess={handleRefreshData}
      />

      <NewOutwardModal
        isOpen={isNewOutwardOpen}
        onClose={() => setIsNewOutwardOpen(false)}
        currentUser={currentUser}
        onSuccess={handleRefreshData}
      />

      <ProofOfDeliveryModal
        isOpen={isPODModalOpen}
        onClose={() => setIsPODModalOpen(false)}
        shipment={selectedShipment}
        type={selectedShipmentType}
        currentUser={currentUser}
        onSuccess={handleRefreshData}
      />

      <UpdateStatusModal
        isOpen={isUpdateStatusOpen}
        onClose={() => setIsUpdateStatusOpen(false)}
        shipment={selectedShipment}
        type={selectedShipmentType}
        currentUser={currentUser}
        onSuccess={handleRefreshData}
      />

      <ShipmentDetailModal
        isOpen={isDetailModalOpen}
        onClose={() => setIsDetailModalOpen(false)}
        shipment={selectedShipment}
        type={selectedShipmentType}
        currentUser={currentUser}
        onOpenPODModal={() => {
          if (selectedShipment) handleOpenPOD(selectedShipment, selectedShipmentType);
        }}
        onOpenUpdateStatus={() => {
          if (selectedShipment) handleOpenUpdateStatus(selectedShipment, selectedShipmentType);
        }}
      />

      {/* Authentication & User Registration Modal */}
      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
        onSuccess={(user) => {
          setCurrentUser(user);
          ParcelStorageService.setCurrentUser(user);
          setIsAuthModalOpen(false);
        }}
        currentTheme={currentTheme}
        initialMode={authModalMode}
      />

      {/* Edit Profile & Role Permissions Modal */}
      <EditProfileModal
        isOpen={isEditProfileOpen}
        onClose={() => setIsEditProfileOpen(false)}
        currentUser={currentUser}
        onSuccess={(updated) => {
          setCurrentUser(updated);
          handleRefreshData();
        }}
        currentTheme={currentTheme}
      />
    </div>
  );
}
