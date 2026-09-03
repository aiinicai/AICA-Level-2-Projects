import React, { createContext, useContext, useEffect, useState } from 'react';
import { User, Session, AuthError } from '@supabase/supabase-js';
import { supabase, isSupabaseConfigured, supabaseUrl, supabasePublishableKey } from '../lib/supabaseClient';

export type UserRole = 'admin' | 'user';

export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  created_at?: string;
  updated_at?: string;
}

export interface AuthResultError {
  message: string;
  name?: string;
  status?: number;
}

interface AuthContextType {
  user: User | null;
  session: Session | null;
  profile: UserProfile | null;
  role: UserRole;
  isAdmin: boolean;
  loading: boolean;
  isConfigured: boolean;
  signInWithPassword: (email: string, password: string) => Promise<{ error: AuthResultError | AuthError | null }>;
  signUpWithPassword: (email: string, password: string, fullName?: string) => Promise<{ error: AuthResultError | AuthError | null; data: any }>;
  signOut: () => Promise<{ error: AuthResultError | AuthError | null }>;
  resetPasswordForEmail: (email: string) => Promise<{ error: AuthResultError | AuthError | null }>;
  refreshProfile: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [role, setRole] = useState<UserRole>('user');
  const [loading, setLoading] = useState<boolean>(true);

  const fetchProfile = async (userId: string) => {
    try {
      const { data, error } = await supabase
        .from('profiles')
        .select('*')
        .eq('id', userId)
        .maybeSingle();

      if (data && !error) {
        setProfile(data as UserProfile);
        setRole((data.role === 'admin' ? 'admin' : 'user') as UserRole);
      } else {
        setProfile(null);
        setRole('user');
      }
    } catch (err) {
      console.warn('Error fetching user profile:', err);
      setRole('user');
    }
  };

  useEffect(() => {
    // Get initial active session
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      const currentUser = session?.user ?? null;
      setUser(currentUser);
      if (currentUser) {
        fetchProfile(currentUser.id).finally(() => setLoading(false));
      } else {
        setLoading(false);
      }
    }).catch((err) => {
      console.warn('Error fetching Supabase session:', err);
      setLoading(false);
    });

    // Listen for real-time auth changes (sign in, sign out, token refresh)
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
      const currentUser = session?.user ?? null;
      setUser(currentUser);
      if (currentUser) {
        fetchProfile(currentUser.id);
      } else {
        setProfile(null);
        setRole('user');
      }
      setLoading(false);
    });

    return () => {
      subscription.unsubscribe();
    };
  }, []);

  const signInWithPassword = async (email: string, password: string) => {
    console.log('[AUTH PROXY] Initiating same-origin authentication request', {
      endpoint: '/api/auth-proxy',
      email: email.trim()
    });

    try {
      const response = await fetch('/api/auth-proxy', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          email: email.trim(),
          password
        })
      });

      const data = await response.json().catch(() => ({}));

      console.log('[AUTH PROXY] Serverless proxy response received', {
        status: response.status,
        ok: response.ok,
        hasAccessToken: Boolean(data?.access_token),
        hasUser: Boolean(data?.user),
        errorCode: data?.error_code || data?.code,
        errorMessage: data?.error_description || data?.msg || data?.message
      });

      if (!response.ok) {
        const errorMsg = data?.error_description || data?.msg || data?.message || `HTTP ${response.status} Authentication Failed`;
        return {
          error: {
            name: 'AuthError',
            status: response.status,
            message: errorMsg
          }
        };
      }

      // If successful, establish the session in the Supabase client
      if (data?.access_token && data?.refresh_token) {
        const { error: sessionError } = await supabase.auth.setSession({
          access_token: data.access_token,
          refresh_token: data.refresh_token
        });
        if (sessionError) {
          console.warn('[AUTH PROXY] Supabase setSession warning:', sessionError);
        }
      }

      return { error: null };
    } catch (err: any) {
      console.error('[AUTH PROXY] Network error during proxy request:', {
        name: err?.name,
        message: err?.message
      });
      return {
        error: {
          name: 'NetworkError',
          message: err?.message || 'Authentication request failed.'
        }
      };
    }
  };

  const signUpWithPassword = async (email: string, password: string, fullName?: string) => {
    try {
      console.log('[AUTH] Calling Supabase signUp');
      const res = await supabase.auth.signUp({
        email: email.trim(),
        password,
        options: {
          data: {
            full_name: fullName || ''
          }
        }
      });
      console.log('[AUTH] Supabase signUp response', { data: res.data, error: res.error });
      return { error: res.error, data: res.data };
    } catch (err: any) {
      console.error('[AUTH] Supabase signUp error:', err);
      return {
        error: {
          name: 'NetworkError',
          message: err.message || 'Account registration failed.'
        },
        data: null
      };
    }
  };

  const signOut = async () => {
    try {
      console.log('[AUTH] Calling Supabase signOut');
      const res = await supabase.auth.signOut();
      setUser(null);
      setSession(null);
      setProfile(null);
      setRole('user');
      return { error: res.error };
    } catch (err: any) {
      setUser(null);
      setSession(null);
      setProfile(null);
      setRole('user');
      return { error: null };
    }
  };

  const resetPasswordForEmail = async (email: string) => {
    try {
      console.log('[AUTH] Calling Supabase resetPasswordForEmail');
      const redirectTo = window.location.origin;
      const res = await supabase.auth.resetPasswordForEmail(email.trim(), {
        redirectTo
      });
      console.log('[AUTH] Supabase resetPassword response', { data: res.data, error: res.error });
      return { error: res.error };
    } catch (err: any) {
      console.error('[AUTH] Supabase resetPassword error:', err);
      return {
        error: {
          name: 'NetworkError',
          message: err.message || 'Failed to dispatch password recovery email.'
        }
      };
    }
  };

  const refreshProfile = async () => {
    if (user) {
      await fetchProfile(user.id);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        session,
        profile,
        role,
        isAdmin: role === 'admin',
        loading,
        isConfigured: isSupabaseConfigured,
        signInWithPassword,
        signUpWithPassword,
        signOut,
        resetPasswordForEmail,
        refreshProfile
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
