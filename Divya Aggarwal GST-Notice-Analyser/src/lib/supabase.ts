import { createClient } from '@supabase/supabase-js';

// These come from Netlify env vars (or .env.local for local dev).
// The anon key is safe to expose in the browser — access is enforced by
// Row-Level Security on the database, not by keeping this key secret.
const url = import.meta.env.VITE_SUPABASE_URL;
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

if (!url || !anonKey) {
  // Surfaced clearly instead of a cryptic runtime failure deep in a query.
  // eslint-disable-next-line no-console
  console.error(
    'Missing VITE_SUPABASE_URL / VITE_SUPABASE_ANON_KEY. ' +
    'Set them in Netlify (Site settings → Environment variables) or in desktop/.env.local — see SUPABASE-SETUP.md.',
  );
}

export const supabase = createClient(url ?? '', anonKey ?? '', {
  auth: {
    persistSession: true,
    autoRefreshToken: true,
    detectSessionInUrl: true,
  },
});

export const isSupabaseConfigured = Boolean(url && anonKey);
