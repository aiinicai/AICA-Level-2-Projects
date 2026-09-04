import React from 'react';
import { 
  Briefcase, 
  FileText, 
  AlertOctagon, 
  IndianRupee, 
  CheckCircle2, 
  Clock, 
  ArrowUpRight, 
  PlusCircle, 
  FileSpreadsheet, 
  TrendingUp,
  Building,
  ChevronRight,
  Eye,
  Edit3,
  FileDown
} from 'lucide-react';
import { Engagement, Observation, AuditType, FirmProfile } from '../../types/audit';
import { formatINR, formatDate, getSeverityBadgeClass, getStatusBadgeClass } from '../../utils/formatters';
import { ExportService } from '../../services/exportService';

interface DashboardViewProps {
  engagements?: Engagement[];
  observations?: Observation[];
  auditTypes?: AuditType[];
  firmProfile: FirmProfile;
  onOpenNewObservation: () => void;
  onOpenNewEngagement: () => void;
  onViewObservation: (obs: Observation) => void;
  onEditObservation?: (obs: Observation) => void;
  onViewEngagement?: (eng: Engagement) => void;
  onNavigateToObservations?: (filterOptions?: any) => void;
  onNavigateToEngagements?: () => void;
  onQuickUpdateStatus?: (obsId: string, newStatus: any) => void;
  onNavigate?: (view: any) => void;
  onFilterObservations?: (filterOptions: any) => void;
}

