import React from 'react';
import {
  LayoutDashboard,
  Package,
  CalendarDays,
  BookOpen,
  ShoppingBag,
  HeartPulse,
  Sun,
  Moon,
} from 'lucide-react';
import { Logo } from './Logo';

interface NavbarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  isDarkMode: boolean;
  setIsDarkMode: (val: boolean) => void;
  unreadAlertsCount?: number;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  isDarkMode,
  setIsDarkMode,
  unreadAlertsCount = 0,
}) => {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'inventory', label: 'Inventory', icon: Package },
    { id: 'mealplanner', label: 'Meal Planner', icon: CalendarDays },
    { id: 'recipes', label: 'Recipes', icon: BookOpen },
    { id: 'family_bmi', label: 'Health Goal', icon: HeartPulse },
    { id: 'grocery', label: 'Grocery List', icon: ShoppingBag },
  ];

  return (
    <header className="sticky top-0 z-40 backdrop-blur-md bg-white/60 dark:bg-slate-900/60 border-b border-white/80 dark:border-slate-800/80 transition-colors duration-300">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Branding */}
          <div className="flex items-center gap-3 cursor-pointer py-1" onClick={() => setActiveTab('dashboard')}>
            <Logo size="sm" showSubtitle={true} />
          </div>

          {/* Navigation Links */}
          <nav className="hidden md:flex items-center gap-1 bg-white/60 dark:bg-slate-800/60 p-1 rounded-2xl border border-slate-200/60 dark:border-slate-700/60">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`flex items-center gap-2 px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all duration-200 ${
                    isActive
                      ? 'bg-orange-500 text-white shadow-sm font-bold'
                      : 'text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-white/80 dark:hover:bg-slate-700/60'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {item.label}
                  {item.id === 'grocery' && unreadAlertsCount > 0 && (
                    <span className="w-2 h-2 rounded-full bg-rose-500 animate-pulse" />
                  )}
                </button>
              );
            })}
          </nav>

          {/* Right Actions: Theme Toggle */}
          <div className="flex items-center gap-3">
            {/* Dark Mode Toggle */}
            <button
              onClick={() => setIsDarkMode(!isDarkMode)}
              aria-label="Toggle theme"
              className="p-2.5 bg-white/80 dark:bg-slate-800/80 border border-slate-200/80 dark:border-slate-700/80 rounded-xl hover:bg-white dark:hover:bg-slate-700 transition-all text-slate-600 dark:text-slate-300 shadow-sm"
            >
              {isDarkMode ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-slate-700" />}
            </button>
          </div>
        </div>

        {/* Mobile Navigation Grid (2 rows of 3 buttons) */}
        <div className="md:hidden grid grid-cols-3 gap-2 py-2 border-t border-slate-200/40 dark:border-slate-800/40">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`relative flex flex-col items-center justify-center gap-1.5 px-1 py-2.5 rounded-xl text-center text-[10px] font-semibold transition-all duration-200 ${
                  isActive
                    ? 'bg-orange-500 text-white shadow-sm font-bold'
                    : 'bg-white/80 dark:bg-slate-800/80 text-slate-600 dark:text-slate-300 border border-slate-200/60 dark:border-slate-700/60'
                }`}
              >
                <Icon className="w-4 h-4" />
                <span className="truncate w-full leading-none">{item.label}</span>
                {item.id === 'grocery' && unreadAlertsCount > 0 && (
                  <span className="absolute top-1.5 right-4 w-2 h-2 rounded-full bg-rose-500 animate-pulse" />
                )}
              </button>
            );
          })}
        </div>
      </div>
    </header>
  );
};
