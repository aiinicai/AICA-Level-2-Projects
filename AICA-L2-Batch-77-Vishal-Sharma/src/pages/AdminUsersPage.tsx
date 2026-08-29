import { useState, type FormEvent } from 'react'
import { useAuth } from '../auth/AuthProvider'
import { useDirectory } from '../lib/DirectoryProvider'
import { supabase } from '../lib/supabase'

// Enforced at the database level too (protect_profile_privilege_columns
// trigger) — this account can never be demoted, by anyone, including
// itself. Kept in sync here just so the UI shows it as locked instead of
// letting someone uncheck it and hit a confusing error.
const PERMANENT_ADMIN_EMAIL = 'ecooglobal@gmail.com'

export function AdminUsersPage() {
  const { profile: myProfile } = useAuth()
  const { profiles, reloadClients } = useDirectory()
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteName, setInviteName] = useState('')
  const [inviting, setInviting] = useState(false)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const setFlag = async (
    id: string,
    field: 'is_admin' | 'can_create_and_assign' | 'is_approved',
    value: boolean,
  ) => {
    setError(null)
    const { error } = await supabase.from('profiles').update({ [field]: value }).eq('id', id)
    if (error) setError(error.message)
    else await reloadClients() // directory reload also re-pulls profiles
  }

  const sortedProfiles = [...profiles].sort((a, b) => {
    if (a.is_approved !== b.is_approved) return a.is_approved ? 1 : -1
    return (a.full_name || a.email).localeCompare(b.full_name || b.email)
  })

  const invite = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setNotice(null)
    setInviting(true)
    try {
      const { error } = await supabase.functions.invoke('admin-invite-user', {
        body: { email: inviteEmail, full_name: inviteName },
      })
      if (error) throw error
      setNotice(`Invited ${inviteEmail}.`)
      setInviteEmail('')
      setInviteName('')
      await reloadClients()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong.')
    } finally {
      setInviting(false)
    }
  }

  const deleteUser = async (id: string, label: string) => {
    if (!confirm(`Delete ${label}? This cannot be undone.`)) return
    setError(null)
    setNotice(null)
    setDeletingId(id)
    try {
      const { error } = await supabase.functions.invoke('admin-delete-user', {
        body: { user_id: id },
      })
      if (error) {
        // FunctionsHttpError's own .message is a generic "non-2xx status code" —
        // the actual reason (e.g. "referenced by a task") is in the JSON body.
        const body = await error.context?.json?.().catch(() => null)
        throw new Error(body?.error || error.message)
      }
      setNotice(`Deleted ${label}.`)
      await reloadClients()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong.')
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <div className="max-w-4xl flex flex-col gap-8">
      <h1 className="font-serif text-2xl font-semibold text-ink">Manage Users</h1>

      <form onSubmit={invite} className="bg-paper-raised border border-line rounded-lg shadow-sm p-4 flex flex-col gap-3">
        <h2 className="font-mono text-xs uppercase tracking-wide text-ink-soft">Invite Someone New</h2>
        <div className="flex gap-2">
          <input
            type="email"
            required
            placeholder="name@company.com"
            value={inviteEmail}
            onChange={(e) => setInviteEmail(e.target.value)}
            className="flex-1 rounded-md border border-line bg-paper px-3 py-1.5 text-sm text-ink transition-colors focus:outline-none focus:border-bark focus:ring-2 focus:ring-bark/15"
          />
          <input
            type="text"
            placeholder="Full name"
            value={inviteName}
            onChange={(e) => setInviteName(e.target.value)}
            className="flex-1 rounded-md border border-line bg-paper px-3 py-1.5 text-sm text-ink transition-colors focus:outline-none focus:border-bark focus:ring-2 focus:ring-bark/15"
          />
          <button
            type="submit"
            disabled={inviting}
            className="text-sm font-medium px-4 py-1.5 rounded-md bg-bark-gradient disabled:opacity-50 text-white shadow-sm hover:shadow-md transition"
          >
            {inviting ? 'Inviting…' : 'Invite'}
          </button>
        </div>
        {notice && <p className="text-sm text-moss">{notice}</p>}
      </form>

      {error && <p className="text-sm text-rust bg-rust-bg rounded-md px-3 py-2">{error}</p>}

      <div className="bg-paper-raised border border-line rounded-lg shadow-sm overflow-hidden overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-line text-left text-ink-soft font-mono text-xs uppercase tracking-wide">
              <th className="px-4 py-2 font-medium whitespace-nowrap">Name</th>
              <th className="px-4 py-2 font-medium whitespace-nowrap">Email</th>
              <th className="px-4 py-2 font-medium text-center whitespace-nowrap">Approved</th>
              <th className="px-4 py-2 font-medium text-center whitespace-nowrap">Admin</th>
              <th className="px-4 py-2 font-medium text-center whitespace-nowrap">Can Create &amp; Assign</th>
              <th className="px-4 py-2 font-medium text-center whitespace-nowrap">Actions</th>
            </tr>
          </thead>
          <tbody>
            {sortedProfiles.map((p) => (
              <tr
                key={p.id}
                className={`border-b border-line last:border-0 ${!p.is_approved ? 'bg-gold-bg/40' : ''}`}
              >
                <td className="px-4 py-2 text-ink">
                  <div className="flex items-center gap-2">
                    {p.full_name || '—'}
                    {!p.is_approved && (
                      <span className="font-mono text-[10px] uppercase tracking-wide px-2 py-0.5 rounded-full bg-gold-bg text-gold-ink whitespace-nowrap">
                        Pending approval
                      </span>
                    )}
                  </div>
                </td>
                <td className="px-4 py-2 text-ink-soft">{p.email}</td>
                <td className="px-4 py-2 text-center">
                  {p.is_approved ? (
                    <input
                      type="checkbox"
                      checked={p.is_approved}
                      onChange={(e) => setFlag(p.id, 'is_approved', e.target.checked)}
                      title="Uncheck to revoke access"
                      className="h-4 w-4 accent-bark cursor-pointer"
                    />
                  ) : (
                    <button
                      onClick={() => setFlag(p.id, 'is_approved', true)}
                      className="text-xs font-medium px-3 py-1 rounded-md bg-bark-gradient text-white transition-colors"
                    >
                      Approve
                    </button>
                  )}
                </td>
                <td className="px-4 py-2 text-center">
                  {p.email === PERMANENT_ADMIN_EMAIL ? (
                    <span
                      title="Permanent Admin — cannot be changed"
                      className="font-mono text-[10px] uppercase tracking-wide px-2 py-0.5 rounded-full bg-gold-bg text-gold-ink"
                    >
                      Locked
                    </span>
                  ) : (
                    <input
                      type="checkbox"
                      checked={p.is_admin}
                      onChange={(e) => setFlag(p.id, 'is_admin', e.target.checked)}
                      className="h-4 w-4 accent-bark cursor-pointer"
                    />
                  )}
                </td>
                <td className="px-4 py-2 text-center">
                  <input
                    type="checkbox"
                    checked={p.can_create_and_assign}
                    onChange={(e) => setFlag(p.id, 'can_create_and_assign', e.target.checked)}
                    className="h-4 w-4 accent-bark cursor-pointer"
                  />
                </td>
                <td className="px-4 py-2 text-center">
                  {p.email === PERMANENT_ADMIN_EMAIL || p.id === myProfile?.id ? (
                    <span className="text-ink-soft/40">—</span>
                  ) : (
                    <button
                      onClick={() => deleteUser(p.id, p.full_name || p.email)}
                      disabled={deletingId === p.id}
                      className="text-xs font-medium px-3 py-1 rounded-md text-rust hover:bg-rust-bg disabled:opacity-50 transition-colors"
                    >
                      {deletingId === p.id ? 'Deleting…' : 'Delete'}
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
