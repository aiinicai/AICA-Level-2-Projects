import React, { useState, useEffect } from "react";
import { db } from "../lib/firebase";
import { collection, onSnapshot, addDoc, serverTimestamp, doc, updateDoc } from "firebase/firestore";
import { Client, EntityType, UserProfile } from "../types";
import { Building2, Plus, Users, UserPlus, Mail, Phone, ShieldCheck, CheckCircle2 } from "lucide-react";

interface AdminClientManagementProps {
  userProfile: UserProfile;
}

export const AdminClientManagement: React.FC<AdminClientManagementProps> = ({ userProfile }) => {
  const [clients, setClients] = useState<Client[]>([]);
  const [usersList, setUsersList] = useState<UserProfile[]>([]);
  
  // New Client Form
  const [isClientModalOpen, setIsClientModalOpen] = useState(false);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [entityType, setEntityType] = useState<EntityType>("company");
  const [creatingClient, setCreatingClient] = useState(false);
  const [clientProof, setClientProof] = useState<any | null>(null);

  // New Team Member Form
  const [isStaffModalOpen, setIsStaffModalOpen] = useState(false);
  const [staffEmail, setStaffEmail] = useState("");
  const [staffPassword, setStaffPassword] = useState("Audit@123456");
  const [staffName, setStaffName] = useState("");
  const [creatingStaff, setCreatingStaff] = useState(false);
  const [staffProof, setStaffProof] = useState<any | null>(null);

  // Real-time clients listener
  useEffect(() => {
    const unsubClients = onSnapshot(collection(db, "clients"), (snap) => {
      const list: Client[] = [];
      snap.forEach((docSnap) => {
        list.push({ id: docSnap.id, ...docSnap.data() } as Client);
      });
      setClients(list);
    });

    return () => unsubClients();
  }, []);

  // Real-time users listener
  useEffect(() => {
    const unsubUsers = onSnapshot(collection(db, "users"), (snap) => {
      const list: UserProfile[] = [];
      snap.forEach((docSnap) => {
        list.push({ uid: docSnap.id, ...docSnap.data() } as UserProfile);
      });
      setUsersList(list);
    });

    return () => unsubUsers();
  }, []);

  // Handle Add Client
  const handleAddClient = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreatingClient(true);
    setClientProof(null);

    try {
      const clientData = {
        name: name.trim(),
        email: email.trim(),
        phone: phone.trim(),
        entityType,
        isActive: true,
        createdAt: serverTimestamp()
      };

      const docRef = await addDoc(collection(db, "clients"), clientData);

      // Create associated client user in auth via backend API
      const userResp = await fetch("/api/admin/create-user", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: email.trim(),
          role: "client",
          displayName: name.trim(),
          linkedClientId: docRef.id
        })
      });

      const userData = await userResp.json();

      setClientProof({
        clientId: docRef.id,
        name: name.trim(),
        email: email.trim(),
        entityType,
        userAccountCreated: userData.success,
        userUid: userData.uid
      });

      setName("");
      setEmail("");
      setPhone("");
      setIsClientModalOpen(false);
    } catch (err: any) {
      console.error("Add client error:", err);
      alert(`Failed to add client: ${err.message}`);
    } finally {
      setCreatingClient(false);
    }
  };

  // Handle Add Staff Team Member
  const handleAddStaff = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreatingStaff(true);
    setStaffProof(null);

    try {
      const resp = await fetch("/api/admin/create-user", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: staffEmail.trim(),
          password: staffPassword,
          role: "team_member",
          displayName: staffName.trim()
        })
      });

      const data = await resp.json();
      if (!data.success) throw new Error(data.error);

      setStaffProof({
        uid: data.uid,
        email: staffEmail.trim(),
        role: "team_member",
        displayName: staffName.trim()
      });

      setStaffEmail("");
      setStaffName("");
      setIsStaffModalOpen(false);
    } catch (err: any) {
      console.error("Add staff error:", err);
      alert(`Failed to add staff: ${err.message}`);
    } finally {
      setCreatingStaff(false);
    }
  };

  return (
    <div className="space-y-8">
      
      {/* Proof Banners */}
      {clientProof && (
        <div className="p-4 bg-emerald-950/80 border border-emerald-800 rounded-2xl text-xs text-emerald-200 space-y-1">
          <div className="font-bold text-emerald-300 flex items-center justify-between">
            <span>Client & Client User Account Provisioned in Firestore & Auth!</span>
            <button onClick={() => setClientProof(null)} className="text-emerald-400 hover:underline">Dismiss</button>
          </div>
          <pre className="bg-slate-950 p-2 rounded text-[11px] font-mono text-emerald-400 overflow-x-auto">
            {JSON.stringify(clientProof, null, 2)}
          </pre>
        </div>
      )}

      {staffProof && (
        <div className="p-4 bg-blue-950/80 border border-blue-800 rounded-2xl text-xs text-blue-200 space-y-1">
          <div className="font-bold text-blue-300 flex items-center justify-between">
            <span>Staff Team Member Provisioned in Auth & Firestore!</span>
            <button onClick={() => setStaffProof(null)} className="text-blue-400 hover:underline">Dismiss</button>
          </div>
          <pre className="bg-slate-950 p-2 rounded text-[11px] font-mono text-blue-400 overflow-x-auto">
            {JSON.stringify(staffProof, null, 2)}
          </pre>
        </div>
      )}

      {/* SECTION 1: CLIENT ENTITY DIRECTORY */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl text-white space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
          <div>
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <Building2 className="w-5 h-5 text-indigo-400" />
              Client Entity Directory
            </h3>
            <p className="text-xs text-slate-400">
              Manage client organizations, emails, and mandatory internal audit entity classifications
            </p>
          </div>

          <button
            onClick={() => setIsClientModalOpen(true)}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs rounded-xl shadow flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            Add New Client Entity
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {clients.map((c) => (
            <div key={c.id} className="p-4 bg-slate-950/80 border border-slate-800 rounded-xl space-y-2">
              <div className="flex items-center justify-between">
                <h4 className="font-bold text-sm text-white">{c.name}</h4>
                <span className={`px-2 py-0.5 rounded text-[10px] font-mono ${
                  c.entityType === "company" ? "bg-indigo-950 text-indigo-300 border border-indigo-800" : "bg-slate-800 text-slate-300"
                }`}>
                  {c.entityType === "company" ? "Company (s.138 Audit)" : "Non-Company Entity"}
                </span>
              </div>

              <div className="text-xs text-slate-400 space-y-1">
                <div className="flex items-center gap-2">
                  <Mail className="w-3.5 h-3.5 text-slate-500" />
                  <span>{c.email}</span>
                </div>
                {c.phone && (
                  <div className="flex items-center gap-2">
                    <Phone className="w-3.5 h-3.5 text-slate-500" />
                    <span>{c.phone}</span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* SECTION 2: STAFF & USERS DIRECTORY */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl text-white space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
          <div>
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <Users className="w-5 h-5 text-indigo-400" />
              Staff & User Accounts Directory
            </h3>
            <p className="text-xs text-slate-400">
              Active role assignments (`full_admin`, `team_member`, `client`)
            </p>
          </div>

          <button
            onClick={() => setIsStaffModalOpen(true)}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs rounded-xl shadow flex items-center gap-2"
          >
            <UserPlus className="w-4 h-4" />
            Add Staff Team Member
          </button>
        </div>

        <div className="space-y-2">
          {usersList.map((u) => (
            <div key={u.uid} className="p-3 bg-slate-950/80 border border-slate-800 rounded-xl flex items-center justify-between text-xs">
              <div>
                <div className="font-bold text-white">{u.displayName || u.email}</div>
                <div className="text-[10px] text-slate-400 font-mono">{u.email} • UID: {u.uid.slice(0, 10)}...</div>
              </div>

              <span className={`px-2.5 py-1 rounded-full text-[10px] font-bold border ${
                u.role === "full_admin"
                  ? "bg-purple-950 text-purple-300 border-purple-800"
                  : u.role === "team_member"
                  ? "bg-blue-950 text-blue-300 border-blue-800"
                  : "bg-emerald-950 text-emerald-300 border-emerald-800"
              }`}>
                Role: {u.role}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* ADD CLIENT MODAL */}
      {isClientModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 text-white space-y-4 shadow-2xl">
            <h3 className="text-lg font-bold border-b border-slate-800 pb-3">Add Client Entity</h3>
            <form onSubmit={handleAddClient} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-300 mb-1 font-medium">Client Organization Name</label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Apex Global Private Limited"
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-white focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-slate-300 mb-1 font-medium">Official Client Email Address</label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="finance@apexglobal.com"
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-white focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-slate-300 mb-1 font-medium">Contact Phone Number</label>
                <input
                  type="text"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="+91 98765 00000"
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-white focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-slate-300 mb-1 font-medium">Entity Type (Mandatory Internal Audit Rule)</label>
                <select
                  value={entityType}
                  onChange={(e) => setEntityType(e.target.value as EntityType)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-white focus:outline-none"
                >
                  <option value="company">Company Entity (Mandatory Internal Audit: 8 Years)</option>
                  <option value="non_company">Non-Company Entity (LLP/Firm: 7 Years)</option>
                </select>
              </div>

              <div className="flex justify-end gap-3 pt-3">
                <button
                  type="button"
                  onClick={() => setIsClientModalOpen(false)}
                  className="px-4 py-2 bg-slate-800 text-slate-300 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creatingClient}
                  className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold rounded-lg shadow"
                >
                  {creatingClient ? "Provisioning..." : "Provision Client Entity"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ADD STAFF MODAL */}
      {isStaffModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 text-white space-y-4 shadow-2xl">
            <h3 className="text-lg font-bold border-b border-slate-800 pb-3">Add Staff Team Member</h3>
            <form onSubmit={handleAddStaff} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-300 mb-1 font-medium">Full Name / Display Title</label>
                <input
                  type="text"
                  required
                  value={staffName}
                  onChange={(e) => setStaffName(e.target.value)}
                  placeholder="Audit Manager (Tax Dept)"
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-white focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-slate-300 mb-1 font-medium">Staff Email Address</label>
                <input
                  type="email"
                  required
                  value={staffEmail}
                  onChange={(e) => setStaffEmail(e.target.value)}
                  placeholder="manager@abc-associates.com"
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-white focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-slate-300 mb-1 font-medium">Initial Password</label>
                <input
                  type="password"
                  required
                  value={staffPassword}
                  onChange={(e) => setStaffPassword(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-white focus:outline-none"
                />
              </div>

              <div className="flex justify-end gap-3 pt-3">
                <button
                  type="button"
                  onClick={() => setIsStaffModalOpen(false)}
                  className="px-4 py-2 bg-slate-800 text-slate-300 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creatingStaff}
                  className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold rounded-lg shadow"
                >
                  {creatingStaff ? "Creating..." : "Provision Staff Member"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
};
