"use client"

import { useState, useEffect, useCallback, useRef } from "react"
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
import {
  Plus, Search, Edit, Trash2, Loader2, AlertCircle, Upload, Download, FileSpreadsheet,
} from "lucide-react"

interface ExchangeRate {
  id: string
  fromCurrency: string
  toCurrency: string
  rate: number
  date: string
  createdAt: string
  updatedAt: string
}

const emptyForm = {
  fromCurrency: "",
  rate: "",
  date: "",
}

export default function ExchangeRatesPage() {
  const { toast } = useToast()
  const [data, setData] = useState<ExchangeRate[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState("")
  const [dialogOpen, setDialogOpen] = useState(false)
  const [deleteId, setDeleteId] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [form, setForm] = useState(emptyForm)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [uploadOpen, setUploadOpen] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [uploadResult, setUploadResult] = useState<{ inserted: number; skipped: number; total: number } | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const fetchData = useCallback(async () => {
    try {
      setLoading(true)
      const params = new URLSearchParams()
      if (search) params.set("search", search)
      const res = await fetch(`/api/exchange-rates?${params}`)
      if (!res.ok) throw new Error("Failed to fetch")
      const json = await res.json()
      setData(json.data || [])
    } catch {
      toast({ title: "Error", description: "Failed to load exchange rates", variant: "destructive" })
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

  function handleOpenEdit(item: ExchangeRate) {
    setEditingId(item.id)
    setForm({
      fromCurrency: item.fromCurrency,
      rate: String(item.rate),
      date: item.date,
    })
    setDialogOpen(true)
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    try {
      const url = editingId
        ? `/api/exchange-rates/${editingId}`
        : "/api/exchange-rates"
      const method = editingId ? "PUT" : "POST"
      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          fromCurrency: form.fromCurrency,
          rate: parseFloat(form.rate),
          date: form.date,
        }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.error || "Request failed")
      }
      toast({
        title: "Success",
        description: editingId ? "Exchange rate updated successfully" : "Exchange rate created successfully",
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
      const res = await fetch(`/api/exchange-rates/${deleteId}`, { method: "DELETE" })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.error || "Delete failed")
      }
      toast({ title: "Success", description: "Exchange rate deleted successfully" })
      setDeleteId(null)
      fetchData()
    } catch (err) {
      toast({ title: "Error", description: (err as Error).message, variant: "destructive" })
    }
  }

  function downloadTemplate() {
    const csv = "fromCurrency,rate,date\nINR,83.50,2026-07-15\nGBP,0.78,2026-07-15\nEUR,0.92,2026-07-15"
    const blob = new Blob([csv], { type: "text/csv" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = "exchange-rates-template.csv"
    a.click()
    URL.revokeObjectURL(url)
  }

  function handleCSVUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return

    const reader = new FileReader()
    reader.onload = async (event) => {
      const text = event.target?.result as string
      const lines = text.split("\n").filter((l) => l.trim())
      if (lines.length < 2) {
        toast({ title: "Error", description: "CSV must have a header row and at least one data row", variant: "destructive" })
        return
      }

      const headers = lines[0].split(",").map((h) => h.trim().toLowerCase())
      const fromIdx = headers.indexOf("fromcurrency")
      const rateIdx = headers.indexOf("rate")
      const dateIdx = headers.indexOf("date")

      if (fromIdx === -1 || rateIdx === -1 || dateIdx === -1) {
        toast({ title: "Error", description: "CSV must have columns: fromCurrency, rate, date", variant: "destructive" })
        return
      }

      const rates = []
      for (let i = 1; i < lines.length; i++) {
        const cols = lines[i].split(",").map((c) => c.trim())
        const fromCurrency = cols[fromIdx]
        const rate = parseFloat(cols[rateIdx])
        const date = cols[dateIdx]
        if (fromCurrency && !isNaN(rate) && date) {
          rates.push({ fromCurrency, rate, date })
        }
      }

      if (rates.length === 0) {
        toast({ title: "Error", description: "No valid rows found in CSV", variant: "destructive" })
        return
      }

      setUploading(true)
      setUploadResult(null)
      try {
        const res = await fetch("/api/exchange-rates/upload", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ rates }),
        })
        if (!res.ok) throw new Error("Upload failed")
        const json = await res.json()
        setUploadResult(json.data)
        toast({
          title: "Upload complete",
          description: `Inserted/Updated ${json.data.inserted} of ${json.data.total} rates`,
        })
        fetchData()
      } catch {
        toast({ title: "Error", description: "Failed to upload rates", variant: "destructive" })
      } finally {
        setUploading(false)
      }
    }
    reader.readAsText(file)
    if (fileInputRef.current) fileInputRef.current.value = ""
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Exchange Rates</CardTitle>
            <CardDescription>Manage currency exchange rates for USD conversion.</CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={downloadTemplate}>
              <Download className="h-4 w-4 mr-2" />
              Template
            </Button>
            <Dialog open={uploadOpen} onOpenChange={(o) => { setUploadOpen(o); if (!o) setUploadResult(null) }}>
              <Button variant="outline" onClick={() => setUploadOpen(true)}>
                <Upload className="h-4 w-4 mr-2" />
                Upload CSV
              </Button>
              <DialogContent className="sm:max-w-md">
                <DialogHeader>
                  <DialogTitle>Upload Exchange Rates</DialogTitle>
                  <DialogDescription>
                    Upload a CSV file with columns: <strong>fromCurrency, rate, date</strong>. Existing rates for the same currency and date will be updated.
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4 py-4">
                  <div className="rounded-md bg-slate-50 p-3 text-xs text-slate-500">
                    <p className="font-medium mb-1">Example CSV:</p>
                    <code className="block">
                      fromCurrency,rate,date<br />
                      INR,83.50,2026-07-15<br />
                      GBP,0.78,2026-07-15<br />
                      EUR,0.92,2026-07-15
                    </code>
                  </div>
                  <div>
                    <Input
                      ref={fileInputRef}
                      type="file"
                      accept=".csv"
                      onChange={handleCSVUpload}
                      disabled={uploading}
                    />
                  </div>
                  {uploading && (
                    <div className="flex items-center gap-2 text-sm text-slate-500">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Uploading and processing...
                    </div>
                  )}
                  {uploadResult && (
                    <div className="text-sm">
                      <p className="text-green-600">Inserted/Updated: {uploadResult.inserted}</p>
                      <p className="text-slate-500">Skipped: {uploadResult.skipped}</p>
                      <p className="text-slate-500">Total: {uploadResult.total}</p>
                    </div>
                  )}
                </div>
                <DialogFooter>
                  <DialogClose asChild>
                    <Button type="button" variant="outline">Close</Button>
                  </DialogClose>
                </DialogFooter>
              </DialogContent>
            </Dialog>
            <Button onClick={handleOpenCreate}>
              <Plus className="h-4 w-4 mr-2" />
              Add Rate
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2 mb-4">
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-slate-400" />
              <Input
                placeholder="Search by currency..."
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
                {search ? "No exchange rates match your search." : "No exchange rates added yet."}
              </p>
              {!search && (
                <div className="flex items-center justify-center gap-2 mt-4">
                  <Button variant="outline" onClick={handleOpenCreate}>
                    <Plus className="h-4 w-4 mr-2" />
                    Add your first rate
                  </Button>
                  <Button variant="outline" onClick={() => setUploadOpen(true)}>
                    <FileSpreadsheet className="h-4 w-4 mr-2" />
                    Upload CSV
                  </Button>
                </div>
              )}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>From Currency</TableHead>
                    <TableHead>To Currency</TableHead>
                    <TableHead>Rate</TableHead>
                    <TableHead>Date</TableHead>
                    <TableHead className="w-[100px]">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.map((item) => (
                    <TableRow key={item.id}>
                      <TableCell className="font-medium">{item.fromCurrency}</TableCell>
                      <TableCell><Badge variant="outline">{item.toCurrency}</Badge></TableCell>
                      <TableCell>{Number(item.rate).toFixed(6)}</TableCell>
                      <TableCell>{item.date}</TableCell>
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
                                <AlertDialogTitle>Delete Exchange Rate</AlertDialogTitle>
                                <AlertDialogDescription>
                                  Are you sure you want to delete the rate for <strong>{item.fromCurrency}</strong> on <strong>{item.date}</strong>? This action cannot be undone.
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
              <DialogTitle>{editingId ? "Edit Exchange Rate" : "Add Exchange Rate"}</DialogTitle>
              <DialogDescription>
                {editingId ? "Update the exchange rate details below." : "Fill in the details to add a new exchange rate."}
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="fromCurrency">From Currency *</Label>
                  <Input
                    id="fromCurrency"
                    value={form.fromCurrency}
                    onChange={(e) => setForm({ ...form, fromCurrency: e.target.value })}
                    required
                    maxLength={3}
                    placeholder="e.g. INR"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="rate">Rate *</Label>
                  <Input
                    id="rate"
                    type="number"
                    step="0.000001"
                    min="0"
                    value={form.rate}
                    onChange={(e) => setForm({ ...form, rate: e.target.value })}
                    required
                    placeholder="e.g. 83.50"
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="date">Date *</Label>
                <Input
                  id="date"
                  type="date"
                  value={form.date}
                  onChange={(e) => setForm({ ...form, date: e.target.value })}
                  required
                />
              </div>
              <div className="text-xs text-slate-500">
                Rate is the amount of <strong>{form.fromCurrency || "foreign currency"}</strong> equal to 1 USD.
                <br />Example: if 1 USD = 83.50 INR, enter fromCurrency: INR, rate: 83.50
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
