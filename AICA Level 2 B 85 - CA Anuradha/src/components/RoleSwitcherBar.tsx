import React from 'react';
import { useApp } from '../context/AppContext';
import { Role, Department } from '../types';
import { Shield, UserCheck, Users, Briefcase, Building, Server, IndianRupee, Eye } from 'lucide-react';

export const RoleSwitcherBar: React.FC = () => {
  const { currentUser, setCurrentUser, users, activeMonth } = useApp();

  const getDeptIcon = (dept?: Department) => {
    switch (dept) {
      case 'HR':
        return <Users className="w-3.5 h-3.5" />;
      case 'Admin':
        return <Building className="w-3.5 h-3.5" />;
      case 'IT':
        return <Server className="w-3.5 h-3.5" />;
      case 'Finance':
        return <IndianRupee className="w-3.5 h-3.5" />;
      default:
        return null;
    }
  };

  const getRoleBadgeStyle = (role: Role) => {
    switch (role) {
      case 'department_submitter':
        return 'bg-blue-50 text-blue-700 border-blue-200';
      case 'finance_controller':
        return 'bg-amber-50 text-amber-800 border-amber-200';
      case 'management':
        return 'bg-emerald-50 text-emerald-800 border-emerald-200';
      case 'admin':
        return 'bg-slate-100 text-slate-800 border-slate-300';
    }
  };

  return (
    <div id="role-switcher-bar" className="bg-[#0F172A] text-slate-200 px-4 sm:px-6 py-2 border-b border-slate-800 text-xs flex flex-wrap items-center justify-between gap-3 sticky top-0 z-50 shadow-md">
      <div className="flex items-center gap-2.5">
        <span className="flex items-center gap-1.5 font-bold text-slate-400 uppercase tracking-widest text-[10px]">
          <UserCheck className="w-3.5 h-3.5 text-blue-400" />
          Active Persona:
        </span>
        <div className="flex items-center gap-2 bg-slate-800/90 px-2.5 py-1 rounded-lg border border-slate-700/80 shadow-xs">
          <img
            src={currentUser.avatar || 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=100&auto=format&fit=crop&q=80'}
            alt={currentUser.name}
            className="w-5 h-5 rounded-full object-cover border border-slate-600"
          />
          <span className="font-bold text-white text-xs">{currentUser.name}</span>
          <span className="text-slate-400 text-[11px] hidden sm:inline">
            ({currentUser.title})
          </span>
          <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border ${getRoleBadgeStyle(currentUser.role)}`}>
            {currentUser.role === 'department_submitter'
              ? `${currentUser.department} Lead`
              : currentUser.role === 'finance_controller'
              ? 'Controller'
              : currentUser.role === 'management'
              ? 'Management'
              : 'Admin'}
          </span>
        </div>
      </div>

      <div className="flex items-center gap-1.5 overflow-x-auto py-0.5 max-w-full">
        <span className="text-slate-400 text-[10px] font-bold uppercase tracking-wider mr-1 hidden lg:inline">Switch Role:</span>
        {users.map((u) => {
          const isActive = u.id === currentUser.id;
          return (
            <button
              key={u.id}
              id={`switch-to-${u.id}`}
              onClick={() => setCurrentUser(u)}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg transition-all font-semibold whitespace-nowrap text-[11px] ${
                isActive
                  ? 'bg-blue-600 text-white shadow-sm ring-1 ring-blue-400 font-bold'
                  : 'bg-slate-800/90 text-slate-300 hover:bg-slate-700 hover:text-white border border-slate-700/70'
              }`}
              title={`Switch to ${u.name} (${u.title})`}
            >
              {u.department ? getDeptIcon(u.department) : u.role === 'finance_controller' ? <Briefcase className="w-3.5 h-3.5 text-blue-400" /> : u.role === 'management' ? <Eye className="w-3.5 h-3.5 text-emerald-400" /> : <Shield className="w-3.5 h-3.5 text-amber-400" />}
              <span>{u.department ? `${u.department} Head` : u.role === 'finance_controller' ? 'Controller' : u.role === 'management' ? 'Management' : 'Admin'}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
};
