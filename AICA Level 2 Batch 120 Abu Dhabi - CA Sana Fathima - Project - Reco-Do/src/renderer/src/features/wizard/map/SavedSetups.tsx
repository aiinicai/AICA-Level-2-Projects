import { useEffect, useId, useState } from 'react'
import { ChevronDown } from 'lucide-react'
import type { SavedMapping } from '@shared/contracts'
import { formatDate } from '@shared/format'
import {
  Button,
  Dialog,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  Field,
  Input,
  useToast
} from '@/components/ui'
import { listMappings, listTemplates, newId, saveMapping, saveTemplate } from '@/lib/db'
import { errorMessage } from '@/lib/useAsync'
import { useWizard } from '../WizardContext'
import { configFromSaved, finalConfig, savedRecord } from '../configFactory'
import { missingColumns } from '../keys'

export type SaveKind = 'mapping' | 'template'

/** "Load saved mapping ▾" (and "Load template ▾" for General). */
export function LoadSavedMenu(): React.JSX.Element {
  const { state, module, dispatch, settings } = useWizard()
  const toast = useToast()
  const [mappings, setMappings] = useState<SavedMapping[] | null>(null)
  const [templates, setTemplates] = useState<SavedMapping[]>([])
  const [open, setOpen] = useState(false)
  const general = module.id === 'general'
  const ready = !!state.files.A && !!state.files.B

  useEffect(() => {
    if (!open) return
    let alive = true
    Promise.all([listMappings(module.id), general ? listTemplates() : Promise.resolve([])])
      .then(([m, t]) => {
        if (!alive) return
        setMappings(m)
        setTemplates(t)
      })
      .catch((err) => {
        if (alive) toast.error('Saved mappings could not be loaded', errorMessage(err))
      })
    return () => {
      alive = false
    }
  }, [open, module.id, general, toast])

  const apply = (saved: SavedMapping, kind: SaveKind): void => {
    const a = state.files.A?.table
    const b = state.files.B?.table
    if (!a || !b) return
    const cfg = configFromSaved(saved, module.id, settings.currency || 'AED')
    dispatch({ type: 'setConfig', config: cfg, source: { kind, name: saved.name } })
    const missing = missingColumns(cfg, a.columns, b.columns)
    if (missing.length > 0) {
      toast({ tone: 'warning', title: `${kind === 'template' ? 'Template' : 'Mapping'} '${saved.name}' loaded with gaps`, description: `These columns are not in the files: ${missing.join(', ')}. Choose them again.` })
    } else {
      toast.success(`${kind === 'template' ? 'Template' : 'Saved mapping'} '${saved.name}' loaded`)
    }
  }

  const item = (m: SavedMapping, kind: SaveKind): React.JSX.Element => (
    <DropdownMenuItem key={`${kind}-${m.id}`} onSelect={() => apply(m, kind)} hint={formatDate(new Date(m.updatedAt))}>
      {m.name}
    </DropdownMenuItem>
  )

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" disabled={!ready}>
          {general ? 'Load template' : 'Load saved mapping'} <ChevronDown size={14} />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent className="w-[340px]">
        {mappings === null ? (
          <DropdownMenuLabel>Loading…</DropdownMenuLabel>
        ) : (
          <>
            {general && (
              <>
                <DropdownMenuLabel>Templates</DropdownMenuLabel>
                {templates.length === 0 ? (
                  <div className="px-2.5 py-1.5 text-[12.5px] text-muted">No templates yet. Use “Save as template”.</div>
                ) : (
                  templates.map((t) => item(t, 'template'))
                )}
                <DropdownMenuSeparator />
              </>
            )}
            <DropdownMenuLabel>Saved mappings</DropdownMenuLabel>
            {mappings.length === 0 ? (
              <div className="px-2.5 py-1.5 text-[12.5px] text-muted">No saved mappings for this module yet. Use “Save mapping”.</div>
            ) : (
              mappings.map((m) => item(m, 'mapping'))
            )}
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

/** Save mapping / Save as template dialog. Saving under an existing name updates that record. */
export function SaveSetupDialog({ kind, open, onOpenChange }: { kind: SaveKind; open: boolean; onOpenChange: (o: boolean) => void }): React.JSX.Element {
  const { state, module, dispatch, settings } = useWizard()
  const toast = useToast()
  const id = useId()
  const [name, setName] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!open) return
    const src = state.configSource
    const suggested =
      src && src.kind === kind
        ? src.name
        : module.id === 'general'
          ? `${state.sideAName} vs ${state.sideBName}`
          : `${state.accountLabel || module.sideA} ↔ ${module.id === 'bank' ? 'GL' : module.sideB}`
    setName(suggested)
  }, [open, kind, state.configSource, state.sideAName, state.sideBName, state.accountLabel, module])

  const save = async (): Promise<void> => {
    const a = state.files.A?.table
    const b = state.files.B?.table
    const n = name.trim()
    if (!a || !b || !state.config || !n) return
    setSaving(true)
    try {
      const existing = (kind === 'template' ? await listTemplates() : await listMappings(module.id)).find((m) => m.name.toLowerCase() === n.toLowerCase())
      const record = savedRecord({
        id: existing?.id ?? newId(),
        createdAt: existing?.createdAt,
        name: n,
        moduleId: module.id,
        tableA: a,
        tableB: b,
        config: finalConfig(state.config, state.sideAName, state.sideBName, settings.currency || 'AED')
      })
      if (kind === 'template') await saveTemplate(record)
      else await saveMapping(record)
      dispatch({ type: 'setConfig', config: state.config, source: { kind, name: n } })
      toast.success(
        `${kind === 'template' ? 'Template' : 'Mapping'} '${n}' ${existing ? 'updated' : 'saved'}`,
        kind === 'mapping' ? 'It loads automatically next time files with the same columns are uploaded.' : 'Find it under Load template and in Mappings & Templates.'
      )
      onOpenChange(false)
    } catch (err) {
      toast.error('Could not save', errorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent width={480}>
        <form
          onSubmit={(e) => {
            e.preventDefault()
            void save()
          }}
        >
          <DialogHeader>
            <DialogTitle>{kind === 'template' ? 'Save as template' : 'Save mapping'}</DialogTitle>
            <DialogDescription>
              {kind === 'template'
                ? 'Stores the side names, key pairs, types, rules, tolerances and sign setting so you can reuse them with any files.'
                : 'Stores the keys, columns, rules and sign setting. When files with the same column headers are uploaded again, this mapping loads automatically.'}
            </DialogDescription>
          </DialogHeader>
          <DialogBody>
            <Field label="Name" htmlFor={id}>
              <Input id={id} autoFocus value={name} maxLength={80} onChange={(e) => setName(e.target.value)} placeholder="e.g. ENBD Current A/c ↔ GL 101200" />
            </Field>
          </DialogBody>
          <DialogFooter>
            <Button variant="secondary" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={!name.trim()} loading={saving}>
              Save
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
