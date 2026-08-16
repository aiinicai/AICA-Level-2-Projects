import React, { useState } from "react";
import { auth } from "../lib/firebase";
import { signInWithEmailAndPassword, sendPasswordResetEmail } from "firebase/auth";
import { Lock, Mail, KeyRound, ArrowRight, ShieldCheck, CheckCircle2, AlertCircle, Building2 } from "lucide-react";

interface LoginScreenProps {
  onSuccess?: () => void;
}

export const LoginScreen: React.FC<LoginScreenProps> = ({ onSuccess }) => {
  const [activeTab, setActiveTab] = useState<"staff" | "client">("staff");

  // Staff login state
  const [staffEmail, setStaffEmail] = useState("");
  const [staffPassword, setStaffPassword] = useState("");

  // Client login state
  const [clientEmail, setClientEmail] = useState("");
  const [clientPassword, setClientPassword] = useState("Client@2026");

  // Common UI state
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  // Handle Staff Email + Password Sign In
  const handleStaffLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setMessage(null);
    setLoading(true);

    try {
      await signInWithEmailAndPassword(auth, staffEmail.trim(), staffPassword);
      if (onSuccess) onSuccess();
    } catch (err: any) {
      console.error("Staff login error:", err);
      if (
        err.code === "auth/invalid-credential" ||
        err.code === "auth/user-not-found" ||
        err.code === "auth/wrong-password" ||
        err.code === "auth/invalid-login-credentials"
      ) {
        setError("Invalid staff email or password. Please verify credentials.");
      } else {
        setError(err.message || "Failed to sign in as staff.");
      }
    } finally {
      setLoading(false);
    }
  };

  // Handle Client Email + Password Sign In
  const handleClientLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setMessage(null);
    setLoading(true);

    const email = clientEmail.trim();
    const pass = clientPassword.trim();

    if (!email) {
      setError("Please enter your client email address.");
      setLoading(false);
      return;
    }

    if (!pass) {
      setError("Please enter your password.");
      setLoading(false);
      return;
    }

    try {
      await signInWithEmailAndPassword(auth, email, pass);
      if (onSuccess) onSuccess();
    } catch (err: any) {
      console.error("Client login error:", err);
      if (
        err.code === "auth/invalid-credential" ||
        err.code === "auth/user-not-found" ||
        err.code === "auth/wrong-password" ||
        err.code === "auth/invalid-login-credentials"
      ) {
        setError("Invalid client email or password. Default demo password is Client@2026");
      } else {
        setError(err.message || "Failed to sign in to client portal.");
      }
    } finally {
      setLoading(false);
    }
  };

  // Handle Staff Password Reset
  const handleForgotPassword = async (targetEmail: string) => {
    if (!targetEmail.trim()) {
      setError("Please enter your email address first.");
      return;
    }
    setError(null);
    setMessage(null);
    setLoading(true);

    try {
      await sendPasswordResetEmail(auth, targetEmail.trim());
      setMessage(`Password reset email sent to ${targetEmail.trim()}. Check your inbox.`);
    } catch (err: any) {
      setError(err.message || "Failed to send password reset email.");
    } finally {
      setLoading(false);
    }
  };

  // Preset demo loader for quick reviewer verification
  const fillCredentials = (type: "staff" | "client", email: string, pass: string) => {
    setError(null);
    setMessage(null);
    if (type === "staff") {
      setActiveTab("staff");
      setStaffEmail(email);
      setStaffPassword(pass);
    } else {
      setActiveTab("client");
      setClientEmail(email);
      setClientPassword(pass);
    }
  };

  return (
    <div className="min-h-[85vh] bg-slate-900 flex items-center justify-center p-4 sm:p-6 lg:p-8">
      <div className="max-w-md w-full space-y-6">
        {/* Header Branding */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-xl bg-indigo-600 text-white font-bold text-xl shadow-lg mb-2">
            ABC
          </div>
          <h2 className="text-2xl font-extrabold text-white tracking-tight">
            ABC & Associates
          </h2>
          <p className="text-sm text-slate-400">
            Chartered Accountants — Client Workflow Portal
          </p>
        </div>

        {/* Tab Switcher: Staff vs Client */}
        <div className="bg-slate-800/80 p-1 rounded-xl border border-slate-700/80 grid grid-cols-2 gap-1">
          <button
            type="button"
            onClick={() => {
              setActiveTab("staff");
              setError(null);
              setMessage(null);
            }}
            className={`py-2 px-3 text-xs font-semibold rounded-lg transition-all flex items-center justify-center gap-2 ${
              activeTab === "staff"
                ? "bg-indigo-600 text-white shadow-sm"
                : "text-slate-400 hover:text-white"
            }`}
          >
            <ShieldCheck className="w-4 h-4" />
            Staff Sign In
          </button>

          <button
            type="button"
            onClick={() => {
              setActiveTab("client");
              setError(null);
              setMessage(null);
            }}
            className={`py-2 px-3 text-xs font-semibold rounded-lg transition-all flex items-center justify-center gap-2 ${
              activeTab === "client"
                ? "bg-indigo-600 text-white shadow-sm"
                : "text-slate-400 hover:text-white"
            }`}
          >
            <Building2 className="w-4 h-4" />
            Client Sign In
          </button>
        </div>

        {/* Status Alerts */}
        {error && (
          <div className="p-3.5 bg-rose-950/80 border border-rose-800 text-rose-200 text-xs rounded-xl flex items-start gap-2.5 shadow-sm">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
            <span className="leading-relaxed">{error}</span>
          </div>
        )}

        {message && (
          <div className="p-3.5 bg-emerald-950/80 border border-emerald-800 text-emerald-200 text-xs rounded-xl flex items-start gap-2.5 shadow-sm">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
            <span className="leading-relaxed">{message}</span>
          </div>
        )}

        {/* Form Body */}
        <div className="bg-slate-800/60 border border-slate-700/80 rounded-2xl p-6 shadow-xl backdrop-blur-sm">
          {activeTab === "staff" ? (
            /* STAFF LOGIN FORM (full_admin, team_member) */
            <form onSubmit={handleStaffLogin} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Staff Email Address
                </label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
                  <input
                    type="email"
                    required
                    value={staffEmail}
                    onChange={(e) => setStaffEmail(e.target.value)}
                    placeholder="partner@abc-associates.com"
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg pl-9 pr-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
              </div>

              <div>
                <div className="flex justify-between items-center mb-1">
                  <label className="block text-xs font-medium text-slate-300">
                    Password
                  </label>
                  <button
                    type="button"
                    onClick={() => handleForgotPassword(staffEmail)}
                    className="text-xs text-indigo-400 hover:text-indigo-300 font-medium"
                  >
                    Forgot Password?
                  </button>
                </div>
                <div className="relative">
                  <KeyRound className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
                  <input
                    type="password"
                    required
                    value={staffPassword}
                    onChange={(e) => setStaffPassword(e.target.value)}
                    placeholder="••••••••••••"
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg pl-9 pr-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-semibold py-2.5 px-4 rounded-lg text-sm transition-all shadow-md flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {loading ? "Signing in..." : "Sign In to Staff Portal"}
                <ArrowRight className="w-4 h-4" />
              </button>
            </form>
          ) : (
            /* CLIENT EMAIL + PASSWORD LOGIN FORM */
            <form onSubmit={handleClientLogin} className="space-y-4">
              <div className="p-3 bg-indigo-950/40 border border-indigo-900/60 rounded-xl text-xs text-indigo-200 space-y-1">
                <p className="font-semibold text-indigo-100 flex items-center gap-1.5">
                  <Lock className="w-3.5 h-3.5 text-indigo-400" />
                  Secure Client Document Portal
                </p>
                <p className="text-slate-300 text-[11px] leading-relaxed">
                  Sign in using the login credentials delivered in your Engagement Setup email (<code className="text-indigo-300 font-bold">Client@2026</code>).
                </p>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Client Email Address
                </label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
                  <input
                    type="email"
                    required
                    value={clientEmail}
                    onChange={(e) => setClientEmail(e.target.value)}
                    placeholder="director@acme-enterprises.com"
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg pl-9 pr-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
              </div>

              <div>
                <div className="flex justify-between items-center mb-1">
                  <label className="block text-xs font-medium text-slate-300">
                    Password
                  </label>
                  <span className="text-[11px] text-slate-400">Default: <code className="text-indigo-300">Client@2026</code></span>
                </div>
                <div className="relative">
                  <KeyRound className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
                  <input
                    type="password"
                    required
                    value={clientPassword}
                    onChange={(e) => setClientPassword(e.target.value)}
                    placeholder="Client@2026"
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg pl-9 pr-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-semibold py-2.5 px-4 rounded-lg text-sm transition-all shadow-md flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {loading ? "Signing in..." : "Sign In to Client Workspace"}
                <ArrowRight className="w-4 h-4" />
              </button>
            </form>
          )}
        </div>

        {/* Quick Testing Seed Credentials Box */}
        <div className="bg-slate-800/40 border border-slate-700/60 rounded-2xl p-4 text-xs space-y-2.5">
          <div className="text-slate-300 font-semibold flex items-center justify-between border-b border-slate-700/60 pb-2">
            <span>Quick Testing Accounts</span>
            <span className="text-[10px] text-slate-400 bg-slate-700/60 px-2 py-0.5 rounded">Pre-configured</span>
          </div>

          <div className="grid grid-cols-1 gap-2 text-[11px]">
            <button
              type="button"
              onClick={() => fillCredentials("staff", "admin@abc-associates.com", "Admin@123456")}
              className="p-2 bg-slate-900/80 hover:bg-slate-800 border border-slate-700 rounded-lg text-left transition-colors flex items-center justify-between group"
            >
              <div>
                <div className="font-semibold text-purple-300 group-hover:text-purple-200">
                  Full Admin (Senior Partner)
                </div>
                <div className="text-slate-400">admin@abc-associates.com / Admin@123456</div>
              </div>
              <span className="text-[10px] text-purple-400 font-semibold bg-purple-950/60 px-2 py-0.5 rounded border border-purple-800/60">
                full_admin
              </span>
            </button>

            <button
              type="button"
              onClick={() => fillCredentials("staff", "auditor@abc-associates.com", "Audit@123456")}
              className="p-2 bg-slate-900/80 hover:bg-slate-800 border border-slate-700 rounded-lg text-left transition-colors flex items-center justify-between group"
            >
              <div>
                <div className="font-semibold text-blue-300 group-hover:text-blue-200">
                  Team Member (Audit Manager)
                </div>
                <div className="text-slate-400">auditor@abc-associates.com / Audit@123456</div>
              </div>
              <span className="text-[10px] text-blue-400 font-semibold bg-blue-950/60 px-2 py-0.5 rounded border border-blue-800/60">
                team_member
              </span>
            </button>

            <button
              type="button"
              onClick={() => fillCredentials("staff", "auditsenior@abc-associates.com", "Demo@Password123")}
              className="p-2 bg-slate-900/80 hover:bg-slate-800 border border-slate-700 rounded-lg text-left transition-colors flex items-center justify-between group"
            >
              <div>
                <div className="font-semibold text-sky-300 group-hover:text-sky-200">
                  Team Member (Audit Senior)
                </div>
                <div className="text-slate-400">auditsenior@abc-associates.com / Demo@Password123</div>
              </div>
              <span className="text-[10px] text-sky-400 font-semibold bg-sky-950/60 px-2 py-0.5 rounded border border-sky-800/60">
                team_member
              </span>
            </button>

            <button
              type="button"
              onClick={() => fillCredentials("client", "director@acme-enterprises.com", "Client@2026")}
              className="p-2 bg-slate-900/80 hover:bg-slate-800 border border-slate-700 rounded-lg text-left transition-colors flex items-center justify-between group"
            >
              <div>
                <div className="font-semibold text-emerald-300 group-hover:text-emerald-200">
                  Client Account (Acme / Any Client)
                </div>
                <div className="text-slate-400">email / Password: Client@2026</div>
              </div>
              <span className="text-[10px] text-emerald-400 font-semibold bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-800/60">
                client
              </span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
