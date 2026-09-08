import { useEffect, useState } from 'react'
import { fetchMyVisibleTasks } from '../lib/queries'
import type { TaskWithDueDate } from '../types/database'
import { DueBucketTable } from '../components/DueBucketTable'
import { Loading } from '../components/Loading'

// Admin-only screen (see App.tsx routing) — a plain User's home is the Task
// List instead, so there's no per-user due-bucket view here anymore.
export function DashboardPage() {
  const [tasks, setTasks] = useState<TaskWithDueDate[] | null>(null)

  useEffect(() => {
    fetchMyVisibleTasks().then(setTasks)
  }, [])

  if (!tasks) return <Loading />

  return (
    <div className="flex flex-col gap-6">
      <h1 className="font-serif text-2xl font-semibold text-ink">Dashboard</h1>
      <div className="flex flex-row flex-wrap items-start gap-6">
        <DueBucketTable tasks={tasks} assigneeField="primary_assignee_id" title="By Primary Assignee" />
        <DueBucketTable tasks={tasks} assigneeField="secondary_assignee_id" title="By Secondary Assignee" />
      </div>
    </div>
  )
}
