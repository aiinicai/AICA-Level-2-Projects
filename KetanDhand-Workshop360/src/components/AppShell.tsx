import { useEffect, useState } from "react";
import { Clock, UserX } from "lucide-react";
import type { User } from "@/types";
import { apiFetch, tokenStore, USER_STORAGE_KEY } from "@/lib/api-client";
import { LoginSignup } from "./LoginSignup";
import { MechanicHome } from "./MechanicHome";
import { OwnerDashboard } from "./OwnerDashboard";

function StatusCard({
  tone,
  title,
  children,
  onLogout,
}: {
  tone: "pending" | "denied";
  title: string;
  children: React.ReactNode;
  onLogout: () => void;
}) {
  return (
    <div className="min-h-screen bg-slate-100 flex items-center justify-center p-4">
      <div className="bg-white border border-slate-200 max-w-md w-full p-8 rounded-3xl text-center space-y-4 shadow-xl shadow-slate-900/5">
        <div
          className={`w-16 h-16 rounded-2xl flex items-center justify-center mx-auto ${
            tone === "pending" ? "bg-amber-50 text-amber-600" : "bg-red-50 text-red-600"
          }`}
        >
          {tone === "pending" ? <Clock className="w-8 h-8" /> : <UserX className="w-8 h-8" />}
        </div>
        <h2 className="text-xl font-bold text-slate-900 tracking-tight">{title}</h2>
        <p className="text-slate-600 text-sm leading-relaxed">{children}</p>
        <button
          onClick={onLogout}
          className="w-full py-3 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl font-semibold text-sm transition-colors mt-4 border border-slate-200"
        >
          Sign Out
        </button>
      </div>
    </div>
  );
}

export function AppShell() {
  const [ready, setReady] = useState(false);
  const [currentUser, setCurrentUser] = useState<User | null>(null);

  useEffect(() => {
    const saved = window.localStorage.getItem(USER_STORAGE_KEY);
    if (saved && tokenStore.get()) {
      try {
        setCurrentUser(JSON.parse(saved) as User);
      } catch {
        tokenStore.clear();
      }
    }
    setReady(true);
  }, []);

  useEffect(() => {
    if (currentUser) {
      window.localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(currentUser));
    }
  }, [currentUser]);

  // Refresh the profile (role / approval status) from the database on load.
  useEffect(() => {
    if (!ready || !currentUser) return;
    let cancelled = false;
    (async () => {
      const res = await apiFetch("/api/auth/me");
      if (cancelled) return;
      if (res.status === 401) {
        tokenStore.clear();
        setCurrentUser(null);
        return;
      }
      const data = await res.json();
      if (res.ok && data?.user) setCurrentUser(data.user as User);
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready]);

  const handleLogout = async () => {
    await apiFetch("/api/auth/logout", { method: "POST" });
    tokenStore.clear();
    setCurrentUser(null);
  };

  if (!ready) {
    return <div className="min-h-screen bg-slate-100" />;
  }

  if (!currentUser) {
    return <LoginSignup onLoginSuccess={(user) => setCurrentUser(user)} />;
  }

  if (currentUser.status === "pending") {
    return (
      <StatusCard tone="pending" title="Pending Workshop Approval" onLogout={handleLogout}>
        Hello <strong className="text-slate-900">{currentUser.name}</strong>, your account is waiting for
        approval from the workshop owner. You can start working once it is approved.
      </StatusCard>
    );
  }

  if (currentUser.status === "deactivated" || currentUser.status === "rejected") {
    return (
      <StatusCard tone="denied" title="Access Denied" onLogout={handleLogout}>
        Your account has been {currentUser.status} by the workshop owner. Please contact workshop
        management for assistance.
      </StatusCard>
    );
  }

  if (currentUser.role === "mechanic") {
    return <MechanicHome currentUser={currentUser} onLogout={handleLogout} />;
  }

  return <OwnerDashboard currentUser={currentUser} onLogout={handleLogout} />;
}
