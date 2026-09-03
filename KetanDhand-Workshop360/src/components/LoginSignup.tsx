import React, { useState, useEffect } from "react";
import { apiFetch, tokenStore } from "@/lib/api-client";
import { User } from "@/types";
import { Wrench, Shield, UserCheck, Lock, Phone, Mail, User as UserIcon, ArrowRight, AlertCircle } from "lucide-react";

interface LoginSignupProps {
  onLoginSuccess: (user: User) => void;
}

export function LoginSignup({ onLoginSuccess }: LoginSignupProps) {
  const [isLogin, setIsLogin] = useState(true);
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");

  // Signup fields
  const [signupName, setSignupName] = useState("");
  const [signupPhone, setSignupPhone] = useState("");
  const [signupEmail, setSignupEmail] = useState("");
  const [signupPassword, setSignupPassword] = useState("");
  const [signupConfirmPassword, setSignupConfirmPassword] = useState("");
  const [signupRole, setSignupRole] = useState<"mechanic" | "shopkeeper">("mechanic");
  const [hasOwner, setHasOwner] = useState(true);

  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");
  const [loading, setLoading] = useState(false);
  const [showForgotNotice, setShowForgotNotice] = useState(false);

  useEffect(() => {
    apiFetch("/api/auth/status")
      .then((res) => res.json())
      .then((data) => {
        if (data && typeof data.hasOwner === "boolean") {
          setHasOwner(data.hasOwner);
        }
      })
      .catch(() => {});
  }, [isLogin]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await apiFetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ identifier, password }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || "Login failed");
      }
      if (data.token) tokenStore.set(data.token);
      onLoginSuccess(data.user);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccessMsg("");
    setLoading(true);
    try {
      const res = await apiFetch("/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: signupName,
          phone: signupPhone,
          email: signupEmail,
          password: signupPassword,
          confirmPassword: signupConfirmPassword,
          role: signupRole,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || "Registration failed");
      }
      setSuccessMsg(data.message);
      if (data.user && data.user.status === "approved") {
        if (data.token) tokenStore.set(data.token);
        setTimeout(() => onLoginSuccess(data.user), 1500);
      } else {
        // Clear signup and switch to login with pending notice
        setTimeout(() => {
          setIsLogin(true);
          setIdentifier(signupPhone);
          setError("Account registered successfully! Waiting for Owner approval.");
        }, 2000);
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const fillDemo = (type: "owner" | "shopkeeper" | "mechanic") => {
    if (type === "owner") {
      setIdentifier("9876543210");
      setPassword("admin123");
    } else if (type === "shopkeeper") {
      setIdentifier("9876543212");
      setPassword("shop123");
    } else {
      setIdentifier("9123456789");
      setPassword("mech123");
    }
  };

  return (
    <div className="min-h-screen bg-[#F1F5F9] text-[#1E293B] flex flex-col justify-center py-12 sm:px-6 lg:px-8 px-4 font-sans">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="flex justify-center">
          <div className="w-16 h-16 bg-blue-600 rounded-2xl flex items-center justify-center shadow-lg shadow-blue-600/20 text-white">
            <Wrench className="w-9 h-9 stroke-[2.5]" />
          </div>
        </div>
        <h2 className="mt-6 text-center text-3xl font-extrabold text-slate-900 tracking-tight">
          MotoWorkshop Pro
        </h2>
        <p className="mt-2 text-center text-sm text-slate-500">
          Motorcycle Spare Parts & Repair Workshop Management
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-4 shadow-sm border border-slate-200 sm:rounded-2xl sm:px-10">
          {/* Tab Switcher */}
          <div className="flex rounded-xl bg-slate-100 p-1 mb-6 border border-slate-200">
            <button
              type="button"
              onClick={() => { setIsLogin(true); setError(""); }}
              className={`flex-1 py-2.5 text-sm font-semibold rounded-lg transition-all ${
                isLogin ? "bg-blue-600 text-white shadow" : "text-slate-600 hover:text-slate-900"
              }`}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => { setIsLogin(false); setError(""); }}
              className={`flex-1 py-2.5 text-sm font-semibold rounded-lg transition-all ${
                !isLogin ? "bg-blue-600 text-white shadow" : "text-slate-600 hover:text-slate-900"
              }`}
            >
              Sign Up
            </button>
          </div>

          {error && (
            <div className="mb-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl text-sm flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {successMsg && (
            <div className="mb-4 bg-emerald-50 border border-emerald-200 text-emerald-700 px-4 py-3 rounded-xl text-sm flex items-start gap-3">
              <UserCheck className="w-5 h-5 text-emerald-500 shrink-0 mt-0.5" />
              <span>{successMsg}</span>
            </div>
          )}

          {isLogin ? (
            <form onSubmit={handleLogin} className="space-y-5">
              <div>
                <label className="block text-xs font-medium text-slate-600 uppercase tracking-wider mb-1.5">
                  Phone Number or Email
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                    <Phone className="w-4 h-4" />
                  </div>
                  <input
                    type="text"
                    required
                    value={identifier}
                    onChange={(e) => setIdentifier(e.target.value)}
                    placeholder="e.g. 9876543210 or email"
                    className="block w-full pl-10 pr-3 py-3 bg-white border border-slate-200 rounded-xl text-slate-900 placeholder-slate-400 text-sm focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-blue-600"
                  />
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="block text-xs font-medium text-slate-600 uppercase tracking-wider">
                    Password
                  </label>
                  <button
                    type="button"
                    onClick={() => setShowForgotNotice(true)}
                    className="text-xs text-blue-600 hover:underline font-semibold"
                  >
                    Forgot password?
                  </button>
                </div>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                    <Lock className="w-4 h-4" />
                  </div>
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="block w-full pl-10 pr-3 py-3 bg-white border border-slate-200 rounded-xl text-slate-900 placeholder-slate-400 text-sm focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-blue-600"
                  />
                </div>
              </div>

              {showForgotNotice && (
                <div className="bg-slate-50 border border-slate-200 p-3 rounded-xl text-xs text-slate-600">
                  Please contact your workshop owner to reset your password.
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full flex justify-center items-center gap-2 py-3.5 px-4 border border-transparent rounded-xl shadow-sm text-sm font-bold text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-600 transition-all disabled:opacity-50"
              >
                {loading ? "Signing in..." : "Sign In"}
                <ArrowRight className="w-4 h-4" />
              </button>
            </form>
          ) : (
            <form onSubmit={handleSignup} className="space-y-4">
              {!hasOwner ? (
                <div className="bg-amber-50 border border-amber-300 p-3.5 rounded-xl text-amber-900 text-xs space-y-1">
                  <div className="flex items-center gap-2 font-bold text-amber-800">
                    <Shield className="w-4 h-4 text-amber-600 shrink-0" />
                    <span>First User Registration — Workshop Owner</span>
                  </div>
                  <p className="text-amber-700 leading-relaxed">
                    No owner exists yet. You are registering as the very first user! Even if you select Mechanic or Shopkeeper below, your account will be automatically assigned the <strong>Workshop Owner</strong> role with full privileges.
                  </p>
                </div>
              ) : (
                <div className="bg-blue-50 border border-blue-200 p-3 rounded-xl text-blue-900 text-xs">
                  <p>ℹ️ Workshop Owner already exists. New staff registrations will be registered as <strong>{signupRole === "shopkeeper" ? "Shopkeeper" : "Mechanic"}</strong> and require Owner approval.</p>
                </div>
              )}

              <div>
                <label className="block text-xs font-medium text-slate-600 uppercase tracking-wider mb-1">
                  Register As *
                </label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setSignupRole("mechanic")}
                    className={`py-2 px-3 text-xs font-bold rounded-xl border transition-all ${
                      signupRole === "mechanic"
                        ? "bg-blue-600 text-white border-blue-600 shadow-sm"
                        : "bg-white text-slate-700 border-slate-200 hover:bg-slate-50"
                    }`}
                  >
                    Mechanic
                  </button>
                  <button
                    type="button"
                    onClick={() => setSignupRole("shopkeeper")}
                    className={`py-2 px-3 text-xs font-bold rounded-xl border transition-all ${
                      signupRole === "shopkeeper"
                        ? "bg-purple-600 text-white border-purple-600 shadow-sm"
                        : "bg-white text-slate-700 border-slate-200 hover:bg-slate-50"
                    }`}
                  >
                    Shopkeeper
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-600 uppercase tracking-wider mb-1">
                  Full Name *
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                    <UserIcon className="w-4 h-4" />
                  </div>
                  <input
                    type="text"
                    required
                    value={signupName}
                    onChange={(e) => setSignupName(e.target.value)}
                    placeholder="e.g. Ramesh Kumar"
                    className="block w-full pl-10 pr-3 py-2.5 bg-white border border-slate-200 rounded-xl text-slate-900 placeholder-slate-400 text-sm focus:outline-none focus:ring-2 focus:ring-blue-600"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-600 uppercase tracking-wider mb-1">
                  Phone Number *
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                    <Phone className="w-4 h-4" />
                  </div>
                  <input
                    type="tel"
                    required
                    value={signupPhone}
                    onChange={(e) => setSignupPhone(e.target.value)}
                    placeholder="e.g. 9123456789"
                    className="block w-full pl-10 pr-3 py-2.5 bg-white border border-slate-200 rounded-xl text-slate-900 placeholder-slate-400 text-sm focus:outline-none focus:ring-2 focus:ring-blue-600"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-600 uppercase tracking-wider mb-1">
                  Email (Optional)
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                    <Mail className="w-4 h-4" />
                  </div>
                  <input
                    type="email"
                    value={signupEmail}
                    onChange={(e) => setSignupEmail(e.target.value)}
                    placeholder="ramesh@workshop.com"
                    className="block w-full pl-10 pr-3 py-2.5 bg-white border border-slate-200 rounded-xl text-slate-900 placeholder-slate-400 text-sm focus:outline-none focus:ring-2 focus:ring-blue-600"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-600 uppercase tracking-wider mb-1">
                  Password *
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                    <Lock className="w-4 h-4" />
                  </div>
                  <input
                    type="password"
                    required
                    value={signupPassword}
                    onChange={(e) => setSignupPassword(e.target.value)}
                    placeholder="••••••••"
                    className="block w-full pl-10 pr-3 py-2.5 bg-white border border-slate-200 rounded-xl text-slate-900 placeholder-slate-400 text-sm focus:outline-none focus:ring-2 focus:ring-blue-600"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-600 uppercase tracking-wider mb-1">
                  Confirm Password *
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                    <Lock className="w-4 h-4" />
                  </div>
                  <input
                    type="password"
                    required
                    value={signupConfirmPassword}
                    onChange={(e) => setSignupConfirmPassword(e.target.value)}
                    placeholder="••••••••"
                    className="block w-full pl-10 pr-3 py-2.5 bg-white border border-slate-200 rounded-xl text-slate-900 placeholder-slate-400 text-sm focus:outline-none focus:ring-2 focus:ring-blue-600"
                  />
                </div>
              </div>

              <div className="text-xs text-slate-600 bg-slate-50 p-3 rounded-xl border border-slate-200 space-y-1">
                <p>ℹ️ <strong>Workshop Owner Signup:</strong> The very first user to sign up on a clean database automatically becomes the <strong>Workshop Owner</strong>.</p>
                <p>Subsequent staff signups register as Mechanic or Shopkeeper and require <strong className="text-amber-600">Owner Approval</strong>.</p>
              </div>

              <button
                type="submit"
                disabled={loading}
                className={`w-full flex justify-center items-center gap-2 py-3 px-4 border border-transparent rounded-xl shadow-sm text-sm font-bold text-white transition-all disabled:opacity-50 ${
                  signupRole === "shopkeeper" ? "bg-purple-600 hover:bg-purple-700 focus:ring-purple-600" : "bg-blue-600 hover:bg-blue-700 focus:ring-blue-600"
                }`}
              >
                {loading ? "Registering..." : `Sign Up as ${signupRole === "shopkeeper" ? "Shopkeeper" : "Mechanic"}`}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
