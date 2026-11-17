import React, { useState } from 'react';
import { GOV_PORTALS } from '../data/statutoryData';
import { Globe, ExternalLink, Search, ShieldCheck, Sparkles, ArrowUpRight, CheckCircle2 } from 'lucide-react';

export const GovernmentPortals: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('');

  const filteredPortals = GOV_PORTALS.filter(portal => {
    const q = searchQuery.toLowerCase();
    return (
      portal.name.toLowerCase().includes(q) ||
      portal.shortName.toLowerCase().includes(q) ||
      portal.description.toLowerCase().includes(q) ||
      portal.tags.some(t => t.toLowerCase().includes(q))
    );
  });

  return (
    <div className="space-y-6 pb-12">
      {/* Top Banner */}
      <div className="bg-gradient-to-r from-blue-700 via-indigo-700 to-teal-700 rounded-2xl p-5 sm:p-6 text-white shadow-lg relative overflow-hidden">
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2 mb-1">
              <span className="px-2.5 py-0.5 rounded-full text-[11px] font-extrabold bg-white/20 backdrop-blur-xs text-white uppercase tracking-wider">
                Official Central &amp; State Gateways
              </span>
              <span className="text-xs text-blue-200">• Direct CA Portals</span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
              Government Compliance Portals
            </h2>
            <p className="text-xs sm:text-sm text-blue-100 mt-1 max-w-2xl">
              One-click direct access to official filing, audit verification, e-Pay taxes, MSME registration, and Agriculture Infrastructure Fund platforms.
            </p>
          </div>

          {/* Quick Search */}
          <div className="w-full md:w-72 relative">
            <Search className="w-4 h-4 text-blue-200 absolute left-3 top-3" />
            <input
              type="text"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              placeholder="Search ITR, GST, MSME, AIF..."
              className="w-full pl-9 pr-3 py-2 rounded-xl bg-white/10 backdrop-blur-md border border-white/20 text-white placeholder-blue-200 text-xs focus:outline-none focus:ring-2 focus:ring-white/40"
            />
          </div>
        </div>
      </div>

      {/* Portals Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {filteredPortals.map((portal, idx) => {
          return (
            <div
              key={idx}
              className="bg-white rounded-2xl p-5 border border-slate-200 hover:border-emerald-400 hover:shadow-lg transition-all flex flex-col justify-between group"
            >
              <div>
                {/* Header with color gradient pill */}
                <div className="flex items-center justify-between mb-3">
                  <div className={`w-10 h-10 rounded-xl bg-gradient-to-tr ${portal.color} flex items-center justify-center text-white shadow-md`}>
                    <Globe className="w-5 h-5" />
                  </div>
                  <span className="text-[10px] font-extrabold bg-slate-100 text-slate-700 px-2 py-0.5 rounded-full border border-slate-200">
                    {portal.badge}
                  </span>
                </div>

                <h3 className="font-extrabold text-slate-900 text-base group-hover:text-emerald-700 transition-colors">
                  {portal.name}
                </h3>
                <p className="text-xs text-slate-500 font-medium mb-3">
                  {portal.shortName}
                </p>

                <p className="text-xs text-slate-600 leading-relaxed mb-4">
                  {portal.description}
                </p>

                {/* Tags */}
                <div className="flex flex-wrap gap-1.5 mb-4">
                  {portal.tags.map((tag, tIdx) => (
                    <span
                      key={tIdx}
                      className="text-[10px] bg-slate-50 text-slate-600 px-2 py-0.5 rounded-md border border-slate-200 font-medium"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </div>

              {/* Action Button */}
              <a
                href={portal.url}
                target="_blank"
                rel="noopener noreferrer"
                className="w-full py-2.5 px-3 bg-slate-100 hover:bg-emerald-600 hover:text-white text-slate-800 rounded-xl text-xs font-bold transition-all flex items-center justify-center space-x-1.5 group-hover:bg-emerald-600 group-hover:text-white"
              >
                <span>Launch Portal</span>
                <ArrowUpRight className="w-4 h-4" />
              </a>
            </div>
          );
        })}
      </div>
    </div>
  );
};
