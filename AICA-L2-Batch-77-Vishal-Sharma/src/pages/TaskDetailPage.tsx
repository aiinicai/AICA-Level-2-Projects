import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useAuth } from '../auth/AuthProvider'
import { useDirectory } from '../lib/DirectoryProvider'
import {
  addComment,
  decideRevision,
  delegateSecondaryAssignee,
  deleteTask,
  fetchComments,
  fetchRevisions,
  fetchTask,
  reopenTask,
  requestRevision,
  updateTaskAdminRemark,
  updateTaskDescription,
  updateTaskStatus,
} from '../lib/queries'
import type { TaskComment, TaskRevision, TaskStatus, TaskWithDueDate } from '../types/database'
import { StatusBadge, UrgencyBadge } from '../components/Badges'
import { Select } from '../components/Select'
import { AdminRemarkCell } from '../components/AdminRemarkCell'
import { Loading } from '../components/Loading'
import { RevisionRow } from '../components/RevisionRow'

const STATUS_OPTIONS: TaskStatus[] = ['Open', 'In Process', 'Pending at Client', 'Pending at Department', 'Hold']

export function TaskDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { profile } = useAuth()
  const { profileName, clientName, profiles } = useDirectory()

  const [task, setTask] = useState<TaskWithDueDate | null>(null)
  const [revisions, setRevisions] = useState<TaskRevision[]>([])
  const [comments, setComments] = useState<TaskComment[]>([])
  const [error, setError] = useState<string | null>(null)
  const [editingDescription, setEditingDescription] = useState(false)
  const [descriptionDraft, setDescriptionDraft] = useState('')

  const load = async () => {
    if (!id) return
    const [t, r, c] = await Promise.all([fetchTask(id), fetchRevisions(id), fetchComments(id)])
    setTask(t)
    setRevisions(r)
    setComments(c)
  }

  useEffect(() => {
    load()
  }, [id])

  if (!task) return <Loading />

  const isAdmin = !!profile?.is_admin
  const isPrimary = task.primary_assignee_id === profile?.id
  const isSecondary = task.secondary_assignee_id === profile?.id
  const isAssignee = isPrimary || isSecondary
  const canDelegate = isPrimary && (isAdmin || profile?.can_create_and_assign)
  // A Primary assignee with can_create_and_assign may decide revisions on
  // their task, but never their own request — same rule as the RLS policy.
  const canDecideRevision = (revision: TaskRevision) =>
    isAdmin || (isPrimary && profile?.can_create_and_assign && revision.requested_by !== profile?.id)
  const isClosed = task.status === 'Closed'
  const canAct = isAdmin || (!isClosed && isAssignee)
  const pendingRevisionCount = revisions.filter((r) => r.status === 'pending').length

  const runAction = async (fn: () => Promise<void>) => {
    setError(null)
    try {
      await fn()
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong.')
    }
  }

  const startEditingDescription = () => {
    setDescriptionDraft(task.description)
    setEditingDescription(true)
  }

  const saveDescription = async () => {
    const trimmed = descriptionDraft.trim()
    if (!trimmed || trimmed === task.description) {
      setEditingDescription(false)
      return
    }
    await runAction(() => updateTaskDescription(task.id, trimmed))
    setEditingDescription(false)
  }

  return (
    <div className="max-w-2xl flex flex-col gap-8">
      <div>
        <div className="flex items-center gap-2 text-xs text-ink-soft font-mono mb-1">
          <span>{task.task_number}</span>
          <span>·</span>
          <span>{clientName(task.client_id)}</span>
        </div>
        <div className="flex items-start justify-between gap-4">
          {editingDescription ? (
            <div className="flex-1 flex flex-col gap-2">
              <textarea
                autoFocus
                rows={3}
                value={descriptionDraft}
                onChange={(e) => setDescriptionDraft(e.target.value)}
                className="w-full rounded-md border border-line bg-paper px-3 py-2 text-sm text-ink transition-colors focus:outline-none focus:border-bark focus:ring-2 focus:ring-bark/15"
              />
              <div className="flex gap-2">
                <button
                  onClick={saveDescription}
                  className="text-xs font-medium px-3 py-1.5 rounded-md bg-bark-gradient text-white transition-colors"
                >
                  Save
                </button>
                <button
                  onClick={() => setEditingDescription(false)}
                  className="text-xs font-medium px-3 py-1.5 rounded-md text-ink-soft hover:text-ink transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <h1 className="font-serif text-xl font-semibold text-ink flex items-start gap-2">
              {task.description}
              {isAdmin && (
                <button
                  onClick={startEditingDescription}
                  className="shrink-0 text-xs font-sans font-normal text-ink-soft hover:text-bark underline underline-offset-2"
                >
                  Edit
                </button>
              )}
            </h1>
          )}
          <div className="flex gap-2 shrink-0">
            <UrgencyBadge urgency={task.urgency} />
            <StatusBadge status={task.status} />
          </div>
        </div>

        {pendingRevisionCount > 0 && (
          <a
            href="#revisions"
            onClick={(e) => {
              e.preventDefault()
              document.getElementById('revisions')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
            }}
            className="mt-3 inline-flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-full bg-gold-bg text-gold-ink hover:opacity-80 transition-opacity w-fit"
          >
            <PendingClockIcon />
            {pendingRevisionCount} pending revision request{pendingRevisionCount === 1 ? '' : 's'} — jump to it ↓
          </a>
        )}
      </div>

      {error && <p className="text-sm text-rust bg-rust-bg rounded-md px-3 py-2">{error}</p>}

      <dl className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm bg-paper-raised border border-line rounded-lg shadow-sm p-4">
        <Field label="Assignor" value={profileName(task.assignor_id)} />
        <Field label="Primary Assignee" value={profileName(task.primary_assignee_id)} />
        <Field
          label="Secondary Assignee"
          value={task.secondary_assignee_id ? profileName(task.secondary_assignee_id) : '—'}
        />
        <Field label="Created Date" value={new Date(task.created_at).toLocaleDateString()} />
        <Field label="Planned Date (fixed)" value={task.planned_date} />
        <Field label="Effective Due Date" value={task.effective_due_date} />
        <Field
          label="Closed Date"
          value={
            task.closed_at
              ? `${new Date(task.closed_at).toLocaleDateString()} ${new Date(task.closed_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`
              : '—'
          }
        />
        <Field label="Closed By" value={task.closed_by ? profileName(task.closed_by) : '—'} />
      </dl>

      <section className="flex flex-col gap-2">
        <h2 className="font-mono text-xs uppercase tracking-wide text-ink-soft">Admin's Remark</h2>
        <div className="bg-paper-raised border border-line rounded-lg shadow-sm px-3 py-2 text-sm">
          <AdminRemarkCell
            value={task.admin_remark}
            isAdmin={isAdmin}
            onSave={(body) => runAction(() => updateTaskAdminRemark(task.id, body))}
          />
        </div>
      </section>

      {canAct && (
        <section className="flex flex-col gap-3">
          <h2 className="font-mono text-xs uppercase tracking-wide text-ink-soft">Actions</h2>
          <div className="bg-paper-raised border border-line rounded-lg shadow-sm p-4 flex flex-col gap-3">
            <div className="flex flex-wrap items-center gap-2">
              {!isClosed &&
                STATUS_OPTIONS.filter((s) => s !== task.status).map((s) => (
                  <button
                    key={s}
                    onClick={() => runAction(() => updateTaskStatus(task.id, s))}
                    className="text-xs font-medium px-3 py-1.5 rounded-md border border-line text-ink-soft hover:border-bark hover:text-ink transition-colors"
                  >
                    Mark {s}
                  </button>
                ))}
              {!isClosed && (
                <button
                  onClick={() => {
                    if (confirm('Close this task? It cannot be reversed except by an Admin.')) {
                      runAction(() => updateTaskStatus(task.id, 'Closed'))
                    }
                  }}
                  className="text-xs font-medium px-3 py-1.5 rounded-md bg-moss text-white hover:opacity-90 transition-opacity"
                >
                  Close Task
                </button>
              )}
              {isClosed && isAdmin && (
                <button
                  onClick={() => runAction(() => reopenTask(task.id))}
                  className="text-xs font-medium px-3 py-1.5 rounded-md bg-gold-bg text-gold-ink hover:opacity-80 transition-opacity"
                >
                  Reopen Task
                </button>
              )}
              {isAdmin && (
                <button
                  onClick={() => {
                    if (confirm('Permanently delete this task? This cannot be undone.')) {
                      runAction(async () => {
                        await deleteTask(task.id)
                        navigate('/tasks')
                      })
                    }
                  }}
                  className="text-xs font-medium px-3 py-1.5 rounded-md border border-rust text-rust hover:bg-rust-bg transition-colors"
                >
                  Delete
                </button>
              )}
            </div>

            {canDelegate && !task.secondary_assignee_id && !isClosed && (
              <DelegateForm
                profiles={profiles.filter((p) => p.id !== task.primary_assignee_id)}
                onDelegate={(pid) => runAction(() => delegateSecondaryAssignee(task.id, pid))}
              />
            )}
          </div>
        </section>
      )}

      <RevisionsSection
        revisions={revisions}
        canRequest={isAssignee && !isClosed}
        canDecide={canDecideRevision}
        onRequest={(date, reason) => runAction(() => requestRevision(task.id, date, reason))}
        onDecide={(revId, decision, impacts, note) =>
          runAction(() => decideRevision(revId, decision, impacts, note))
        }
        profileName={profileName}
      />

      <CommentsSection
        comments={comments}
        profileName={profileName}
        onAdd={(body) => runAction(() => addComment(task.id, body))}
      />
    </div>
  )
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase tracking-wide text-ink-soft">{label}</dt>
      <dd className="text-ink">{value}</dd>
    </div>
  )
}

function PendingClockIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 16 16" fill="none" className="shrink-0">
      <circle cx="8" cy="8" r="6.5" stroke="currentColor" strokeWidth="1.4" />
      <path d="M8 4.5V8l2.5 1.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function DelegateForm({
  profiles,
  onDelegate,
}: {
  profiles: { id: string; full_name: string; email: string }[]
  onDelegate: (id: string) => void
}) {
  const [selected, setSelected] = useState('')
  return (
    <div className="flex items-center gap-2 pt-1">
      <div className="w-56">
        <Select
          value={selected}
          onValueChange={setSelected}
          placeholder="Delegate to…"
          options={profiles.map((p) => ({ value: p.id, label: p.full_name || p.email }))}
        />
      </div>
      <button
        disabled={!selected}
        onClick={() => selected && onDelegate(selected)}
        className="text-xs font-medium px-3 py-1.5 rounded-md bg-bark-gradient disabled:opacity-40 text-white transition-colors"
      >
        Delegate
      </button>
    </div>
  )
}

function RevisionsSection({
  revisions,
  canRequest,
  canDecide,
  onRequest,
  onDecide,
  profileName,
}: {
  revisions: TaskRevision[]
  canRequest: boolean
  canDecide: (revision: TaskRevision) => boolean | undefined
  onRequest: (date: string, reason: string) => void
  onDecide: (id: string, decision: 'approved' | 'rejected', impacts: boolean | null, note: string) => void
  profileName: (id: string) => string
}) {
  const [proposedDate, setProposedDate] = useState('')
  const [reason, setReason] = useState('')

  const submitRequest = (e: FormEvent) => {
    e.preventDefault()
    if (!proposedDate) return
    onRequest(proposedDate, reason)
    setProposedDate('')
    setReason('')
  }

  return (
    <section id="revisions" className="flex flex-col gap-3 scroll-mt-4">
      <h2 className="font-mono text-xs uppercase tracking-wide text-ink-soft">Due Date Revisions</h2>

      {revisions.length === 0 && <p className="text-sm text-ink-soft">No revisions requested yet.</p>}

      <div className="flex flex-col gap-2">
        {revisions.map((r) => (
          <RevisionRow key={r.id} revision={r} canDecide={!!canDecide(r)} onDecide={onDecide} profileName={profileName} />
        ))}
      </div>

      {canRequest && (
        <form onSubmit={submitRequest} className="flex items-end gap-2 pt-1">
          <div>
            <label className="block text-xs text-ink-soft mb-1">New date</label>
            <input
              type="date"
              required
              value={proposedDate}
              onChange={(e) => setProposedDate(e.target.value)}
              className="rounded-md border border-line bg-paper px-3 py-1.5 text-sm text-ink transition-colors focus:outline-none focus:border-bark focus:ring-2 focus:ring-bark/15"
            />
          </div>
          <div className="flex-1">
            <label className="block text-xs text-ink-soft mb-1">Reason</label>
            <input
              type="text"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="w-full rounded-md border border-line bg-paper px-3 py-1.5 text-sm text-ink transition-colors focus:outline-none focus:border-bark focus:ring-2 focus:ring-bark/15"
            />
          </div>
          <button
            type="submit"
            className="text-xs font-medium px-3 py-1.5 rounded-md bg-bark-gradient text-white transition-colors"
          >
            Request
          </button>
        </form>
      )}
    </section>
  )
}

