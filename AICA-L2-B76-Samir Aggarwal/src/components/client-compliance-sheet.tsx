import { useMemo, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { AlertTriangle, Loader2, Plus, ShieldCheck, Trash2 } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { Switch } from '@/components/ui/switch'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Field } from '@/components/common'
import { Combobox } from '@/components/combobox'
import { useAuth } from '@/components/auth-provider'
import {
  QK,
  useClientCompliance,
  useComplianceMasters,
  useGstRegistrations,
  useProfiles,
} from '@/hooks/use-app-data'
import { friendlyError, supabase } from '@/lib/supabase'
import { GSTIN_REGEX } from '@/lib/constants'
import { toDateInput } from '@/lib/utils'
import type { Client, ClientCompliance, ComplianceMaster } from '@/types/db'

/**
 * The applicability window: tick what applies to this client, with start date
 * and assignee. Per the agreed policy, any staff may ADD a tick or a GSTIN;
 * removal and start-date changes are admin-only (enforced by the database,
 * mirrored here).
 */
export function ClientComplianceSheet({
  client,
  open,
  onOpenChange,
}: {
  client: Client | null
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const { session, isAdmin } = useAuth()
  const queryClient = useQueryClient()
  const mastersQuery = useComplianceMasters()
  const ticksQuery = useClientCompliance()
  const gstinsQuery = useGstRegistrations()
  const profilesQuery = useProfiles()

  const [newGstin, setNewGstin] = useState('')
  const [newGstinState, setNewGstinState] = useState('')
  const [gstinError, setGstinError] = useState<string | null>(null)

  const masters = mastersQuery.data ?? []
  const generatable = useMemo(() => masters.filter((m) => m.is_generatable), [masters])
  const reference = useMemo(() => masters.filter((m) => !m.is_generatable), [masters])

  const ticks = useMemo(
    () => (ticksQuery.data ?? []).filter((t) => t.client_id === client?.id),
    [ticksQuery.data, client?.id],
  )
  const tickByCompliance = useMemo(() => {
    const map = new Map<string, ClientCompliance>()
    for (const tick of ticks) map.set(tick.compliance_id, tick)
    return map
  }, [ticks])

  const gstins = useMemo(
    () => (gstinsQuery.data ?? []).filter((g) => g.client_id === client?.id),
    [gstinsQuery.data, client?.id],
  )
  const activeGstins = gstins.filter((g) => g.is_active)

  const staffOptions = useMemo(
    () =>
      (profilesQuery.data ?? [])
        .filter((p) => p.is_active)
        .map((p) => ({ value: p.id, label: p.full_name, hint: p.designation })),
    [profilesQuery.data],
  )

  const byLaw = useMemo(() => {
    const map = new Map<string, ComplianceMaster[]>()
    for (const master of generatable) {
      const law = master.law ?? 'Other'
      const list = map.get(law) ?? []
      list.push(master)
      map.set(law, list)
    }
    return [...map.entries()].sort((a, b) => a[0].localeCompare(b[0]))
  }, [generatable])

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: QK.ticks })
    void queryClient.invalidateQueries({ queryKey: QK.gstins })
  }

  const addTick = useMutation({
    mutationFn: async (master: ComplianceMaster) => {
      const { error } = await supabase.from('client_compliance').insert({
        client_id: client!.id,
        compliance_id: master.id,
        created_by: session?.user.id ?? null,
      })
      if (error) throw error
    },
    onSuccess: () => {
      invalidate()
      toast.success('Compliance ticked — set who handles it below')
    },
    onError: (error) => toast.error(friendlyError(error)),
  })

  const updateTick = useMutation({
    mutationFn: async (payload: {
      id: string
      patch: Partial<Pick<ClientCompliance, 'assigned_to' | 'start_date' | 'frequency_override'>>
    }) => {
      const { error } = await supabase
        .from('client_compliance')
        .update(payload.patch)
        .eq('id', payload.id)
      if (error) throw error
    },
    onSuccess: invalidate,
    onError: (error) => toast.error(friendlyError(error)),
  })

  const removeTick = useMutation({
    mutationFn: async (id: string) => {
      const { error } = await supabase.from('client_compliance').delete().eq('id', id)
      if (error) throw error
    },
    onSuccess: () => {
      invalidate()
      toast.success('Un-ticked — future periods will not generate')
    },
    onError: (error) => toast.error(friendlyError(error)),
  })

  const addGstin = useMutation({
    mutationFn: async () => {
      const gstin = newGstin.trim().toUpperCase()
      if (!GSTIN_REGEX.test(gstin)) throw new Error('That is not a valid GSTIN.')
      const { error } = await supabase.from('gst_registrations').insert({
        client_id: client!.id,
        gstin,
        state: newGstinState.trim() || null,
        created_by: session?.user.id ?? null,
      })
      if (error) throw error
    },
    onSuccess: () => {
      invalidate()
      setNewGstin('')
      setNewGstinState('')
      setGstinError(null)
      toast.success('GSTIN added')
    },
    onError: (error) => setGstinError(friendlyError(error)),
  })

  const toggleGstin = useMutation({
    mutationFn: async (payload: { id: string; is_active: boolean }) => {
      const { error } = await supabase
        .from('gst_registrations')
        .update({ is_active: payload.is_active })
        .eq('id', payload.id)
      if (error) throw error
    },
    onSuccess: invalidate,
    onError: (error) => toast.error(friendlyError(error)),
  })

  if (!client) return null

  const hasGstRules = ticks.some((tick) => {
    const master = masters.find((m) => m.id === tick.compliance_id)
    return master?.target_level === 'GSTIN'
  })

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full overflow-y-auto sm:max-w-2xl">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2">
            <ShieldCheck className="size-4" />
            {client.name}
          </SheetTitle>
          <SheetDescription>
            Tick what applies. Ticked compliances generate dated tasks automatically each morning
            for the current financial year.
          </SheetDescription>
        </SheetHeader>

        <div className="space-y-4 px-4 pb-8">
          {hasGstRules && activeGstins.length === 0 ? (
            <div className="border-destructive/40 text-destructive flex items-start gap-2 rounded-md border p-3 text-sm">
              <AlertTriangle className="mt-0.5 size-4 shrink-0" />
              <span>
                GST compliances are ticked but this client has <strong>no active GSTIN</strong> —
                nothing will generate for them until one is added under the GSTINs tab.
              </span>
            </div>
          ) : null}

          <Tabs defaultValue="compliances">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="compliances">
                Compliances
                <Badge variant="secondary" className="ml-1.5 tabular-nums">
                  {ticks.length}
                </Badge>
              </TabsTrigger>
              <TabsTrigger value="gstins">
                GSTINs
                <Badge variant="secondary" className="ml-1.5 tabular-nums">
                  {gstins.length}
                </Badge>
              </TabsTrigger>
            </TabsList>

            {/* ------------- Compliances ------------- */}
            <TabsContent value="compliances" className="mt-4 space-y-5">
              {byLaw.map(([law, items]) => (
                <section key={law} className="space-y-2">
                  <h3 className="text-muted-foreground text-xs font-semibold tracking-wide uppercase">
                    {law}
                  </h3>
                  <ul className="space-y-2">
                    {items.map((master) => {
                      const tick = tickByCompliance.get(master.id)
                      return (
                        <li
                          key={master.id}
                          className={
                            tick ? 'bg-card rounded-lg border p-3' : 'rounded-lg border border-dashed p-3'
                          }
                        >
                          <div className="flex items-start gap-3">
                            <Checkbox
                              className="mt-0.5"
                              checked={Boolean(tick)}
                              disabled={
                                addTick.isPending ||
                                removeTick.isPending ||
                                (Boolean(tick) && !isAdmin)
                              }
                              onCheckedChange={(checked) => {
                                if (checked) addTick.mutate(master)
                                else if (tick && isAdmin) removeTick.mutate(tick.id)
                              }}
                              title={
                                tick && !isAdmin
                                  ? 'Only an administrator can un-tick a compliance'
                                  : undefined
                              }
                            />
                            <div className="min-w-0 flex-1">
                              <div className="flex flex-wrap items-center gap-2">
                                <span className="text-sm font-medium">{master.name}</span>
                                <Badge variant="outline" className="font-normal">
                                  {master.frequency}
                                </Badge>
                                {master.target_level === 'GSTIN' ? (
                                  <Badge variant="secondary" className="font-normal">
                                    per GSTIN
                                  </Badge>
                                ) : null}
                              </div>
                              {master.due_rule_text ? (
                                <p className="text-muted-foreground mt-0.5 text-xs">
                                  Due: {master.due_rule_text}
                                </p>
                              ) : null}

                              {tick ? (
                                <div className="mt-3 grid gap-3 sm:grid-cols-2">
                                  <Field label="Handled by">
                                    <div>
                                      <Combobox
                                        options={staffOptions}
                                        value={tick.assigned_to}
                                        onChange={(value) =>
                                          updateTick.mutate({
                                            id: tick.id,
                                            patch: { assigned_to: value },
                                          })
                                        }
                                        placeholder="Nobody — will NOT generate"
                                      />
                                      {!tick.assigned_to ? (
                                        <p className="text-destructive mt-1 text-xs font-medium">
                                          No assignee — this compliance is skipped.
                                        </p>
                                      ) : null}
                                    </div>
                                  </Field>
                                  <Field
                                    label="Start Date"
                                    hint={isAdmin ? 'Generation begins here or FY start.' : 'Admin only.'}
                                  >
                                    <Input
                                      type="date"
                                      disabled={!isAdmin}
                                      value={toDateInput(tick.start_date)}
                                      onChange={(e) =>
                                        updateTick.mutate({
                                          id: tick.id,
                                          patch: { start_date: e.target.value || null },
                                        })
                                      }
                                    />
                                  </Field>
                                  {master.frequency_overridable ? (
                                    <Field label="Filing cycle" hint="QRMP clients file quarterly.">
                                      <Select
                                        value={tick.frequency_override ?? '__default__'}
                                        onValueChange={(value) =>
                                          updateTick.mutate({
                                            id: tick.id,
                                            patch: {
                                              frequency_override:
                                                value === '__default__' ? null : value,
                                            },
                                          })
                                        }
                                      >
                                        <SelectTrigger className="w-full">
                                          <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                          <SelectItem value="__default__">
                                            Default ({master.frequency})
                                          </SelectItem>
                                          <SelectItem value="Monthly">Monthly</SelectItem>
                                          <SelectItem value="Quarterly">Quarterly (QRMP)</SelectItem>
                                        </SelectContent>
                                      </Select>
                                    </Field>
                                  ) : null}
                                </div>
                              ) : null}
                            </div>
                            {tick && isAdmin ? (
                              <Button
                                variant="ghost"
                                size="icon"
                                className="text-destructive size-7 shrink-0"
                                onClick={() => removeTick.mutate(tick.id)}
                                aria-label="Un-tick"
                              >
                                <Trash2 className="size-3.5" />
                              </Button>
                            ) : null}
                          </div>
                        </li>
                      )
                    })}
                  </ul>
                </section>
              ))}

              {reference.length ? (
                <Collapsible>
                  <CollapsibleTrigger asChild>
                    <Button variant="ghost" size="sm" className="text-muted-foreground">
                      Event-driven compliances ({reference.length}) — not tickable
                    </Button>
                  </CollapsibleTrigger>
                  <CollapsibleContent>
                    <p className="text-muted-foreground px-3 pt-1 pb-2 text-xs">
                      These arise from events (board changes, charges, incorporation…), so they
                      cannot be scheduled. Create them as tasks from the Task Master when the event
                      happens.
                    </p>
                    <ul className="text-muted-foreground space-y-1 px-3 pb-2 text-sm">
                      {reference.map((master) => (
                        <li key={master.id}>
                          {master.name}
                          <span className="text-muted-foreground/60"> — {master.law}</span>
                        </li>
                      ))}
                    </ul>
                  </CollapsibleContent>
                </Collapsible>
              ) : null}
            </TabsContent>

            {/* ------------- GSTINs ------------- */}
            <TabsContent value="gstins" className="mt-4 space-y-4">
              <div className="rounded-lg border p-3">
                <p className="mb-3 text-sm font-medium">Add a GSTIN</p>
                <div className="flex flex-col gap-2 sm:flex-row">
                  <Input
                    placeholder="07AAACA1234B1Z5"
                    className="font-mono"
                    maxLength={15}
                    value={newGstin}
                    onChange={(e) => setNewGstin(e.target.value.toUpperCase())}
                  />
                  <Input
                    placeholder="State (optional)"
                    className="sm:w-40"
                    value={newGstinState}
                    onChange={(e) => setNewGstinState(e.target.value)}
                  />
                  <Button
                    onClick={() => addGstin.mutate()}
                    disabled={addGstin.isPending || !newGstin.trim()}
                  >
                    {addGstin.isPending ? (
                      <Loader2 className="size-4 animate-spin" />
                    ) : (
                      <Plus className="size-4" />
                    )}
                    Add
                  </Button>
                </div>
                {gstinError ? <p className="text-destructive mt-1 text-xs">{gstinError}</p> : null}
              </div>

              {gstins.length === 0 ? (
                <p className="text-muted-foreground text-sm">
                  No GSTINs recorded. GST compliances ticked for this client will not generate
                  until one is added.
                </p>
              ) : (
                <ul className="space-y-2">
                  {gstins.map((registration) => (
                    <li
                      key={registration.id}
                      className="bg-card flex items-center justify-between gap-3 rounded-lg border p-3"
                    >
                      <div className="min-w-0">
                        <p className="font-mono text-sm font-medium">{registration.gstin}</p>
                        <p className="text-muted-foreground text-xs">
                          {registration.state ?? '—'}
                          {!registration.is_active ? ' · inactive' : ''}
                        </p>
                      </div>
                      <Switch
                        checked={registration.is_active}
                        disabled={!isAdmin}
                        onCheckedChange={(checked) =>
                          toggleGstin.mutate({ id: registration.id, is_active: checked })
                        }
                        title={!isAdmin ? 'Only an administrator can deactivate a GSTIN' : undefined}
                      />
                    </li>
                  ))}
                </ul>
              )}
            </TabsContent>
          </Tabs>
        </div>
      </SheetContent>
    </Sheet>
  )
}
