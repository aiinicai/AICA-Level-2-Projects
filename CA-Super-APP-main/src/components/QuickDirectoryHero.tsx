import React, { useState } from 'react';
import { useApp } from '../context/AppContext';
import { GOV_PORTALS } from '../data/statutoryData';
import { 
  Building2, 
  CheckSquare, 
  Calendar as CalendarIcon, 
  Globe, 
  KeyRound, 
  FileSpreadsheet, 
  Sprout, 
  Wrench, 
  ExternalLink, 
  ArrowDown, 
  Sparkles, 
  Search, 
  Clock, 
  ShieldCheck, 
  Flame,
  Layers,
  ArrowRight
} from 'lucide-react';

export const QuickDirectoryHero: React.FC = () => {
  const { auth, tasks, calendarEvents } = useApp();
  const [searchTerm, setSearchTerm] = useState('');

  const scrollToSection = (id: string) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  const pendingTasks = tasks.filter(t => !t.completed).length;
  const urgentTasks = tasks.filter(t => t.isUrgent && !t.completed).length;

  const quickJumpCards = [
    {
      id: 'tasks',
      title: 'To-Do Tasks & Weekly Schedule',
      desc: 'Staff weekly chart, tick-to-truncate completion, urgent flags & attachments',
      icon: CheckSquare,
      gradient: 'from-emerald-500 to-teal-600',
      badge: `${pendingTasks} Pending`,
      badgeColor: 'bg-emerald-100 text-emerald-800'
    },
    {
      id: 'calendar',
      title: 'Statutory Calendar & Punjab Festivals',
      desc: auth.role === 'admin' ? '15-Day Admin compliance outlook, GST/ITR due dates & Lohri/Baisakhi' : '7-Day Staff compliance outlook, GST/ITR due dates & Punjab holidays',
      icon: CalendarIcon,
      gradient: 'from-amber-500 to-orange-600',
      badge: 'Live AI Sync',
      badgeColor: 'bg-amber-100 text-amber-900'
    },
    {
      id: 'portals',
      title: 'Government Compliance Portals',
      desc: 'Instant direct launch to Income Tax, GST, MSME, AIF, TRACES, MCA & E-Way Bill',
      icon: Globe,
      gradient: 'from-blue-600 to-indigo-700',
      badge: '8 Gateways',
      badgeColor: 'bg-blue-100 text-blue-800'
    },
    {
      id: 'udin',
      title: 'ICAI UDIN Partner Manager',
      desc: 'Partner 1 & 2 credentials vault, live captcha visualizer, 1-click copy & update',
      icon: KeyRound,
      gradient: 'from-rose-600 to-pink-600',
      badge: '2 Partners',
      badgeColor: 'bg-rose-100 text-rose-800'
    },
    {
      id: 'msme',
      title: 'MSME Udyam AI Folder Assistant',
      desc: 'Drop client folders to extract variable data with fixed office presets & download Udyam',
      icon: FileSpreadsheet,
      gradient: 'from-orange-500 to-amber-600',
      badge: 'Gemini AI',
      badgeColor: 'bg-orange-100 text-orange-900'
    },
    {
      id: 'aif',
      title: 'Agriculture Infrastructure Fund (AIF)',
      desc: 'DPR & Land record analysis, 3% interest subvention schedule up to ₹2 Crore',
      icon: Sprout,
      gradient: 'from-emerald-600 to-green-700',
      badge: '3% Subsidy',
      badgeColor: 'bg-emerald-100 text-emerald-800'
    },
    {
      id: 'tools',
      title: 'Office PDF & Automation Suite',
      desc: 'PDF Merge, Compress strictly to target MB, Image-to-PDF, Page Organizer & Redaction',
      icon: Wrench,
      gradient: 'from-teal-600 to-cyan-700',
      badge: '5 Tools',
      badgeColor: 'bg-teal-100 text-teal-800'
    }
  ];

  const filteredCards = quickJumpCards.filter(c =>
    c.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
    c.desc.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6 mb-8">
      {/* Lively Hero Master Card */}
      <div className="relative rounded-3xl bg-gradient-to-r from-emerald-700 via-teal-800 to-amber-600 p-6 sm:p-8 text-white shadow-xl overflow-hidden">
        {/* Decorative ambient blobs */}
        <div className="absolute top-0 right-0 -mt-8 -mr-8 w-72 h-72 rounded-full bg-amber-400/20 blur-3xl pointer-events-none"></div>
        <div className="absolute bottom-0 left-1/3 -mb-12 w-64 h-64 rounded-full bg-emerald-400/20 blur-3xl pointer-events-none"></div>

        <div className="relative z-10">
          <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
            <div className="flex items-center space-x-3">
              <div className="w-12 h-12 rounded-2xl bg-white/15 backdrop-blur-md flex items-center justify-center border border-white/25 shadow-md">
                <Building2 className="w-7 h-7 text-amber-300" />
              </div>
              <div>
                <span className="text-[11px] font-extrabold uppercase tracking-widest text-amber-300 bg-black/20 px-2.5 py-0.5 rounded-full border border-white/10">
                  Single Pager Executive Desk
                </span>
                <h1 className="text-2xl sm:text-4xl font-black tracking-tight text-white mt-0.5">
                  CA RISHU GARG &amp; ASSOCIATES
                </h1>
              </div>
            </div>

            {/* Role indicator pill */}
            <div className="flex items-center space-x-2 bg-white/15 backdrop-blur-md px-3.5 py-2 rounded-2xl border border-white/20">
              <ShieldCheck className="w-5 h-5 text-amber-300" />
              <div className="text-left text-xs">
                <div className="font-extrabold text-white">
                  {auth.role === 'admin' ? 'Administrator Login' : 'Staff Common Login'}
                </div>
                <div className="text-[10px] text-emerald-100">{auth.username}</div>
              </div>
            </div>
          </div>

          <p className="text-sm sm:text-base text-emerald-50 max-w-3xl leading-relaxed mb-6">
            All firm workflows on a single continuous page: Task management with weekly charts, Punjab statutory compliance, 1-click Government portals, ICAI UDIN manager, AI MSME &amp; AIF dossiers, and client-side PDF automation tools.
          </p>

          {/* Quick Search on Single Page */}
          <div className="max-w-xl relative mb-6">
            <Search className="w-4 h-4 text-emerald-950 absolute left-3.5 top-3.5" />
            <input
              type="text"
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              placeholder="Search or jump to any module (Tasks, Calendar, UDIN, MSME, AIF, PDF Merge, Portals)..."
              className="w-full pl-10 pr-4 py-3 rounded-2xl bg-white text-slate-900 placeholder-slate-400 text-xs sm:text-sm font-semibold shadow-lg focus:outline-none focus:ring-4 focus:ring-amber-400"
            />
          </div>

          {/* Direct Government Portals Quick Links Row */}
          <div>
            <div className="text-[11px] font-bold uppercase tracking-wider text-amber-200 mb-2 flex items-center space-x-1.5">
              <Globe className="w-3.5 h-3.5" />
              <span>Link of Everything: Official Government &amp; ICAI Gateways</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {GOV_PORTALS.map((portal, idx) => (
                <a
                  key={idx}
                  href={portal.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-white/15 hover:bg-white/30 backdrop-blur-md border border-white/20 text-xs font-bold text-white transition-all shadow-xs hover:scale-105 active:scale-95"
                >
                  <span>{portal.shortName}</span>
                  <ExternalLink className="w-3 h-3 text-amber-200" />
                </a>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Visual Section Directory Cards Grid ("Link of Everything") */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2 text-slate-800 font-extrabold text-sm sm:text-base">
            <Layers className="w-5 h-5 text-emerald-600" />
            <span>Interactive Section Directory (1-Click Smooth Jump)</span>
          </div>
          <span className="text-xs text-slate-500 font-medium hidden sm:inline">
            Scroll down or tap any card to jump directly
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {filteredCards.map((card, idx) => {
            const Icon = card.icon;
            return (
              <div
                key={card.id}
                onClick={() => scrollToSection(card.id)}
                className="group cursor-pointer bg-white rounded-2xl p-4 border border-slate-200 hover:border-emerald-400 hover:shadow-lg transition-all flex flex-col justify-between hover:-translate-y-0.5"
              >
                <div>
                  <div className="flex items-center justify-between mb-2.5">
                    <div className={`w-9 h-9 rounded-xl bg-gradient-to-tr ${card.gradient} flex items-center justify-center text-white shadow-xs group-hover:scale-110 transition-transform`}>
                      <Icon className="w-5 h-5" />
                    </div>
                    <span className={`text-[10px] font-extrabold px-2 py-0.5 rounded-full ${card.badgeColor}`}>
                      {card.badge}
                    </span>
                  </div>

                  <h3 className="font-extrabold text-slate-900 text-sm group-hover:text-emerald-700 transition-colors leading-snug">
                    {card.title}
                  </h3>

                  <p className="text-xs text-slate-500 mt-1 line-clamp-2 leading-relaxed">
                    {card.desc}
                  </p>
                </div>

                <div className="mt-3 pt-2.5 border-t border-slate-100 flex items-center justify-between text-xs font-bold text-emerald-700">
                  <span>Jump to Section</span>
                  <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
