import React, { useState, useEffect } from "react";
import { db } from "../lib/firebase";
import { collection, onSnapshot } from "firebase/firestore";
import { Service, Engagement, Client, UserProfile } from "../types";
import { SERVICES_CONFIG } from "../lib/retention";
import {
  Folder,
  FolderOpen,
  Lock,
  Plus,
  Search,
  Calendar,
  ChevronRight,
  CheckCircle2,
  Clock,
  RotateCcw,
  Mail,
  AlertCircle,
  ExternalLink,
  ShieldCheck,
  Users,
  UserCheck,
  UserPlus
} from "lucide-react";

interface ServiceFolderListProps {
  userProfile: UserProfile;
  onSelectEngagement: (engagementId: string) => void;
}

export const ServiceFolderList: React.FC<ServiceFolderListProps> = ({
  userProfile,
  onSelectEngagement,
}) => {
  const [services, setServices] = useState<Service[]>([]);
  const [engagements, setEngagements] = useState<Engagement[]>([]);
  const [clients, setClients] = useState<Record<string, Client>>({});
  const [teamMembers, setTeamMembers] = useState<UserProfile[]>([]);
  const [allUsersMap, setAllUsersMap] = useState<Record<string, UserProfile>>({});
  const [expandedServiceId, setExpandedServiceId] = useState<string | null>("statutory-audit");
  const [searchTerm, setSearchTerm] = useState("");
  const [loading, setLoading] = useState(true);

  // New Engagement Form Modal State
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [selectedServiceForNew, setSelectedServiceForNew] = useState("statutory-audit");
  const [selectedClientId, setSelectedClientId] = useState("");
  const [selectedTeamMemberIds, setSelectedTeamMemberIds] = useState<string[]>([]);
  const [contractStartDate, setContractStartDate] = useState("2026-01-01");
  const [contractEndDate, setContractEndDate] = useState("2026-12-31");
  const [creating, setCreating] = useState(false);
  const [createProof, setCreateProof] = useState<any | null>(null);

  const [servicesError, setServicesError] = useState<string | null>(null);

  // 1. Listen to Services collection in real-time
  useEffect(() => {
    if (!userProfile || !userProfile.uid) {
      return;
    }

    const unsubServices = onSnapshot(
      collection(db, "services"),
      (snap) => {
        const list: Service[] = [];
        snap.forEach((doc) => {
          list.push({ id: doc.id, ...doc.data() } as Service);
        });
        setServices(list);
        setServicesError(null);
      },
      (err) => {
        console.error("Services snapshot error:", err);
        setServicesError(err.message || "Failed to load services from Firestore.");
      }
    );

    return () => unsubServices();
  }, [userProfile?.uid]);

  // 2. Listen to Clients dictionary
  useEffect(() => {
    if (!userProfile || !userProfile.uid) {
      return;
    }

    const unsubClients = onSnapshot(
      collection(db, "clients"),
      (snap) => {
        const map: Record<string, Client> = {};
        snap.forEach((doc) => {
          map[doc.id] = { id: doc.id, ...doc.data() } as Client;
        });
        setClients(map);
      },
      (err) => {
        console.error("Clients snapshot error:", err);
      }
    );

    return () => unsubClients();
  }, [userProfile?.uid]);

  // 3. Listen to Users collection in real-time (Populate team members with role: "team_member")
  useEffect(() => {
    if (!userProfile || !userProfile.uid) {
      return;
    }

    const unsubUsers = onSnapshot(
      collection(db, "users"),
      (snap) => {
        const staffList: UserProfile[] = [];
        const usersMap: Record<string, UserProfile> = {};

        snap.forEach((docSnap) => {
          const u = { uid: docSnap.id, ...docSnap.data() } as UserProfile;
          usersMap[u.uid] = u;

          // Filter by role "team_member" (or full_admin)
          if (u.role === "team_member") {
            staffList.push(u);
          }
        });

        setTeamMembers(staffList);
        setAllUsersMap(usersMap);

        // Pre-select team members if not yet selected
        setSelectedTeamMemberIds((prev) => {
          if (prev.length === 0 && staffList.length > 0) {
            return [staffList[0].uid];
          }
          return prev;
        });
      },
      (err) => {
        console.error("Users snapshot error:", err);
      }
    );

    return () => unsubUsers();
  }, [userProfile?.uid]);

  // 4. Listen to Engagements collection in real-time
  useEffect(() => {
    if (!userProfile || !userProfile.uid) {
      setLoading(false);
      return;
    }

    setLoading(true);
    const engQuery = collection(db, "engagements");

    const unsub = onSnapshot(
      engQuery,
      (snap) => {
        const list: Engagement[] = [];
        snap.forEach((docSnap) => {
          const data = { id: docSnap.id, ...docSnap.data() } as Engagement;

          // Scope enforcement
          if (userProfile.role === "full_admin") {
            list.push(data);
          } else if (userProfile.role === "team_member") {
            if (data.assignedTeamMemberIds?.includes(userProfile.uid)) {
              list.push(data);
            }
          } else if (userProfile.role === "client") {
            if (data.clientId === userProfile.linkedClientId) {
              list.push(data);
            }
          }
        });
        setEngagements(list);
        setLoading(false);
      },
      (err) => {
        console.error("Engagements snapshot error:", err);
        setLoading(false);
      }
    );

    return () => unsub();
  }, [userProfile?.uid, userProfile?.role, userProfile?.linkedClientId]);

  // Handle Create Engagement (Admin only) - Creates folder, assigns team members, and fires SINGLE COMBINED email
  const handleCreateEngagement = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedClientId || !selectedServiceForNew) return;

    setCreating(true);
    setCreateProof(null);

    try {
      const resp = await fetch("/api/engagements/create-and-notify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          clientId: selectedClientId,
          serviceId: selectedServiceForNew,
          contractStartDate,
          contractEndDate,
          actorUid: userProfile.uid,
          actorEmail: userProfile.email,
          assignedTeamMemberIds: selectedTeamMemberIds,
        }),
      });

      const result = await resp.json();
      if (!result.success) {
        throw new Error(result.error || "Failed to create engagement");
      }

      setCreateProof(result);
      setIsCreateModalOpen(false);
      setExpandedServiceId(selectedServiceForNew);
    } catch (err: any) {
      console.error("Error creating engagement:", err);
      alert(`Error creating engagement: ${err.message}`);
    } finally {
      setCreating(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "APPROVED":
        return (
          <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-950 text-emerald-300 border border-emerald-800 flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3" /> Approved
          </span>
        );
      case "BEING_REVIEWED":
        return (
          <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-950 text-amber-300 border border-amber-800 flex items-center gap-1">
            <Clock className="w-3 h-3" /> Being Reviewed
          </span>
        );
      case "WIP":
      default:
        return (
          <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-slate-800 text-slate-300 border border-slate-700 flex items-center gap-1">
            <RotateCcw className="w-3 h-3" /> Work in Progress
          </span>
        );
    }
  };

  const getConsentBadge = (consentStatus: string) => {
    switch (consentStatus) {
      case "GIVEN":
        return (
          <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-950 text-emerald-300 border border-emerald-800 flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3 text-emerald-400" /> Consent Given
          </span>
        );
      case "SENT":
        return (
          <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-sky-950 text-sky-300 border border-sky-800 flex items-center gap-1">
            <Mail className="w-3 h-3 text-sky-400" /> Notice Emailed
          </span>
        );
      case "SEND_FAILED":
        return (
          <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-rose-950 text-rose-300 border border-rose-800 flex items-center gap-1">
            <AlertCircle className="w-3 h-3 text-rose-400" /> Email Send Failed
          </span>
        );
      case "WITHDRAWN":
        return (
          <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-orange-950 text-orange-300 border border-orange-800 flex items-center gap-1">
            <AlertCircle className="w-3 h-3 text-orange-400" /> Consent Withdrawn
          </span>
        );
      case "DECLINED":
        return (
          <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-rose-950 text-rose-300 border border-rose-800 flex items-center gap-1">
            <AlertCircle className="w-3 h-3 text-rose-400" /> Consent Declined
          </span>
        );
      case "PENDING":
      default:
        return (
          <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-950 text-amber-300 border border-amber-800 flex items-center gap-1">
            <Clock className="w-3 h-3 text-amber-400" /> Consent Pending
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header & Search / Actions Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
            <FolderOpen className="w-6 h-6 text-indigo-400" />
            Statutory Service Folders & Client Engagements
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Browse top-level statutory service directories and client sub-folders with automated DPDP retention tracking.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="relative w-full sm:w-64">
            <Search className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search services or clients..."
              className="w-full bg-slate-900 border border-slate-700 rounded-xl pl-9 pr-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          {userProfile.role === "full_admin" && (
            <button
              onClick={() => setIsCreateModalOpen(true)}
              className="px-3.5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold flex items-center gap-1.5 shadow-md shrink-0 transition-all"
            >
              <Plus className="w-4 h-4" />
              <span>Create Engagement / Folder</span>
            </button>
          )}
        </div>
      </div>

      {/* Creation & Email Dispatch Verification Banner */}
      {createProof && (
        <div className="p-4 bg-emerald-950/80 border border-emerald-800 text-emerald-200 text-xs rounded-2xl space-y-3 shadow-lg">
          <div className="flex items-center justify-between font-bold text-emerald-300">
            <span className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              Client Engagement Folder Created & Single Setup Email Dispatched!
            </span>
            <button onClick={() => setCreateProof(null)} className="text-emerald-400 hover:underline">
              Dismiss
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-[11px] bg-slate-950/60 p-3 rounded-xl border border-emerald-900/50">
            <div>
              <div className="text-slate-400">Engagement ID:</div>
              <div className="font-mono text-emerald-300 font-bold">{createProof.engagementId}</div>
              
              <div className="text-slate-400 mt-2">Erasure Due Date:</div>
              <div className="font-mono text-white">{createProof.engagement?.erasureDueDate}</div>
            </div>

            <div>
              <div className="text-slate-400">Client Login Account:</div>
              <div className="font-mono text-white">{createProof.clientUser?.email} (Password: Client@2026)</div>

              <div className="text-slate-400 mt-2">SMTP Delivery Result:</div>
              <div className="font-mono text-emerald-300">
                Method: {createProof.emailResult?.method}
              </div>
              <div className="font-mono text-[10px] text-slate-400">
                MessageId: {createProof.emailResult?.messageId}
              </div>

              {createProof.emailResult?.previewUrl && (
                <div className="mt-1.5">
                  <a
                    href={createProof.emailResult.previewUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="text-indigo-400 hover:text-indigo-300 underline inline-flex items-center gap-1 font-semibold"
                  >
                    <ExternalLink className="w-3 h-3" />
                    Open Live SMTP Mailbox Preview
                  </a>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Team Member Zero-Assignments Information Banner */}
      {userProfile.role === "team_member" && engagements.length === 0 && !loading && (
        <div className="p-4 bg-slate-900/90 border border-slate-800 rounded-2xl flex items-start gap-3 shadow-lg">
          <div className="p-2 bg-indigo-950/60 border border-indigo-800/60 rounded-xl text-indigo-400 shrink-0 mt-0.5">
            <Users className="w-5 h-5" />
          </div>
          <div>
            <h4 className="text-sm font-bold text-white">No Client Engagements Currently Assigned</h4>
            <p className="text-xs text-slate-400 mt-1 leading-relaxed">
              You are logged in as a Team Member (<strong className="text-slate-200">{userProfile.displayName || userProfile.email}</strong>). In compliance with firm data isolation, client folders, review notes, pending items, and working papers are strictly scoped to engagements you are assigned to. When a Senior Partner assigns you to an engagement, its client folder will automatically appear below in real time.
            </p>
          </div>
        </div>
      )}

      {/* Services Error or Empty State */}
      {servicesError && (
        <div className="p-4 bg-rose-950/80 border border-rose-800 rounded-2xl text-xs text-rose-200">
          <p className="font-bold text-rose-300">Firestore Services Error</p>
          <p className="mt-1">{servicesError}</p>
        </div>
      )}

      {!servicesError && services.length === 0 && !loading && (
        <div className="text-center py-12 bg-slate-900/60 border border-dashed border-slate-800 rounded-2xl p-6">
          <Folder className="w-8 h-8 text-slate-600 mx-auto mb-2" />
          <p className="text-sm font-semibold text-slate-300">No Services Found in Firestore</p>
          <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
            The services collection in Firestore returned 0 documents. Please run bootstrap or configure services.
          </p>
        </div>
      )}

      {/* Top-Level 7 Service Folders Container */}
      <div className="space-y-4">
        {services.map((service) => {
          const serviceConfig = SERVICES_CONFIG[service.id] || {
            name: service.name,
            basis: service.retentionPolicy?.basis || "contract_tenure",
            statute: service.retentionPolicy?.statute || "Statutory retention policy",
          };

          // Filter engagements under this service folder
          const serviceEngagements = engagements.filter((eng) => {
            if (eng.serviceId !== service.id) return false;
            if (!searchTerm) return true;

            const clientName = clients[eng.clientId]?.name || "";
            return (
              clientName.toLowerCase().includes(searchTerm.toLowerCase()) ||
              service.name.toLowerCase().includes(searchTerm.toLowerCase())
            );
          });

          const isExpanded = expandedServiceId === service.id;

          return (
            <div
              key={service.id}
              className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden transition-all shadow-lg"
            >
              {/* Top-Level Service Folder Header */}
              <button
                onClick={() => setExpandedServiceId(isExpanded ? null : service.id)}
                className="w-full p-4 sm:p-5 flex items-center justify-between bg-gradient-to-r from-slate-900 via-slate-900 to-slate-800/80 hover:bg-slate-800/80 transition-colors text-left"
              >
                <div className="flex items-center space-x-3.5">
                  <div
                    className={`p-2.5 rounded-xl border ${
                      isExpanded
                        ? "bg-indigo-600/20 text-indigo-400 border-indigo-500/40"
                        : "bg-slate-800 text-slate-400 border-slate-700"
                    }`}
                  >
                    {isExpanded ? <FolderOpen className="w-5 h-5" /> : <Folder className="w-5 h-5" />}
                  </div>

                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="text-base font-bold text-white tracking-tight">{service.name}</h3>
                      <span className="text-[10px] font-mono px-2 py-0.5 bg-slate-800 text-slate-400 rounded border border-slate-700">
                        {serviceConfig.basis === "from_date" ? "Statutory Tenure Basis" : "Contract Tenure Basis"}
                      </span>
                    </div>
                    <p className="text-xs text-slate-400 mt-0.5">Statute: {serviceConfig.statute}</p>
                  </div>
                </div>

                <div className="flex items-center space-x-3">
                  <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-800 text-slate-300 border border-slate-700">
                    {serviceEngagements.length} Client {serviceEngagements.length === 1 ? "Folder" : "Folders"}
                  </span>
                  <ChevronRight
                    className={`w-4 h-4 text-slate-400 transition-transform ${
                      isExpanded ? "rotate-90 text-indigo-400" : ""
                    }`}
                  />
                </div>
              </button>

              {/* Client Sub-folders List */}
              {isExpanded && (
                <div className="border-t border-slate-800 p-4 sm:p-5 bg-slate-950/60 space-y-3">
                  {serviceEngagements.length === 0 ? (
                    <div className="text-center py-8 text-xs text-slate-500 border border-dashed border-slate-800 rounded-xl">
                      {userProfile.role === "team_member"
                        ? `No client engagements assigned to your account under ${service.name}.`
                        : `No client engagements created under ${service.name} yet.`}
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                      {serviceEngagements.map((eng) => {
                        const clientObj = clients[eng.clientId];
                        const isLockedForClient = userProfile.role === "client" && eng.consentStatus !== "GIVEN";

                        return (
                          <div
                            key={eng.id}
                            onClick={() => onSelectEngagement(eng.id)}
                            className={`p-4 rounded-xl border transition-all cursor-pointer relative overflow-hidden group ${
                              isLockedForClient
                                ? "bg-slate-900/60 border-rose-950/60 opacity-80"
                                : "bg-slate-900 hover:bg-slate-800/90 border-slate-800 hover:border-slate-700 shadow-md"
                            }`}
                          >
                            <div className="flex items-start justify-between gap-2 mb-2">
                              <div className="flex items-center gap-2">
                                <Folder
                                  className={`w-4 h-4 ${isLockedForClient ? "text-rose-400" : "text-indigo-400"}`}
                                />
                                <h4 className="text-sm font-bold text-white group-hover:text-indigo-300 transition-colors">
                                  {clientObj?.name || "Client Sub-folder"}
                                </h4>
                              </div>

                              {getStatusBadge(eng.status)}
                            </div>

                            <div className="flex flex-wrap items-center gap-2 my-2.5">
                              {getConsentBadge(eng.consentStatus)}

                              <div className="text-[11px] font-mono text-slate-400 bg-slate-950 px-2 py-0.5 rounded border border-slate-800 flex items-center gap-1">
                                <Calendar className="w-3 h-3 text-slate-500" />
                                Erasure: <strong className="text-slate-200">{eng.erasureDueDate}</strong>
                              </div>
                            </div>

                            {/* Client Lock Banner Warning */}
                            {isLockedForClient && (
                              <div className="mt-2 text-[11px] bg-rose-950/80 border border-rose-800/80 text-rose-300 p-2 rounded-lg flex items-center gap-1.5">
                                <Lock className="w-3.5 h-3.5 text-rose-400 shrink-0" />
                                Folder Locked: Consent required to unlock document access.
                              </div>
                            )}

                            {/* Assigned Team Members Badge */}
                            <div className="mt-2 text-[11px] flex items-center gap-1.5 text-slate-400">
                              <Users className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
                              <span className="truncate">
                                {eng.assignedTeamMemberIds && eng.assignedTeamMemberIds.length > 0 ? (
                                  <>
                                    Assigned:{" "}
                                    <strong className="text-slate-200">
                                      {eng.assignedTeamMemberIds
                                        .map((uid) => allUsersMap[uid]?.displayName || allUsersMap[uid]?.email || (uid === userProfile.uid ? "You" : "Staff"))
                                        .join(", ")}
                                    </strong>
                                  </>
                                ) : (
                                  <span className="text-slate-500 italic">No team member assigned</span>
                                )}
                              </span>
                            </div>

                            <div className="mt-2 text-[10px] text-slate-500 flex justify-between items-center pt-2 border-t border-slate-800/80">
                              <span>
                                Tenure: {eng.contractStartDate} → {eng.contractEndDate}
                              </span>
                              <span className="text-indigo-400 group-hover:translate-x-0.5 transition-transform">
                                View Folder →
                              </span>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* CREATE NEW ENGAGEMENT MODAL (Full Admin) */}
      {isCreateModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 sm:p-6 overflow-y-auto">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-5 sm:p-6 text-white shadow-2xl my-auto max-h-[90vh] flex flex-col">
            <h3 className="text-lg font-bold text-white border-b border-slate-800 pb-3 flex items-center gap-2 shrink-0">
              <Folder className="w-5 h-5 text-indigo-400" />
              Create Client Sub-Folder (Engagement)
            </h3>

            <form onSubmit={handleCreateEngagement} className="space-y-3.5 text-xs overflow-y-auto pr-1 my-3 flex-1">
              <div>
                <label className="block text-slate-300 font-medium mb-1">Select Top-Level Service Folder</label>
                <select
                  value={selectedServiceForNew}
                  onChange={(e) => setSelectedServiceForNew(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  {services.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Select Client Entity</label>
                <select
                  required
                  value={selectedClientId}
                  onChange={(e) => setSelectedClientId(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="">-- Choose Client --</option>
                  {(Object.values(clients) as Client[]).map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name} ({c.email})
                    </option>
                  ))}
                </select>
              </div>

              {/* TEAM MEMBER ASSIGNMENT SELECTION - Fixed Scrollable Container */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="block text-slate-300 font-medium flex items-center gap-1.5">
                    <Users className="w-3.5 h-3.5 text-indigo-400" />
                    Assign Team Member(s) (Auditors / Staff)
                  </label>
                  {teamMembers.length > 0 && (
                    <div className="flex items-center gap-2 text-[10px]">
                      <button
                        type="button"
                        onClick={() => setSelectedTeamMemberIds(teamMembers.map((t) => t.uid))}
                        className="text-indigo-400 hover:underline"
                      >
                        Select All
                      </button>
                      <span className="text-slate-600">|</span>
                      <button
                        type="button"
                        onClick={() => setSelectedTeamMemberIds([])}
                        className="text-slate-400 hover:underline"
                      >
                        Clear
                      </button>
                    </div>
                  )}
                </div>

                {teamMembers.length === 0 ? (
                  <div className="p-2.5 bg-slate-950 border border-slate-800 rounded-lg text-slate-400 text-[11px]">
                    No team members found with role <code>team_member</code>. The folder will default to current admin.
                  </div>
                ) : (
                  <div className="h-28 overflow-y-auto space-y-1.5 bg-slate-950 border border-slate-800 p-2 rounded-xl custom-scrollbar">
                    {teamMembers.map((tm) => {
                      const isSelected = selectedTeamMemberIds.includes(tm.uid);
                      return (
                        <label
                          key={tm.uid}
                          className={`flex items-center justify-between p-1.5 px-2 rounded-lg border cursor-pointer transition-all text-xs ${
                            isSelected
                              ? "bg-indigo-950/60 border-indigo-700 text-white"
                              : "bg-slate-900/60 border-slate-800 text-slate-300 hover:bg-slate-800"
                          }`}
                        >
                          <div className="flex items-center gap-2">
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={() => {
                                if (isSelected) {
                                  setSelectedTeamMemberIds(selectedTeamMemberIds.filter((id) => id !== tm.uid));
                                } else {
                                  setSelectedTeamMemberIds([...selectedTeamMemberIds, tm.uid]);
                                }
                              }}
                              className="w-3.5 h-3.5 rounded text-indigo-600 bg-slate-900 border-slate-700 focus:ring-0 focus:ring-offset-0 cursor-pointer"
                            />
                            <div className="leading-tight">
                              <span className="font-semibold block text-slate-100 text-xs">{tm.displayName || tm.email}</span>
                              <span className="text-[10px] text-slate-400 font-mono">{tm.email}</span>
                            </div>
                          </div>
                          <span className="text-[9px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700 font-mono">
                            {tm.role}
                          </span>
                        </label>
                      );
                    })}
                  </div>
                )}
                <div className="text-[10px] text-slate-400">
                  {selectedTeamMemberIds.length} of {teamMembers.length} team member(s) selected.
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2.5">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Contract Start Date</label>
                  <input
                    type="date"
                    required
                    value={contractStartDate}
                    onChange={(e) => setContractStartDate(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-white focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-slate-300 font-medium mb-1">Contract End Date</label>
                  <input
                    type="date"
                    required
                    value={contractEndDate}
                    onChange={(e) => setContractEndDate(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-white focus:outline-none"
                  />
                </div>
              </div>

              <div className="p-2.5 bg-indigo-950/40 border border-indigo-900 rounded-xl text-[11px] text-indigo-300 space-y-1">
                <div className="font-semibold text-indigo-200 flex items-center gap-1">
                  <Mail className="w-3.5 h-3.5" /> Single Combined Notice & Setup Email:
                </div>
                <div>
                  Upon creation, a single email containing both the DPDP statutory notice and client login credentials (<code className="text-white font-bold">Client@2026</code>) will be dispatched directly to the client via real SMTP.
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-2 border-t border-slate-800 shrink-0">
                <button
                  type="button"
                  onClick={() => setIsCreateModalOpen(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs"
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  disabled={creating}
                  className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold rounded-lg shadow disabled:opacity-50 flex items-center gap-2 text-xs"
                >
                  {creating ? "Creating & Notifying..." : "Create & Send Combined Email"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