function CommentsSection({
  comments,
  profileName,
  onAdd,
}: {
  comments: TaskComment[]
  profileName: (id: string) => string
  onAdd: (body: string) => void
}) {
  const [body, setBody] = useState('')

  const submit = (e: FormEvent) => {
    e.preventDefault()
    if (!body.trim()) return
    onAdd(body.trim())
    setBody('')
  }

  return (
    <section className="flex flex-col gap-3 pb-8">
      <h2 className="font-mono text-xs uppercase tracking-wide text-ink-soft">Remarks</h2>
      <div className="flex flex-col gap-2">
        {comments.map((c) => (
          <div key={c.id} className="text-sm bg-paper-raised border border-line rounded-md px-3 py-2">
            <div className="flex items-center justify-between text-xs text-ink-soft mb-1">
              <span className="font-medium text-ink">{profileName(c.author_id)}</span>
              <span>{new Date(c.created_at).toLocaleString()}</span>
            </div>
            <p className="text-ink">{c.body}</p>
          </div>
        ))}
        {comments.length === 0 && <p className="text-sm text-ink-soft">No remarks yet.</p>}
      </div>
      <form onSubmit={submit} className="flex gap-2">
        <input
          type="text"
          placeholder="Add a remark…"
          value={body}
          onChange={(e) => setBody(e.target.value)}
          className="flex-1 rounded-md border border-line bg-paper px-3 py-1.5 text-sm text-ink transition-colors focus:outline-none focus:border-bark focus:ring-2 focus:ring-bark/15"
        />
        <button
          type="submit"
          className="text-xs font-medium px-3 py-1.5 rounded-md bg-bark-gradient text-white transition-colors"
        >
          Post
        </button>
      </form>
    </section>
  )
}
