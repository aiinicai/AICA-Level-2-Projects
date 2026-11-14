// Backend connection. When VITE_SUPABASE_URL / VITE_SUPABASE_ANON_KEY are set, OCR and other
// server features call Supabase Edge Functions; otherwise the app runs in local demo mode.
import { createClient, type SupabaseClient } from '@supabase/supabase-js';

const url = import.meta.env.VITE_SUPABASE_URL as string | undefined;
const key = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined;

export const supabase: SupabaseClient | null = url && key ? createClient(url, key) : null;
/** Demo mode only when asked for (VITE_DEMO=true) or in local development without a backend.
 *  A production build without Supabase settings must NOT quietly keep business data in one browser. */
export const isDemo = !supabase && (import.meta.env.VITE_DEMO === 'true' || import.meta.env.DEV);
export const misconfigured = !supabase && !isDemo;
