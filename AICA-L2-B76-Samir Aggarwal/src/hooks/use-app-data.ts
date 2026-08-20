import { useMemo } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { friendlyError, supabase } from '@/lib/supabase'
import { STAGE_NEED_HELP } from '@/lib/constants'
import type {
  Client,
  ClientCompliance,
  ComplianceMaster,
  GstRegistration,
  Profile,
  RecurringAssignment,
  Stage,
  TaskEnriched,
  TaskMaster,
} from '@/types/db'

export const QK = {
  stages: ['stages'] as const,
  tasks: ['tasks_enriched'] as const,
  profiles: ['profiles'] as const,
  clients: ['clients'] as const,
  masters: ['task_master'] as const,
  recurring: ['recurring_assignments'] as const,
  compliance: ['compliance_master'] as const,
  ticks: ['client_compliance'] as const,
  gstins: ['gst_registrations'] as const,
}

/** The stage master. Cached hard — it changes about once a year. */
export function useStages() {
  const query = useQuery({
    queryKey: QK.stages,
    staleTime: 10 * 60_000,
    queryFn: async () => {
      const { data, error } = await supabase
        .from('stages')
        .select('*')
        .eq('is_active', true)
        .order('sort_order')
      if (error) throw error
      return data as Stage[]
    },
  })

  const byCode = useMemo(() => {
    const map = new Map<string, Stage>()
    for (const stage of query.data ?? []) map.set(stage.code, stage)
    return map
  }, [query.data])

  const byId = useMemo(() => {
    const map = new Map<string, Stage>()
    for (const stage of query.data ?? []) map.set(stage.id, stage)
    return map
  }, [query.data])

  return { ...query, stages: query.data ?? [], byCode, byId }
}

/**
 * Every task the caller may see. RLS narrows this to the signed-in user's own
 * rows for an employee, and to everything for an admin — so the same query
 * powers My Tasks and the whole admin side.
 */
export function useTasks() {
  return useQuery({
    queryKey: QK.tasks,
    queryFn: async () => {
      const { data, error } = await supabase
        .from('v_tasks_enriched')
        .select('*')
        .order('stage_sort')
        .order('due_date', { ascending: true, nullsFirst: false })
      if (error) throw error
      return data as TaskEnriched[]
    },
  })
}

export function useProfiles() {
  return useQuery({
    queryKey: QK.profiles,
    queryFn: async () => {
      const { data, error } = await supabase.from('profiles').select('*').order('full_name')
      if (error) throw error
      return data as Profile[]
    },
  })
}

export function useClients() {
  return useQuery({
    queryKey: QK.clients,
    queryFn: async () => {
      const { data, error } = await supabase.from('clients').select('*').order('name')
      if (error) throw error
      return data as Client[]
    },
  })
}

export function useTaskMasters() {
  return useQuery({
    queryKey: QK.masters,
    queryFn: async () => {
      const { data, error } = await supabase
        .from('task_master')
        .select('*')
        .order('category')
        .order('name')
      if (error) throw error
      return data as TaskMaster[]
    },
  })
}

export function useRecurringAssignments() {
  return useQuery({
    queryKey: QK.recurring,
    queryFn: async () => {
      const { data, error } = await supabase
        .from('recurring_assignments')
        .select('*')
        .order('created_at', { ascending: false })
      if (error) throw error
      return data as RecurringAssignment[]
    },
  })
}

/** The compliance rule catalogue. Changes rarely; cached hard. */
export function useComplianceMasters() {
  return useQuery({
    queryKey: QK.compliance,
    staleTime: 10 * 60_000,
    queryFn: async () => {
      const { data, error } = await supabase
        .from('compliance_master')
        .select('*')
        .eq('active', true)
        .order('law')
        .order('name')
      if (error) throw error
      return data as ComplianceMaster[]
    },
  })
}

/** Every applicability tick, all clients. Small table; filtered client-side. */
export function useClientCompliance() {
  return useQuery({
    queryKey: QK.ticks,
    queryFn: async () => {
      const { data, error } = await supabase.from('client_compliance').select('*')
      if (error) throw error
      return data as ClientCompliance[]
    },
  })
}

export function useGstRegistrations() {
  return useQuery({
    queryKey: QK.gstins,
    queryFn: async () => {
      const { data, error } = await supabase
        .from('gst_registrations')
        .select('*')
        .order('gstin')
      if (error) throw error
      return data as GstRegistration[]
    },
  })
}

/**
 * Moving a task between stages — the single most-used action in the app.
 *
 * The note is sent in the same update as the stage so the history trigger can
 * record why it moved. Everything else (stage_since, completed_at, clearing a
 * stale help note) is handled by the database.
 */
export function useMoveStage() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (payload: {
      id: string
      stageId: string
      stageCode: string
      note?: string | null
      /** Compliance completion: statutory filing date and acknowledgment URL. */
      filingDate?: string | null
      filingLink?: string | null
    }) => {
      const update: Record<string, unknown> = { stage_id: payload.stageId }
      if (payload.stageCode === STAGE_NEED_HELP) {
        update.help_note = payload.note?.trim() || null
      }
      if (payload.filingDate !== undefined) update.filing_date = payload.filingDate
      if (payload.filingLink !== undefined) update.filing_link = payload.filingLink?.trim() || null
      const { error } = await supabase.from('tasks').update(update).eq('id', payload.id)
      if (error) throw error
    },
    onMutate: async (payload) => {
      await queryClient.cancelQueries({ queryKey: QK.tasks })
      const previous = queryClient.getQueryData<TaskEnriched[]>(QK.tasks)
      // Optimistic: the board should respond to a drag immediately.
      queryClient.setQueryData<TaskEnriched[]>(QK.tasks, (old) =>
        (old ?? []).map((task) =>
          task.id === payload.id
            ? {
                ...task,
                stage_id: payload.stageId,
                stage_code: payload.stageCode,
                days_in_stage: 0,
                help_note:
                  payload.stageCode === STAGE_NEED_HELP ? (payload.note ?? null) : null,
              }
            : task,
        ),
      )
      return { previous }
    },
    onError: (error, _payload, context) => {
      if (context?.previous) queryClient.setQueryData(QK.tasks, context.previous)
      toast.error(friendlyError(error))
    },
    onSuccess: () => toast.success('Stage updated'),
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: QK.tasks })
    },
  })
}
