import { createClient, SupabaseClient, User, Session } from '@supabase/supabase-js';

/**
 * Designated Super User Google Account with exclusive write and rate ingestion permissions.
 */
export const SUPERUSER_EMAIL = 'kosamgo@gmail.com';

/**
 * Verify whether an authenticated user matches the designated Super User account.
 */
export function isUserSuperUser(user: { email?: string } | null | undefined): boolean {
  if (!user || !user.email) return false;
  return user.email.trim().toLowerCase() === SUPERUSER_EMAIL.toLowerCase();
}

// Local storage keys for runtime configuration overrides
const LS_SUPABASE_URL_KEY = 'bullion_supabase_url';
const LS_SUPABASE_ANON_KEY = 'bullion_supabase_anon_key';

export interface SupabaseConfig {
  url: string;
  anonKey: string;
  isConfigured: boolean;
  source: 'env' | 'storage' | 'none';
}

/**
 * Retrieve the active Supabase configuration from environment variables or localStorage override.
 */
export function getSupabaseConfig(): SupabaseConfig {
  // 1. Check Vite Environment Variables
  const envUrl = import.meta.env.VITE_SUPABASE_URL as string | undefined;
  const envKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined;

  if (envUrl && envKey && envUrl.trim() !== '' && envKey.trim() !== '') {
    return {
      url: envUrl.trim(),
      anonKey: envKey.trim(),
      isConfigured: true,
      source: 'env',
    };
  }

  // 2. Check runtime localStorage overrides (useful for browser setup without rebuild)
  if (typeof window !== 'undefined' && window.localStorage) {
    const lsUrl = window.localStorage.getItem(LS_SUPABASE_URL_KEY);
    const lsKey = window.localStorage.getItem(LS_SUPABASE_ANON_KEY);
    if (lsUrl && lsKey && lsUrl.trim() !== '' && lsKey.trim() !== '') {
      return {
        url: lsUrl.trim(),
        anonKey: lsKey.trim(),
        isConfigured: true,
        source: 'storage',
      };
    }
  }

  return {
    url: '',
    anonKey: '',
    isConfigured: false,
    source: 'none',
  };
}

/**
 * Set runtime Supabase configuration in localStorage.
 */
export function setSupabaseConfig(url: string, anonKey: string): void {
  if (typeof window === 'undefined' || !window.localStorage) return;
  if (url && anonKey) {
    window.localStorage.setItem(LS_SUPABASE_URL_KEY, url.trim());
    window.localStorage.setItem(LS_SUPABASE_ANON_KEY, anonKey.trim());
  } else {
    window.localStorage.removeItem(LS_SUPABASE_URL_KEY);
    window.localStorage.removeItem(LS_SUPABASE_ANON_KEY);
  }
  // Reset client singleton so next call re-instantiates
  cachedClient = null;
}

let cachedClient: SupabaseClient | null = null;

/**
 * Returns the Supabase client singleton, or null if unconfigured.
 */
export function getSupabase(): SupabaseClient | null {
  if (cachedClient) return cachedClient;

  const config = getSupabaseConfig();
  if (!config.isConfigured) return null;

  try {
    cachedClient = createClient(config.url, config.anonKey, {
      auth: {
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: true,
      },
    });
    return cachedClient;
  } catch (err) {
    console.warn('Failed to initialize Supabase client:', err);
    return null;
  }
}

/**
 * Check whether Supabase is configured and ready.
 */
export function isSupabaseConfigured(): boolean {
  return getSupabaseConfig().isConfigured;
}

// -------------------------------------------------------------
// Authentication Helpers
// -------------------------------------------------------------

/**
 * Resolves the dynamic redirect URL based on current browser origin.
 * Automatically handles Netlify domains, custom domains, or local testing.
 */
export function getAuthRedirectUrl(): string {
  if (typeof window === 'undefined') return 'http://localhost:3000';
  // Standardize origin without trailing slash (e.g. https://your-site.netlify.app)
  return window.location.origin.replace(/\/$/, '');
}

/**
 * Super User sign in with Google OAuth.
 * Uses current browser origin (Netlify or localhost) as redirect URL.
 * Probes the endpoint first to prevent raw JSON errors if Google provider is not yet enabled.
 */
