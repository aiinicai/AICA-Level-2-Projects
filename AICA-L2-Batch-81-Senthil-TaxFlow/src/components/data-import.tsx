"use client"

import { useState, useRef } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Dialog, DialogContent, DialogHeader, DialogFooter,
  DialogTitle, DialogDescription, DialogClose,
} from "@/components/ui/dialog"
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { useToast } from "@/components/ui/toast"
import { Upload, Download, Loader2, CheckCircle2, XCircle, Plus } from "lucide-react"

export interface ImportColumn {
  key: string
  label: string
  required?: boolean
  description?: string
}

interface DataImportProps {
  entityName: string
  columns: ImportColumn[]
  uploadEndpoint: string
  onComplete: () => void
  dropdownTrigger?: string
}

export default function DataImport({ entityName, columns, uploadEndpoint, onComplete, dropdownTrigger }: DataImportProps) {
  const { toast } = useToast()
  const [open, setOpen] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [uploadResult, setUploadResult] = useState<{ inserted: number; skipped: number; total: number } | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  function downloadTemplate() {
    const header = columns.map((c) => c.label).join(",")
    const sample = columns.map((c) => c.description || "").join(",")
    const csv = `${header}\n${sample}`
    const blob = new Blob([csv], { type: "text/csv" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = `${entityName.toLowerCase().replace(/\s+/g, "-")}-template.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
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

      const headers = lines[0].split(",").map((h) => h.trim().toLowerCase().replace(/\s+/g, ""))
      const colIndexes = columns.map((c) => {
        const idx = headers.indexOf(c.label.toLowerCase().replace(/\s+/g, ""))
        if (idx === -1 && c.required) return -1
        return idx
      })

      const missingRequired = columns.filter((_, i) => colIndexes[i] === -1 && columns[i].required)
      if (missingRequired.length > 0) {
        toast({
          title: "Error",
          description: `CSV missing required columns: ${missingRequired.map((c) => c.label).join(", ")}`,
          variant: "destructive",
        })
        return
      }

      const items: Record<string, string>[] = []
      for (let i = 1; i < lines.length; i++) {
        const cols = lines[i].split(",").map((c) => c.trim())
        const item: Record<string, string> = {}
        let valid = true
        for (let j = 0; j < columns.length; j++) {
          const idx = colIndexes[j]
          if (idx !== undefined && idx >= 0 && idx < cols.length) {
            item[columns[j].key] = cols[idx]
          } else if (columns[j].required) {
            valid = false
          }
        }
        if (valid && Object.keys(item).length > 0) {
          items.push(item)
        }
      }

      if (items.length === 0) {
        toast({ title: "Error", description: "No valid rows found in CSV", variant: "destructive" })
        return
      }

      setUploading(true)
      setUploadResult(null)
      try {
        const res = await fetch(uploadEndpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ items }),
        })
        if (!res.ok) {
          const err = await res.json().catch(() => ({}))
          throw new Error(err.error || "Upload failed")
        }
        const json = await res.json()
        setUploadResult(json.data)
        toast({
          title: "Upload complete",
          description: `Inserted/Updated ${json.data.inserted} of ${json.data.total} ${entityName.toLowerCase()}`,
        })
        onComplete()
      } catch (err) {
        toast({ title: "Error", description: (err as Error).message, variant: "destructive" })
      } finally {
        setUploading(false)
      }
    }
    reader.readAsText(file)
    if (fileInputRef.current) fileInputRef.current.value = ""
  }

  return (
    <>
      {dropdownTrigger ? (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline">
              <Plus className="h-4 w-4 mr-1" />
              {dropdownTrigger}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={downloadTemplate}>
              <Download className="h-4 w-4 mr-2" />
              Download Template
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => { setOpen(true); setUploadResult(null) }}>
              <Upload className="h-4 w-4 mr-2" />
              Upload CSV
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ) : (
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={downloadTemplate}>
            <Download className="h-4 w-4 mr-2" />
            Template
          </Button>
          <Button variant="outline" onClick={() => { setOpen(true); setUploadResult(null) }}>
            <Upload className="h-4 w-4 mr-2" />
            Upload CSV
          </Button>
        </div>
      )}

      <Dialog open={open} onOpenChange={(o) => { setOpen(o); if (!o) setUploadResult(null) }}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Import {entityName}</DialogTitle>
            <DialogDescription>
              Upload a CSV file with columns:{" "}
              <strong>{columns.map((c) => c.label).join(", ")}</strong>.
              {columns.some((c) => c.required) && " Required columns are marked."}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="rounded-md bg-slate-50 p-3 text-xs text-slate-500">
              <p className="font-medium mb-1">Required columns:</p>
              <ul className="list-disc list-inside space-y-0.5">
                {columns.map((c) => (
                  <li key={c.key}>
                    <code>{c.label}</code>
                    {c.required && <span className="text-red-500 ml-1">*</span>}
                    {c.description && <span className="ml-1">- {c.description}</span>}
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <Input
                ref={fileInputRef}
                type="file"
                accept=".csv"
                onChange={handleFileUpload}
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
              <div className="text-sm space-y-1">
                <p className="flex items-center gap-1.5 text-green-600">
                  <CheckCircle2 className="h-4 w-4" />
                  Inserted/Updated: {uploadResult.inserted}
                </p>
                {uploadResult.skipped > 0 && (
                  <p className="flex items-center gap-1.5 text-amber-600">
                    <XCircle className="h-4 w-4" />
                    Skipped: {uploadResult.skipped}
                  </p>
                )}
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
    </>
  )
}
