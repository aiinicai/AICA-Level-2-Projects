import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import {
  Copy,
  Loader2,
  Mail,
  Pencil,
  Search,
  ShieldCheck,
  ShieldOff,
  Trash2,
  UserPlus,
  Users,
} from 'lucide-react'
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
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { EmptyState, Field, PageHeader, StatCard, TableSkeleton } from '@/components/common'
import { useAuth } from '@/components/auth-provider'
import { friendlyError, supabase } from '@/lib/supabase'
import { DESIGNATIONS, FIRM_NAME } from '@/lib/constants'
import { formatDate, toDateInput } from '@/lib/utils'
import type { AllowedEmail, Designation, Profile } from '@/types/db'

type RowKind = 'invite' | 'staff'

interface Row {
  kind: RowKind
  id: string
  name: string
  email: string
  designation: Designation
  isActive: boolean
  joined: string | null
  invite?: AllowedEmail
  staff?: Profile
}

export default function EmployeesPage() {
  const { session } = useAuth()
  const queryClient = useQueryClient()

  const [search, setSearch] = useState('')
  const [designationFilter, setDesignationFilter] = useState<string>('all')

  const [inviteOpen, setInviteOpen] = useState(false)
  const [inviteName, setInviteName] = useState('')
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteDesignation, setInviteDesignation] = useState<Designation>('Accountant')
  const [inviteErrors, setInviteErrors] = useState<{ name?: string; email?: string }>({})
  const [invitedConfirmation, setInvitedConfirmation] = useState<{
    name: string
    email: string
  } | null>(null)

  const [editingStaff, setEditingStaff] = useState<Profile | null>(null)
  const [editingInvite, setEditingInvite] = useState<AllowedEmail | null>(null)
  const [deletingInvite, setDeletingInvite] = useState<AllowedEmail | null>(null)

  const profilesQuery = useQuery({
    queryKey: ['profiles'],
    queryFn: async () => {
      const { data, error } = await supabase.from('profiles').select('*').order('full_name')
      if (error) throw error
      return data as Profile[]
    },
  })

  // Who currently holds the admin role. Kept in its own table on purpose, so
  // nobody can promote themselves by editing their profile row.
  const adminsQuery = useQuery({
    queryKey: ['user_roles', 'admin'],
    queryFn: async () => {
      const { data, error } = await supabase
        .from('user_roles')
        .select('user_id')
        .eq('role', 'admin')
      if (error) throw error
      return (data as { user_id: string }[]).map((r) => r.user_id)
    },
  })

  const adminIds = useMemo(() => new Set(adminsQuery.data ?? []), [adminsQuery.data])

  const invitesQuery = useQuery({
    queryKey: ['allowed_emails'],
    queryFn: async () => {
      const { data, error } = await supabase
        .from('allowed_emails')
        .select('*')
        .eq('is_used', false)
        .order('created_at', { ascending: false })
      if (error) throw error
      return data as AllowedEmail[]
    },
  })

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ['profiles'] })
    void queryClient.invalidateQueries({ queryKey: ['allowed_emails'] })
  }

  const addInvite = useMutation({
    mutationFn: async (payload: { full_name: string; email: string; designation: Designation }) => {
      const { error } = await supabase.from('allowed_emails').insert({
        full_name: payload.full_name,
        email: payload.email,
        designation: payload.designation,
        invited_by: session?.user.id ?? null,
      })
      if (error) throw error
    },
    onSuccess: (_data, variables) => {
      invalidate()
      setInviteOpen(false)
      setInvitedConfirmation({ name: variables.full_name, email: variables.email })
      toast.success('Employee added to the invite list')
    },
    onError: (error) => toast.error(friendlyError(error)),
  })

  const updateInvite = useMutation({
    mutationFn: async (payload: AllowedEmail) => {
      const { error } = await supabase
        .from('allowed_emails')
        .update({
          full_name: payload.full_name,
          email: payload.email.trim().toLowerCase(),
          designation: payload.designation,
        })
        .eq('id', payload.id)
      if (error) throw error
    },
    onSuccess: () => {
      invalidate()
      setEditingInvite(null)
      toast.success('Invite updated')
    },
    onError: (error) => toast.error(friendlyError(error)),
  })

  const deleteInvite = useMutation({
    mutationFn: async (id: string) => {
      const { error } = await supabase.from('allowed_emails').delete().eq('id', id)
      if (error) throw error
    },
    onSuccess: () => {
      invalidate()
      setDeletingInvite(null)
      toast.success('Invite removed — that email can no longer sign up')
    },
    onError: (error) => toast.error(friendlyError(error)),
  })

  const updateStaff = useMutation({
    mutationFn: async (payload: Profile) => {
      const { error } = await supabase
        .from('profiles')
        .update({
          full_name: payload.full_name,
          designation: payload.designation,
          phone: payload.phone,
          date_of_joining: payload.date_of_joining || null,
        })
        .eq('id', payload.id)
      if (error) throw error
    },
    onSuccess: () => {
      invalidate()
      setEditingStaff(null)
      toast.success('Employee updated')
    },
    onError: (error) => toast.error(friendlyError(error)),
  })

  const toggleAdmin = useMutation({
    mutationFn: async (payload: { userId: string; makeAdmin: boolean }) => {
      if (payload.makeAdmin) {
        const { error } = await supabase
          .from('user_roles')
          .insert({ user_id: payload.userId, role: 'admin' })
        if (error) throw error
      } else {
        const { error } = await supabase
          .from('user_roles')
          .delete()
          .eq('user_id', payload.userId)
          .eq('role', 'admin')
        if (error) throw error
      }
    },
    onSuccess: (_d, variables) => {
      void queryClient.invalidateQueries({ queryKey: ['user_roles', 'admin'] })
      toast.success(
        variables.makeAdmin
          ? 'Administrator access granted'
          : 'Administrator access removed',
      )
    },
    onError: (error) => toast.error(friendlyError(error)),
  })

  const toggleActive = useMutation({
    mutationFn: async (payload: { id: string; is_active: boolean }) => {
      const { error } = await supabase
        .from('profiles')
        .update({ is_active: payload.is_active })
        .eq('id', payload.id)
      if (error) throw error
    },
    onSuccess: (_d, variables) => {
      invalidate()
      toast.success(variables.is_active ? 'Employee activated' : 'Employee deactivated')
    },
    onError: (error) => toast.error(friendlyError(error)),
  })

  const rows = useMemo<Row[]>(() => {
    const invites: Row[] = (invitesQuery.data ?? []).map((invite) => ({
      kind: 'invite',
      id: invite.id,
      name: invite.full_name ?? '—',
      email: invite.email,
      designation: invite.designation,
      isActive: false,
      joined: null,
      invite,
    }))
    const staff: Row[] = (profilesQuery.data ?? []).map((profile) => ({
      kind: 'staff',
      id: profile.id,
      name: profile.full_name,
      email: profile.email,
      designation: profile.designation,
      isActive: profile.is_active,
      joined: profile.date_of_joining ?? profile.created_at,
      staff: profile,
    }))
    // Pending invites first — they are the ones needing an action.
    return [...invites, ...staff]
  }, [invitesQuery.data, profilesQuery.data])

  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase()
    return rows.filter((row) => {
      if (designationFilter !== 'all' && row.designation !== designationFilter) return false
      if (!term) return true
      return row.name.toLowerCase().includes(term) || row.email.toLowerCase().includes(term)
    })
  }, [rows, search, designationFilter])

  const summary = useMemo(() => {
    const staff = profilesQuery.data ?? []
    const byDesignation = new Map<string, number>()
    for (const person of staff) {
      byDesignation.set(person.designation, (byDesignation.get(person.designation) ?? 0) + 1)
    }
    return {
      total: staff.length,
      active: staff.filter((p) => p.is_active).length,
      pending: invitesQuery.data?.length ?? 0,
      byDesignation: [...byDesignation.entries()].sort((a, b) => b[1] - a[1]),
    }
  }, [profilesQuery.data, invitesQuery.data])

  /**
   * Adding an employee does not send mail — it only authorises the address.
   * Rather than pretend otherwise, hand the admin something they can paste
   * into WhatsApp, which is how a firm this size actually tells people.
   */
  function inviteText(name: string | null, email: string) {
    const origin = window.location.origin
    return (
      `Hello ${name?.trim() || 'there'},\n\n` +
      `You have been added to the ${FIRM_NAME} task tracker.\n\n` +
      `1. Open ${origin}\n` +
      `2. Choose "Sign Up"\n` +
      `3. Register using exactly this email: ${email}\n` +
      `4. Set your own password (minimum 8 characters)\n\n` +
      `Any other email address will be refused. Once registered you will see the tasks assigned to you.`
    )
  }

  async function copyInvite(name: string | null, email: string) {
    try {
      await navigator.clipboard.writeText(inviteText(name, email))
      toast.success('Invite message copied — paste it into WhatsApp or email')
    } catch {
      toast.error('Could not copy. Select the text in the dialog instead.')
    }
  }

  function submitInvite(event: React.FormEvent) {
    event.preventDefault()
    const email = inviteEmail.trim().toLowerCase()
    const errors: { name?: string; email?: string } = {}
    if (!inviteName.trim()) errors.name = 'Full name is required.'
    if (!email) errors.email = 'Email is required.'
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) errors.email = 'Enter a valid email address.'
    setInviteErrors(errors)
    if (Object.keys(errors).length) return

    addInvite.mutate({ full_name: inviteName.trim(), email, designation: inviteDesignation })
  }

  const loading = profilesQuery.isLoading || invitesQuery.isLoading
  const queryError = profilesQuery.error ?? invitesQuery.error

  return (
    <div className="space-y-5">
      <PageHeader
        title="Employee Master"
        description="Invite staff, then manage everyone who has registered."
      >
        <Button
          onClick={() => {
            setInviteName('')
            setInviteEmail('')
            setInviteDesignation('Accountant')
            setInviteErrors({})
            setInviteOpen(true)
          }}
        >
          <UserPlus className="size-4" />
          Add Employee
        </Button>
      </PageHeader>

      <div className="grid gap-3 sm:grid-cols-3">
        <StatCard label="Total Staff" value={summary.total} icon={Users} />
        <StatCard label="Active" value={summary.active} icon={Users} tone="success" />
        <StatCard
          label="Pending Invites"
          value={summary.pending}
          icon={Mail}
          tone={summary.pending ? 'accent' : 'default'}
        />
      </div>

      {summary.byDesignation.length ? (
        <div className="flex flex-wrap gap-2">
          {summary.byDesignation.map(([designation, count]) => (
            <Badge key={designation} variant="outline" className="font-normal">
              {designation}
              <span className="text-muted-foreground ml-1.5 tabular-nums">{count}</span>
            </Badge>
          ))}
        </div>
      ) : null}

      <Card className="py-0">
        <CardContent className="p-0">
          <div className="flex flex-col gap-3 border-b p-4 sm:flex-row sm:items-center">
            <div className="relative flex-1">
              <Search className="text-muted-foreground absolute top-1/2 left-2.5 size-4 -translate-y-1/2" />
              <Input
                placeholder="Search by name or email…"
                className="pl-8"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <Select value={designationFilter} onValueChange={setDesignationFilter}>
              <SelectTrigger className="sm:w-56">
                <SelectValue placeholder="All designations" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All designations</SelectItem>
                {DESIGNATIONS.map((designation) => (
                  <SelectItem key={designation} value={designation}>
                    {designation}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {loading ? (
            <TableSkeleton cols={6} />
          ) : queryError ? (
            <div className="text-destructive p-6 text-sm">{friendlyError(queryError)}</div>
          ) : filtered.length === 0 ? (
            <div className="p-4">
              <EmptyState
                title={rows.length ? 'No one matches those filters' : 'No employees yet'}
                description={
                  rows.length
                    ? 'Try clearing the search box or the designation filter.'
                    : 'Add your first employee to the invite list. They can then sign up with that exact email.'
                }
                action={
                  rows.length ? null : (
                    <Button onClick={() => setInviteOpen(true)}>
                      <UserPlus className="size-4" />
                      Add Employee
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
                    <TableHead>Name</TableHead>
                    <TableHead>Email</TableHead>
                    <TableHead>Designation</TableHead>
                    <TableHead>Role</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Joined</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filtered.map((row) => (
                    <TableRow key={`${row.kind}-${row.id}`}>
                      <TableCell className="font-medium">{row.name}</TableCell>
                      <TableCell className="text-muted-foreground">{row.email}</TableCell>
                      <TableCell>{row.designation}</TableCell>
                      <TableCell>
                        {row.kind === 'invite' ? (
                          <span className="text-muted-foreground text-sm">—</span>
                        ) : adminIds.has(row.id) ? (
                          <Badge className="gap-1 whitespace-nowrap">
                            <ShieldCheck className="size-3" />
                            Administrator
                          </Badge>
                        ) : (
                          <Badge variant="secondary" className="whitespace-nowrap">
                            Employee
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell>
                        {row.kind === 'invite' ? (
                          <Badge
                            variant="outline"
                            className="border-warning text-warning whitespace-nowrap"
                          >
                            Invited — not signed up
                          </Badge>
                        ) : row.isActive ? (
                          <Badge
                            variant="outline"
                            className="border-success text-success whitespace-nowrap"
                          >
                            Active
                          </Badge>
                        ) : (
                          <Badge variant="secondary" className="whitespace-nowrap">
                            Inactive
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-muted-foreground whitespace-nowrap">
                        {row.kind === 'invite' ? '—' : formatDate(row.joined)}
                      </TableCell>
                      <TableCell>
                        <div className="flex justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() =>
                              row.kind === 'invite'
                                ? setEditingInvite(row.invite!)
                                : setEditingStaff(row.staff!)
                            }
                          >
                            <Pencil className="size-3.5" />
                            Edit
                          </Button>
                          {row.kind === 'invite' ? (
                            <>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => void copyInvite(row.name, row.email)}
                                title="Copy a message to send them"
                              >
                                <Copy className="size-3.5" />
                                Invite text
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                className="text-destructive hover:text-destructive"
                                onClick={() => setDeletingInvite(row.invite!)}
                              >
                                <Trash2 className="size-3.5" />
                                Delete
                              </Button>
                            </>
                          ) : (
                            <>
                              <Button
                                variant="ghost"
                                size="sm"
                                disabled={
                                  toggleAdmin.isPending || row.id === session?.user.id
                                }
                                title={
                                  row.id === session?.user.id
                                    ? 'You cannot change your own administrator access'
                                    : undefined
                                }
                                onClick={() =>
                                  toggleAdmin.mutate({
                                    userId: row.id,
                                    makeAdmin: !adminIds.has(row.id),
                                  })
                                }
                              >
                                {adminIds.has(row.id) ? (
                                  <>
                                    <ShieldOff className="size-3.5" />
                                    Remove admin
                                  </>
                                ) : (
                                  <>
                                    <ShieldCheck className="size-3.5" />
                                    Make admin
                                  </>
                                )}
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() =>
                                  toggleActive.mutate({ id: row.id, is_active: !row.isActive })
                                }
                              >
                                {row.isActive ? 'Deactivate' : 'Activate'}
                              </Button>
                            </>
                          )}
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

      {/* Add employee */}
      <Dialog open={inviteOpen} onOpenChange={setInviteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Employee</DialogTitle>
            <DialogDescription>
              This authorises the email to create an account. It does not create the account itself.
            </DialogDescription>
          </DialogHeader>
          <form className="space-y-4" onSubmit={submitInvite} noValidate>
            <Field label="Full Name" htmlFor="invite-name" error={inviteErrors.name} required>
              <Input
                id="invite-name"
                value={inviteName}
                onChange={(e) => setInviteName(e.target.value)}
              />
            </Field>
            <Field label="Email" htmlFor="invite-email" error={inviteErrors.email} required>
              <Input
                id="invite-email"
                type="email"
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
              />
            </Field>
            <Field label="Designation" required>
              <Select
                value={inviteDesignation}
                onValueChange={(value) => setInviteDesignation(value as Designation)}
              >
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {DESIGNATIONS.map((designation) => (
                    <SelectItem key={designation} value={designation}>
                      {designation}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setInviteOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={addInvite.isPending}>
                {addInvite.isPending ? <Loader2 className="size-4 animate-spin" /> : null}
                Add Employee
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Post-invite instruction */}
      <Dialog
        open={Boolean(invitedConfirmation)}
        onOpenChange={(open) => !open && setInvitedConfirmation(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Employee added — no email was sent</DialogTitle>
            <DialogDescription>
              This authorises the address. Telling them is still up to you.
            </DialogDescription>
          </DialogHeader>
          <p className="text-sm">
            They must register themselves using exactly this address:
          </p>
          <p className="bg-muted rounded-md px-3 py-2 font-mono text-sm">
            {invitedConfirmation?.email}
          </p>
          <pre className="bg-muted max-h-48 overflow-y-auto rounded-md px-3 py-2 text-xs whitespace-pre-wrap">
            {invitedConfirmation
              ? inviteText(invitedConfirmation.name, invitedConfirmation.email)
              : ''}
          </pre>
          <p className="text-muted-foreground text-sm">
            Any other address is refused by the database. They appear here as “Active” once
            registered.
          </p>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() =>
                invitedConfirmation &&
                void copyInvite(invitedConfirmation.name, invitedConfirmation.email)
              }
            >
              <Copy className="size-4" />
              Copy message
            </Button>
            <Button onClick={() => setInvitedConfirmation(null)}>Got it</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit registered employee */}
      <Dialog open={Boolean(editingStaff)} onOpenChange={(open) => !open && setEditingStaff(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Employee</DialogTitle>
            <DialogDescription>{editingStaff?.email}</DialogDescription>
          </DialogHeader>
          {editingStaff ? (
            <form
              className="space-y-4"
              onSubmit={(event) => {
                event.preventDefault()
                updateStaff.mutate(editingStaff)
              }}
            >
              <Field label="Full Name" htmlFor="staff-name" required>
                <Input
                  id="staff-name"
                  value={editingStaff.full_name}
                  onChange={(e) =>
                    setEditingStaff({ ...editingStaff, full_name: e.target.value })
                  }
                />
              </Field>
              <Field label="Designation" required>
                <Select
                  value={editingStaff.designation}
                  onValueChange={(value) =>
                    setEditingStaff({ ...editingStaff, designation: value as Designation })
                  }
                >
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {DESIGNATIONS.map((designation) => (
                      <SelectItem key={designation} value={designation}>
                        {designation}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </Field>
              <div className="grid gap-4 sm:grid-cols-2">
                <Field label="Phone" htmlFor="staff-phone">
                  <Input
                    id="staff-phone"
                    value={editingStaff.phone ?? ''}
                    onChange={(e) => setEditingStaff({ ...editingStaff, phone: e.target.value })}
                  />
                </Field>
                <Field label="Date of Joining" htmlFor="staff-doj">
                  <Input
                    id="staff-doj"
                    type="date"
                    value={toDateInput(editingStaff.date_of_joining)}
                    onChange={(e) =>
                      setEditingStaff({ ...editingStaff, date_of_joining: e.target.value })
                    }
                  />
                </Field>
              </div>
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setEditingStaff(null)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={updateStaff.isPending}>
                  {updateStaff.isPending ? <Loader2 className="size-4 animate-spin" /> : null}
                  Save
                </Button>
              </DialogFooter>
            </form>
          ) : null}
        </DialogContent>
      </Dialog>

      {/* Edit pending invite */}
      <Dialog open={Boolean(editingInvite)} onOpenChange={(open) => !open && setEditingInvite(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Invite</DialogTitle>
            <DialogDescription>This person has not signed up yet.</DialogDescription>
          </DialogHeader>
          {editingInvite ? (
            <form
              className="space-y-4"
              onSubmit={(event) => {
                event.preventDefault()
                updateInvite.mutate(editingInvite)
              }}
            >
              <Field label="Full Name" htmlFor="invite-edit-name">
                <Input
                  id="invite-edit-name"
                  value={editingInvite.full_name ?? ''}
                  onChange={(e) =>
                    setEditingInvite({ ...editingInvite, full_name: e.target.value })
                  }
                />
              </Field>
              <Field label="Email" htmlFor="invite-edit-email" required>
                <Input
                  id="invite-edit-email"
                  type="email"
                  value={editingInvite.email}
                  onChange={(e) => setEditingInvite({ ...editingInvite, email: e.target.value })}
                />
              </Field>
              <Field label="Designation" required>
                <Select
                  value={editingInvite.designation}
                  onValueChange={(value) =>
                    setEditingInvite({ ...editingInvite, designation: value as Designation })
                  }
                >
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {DESIGNATIONS.map((designation) => (
                      <SelectItem key={designation} value={designation}>
                        {designation}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </Field>
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setEditingInvite(null)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={updateInvite.isPending}>
                  {updateInvite.isPending ? <Loader2 className="size-4 animate-spin" /> : null}
                  Save
                </Button>
              </DialogFooter>
            </form>
          ) : null}
        </DialogContent>
      </Dialog>

      <AlertDialog
        open={Boolean(deletingInvite)}
        onOpenChange={(open) => !open && setDeletingInvite(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Remove this invite?</AlertDialogTitle>
            <AlertDialogDescription>
              {deletingInvite?.email} will no longer be able to create an account. You can add the
              address again later.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => deletingInvite && deleteInvite.mutate(deletingInvite.id)}
            >
              Remove
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
