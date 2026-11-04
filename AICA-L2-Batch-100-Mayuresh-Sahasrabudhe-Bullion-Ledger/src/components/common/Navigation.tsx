import React from 'react';
import {
  LayoutDashboard,
  ReceiptText,
  Boxes,
  LineChart,
  Settings,
  ShieldCheck,
  Coins,
} from 'lucide-react';

export type NavTab = 'dashboard' | 'purchases' | 'holdings' | 'prices' | 'settings' | 'diagnostics';

interface NavigationProps {
  activeTab: NavTab;
  onTabChange: (tab: NavTab) => void;
  purchasesCount: number;
  ratesCount: number;
}

export const Navigation: React.FC<NavigationProps> = ({
  activeTab,
  onTabChange,
  purchasesCount,
  ratesCount,
}) => {
  const navItems = [
    {
      id: 'dashboard' as NavTab,
      label: 'Dashboard',
      icon: LayoutDashboard,
      description: 'Portfolio overview & charts',
    },
    {
      id: 'purchases' as NavTab,
      label: 'Purchases',
      icon: ReceiptText,
      badge: purchasesCount > 0 ? purchasesCount : undefined,
      description: 'Transaction log & invoices',
    },
    {
      id: 'holdings' as NavTab,
      label: 'Holding Details',
      icon: Boxes,
      description: 'Individual lots & XIRR',
    },
    {
      id: 'prices' as NavTab,
      label: 'Price History',
      icon: LineChart,
      badge: ratesCount > 0 ? `${(ratesCount / 1000).toFixed(1)}k` : undefined,
      description: 'Historical rates & provenance',
    },
    {
      id: 'settings' as NavTab,
      label: 'Settings & Backup',
      icon: Settings,
      description: 'Markdowns, sync & export',
    },
    {
      id: 'diagnostics' as NavTab,
      label: 'Verification Suite',
      icon: ShieldCheck,
      description: '10 acceptance test checks',
    },
  ];

  return (
    <>
      {/* Desktop & Tablet Sidebar */}
      <aside className="hidden md:flex flex-col w-64 shrink-0 bg-white border-r border-[#E7E2DA] min-h-[calc(100vh-61px)] p-4 justify-between">
        <div className="space-y-6">
          <div className="px-2">
            <span className="text-[11px] font-bold uppercase tracking-wider text-stone-500">
              Portfolio Navigation
            </span>
          </div>

          <nav className="space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => onTabChange(item.id)}
                  className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-xs font-medium transition-colors text-left ${
                    isActive
                      ? 'bg-[#FBF6E9] text-[#B88B2A] font-semibold border-l-4 border-[#B88B2A]'
                      : 'text-stone-600 hover:bg-stone-50 hover:text-stone-900'
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <Icon
                      className={`w-4 h-4 shrink-0 ${
                        isActive ? 'text-[#B88B2A]' : 'text-stone-500'
                      }`}
                    />
                    <span>{item.label}</span>
                  </div>
                  {item.badge !== undefined && (
                    <span
                      className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${
                        isActive
                          ? 'bg-[#B88B2A] text-white'
                          : 'bg-stone-100 text-stone-600 border border-stone-200'
                      }`}
                    >
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>
        </div>

        {/* Sidebar Footer Info */}
        <div className="bg-[#FAF7F2] p-3 rounded-lg border border-[#E7E2DA] text-[11px] space-y-1.5">
          <div className="flex items-center justify-between font-medium text-stone-700">
            <span className="flex items-center gap-1">
              <Coins className="w-3.5 h-3.5 text-[#B88B2A]" />
              Data Persistence
            </span>
            <span className="text-emerald-700 font-semibold">Local IndexedDB</span>
          </div>
          <p className="text-stone-500 text-[10px] leading-tight">
            All purchases & 5,666 rates stored safely offline in your browser.
          </p>
        </div>
      </aside>

      {/* Mobile Sticky Bottom Navigation */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 z-40 bg-white border-t border-[#E7E2DA] px-2 py-1 flex justify-around items-center shadow-lg">
        {navItems.slice(0, 5).map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => onTabChange(item.id)}
              className={`flex flex-col items-center justify-center py-1 px-2 rounded min-w-[58px] transition-colors ${
                isActive ? 'text-[#B88B2A]' : 'text-stone-500 hover:text-stone-800'
              }`}
            >
              <div className="relative">
                <Icon className={`w-5 h-5 ${isActive ? 'stroke-[2.5]' : 'stroke-2'}`} />
                {item.badge !== undefined && (
                  <span className="absolute -top-1 -right-2 text-[9px] bg-[#B88B2A] text-white font-bold rounded-full px-1 min-w-[14px] text-center">
                    {item.badge}
                  </span>
                )}
              </div>
              <span className={`text-[10px] mt-0.5 ${isActive ? 'font-bold' : 'font-normal'}`}>
                {item.id === 'holdings'
                  ? 'Holdings'
                  : item.id === 'settings'
                  ? 'Settings'
                  : item.id === 'prices'
                  ? 'Rates'
                  : item.label}
              </span>
            </button>
          );
        })}
      </nav>
    </>
  );
};
