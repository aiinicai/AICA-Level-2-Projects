// Invoked directly from the Admin Users screen (supabase.functions.invoke).
// Runs with the service_role key, which must never be shipped to the
// browser — this function is the only place that key is used, and only
// after confirming the caller is an Admin.

import { createClient } from 'jsr:@supabase/supabase-js@2'

const SUPABASE_URL = Deno.env.get('SUPABASE_URL')!
const SERVICE_ROLE_KEY = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
const ANON_KEY = Deno.env.get('SUPABASE_ANON_KEY')!

Deno.serve(async (req) => {
  // Browser calls to Edge Functions are cross-origin — without handling the
  // preflight OPTIONS request and echoing CORS headers back, the browser
  // blocks the real request before it's ever sent (shows up as a vague
  // "failed to fetch" with zero server-side logs, since it never arrives).
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: CORS_HEADERS })
  }

  try {
    const authHeader = req.headers.get('Authorization')
    if (!authHeader) return json({ error: 'Missing Authorization header' }, 401)

    // Verify the caller with their own JWT (RLS-respecting client) and check
    // the is_admin flag on their profile.
    const callerClient = createClient(SUPABASE_URL, ANON_KEY, {
      global: { headers: { Authorization: authHeader } },
    })
    const {
      data: { user },
    } = await callerClient.auth.getUser()
    if (!user) return json({ error: 'Not signed in' }, 401)

    const { data: callerProfile } = await callerClient
      .from('profiles')
      .select('is_admin')
      .eq('id', user.id)
      .single()
    if (!callerProfile?.is_admin) return json({ error: 'Only an Admin can invite users' }, 403)

    const { email, full_name } = await req.json()
    if (!email) return json({ error: 'Email is required' }, 400)

    const admin = createClient(SUPABASE_URL, SERVICE_ROLE_KEY)
    const { data, error } = await admin.auth.admin.inviteUserByEmail(email, {
      // handle_new_user() reads this to mark the profile pre-approved —
      // being invited by an Admin IS the approval, no separate step needed.
      data: { full_name: full_name ?? '', invited: true },
    })
    if (error) return json({ error: error.message }, 400)

    return json({ ok: true, user_id: data.user.id })
  } catch (err) {
    return json({ error: err instanceof Error ? err.message : 'Unknown error' }, 500)
  }
})

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
}

function json(body: unknown, status: number) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
  })
}
