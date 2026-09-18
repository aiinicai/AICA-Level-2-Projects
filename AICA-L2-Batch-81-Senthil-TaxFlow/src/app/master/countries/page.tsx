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
import DataImport from "@/components/data-import"
import {
  Plus, Search, Edit, Trash2, Loader2, AlertCircle,
} from "lucide-react"

interface Country {
  id: string
  name: string
  code: string
  region: string | null
}

const emptyForm = {
  name: "",
  code: "",
  region: "",
}

export default function CountriesPage() {
  const { toast } = useToast()
  const [data, setData] = useState<Country[]>([])
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
      const res = await fetch(`/api/countries?${params}`)
      if (!res.ok) throw new Error("Failed to fetch")
      const json = await res.json()
      setData(json.data || [])
    } catch {
      toast({ title: "Error", description: "Failed to load countries", variant: "destructive" })
    } finally {
      setLoading(false)
    }
  }, [search, toast])

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- data fetching is async
    fetchData()
  }, [fetchData])

  function handleOpenCreate() {
    setEditingId(null)
    setForm(emptyForm)
    setDialogOpen(true)
  }

  function handleOpenEdit(item: Country) {
    setEditingId(item.id)
    setForm({
      name: item.name,
      code: item.code,
      region: item.region || "",
    })
    setDialogOpen(true)
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    try {
      const url = editingId
        ? `/api/countries/${editingId}`
        : "/api/countries"
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
        description: editingId ? "Country updated successfully" : "Country created successfully",
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
      const res = await fetch(`/api/countries/${deleteId}`, { method: "DELETE" })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.error || "Delete failed")
      }
      toast({ title: "Success", description: "Country deleted successfully" })
      setDeleteId(null)
      fetchData()
    } catch (err) {
      toast({ title: "Error", description: (err as Error).message, variant: "destructive" })
    }
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Countries</CardTitle>
            <CardDescription>Manage country master data.</CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <DataImport
              entityName="Countries"
              columns={[
                { key: "name", label: "Name", required: true, description: "e.g. United States" },
                { key: "code", label: "Code", required: true, description: "e.g. US" },
                { key: "region", label: "Region", description: "e.g. North America" },
              ]}
              uploadEndpoint="/api/countries/upload"
              onComplete={fetchData}
            />
            <Button onClick={handleOpenCreate}>
              <Plus className="h-4 w-4 mr-2" />
              Add Country
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2 mb-4">
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-slate-400" />
              <Input
                placeholder="Search countries..."
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
                {search ? "No countries match your search." : "No countries added yet."}
              </p>
              {!search && (
                <Button variant="outline" className="mt-4" onClick={handleOpenCreate}>
                  <Plus className="h-4 w-4 mr-2" />
                  Add your first country
                </Button>
              )}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Code</TableHead>
                    <TableHead>Region</TableHead>
                    <TableHead className="w-[100px]">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.map((item) => (
                    <TableRow key={item.id}>
                      <TableCell className="font-medium">{item.name}</TableCell>
                      <TableCell><Badge variant="outline">{item.code}</Badge></TableCell>
                      <TableCell>{item.region || "-"}</TableCell>
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
                                <AlertDialogTitle>Delete Country</AlertDialogTitle>
                                <AlertDialogDescription>
                                  Are you sure you want to delete <strong>{item.name}</strong>? This action cannot be undone.
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
              <DialogTitle>{editingId ? "Edit Country" : "Add Country"}</DialogTitle>
              <DialogDescription>
                {editingId ? "Update the country details below." : "Fill in the details to add a new country."}
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="name">Name *</Label>
                  <Input id="name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="code">Code *</Label>
                  <Input id="code" value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} required maxLength={3} placeholder="e.g. US" />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="region">Region</Label>
                <Input id="region" value={form.region} onChange={(e) => setForm({ ...form, region: e.target.value })} placeholder="e.g. North America" />
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
