import React, { useState } from 'react';
import {
  signInWithGoogle,
  signInWithEmail,
  signUpWithEmail,
  sendMagicLink,
  verifyEmailOtp,
  isSupabaseConfigured,
  getSupabaseConfig,
  SUPERUSER_EMAIL,
} from '../../services/supabaseClient';
import {
  ShieldCheck,
  Lock,
  Mail,
  AlertCircle,
  CheckCircle,
  ExternalLink,
  X,
  KeyRound,
  Copy,
  Check,
  ArrowRight,
  Sparkles,
} from 'lucide-react';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAuthSuccess?: () => void;
}

export const AuthModal: React.FC<AuthModalProps> = ({ isOpen, onClose, onAuthSuccess }) => {
  const [tab, setTab] = useState<'google' | 'magic-link' | 'email'>('google');
  const [email, setEmail] = useState(SUPERUSER_EMAIL);
  const [password, setPassword] = useState('');
  const [isSignUp, setIsSignUp] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Google provider error helper states
  const [providerNotEnabled, setProviderNotEnabled] = useState(false);
  const [showGoogleHelp, setShowGoogleHelp] = useState(false);
  const [copiedCallback, setCopiedCallback] = useState(false);
  const [showUrlConfigHelp, setShowUrlConfigHelp] = useState(false);
  const [copiedNetlifyWildcard, setCopiedNetlifyWildcard] = useState(false);

  // Magic link & OTP states
  const [magicLinkSent, setMagicLinkSent] = useState(false);
  const [otpToken, setOtpToken] = useState('');
  const [isVerifyingOtp, setIsVerifyingOtp] = useState(false);

  if (!isOpen) return null;

  const isConfigured = isSupabaseConfigured();
  const config = getSupabaseConfig();
  const projectRef = config.url ? config.url.replace('https://', '').split('.')[0] : 'your-project';
  const providerDashboardUrl = `https://supabase.com/dashboard/project/${projectRef}/auth/providers`;
  const callbackUrl = config.url
    ? `${config.url}/auth/v1/callback`
    : 'https://<your-project>.supabase.co/auth/v1/callback';

  const handleCopyCallback = () => {
    navigator.clipboard.writeText(callbackUrl);
    setCopiedCallback(true);
    setTimeout(() => setCopiedCallback(false), 2500);
  };

  const handleGoogleLogin = async () => {
    setIsLoading(true);
    setErrorMsg(null);
    setProviderNotEnabled(false);
    try {
      const res = await signInWithGoogle();
      if (res.error) {
        if (res.providerNotEnabled) {
          setProviderNotEnabled(true);
        }
        setErrorMsg(res.error.message);
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Google sign in failed');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSendMagicLink = async () => {
    setIsLoading(true);
    setErrorMsg(null);
    setSuccessMsg(null);
    try {
      const { error } = await sendMagicLink(email);
      if (error) {
        setErrorMsg(error.message);
      } else {
        setMagicLinkSent(true);
        setSuccessMsg(`Magic login link sent to ${email}!`);
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to send magic link');
    } finally {
      setIsLoading(false);
    }
  };

  const handleVerifyOtp = async () => {
    if (!otpToken.trim()) return;
    setIsVerifyingOtp(true);
    setErrorMsg(null);
    try {
      const { user, error } = await verifyEmailOtp(email, otpToken);
      if (error) {
        setErrorMsg(error.message);
      } else if (user) {
        setSuccessMsg(`Successfully authenticated as ${user.email}!`);
        setTimeout(() => {
          onAuthSuccess?.();
          onClose();
        }, 1000);
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to verify OTP');
    } finally {
      setIsVerifyingOtp(false);
    }
  };

  const handleEmailAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) return;

    setIsLoading(true);
    setErrorMsg(null);
    setSuccessMsg(null);

    try {
      if (isSignUp) {
        const { user, error } = await signUpWithEmail(email, password);
        if (error) {
          setErrorMsg(error.message);
        } else if (user) {
          setSuccessMsg(`Super User account created for ${user.email}! Signed in.`);
          setTimeout(() => {
            onAuthSuccess?.();
            onClose();
          }, 1200);
        }
      } else {
        const { user, error } = await signInWithEmail(email, password);
        if (error) {
          setErrorMsg(error.message);
        } else if (user) {
          setSuccessMsg(`Signed in as Super User ${user.email}!`);
          setTimeout(() => {
            onAuthSuccess?.();
            onClose();
          }, 1000);
        }
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Authentication error');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-stone-900/60 backdrop-blur-2xs flex items-center justify-center p-3 sm:p-4">
      <div className="bg-white rounded-xl shadow-2xl max-w-lg w-full border border-stone-200 overflow-hidden flex flex-col">
        {/* Header */}
        <div className="bg-[#FAF7F2] px-5 py-4 border-b border-stone-200 flex justify-between items-center">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-[#FBF6E9] border border-[#D4AF37]/50 flex items-center justify-center text-[#B88B2A]">
              <Lock className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-stone-900">Super User Authentication</h3>
              <p className="text-[11px] text-stone-500">
                Exclusive cloud write access for {SUPERUSER_EMAIL}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-stone-400 hover:text-stone-700 p-1 rounded-md cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-5 space-y-4 text-xs">
          {/* Explanation Box */}
          <div className="bg-[#FAF7F2] p-3 rounded-lg border border-[#D4AF37]/40 text-stone-700 space-y-1">
            <div className="font-bold text-stone-900 flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-[#B88B2A]" />
              <span>Designated Super User: {SUPERUSER_EMAIL}</span>
            </div>
            <p className="text-[11px] leading-relaxed text-stone-600">
              Only the portfolio owner (<strong>{SUPERUSER_EMAIL}</strong>) has permissions to record purchases,
              upload supplemental rates, and update valuation parameters. Public link visitors view stored data without login.
            </p>
          </div>

          {!isConfigured && (
            <div className="bg-amber-50 p-3 rounded-lg border border-amber-200 text-amber-800 text-[11px] space-y-1">
              <div className="font-bold flex items-center gap-1">
                <AlertCircle className="w-3.5 h-3.5 text-amber-600" />
                <span>Supabase Credentials Not Yet Configured</span>
              </div>
              <p>
                Connect your Supabase project in <strong>Settings → Supabase Cloud Database</strong>{' '}
                or configure <code className="font-mono font-semibold">VITE_SUPABASE_URL</code> in{' '}
                <code className="font-mono font-semibold">.env</code>.
              </p>
            </div>
          )}

          {errorMsg && !providerNotEnabled && (
            <div className="bg-rose-50 border border-rose-200 text-rose-700 px-3 py-2 rounded-lg text-[11px] flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          {successMsg && (
            <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 px-3 py-2 rounded-lg text-[11px] flex items-center gap-2">
              <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0" />
              <span>{successMsg}</span>
            </div>
          )}

          {/* Login Tabs */}
          <div className="flex border-b border-stone-200 gap-2 sm:gap-4 text-xs font-semibold overflow-x-auto">
            <button
              type="button"
              onClick={() => {
                setTab('google');
                setErrorMsg(null);
              }}
              className={`pb-2 px-1 transition-colors shrink-0 flex items-center gap-1.5 cursor-pointer ${
                tab === 'google'
                  ? 'border-b-2 border-[#B88B2A] text-stone-900'
                  : 'text-stone-400 hover:text-stone-600'
              }`}
            >
              <span>Google Account</span>
            </button>

            <button
              type="button"
              onClick={() => {
                setTab('magic-link');
                setErrorMsg(null);
              }}
              className={`pb-2 px-1 transition-colors shrink-0 flex items-center gap-1.5 cursor-pointer ${
                tab === 'magic-link'
                  ? 'border-b-2 border-emerald-600 text-stone-900'
                  : 'text-stone-400 hover:text-stone-600'
              }`}
            >
              <Sparkles className="w-3.5 h-3.5 text-emerald-600" />
              <span>1-Click Magic Link</span>
            </button>

            <button
              type="button"
              onClick={() => {
                setTab('email');
                setErrorMsg(null);
              }}
              className={`pb-2 px-1 transition-colors shrink-0 flex items-center gap-1.5 cursor-pointer ${
                tab === 'email'
                  ? 'border-b-2 border-[#B88B2A] text-stone-900'
                  : 'text-stone-400 hover:text-stone-600'
              }`}
            >
              <KeyRound className="w-3.5 h-3.5" />
              <span>Password</span>
            </button>
          </div>

          {/* Google Auth Tab */}
          {tab === 'google' && (
            <div className="space-y-3 pt-1">
              <button
                type="button"
                onClick={handleGoogleLogin}
                disabled={isLoading || !isConfigured}
                className="w-full flex items-center justify-center gap-3 px-4 py-2.5 bg-white hover:bg-stone-50 border border-stone-300 text-stone-700 font-semibold rounded-lg shadow-2xs transition-colors disabled:opacity-50 cursor-pointer"
              >
                {/* Google Multi-color Icon */}
                <svg className="w-4 h-4" viewBox="0 0 24 24">
                  <path
                    fill="#4285F4"
                    d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                  />
                  <path
                    fill="#34A853"
                    d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  />
                  <path
                    fill="#FBBC05"
                    d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
                  />
                  <path
                    fill="#EA4335"
                    d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
                  />
                </svg>
                <span>{isLoading ? 'Checking Google Provider...' : 'Continue with Google'}</span>
              </button>

              {/* Provider Not Enabled Explanatory Box */}
              {providerNotEnabled && (
                <div className="bg-amber-50 border border-amber-300 rounded-xl p-3.5 space-y-3 text-xs text-amber-900 animate-fadeIn">
                  <div className="flex items-start gap-2">
                    <AlertCircle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                    <div className="space-y-1">
                      <span className="font-bold block">Google Provider is Not Enabled in Supabase</span>
                      <p className="text-[11px] leading-relaxed text-amber-800">
                        In Supabase, Google OAuth requires enabling the Google provider toggle with Google Cloud OAuth Client credentials before it accepts sign-in requests.
                      </p>
                    </div>
                  </div>

                  {/* Immediate Alternative Action */}
                  <div className="bg-white p-3 rounded-lg border border-amber-200 shadow-2xs space-y-2">
                    <span className="text-[11px] font-bold text-stone-900 flex items-center gap-1">
                      <Sparkles className="w-3.5 h-3.5 text-emerald-600" />
                      Instant Solution (Zero Setup Required):
                    </span>
                    <p className="text-[11px] text-stone-600">
                      You can log in right now as <strong>{SUPERUSER_EMAIL}</strong> using an Email Magic Link or Password without needing to configure Google Cloud Console:
                    </p>
                    <div className="flex flex-col sm:flex-row gap-2 pt-1">
                      <button
                        type="button"
                        onClick={() => {
                          setTab('magic-link');
                          handleSendMagicLink();
                        }}
                        className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg font-bold text-[11px] transition-colors flex items-center justify-center gap-1.5 cursor-pointer shadow-2xs"
                      >
                        <Mail className="w-3.5 h-3.5" />
                        <span>Send 1-Click Magic Link to {SUPERUSER_EMAIL}</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => setTab('email')}
                        className="px-3 py-1.5 bg-stone-100 hover:bg-stone-200 text-stone-700 border border-stone-200 rounded-lg font-semibold text-[11px] transition-colors flex items-center justify-center gap-1 cursor-pointer"
                      >
                        <KeyRound className="w-3 h-3 text-[#B88B2A]" />
                        <span>Use Password</span>
                      </button>
                    </div>
                  </div>

                  {/* 2-Minute Google Setup Guide */}
                  <div>
                    <button
                      type="button"
                      onClick={() => setShowGoogleHelp(!showGoogleHelp)}
                      className="text-[11px] text-[#B88B2A] font-semibold hover:underline flex items-center gap-1 cursor-pointer"
                    >
                      <span>{showGoogleHelp ? 'Hide' : 'Want Google Sign-In?'} 2-Minute Guide to Enable in Supabase</span>
                      <ExternalLink className="w-3 h-3" />
                    </button>

                    {showGoogleHelp && (
                      <div className="mt-2.5 p-3.5 bg-stone-900 text-stone-200 rounded-lg space-y-2 text-[11px] font-sans">
                        <p className="font-semibold text-emerald-400">How to Enable Google Provider in Supabase:</p>
                        <ol className="list-decimal list-inside space-y-2 text-stone-300 leading-relaxed">
                          <li>
                            Open{' '}
                            <a
                              href={providerDashboardUrl}
                              target="_blank"
                              rel="noreferrer"
                              className="text-[#D4AF37] underline inline-flex items-center gap-0.5 font-mono"
                            >
                              Supabase Providers <ExternalLink className="w-2.5 h-2.5" />
                            </a>{' '}
                            and click <strong>Google</strong>.
                          </li>
                          <li>
                            Toggle <strong>Enable Sign in with Google</strong> to <strong>ON</strong>.
                          </li>
                          <li>
                            In Google Cloud Console, add this authorized redirect URI:
                            <div className="flex items-center gap-1.5 mt-1 font-mono text-[10px] bg-stone-800 p-2 rounded text-amber-300 border border-stone-700">
                              <span className="truncate">{callbackUrl}</span>
                              <button
                                type="button"
                                onClick={handleCopyCallback}
                                className="ml-auto px-2 py-0.5 bg-stone-700 hover:bg-stone-600 rounded text-stone-200 text-[10px] shrink-0 cursor-pointer flex items-center gap-1"
                              >
                                {copiedCallback ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                                <span>{copiedCallback ? 'Copied!' : 'Copy'}</span>
                              </button>
                            </div>
                          </li>
                          <li>
                            Paste your <strong>Client ID</strong> &amp; <strong>Client Secret</strong> into Supabase and click <strong>Save</strong>.
                          </li>
                        </ol>
                      </div>
                    )}
                  </div>
                </div>
              )}

              <div className="pt-1 text-[11px] text-stone-500 space-y-1">
                <p className="text-center">
                  Signs in through your Google Account via Supabase OAuth.
                </p>
                <div className="text-center">
                  <button
                    type="button"
                    onClick={() => setShowUrlConfigHelp(!showUrlConfigHelp)}
                    className="text-[#B88B2A] hover:underline cursor-pointer font-medium text-[10.5px]"
                  >
                    {showUrlConfigHelp ? '▲ Hide URL Config' : '⚠️ Redirecting to localhost instead of Netlify?'}
                  </button>
                </div>
              </div>

              {showUrlConfigHelp && (
                <div className="bg-amber-50 border border-amber-300 rounded-xl p-3 text-xs text-amber-900 space-y-2 animate-fadeIn">
                  <span className="font-bold block text-[11.5px] text-amber-950">
                    Fix: Allow Netlify in Supabase URL Configuration
                  </span>
                  <p className="text-[11px] leading-relaxed text-amber-800">
                    If Google redirects you to <code>http://localhost:3000</code> with <em>"Safari can't connect to server"</em>, Supabase blocked the Netlify redirect because Netlify is not yet in your Supabase allow-list:
                  </p>
                  <ol className="list-decimal list-inside space-y-1.5 text-[11px] text-amber-900">
                    <li>
                      Open{' '}
                      <a
                        href={`https://supabase.com/dashboard/project/${projectRef}/auth/url-configuration`}
                        target="_blank"
                        rel="noreferrer"
                        className="text-[#B88B2A] underline font-bold inline-flex items-center gap-0.5"
                      >
                        Supabase URL Configuration <ExternalLink className="w-2.5 h-2.5" />
                      </a>
                    </li>
                    <li>
                      Change <strong>Site URL</strong> to your Netlify address (or <code>{typeof window !== 'undefined' ? window.location.origin : 'https://your-site.netlify.app'}</code>).
                    </li>
                    <li>
                      Under <strong>Redirect URLs</strong>, click <strong>Add URL</strong> and add this pattern:
                      <div className="flex items-center gap-1.5 mt-1 font-mono text-[10px] bg-white p-1.5 rounded border border-amber-300 text-stone-800">
                        <span>https://*.netlify.app/**</span>
                        <button
                          type="button"
                          onClick={() => {
                            navigator.clipboard.writeText('https://*.netlify.app/**');
                            setCopiedNetlifyWildcard(true);
                            setTimeout(() => setCopiedNetlifyWildcard(false), 2000);
                          }}
                          className="ml-auto px-2 py-0.5 bg-amber-100 hover:bg-amber-200 rounded text-amber-900 font-sans text-[10px] shrink-0 cursor-pointer"
                        >
                          {copiedNetlifyWildcard ? 'Copied!' : 'Copy'}
                        </button>
                      </div>
                    </li>
                    <li>Click <strong>Save</strong>. Future Google logins will return cleanly to Netlify!</li>
                  </ol>
                </div>
              )}
            </div>
          )}

          {/* Magic Link / OTP Tab */}
          {tab === 'magic-link' && (
            <div className="space-y-3 pt-1">
              <div className="space-y-1">
                <label className="block text-stone-700 font-semibold">Super User Email</label>
                <div className="relative">
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full px-3 py-2 border border-stone-300 rounded-lg text-xs bg-stone-50 font-mono text-stone-800"
                    disabled
                  />
                  <span className="absolute right-3 top-2 text-[10px] bg-emerald-100 text-emerald-800 font-bold px-1.5 py-0.5 rounded">
                    Designated Owner
                  </span>
                </div>
                <span className="text-[10px] text-stone-500 block">
                  Passwordless authentication. Supabase sends a secure login link directly to your Gmail inbox.
                </span>
              </div>

              {!magicLinkSent ? (
                <button
                  type="button"
                  onClick={handleSendMagicLink}
                  disabled={isLoading || !isConfigured}
                  className="w-full py-2.5 px-4 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-lg shadow-2xs transition-colors flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
                >
                  <Mail className="w-4 h-4" />
                  <span>{isLoading ? 'Sending Magic Link...' : `Send Magic Link to ${email}`}</span>
                </button>
              ) : (
                <div className="space-y-3 bg-emerald-50 border border-emerald-200 rounded-lg p-3 text-emerald-900 animate-fadeIn">
                  <div className="flex items-start gap-2">
                    <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                    <div className="space-y-1">
                      <span className="font-bold block text-xs">Magic Link Dispatched!</span>
                      <p className="text-[11px] text-emerald-800 leading-relaxed">
                        We sent a secure login link to <strong>{email}</strong>. Check your inbox and click the link to log in immediately.
                      </p>
                    </div>
                  </div>

                  {/* Optional OTP Code input */}
                  <div className="pt-2 border-t border-emerald-200/60 space-y-2">
                    <span className="text-[11px] font-semibold text-emerald-950 block">
                      Or enter the 6-digit confirmation code from the email:
                    </span>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        maxLength={6}
                        value={otpToken}
                        onChange={(e) => setOtpToken(e.target.value)}
                        placeholder="123456"
                        className="w-32 px-3 py-1.5 border border-emerald-300 rounded-lg text-xs font-mono tracking-widest text-center uppercase bg-white focus:ring-1 focus:ring-emerald-600"
                      />
                      <button
                        type="button"
                        onClick={handleVerifyOtp}
                        disabled={isVerifyingOtp || otpToken.length < 6}
                        className="px-3.5 py-1.5 bg-emerald-700 hover:bg-emerald-800 text-white text-xs font-bold rounded-lg disabled:opacity-50 cursor-pointer"
                      >
                        {isVerifyingOtp ? 'Verifying...' : 'Verify Code'}
                      </button>
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={handleSendMagicLink}
                    disabled={isLoading}
                    className="text-[11px] text-emerald-800 underline hover:text-emerald-950 font-medium cursor-pointer"
                  >
                    Didn't receive it? Resend Magic Link
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Email & Password Tab */}
          {tab === 'email' && (
            <form onSubmit={handleEmailAuth} className="space-y-3 pt-1">
              <div>
                <label className="block text-stone-700 font-semibold mb-1">Super User Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="kosamgo@gmail.com"
                  className="w-full px-3 py-1.5 border border-stone-300 rounded-lg text-xs focus:ring-1 focus:ring-[#B88B2A]"
                  required
                />
              </div>

              <div>
                <div className="flex justify-between items-center mb-1">
                  <label className="block text-stone-700 font-semibold">Password</label>
                  <span className="text-[10px] text-stone-400">
                    {isSignUp ? 'Choose password for kosamgo@gmail.com' : 'Enter password'}
                  </span>
                </div>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full px-3 py-1.5 border border-stone-300 rounded-lg text-xs focus:ring-1 focus:ring-[#B88B2A]"
                  required
                />
              </div>

              <div className="flex items-center justify-between pt-1">
                <button
                  type="button"
                  onClick={() => {
                    setIsSignUp(!isSignUp);
                    setErrorMsg(null);
                  }}
                  className="text-[11px] text-[#B88B2A] hover:underline cursor-pointer"
                >
                  {isSignUp ? 'Already set a password? Sign In' : 'First time? Set Password for Super User'}
                </button>
                <button
                  type="submit"
                  disabled={isLoading || !isConfigured}
                  className="px-4 py-1.5 bg-[#B88B2A] hover:bg-[#8E6B1D] text-white font-semibold rounded-lg shadow-2xs transition-colors disabled:opacity-50 cursor-pointer"
                >
                  {isLoading ? 'Authenticating...' : isSignUp ? 'Set Password & Create' : 'Sign In'}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};
