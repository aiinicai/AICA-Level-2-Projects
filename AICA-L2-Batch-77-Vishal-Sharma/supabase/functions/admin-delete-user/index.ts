// Invoked directly from the Admin Users screen (supabase.functions.invoke).
// Runs with the service_role key, which must never be shipped to the
// browser — this function is the only place that key is used, and only
// after confirming the caller is an Admin.
//
// Deleting the auth.users row cascades to profiles (on delete cascade), but
// every task-side reference to profiles (assignor/primary/secondary/closed_by/
// requested_by/decided_by/author_id) is a plain RESTRICT foreign key on
// purpose — a person who has ever touched a task can't be deleted without
// destroying that task's history. Postgres rejects the delete outright in
// that case, but GoTrue's admin API collapses *any* DB-level delete error
// into the generic "Database error deleting user" and doesn't surface the
// underlying constraint-violation text — so detecting it after the fact
// isn't reliable. Instead, check for references up front and return a
// specific, correct reason before ever attempting the delete.

import { createClient } from 'jsr:@supabase/supabase-js@2'

const SUPABASE_URL = Deno.env.get('SUPABASE_URL')!
const SERVICE_ROLE_KEY = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
const ANON_KEY = Deno.env.get('SUPABASE_ANON_KEY')!

// Kept in sync with the protect_profile_privilege_columns trigger, which
// already blocks this account from ever being demoted — deletion is a
// different code path (DELETE, not UPDATE) so it needs its own guard.
const PERMANENT_ADMIN_EMAIL = 'hardiksharma.ecooglobal@gmail.com'

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: CORS_HEADERS })
  }

  try {
    const authHeader = req.headers.get('Authorization')
    if (!authHeader) return json({ error: 'Missing Authorization header' }, 401)

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
    if (!callerProfile?.is_admin) return json({ error: 'Only an Admin can delete users' }, 403)

    const { user_id } = await req.json()
    if (!user_id) return json({ error: 'user_id is required' }, 400)

    if (user_id === user.id) {
      return json({ error: "You can't delete your own account." }, 400)
    }

    const admin = createClient(SUPABASE_URL, SERVICE_ROLE_KEY)

    const { data: targetProfile } = await admin
      .from('profiles')
      .select('email')
      .eq('id', user_id)
      .single()
    if (targetProfile?.email === PERMANENT_ADMIN_EMAIL) {
      return json({ error: 'This account is a permanent Admin and cannot be deleted.' }, 400)
    }

    const [tasksRef, revisionsRef, commentsRef] = await Promise.all([
      admin
        .from('tasks')
        .select('id', { count: 'exact', head: true })
        .or(
          `assignor_id.eq.${user_id},primary_assignee_id.eq.${user_id},secondary_assignee_id.eq.${user_id},closed_by.eq.${user_id}`,
        ),
      admin
        .from('task_revisions')
        .select('id', { count: 'exact', head: true })
        .or(`requested_by.eq.${user_id},decided_by.eq.${user_id}`),
      admin.from('task_comments').select('id', { count: 'exact', head: true }).eq('author_id', user_id),
    ])
    const isReferenced = (tasksRef.count ?? 0) > 0 || (revisionsRef.count ?? 0) > 0 || (commentsRef.count ?? 0) > 0
    if (isReferenced) {
      return json(
        {
          error:
            "Can't delete — this person is referenced by at least one existing task (assigned, requested a revision, decided one, closed a task, or commented). Revoke their approval instead if you want to remove their access.",
        },
        400,
      )
    }

    const { error } = await admin.auth.admin.deleteUser(user_id)
    if (error) return json({ error: error.message }, 400)

    return json({ ok: true })
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
