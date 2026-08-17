import React from "react";
import { UserProfile } from "../types";
import { auth } from "../lib/firebase";
import { signOut } from "firebase/auth";
import { Building2, Shield, UserCheck, LogOut, FolderKanban, Users, FileCheck } from "lucide-react";

interface NavbarProps {
  userProfile: UserProfile | null;
  activeTab: "engagements" | "clients" | "audit_log";
  setActiveTab: (tab: "engagements" | "clients" | "audit_log") => void;
}

export const Navbar: React.FC<NavbarProps> = ({ userProfile, activeTab, setActiveTab }) => {
  const handleSignOut = async () => {
    try {
      await signOut(auth);
    } catch (err) {
      console.error("Sign out error:", err);
    }
  };

  const getRoleBadge = (role?: string) => {
    switch (role) {
      case "full_admin":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-purple-100 text-purple-800 border border-purple-200">
            <Shield className="w-3.5 h-3.5 text-purple-600" />
            Full Admin
          </span>
        );
      case "team_member":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-100 text-blue-800 border border-blue-200">
            <UserCheck className="w-3.5 h-3.5 text-blue-600" />
            Team Member
          </span>
        );
      case "client":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">
            <Building2 className="w-3.5 h-3.5 text-emerald-600" />
            Client Account
          </span>
        );
      default:
        return null;
    }
  };

  return (
    <header className="bg-slate-900 text-white border-b border-slate-800 sticky top-0 z-40 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          
          {/* Logo & Brand */}
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-lg bg-indigo-600 flex items-center justify-center font-bold text-white shadow-md">
              ABC
            </div>
            <div>
              <h1 className="text-base font-bold tracking-tight text-white leading-tight">
                ABC & Associates
              </h1>
              <p className="text-xs text-slate-400 font-medium">
                Chartered Accountants — Client Workflow Portal
              </p>
            </div>
          </div>

          {/* Navigation Tabs for Staff/Admin */}
          {userProfile && userProfile.role !== "client" && (
            <nav className="hidden md:flex space-x-1 bg-slate-800/80 p-1 rounded-lg border border-slate-700/60">
              <button
                onClick={() => setActiveTab("engagements")}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                  activeTab === "engagements"
                    ? "bg-indigo-600 text-white shadow-sm"
                    : "text-slate-300 hover:text-white hover:bg-slate-700/50"
                }`}
              >
                <FolderKanban className="w-3.5 h-3.5" />
                Service Folders
              </button>

              {userProfile.role === "full_admin" && (
                <button
                  onClick={() => setActiveTab("clients")}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                    activeTab === "clients"
                      ? "bg-indigo-600 text-white shadow-sm"
                      : "text-slate-300 hover:text-white hover:bg-slate-700/50"
                  }`}
                >
                  <Users className="w-3.5 h-3.5" />
                  Client & Staff Directory
                </button>
              )}

              <button
                onClick={() => setActiveTab("audit_log")}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                  activeTab === "audit_log"
                    ? "bg-indigo-600 text-white shadow-sm"
                    : "text-slate-300 hover:text-white hover:bg-slate-700/50"
                }`}
              >
                <FileCheck className="w-3.5 h-3.5" />
                Consent Audit Log
              </button>
            </nav>
          )}

          {/* User Profile Info & Sign Out */}
          {userProfile && (
            <div className="flex items-center space-x-3">
              <div className="text-right hidden sm:block">
                <div className="text-xs font-semibold text-slate-200">
                  {userProfile.displayName || userProfile.email}
                </div>
                <div className="text-[10px] text-slate-400">
                  {userProfile.email}
                </div>
              </div>

              {getRoleBadge(userProfile.role)}

              <button
                onClick={handleSignOut}
                title="Sign Out"
                className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors border border-transparent hover:border-slate-700"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
