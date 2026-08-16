import React, { useState, useEffect } from "react";
import { auth, db } from "./lib/firebase";
import { onAuthStateChanged } from "firebase/auth";
import { doc, onSnapshot } from "firebase/firestore";
import { UserProfile } from "./types";
import { Navbar } from "./components/Navbar";
import { LoginScreen } from "./components/LoginScreen";
import { ServiceFolderList } from "./components/ServiceFolderList";
import { EngagementDetailView } from "./components/EngagementDetailView";
import { AdminClientManagement } from "./components/AdminClientManagement";
import { ConsentLogAuditView } from "./components/ConsentLogAuditView";
import { ConsentScreen } from "./components/ConsentScreen";
import { ShieldAlert, AlertTriangle } from "lucide-react";

export default function App() {
  const [user, setUser] = useState<any | null>(null);
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
  const [authLoading, setAuthLoading] = useState(true);
  
  // Navigation & View States
  const [activeTab, setActiveTab] = useState<"engagements" | "clients" | "audit_log">("engagements");
  const [selectedEngagementId, setSelectedEngagementId] = useState<string | null>(null);

  // Check if current URL is consent route or has engagementId parameter
  const pathname = window.location.pathname;
  const isConsentRoute = pathname === "/consent" || new URLSearchParams(window.location.search).has("engagementId");

  // 1. Initial Database Bootstrap Trigger
  useEffect(() => {
    fetch("/api/bootstrap", { method: "POST" })
      .then((res) => res.json())
      .then((data) => console.log("[Bootstrap Result]", data))
      .catch((err) => console.error("[Bootstrap Fetch Error]", err));
  }, []);

  // 2. Real-Time Auth State Listener & User Profile Fetch
  useEffect(() => {
    const unsubscribeAuth = onAuthStateChanged(auth, async (currentUser) => {
      setUser(currentUser);

      if (!currentUser) {
        setUserProfile(null);
        setAuthLoading(false);
        return;
      }

      // Fetch user profile from Firestore /users/{uid}
      const userRef = doc(db, "users", currentUser.uid);
      const unsubProfile = onSnapshot(
        userRef,
        (snap) => {
          if (snap.exists()) {
            const data = snap.data();
            setUserProfile({
              uid: currentUser.uid,
              email: currentUser.email || "",
              role: data.role || "client",
              linkedClientId: data.linkedClientId,
              isActive: data.isActive !== false,
              displayName: data.displayName || currentUser.displayName || currentUser.email
            });
          } else {
            // Default user profile if doc not created yet
            setUserProfile({
              uid: currentUser.uid,
              email: currentUser.email || "",
              role: "client",
              isActive: true,
              displayName: currentUser.displayName || currentUser.email
            });
          }
          setAuthLoading(false);
        },
        (err) => {
          console.error("User profile snapshot error:", err);
          setAuthLoading(false);
        }
      );

      return () => unsubProfile();
    });

    return () => unsubscribeAuth();
  }, []);

  if (authLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center text-white">
        <div className="flex items-center gap-3">
          <div className="w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-sm font-semibold tracking-wide">Authenticating ABC Portal Session...</span>
        </div>
      </div>
    );
  }

  // Deactivated Account Check
  if (userProfile && !userProfile.isActive) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-slate-900 border border-rose-900 rounded-2xl p-6 text-center text-white space-y-4 shadow-2xl">
          <div className="w-12 h-12 bg-rose-950/80 rounded-xl border border-rose-800 flex items-center justify-center mx-auto text-rose-400">
            <ShieldAlert className="w-6 h-6" />
          </div>
          <h2 className="text-xl font-bold">Account Deactivated</h2>
          <p className="text-xs text-slate-300">
            Your user account ({userProfile.email}) has been deactivated by the Senior Partner. Access to firm client records is restricted.
          </p>
          <button
            onClick={() => auth.signOut()}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-xs font-semibold rounded-xl"
          >
            Sign Out
          </button>
        </div>
      </div>
    );
  }

  // Route 1: Consent Direct Link Route
  if (isConsentRoute) {
    return (
      <div className="min-h-screen bg-slate-950 text-white">
        <header className="bg-slate-900 border-b border-slate-800 py-4 px-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center font-bold text-white text-sm">
              ABC
            </div>
            <div>
              <div className="font-bold text-sm text-white">ABC & Associates</div>
              <div className="text-[10px] text-slate-400">Chartered Accountants — Consent Authorization</div>
            </div>
          </div>

          {userProfile && (
            <button
              onClick={() => window.location.href = "/"}
              className="px-3 py-1.5 bg-slate-800 text-slate-300 text-xs font-semibold rounded-lg border border-slate-700 hover:text-white"
            >
              Go to Main Dashboard →
            </button>
          )}
        </header>

        <ConsentScreen userProfile={userProfile} />
      </div>
    );
  }

  // Route 2: Signed-Out View (Login Screen)
  if (!user || !userProfile) {
    return <LoginScreen />;
  }

  // Route 3: Signed-In Main Portal Layout
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      
      {/* Top Navbar */}
      <Navbar
        userProfile={userProfile}
        activeTab={activeTab}
        setActiveTab={(tab) => {
          setActiveTab(tab);
          setSelectedEngagementId(null);
        }}
      />

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        
        {/* VIEW 1: SERVICE FOLDERS & ENGAGEMENTS */}
        {activeTab === "engagements" && (
          <>
            {selectedEngagementId ? (
              <EngagementDetailView
                engagementId={selectedEngagementId}
                userProfile={userProfile}
                onBack={() => setSelectedEngagementId(null)}
              />
            ) : (
              <ServiceFolderList
                userProfile={userProfile}
                onSelectEngagement={(id) => setSelectedEngagementId(id)}
              />
            )}
          </>
        )}

        {/* VIEW 2: CLIENT & STAFF DIRECTORY (Full Admin) */}
        {activeTab === "clients" && userProfile.role === "full_admin" && (
          <AdminClientManagement userProfile={userProfile} />
        )}

        {/* VIEW 3: AUDIT CONSENT LOG */}
        {activeTab === "audit_log" && (
          <ConsentLogAuditView userProfile={userProfile} />
        )}

      </main>

      {/* Footer */}
      <footer className="bg-slate-900/60 border-t border-slate-800/80 py-4 text-center text-xs text-slate-500">
        ABC & Associates | Chartered Accountants — Client Workflow & Consent Portal
      </footer>

    </div>
  );
}
