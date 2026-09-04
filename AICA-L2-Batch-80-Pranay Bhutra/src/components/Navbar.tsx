import React, { useState, useEffect, useRef } from 'react';
import {
  Bell,
  Palette,
  Plus,
  Package,
  Truck,
  BarChart3,
  BookOpen,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  MessageSquare,
  Mail,
  Check,
  LogIn,
  UserPlus,
  LogOut,
  UserCheck,
  Shield,
  KeyRound,
  Copy,
  Edit3,
  Trash2,
  UserCog,
  Sparkles,
  Smartphone,
  Download
} from 'lucide-react';
import { UserProfile, UserRole, ThemeStyle, IconConcept, NotificationLog } from '../types';
import { AppLogo } from './AppLogo';
import { THEMES } from '../utils/theme';
import { ParcelStorageService } from '../services/storage';

interface NavbarProps {
  currentUser: UserProfile;
  onChangeUser: (user: UserProfile) => void;
  currentTheme: ThemeStyle;
  currentIcon: IconConcept;
  onOpenThemeModal: () => void;
  onOpenGuideModal: () => void;
  onOpenNewInward: () => void;
  onOpenNewOutward: () => void;
  activeTab: 'inward' | 'outward' | 'analytics' | 'notifications';
  setActiveTab: (tab: 'inward' | 'outward' | 'analytics' | 'notifications') => void;
  onOpenPWAModal: () => void;
  onNavigateToShipment?: (referenceNumber: string, trackingNumber: string, type: 'inward' | 'outward') => void;
  onOpenAuthModal?: (mode: 'login' | 'signup' | 'change_password') => void;
  onOpenEditProfile?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  currentUser,
  onChangeUser,
  currentTheme,
  currentIcon,
  onOpenThemeModal,
  onOpenGuideModal,
  onOpenNewInward,
  onOpenNewOutward,
  activeTab,
  setActiveTab,
  onOpenPWAModal,
  onNavigateToShipment,
  onOpenAuthModal,
  onOpenEditProfile,
}) => {
  const [allUsers, setAllUsers] = useState<UserProfile[]>([]);
  const [notifications, setNotifications] = useState<NotificationLog[]>([]);
  const [showRoleDropdown, setShowRoleDropdown] = useState(false);
  const [showNotificationDropdown, setShowNotificationDropdown] = useState(false);
  const notifRef = useRef<HTMLDivElement>(null);
  const roleRef = useRef<HTMLDivElement>(null);

  const activeOrg = ParcelStorageService.getOrganizationById(currentUser?.organizationId);
  const [copiedCode, setCopiedCode] = useState(false);

  useEffect(() => {
    setNotifications(ParcelStorageService.getNotifications(currentUser?.organizationId));
    setAllUsers(ParcelStorageService.getOrganizationUsers(currentUser?.organizationId));

    const handleNotifs = (e: any) => setNotifications(e.detail || []);
    const handleUsers = (e: any) => {
      setAllUsers(ParcelStorageService.getOrganizationUsers(currentUser?.organizationId));
    };
    window.addEventListener('notifications_updated', handleNotifs);
    window.addEventListener('users_list_updated', handleUsers);
    return () => {
      window.removeEventListener('notifications_updated', handleNotifs);
      window.removeEventListener('users_list_updated', handleUsers);
    };
  }, [currentUser?.organizationId]);

  // Close dropdowns on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) {
        setShowNotificationDropdown(false);
      }
      if (roleRef.current && !roleRef.current.contains(e.target as Node)) {
        setShowRoleDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const themeConfig = THEMES[currentTheme] || THEMES.navy;
  const unreadCount = notifications.filter((n) => n.status !== 'Read').length;

  const getRoleBadge = (role: UserRole) => {
    switch (role) {
      case 'admin_partner':
        return { label: 'Partner / Admin', bg: 'bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20' };
      case 'front_desk':
        return { label: 'Front Desk / Dispatch', bg: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20' };
      default:
        return { label: 'Audit / Tax Staff', bg: `${themeConfig.badgeBg} ${themeConfig.badgeText}` };
    }
  };

  const handleNotificationClick = (notif: NotificationLog) => {
    ParcelStorageService.markNotificationAsRead(notif.id);
    setShowNotificationDropdown(false);

    if (onNavigateToShipment) {
      const isOutward =
        notif.type === 'Outward Dispatched' ||
        notif.referenceNumber.startsWith('OUT-') ||
        notif.type.includes('Dispatched');
      const targetType = isOutward ? 'outward' : 'inward';
      onNavigateToShipment(notif.referenceNumber, notif.trackingNumber, targetType);
    } else {
      setActiveTab('notifications');
    }
  };

  const handleMarkAllRead = () => {
    ParcelStorageService.markAllNotificationsAsRead();
  };

  return (
    <header
      className={`sticky top-0 z-40 ${themeConfig.headerBg} backdrop-blur-md border-b ${themeConfig.cardBorder} shadow-md pt-[max(env(safe-area-inset-top,0px),8px)] transition-colors duration-300`}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 sm:h-18">
          {/* Brand Logo & Name */}
          <div className="flex items-center gap-6">
            <AppLogo concept={currentIcon} themeStyle={currentTheme} size="md" showText={true} />

            {/* Desktop Navigation Tabs */}
            <nav className={`hidden md:flex items-center gap-1.5 p-1 rounded-xl ${themeConfig.subCardBg} border ${themeConfig.cardBorder}`}>
              <button
                onClick={() => setActiveTab('inward')}
                className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  activeTab === 'inward'
                    ? `${themeConfig.activeTab}`
                    : `${themeConfig.textMuted} hover:${themeConfig.textPrimary} hover:bg-slate-500/10`
                }`}
              >
                <Package className="w-3.5 h-3.5" />
                <span>Inward Register</span>
              </button>

              <button
                onClick={() => setActiveTab('outward')}
                className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  activeTab === 'outward'
                    ? `${themeConfig.activeTab}`
                    : `${themeConfig.textMuted} hover:${themeConfig.textPrimary} hover:bg-slate-500/10`
                }`}
              >
                <Truck className="w-3.5 h-3.5" />
                <span>Outward Dispatch</span>
              </button>

              <button
                onClick={() => setActiveTab('analytics')}
                className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  activeTab === 'analytics'
                    ? `${themeConfig.activeTab}`
                    : `${themeConfig.textMuted} hover:${themeConfig.textPrimary} hover:bg-slate-500/10`
                }`}
              >
                <BarChart3 className="w-3.5 h-3.5" />
                <span>Analytics & Audit</span>
              </button>

              <button
                onClick={() => setActiveTab('notifications')}
                className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  activeTab === 'notifications'
                    ? `${themeConfig.activeTab}`
                    : `${themeConfig.textMuted} hover:${themeConfig.textPrimary} hover:bg-slate-500/10`
                }`}
              >
                <Bell className="w-3.5 h-3.5" />
                <span>Notifications</span>
                {unreadCount > 0 && (
                  <span className="ml-0.5 px-1.5 py-0.2 rounded-full bg-red-500 text-[10px] font-bold text-white leading-tight">
                    {unreadCount}
                  </span>
                )}
              </button>
            </nav>
          </div>

          {/* Desktop & Mobile Right Actions (Compact & Responsive) */}
          <div className="flex items-center gap-1 sm:gap-2.5 shrink-0">
            {/* Quick Create Buttons for Desk/Partner */}
            {(currentUser.role === 'admin_partner' || currentUser.role === 'front_desk') && (
              <div className="hidden lg:flex items-center gap-2">
                <button
                  onClick={onOpenNewInward}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-md shadow-emerald-950/20 transition-all active:scale-95"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Log Inward</span>
                </button>

                <button
                  onClick={onOpenNewOutward}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl ${themeConfig.primaryBtn} text-xs font-semibold shadow-md transition-all active:scale-95`}
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>New Outbound</span>
                </button>
              </div>
            )}

            {/* SOP Guide */}
            <button
              onClick={onOpenGuideModal}
              className={`flex items-center gap-1.5 p-2 sm:px-2.5 sm:py-1.5 rounded-xl ${themeConfig.secondaryBtn} text-xs font-medium transition-colors`}
              title="Standard Operating Procedures"
            >
              <BookOpen className={`w-3.5 h-3.5 ${themeConfig.textAccent}`} />
              <span className="hidden xl:inline">SOP Guide</span>
            </button>

            {/* Theme & Icon Selector */}
            <button
              onClick={onOpenThemeModal}
              className={`flex items-center gap-1.5 p-2 sm:px-2.5 sm:py-1.5 rounded-xl ${themeConfig.secondaryBtn} text-xs font-medium transition-colors`}
              title="Full Color Schemes & Icon Selector"
            >
              <Palette className="w-3.5 h-3.5 text-amber-500" />
              <span className="hidden sm:inline">Theme</span>
            </button>

            {/* Install PWA Button */}
            <button
              onClick={onOpenPWAModal}
              className={`flex items-center gap-1.5 p-2 sm:px-2.5 sm:py-1.5 rounded-xl ${themeConfig.badgeBg} ${themeConfig.badgeText} border ${themeConfig.borderAccent} text-xs font-semibold hover:brightness-110 transition-all shadow-sm active:scale-95`}
              title="Install Mobile & Desktop PWA Application"
            >
              <Smartphone className="w-3.5 h-3.5" />
              <span className="hidden md:inline">Install PWA</span>
            </button>

            {/* Interactive Notification Bell Dropdown */}
            <div className="relative" ref={notifRef}>
              <button
                onClick={() => setShowNotificationDropdown(!showNotificationDropdown)}
                className={`relative p-2 rounded-xl border transition-colors ${
                  showNotificationDropdown || activeTab === 'notifications'
                    ? `${themeConfig.badgeBg} ${themeConfig.badgeText} ${themeConfig.borderAccent}`
                    : `${themeConfig.secondaryBtn}`
                }`}
                title="Stakeholder Notifications & Activity Alerts"
              >
                <Bell className="w-4 h-4" />
                {unreadCount > 0 ? (
                  <span className="absolute -top-1 -right-1 flex h-4 min-w-[16px] px-1 items-center justify-center rounded-full bg-red-500 text-[9px] font-bold text-white shadow-md animate-pulse">
                    {unreadCount}
                  </span>
                ) : notifications.length > 0 ? (
                  <span className={`absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full bg-blue-500`} />
                ) : null}
              </button>

              {/* Notification Popover Menu (Fixed on Mobile, Anchored on Desktop) */}
              {showNotificationDropdown && (
                <div className={`fixed left-3 right-3 top-16 sm:absolute sm:left-auto sm:right-0 sm:top-auto sm:mt-2 sm:w-96 rounded-2xl ${themeConfig.cardBg} border ${themeConfig.cardBorder} shadow-2xl p-3 z-50 animate-in fade-in zoom-in-95 backdrop-blur-xl`}>
                  <div className={`flex items-center justify-between pb-2 mb-2 border-b ${themeConfig.cardBorder}`}>
                    <div className="flex items-center gap-2">
                      <Bell className={`w-4 h-4 ${themeConfig.textAccent}`} />
                      <span className={`text-xs font-bold ${themeConfig.textPrimary}`}>Live Activity Alerts</span>
                      {unreadCount > 0 && (
                        <span className="px-1.5 py-0.5 rounded-full bg-red-500/10 border border-red-500/30 text-[10px] font-bold text-red-500">
                          {unreadCount} new
                        </span>
                      )}
                    </div>

                    <button
                      onClick={handleMarkAllRead}
                      className={`text-[11px] ${themeConfig.textAccent} hover:underline font-medium transition-colors`}
                    >
                      Mark all as read
                    </button>
                  </div>

                  <div className="max-h-72 overflow-y-auto space-y-1.5 pr-1 divide-y divide-slate-200 dark:divide-slate-800">
                    {notifications.length === 0 ? (
                      <div className={`py-6 text-center ${themeConfig.textMuted} text-xs`}>
                        No notifications logged yet.
                      </div>
                    ) : (
                      notifications.slice(0, 6).map((notif) => {
                        const isUnread = notif.status !== 'Read';
                        return (
                          <div
                            key={notif.id}
                            onClick={() => handleNotificationClick(notif)}
                            className={`pt-1.5 p-2 rounded-xl text-left cursor-pointer transition-all ${
                              isUnread
                                ? `${themeConfig.subCardBg} border ${themeConfig.cardBorder}`
                                : `${themeConfig.cardHover}`
                            }`}
                          >
                            <div className="flex items-start justify-between gap-2">
                              <div className="flex items-center gap-1.5">
                                <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                                  notif.type.includes('Urgent')
                                    ? 'bg-red-500/15 text-red-500'
                                    : notif.type.includes('Inward')
                                    ? 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'
                                    : `${themeConfig.badgeBg} ${themeConfig.badgeText}`
                                }`}>
                                  {notif.type}
                                </span>
                                <span className={`text-[10px] font-mono ${themeConfig.textMuted}`}>
                                  {notif.referenceNumber}
                                </span>
                              </div>
                              <span className={`text-[9px] ${themeConfig.textMuted} shrink-0`}>
                                {notif.timestamp.split(' ')[0]}
                              </span>
                            </div>

                            <p className={`text-xs ${themeConfig.textSecondary} mt-1 line-clamp-2 leading-relaxed`}>
                              {notif.message}
                            </p>

                            <div className={`flex items-center justify-between mt-1 text-[10px] ${themeConfig.textMuted}`}>
                              <span>For: <strong className={themeConfig.textPrimary}>{notif.recipient}</strong></span>
                              <span className={`${themeConfig.textAccent} hover:underline flex items-center gap-0.5 font-medium`}>
                                View Activity &rarr;
                              </span>
                            </div>
                          </div>
                        );
                      })
                    )}
                  </div>

                  <div className={`pt-2 mt-2 border-t ${themeConfig.cardBorder} flex items-center justify-between`}>
                    <button
                      onClick={() => {
                        setActiveTab('notifications');
                        setShowNotificationDropdown(false);
                      }}
                      className={`w-full py-1.5 rounded-lg ${themeConfig.secondaryBtn} text-xs font-semibold text-center`}
                    >
                      View All in Full Notification Center &rarr;
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Account Box & Dropdown (No Chevron, Clickable Whole Box) */}
            <div className="relative shrink-0" ref={roleRef}>
              <button
                type="button"
                onClick={() => setShowRoleDropdown(!showRoleDropdown)}
                className={`flex items-center gap-1.5 sm:gap-2 p-1.5 sm:pl-2 sm:pr-3 rounded-xl ${themeConfig.subCardBg} border ${themeConfig.cardBorder} hover:brightness-105 transition-all text-left cursor-pointer active:scale-95 shadow-sm`}
                title="Account & Staff Role Switcher"
              >
                <div className={`w-7 h-7 sm:w-7 sm:h-7 rounded-lg bg-gradient-to-tr ${themeConfig.accentGlow} flex items-center justify-center text-white text-xs font-bold shadow-sm shrink-0`}>
                  {currentUser?.name?.charAt(0) || 'U'}
                </div>
                <div className="hidden md:block">
                  <span className={`block text-xs font-semibold ${themeConfig.textPrimary} truncate max-w-[110px]`}>
                    {currentUser?.name || 'Staff User'}
                  </span>
                  <span className={`block text-[10px] ${themeConfig.textMuted}`}>
                    {currentUser?.role ? getRoleBadge(currentUser.role).label : 'Staff'}
                  </span>
                </div>
              </button>

              {/* Role & Auth Dropdown (Fixed on Mobile, Anchored on Desktop) */}
              {showRoleDropdown && (
                <div className={`fixed left-3 right-3 top-16 sm:absolute sm:left-auto sm:right-0 sm:top-auto sm:mt-2 sm:w-80 rounded-2xl ${themeConfig.cardBg} border ${themeConfig.cardBorder} shadow-2xl p-2.5 z-50 animate-in fade-in zoom-in-95 backdrop-blur-xl`}>
                    {/* Current Active Account Header */}
                  <div className={`p-2.5 rounded-xl ${themeConfig.subCardBg} border ${themeConfig.cardBorder} mb-2`}>
                    <div className="flex items-center justify-between">
                      <span className={`text-[10px] uppercase font-bold tracking-wider ${themeConfig.textMuted}`}>
                        {currentUser?.firmName || activeOrg?.name || 'Active Firm'}
                      </span>
                      <span className={`text-[9px] px-1.5 py-0.5 rounded border uppercase font-mono font-bold ${currentUser?.role ? getRoleBadge(currentUser.role).bg : ''}`}>
                        {currentUser?.role === 'admin_partner' ? 'Partner' : currentUser?.role === 'front_desk' ? 'Front Desk' : 'Audit Staff'}
                      </span>
                    </div>
                    <div className="mt-1">
                      <span className={`block text-xs font-bold ${themeConfig.textPrimary}`}>
                        {currentUser?.name || 'Staff User'}
                      </span>
                      <span className={`block text-[11px] ${themeConfig.textSecondary}`}>
                        {currentUser?.department || 'Audit & Assurance'} &bull; {currentUser?.designation || 'Staff'}
                      </span>
                      <span className={`block text-[10px] font-mono ${themeConfig.textMuted} mt-0.5`}>
                        {currentUser?.email || ''}
                      </span>
                    </div>

                    {/* Edit Profile Button directly in Header */}
                    <div className="mt-2 pt-2 border-t border-slate-500/20 flex items-center gap-1.5">
                      <button
                        type="button"
                        onClick={() => {
                          setShowRoleDropdown(false);
                          if (onOpenEditProfile) onOpenEditProfile();
                        }}
                        className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 px-2 rounded-lg text-xs font-semibold ${themeConfig.badgeBg} ${themeConfig.badgeText} border ${themeConfig.borderAccent} hover:opacity-90 transition-all`}
                      >
                        <Edit3 className="w-3.5 h-3.5" />
                        <span>Edit Profile & Permissions</span>
                      </button>
                    </div>

                    {/* Firm Workspace Code Display & Copy */}
                    {activeOrg?.code && (
                      <div className="mt-2 pt-2 border-t border-slate-500/20 flex items-center justify-between">
                        <div>
                          <span className={`text-[9px] uppercase font-semibold ${themeConfig.textMuted} block`}>
                            Firm Invite Code
                          </span>
                          <span className="text-xs font-mono font-bold text-amber-500">
                            {activeOrg.code}
                          </span>
                        </div>
                        <button
                          type="button"
                          onClick={() => {
                            navigator.clipboard.writeText(activeOrg.code);
                            setCopiedCode(true);
                            setTimeout(() => setCopiedCode(false), 2000);
                          }}
                          className={`px-2 py-1 rounded-lg text-[10px] font-semibold border transition-all flex items-center gap-1 ${
                            copiedCode
                              ? 'bg-emerald-500/20 text-emerald-500 border-emerald-500/40'
                              : `${themeConfig.badgeBg} ${themeConfig.badgeText} border ${themeConfig.borderAccent}`
                          }`}
                        >
                          {copiedCode ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                          <span>{copiedCode ? 'Copied' : 'Copy'}</span>
                        </button>
                      </div>
                    )}
                  </div>

                  {/* Switch Staff Persona List */}
                  <div className="px-1 py-1">
                    <span className={`text-[10px] uppercase font-bold ${themeConfig.textMuted} tracking-wider block mb-1.5`}>
                      Switch Staff Persona (RBAC)
                    </span>
                    <div className="space-y-1 max-h-48 overflow-y-auto pr-0.5">
                      {allUsers.map((user) => {
                        const isCurrent = user.id === currentUser.id;
                        return (
                          <button
                            key={user.id}
                            onClick={() => {
                              onChangeUser(user);
                              setShowRoleDropdown(false);
                            }}
                            className={`w-full text-left p-2 rounded-xl text-xs transition-colors flex items-center justify-between ${
                              isCurrent
                                ? `${themeConfig.badgeBg} ${themeConfig.badgeText} font-semibold border ${themeConfig.borderAccent}`
                                : `${themeConfig.textSecondary} ${themeConfig.cardHover}`
                            }`}
                          >
                            <div className="truncate pr-2">
                              <span className="block font-medium truncate">{user.name}</span>
                              <span className={`block text-[10px] ${themeConfig.textMuted} truncate`}>
                                {user.designation}
                              </span>
                            </div>
                            <span
                              className={`text-[9px] px-1.5 py-0.5 rounded border uppercase font-mono shrink-0 ${
                                getRoleBadge(user.role).bg
                              }`}
                            >
                              {user.role === 'admin_partner' ? 'Partner' : user.role === 'front_desk' ? 'Desk' : 'Staff'}
                            </span>
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* Auth & Testing Actions (Edit Profile / Clear / Login / Signup / Password / Logout) */}
                  <div className={`mt-2 pt-2 border-t ${themeConfig.cardBorder} space-y-1`}>
                    <button
                      onClick={() => {
                        setShowRoleDropdown(false);
                        if (onOpenEditProfile) onOpenEditProfile();
                      }}
                      className={`w-full flex items-center gap-2 p-2 rounded-xl text-xs font-semibold ${themeConfig.textPrimary} ${themeConfig.cardHover} transition-colors text-left`}
                    >
                      <UserCog className={`w-3.5 h-3.5 ${themeConfig.textAccent}`} />
                      <span>Edit My Profile & Permissions</span>
                    </button>

                    <button
                      onClick={() => {
                        setShowRoleDropdown(false);
                        onOpenPWAModal();
                      }}
                      className={`w-full flex items-center gap-2 p-2 rounded-xl text-xs font-semibold ${themeConfig.textPrimary} ${themeConfig.cardHover} transition-colors text-left`}
                    >
                      <Smartphone className={`w-3.5 h-3.5 ${themeConfig.textAccent}`} />
                      <span>Install PWA (iOS / Android / Desktop)</span>
                    </button>

                    <button
                      onClick={() => {
                        setShowRoleDropdown(false);
                        if (onOpenAuthModal) onOpenAuthModal('signup');
                      }}
                      className={`w-full flex items-center gap-2 p-2 rounded-xl text-xs font-semibold ${themeConfig.textPrimary} ${themeConfig.cardHover} transition-colors text-left`}
                    >
                      <UserPlus className={`w-3.5 h-3.5 ${themeConfig.textAccent}`} />
                      <span>Register New Staff Account</span>
                    </button>

                    <button
                      onClick={() => {
                        setShowRoleDropdown(false);
                        if (onOpenAuthModal) onOpenAuthModal('change_password');
                      }}
                      className={`w-full flex items-center gap-2 p-2 rounded-xl text-xs font-semibold ${themeConfig.textPrimary} ${themeConfig.cardHover} transition-colors text-left`}
                    >
                      <KeyRound className="w-3.5 h-3.5 text-amber-500" />
                      <span>Change Password / PIN</span>
                    </button>

                    <button
                      onClick={() => {
                        setShowRoleDropdown(false);
                        if (onOpenAuthModal) onOpenAuthModal('login');
                      }}
                      className={`w-full flex items-center gap-2 p-2 rounded-xl text-xs font-semibold ${themeConfig.textPrimary} ${themeConfig.cardHover} transition-colors text-left`}
                    >
                      <LogIn className="w-3.5 h-3.5 text-blue-500" />
                      <span>Sign In / Switch Workstation</span>
                    </button>

                    <button
                      onClick={() => {
                        setShowRoleDropdown(false);
                        ParcelStorageService.logoutUser();
                        if (onOpenAuthModal) onOpenAuthModal('login');
                      }}
                      className="w-full flex items-center gap-2 p-2 rounded-xl text-xs font-semibold text-red-500 hover:bg-red-500/10 transition-colors text-left"
                    >
                      <LogOut className="w-3.5 h-3.5 text-red-500" />
                      <span>Sign Out</span>
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Mobile Quick Action Buttons (Top Priority) */}
        {(currentUser.role === 'admin_partner' || currentUser.role === 'front_desk') && (
          <div className={`flex md:hidden items-center gap-2 pt-1 pb-2 border-t ${themeConfig.cardBorder}`}>
            <button
              onClick={onOpenNewInward}
              className="flex-1 flex items-center justify-center gap-1.5 py-2 px-3 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold shadow-md shadow-emerald-950/20 active:scale-95 transition-all"
            >
              <Plus className="w-4 h-4" />
              <span>Log Inward</span>
            </button>

            <button
              onClick={onOpenNewOutward}
              className={`flex-1 flex items-center justify-center gap-1.5 py-2 px-3 rounded-xl ${themeConfig.primaryBtn} text-xs font-bold shadow-md active:scale-95 transition-all`}
            >
              <Plus className="w-4 h-4" />
              <span>New Outbound</span>
            </button>
          </div>
        )}

        {/* Mobile Navigation Tabs */}
        <div className={`flex md:hidden items-center justify-between py-2 border-t ${themeConfig.cardBorder} gap-1`}>
          <button
            onClick={() => setActiveTab('inward')}
            className={`flex-1 py-1.5 rounded-lg text-[11px] font-semibold text-center transition-all ${
              activeTab === 'inward' ? `${themeConfig.activeTab}` : `${themeConfig.textMuted} ${themeConfig.subCardBg}`
            }`}
          >
            Inward Log
          </button>
          <button
            onClick={() => setActiveTab('outward')}
            className={`flex-1 py-1.5 rounded-lg text-[11px] font-semibold text-center transition-all ${
              activeTab === 'outward' ? `${themeConfig.activeTab}` : `${themeConfig.textMuted} ${themeConfig.subCardBg}`
            }`}
          >
            Outward Dispatch
          </button>
          <button
            onClick={() => setActiveTab('analytics')}
            className={`flex-1 py-1.5 rounded-lg text-[11px] font-semibold text-center transition-all ${
              activeTab === 'analytics' ? `${themeConfig.activeTab}` : `${themeConfig.textMuted} ${themeConfig.subCardBg}`
            }`}
          >
            Reports
          </button>
          <button
            onClick={() => setActiveTab('notifications')}
            className={`flex-1 py-1.5 rounded-lg text-[11px] font-semibold text-center transition-all ${
              activeTab === 'notifications' ? `${themeConfig.activeTab}` : `${themeConfig.textMuted} ${themeConfig.subCardBg}`
            }`}
          >
            Alerts {unreadCount > 0 ? `(${unreadCount})` : ''}
          </button>
        </div>
      </div>
    </header>
  );
};
