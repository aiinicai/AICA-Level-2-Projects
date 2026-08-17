import React, { useState, useEffect } from "react";
import { db } from "../lib/firebase";
import { collection, onSnapshot, query, orderBy } from "firebase/firestore";
import { ConsentLogEntry, UserProfile } from "../types";
import { FileCheck, ShieldCheck, Send, Lock, Unlock, AlertOctagon, XCircle, Clock } from "lucide-react";

interface ConsentLogAuditViewProps {
  userProfile: UserProfile;
}

export const ConsentLogAuditView: React.FC<ConsentLogAuditViewProps> = ({ userProfile }) => {
  const [logs, setLogs] = useState<ConsentLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [assignedEngIds, setAssignedEngIds] = useState<string[]>([]);
  const [assignedClientEmails, setAssignedClientEmails] = useState<string[]>([]);

  // 1. If team_member, listen to assigned engagements to build whitelist of engagementIds and clientEmails
  useEffect(() => {
    if (!userProfile) return;

    if (userProfile.role === "team_member") {
      const unsub = onSnapshot(collection(db, "engagements"), async (snap) => {
        const engIds: string[] = [];
        const clientIds: string[] = [];

        snap.forEach((d) => {
          const data = d.data();
          if (data.assignedTeamMemberIds && data.assignedTeamMemberIds.includes(userProfile.uid)) {
            engIds.push(d.id);
            if (data.clientId) clientIds.push(data.clientId);
          }
        });

        setAssignedEngIds(engIds);

        // Fetch client emails
        if (clientIds.length > 0) {
          const cUnsub = onSnapshot(collection(db, "clients"), (cSnap) => {
            const emails: string[] = [];
            cSnap.forEach((cDoc) => {
              if (clientIds.includes(cDoc.id)) {
                const cData = cDoc.data();
                if (cData.email) emails.push(cData.email.toLowerCase());
              }
            });
            setAssignedClientEmails(emails);
          });
          return () => cUnsub();
        } else {
          setAssignedClientEmails([]);
        }
      });

      return () => unsub();
    }
  }, [userProfile?.uid, userProfile?.role]);

  // 2. Fetch and filter consent logs
  useEffect(() => {
    setLoading(true);
    const q = query(collection(db, "consentLog"), orderBy("timestamp", "desc"));

    const unsub = onSnapshot(
      q,
      (snap) => {
        const rawList: ConsentLogEntry[] = [];
        snap.forEach((docSnap) => {
          rawList.push({ id: docSnap.id, ...docSnap.data() } as ConsentLogEntry);
        });

        // Scope logs according to user role
        let filteredList: ConsentLogEntry[] = [];
        if (userProfile.role === "full_admin") {
          filteredList = rawList;
        } else if (userProfile.role === "team_member") {
          filteredList = rawList.filter((log) => {
            if (log.engagementId && assignedEngIds.includes(log.engagementId)) return true;
            if (log.clientEmail && assignedClientEmails.includes(log.clientEmail.toLowerCase())) return true;
            return false;
          });
        } else if (userProfile.role === "client") {
          filteredList = rawList.filter((log) => {
            if (userProfile.email && log.clientEmail && log.clientEmail.toLowerCase() === userProfile.email.toLowerCase()) return true;
            if (userProfile.linkedClientId && log.engagementId) return true;
            return false;
          });
        }

        setLogs(filteredList);
        setLoading(false);
      },
      (err) => {
        console.error("ConsentLog snapshot error:", err);
        setLoading(false);
      }
    );

    return () => unsub();
  }, [userProfile?.role, userProfile?.uid, userProfile?.email, userProfile?.linkedClientId, assignedEngIds, assignedClientEmails]);

  const getActionBadge = (action: string) => {
    switch (action) {
      case "GIVEN":
        return (
          <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-950 text-emerald-300 border border-emerald-800 flex items-center gap-1.5 w-fit">
            <Unlock className="w-3.5 h-3.5 text-emerald-400" /> GIVEN (Client Grant)
          </span>
        );
      case "WITHDRAWN":
        return (
          <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-orange-950 text-orange-300 border border-orange-800 flex items-center gap-1.5 w-fit">
            <Lock className="w-3.5 h-3.5 text-orange-400" /> WITHDRAWN (Client Action)
          </span>
        );
      case "DECLINED":
        return (
          <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-rose-950 text-rose-300 border border-rose-800 flex items-center gap-1.5 w-fit">
            <XCircle className="w-3.5 h-3.5 text-rose-400" /> DECLINED (Client Refusal)
          </span>
        );
      case "SENT":
        return (
          <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-sky-950 text-sky-300 border border-sky-800 flex items-center gap-1.5 w-fit">
            <Send className="w-3.5 h-3.5 text-sky-400" /> SENT (Notice Dispatched)
          </span>
        );
      case "SEND_FAILED":
        return (
          <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-rose-950 text-rose-300 border border-rose-700/80 flex items-center gap-1.5 w-fit">
            <AlertOctagon className="w-3.5 h-3.5 text-rose-400" /> SEND_FAILED (System / SMTP)
          </span>
        );
      default:
        return (
          <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-slate-800 text-slate-300 border border-slate-700 flex items-center gap-1.5 w-fit">
            <Clock className="w-3.5 h-3.5 text-slate-400" /> {action || "UNKNOWN"}
          </span>
        );
    }
  };

  const formatTimestamp = (ts: any) => {
    if (!ts) return "Just now";
    if (ts.toDate) return ts.toDate().toLocaleString();
    if (typeof ts === "string") return new Date(ts).toLocaleString();
    if (ts.seconds) return new Date(ts.seconds * 1000).toLocaleString();
    return String(ts);
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl text-white space-y-6">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <div className="text-xs font-semibold text-indigo-400 uppercase tracking-wider mb-1 flex items-center gap-1.5">
            <ShieldCheck className="w-4 h-4" />
            Immutable Audit Compliance Trail
          </div>
          <h2 className="text-2xl font-extrabold text-white flex items-center gap-2">
            <FileCheck className="w-6 h-6 text-indigo-500" />
            Consent Log Audit Register
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Append-only record of all client consent dispatches, system delivery events, explicit client grants, and consent withdrawals
          </p>
        </div>

        <div className="px-3 py-1.5 bg-slate-950 rounded-xl border border-slate-800 text-xs font-mono text-slate-300">
          Total Log Entries: <strong className="text-indigo-400">{logs.length}</strong>
        </div>
      </div>

      {loading ? (
        <div className="text-center py-12 text-slate-400 text-xs">Loading immutable audit log...</div>
      ) : logs.length === 0 ? (
        <div className="text-center py-12 text-xs text-slate-500 border border-dashed border-slate-800 rounded-xl">
          No consent log events recorded yet.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-950 text-slate-400 uppercase tracking-wider text-[10px] font-bold border-b border-slate-800">
              <tr>
                <th className="p-3">Timestamp</th>
                <th className="p-3">Action Type</th>
                <th className="p-3">Service Name</th>
                <th className="p-3">Client Email</th>
                <th className="p-3">Actor / Origin</th>
                <th className="p-3">Audit Details & Notes</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80 font-mono text-[11px]">
              {logs.map((log) => (
                <tr key={log.id} className="hover:bg-slate-800/40 transition-colors">
                  <td className="p-3 text-slate-400 whitespace-nowrap">
                    {formatTimestamp(log.timestamp)}
                  </td>
                  <td className="p-3">
                    {getActionBadge(log.action)}
                  </td>
                  <td className="p-3 text-white font-sans font-bold">
                    {log.serviceName || log.serviceId || "Statutory Audit"}
                  </td>
                  <td className="p-3 text-indigo-300">
                    {log.clientEmail || "client@domain.com"}
                  </td>
                  <td className="p-3 text-slate-400">
                    {log.actorEmail}
                  </td>
                  <td className="p-3 text-slate-300 font-sans max-w-md">
                    {log.notes || "N/A"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

    </div>
  );
};

