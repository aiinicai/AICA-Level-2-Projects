"use client"

import { useState, useEffect, useCallback } from "react"
import {
  Card, CardContent, CardHeader, CardTitle, CardDescription,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Switch } from "@/components/ui/switch"
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
import { TAX_TYPE_OPTIONS, taxTypeLabel } from "@/lib/tax-types"
import { APPROVAL_FLOW_OPTIONS } from "@/lib/approval-flow"

const importColumns = [
  { key: "formNumber", label: "Form Number", required: true, description: "Unique form number" },
  { key: "formName", label: "Form Name", required: true, description: "Descriptive form name" },
  { key: "taxType", label: "Tax Type", description: "e.g. VAT, WHT, GST" },
  { key: "description", label: "Description", description: "Form description" },
  { key: "requiresPayment", label: "Requires Payment", description: "yes/no — whether this form's filing requires payment" },
  { key: "approvalFlow", label: "Approval Flow", description: "NONE / ONE_LEVEL / TWO_LEVEL" },
]

interface FormMaster {
  id: string
  formNumber: string
  formName: string
  taxType: string | null
  complianceTypeId: string | null
  description: string | null
  requiresPayment: boolean
  approvalFlow: string
}

const emptyForm = {
  formNumber: "",
  formName: "",
  taxType: "",
  complianceTypeId: "",
  description: "",
  requiresPayment: true,
  approvalFlow: "ONE_LEVEL",
}

