"use client"

import { useState, useEffect, useCallback } from "react"
import {
  Card, CardContent, CardHeader, CardTitle, CardDescription,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table, TableHeader, TableBody, TableHead, TableRow, TableCell,
} from "@/components/ui/table"
import {
  Dialog, DialogContent, DialogHeader, DialogFooter,
  DialogTitle, DialogDescription, DialogClose,
} from "@/components/ui/dialog"
import {
  AlertDialog, AlertDialogTrigger, AlertDialogContent, AlertDialogHeader,
  AlertDialogFooter, AlertDialogTitle, AlertDialogDescription,
  AlertDialogAction, AlertDialogCancel,
} from "@/components/ui/alert-dialog"
import { useToast } from "@/components/ui/toast"
import { cn } from "@/lib/utils"
import { Search, Edit, Trash2, Loader2, AlertCircle, UserPlus, X } from "lucide-react"

interface OrgMember {
  id: string
  userId: string
  name: string | null
  email: string
  username: string
  image: string | null
  isActive: boolean
  roles: string[]
}

interface SearchUser {
  id: string
  name: string | null
  email: string
  username: string
}

const roleOptions = [
  { value: "ADMINISTRATOR", label: "Administrator" },
  { value: "MANAGER", label: "Manager" },
  { value: "PREPARER", label: "Preparer" },
  { value: "REVIEWER", label: "Reviewer" },
  { value: "APPROVER", label: "Approver" },
]

function getRoleVariant(role: string): "default" | "secondary" | "destructive" | "outline" {
  switch (role) {
    case "ADMINISTRATOR": return "default"
    case "MANAGER": return "secondary"
    case "PREPARER": return "outline"
    case "REVIEWER": return "outline"
    case "APPROVER": return "destructive"
    default: return "outline"
  }
}

