import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthProvider'
import { useDirectory } from '../lib/DirectoryProvider'
import { createClient, createTask } from '../lib/queries'
import type { Urgency } from '../types/database'
import { Select } from '../components/Select'

export function NewTaskPage() {
  const { profile } = useAuth()
  const { clients, profiles, reloadClients } = useDirectory()
  const navigate = useNavigate()

  const [clientId, setClientId] = useState('')
  const [newClientName, setNewClientName] = useState('')
  const [description, setDescription] = useState('')
  const [primaryAssigneeId, setPrimaryAssigneeId] = useState('')
  const [secondaryAssigneeId, setSecondaryAssigneeId] = useState('')
  const [urgency, setUrgency] = useState<Urgency>('Medium')
  const [plannedDate, setPlannedDate] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setSaving(true)
    try {
      let finalClientId = clientId
      if (!finalClientId && newClientName.trim()) {
        const created = await createClient(newClientName.trim())
        finalClientId = created.id
        await reloadClients()
      }
      if (!finalClientId) throw new Error('Choose or add a client.')
      if (!primaryAssigneeId) throw new Error('Choose who this is assigned to.')
      if (secondaryAssigneeId && secondaryAssigneeId === primaryAssigneeId) {
        throw new Error('Secondary assignee must be different from the Primary assignee.')
      }
      if (!plannedDate) throw new Error('Set a planned completion date.')

      const task = await createTask({
        client_id: finalClientId,
        description,
        assignor_id: profile!.id,
        primary_assignee_id: primaryAssigneeId,
        secondary_assignee_id: secondaryAssigneeId || null,
        urgency,
        planned_date: plannedDate,
      })
      navigate(`/tasks/${task.id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong.')
    } finally {
      setSaving(false)
    }
  }

  const inputClass =
    'w-full rounded-md border border-line bg-paper px-3 py-2 text-sm text-ink transition-colors focus:outline-none focus:border-bark focus:ring-2 focus:ring-bark/15'

  return (
    <div className="max-w-xl flex flex-col gap-6">
      <h1 className="font-serif text-2xl font-semibold text-ink">New Task</h1>
      <form
        onSubmit={handleSubmit}
        className="bg-paper-raised border border-line rounded-lg shadow-sm p-6 flex flex-col gap-5"
      >
        <div>
          <label className="block text-xs font-medium uppercase tracking-wide text-ink-soft mb-1.5">Client</label>
          <Select
            value={clientId}
            onValueChange={setClientId}
            placeholder="— choose a client —"
            options={clients.map((c) => ({ value: c.id, label: c.name }))}
          />
          <input
            type="text"
            placeholder="…or add a new client"
            value={newClientName}
            onChange={(e) => {
              setNewClientName(e.target.value)
              setClientId('')
            }}
            className={`${inputClass} mt-2`}
          />
        </div>

        <div>
          <label className="block text-xs font-medium uppercase tracking-wide text-ink-soft mb-1.5">
            Task Description
          </label>
          <textarea
            required
            rows={3}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className={inputClass}
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium uppercase tracking-wide text-ink-soft mb-1.5">
              Primary Assignee
            </label>
            <Select
              value={primaryAssigneeId}
              onValueChange={setPrimaryAssigneeId}
              placeholder="— choose a person —"
              options={profiles.map((p) => ({ value: p.id, label: p.full_name || p.email }))}
            />
          </div>
          <div>
            <label className="block text-xs font-medium uppercase tracking-wide text-ink-soft mb-1.5">
              Secondary Assignee <span className="normal-case text-ink-soft/70">(optional)</span>
            </label>
            <Select
              value={secondaryAssigneeId}
              onValueChange={setSecondaryAssigneeId}
              placeholder="— none —"
              options={profiles
                .filter((p) => p.id !== primaryAssigneeId)
                .map((p) => ({ value: p.id, label: p.full_name || p.email }))}
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium uppercase tracking-wide text-ink-soft mb-1.5">Urgency</label>
            <Select
              value={urgency}
              onValueChange={(v) => setUrgency(v as Urgency)}
              placeholder="Urgency"
              options={[
                { value: 'Low', label: 'Low' },
                { value: 'Medium', label: 'Medium' },
                { value: 'High', label: 'High' },
              ]}
            />
          </div>
          <div>
            <label className="block text-xs font-medium uppercase tracking-wide text-ink-soft mb-1.5">
              Planned Date
            </label>
            <input
              type="date"
              required
              value={plannedDate}
              onChange={(e) => setPlannedDate(e.target.value)}
              className={inputClass}
            />
          </div>
        </div>

        {error && <p className="text-sm text-rust bg-rust-bg rounded-md px-3 py-2">{error}</p>}

        <button
          type="submit"
          disabled={saving}
          className="self-start bg-bark-gradient disabled:opacity-50 text-white text-sm font-medium px-5 py-2.5 rounded-md shadow-sm hover:shadow-md transition"
        >
          {saving ? 'Creating…' : 'Create Task'}
        </button>
      </form>
    </div>
  )
}
