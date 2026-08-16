import React, { useState, useEffect } from "react";
import { db } from "../lib/firebase";
import { doc, onSnapshot, updateDoc, addDoc, collection, serverTimestamp } from "firebase/firestore";
import { Engagement, Client, Service, UserProfile } from "../types";
import { SERVICES_CONFIG } from "../lib/retention";
import { ShieldAlert, CheckCircle, FileText, Lock, Calendar, AlertTriangle, ShieldCheck, ArrowRight, Building2, XCircle } from "lucide-react";

interface ConsentScreenProps {
  engagementIdParam?: string;
  userProfile?: UserProfile | null;
  onConsentGiven?: () => void;
}

export const ConsentScreen: React.FC<ConsentScreenProps> = ({
  engagementIdParam,
  userProfile,
  onConsentGiven
}) => {
  // Extract engagementId from URL or props
  const queryParams = new URLSearchParams(window.location.search);
  const engagementId = engagementIdParam || queryParams.get("engagementId") || "";
  const emailParam = queryParams.get("email") || userProfile?.email || "";

  const [engagement, setEngagement] = useState<Engagement | null>(null);
  const [client, setClient] = useState<Client | null>(null);
  const [service, setService] = useState<Service | null>(null);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);
  const [actionProof, setActionProof] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  // Real-time Firestore Listener on the exact engagement document
  useEffect(() => {
    if (!engagementId) {
      setLoading(false);
      setError("No Engagement ID provided in consent URL link.");
      return;
    }

    setLoading(true);
    const engRef = doc(db, "engagements", engagementId);

    const unsubscribe = onSnapshot(
      engRef,
      async (engSnap) => {
        if (!engSnap.exists()) {
          setError(`Engagement document '${engagementId}' not found in Firestore.`);
          setLoading(false);
          return;
        }

        const engData = { id: engSnap.id, ...engSnap.data() } as Engagement;
        setEngagement(engData);

        // Fetch Client details
        if (engData.clientId) {
          const clientRef = doc(db, "clients", engData.clientId);
          onSnapshot(clientRef, (cSnap) => {
            if (cSnap.exists()) {
              setClient({ id: cSnap.id, ...cSnap.data() } as Client);
            }
          });
        }

        // Fetch Service details
        if (engData.serviceId) {
          const serviceRef = doc(db, "services", engData.serviceId);
          onSnapshot(serviceRef, (sSnap) => {
            if (sSnap.exists()) {
              setService({ id: sSnap.id, ...sSnap.data() } as Service);
            } else {
              // Fallback to static service config
              const cfg = SERVICES_CONFIG[engData.serviceId];
              setService({
                id: engData.serviceId,
                name: cfg?.name || engData.serviceId,
                consentTemplate: {
                  body: "Standard client data processing and engagement consent template.",
                  version: "1.0"
                },
                retentionPolicy: {
                  basis: cfg?.basis || "contract_tenure",
                  years: cfg?.years,
                  statute: cfg?.statute || "Statutory retention policy"
                }
              });
            }
          });
        }

        setLoading(false);
      },
      (err) => {
        console.error("Firestore onSnapshot error:", err);
        setError(`Firestore error: ${err.message}`);
        setLoading(false);
      }
    );

    return () => unsubscribe();
  }, [engagementId]);

  // Handle "I Consent" Click
  const handleGiveConsent = async () => {
    if (!engagement) return;
    setUpdating(true);
    setActionError(null);

    try {
      const engRef = doc(db, "engagements", engagement.id);
      
      // Update consentStatus to "GIVEN"
      await updateDoc(engRef, {
        consentStatus: "GIVEN",
        updatedAt: serverTimestamp()
      });

      // Write to append-only consentLog
      const logData = {
        engagementId: engagement.id,
        clientId: engagement.clientId,
        serviceId: engagement.serviceId,
        serviceName: service?.name || engagement.serviceId,
        action: "GIVEN",
        timestamp: new Date().toISOString(),
        actorUid: userProfile?.uid || "client_auth",
        actorEmail: emailParam || userProfile?.email || "client@domain.com",
        clientEmail: emailParam || client?.email || "",
        notes: `Explicit client consent given for ${service?.name || engagement.serviceId}`
      };

      await addDoc(collection(db, "consentLog"), {
        ...logData,
        timestamp: serverTimestamp()
      });

      setActionProof({
        action: "GIVEN",
        engagementId: engagement.id,
        newConsentStatus: "GIVEN",
        timestamp: new Date().toISOString(),
        clientEmail: emailParam || client?.email,
        erasureDueDate: engagement.erasureDueDate
      });

      if (onConsentGiven) onConsentGiven();
    } catch (err: any) {
      console.error("Error setting consent:", err);
      setActionError(`Failed to update consent status: ${err.message}`);
    } finally {
      setUpdating(false);
    }
  };

  // Handle "Decline Consent" Click
  const handleDeclineConsent = async () => {
    if (!engagement) return;
    setUpdating(true);
    setActionError(null);

    try {
      const engRef = doc(db, "engagements", engagement.id);

      // Update consentStatus to "DECLINED"
      await updateDoc(engRef, {
        consentStatus: "DECLINED",
        updatedAt: serverTimestamp()
      });

      // Write to append-only consentLog
      await addDoc(collection(db, "consentLog"), {
        engagementId: engagement.id,
        clientId: engagement.clientId,
        serviceId: engagement.serviceId,
        serviceName: service?.name || engagement.serviceId,
        action: "DECLINED",
        timestamp: serverTimestamp(),
        actorUid: userProfile?.uid || "client_auth",
        actorEmail: emailParam || userProfile?.email || "client@domain.com",
        clientEmail: emailParam || client?.email || "",
        notes: "Client actively declined engagement data consent."
      });

      setActionProof({
        action: "DECLINED",
        engagementId: engagement.id,
        newConsentStatus: "DECLINED",
        timestamp: new Date().toISOString(),
        clientEmail: emailParam || client?.email
      });
    } catch (err: any) {
      console.error("Error declining consent:", err);
      setActionError(`Failed to decline consent: ${err.message}`);
    } finally {
      setUpdating(false);
    }
  };

  // Handle "Withdraw Consent" Click
  const handleWithdrawConsent = async () => {
    if (!engagement) return;
    setUpdating(true);
    setActionError(null);

    try {
      const engRef = doc(db, "engagements", engagement.id);

      // Update consentStatus to "WITHDRAWN"
      await updateDoc(engRef, {
        consentStatus: "WITHDRAWN",
        updatedAt: serverTimestamp()
      });

      // Write to append-only consentLog
      await addDoc(collection(db, "consentLog"), {
        engagementId: engagement.id,
        clientId: engagement.clientId,
        serviceId: engagement.serviceId,
        serviceName: service?.name || engagement.serviceId,
        action: "WITHDRAWN",
        timestamp: serverTimestamp(),
        actorUid: userProfile?.uid || "client_auth",
        actorEmail: emailParam || userProfile?.email || "client@domain.com",
        clientEmail: emailParam || client?.email || "",
        notes: "Client explicitly withdrew engagement data consent."
      });

      setActionProof({
        action: "WITHDRAWN",
        engagementId: engagement.id,
        newConsentStatus: "WITHDRAWN",
        timestamp: new Date().toISOString(),
        clientEmail: emailParam || client?.email
      });
    } catch (err: any) {
      console.error("Error withdrawing consent:", err);
      setActionError(`Failed to withdraw consent: ${err.message}`);
    } finally {
      setUpdating(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center p-8 text-slate-300">
        <div className="flex items-center gap-3">
          <div className="w-5 h-5 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-sm font-medium">Loading engagement consent record...</span>
        </div>
      </div>
    );
  }

  if (error || !engagement) {
    return (
      <div className="max-w-2xl mx-auto my-12 p-6 bg-slate-900 border border-slate-800 rounded-2xl shadow-xl text-white space-y-4">
        <div className="flex items-center gap-3 text-rose-400 font-bold text-lg border-b border-slate-800 pb-3">
          <AlertTriangle className="w-6 h-6" />
          Consent Record Unreachable
        </div>
        <p className="text-slate-300 text-sm leading-relaxed">{error}</p>
        <p className="text-xs text-slate-500">
          Please make sure you clicked the exact engagement consent link sent to your registered client email address.
        </p>
      </div>
    );
  }

  const serviceConfig = SERVICES_CONFIG[engagement.serviceId];

  return (
    <div className="max-w-3xl mx-auto my-8 px-4 sm:px-6">
      <div className="bg-slate-900 border border-slate-800 rounded-3xl shadow-2xl overflow-hidden text-white">
        
        {/* Header */}
        <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 p-6 sm:p-8 border-b border-slate-800">
          <div className="flex items-center justify-between mb-4">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-indigo-900/60 text-indigo-300 border border-indigo-700/60">
              <ShieldCheck className="w-3.5 h-3.5 text-indigo-400" />
              Official Engagement Consent Form
            </div>
            
            <span className={`px-3 py-1 rounded-full text-xs font-bold border ${
              engagement.consentStatus === "GIVEN"
                ? "bg-emerald-950/80 text-emerald-300 border-emerald-800"
                : engagement.consentStatus === "WITHDRAWN"
                ? "bg-rose-950/80 text-rose-300 border-rose-800"
                : "bg-amber-950/80 text-amber-300 border-amber-800"
            }`}>
              Consent Status: {engagement.consentStatus}
            </span>
          </div>

          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white mb-2">
            {service?.name || serviceConfig?.name || engagement.serviceId}
          </h1>

          <p className="text-slate-400 text-sm flex items-center gap-2">
            <Building2 className="w-4 h-4 text-slate-500" />
            Client Entity: <strong className="text-slate-200">{client?.name || "Client Enterprise"}</strong> ({client?.entityType === "company" ? "Company Entity" : "Non-Company Entity"})
          </p>
        </div>

        <div className="p-6 sm:p-8 space-y-6">
          
          {/* Statutory Retention & Erasure Due Date Display */}
          <div className="bg-slate-800/80 border border-slate-700 rounded-2xl p-5 space-y-3">
            <div className="flex items-center justify-between border-b border-slate-700/80 pb-3">
              <span className="text-xs font-semibold uppercase tracking-wider text-indigo-400 flex items-center gap-1.5">
                <Calendar className="w-4 h-4" />
                Statutory Retention & Data Governance
              </span>
              <span className="text-xs bg-slate-700 text-slate-300 px-2.5 py-0.5 rounded font-mono">
                Basis: {serviceConfig?.basis || "statutory"}
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              <div>
                <span className="text-slate-400 block mb-0.5">Statutory Standard / Statute:</span>
                <span className="text-slate-200 font-medium">{serviceConfig?.statute || "Applicable Law"}</span>
              </div>

              <div>
                <span className="text-slate-400 block mb-0.5">Engagement Contract Tenure:</span>
                <span className="text-slate-200 font-medium">
                  {engagement.contractStartDate} to {engagement.contractEndDate}
                </span>
              </div>
            </div>

            {/* Calculated Erasure Due Date Prominently Displayed */}
            <div className="mt-3 p-3.5 bg-indigo-950/50 border border-indigo-800/80 rounded-xl flex items-center justify-between">
              <div>
                <div className="text-[11px] font-semibold text-indigo-300 uppercase tracking-wide">
                  Calculated Explicit Erasure Due Date
                </div>
                <div className="text-lg font-bold text-white font-mono mt-0.5">
                  {engagement.erasureDueDate}
                </div>
              </div>
              <div className="text-right text-[11px] text-slate-400 max-w-[200px]">
                Data retained until tenure + statutory period + 60 days buffer.
              </div>
            </div>
          </div>

          {/* DPDP Statutory Notice Body */}
          <div className="space-y-2">
            <label className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
              <FileText className="w-4 h-4 text-indigo-400" />
              DPDP Statutory Notice & Processing Purpose
            </label>
            <div className="p-5 bg-slate-950 border border-slate-800 rounded-2xl text-xs sm:text-sm text-slate-200 leading-relaxed whitespace-pre-line font-sans border-l-4 border-l-indigo-500 shadow-inner">
              {service?.consentTemplate?.body || "Standard client authorization and data processing consent template text for ABC & Associates Chartered Accountants."}
            </div>
          </div>

          {/* Error Message Display if Consent Action Fails */}
          {actionError && (
            <div className="p-4 bg-rose-950/90 border border-rose-700 rounded-2xl text-xs text-rose-200 flex items-start gap-3 shadow-lg animate-in fade-in">
              <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
              <div>
                <strong className="block text-rose-300 font-bold mb-0.5">Consent Action Failed</strong>
                <span>{actionError}</span>
              </div>
            </div>
          )}

          {/* Action proof banner */}
          {actionProof && (
            <div className="p-4 bg-emerald-950/90 border border-emerald-700 rounded-2xl text-xs text-emerald-200 space-y-2">
              <div className="font-bold flex items-center gap-2 text-emerald-300 text-sm">
                <CheckCircle className="w-4 h-4 text-emerald-400" />
                Firestore Document Updated Successfully!
              </div>
              <pre className="bg-slate-950 p-2.5 rounded-lg text-[11px] text-emerald-400 font-mono overflow-x-auto">
                {JSON.stringify(actionProof, null, 2)}
              </pre>
            </div>
          )}

          {/* Interactive Consent Action Buttons */}
          <div className="pt-2 border-t border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-4">
            
            {engagement.consentStatus === "GIVEN" ? (
              <div className="w-full flex flex-col sm:flex-row items-center justify-between gap-3 bg-emerald-950/40 p-4 border border-emerald-800/60 rounded-2xl">
                <div className="flex items-center gap-2.5 text-xs text-emerald-200">
                  <ShieldCheck className="w-5 h-5 text-emerald-400 shrink-0" />
                  <span>
                    <strong>Consent Granted.</strong> Your folder is unlocked and active.
                  </span>
                </div>

                <button
                  type="button"
                  disabled={updating}
                  onClick={handleWithdrawConsent}
                  className="w-full sm:w-auto px-4 py-2 bg-rose-600 hover:bg-rose-500 text-white font-semibold text-xs rounded-xl shadow transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
                >
                  <Lock className="w-3.5 h-3.5" />
                  {updating ? "Processing..." : "Withdraw Consent"}
                </button>
              </div>
            ) : (
              <div className="w-full flex flex-col sm:flex-row items-center justify-between gap-4">
                <p className="text-xs text-slate-400 max-w-md">
                  Clicking "I Consent" authorizes ABC & Associates to process document workflows under this engagement.
                </p>

                <div className="flex items-center gap-3 w-full sm:w-auto shrink-0">
                  <button
                    type="button"
                    disabled={updating}
                    onClick={handleDeclineConsent}
                    className="flex-1 sm:flex-none px-4 py-3 bg-slate-800 hover:bg-rose-950/80 text-rose-300 hover:text-rose-200 border border-slate-700 hover:border-rose-700 font-bold text-xs rounded-xl transition-all flex items-center justify-center gap-2 disabled:opacity-50"
                  >
                    <XCircle className="w-4 h-4 text-rose-400" />
                    {updating ? "Updating..." : "Decline"}
                  </button>

                  <button
                    type="button"
                    disabled={updating}
                    onClick={handleGiveConsent}
                    className="flex-1 sm:flex-none px-6 py-3 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-sm rounded-xl shadow-lg transition-all flex items-center justify-center gap-2 disabled:opacity-50 shrink-0"
                  >
                    <ShieldCheck className="w-4 h-4" />
                    {updating ? "Updating Firestore..." : "I Consent"}
                  </button>
                </div>
              </div>
            )}

          </div>

        </div>
      </div>
    </div>
  );
};