export async function signInWithGoogle(): Promise<{
  error: Error | null;
  providerNotEnabled?: boolean;
}> {
  const supabase = getSupabase();
  if (!supabase) {
    return {
      error: new Error('Supabase is not configured. Please configure Supabase URL & Anon Key.'),
    };
  }

  try {
    const redirectUrl = getAuthRedirectUrl();
    const { data, error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: redirectUrl,
        queryParams: {
          access_type: 'offline',
          prompt: 'consent',
        },
        skipBrowserRedirect: true,
      },
    });

    if (error) {
      const msg = error.message || '';
      const notEnabled =
        msg.toLowerCase().includes('unsupported provider') ||
        msg.toLowerCase().includes('not enabled') ||
        msg.toLowerCase().includes('validation_failed');
      return { error, providerNotEnabled: notEnabled };
    }

    if (data?.url) {
      // Check if provider is enabled before redirecting the browser
      try {
        const probe = await fetch(data.url, { method: 'GET' });
        if (!probe.ok && probe.status === 400) {
          const json = await probe.json().catch(() => null);
          if (
            json?.msg?.toLowerCase().includes('unsupported provider') ||
            json?.error_code === 'validation_failed'
          ) {
            return {
              error: new Error(
                'Google Sign-In is not enabled in your Supabase project. In Supabase Dashboard, go to Authentication -> Providers -> Google to enable it, or use Email / Password below.'
              ),
              providerNotEnabled: true,
            };
          }
        }
      } catch {
        // If fetch throws (e.g. CORS after successful redirect to accounts.google.com), Google provider is active!
      }

      window.location.assign(data.url);
      return { error: null };
    }

    return { error: new Error('No OAuth URL returned from Supabase.') };
  } catch (err: any) {
    const msg = err.message || '';
    const notEnabled =
      msg.toLowerCase().includes('unsupported provider') ||
      msg.toLowerCase().includes('not enabled') ||
      msg.toLowerCase().includes('validation_failed');
    return { error: err, providerNotEnabled: notEnabled };
  }
}

/**
 * Super User sign in with Magic Link / OTP email (passwordless).
 */
export async function sendMagicLink(
  email: string
): Promise<{ error: Error | null }> {
  const supabase = getSupabase();
  if (!supabase) {
    return { error: new Error('Supabase is not configured.') };
  }

  try {
    const redirectUrl = getAuthRedirectUrl();
    const { error } = await supabase.auth.signInWithOtp({
      email: email.trim(),
      options: {
        emailRedirectTo: redirectUrl,
      },
    });
    return { error };
  } catch (err: any) {
    return { error: err };
  }
}

/**
 * Verify 6-digit OTP code sent to user email.
 */
export async function verifyEmailOtp(
  email: string,
  token: string
): Promise<{ user: User | null; error: Error | null }> {
  const supabase = getSupabase();
  if (!supabase) {
    return { user: null, error: new Error('Supabase is not configured.') };
  }

  try {
    const { data, error } = await supabase.auth.verifyOtp({
      email: email.trim(),
      token: token.trim(),
      type: 'email',
    });
    return { user: data.user, error };
  } catch (err: any) {
    return { user: null, error: err };
  }
}

/**
 * Super User sign in with Email & Password (fallback for initial admin setup).
 */
export async function signInWithEmail(
  email: string,
  pass: string
): Promise<{ user: User | null; error: Error | null }> {
  const supabase = getSupabase();
  if (!supabase) {
    return {
      user: null,
      error: new Error('Supabase is not configured.'),
    };
  }

  const { data, error } = await supabase.auth.signInWithPassword({
    email,
    password: pass,
  });

  return { user: data.user, error };
}

/**
 * Super User sign up with Email & Password (fallback admin creation).
 */
export async function signUpWithEmail(
  email: string,
  pass: string
): Promise<{ user: User | null; error: Error | null }> {
  const supabase = getSupabase();
  if (!supabase) {
    return {
      user: null,
      error: new Error('Supabase is not configured.'),
    };
  }

  const { data, error } = await supabase.auth.signUp({
    email,
    password: pass,
  });

  return { user: data.user, error };
}

/**
 * Sign out current authenticated user.
 */
export async function signOut(): Promise<{ error: Error | null }> {
  const supabase = getSupabase();
  if (!supabase) return { error: null };
  const { error } = await supabase.auth.signOut();
  return { error };
}

/**
 * Retrieve current active authenticated session & user.
 */
export async function getCurrentUser(): Promise<User | null> {
  const supabase = getSupabase();
  if (!supabase) return null;

  try {
    const {
      data: { user },
    } = await supabase.auth.getUser();
    return user;
  } catch {
    return null;
  }
}

/**
 * Subscribe to Supabase Auth state changes (sign in, token refresh, sign out).
 */
export function onAuthStateChange(
  callback: (user: User | null, session: Session | null) => void
): () => void {
  const supabase = getSupabase();
  if (!supabase) {
    callback(null, null);
    return () => {};
  }

  const {
    data: { subscription },
  } = supabase.auth.onAuthStateChange((_event, session) => {
    callback(session?.user ?? null, session);
  });

  return () => {
    subscription.unsubscribe();
  };
}
