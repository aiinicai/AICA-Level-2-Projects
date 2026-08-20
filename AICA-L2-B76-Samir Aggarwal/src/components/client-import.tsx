import { useMemo, useRef, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import {
  AlertTriangle,
  CheckCircle2,
  Download,
  FileSpreadsheet,
  Loader2,
  Upload,
  X,
} from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { useAuth } from '@/components/auth-provider'
import { QK, useClients, useProfiles } from '@/hooks/use-app-data'
import { friendlyError, supabase } from '@/lib/supabase'
import { CLIENT_TYPES, GSTIN_REGEX, PAN_REGEX } from '@/lib/constants'
import { readSheet } from '@/lib/sheet-parse'
import { cn } from '@/lib/utils'
import type { ClientType } from '@/types/db'

interface ParsedRow {
  rowNumber: string
  status: 'new' | 'duplicate' | 'error'
  messages: string[]
  payload: {
    name: string
    client_code: string | null
    client_group: string | null
    client_type: ClientType
    pan: string | null
    gstin: string | null
    contact_person: string | null
    email: string | null
    phone: string | null
    address: string | null
    city: string | null
    state: string | null
    relationship_manager: string | null
    notes: string | null
  }
}

const blank = (value: string | undefined) => (value && value.trim() ? value.trim() : null)

export function ClientImportDialog({
  open,
  onOpenChange,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const { session } = useAuth()
  const queryClient = useQueryClient()
  const clientsQuery = useClients()
  const profilesQuery = useProfiles()
  const fileInput = useRef<HTMLInputElement>(null)

  const [fileName, setFileName] = useState<string | null>(null)
  const [parsing, setParsing] = useState(false)
  const [rows, setRows] = useState<ParsedRow[] | null>(null)
  const [parseError, setParseError] = useState<string | null>(null)

  const summary = useMemo(() => {
    const list = rows ?? []
    return {
      total: list.length,
      importable: list.filter((r) => r.status === 'new').length,
      duplicates: list.filter((r) => r.status === 'duplicate').length,
      errors: list.filter((r) => r.status === 'error').length,
      warnings: list.filter((r) => r.status === 'new' && r.messages.length).length,
    }
  }, [rows])

  function reset() {
    setFileName(null)
    setRows(null)
    setParseError(null)
    if (fileInput.current) fileInput.current.value = ''
  }

  async function handleFile(file: File) {
    setParsing(true)
    setParseError(null)
    setRows(null)
    setFileName(file.name)

    try {
      const raw = await readSheet(file)

      const existingNames = new Set(
        (clientsQuery.data ?? []).map((c) => c.name.trim().toLowerCase()),
      )
      const existingCodes = new Set(
        (clientsQuery.data ?? [])
          .map((c) => c.client_code?.trim().toLowerCase())
          .filter(Boolean) as string[],
      )

      const staffByEmail = new Map<string, string>()
      const staffByName = new Map<string, string>()
      for (const profile of profilesQuery.data ?? []) {
        staffByEmail.set(profile.email.trim().toLowerCase(), profile.id)
        staffByName.set(profile.full_name.trim().toLowerCase(), profile.id)
      }

      const seenNames = new Set<string>()
      const seenCodes = new Set<string>()
      const parsed: ParsedRow[] = []

      for (const row of raw) {
        const name = (row.name ?? '').trim()
        // The template ships with a greyed example row; skip it silently.
        if (!name || name.toUpperCase().startsWith('EXAMPLE')) continue

        const messages: string[] = []
        let status: ParsedRow['status'] = 'new'

        const code = blank(row.clientcode)
        const key = name.toLowerCase()
        const codeKey = code?.toLowerCase()

        if (existingNames.has(key) || (codeKey && existingCodes.has(codeKey))) {
          status = 'duplicate'
          messages.push('Already exists — skipped')
        } else if (seenNames.has(key) || (codeKey && seenCodes.has(codeKey))) {
          status = 'duplicate'
          messages.push('Repeated earlier in this file — skipped')
        }

        seenNames.add(key)
        if (codeKey) seenCodes.add(codeKey)

        // Client type
        const rawType = (row.clienttype ?? '').trim()
        let clientType: ClientType = 'Individual'
        if (rawType) {
          const match = CLIENT_TYPES.find(
            (t) => t.toLowerCase() === rawType.toLowerCase(),
          )
          if (match) {
            clientType = match
          } else {
            messages.push(`Unknown client type "${rawType}" — set to Individual`)
          }
        }

        // PAN / GSTIN are optional, so a bad value must never block the client.
        // Import them without it and say so — the field is editable afterwards.
        let pan = blank(row.pan)?.toUpperCase() ?? null
        if (pan && !PAN_REGEX.test(pan)) {
          messages.push(`PAN "${pan}" ignored — not a valid PAN`)
          pan = null
        }

        let gstin = blank(row.gstin)?.toUpperCase() ?? null
        if (gstin && !GSTIN_REGEX.test(gstin)) {
          messages.push(`GSTIN "${gstin}" ignored — not a valid GSTIN`)
          gstin = null
        }

        // Relationship manager
        const rmRaw = blank(row.relationshipmanager)
        let rm: string | null = null
        if (rmRaw) {
          rm =
            staffByEmail.get(rmRaw.toLowerCase()) ??
            staffByName.get(rmRaw.toLowerCase()) ??
            null
          if (!rm) messages.push(`No staff member matches "${rmRaw}" — left unassigned`)
        }

        parsed.push({
          rowNumber: row.__row ?? '?',
          status,
          messages,
          payload: {
            name,
            client_code: code,
            client_group: blank(row.group),
            client_type: clientType,
            pan,
            gstin,
            contact_person: blank(row.contactperson),
            email: blank(row.email),
            phone: blank(row.phone),
            address: blank(row.address),
            city: blank(row.city),
            state: blank(row.state),
            relationship_manager: rm,
            notes: blank(row.notes),
          },
        })
      }

      if (!parsed.length) {
        setParseError(
          'No client rows found. Check that the first row holds the column headings from the template.',
        )
      }
      setRows(parsed)
    } catch (error) {
      setParseError(error instanceof Error ? error.message : String(error))
    } finally {
      setParsing(false)
    }
  }

  const importRows = useMutation({
    mutationFn: async () => {
      const payloads = (rows ?? [])
        .filter((r) => r.status === 'new')
        .map((r) => ({ ...r.payload, created_by: session?.user.id ?? null }))

      // Chunked so a long list does not hit the request size limit.
      let inserted = 0
      for (let i = 0; i < payloads.length; i += 100) {
        const chunk = payloads.slice(i, i + 100)
        const { error } = await supabase.from('clients').insert(chunk)
        if (error) throw error
        inserted += chunk.length
      }
      return inserted
    },
    onSuccess: (count) => {
      void queryClient.invalidateQueries({ queryKey: QK.clients })
      toast.success(`${count} client${count === 1 ? '' : 's'} imported`)
      reset()
      onOpenChange(false)
    },
    onError: (error) => toast.error(friendlyError(error)),
  })

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) reset()
        onOpenChange(next)
      }}
    >
      <DialogContent className="max-h-[92vh] overflow-hidden sm:max-w-4xl">
        <DialogHeader>
          <DialogTitle>Import Clients</DialogTitle>
          <DialogDescription>
            Nothing is saved until you press Import. Every row is shown first.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-wrap items-center gap-3 rounded-lg border p-3">
          <Button variant="outline" asChild>
            <a href="/client-upload-template.xlsx" download>
              <Download className="size-4" />
              Download template
            </a>
          </Button>

          <input
            ref={fileInput}
            type="file"
            accept=".xlsx,.xlsm,.csv"
            className="hidden"
            onChange={(event) => {
              const file = event.target.files?.[0]
              if (file) void handleFile(file)
            }}
          />
          <Button onClick={() => fileInput.current?.click()} disabled={parsing}>
            {parsing ? <Loader2 className="size-4 animate-spin" /> : <Upload className="size-4" />}
            Choose file
          </Button>

          {fileName ? (
            <span className="text-muted-foreground flex items-center gap-1.5 text-sm">
              <FileSpreadsheet className="size-3.5" />
              {fileName}
              <Button variant="ghost" size="icon" className="size-5" onClick={reset}>
                <X className="size-3" />
              </Button>
            </span>
          ) : (
            <span className="text-muted-foreground text-sm">.xlsx or .csv</span>
          )}
        </div>

        {parseError ? (
          <div className="text-destructive flex items-start gap-2 rounded-md border border-current/30 p-3 text-sm">
            <AlertTriangle className="mt-0.5 size-4 shrink-0" />
            <span>{parseError}</span>
          </div>
        ) : null}

        {rows && rows.length ? (
          <>
            <div className="flex flex-wrap gap-2">
              <Badge variant="outline">{summary.total} rows read</Badge>
              <Badge className="bg-success text-success-foreground">
                {summary.importable} to import
              </Badge>
              {summary.duplicates ? (
                <Badge variant="secondary">{summary.duplicates} duplicate</Badge>
              ) : null}
              {summary.errors ? (
                <Badge variant="destructive">{summary.errors} with errors</Badge>
              ) : null}
              {summary.warnings ? (
                <Badge variant="outline" className="border-warning text-warning">
                  {summary.warnings} with warnings
                </Badge>
              ) : null}
            </div>

            <ScrollArea className="h-[45vh] rounded-md border">
              <Table>
                <TableHeader className="bg-background sticky top-0 z-10">
                  <TableRow>
                    <TableHead className="w-14">Row</TableHead>
                    <TableHead>Name</TableHead>
                    <TableHead>Group</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>PAN</TableHead>
                    <TableHead className="w-28">Status</TableHead>
                    <TableHead>Notes</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rows.map((row, index) => (
                    <TableRow
                      key={`${row.rowNumber}-${index}`}
                      className={cn(
                        row.status === 'error' && 'bg-destructive/5',
                        row.status === 'duplicate' && 'opacity-60',
                      )}
                    >
                      <TableCell className="text-muted-foreground text-xs tabular-nums">
                        {row.rowNumber}
                      </TableCell>
                      <TableCell className="font-medium">{row.payload.name}</TableCell>
                      <TableCell className="text-sm">
                        {row.payload.client_group ?? '—'}
                      </TableCell>
                      <TableCell className="text-sm whitespace-nowrap">
                        {row.payload.client_type}
                      </TableCell>
                      <TableCell className="font-mono text-xs">
                        {row.payload.pan ?? '—'}
                      </TableCell>
                      <TableCell>
                        {row.status === 'new' ? (
                          <Badge
                            variant="outline"
                            className="border-success text-success gap-1"
                          >
                            <CheckCircle2 className="size-3" />
                            New
                          </Badge>
                        ) : row.status === 'duplicate' ? (
                          <Badge variant="secondary">Skip</Badge>
                        ) : (
                          <Badge variant="destructive">Error</Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-muted-foreground text-xs">
                        {row.messages.join(' · ') || '—'}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </ScrollArea>
          </>
        ) : null}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={() => importRows.mutate()}
            disabled={!summary.importable || importRows.isPending}
          >
            {importRows.isPending ? <Loader2 className="size-4 animate-spin" /> : null}
            {summary.importable
              ? `Import ${summary.importable} client${summary.importable === 1 ? '' : 's'}`
              : 'Import'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
