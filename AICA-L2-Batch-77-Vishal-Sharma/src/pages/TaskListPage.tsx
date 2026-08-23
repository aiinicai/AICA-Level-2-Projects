import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../auth/AuthProvider'
import {
  addComment,
  fetchMyVisibleTasks,
  fetchPendingRevisionsCount,
  updateTaskAdminRemark,
  updateTaskStatus,
} from '../lib/queries'
import type { TaskStatus, TaskWithDueDate } from '../types/database'
import { StatusBadge, UrgencyBadge } from '../components/Badges'
import { StatusMenu } from '../components/StatusMenu'
import { RemarkCell } from '../components/RemarkCell'
import { AdminRemarkCell } from '../components/AdminRemarkCell'
import { Loading } from '../components/Loading'
import { PersonChip } from '../components/PersonChip'
import { useDirectory } from '../lib/DirectoryProvider'

const STATUS_FILTERS: Array<TaskStatus | 'All'> = [
  'All',
  'Open',
  'In Process',
  'Pending at Client',
  'Pending at Department',
  'Hold',
  'Closed',
]

export function TaskListPage() {
  const { profile } = useAuth()
  const { profileName, clientName } = useDirectory()
  const [tasks, setTasks] = useState<TaskWithDueDate[] | null>(null)
  const [filter, setFilter] = useState<TaskStatus | 'All'>('All')
  const [pendingRevisionsCount, setPendingRevisionsCount] = useState(0)

  useEffect(() => {
    fetchMyVisibleTasks().then(setTasks)
  }, [])

  useEffect(() => {
    if (profile?.is_admin) fetchPendingRevisionsCount().then(setPendingRevisionsCount)
  }, [profile?.is_admin])

  const canCreate = profile?.is_admin || profile?.can_create_and_assign
  // "All" means "everything still active" — Closed has its own dedicated tab,
  // since a huge archive of closed tasks isn't useful mixed into the default view.
  const visible = tasks?.filter((t) => (filter === 'All' ? t.status !== 'Closed' : t.status === filter)) ?? []

  const canChangeStatus = (t: TaskWithDueDate) =>
    profile?.is_admin ||
    (t.status !== 'Closed' && (t.primary_assignee_id === profile?.id || t.secondary_assignee_id === profile?.id))

  const canAddRemark = (t: TaskWithDueDate) =>
    profile?.is_admin ||
    t.assignor_id === profile?.id ||
    t.primary_assignee_id === profile?.id ||
    t.secondary_assignee_id === profile?.id

  const handleStatusChange = async (taskId: string, next: TaskStatus) => {
    await updateTaskStatus(taskId, next)
    setTasks((prev) => prev?.map((t) => (t.id === taskId ? { ...t, status: next } : t)) ?? null)
  }

  const handleAddRemark = async (taskId: string, body: string) => {
    await addComment(taskId, body)
    setTasks((prev) => prev?.map((t) => (t.id === taskId ? { ...t, latest_remark: body } : t)) ?? null)
  }

  const handleSaveAdminRemark = async (taskId: string, body: string) => {
    await updateTaskAdminRemark(taskId, body)
    setTasks((prev) => prev?.map((t) => (t.id === taskId ? { ...t, admin_remark: body } : t)) ?? null)
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="font-serif text-2xl font-semibold text-ink">Tasks</h1>
        <div className="flex items-center gap-2">
          {canCreate && (
            <Link
              to="/tasks/new"
              className="bg-bark-gradient text-white text-sm font-medium px-4 py-2 rounded-md shadow-sm hover:shadow-md transition"
            >
              + New Task
            </Link>
          )}
          {profile?.is_admin && (
            <Link
              to="/revisions"
              className="relative inline-flex items-center border border-line text-ink-soft hover:border-bark hover:text-ink text-sm font-medium px-4 py-2 rounded-md bg-paper-raised shadow-sm hover:shadow-md transition"
            >
              Revision Requests
              {pendingRevisionsCount > 0 && (
                <span className="ml-2 inline-flex items-center justify-center min-w-[1.25rem] h-5 px-1 rounded-full bg-rust text-white text-xs font-semibold">
                  {pendingRevisionsCount}
                </span>
              )}
            </Link>
          )}
        </div>
      </div>

      <div className="flex gap-1.5 flex-wrap">
        {STATUS_FILTERS.map((s) => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            className={`text-xs font-medium px-3 py-1.5 rounded-full border transition-colors ${
              filter === s
                ? 'bg-bark-gradient text-white border-bark'
                : 'border-line text-ink-soft hover:border-bark hover:text-ink'
            }`}
          >
            {s}
          </button>
        ))}
      </div>

      {!tasks && <Loading />}

      {tasks && (
        <div className="bg-paper-raised border border-line rounded-lg shadow-sm overflow-hidden">
          <table className="w-full text-sm table-fixed">
            <colgroup>
              <col className="w-[10%]" />
              <col className="w-[11%]" />
              <col className="w-[8%]" />
              <col className="w-[9%]" />
              <col className="w-[9%]" />
              <col className="w-[7%]" />
              <col className="w-[7%]" />
              <col className="w-[5%]" />
              <col className="w-[13%]" />
              <col className="w-[11%]" />
              <col className="w-[10%]" />
            </colgroup>
            <thead>
              <tr className="bg-bark-gradient text-left text-white font-mono text-xs uppercase tracking-wide">
                <th className="px-3 py-2 font-medium">Task ID</th>
                <th className="px-3 py-2 font-medium">Description</th>
                <th className="px-3 py-2 font-medium">Client</th>
                <th className="px-3 py-2 font-medium">Primary</th>
                <th className="px-3 py-2 font-medium">Secondary</th>
                <th className="px-3 py-2 font-medium">Planned Date</th>
                <th className="px-3 py-2 font-medium">Revised Date</th>
                <th className="px-3 py-2 font-medium">Urgency</th>
                <th className="px-3 py-2 font-medium">Status</th>
                <th className="px-3 py-2 font-medium">Remark</th>
                <th className="px-3 py-2 font-medium">Admin Remark</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((t) => (
                <tr key={t.id} className="border-b border-line last:border-0 hover:bg-paper align-top">
                  <td className="px-3 py-2.5 whitespace-nowrap">
                    <div className="flex flex-col gap-1 items-start">
                      <Link to={`/tasks/${t.id}`} className="font-mono text-xs text-ink-soft hover:text-bark">
                        {t.task_number}
                      </Link>
                      <span
                        title={`Created ${new Date(t.created_at).toLocaleString()}`}
                        className="inline-flex items-center gap-1 rounded-full border border-line bg-paper px-1.5 py-0.5 font-mono text-[10px] text-ink-soft/80 whitespace-nowrap"
                      >
                        <ClockIcon />
                        {new Date(t.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  </td>
                  <td className="px-3 py-2.5 break-words">
                    <Link to={`/tasks/${t.id}`} className="text-ink hover:text-bark">
                      {t.description}
                    </Link>
                  </td>
                  <td className="px-3 py-2.5 text-ink-soft break-words">{clientName(t.client_id)}</td>
                  <td className="px-3 py-2.5">
                    <PersonChip id={t.primary_assignee_id} name={profileName(t.primary_assignee_id)} />
                  </td>
                  <td className="px-3 py-2.5">
                    {t.secondary_assignee_id ? (
                      <PersonChip id={t.secondary_assignee_id} name={profileName(t.secondary_assignee_id)} />
                    ) : (
                      <span className="text-ink-soft">—</span>
                    )}
                  </td>
                  <td className="px-3 py-2.5 text-ink-soft font-mono text-xs tabular-nums whitespace-nowrap">
                    {t.planned_date}
                  </td>
                  <td className="px-3 py-2.5 text-ink-soft font-mono text-xs tabular-nums whitespace-nowrap">
                    {t.latest_revised_date ?? '—'}
                  </td>
                  <td className="px-3 py-2.5">
                    <UrgencyBadge urgency={t.urgency} />
                  </td>
                  <td className="px-3 py-2.5">
                    <div className="flex flex-col gap-1 items-start">
                      {canChangeStatus(t) ? (
                        <StatusMenu status={t.status} onChange={(next) => handleStatusChange(t.id, next)} />
                      ) : (
                        <StatusBadge status={t.status} />
                      )}
                      {t.status === 'Closed' && t.closed_at && (
                        <span
                          title={`Closed ${new Date(t.closed_at).toLocaleString()}`}
                          className="inline-flex items-center gap-1 rounded-full border border-line bg-paper px-1.5 py-0.5 font-mono text-[10px] text-ink-soft/80 whitespace-nowrap"
                        >
                          <ClockIcon />
                          {new Date(t.closed_at).toLocaleDateString()}{' '}
                          {new Date(t.closed_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-3 py-2.5">
                    <RemarkCell
                      latestRemark={t.latest_remark}
                      canAdd={canAddRemark(t)}
                      onAdd={(body) => handleAddRemark(t.id, body)}
                    />
                  </td>
                  <td className="px-3 py-2.5">
                    <AdminRemarkCell
                      value={t.admin_remark}
                      isAdmin={!!profile?.is_admin}
                      onSave={(body) => handleSaveAdminRemark(t.id, body)}
                    />
                  </td>
                </tr>
              ))}
              {visible.length === 0 && (
                <tr>
                  <td colSpan={11} className="px-3 py-8 text-center text-ink-soft">
                    No tasks here.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function ClockIcon() {
  return (
    <svg width="9" height="9" viewBox="0 0 16 16" fill="none" className="shrink-0">
      <circle cx="8" cy="8" r="6.5" stroke="currentColor" strokeWidth="1.4" />
      <path d="M8 4.5V8l2.5 1.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}
