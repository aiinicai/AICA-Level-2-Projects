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
  Select, SelectTrigger, SelectValue, SelectContent, SelectItem,
} from "@/components/ui/select"
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
import DataImport from "@/components/data-import"
import { Plus, Search, Edit, Trash2, Loader2, AlertCircle } from "lucide-react"

interface Country {
  id: string
  name: string
}

interface Entity {
  id: string
  entityNumber: string
  entityName: string
  country: Country | null
  status: string
  taxRegistrationNumber: string | null
  currency: string | null
  approvalFlow: string
}

const emptyForm = {
  entityNumber: "",
  entityName: "",
  countryId: "",
  status: "ACTIVE",
  taxRegistrationNumber: "",
  currency: "",
  approvalFlow: "ONE_LEVEL",
}

export default function EntitiesPage() {
  const { toast } = useToast()
  const [data, setData] = useState<Entity[]>([])
  const [countries, setCountries] = useState<Country[]>([])
  const [currencies, setCurrencies] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState("")
  const [dialogOpen, setDialogOpen] = useState(false)
  const [deleteId, setDeleteId] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [form, setForm] = useState(emptyForm)
  const [editingId, setEditingId] = useState<string | null>(null)

  const fetchData = useCallback(async () => {
    try {
      setLoading(true)
      const params = new URLSearchParams()
      if (search) params.set("search", search)
      const res = await fetch(`/api/entities?${params}`)
      if (!res.ok) throw new Error("Failed to fetch")
      const json = await res.json()
      setData(json.data || [])
    } catch {
      toast({ title: "Error", description: "Failed to load entities", variant: "destructive" })
    } finally {
      setLoading(false)
    }
  }, [search, toast])

  const fetchCountries = useCallback(async () => {
    try {
      const res = await fetch("/api/countries")
      if (res.ok) {
        const json = await res.json()
        setCountries(json.data || [])
      }
    } catch {
      // silent
    }
  }, [])

  const fetchCurrencies = useCallback(async () => {
    try {
      const res = await fetch("/api/exchange-rates?limit=500")
      if (res.ok) {
        const json = await res.json()
        const unique = [...new Set<string>((json.data || []).map((r: { fromCurrency: string }) => r.fromCurrency))].sort()
        setCurrencies(unique)
      }
    } catch {
      // silent
    }
  }, [])

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- data fetching is async
    fetchData()
    fetchCountries()
    fetchCurrencies()
  }, [fetchData, fetchCountries, fetchCurrencies])

  function handleOpenCreate() {
    setEditingId(null)
    setForm(emptyForm)
    setDialogOpen(true)
  }

  function handleOpenEdit(item: Entity) {
    setEditingId(item.id)
    setForm({
      entityNumber: item.entityNumber,
      entityName: item.entityName,
      countryId: item.country?.id || "",
      status: item.status,
      taxRegistrationNumber: item.taxRegistrationNumber || "",
      currency: item.currency || "",
      approvalFlow: item.approvalFlow || "ONE_LEVEL",
    })
    setDialogOpen(true)
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    try {
      const url = editingId ? `/api/entities/${editingId}` : "/api/entities"
      const method = editingId ? "PUT" : "POST"
      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.error || "Request failed")
      }
      toast({
        title: "Success",
        description: editingId ? "Entity updated successfully" : "Entity created successfully",
      })
      setDialogOpen(false)
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
      const res = await fetch(`/api/entities/${deleteId}`, { method: "DELETE" })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.error || "Delete failed")
      }
      toast({ title: "Success", description: "Entity deleted successfully" })
      setDeleteId(null)
      fetchData()
    } catch (err) {
      toast({ title: "Error", description: (err as Error).message, variant: "destructive" })
    }
  }

  function getStatusVariant(status: string): "default" | "secondary" | "destructive" | "outline" {
    switch (status) {
      case "ACTIVE": return "default"
      case "INACTIVE": return "secondary"
      case "SUSPENDED": return "destructive"
      default: return "outline"
    }
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Legal Entities</CardTitle>
            <CardDescription>Manage legal entities.</CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <DataImport
              entityName="Entities"
              columns={[
                { key: "entityNumber", label: "Entity Number", required: true, description: "e.g. ENT-001" },
                { key: "entityName", label: "Entity Name", required: true, description: "e.g. Acme Corp" },
                { key: "countryId", label: "Country ID", required: true, description: "UUID from Countries" },
                { key: "status", label: "Status", description: "ACTIVE / INACTIVE / SUSPENDED" },
                { key: "taxRegistrationNumber", label: "Tax Reg Number", description: "e.g. TAX-12345" },
                { key: "currency", label: "Currency", description: "e.g. USD" },
                { key: "approvalFlow", label: "Approval Flow", description: "NONE / ONE_LEVEL / TWO_LEVEL" },
              ]}
              uploadEndpoint="/api/entities/upload"
              onComplete={fetchData}
            />
            <Button onClick={handleOpenCreate}>
              <Plus className="h-4 w-4 mr-2" />
              Add Entity
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2 mb-4">
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-slate-400" />
              <Input
                placeholder="Search entities..."
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
                {search ? "No entities match your search." : "No entities added yet."}
              </p>
              {!search && (
                <Button variant="outline" className="mt-4" onClick={handleOpenCreate}>
                  <Plus className="h-4 w-4 mr-2" />
                  Add your first entity
                </Button>
              )}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Entity Number</TableHead>
                    <TableHead>Entity Name</TableHead>
                    <TableHead>Country</TableHead>
                    <TableHead>Approval Flow</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Tax Reg Number</TableHead>
                    <TableHead>Legal Entity Functional Currency</TableHead>
                    <TableHead className="w-[100px]">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.map((item) => (
                    <TableRow key={item.id}>
                      <TableCell className="font-medium">{item.entityNumber}</TableCell>
                      <TableCell>{item.entityName}</TableCell>
                      <TableCell>{item.country?.name || "-"}</TableCell>
                      <TableCell>
                        <Badge variant={item.approvalFlow === "TWO_LEVEL" ? "default" : item.approvalFlow === "NONE" ? "outline" : "secondary"}>
                          {item.approvalFlow === "TWO_LEVEL" ? "Two-Level" : item.approvalFlow === "NONE" ? "None" : "One-Level"}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant={getStatusVariant(item.status)}>{item.status}</Badge>
                      </TableCell>
                      <TableCell>{item.taxRegistrationNumber || "-"}</TableCell>
                      <TableCell>{item.currency || "-"}</TableCell>
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
                                <AlertDialogTitle>Delete Entity</AlertDialogTitle>
                                <AlertDialogDescription>
                                  Are you sure you want to delete <strong>{item.entityName}</strong>? This action cannot be undone.
                                </AlertDialogDescription>
                              </AlertDialogHeader>
                              <AlertDialogFooter>
                                <AlertDialogCancel>Cancel</AlertDialogCancel>
                                <AlertDialogAction className="bg-red-500 hover:bg-red-600" onClick={handleDelete}>
                                  Delete
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

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-lg">
          <form onSubmit={handleSubmit}>
            <DialogHeader>
              <DialogTitle>{editingId ? "Edit Entity" : "Add Entity"}</DialogTitle>
              <DialogDescription>
                {editingId ? "Update the entity details below." : "Fill in the details to add a new entity."}
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="entityNumber">Entity Number *</Label>
                  <Input id="entityNumber" value={form.entityNumber} onChange={(e) => setForm({ ...form, entityNumber: e.target.value })} required />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="entityName">Entity Name *</Label>
                  <Input id="entityName" value={form.entityName} onChange={(e) => setForm({ ...form, entityName: e.target.value })} required />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="countryId">Country *</Label>
                  <Select value={form.countryId} onValueChange={(v) => setForm({ ...form, countryId: v })} required>
                    <SelectTrigger id="countryId">
                      <SelectValue placeholder="Select country" />
                    </SelectTrigger>
                    <SelectContent>
                      {countries.map((c) => (
                        <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="status">Status</Label>
                  <Select value={form.status} onValueChange={(v) => setForm({ ...form, status: v })}>
                    <SelectTrigger id="status">
                      <SelectValue placeholder="Select status" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="ACTIVE">Active</SelectItem>
                      <SelectItem value="INACTIVE">Inactive</SelectItem>
                      <SelectItem value="SUSPENDED">Suspended</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="approvalFlow">Approval Flow *</Label>
                <Select value={form.approvalFlow} onValueChange={(v) => setForm({ ...form, approvalFlow: v })}>
                  <SelectTrigger id="approvalFlow">
                    <SelectValue placeholder="Select approval flow" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="NONE">None (no approval)</SelectItem>
                    <SelectItem value="ONE_LEVEL">One-Level (Reviewer only)</SelectItem>
                    <SelectItem value="TWO_LEVEL">Two-Level (Reviewer then Approver)</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-[var(--color-muted-foreground)]">
                  Determines how submitted compliances are approved for this entity.
                </p>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="taxRegistrationNumber">Tax Registration Number</Label>
                  <Input id="taxRegistrationNumber" value={form.taxRegistrationNumber} onChange={(e) => setForm({ ...form, taxRegistrationNumber: e.target.value })} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="currency">Legal Entity Functional Currency</Label>
                  <Select value={form.currency} onValueChange={(v) => setForm({ ...form, currency: v })}>
                    <SelectTrigger id="currency">
                      <SelectValue placeholder="Select currency" />
                    </SelectTrigger>
                    <SelectContent>
                      {currencies.length === 0 && (
                        <SelectItem value="USD">USD</SelectItem>
                      )}
                      {currencies.map((c) => (
                        <SelectItem key={c} value={c}>{c}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>
            <DialogFooter>
              <DialogClose asChild>
                <Button type="button" variant="outline">Cancel</Button>
              </DialogClose>
              <Button type="submit" disabled={submitting}>
                {submitting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                {editingId ? "Update" : "Create"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
