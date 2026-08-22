import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Building2, Loader2, Pencil, Plus, Search, ShieldCheck, Upload } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Textarea } from '@/components/ui/textarea'
import { EmptyState, Field, PageHeader, StatCard, TableSkeleton } from '@/components/common'
import { Combobox, CreatableCombobox } from '@/components/combobox'
import { ClientImportDialog } from '@/components/client-import'
import { ClientComplianceSheet } from '@/components/client-compliance-sheet'
import { useAuth } from '@/components/auth-provider'
import { friendlyError, supabase } from '@/lib/supabase'
import { CLIENT_TYPES, GSTIN_REGEX, PAN_REGEX } from '@/lib/constants'
import type { Client, ClientType, Profile } from '@/types/db'

type ClientDraft = {
  id?: string
  client_code: string
  client_group: string
  name: string
  client_type: ClientType
  pan: string
  gstin: string
  contact_person: string
  email: string
  phone: string
  address: string
  city: string
  state: string
  relationship_manager: string | null
  notes: string
}

const EMPTY_DRAFT: ClientDraft = {
  client_code: '',
  client_group: '',
  name: '',
  client_type: 'Individual',
  pan: '',
  gstin: '',
  contact_person: '',
  email: '',
  phone: '',
  address: '',
  city: '',
  state: '',
  relationship_manager: null,
  notes: '',
}

function toDraft(client: Client): ClientDraft {
  return {
    id: client.id,
    client_code: client.client_code ?? '',
    client_group: client.client_group ?? '',
    name: client.name,
    client_type: client.client_type,
    pan: client.pan ?? '',
    gstin: client.gstin ?? '',
    contact_person: client.contact_person ?? '',
    email: client.email ?? '',
    phone: client.phone ?? '',
    address: client.address ?? '',
    city: client.city ?? '',
    state: client.state ?? '',
    relationship_manager: client.relationship_manager,
    notes: client.notes ?? '',
  }
}

