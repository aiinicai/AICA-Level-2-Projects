import React, { useState } from 'react';
import {
  ListTodo,
  Search,
  BarChart2,
  X,
  ChevronRight,
  ExternalLink,
  Filter,
} from 'lucide-react';

export interface TaskItem {
  label: string;
  onClick: () => void;
  badge?: string | number;
}

interface RightRailProps {
  tasks: TaskItem[];
  onSearchSubmit?: (filters: Record<string, any>) => void;
  analyticsComponent?: React.ReactNode;
}

export const RightRail: React.FC<RightRailProps> = ({
  tasks,
  onSearchSubmit,
  analyticsComponent,
}) => {
  const [activePanel, setActivePanel] = useState<'tasks' | 'search' | 'analytics' | null>(null);

  const togglePanel = (panel: 'tasks' | 'search' | 'analytics') => {
    setActivePanel(activePanel === panel ? null : panel);
  };

  return (
    <div className="relative flex select-none no-print">
      {/* Expanded Drawer */}
      {activePanel && (
        <div className="fixed right-12 top-14 bottom-0 w-80 bg-white border-l border-gray-200 shadow-2xl z-30 p-4 flex flex-col animate-in slide-in-from-right duration-150">
          <div className="flex items-center justify-between pb-3 border-b border-gray-200 mb-4">
            <h3 className="font-bold text-sm text-[#3F1D5C] uppercase tracking-wider flex items-center space-x-1.5">
              {activePanel === 'tasks' && (
                <>
                  <ListTodo className="w-4 h-4 text-[#5B2C83]" />
                  <span>Tasks</span>
                </>
              )}
              {activePanel === 'search' && (
                <>
                  <Search className="w-4 h-4 text-[#5B2C83]" />
                  <span>Advanced Search</span>
                </>
              )}
              {activePanel === 'analytics' && (
                <>
                  <BarChart2 className="w-4 h-4 text-[#5B2C83]" />
                  <span>Reports & Analytics</span>
                </>
              )}
            </h3>
            <button
              onClick={() => setActivePanel(null)}
              className="p-1 rounded hover:bg-gray-100 text-gray-500"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto text-xs">
            {activePanel === 'tasks' && (
              <div className="space-y-1">
                {tasks.map((task, idx) => (
                  <button
                    key={idx}
                    onClick={() => {
                      task.onClick();
                      setActivePanel(null);
                    }}
                    className="w-full text-left p-2.5 rounded-lg hover:bg-plum-50 text-gray-700 hover:text-[#5B2C83] transition-colors flex items-center justify-between border border-transparent hover:border-plum-200 group"
                  >
                    <span className="font-medium group-hover:underline">{task.label}</span>
                    <div className="flex items-center space-x-1.5">
                      {task.badge && (
                        <span className="bg-amber-100 text-amber-800 text-[10px] font-bold px-1.5 py-0.5 rounded-full">
                          {task.badge}
                        </span>
                      )}
                      <ChevronRight className="w-3.5 h-3.5 text-gray-400 group-hover:text-[#5B2C83]" />
                    </div>
                  </button>
                ))}
              </div>
            )}

            {activePanel === 'search' && (
              <div className="space-y-3">
                <p className="text-gray-500 text-[11px]">
                  Filter transactions by document number, supplier/customer, date, or amount.
                </p>
                <div>
                  <label className="block text-gray-700 font-semibold mb-1">Document Number</label>
                  <input
                    type="text"
                    placeholder="e.g. PINV-2026-000001"
                    className="w-full p-2 border border-gray-300 rounded text-xs focus:ring-1 focus:ring-[#5B2C83] focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-gray-700 font-semibold mb-1">Business Unit</label>
                  <select className="w-full p-2 border border-gray-300 rounded text-xs focus:ring-1 focus:ring-[#5B2C83] focus:outline-none">
                    <option value="">All Business Units</option>
                    <option value="H01">H01 - Meridian Hospital Abu Dhabi</option>
                    <option value="H02">H02 - Meridian Hospital Dubai</option>
                    <option value="C01">C01 - Meridian Clinic Khalifa City</option>
                    <option value="P01">P01 - Meridian Pharmacy Corniche</option>
                  </select>
                </div>
                <div>
                  <label className="block text-gray-700 font-semibold mb-1">Status</label>
                  <select className="w-full p-2 border border-gray-300 rounded text-xs focus:ring-1 focus:ring-[#5B2C83] focus:outline-none">
                    <option value="">All Statuses</option>
                    <option value="Pending Approval">Pending Approval</option>
                    <option value="Approved">Approved</option>
                    <option value="Posted">Posted</option>
                    <option value="Draft">Draft</option>
                    <option value="Rejected">Rejected</option>
                  </select>
                </div>
                <div className="pt-2">
                  <button
                    onClick={() => setActivePanel(null)}
                    className="w-full py-2 bg-[#5B2C83] hover:bg-[#3F1D5C] text-white font-semibold rounded shadow-xs"
                  >
                    Search Records
                  </button>
                </div>
              </div>
            )}

            {activePanel === 'analytics' && (
              <div>
                {analyticsComponent || (
                  <div className="text-center py-6 text-gray-500">
                    <p className="text-xs">Module analytics and reporting graphs.</p>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Rail Icon Strip */}
      <div className="w-12 bg-gray-100 border-l border-gray-200 flex flex-col items-center py-4 space-y-4 shrink-0">
        <button
          onClick={() => togglePanel('tasks')}
          title="Tasks Panel"
          className={`p-2.5 rounded-lg transition-colors ${
            activePanel === 'tasks'
              ? 'bg-[#5B2C83] text-white shadow-md'
              : 'text-gray-600 hover:bg-plum-100 hover:text-[#5B2C83]'
          }`}
        >
          <ListTodo className="w-5 h-5" />
        </button>

        <button
          onClick={() => togglePanel('search')}
          title="Advanced Search"
          className={`p-2.5 rounded-lg transition-colors ${
            activePanel === 'search'
              ? 'bg-[#5B2C83] text-white shadow-md'
              : 'text-gray-600 hover:bg-plum-100 hover:text-[#5B2C83]'
          }`}
        >
          <Search className="w-5 h-5" />
        </button>

        <button
          onClick={() => togglePanel('analytics')}
          title="Reports and Analytics"
          className={`p-2.5 rounded-lg transition-colors ${
            activePanel === 'analytics'
              ? 'bg-[#5B2C83] text-white shadow-md'
              : 'text-gray-600 hover:bg-plum-100 hover:text-[#5B2C83]'
          }`}
        >
          <BarChart2 className="w-5 h-5" />
        </button>
      </div>
    </div>
  );
};
