import { createClient } from '@supabase/supabase-js';

// Explicit production constants
const DEFAULT_SUPABASE_URL = 'https://omybszbzealjvaltzvpi.supabase.co';
const DEFAULT_SUPABASE_KEY = 'sb_publishable_eujc45-UUKFqGPabJx6cvw_vOCSMBCy';

// Clean and sanitize build-time / runtime environment variables
const rawEnvUrl = (import.meta.env.VITE_SUPABASE_URL || '').trim().replace(/^["']|["']$/g, '');
const rawEnvKey = (
  import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY || 
  import.meta.env.VITE_SUPABASE_ANON_KEY || 
  ''
).trim().replace(/^["']|["']$/g, '');

export const supabaseUrl = (rawEnvUrl && rawEnvUrl.startsWith('https://') && rawEnvUrl.includes('supabase.co'))
  ? rawEnvUrl.replace(/\/+$/, '')
  : DEFAULT_SUPABASE_URL;

export const supabasePublishableKey = (rawEnvKey && rawEnvKey.length > 10)
  ? rawEnvKey
  : DEFAULT_SUPABASE_KEY;

export const isSupabaseConfigured = Boolean(
  supabaseUrl && 
  supabasePublishableKey && 
  supabaseUrl.startsWith('https://')
);

const projectRef = supabaseUrl.match(/https:\/\/([a-z0-9-]+)\.supabase\.co/)?.[1] || 'unknown';

console.log('[SUPABASE DEBUG]', {
  SUPABASE_URL_PRESENT: Boolean(supabaseUrl),
  SUPABASE_KEY_PRESENT: Boolean(supabasePublishableKey),
  projectRef,
  configured: isSupabaseConfigured
});

// Create Supabase client with standard client-side browser configuration
export const supabase = createClient(
  supabaseUrl,
  supabasePublishableKey,
  {
    auth: {
      persistSession: true,
      autoRefreshToken: true,
      detectSessionInUrl: true,
      storageKey: 'cfo_dashboard_auth_token_v1'
    }
  }
);