export default function ClientsPage() {
  const { session } = useAuth()
  const queryClient = useQueryClient()

  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState<string>('all')
  const [groupFilter, setGroupFilter] = useState<string>('all')
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'inactive'>('active')

  const [dialogOpen, setDialogOpen] = useState(false)
  const [importOpen, setImportOpen] = useState(false)
  const [complianceFor, setComplianceFor] = useState<Client | null>(null)
  const [draft, setDraft] = useState<ClientDraft>(EMPTY_DRAFT)
  const [errors, setErrors] = useState<Record<string, string>>({})

  const clientsQuery = useQuery({
    queryKey: ['clients'],
    queryFn: async () => {
      const { data, error } = await supabase.from('clients').select('*').order('name')
      if (error) throw error
      return data as Client[]
    },
  })

  const profilesQuery = useQuery({
    queryKey: ['profiles'],
    queryFn: async () => {
      const { data, error } = await supabase.from('profiles').select('*').order('full_name')
      if (error) throw error
      return data as Profile[]
    },
  })

  const managerOptions = useMemo(
    () =>
      (profilesQuery.data ?? [])
        .filter((profile) => profile.is_active)
        .map((profile) => ({
          value: profile.id,
          label: profile.full_name,
          hint: profile.designation,
        })),
    [profilesQuery.data],
  )

  const managerName = useMemo(() => {
    const map = new Map<string, string>()
    for (const profile of profilesQuery.data ?? []) map.set(profile.id, profile.full_name)
    return map
  }, [profilesQuery.data])

  const saveClient = useMutation({
    mutationFn: async (payload: ClientDraft) => {
      const row = {
        client_code: payload.client_code.trim() || null,
        client_group: payload.client_group.trim() || null,
        name: payload.name.trim(),
        client_type: payload.client_type,
        pan: payload.pan.trim().toUpperCase() || null,
        gstin: payload.gstin.trim().toUpperCase() || null,
        contact_person: payload.contact_person.trim() || null,
        email: payload.email.trim() || null,
        phone: payload.phone.trim() || null,
        address: payload.address.trim() || null,
        city: payload.city.trim() || null,
        state: payload.state.trim() || null,
        relationship_manager: payload.relationship_manager,
        notes: payload.notes.trim() || null,
      }

      if (payload.id) {
        const { error } = await supabase.from('clients').update(row).eq('id', payload.id)
        if (error) throw error
      } else {
        const { error } = await supabase
          .from('clients')
          .insert({ ...row, created_by: session?.user.id ?? null })
        if (error) throw error
      }
    },
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({ queryKey: ['clients'] })
      setDialogOpen(false)
      toast.success(variables.id ? 'Client updated' : 'Client added')
    },
    onError: (error) => toast.error(friendlyError(error)),
  })

  const toggleActive = useMutation({
    mutationFn: async (payload: { id: string; is_active: boolean }) => {
      const { error } = await supabase
        .from('clients')
        .update({ is_active: payload.is_active })
        .eq('id', payload.id)
      if (error) throw error
    },
    onSuccess: (_d, variables) => {
      void queryClient.invalidateQueries({ queryKey: ['clients'] })
      toast.success(variables.is_active ? 'Client activated' : 'Client deactivated')
    },
    onError: (error) => toast.error(friendlyError(error)),
  })

  const groups = useMemo(() => {
    const set = new Set<string>()
    for (const client of clientsQuery.data ?? []) {
      if (client.client_group) set.add(client.client_group)
    }
    return [...set].sort((a, b) => a.localeCompare(b))
  }, [clientsQuery.data])

  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase()
    return (clientsQuery.data ?? []).filter((client) => {
      if (typeFilter !== 'all' && client.client_type !== typeFilter) return false
      if (groupFilter === '__none__' && client.client_group) return false
      if (groupFilter !== 'all' && groupFilter !== '__none__' && client.client_group !== groupFilter)
        return false
      if (statusFilter === 'active' && !client.is_active) return false
      if (statusFilter === 'inactive' && client.is_active) return false
      if (!term) return true
      return (
        client.name.toLowerCase().includes(term) ||
        (client.pan ?? '').toLowerCase().includes(term) ||
        (client.gstin ?? '').toLowerCase().includes(term) ||
        (client.client_code ?? '').toLowerCase().includes(term) ||
        (client.client_group ?? '').toLowerCase().includes(term)
      )
    })
  }, [clientsQuery.data, search, typeFilter, groupFilter, statusFilter])

  const summary = useMemo(() => {
    const all = clientsQuery.data ?? []
    return {
      total: all.length,
      active: all.filter((c) => c.is_active).length,
      gstRegistered: all.filter((c) => Boolean(c.gstin)).length,
    }
  }, [clientsQuery.data])

  function openAdd() {
    setDraft(EMPTY_DRAFT)
    setErrors({})
    setDialogOpen(true)
  }

  function openEdit(client: Client) {
    setDraft(toDraft(client))
    setErrors({})
    setDialogOpen(true)
  }

  function submit(event: React.FormEvent) {
    event.preventDefault()
    const next: Record<string, string> = {}
    if (!draft.name.trim()) next.name = 'Client name is required.'
    const pan = draft.pan.trim().toUpperCase()
    const gstin = draft.gstin.trim().toUpperCase()
    if (pan && !PAN_REGEX.test(pan)) next.pan = 'PAN must look like AAAAA9999A.'
    if (gstin && !GSTIN_REGEX.test(gstin)) next.gstin = 'GSTIN must be 15 characters, e.g. 07AAAAA9999A1Z5.'
    setErrors(next)
    if (Object.keys(next).length) return
    saveClient.mutate({ ...draft, pan, gstin })
  }

  const set = <K extends keyof ClientDraft>(key: K, value: ClientDraft[K]) =>
    setDraft((prev) => ({ ...prev, [key]: value }))

  return (
    <div className="space-y-5">
      <PageHeader title="Client Master" description="Every client the firm bills or files for.">
        <Button variant="outline" onClick={() => setImportOpen(true)}>
          <Upload className="size-4" />
          Import
        </Button>
        <Button onClick={openAdd}>
          <Plus className="size-4" />
          Add Client
        </Button>
      </PageHeader>

      <ClientImportDialog open={importOpen} onOpenChange={setImportOpen} />
      <ClientComplianceSheet
        client={complianceFor}
        open={Boolean(complianceFor)}
        onOpenChange={(open) => !open && setComplianceFor(null)}
      />

      <div className="grid gap-3 sm:grid-cols-3">
        <StatCard label="Total Clients" value={summary.total} icon={Building2} />
        <StatCard label="Active" value={summary.active} icon={Building2} tone="success" />
        <StatCard label="GST Registered" value={summary.gstRegistered} icon={Building2} />
      </div>

      <Card className="py-0">
        <CardContent className="p-0">
          <div className="flex flex-col gap-3 border-b p-4 lg:flex-row lg:items-center">
            <div className="relative flex-1">
              <Search className="text-muted-foreground absolute top-1/2 left-2.5 size-4 -translate-y-1/2" />
              <Input
                placeholder="Search by name, code, PAN or GSTIN…"
                className="pl-8"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <Select value={typeFilter} onValueChange={setTypeFilter}>
              <SelectTrigger className="lg:w-52">
                <SelectValue placeholder="All types" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All types</SelectItem>
                {CLIENT_TYPES.map((type) => (
                  <SelectItem key={type} value={type}>
                    {type}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={groupFilter} onValueChange={setGroupFilter}>
              <SelectTrigger className="lg:w-52">
                <SelectValue placeholder="All groups" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All groups</SelectItem>
                <SelectItem value="__none__">Ungrouped</SelectItem>
                {groups.map((group) => (
                  <SelectItem key={group} value={group}>
                    {group}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select
              value={statusFilter}
              onValueChange={(value) => setStatusFilter(value as typeof statusFilter)}
            >
              <SelectTrigger className="lg:w-40">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="active">Active only</SelectItem>
                <SelectItem value="inactive">Inactive only</SelectItem>
                <SelectItem value="all">All statuses</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {clientsQuery.isLoading ? (
            <TableSkeleton cols={7} />
          ) : clientsQuery.error ? (
            <div className="text-destructive p-6 text-sm">{friendlyError(clientsQuery.error)}</div>
          ) : filtered.length === 0 ? (
            <div className="p-4">
              <EmptyState
                icon={Building2}
                title={clientsQuery.data?.length ? 'No clients match those filters' : 'No clients yet'}
                description={
                  clientsQuery.data?.length
                    ? 'Try a different search term or switch the status filter to “All”.'
                    : 'Add your first client so tasks can be allocated against them.'
                }
                action={
                  clientsQuery.data?.length ? null : (
                    <Button onClick={openAdd}>
                      <Plus className="size-4" />
                      Add Client
                    </Button>
                  )
                }
              />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Code</TableHead>
                    <TableHead>Name</TableHead>
                    <TableHead>Group</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>PAN</TableHead>
                    <TableHead>GSTIN</TableHead>
                    <TableHead>Relationship Manager</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filtered.map((client) => (
                    <TableRow key={client.id}>
                      <TableCell className="text-muted-foreground font-mono text-xs">
                        {client.client_code ?? '—'}
                      </TableCell>
                      <TableCell className="font-medium">{client.name}</TableCell>
                      <TableCell className="whitespace-nowrap">
                        {client.client_group ? (
                          <Badge variant="secondary" className="font-normal">
                            {client.client_group}
                          </Badge>
                        ) : (
                          <span className="text-muted-foreground/50 text-sm">—</span>
                        )}
                      </TableCell>
                      <TableCell className="whitespace-nowrap">{client.client_type}</TableCell>
                      <TableCell className="font-mono text-xs">{client.pan ?? '—'}</TableCell>
                      <TableCell className="font-mono text-xs">{client.gstin ?? '—'}</TableCell>
                      <TableCell className="whitespace-nowrap">
                        {client.relationship_manager
                          ? (managerName.get(client.relationship_manager) ?? '—')
                          : '—'}
                      </TableCell>
                      <TableCell>
                        {client.is_active ? (
                          <Badge variant="outline" className="border-success text-success">
                            Active
                          </Badge>
                        ) : (
                          <Badge variant="secondary">Inactive</Badge>
                        )}
                      </TableCell>
                      <TableCell>
                        <div className="flex justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setComplianceFor(client)}
                            title="Compliances and GSTINs"
                          >
                            <ShieldCheck className="size-3.5" />
                            Compliance
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => openEdit(client)}>
                            <Pencil className="size-3.5" />
                            Edit
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() =>
                              toggleActive.mutate({ id: client.id, is_active: !client.is_active })
                            }
                          >
                            {client.is_active ? 'Deactivate' : 'Activate'}
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-h-[92vh] overflow-y-auto sm:max-w-3xl">
          <DialogHeader>
            <DialogTitle>{draft.id ? 'Edit Client' : 'Add Client'}</DialogTitle>
            <DialogDescription>
              PAN and GSTIN are optional, but are validated when entered.
            </DialogDescription>
          </DialogHeader>
          <form className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3" onSubmit={submit} noValidate>
            <Field label="Client Code" htmlFor="client-code">
              <Input
                id="client-code"
                value={draft.client_code}
                onChange={(e) => set('client_code', e.target.value)}
                placeholder="e.g. ASC-001"
              />
            </Field>
            <Field label="Name" htmlFor="client-name" error={errors.name} required>
              <Input
                id="client-name"
                value={draft.name}
                onChange={(e) => set('name', e.target.value)}
              />
            </Field>
            <Field
              label="Group"
              hint="Family or business group — e.g. Agarwal Group. Type a new one or pick an existing."
            >
              <CreatableCombobox
                options={groups}
                value={draft.client_group}
                onChange={(value) => set('client_group', value)}
                placeholder="Ungrouped"
                createLabel="Create group"
              />
            </Field>
            <Field label="Client Type" required>
              <Select
                value={draft.client_type}
                onValueChange={(value) => set('client_type', value as ClientType)}
              >
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {CLIENT_TYPES.map((type) => (
                    <SelectItem key={type} value={type}>
                      {type}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
            <Field label="Relationship Manager">
              <Combobox
                options={managerOptions}
                value={draft.relationship_manager}
                onChange={(value) => set('relationship_manager', value)}
                placeholder="Unassigned"
                allowClear
                clearLabel="Unassigned"
              />
            </Field>
            <Field label="PAN" htmlFor="client-pan" error={errors.pan}>
              <Input
                id="client-pan"
                value={draft.pan}
                onChange={(e) => set('pan', e.target.value.toUpperCase())}
                placeholder="AAAAA9999A"
                maxLength={10}
                className="font-mono"
              />
            </Field>
            <Field label="GSTIN" htmlFor="client-gstin" error={errors.gstin}>
              <Input
                id="client-gstin"
                value={draft.gstin}
                onChange={(e) => set('gstin', e.target.value.toUpperCase())}
                placeholder="07AAAAA9999A1Z5"
                maxLength={15}
                className="font-mono"
              />
            </Field>
            <Field label="Contact Person" htmlFor="client-contact">
              <Input
                id="client-contact"
                value={draft.contact_person}
                onChange={(e) => set('contact_person', e.target.value)}
              />
            </Field>
            <Field label="Phone" htmlFor="client-phone">
              <Input
                id="client-phone"
                value={draft.phone}
                onChange={(e) => set('phone', e.target.value)}
              />
            </Field>
            <Field label="Email" htmlFor="client-email">
              <Input
                id="client-email"
                type="email"
                value={draft.email}
                onChange={(e) => set('email', e.target.value)}
              />
            </Field>
            <Field label="City" htmlFor="client-city">
              <Input
                id="client-city"
                value={draft.city}
                onChange={(e) => set('city', e.target.value)}
              />
            </Field>
            <Field label="State" htmlFor="client-state">
              <Input
                id="client-state"
                value={draft.state}
                onChange={(e) => set('state', e.target.value)}
              />
            </Field>
            <Field label="Address" htmlFor="client-address" className="sm:col-span-2 lg:col-span-3">
              <Textarea
                id="client-address"
                rows={2}
                value={draft.address}
                onChange={(e) => set('address', e.target.value)}
              />
            </Field>
            <Field label="Notes" htmlFor="client-notes" className="sm:col-span-2 lg:col-span-3">
              <Textarea
                id="client-notes"
                rows={2}
                value={draft.notes}
                onChange={(e) => set('notes', e.target.value)}
              />
            </Field>
            <DialogFooter className="sm:col-span-2 lg:col-span-3">
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={saveClient.isPending}>
                {saveClient.isPending ? <Loader2 className="size-4 animate-spin" /> : null}
                {draft.id ? 'Save changes' : 'Add Client'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