export default function EmployeesPage() {
  const { toast } = useToast()
  const [data, setData] = useState<OrgMember[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState("")
  const [dialogOpen, setDialogOpen] = useState(false)
  const [deleteId, setDeleteId] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  // Add user flow
  const [userSearch, setUserSearch] = useState("")
  const [searchResults, setSearchResults] = useState<SearchUser[]>([])
  const [searching, setSearching] = useState(false)
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null)
  const [selectedUserDisplay, setSelectedUserDisplay] = useState<string>("")
  const [selectedRoles, setSelectedRoles] = useState<string[]>([])

  // Edit flow
  const [editingMember, setEditingMember] = useState<OrgMember | null>(null)
  const [editRoles, setEditRoles] = useState<string[]>([])

  const fetchData = useCallback(async () => {
    try {
      setLoading(true)
      const params = new URLSearchParams()
      if (search) params.set("search", search)
      const res = await fetch(`/api/employees?${params}`)
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.error || `HTTP ${res.status}`)
      }
      const json = await res.json()
      setData(json.data || [])
    } catch (e) {
      toast({ title: "Error", description: e instanceof Error ? e.message : "Failed to load employees", variant: "destructive" })
    } finally {
      setLoading(false)
    }
  }, [search, toast])

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- data fetching is async
    fetchData()
  }, [fetchData])

  async function handleUserSearch(q: string) {
    setUserSearch(q)
    if (q.length < 2) {
      setSearchResults([])
      return
    }
    setSearching(true)
    try {
      const res = await fetch(`/api/users?search=${encodeURIComponent(q)}&scope=all`)
      if (res.ok) {
        const json = await res.json()
        setSearchResults(json.data || [])
      }
    } catch {
      // silent
    } finally {
      setSearching(false)
    }
  }

  function handleOpenCreate() {
    setSelectedUserId(null)
    setSelectedUserDisplay("")
    setSelectedRoles(["PREPARER"])
    setUserSearch("")
    setSearchResults([])
    setDialogOpen(true)
  }

  function handleOpenEdit(item: OrgMember) {
    setEditingMember(item)
    setEditRoles([...item.roles])
  }

  async function handleAddMember() {
    if (!selectedUserId || selectedRoles.length === 0) return
    setSubmitting(true)
    try {
      const res = await fetch("/api/employees", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ userId: selectedUserId, roles: selectedRoles }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.error || "Failed to add member")
      }
      toast({ title: "Success", description: "Member added successfully" })
      setDialogOpen(false)
      fetchData()
    } catch (err) {
      toast({ title: "Error", description: (err as Error).message, variant: "destructive" })
    } finally {
      setSubmitting(false)
    }
  }

  async function handleUpdateRoles() {
    if (!editingMember || editRoles.length === 0) return
    setSubmitting(true)
    try {
      const res = await fetch(`/api/employees/${editingMember.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ roles: editRoles }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.error || "Failed to update roles")
      }
      toast({ title: "Success", description: "Roles updated successfully" })
      setEditingMember(null)
      fetchData()
    } catch (err) {
      toast({ title: "Error", description: (err as Error).message, variant: "destructive" })
    } finally {
      setSubmitting(false)
    }
  }

  async function handleDelete() {
    if (!deleteId) return
    try {
      const res = await fetch(`/api/employees/${deleteId}`, { method: "DELETE" })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.error || "Delete failed")
      }
      toast({ title: "Success", description: "Member removed successfully" })
      setDeleteId(null)
      fetchData()
    } catch (err) {
      toast({ title: "Error", description: (err as Error).message, variant: "destructive" })
    }
  }

  function toggleRole(role: string, currentRoles: string[], setter: (r: string[]) => void) {
    if (currentRoles.includes(role)) {
      if (currentRoles.length > 1) {
        setter(currentRoles.filter((r) => r !== role))
      }
    } else {
      setter([...currentRoles, role])
    }
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Employees</CardTitle>
            <CardDescription>Manage organization members and their roles.</CardDescription>
          </div>
          <Button onClick={handleOpenCreate}>
            <UserPlus className="h-4 w-4 mr-2" />
            Add Member
          </Button>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2 mb-4">
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-slate-400" />
              <Input
                placeholder="Search members..."
                className="pl-8"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
          </div>

          {loading ? (
            <div className="space-y-3">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : data.length === 0 ? (
            <div className="text-center py-12">
              <AlertCircle className="h-12 w-12 mx-auto text-slate-300" />
              <p className="mt-3 text-sm text-slate-500">
                {search ? "No members match your search." : "No members added yet."}
              </p>
              {!search && (
                <Button variant="outline" className="mt-4" onClick={handleOpenCreate}>
                  <UserPlus className="h-4 w-4 mr-2" />
                  Add your first member
                </Button>
              )}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Email</TableHead>
                    <TableHead>Roles</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="w-[100px]">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.map((item) => (
                    <TableRow key={item.id}>
                      <TableCell className="font-medium">{item.name || item.username || "-"}</TableCell>
                      <TableCell>{item.email}</TableCell>
                      <TableCell>
                        <div className="flex gap-1 flex-wrap">
                          {item.roles.map((r) => (
                            <Badge key={r} variant={getRoleVariant(r)} className="text-[10px]">
                              {r === "ADMINISTRATOR" ? "Admin" : r.charAt(0) + r.slice(1).toLowerCase()}
                            </Badge>
                          ))}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant={item.isActive ? "default" : "secondary"}>
                          {item.isActive ? "Active" : "Inactive"}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1">
                          <Button variant="ghost" size="icon" onClick={() => handleOpenEdit(item)}>
                            <Edit className="h-4 w-4" />
                          </Button>
                          <AlertDialog open={deleteId === item.id} onOpenChange={(open) => { if (!open) setDeleteId(null) }}>
                            <AlertDialogTrigger asChild>
                              <Button variant="ghost" size="icon" onClick={() => setDeleteId(item.id)}>
                                <Trash2 className="h-4 w-4 text-red-500" />
                              </Button>
                            </AlertDialogTrigger>
                            <AlertDialogContent>
                              <AlertDialogHeader>
                                <AlertDialogTitle>Remove Member</AlertDialogTitle>
                                <AlertDialogDescription>
                                  Are you sure you want to remove <strong>{item.name || item.email}</strong> from this organization?
                                </AlertDialogDescription>
                              </AlertDialogHeader>
                              <AlertDialogFooter>
                                <AlertDialogCancel>Cancel</AlertDialogCancel>
                                <AlertDialogAction className="bg-red-500 hover:bg-red-600" onClick={handleDelete}>
                                  Remove
                                </AlertDialogAction>
                              </AlertDialogFooter>
                            </AlertDialogContent>
                          </AlertDialog>
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

      {/* Add Member Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Add Member</DialogTitle>
            <DialogDescription>
              Search for an existing user and assign them roles in this organization.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="space-y-2">
              <Label>Search User</Label>
              <div className="relative">
                <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-slate-400" />
                <Input
                  placeholder="Type name or email..."
                  className="pl-8"
                  value={userSearch}
                  onChange={(e) => handleUserSearch(e.target.value)}
                />
              </div>
              {searching && <p className="text-xs text-slate-400">Searching...</p>}
              {searchResults.length > 0 && !selectedUserId && (
                <div className="border rounded-lg max-h-40 overflow-y-auto">
                  {searchResults.map((u) => (
                    <button
                      key={u.id}
                      type="button"
                      className="w-full text-left px-3 py-2 text-sm hover:bg-slate-100 border-b last:border-0"
                      onClick={() => {
                        setSelectedUserId(u.id)
                        setSelectedUserDisplay(`${u.name || u.username} (${u.email})`)
                        setSearchResults([])
                      }}
                    >
                      <span className="font-medium">{u.name || u.username}</span>
                      <span className="text-slate-400 ml-2">{u.email}</span>
                    </button>
                  ))}
                </div>
              )}
              {selectedUserId && (
                <div className="flex items-center gap-2 p-2 bg-slate-100 rounded-lg">
                  <span className="text-sm flex-1">{selectedUserDisplay}</span>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6"
                    onClick={() => { setSelectedUserId(null); setSelectedUserDisplay("") }}
                  >
                    <X className="h-3 w-3" />
                  </Button>
                </div>
              )}
            </div>
            <div className="space-y-2">
              <Label>Roles</Label>
              <div className="flex flex-wrap gap-2">
                {roleOptions.map((o) => {
                  const active = selectedRoles.includes(o.value)
                  return (
                    <button
                      key={o.value}
                      type="button"
                      onClick={() => toggleRole(o.value, selectedRoles, setSelectedRoles)}
                      className={cn(
                        "px-3 py-1.5 text-xs font-medium rounded-full border transition-colors",
                        active
                          ? "bg-[var(--color-primary)]/10 border-[var(--color-primary)] text-[var(--color-primary)]"
                          : "border-slate-200 text-slate-500 hover:border-slate-300"
                      )}
                    >
                      {o.label}
                    </button>
                  )
                })}
              </div>
            </div>
          </div>
          <DialogFooter>
            <DialogClose asChild>
              <Button type="button" variant="outline">Cancel</Button>
            </DialogClose>
            <Button onClick={handleAddMember} disabled={submitting || !selectedUserId || selectedRoles.length === 0}>
              {submitting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Add Member
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Roles Dialog */}
      <Dialog open={!!editingMember} onOpenChange={(open) => { if (!open) setEditingMember(null) }}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Edit Roles</DialogTitle>
            <DialogDescription>
              Update roles for {editingMember?.name || editingMember?.email}
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <Label className="mb-2 block">Roles</Label>
            <div className="flex flex-wrap gap-2">
              {roleOptions.map((o) => {
                const active = editRoles.includes(o.value)
                return (
                  <button
                    key={o.value}
                    type="button"
                    onClick={() => toggleRole(o.value, editRoles, setEditRoles)}
                    className={cn(
                      "px-3 py-1.5 text-xs font-medium rounded-full border transition-colors",
                      active
                        ? "bg-[var(--color-primary)]/10 border-[var(--color-primary)] text-[var(--color-primary)]"
                        : "border-slate-200 text-slate-500 hover:border-slate-300"
                    )}
                  >
                    {o.label}
                  </button>
                )
              })}
            </div>
          </div>
          <DialogFooter>
            <DialogClose asChild>
              <Button type="button" variant="outline">Cancel</Button>
            </DialogClose>
            <Button onClick={handleUpdateRoles} disabled={submitting || editRoles.length === 0}>
              {submitting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Update
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