export default function FormsPage() {
  const { toast } = useToast()
  const [data, setData] = useState<FormMaster[]>([])
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
      const res = await fetch(`/api/forms?${params}`)
      if (!res.ok) throw new Error("Failed to fetch forms")
      const json = await res.json()
      setData(json.data || [])
    } catch {
      toast({ title: "Error", description: "Failed to load forms", variant: "destructive" })
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

  async function handleOpenEdit(item: FormMaster) {
    setEditingId(item.id)
    try {
      const res = await fetch(`/api/forms/${item.id}`)
      if (res.ok) {
        const json = await res.json()
        const detail = json.data
        setForm({
          formNumber: detail.formNumber || "",
          formName: detail.formName || "",
          taxType: detail.taxType || "",
          complianceTypeId: detail.complianceTypeId || "",
          description: detail.description || "",
          requiresPayment: detail.requiresPayment === undefined ? true : detail.requiresPayment === true,
          approvalFlow: detail.approvalFlow || "ONE_LEVEL",
        })
      } else {
        setForm({
          formNumber: item.formNumber || "",
          formName: item.formName || "",
          taxType: item.taxType || "",
          complianceTypeId: item.complianceTypeId || "",
          description: item.description || "",
          requiresPayment: item.requiresPayment === undefined ? true : item.requiresPayment === true,
          approvalFlow: item.approvalFlow || "ONE_LEVEL",
        })
      }
    } catch {
      setForm({
        formNumber: item.formNumber || "",
        formName: item.formName || "",
        taxType: item.taxType || "",
        complianceTypeId: item.complianceTypeId || "",
        description: item.description || "",
        requiresPayment: item.requiresPayment === undefined ? true : item.requiresPayment === true,
        approvalFlow: item.approvalFlow || "ONE_LEVEL",
      })
    }
    setDialogOpen(true)
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!form.formNumber.trim() || !form.formName.trim()) {
      toast({ title: "Validation Error", description: "Form Number and Form Name are required", variant: "destructive" })
      return
    }

    setSubmitting(true)
    try {
      const url = editingId ? `/api/forms/${editingId}` : "/api/forms"
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
        description: editingId ? "Form updated successfully" : "Form created successfully",
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
      const res = await fetch(`/api/forms/${deleteId}`, { method: "DELETE" })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.error || "Delete failed")
      }
      toast({ title: "Success", description: "Form deleted successfully" })
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
            <CardTitle>Forms</CardTitle>
            <CardDescription>Manage form masters and tax requirements.</CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <DataImport
              entityName="Forms"
              columns={importColumns}
              uploadEndpoint="/api/forms/upload"
              onComplete={fetchData}
            />
            <Button onClick={handleOpenCreate}>
              <Plus className="h-4 w-4 mr-2" />
              Add Form
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2 mb-4">
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-slate-400" />
              <Input
                placeholder="Search forms..."
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
                {search ? "No forms match your search." : "No forms added yet."}
              </p>
              {!search && (
                <Button variant="outline" className="mt-4" onClick={handleOpenCreate}>
                  <Plus className="h-4 w-4 mr-2" />
                  Add your first form
                </Button>
              )}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Form Number</TableHead>
                    <TableHead>Form Name</TableHead>
                    <TableHead>Tax Type</TableHead>
                    <TableHead>Payment Required</TableHead>
                    <TableHead>Approval Flow</TableHead>
                    <TableHead>Description</TableHead>
                    <TableHead className="w-[100px]">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.map((item) => (
                    <TableRow key={item.id}>
                      <TableCell className="font-medium">{item.formNumber}</TableCell>
                      <TableCell>{item.formName}</TableCell>
                      <TableCell>{taxTypeLabel(item.taxType)}</TableCell>
                      <TableCell>
                        <Badge variant={item.requiresPayment === false ? "secondary" : "default"}>
                          {item.requiresPayment === false ? "No" : "Yes"}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant={item.approvalFlow === "TWO_LEVEL" ? "default" : item.approvalFlow === "NONE" ? "outline" : "secondary"}>
                          {item.approvalFlow === "TWO_LEVEL" ? "Two-Level" : item.approvalFlow === "NONE" ? "None" : "One-Level"}
                        </Badge>
                      </TableCell>
                      <TableCell className="max-w-[200px] truncate">{item.description || "-"}</TableCell>
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
                                <AlertDialogTitle>Delete Form</AlertDialogTitle>
                                <AlertDialogDescription>
                                  Are you sure you want to delete <strong>{item.formName}</strong>? This action cannot be undone.
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
              <DialogTitle>{editingId ? "Edit Form" : "Add Form"}</DialogTitle>
              <DialogDescription>
                {editingId ? "Update the form details below." : "Fill in the details to add a new form."}
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="formNumber">Form Number *</Label>
                  <Input
                    id="formNumber"
                    value={form.formNumber}
                    onChange={(e) => setForm({ ...form, formNumber: e.target.value })}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="formName">Form Name *</Label>
                  <Input
                    id="formName"
                    value={form.formName}
                    onChange={(e) => setForm({ ...form, formName: e.target.value })}
                    required
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="taxType">Tax Type</Label>
                  <Select value={form.taxType} onValueChange={(v) => setForm({ ...form, taxType: v })}>
                    <SelectTrigger id="taxType">
                      <SelectValue placeholder="Select tax type" />
                    </SelectTrigger>
                    <SelectContent>
                      {TAX_TYPE_OPTIONS.map((t) => (
                        <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="description">Description</Label>
                  <Input
                    id="description"
                    value={form.description}
                    onChange={(e) => setForm({ ...form, description: e.target.value })}
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="approvalFlow">Approval Flow *</Label>
                  <Select value={form.approvalFlow} onValueChange={(v) => setForm({ ...form, approvalFlow: v })}>
                    <SelectTrigger id="approvalFlow">
                      <SelectValue placeholder="Select approval flow" />
                    </SelectTrigger>
                    <SelectContent>
                      {APPROVAL_FLOW_OPTIONS.map((f) => (
                        <SelectItem key={f.value} value={f.value}>{f.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-[var(--color-muted-foreground)]">
                    Compared against the entity master on each compliance. The form&apos;s flow applies.
                  </p>
                </div>
              </div>
              <div className="flex items-center justify-between border rounded-md p-3">
                <div>
                  <Label htmlFor="requiresPayment">Requires Payment</Label>
                  <p className="text-xs text-[var(--color-muted-foreground)]">
                    Whether this form&apos;s filing requires payment. Non-payment filings skip the payment section.
                  </p>
                </div>
                <Switch
                  id="requiresPayment"
                  checked={form.requiresPayment}
                  onCheckedChange={(v) => setForm({ ...form, requiresPayment: v === true })}
                />
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