export const DashboardView: React.FC<DashboardViewProps> = ({
  engagements = [],
  observations = [],
  auditTypes = [],
  firmProfile,
  onOpenNewObservation,
  onOpenNewEngagement,
  onViewObservation,
  onEditObservation = (_obs: Observation) => {},
  onViewEngagement = (_eng: Engagement) => {},
  onNavigateToObservations,
  onNavigateToEngagements,
  onQuickUpdateStatus = (_obsId: string, _newStatus: any) => {},
  onNavigate,
  onFilterObservations,
}) => {
  const engList = engagements || [];
  const obsList = observations || [];
  const typeList = auditTypes || [];

  const handleGoToObservations = (filterOptions?: any) => {
    if (onNavigateToObservations) {
      onNavigateToObservations(filterOptions);
    } else if (onFilterObservations) {
      onFilterObservations(filterOptions);
    } else if (onNavigate) {
      onNavigate('observations');
    }
  };

  const handleGoToEngagements = () => {
    if (onNavigateToEngagements) {
      onNavigateToEngagements();
    } else if (onNavigate) {
      onNavigate('engagements');
    }
  };

  const auditTypeMap = new Map<string, AuditType>(typeList.map(at => [at.id, at]));
  const engagementMap = new Map<string, Engagement>(engList.map(e => [e.id, e]));

  // Metrics
  const totalObservations = obsList.length;
  const closedObservations = obsList.filter(o => o.status === 'Closed' || o.status === 'Rectified').length;
  const openObservations = totalObservations - closedObservations;
  const criticalObservations = obsList.filter(o => o.severity === 'Critical');
  const highObservations = obsList.filter(o => o.severity === 'High');
  const mediumObservations = obsList.filter(o => o.severity === 'Medium');
  const lowObservations = obsList.filter(o => o.severity === 'Low');

  const criticalAndHighOpenCount = obsList.filter(
    o => (o.severity === 'Critical' || o.severity === 'High') && o.status !== 'Closed' && o.status !== 'Rectified'
  ).length;

  const totalFinancialImpact = obsList.reduce((acc, o) => acc + (o.financialImpact || 0), 0);

  // Recent open critical & high observations
  const urgentObservations = obsList
    .filter(o => o.status !== 'Closed' && o.status !== 'Rectified')
    .sort((a, b) => {
      const order = { Critical: 0, High: 1, Medium: 2, Low: 3 };
      if (order[a.severity] !== order[b.severity]) {
        return order[a.severity] - order[b.severity];
      }
      return new Date(b.dateOfObservation).getTime() - new Date(a.dateOfObservation).getTime();
    })
    .slice(0, 6);

  // Audit type breakdown
  const auditTypeStats = typeList.map(at => {
    const matchingEngs = engList.filter(e => e.auditTypeId === at.id);
    const engIds = new Set(matchingEngs.map(e => e.id));
    const matchingObs = obsList.filter(o => engIds.has(o.engagementId));
    const openCount = matchingObs.filter(o => o.status !== 'Closed' && o.status !== 'Rectified').length;
    const impact = matchingObs.reduce((sum, o) => sum + (o.financialImpact || 0), 0);

    return {
      type: at,
      engagementCount: matchingEngs.length,
      observationCount: matchingObs.length,
      openCount,
      impact,
    };
  }).filter(stat => stat.engagementCount > 0 || stat.observationCount > 0);

  return (
    <div id="dashboard-view-container" className="space-y-6">
      {/* Top Header & Quick Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-5 rounded-2xl border border-stone-200 shadow-sm">
        <div>
          <h1 className="text-xl font-bold text-stone-800 tracking-tight">Audit Practice Dashboard</h1>
          <p className="text-sm text-stone-500 mt-0.5">
            Real-time tracking of active engagements, risk findings, and management rectifications.
          </p>
        </div>
        <div className="flex items-center gap-2.5">
          <button
            id="dash-export-all-excel"
            onClick={() => ExportService.exportObservationsToExcel(obsList, engList, typeList, 'Audit_Tracker_Master')}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg border border-stone-300 bg-white hover:bg-[#F5F2ED] text-stone-700 text-xs font-semibold shadow-xs transition-colors"
          >
            <FileSpreadsheet className="w-4 h-4 text-emerald-700" />
            <span>Master Excel Export</span>
          </button>
          <button
            id="dash-new-obs-btn"
            onClick={onOpenNewObservation}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-[#5A5A40] hover:bg-[#4A4A34] text-white text-xs font-semibold shadow-xs transition-colors"
          >
            <PlusCircle className="w-4 h-4 text-amber-300" />
            <span>+ New Observation</span>
          </button>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {/* Card 1: Total Engagements */}
        <div 
          onClick={handleGoToEngagements}
          className="bg-white p-5 rounded-2xl shadow-sm border border-stone-200 hover:border-stone-300 transition-all cursor-pointer group"
        >
          <p className="text-xs font-bold text-stone-400 uppercase tracking-wider mb-1">Total Active Audits</p>
          <p className="text-3xl font-light text-stone-800">{engList.length}</p>
          <div className="mt-3 text-xs text-stone-500 flex items-center justify-between pt-2 border-t border-stone-100">
            <span>{engList.filter(e => e.overallStatus === 'In Progress').length} In Progress</span>
            <span className="text-[#5A5A40] font-semibold group-hover:underline flex items-center">
              View All <ChevronRight className="w-3 h-3 ml-0.5" />
            </span>
          </div>
        </div>

        {/* Card 2: Observations Logged */}
        <div 
          onClick={() => handleGoToObservations()}
          className="bg-white p-5 rounded-2xl shadow-sm border border-stone-200 hover:border-stone-300 transition-all cursor-pointer group"
        >
          <p className="text-xs font-bold text-stone-400 uppercase tracking-wider mb-1">Open Observations</p>
          <p className="text-3xl font-light text-amber-600">{openObservations}</p>
          <div className="mt-3 text-xs text-stone-500 flex items-center justify-between pt-2 border-t border-stone-100">
            <span>{closedObservations} Rectified / Closed</span>
            <span className="text-[#5A5A40] font-semibold group-hover:underline flex items-center">
              Register <ChevronRight className="w-3 h-3 ml-0.5" />
            </span>
          </div>
        </div>

        {/* Card 3: High Risk / Critical Attention */}
        <div 
          onClick={() => handleGoToObservations({ severity: ['Critical', 'High'] })}
          className="bg-white p-5 rounded-2xl shadow-sm border border-stone-200 border-l-4 border-l-rose-500 hover:bg-rose-50/20 transition-all cursor-pointer group"
        >
          <p className="text-xs font-bold text-stone-400 uppercase tracking-wider mb-1">Critical Issues</p>
          <p className="text-3xl font-light text-rose-600">{criticalAndHighOpenCount.toString().padStart(2, '0')}</p>
          <div className="mt-3 text-xs text-stone-500 flex items-center justify-between pt-2 border-t border-stone-100">
            <span>{criticalObservations.length} Critical, {highObservations.length} High</span>
            <span className="text-rose-600 font-semibold group-hover:underline flex items-center">
              Filter <ChevronRight className="w-3 h-3 ml-0.5" />
            </span>
          </div>
        </div>

        {/* Card 4: Closure Rate / Financial Impact */}
        <div className="bg-white p-5 rounded-2xl shadow-sm border border-stone-200">
          <p className="text-xs font-bold text-stone-400 uppercase tracking-wider mb-1">Closure Rate</p>
          <p className="text-3xl font-light text-emerald-600">
            {totalObservations > 0 ? `${Math.round((closedObservations / totalObservations) * 100)}%` : '100%'}
          </p>
          <div className="mt-3 text-xs text-stone-500 pt-2 border-t border-stone-100 truncate">
            Exposure: <strong className="text-stone-800 font-semibold">{formatINR(totalFinancialImpact)}</strong>
          </div>
        </div>
      </div>

      {/* Mid Section: Risk & Audit Type Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Severity Breakdown Card */}
        <div className="bg-white p-5 rounded-2xl border border-stone-200 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-stone-800">Observation Severity Distribution</h2>
            <span className="text-xs font-medium text-stone-500">{totalObservations} total</span>
          </div>

          <div className="space-y-3">
            {/* Critical */}
            <div 
              onClick={() => onNavigateToObservations({ severity: ['Critical'] })}
              className="p-2.5 rounded-xl bg-rose-50/50 hover:bg-rose-50 border border-rose-100 transition-colors cursor-pointer"
            >
              <div className="flex items-center justify-between text-xs font-semibold text-rose-900">
                <span className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-rose-600"></span>
                  Critical Risk
                </span>
                <span>{criticalObservations.length} ({totalObservations > 0 ? Math.round((criticalObservations.length / totalObservations) * 100) : 0}%)</span>
              </div>
              <div className="mt-1.5 w-full bg-rose-200/50 rounded-full h-1.5">
                <div 
                  className="bg-rose-600 h-1.5 rounded-full" 
                  style={{ width: `${totalObservations > 0 ? (criticalObservations.length / totalObservations) * 100 : 0}%` }}
                ></div>
              </div>
              <div className="mt-1 text-[11px] text-rose-700 font-medium">
                Exposure: {formatINR(criticalObservations.reduce((s, o) => s + (o.financialImpact || 0), 0))}
              </div>
            </div>

            {/* High */}
            <div 
              onClick={() => onNavigateToObservations({ severity: ['High'] })}
              className="p-2.5 rounded-xl bg-amber-50/50 hover:bg-amber-50 border border-amber-100 transition-colors cursor-pointer"
            >
              <div className="flex items-center justify-between text-xs font-semibold text-amber-900">
                <span className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-amber-600"></span>
                  High Risk
                </span>
                <span>{highObservations.length} ({totalObservations > 0 ? Math.round((highObservations.length / totalObservations) * 100) : 0}%)</span>
              </div>
              <div className="mt-1.5 w-full bg-amber-200/50 rounded-full h-1.5">
                <div 
                  className="bg-amber-600 h-1.5 rounded-full" 
                  style={{ width: `${totalObservations > 0 ? (highObservations.length / totalObservations) * 100 : 0}%` }}
                ></div>
              </div>
              <div className="mt-1 text-[11px] text-amber-800 font-medium">
                Exposure: {formatINR(highObservations.reduce((s, o) => s + (o.financialImpact || 0), 0))}
              </div>
            </div>

            {/* Medium */}
            <div 
              onClick={() => onNavigateToObservations({ severity: ['Medium'] })}
              className="p-2.5 rounded-xl bg-yellow-50/50 hover:bg-yellow-50 border border-yellow-100 transition-colors cursor-pointer"
            >
              <div className="flex items-center justify-between text-xs font-semibold text-yellow-900">
                <span className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-yellow-500"></span>
                  Medium Risk
                </span>
                <span>{mediumObservations.length} ({totalObservations > 0 ? Math.round((mediumObservations.length / totalObservations) * 100) : 0}%)</span>
              </div>
              <div className="mt-1.5 w-full bg-yellow-200/50 rounded-full h-1.5">
                <div 
                  className="bg-yellow-500 h-1.5 rounded-full" 
                  style={{ width: `${totalObservations > 0 ? (mediumObservations.length / totalObservations) * 100 : 0}%` }}
                ></div>
              </div>
              <div className="mt-1 text-[11px] text-yellow-800 font-medium">
                Exposure: {formatINR(mediumObservations.reduce((s, o) => s + (o.financialImpact || 0), 0))}
              </div>
            </div>

            {/* Low */}
            <div 
              onClick={() => onNavigateToObservations({ severity: ['Low'] })}
              className="p-2.5 rounded-xl bg-emerald-50/50 hover:bg-emerald-50 border border-emerald-100 transition-colors cursor-pointer"
            >
              <div className="flex items-center justify-between text-xs font-semibold text-emerald-900">
                <span className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-600"></span>
                  Low / Compliance
                </span>
                <span>{lowObservations.length} ({totalObservations > 0 ? Math.round((lowObservations.length / totalObservations) * 100) : 0}%)</span>
              </div>
              <div className="mt-1.5 w-full bg-emerald-200/50 rounded-full h-1.5">
                <div 
                  className="bg-emerald-600 h-1.5 rounded-full" 
                  style={{ width: `${totalObservations > 0 ? (lowObservations.length / totalObservations) * 100 : 0}%` }}
                ></div>
              </div>
            </div>
          </div>
        </div>

        {/* Audit Types & Client Engagements Summary */}
        <div className="lg:col-span-2 bg-white p-5 rounded-2xl border border-stone-200 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold text-stone-800">Audit Assignments by Discipline</h2>
              <p className="text-xs text-stone-500">Breakdown of Stock, Tax, CAG, and Concurrent Audits</p>
            </div>
            <button
              onClick={onNavigateToEngagements}
              className="text-xs font-semibold text-[#5A5A40] hover:underline flex items-center"
            >
              Manage Engagements <ChevronRight className="w-3.5 h-3.5 ml-0.5" />
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {auditTypeStats.map(stat => (
              <div
                key={stat.type.id}
                onClick={() => handleGoToObservations({ auditTypeId: stat.type.id })}
                className="p-3.5 rounded-xl border border-stone-200 hover:border-stone-300 hover:bg-[#FAF9F6] transition-all cursor-pointer"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded-md bg-[#5A5A40] text-amber-300 font-bold text-[11px]">
                      {stat.type.code}
                    </span>
                    <span className="font-bold text-xs text-stone-800">{stat.type.name}</span>
                  </div>
                  <span className="text-xs font-semibold text-stone-600">
                    {stat.engagementCount} Eng.
                  </span>
                </div>
                <div className="mt-3 flex items-center justify-between text-xs text-stone-500 pt-2 border-t border-stone-100">
                  <span>
                    <strong className="text-stone-800">{stat.observationCount}</strong> Obs. ({stat.openCount} Open)
                  </span>
                  <span className="font-semibold text-stone-700">{formatINR(stat.impact)}</span>
                </div>
              </div>
            ))}
          </div>

          {/* Status lifecycle pipeline pills */}
          <div className="pt-3 border-t border-stone-100">
            <div className="text-xs font-bold text-stone-700 mb-2">Observation Lifecycle Pipeline:</div>
            <div className="flex flex-wrap gap-2">
              <span className="px-2.5 py-1 rounded-lg bg-rose-50 text-rose-800 text-xs font-medium border border-rose-200">
                Open: {obsList.filter(o => o.status === 'Open').length}
              </span>
              <span className="px-2.5 py-1 rounded-lg bg-amber-50 text-amber-800 text-xs font-medium border border-amber-200">
                Under Discussion: {obsList.filter(o => o.status === 'Under Discussion').length}
              </span>
              <span className="px-2.5 py-1 rounded-lg bg-stone-100 text-stone-800 text-xs font-medium border border-stone-300">
                Response Awaited: {obsList.filter(o => o.status === 'Management Response Awaited').length}
              </span>
              <span className="px-2.5 py-1 rounded-lg bg-[#5A5A40]/10 text-[#5A5A40] text-xs font-medium border border-[#5A5A40]/30">
                Rectified: {obsList.filter(o => o.status === 'Rectified').length}
              </span>
              <span className="px-2.5 py-1 rounded-lg bg-emerald-50 text-emerald-800 text-xs font-medium border border-emerald-200">
                Closed: {obsList.filter(o => o.status === 'Closed').length}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Priority Action Queue Table: Urgent Open Observations */}
      <div className="bg-white rounded-2xl border border-stone-200 shadow-sm overflow-hidden">
        <div className="p-5 border-b border-stone-100 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-[#FAF9F6]">
          <div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 bg-amber-500 rounded-full mr-1"></span>
              <h2 className="text-base font-bold text-stone-800">Recent High-Priority Observations</h2>
              <span className="px-2 py-0.5 rounded-full bg-rose-100 text-rose-800 text-xs font-bold">
                {urgentObservations.length} Urgent
              </span>
            </div>
            <p className="text-xs text-stone-500 mt-0.5">
              Open Critical and High severity observations pending discussion or rectification
            </p>
          </div>
          <button
            onClick={() => handleGoToObservations({ status: ['Open', 'Under Discussion', 'Management Response Awaited'] })}
            className="text-sm text-[#5A5A40] font-semibold underline underline-offset-4 flex items-center self-start sm:self-auto"
          >
            View All <ChevronRight className="w-4 h-4 ml-1" />
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-stone-200 bg-stone-50 text-[11px] font-bold text-stone-500 uppercase tracking-wider">
                <th className="py-3.5 px-6">Ref No.</th>
                <th className="py-3.5 px-6">Client Name</th>
                <th className="py-3.5 px-6">Process Area</th>
                <th className="py-3.5 px-6">Severity</th>
                <th className="py-3.5 px-6">Target Date</th>
                <th className="py-3.5 px-6">Status</th>
                <th className="py-3.5 px-6 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100 text-sm">
              {urgentObservations.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-stone-400">
                    <CheckCircle2 className="w-8 h-8 text-emerald-600 mx-auto mb-2" />
                    <p className="font-medium text-stone-600">No urgent open observations found!</p>
                    <p className="text-xs text-stone-400 mt-0.5">All critical audit items are rectified or closed.</p>
                  </td>
                </tr>
              ) : (
                urgentObservations.map((obs) => {
                  const eng = engagementMap.get(obs.engagementId);
                  const at = eng ? auditTypeMap.get(eng.auditTypeId) : undefined;
                  const statStyle = getStatusBadgeClass(obs.status);

                  return (
                    <tr key={obs.id} className="hover:bg-stone-50 transition-colors">
                      <td className="px-6 py-4 font-mono text-xs text-stone-500">
                        {obs.referenceNo}
                      </td>
                      <td className="px-6 py-4 font-medium text-stone-800">
                        {eng?.clientName || 'Unknown Client'}
                      </td>
                      <td className="px-6 py-4 text-stone-600">
                        {obs.areaProcess}
                      </td>
                      <td className="px-6 py-4">
                        {obs.severity === 'Critical' && (
                          <span className="px-2 py-1 bg-red-100 text-red-700 text-[10px] font-bold rounded uppercase">Critical</span>
                        )}
                        {obs.severity === 'High' && (
                          <span className="px-2 py-1 bg-orange-100 text-orange-700 text-[10px] font-bold rounded uppercase">High</span>
                        )}
                        {obs.severity === 'Medium' && (
                          <span className="px-2 py-1 bg-yellow-100 text-yellow-700 text-[10px] font-bold rounded uppercase">Medium</span>
                        )}
                        {obs.severity === 'Low' && (
                          <span className="px-2 py-1 bg-green-100 text-green-700 text-[10px] font-bold rounded uppercase">Low</span>
                        )}
                      </td>
                      <td className="px-6 py-4 text-stone-500">
                        {formatDate(obs.targetRectificationDate)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <select
                          value={obs.status}
                          onChange={(e) => onQuickUpdateStatus(obs.id, e.target.value)}
                          className={`text-xs font-medium rounded-lg px-2.5 py-1 border focus:outline-hidden cursor-pointer ${statStyle.bg} ${statStyle.text} ${statStyle.border}`}
                        >
                          <option value="Open">Open</option>
                          <option value="Under Discussion">Under Discussion</option>
                          <option value="Management Response Awaited">Resp Awaited</option>
                          <option value="Rectified">Rectified</option>
                          <option value="Closed">Closed</option>
                          <option value="Not Accepted">Not Accepted</option>
                        </select>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right space-x-1">
                        <button
                          onClick={() => onViewObservation(obs)}
                          className="p-1.5 rounded-lg text-stone-500 hover:text-stone-900 hover:bg-stone-100 transition-colors"
                          title="View Observation Details & Letterhead Memo"
                        >
                          <Eye className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => onEditObservation(obs)}
                          className="p-1.5 rounded-lg text-stone-500 hover:text-stone-900 hover:bg-stone-100 transition-colors"
                          title="Edit Observation"
                        >
                          <Edit3 className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => {
                            if (eng) {
                              ExportService.exportSingleObservationPDF(obs, eng, at, firmProfile);
                            }
                          }}
                          className="p-1.5 rounded-lg text-stone-500 hover:text-stone-900 hover:bg-stone-100 transition-colors"
                          title="Download PDF Memo"
                        >
                          <FileDown className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Natural Tones Quick Action Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div 
          onClick={() => ExportService.exportObservationsToExcel(obsList, engList, typeList, 'Audit_Tracker_Monthly_Report')}
          className="flex items-center p-4 bg-emerald-50 rounded-2xl border border-emerald-100 hover:border-emerald-200 transition-all cursor-pointer"
        >
          <div className="w-10 h-10 bg-emerald-600 text-white rounded-full flex items-center justify-center mr-4 shrink-0 shadow-xs">
            <FileSpreadsheet className="w-5 h-5" />
          </div>
          <div>
            <p className="font-bold text-emerald-900 leading-none">Monthly Export</p>
            <p className="text-xs text-emerald-700 mt-1">Generate Excel for all clients</p>
          </div>
        </div>

        <div 
          onClick={handleGoToEngagements}
          className="flex items-center p-4 bg-stone-50 rounded-2xl border border-stone-200 hover:border-stone-300 transition-all cursor-pointer"
        >
          <div className="w-10 h-10 bg-[#5A5A40] text-white rounded-full flex items-center justify-center mr-4 shrink-0 shadow-xs">
            <Briefcase className="w-5 h-5" />
          </div>
          <div>
            <p className="font-bold text-stone-900 leading-none">Client Master</p>
            <p className="text-xs text-stone-600 mt-1">Manage engagement team</p>
          </div>
        </div>

        <div 
          onClick={() => handleGoToObservations()}
          className="flex items-center p-4 bg-[#F5F2ED] rounded-2xl border border-[#DED9D0] hover:border-stone-400 transition-all cursor-pointer"
        >
          <div className="w-10 h-10 bg-[#5A5A40] text-white rounded-full flex items-center justify-center mr-4 shrink-0 shadow-xs">
            <FileText className="w-5 h-5" />
          </div>
          <div>
            <p className="font-bold text-stone-800 leading-none">Observations Log</p>
            <p className="text-xs text-stone-600 mt-1">Manage finding registers</p>
          </div>
        </div>
      </div>
    </div>
  );
};
