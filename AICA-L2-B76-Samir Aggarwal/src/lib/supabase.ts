import { createClient } from '@supabase/supabase-js'

const url = import.meta.env.VITE_SUPABASE_URL as string | undefined
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined

/**
 * These are baked in at build time by Vite, so on Railway they must be set as
 * service variables BEFORE the build step, not only at runtime.
 */
export const isSupabaseConfigured = Boolean(url && anonKey)

/** The project origin, for preconnect hints. */
export const supabaseUrl = url ?? null

if (!isSupabaseConfigured && import.meta.env.DEV) {
  console.warn(
    '[config] VITE_SUPABASE_URL / VITE_SUPABASE_ANON_KEY are missing. ' +
      'Copy .env.example to .env and fill them in.',
  )
}

export const supabase = createClient(
  url ?? 'https://placeholder.supabase.co',
  anonKey ?? 'placeholder-anon-key',
  {
    auth: {
      persistSession: true,
      autoRefreshToken: true,
      detectSessionInUrl: true,
      storage: typeof window === 'undefined' ? undefined : window.localStorage,
    },
  },
)

/** Turns a Supabase/Postgres error into something a CA can actually read. */
export function friendlyError(error: unknown): string {
  const message =
    typeof error === 'object' && error && 'message' in error
      ? String((error as { message: unknown }).message)
      : String(error)

  if (message.includes('EMAIL_NOT_AUTHORISED')) {
    return 'This email is not authorised. Please ask your firm administrator to add you first.'
  }
  if (message.includes('Only an administrator can change')) {
    return 'Only an administrator can change the assignee, client or due date.'
  }
  if (message.includes('duplicate key') && message.includes('client_code')) {
    return 'That client code is already in use.'
  }
  if (message.includes('duplicate key') && message.includes('allowed_emails')) {
    return 'That email has already been added to the employee list.'
  }
  if (message.includes('duplicate key') && message.includes('task_master')) {
    return 'A task with this name already exists in that category.'
  }
  if (message.includes('row-level security')) {
    return 'You do not have permission to do that.'
  }
  // Worth its own message: an unconfirmed account fails to sign in with what
  // looks like a wrong password, and people go hunting for the wrong problem.
  if (/email.?not.?confirmed/i.test(message)) {
    return (
      'This email address has not been confirmed yet. Open the confirmation link that was ' +
      'emailed to you, or ask your administrator to confirm the account.'
    )
  }
  if (message.includes('New password should be different')) {
    return 'That is already your current password. Choose a different one.'
  }
  if (message.includes('Invalid login credentials')) {
    return 'Incorrect email or password. If you have never confirmed your email address, ask your administrator to check the account.'
  }
  if (/rate limit|too many requests/i.test(message)) {
    return 'Too many attempts. Wait a few minutes and try again.'
  }
  return message
}
