import { useState } from 'react'
import { Copy, FileCog, MoreHorizontal, Pencil, Trash2 } from 'lucide-react'
import type { SavedMapping, ToolRecipe } from '@shared/contracts'
import { getModule } from '@shared/modules'
import { getTool } from '@shared/tools'
import { formatDate } from '@shared/format'
import {
  Badge,
  Button,
  Card,
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
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  EmptyState,
  Field,
  Input,
  Spinner,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  TechnicalDetails,
  useConfirm,
  useToast
} from '@/components/ui'
import { deleteMapping, deleteRecipe, deleteTemplate, listMappings, listRecipes, listTemplates, newId, saveMapping, saveRecipe, saveTemplate } from '@/lib/db'
import { errorMessage, useAsync } from '@/lib/useAsync'

/** What every saved item has in common, so one list component serves mappings, templates and recipes. */
interface SavedItem {
  id: string
  name: string
  createdAt: string
  updatedAt: string
}

interface ListProps<T extends SavedItem> {
  kind: string
  items: T[]
  describe: (item: T) => { badge: React.ReactNode; detail: React.ReactNode }
  onSave: (item: T) => Promise<void>
  onDelete: (id: string) => Promise<void>
  onChange: (items: T[]) => void
  emptyTitle: string
  emptyText: string
}

function updatedLabel(iso: string): string {
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? '' : formatDate(d)
}

function uniqueCopyName(name: string, taken: Set<string>): string {
  let candidate = `${name} (copy)`
  for (let n = 2; taken.has(candidate.toLowerCase()); n++) candidate = `${name} (copy ${n})`
  return candidate
}

function SavedList<T extends SavedItem>({ kind, items, describe, onSave, onDelete, onChange, emptyTitle, emptyText }: ListProps<T>): React.JSX.Element {
  const toast = useToast()
  const confirm = useConfirm()
  const [renaming, setRenaming] = useState<T | null>(null)
  const [newName, setNewName] = useState('')
  const [saving, setSaving] = useState(false)

  const nameTaken = (name: string, exceptId?: string): boolean =>
    items.some((i) => i.id !== exceptId && i.name.trim().toLowerCase() === name.trim().toLowerCase())

  const rename = async (): Promise<void> => {
    if (!renaming) return
    const name = newName.trim()
    setSaving(true)
    try {
      const updated = { ...renaming, name, updatedAt: new Date().toISOString() }
      await onSave(updated)
      onChange(items.map((i) => (i.id === updated.id ? updated : i)))
      setRenaming(null)
      toast.success(`Renamed to "${name}"`)
    } catch (err) {
      toast.error('Rename failed', errorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  const duplicate = async (item: T): Promise<void> => {
    const now = new Date().toISOString()
    const copy = { ...structuredClone(item), id: newId(), name: uniqueCopyName(item.name, new Set(items.map((i) => i.name.toLowerCase()))), createdAt: now, updatedAt: now }
    try {
      await onSave(copy)
      onChange([copy, ...items])
      toast.success(`Created "${copy.name}"`)
    } catch (err) {
      toast.error('Duplicate failed', errorMessage(err))
    }
  }

  const remove = async (item: T): Promise<void> => {
    const ok = await confirm({
      title: `Delete this ${kind}?`,
      description: `"${item.name}" will be removed from this computer. Reconciliations already saved are not affected.`,
      confirmLabel: 'Delete',
      tone: 'danger'
    })
    if (!ok) return
    try {
      await onDelete(item.id)
      onChange(items.filter((i) => i.id !== item.id))
      toast.success(`Deleted "${item.name}"`)
    } catch (err) {
      toast.error('Delete failed', errorMessage(err))
    }
  }

  if (!items.length) return <EmptyState icon={<FileCog size={22} />} title={emptyTitle} description={emptyText} />

  const trimmed = newName.trim()
  const renameError = !trimmed ? 'Enter a name.' : renaming && nameTaken(trimmed, renaming.id) ? `Another ${kind} already has this name.` : null

  return (
    <>
      <ul className="divide-y divide-line">
        {items.map((item) => {
          const d = describe(item)
          return (
            <li key={item.id} className="flex items-center gap-4 px-1 py-3">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="truncate text-[14px] font-semibold text-ink">{item.name}</span>
                  {d.badge}
                </div>
                <div className="mt-0.5 truncate text-[12.5px] text-muted">{d.detail}</div>
              </div>
              <div className="num w-[170px] text-right text-[12.5px] whitespace-nowrap text-muted">Updated {updatedLabel(item.updatedAt)}</div>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="icon" aria-label={`Actions for ${item.name}`}>
                    <MoreHorizontal size={17} />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent>
                  <DropdownMenuItem
                    icon={<Pencil size={14} />}
                    onSelect={() => {
                      setNewName(item.name)
                      setRenaming(item)
                    }}
                  >
                    Rename
                  </DropdownMenuItem>
                  <DropdownMenuItem icon={<Copy size={14} />} onSelect={() => void duplicate(item)}>
                    Duplicate
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem icon={<Trash2 size={14} />} tone="danger" onSelect={() => void remove(item)}>
                    Delete
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </li>
          )
        })}
      </ul>

      <Dialog open={!!renaming} onOpenChange={(open) => !open && setRenaming(null)}>
        <DialogContent width={440}>
          <form
            onSubmit={(e) => {
              e.preventDefault()
              if (!renameError) void rename()
            }}
          >
            <DialogHeader>
              <DialogTitle>Rename {kind}</DialogTitle>
              <DialogDescription>Choose a name you will recognise next month.</DialogDescription>
            </DialogHeader>
            <DialogBody>
              <Field label="Name" htmlFor="rename" error={trimmed ? renameError : null}>
                <Input id="rename" autoFocus maxLength={120} value={newName} onChange={(e) => setNewName(e.target.value)} />
              </Field>
            </DialogBody>
            <DialogFooter>
              <Button variant="secondary" onClick={() => setRenaming(null)}>
                Cancel
              </Button>
              <Button type="submit" loading={saving} disabled={!!renameError}>
                Save name
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </>
  )
}

function describeMapping(m: SavedMapping): { badge: React.ReactNode; detail: React.ReactNode } {
  const mod = getModule(m.moduleId)
  const keys = m.config.keys.filter((k) => k.use)
  return {
    badge: <Badge tone="info">{mod?.name ?? m.moduleId}</Badge>,
    detail: `${m.config.sideAName} (${m.headersA.length} columns) ↔ ${m.config.sideBName} (${m.headersB.length} columns) · ${keys.length} key${keys.length === 1 ? '' : 's'}: ${keys.map((k) => k.name).join(', ') || 'none'}`
  }
}

function describeRecipe(r: ToolRecipe): { badge: React.ReactNode; detail: React.ReactNode } {
  const tool = getTool(r.tool)
  return {
    badge: <Badge tone="teal">{tool?.name ?? r.tool}</Badge>,
    detail: `Saved options for ${tool?.name ?? r.tool} · created ${updatedLabel(r.createdAt)}`
  }
}

export function MappingsPage(): React.JSX.Element {
  const state = useAsync(async () => {
    const [mappings, templates, recipes] = await Promise.all([listMappings(), listTemplates(), listRecipes()])
    return { mappings, templates, recipes }
  })
  const data = state.data
  const [tab, setTab] = useState('mappings')

  if (state.loading && !data) {
    return (
      <Card className="grid h-64 place-items-center">
        <Spinner />
      </Card>
    )
  }
  if (state.error || !data) {
    return (
      <Card>
        <EmptyState title="Saved setups could not be loaded" description={state.error ?? undefined} action={<TechnicalDetails details={state.details} />} />
      </Card>
    )
  }

  const set = <K extends keyof typeof data>(key: K) => (items: (typeof data)[K]) => state.setData((d) => (d ? { ...d, [key]: items } : d))

  return (
    <Card className="px-6 pt-4 pb-3">
      <Tabs value={tab} onValueChange={setTab}>
        <TabsList>
          <TabsTrigger value="mappings" count={data.mappings.length}>
            Column mappings
          </TabsTrigger>
          <TabsTrigger value="templates" count={data.templates.length}>
            General templates
          </TabsTrigger>
          <TabsTrigger value="recipes" count={data.recipes.length}>
            Tool recipes
          </TabsTrigger>
        </TabsList>
        <TabsContent value="mappings">
          <SavedList
            kind="mapping"
            items={data.mappings}
            describe={describeMapping}
            onSave={saveMapping}
            onDelete={deleteMapping}
            onChange={set('mappings')}
            emptyTitle="No saved mappings yet"
            emptyText="After you map columns in Bank, AR or AP reconciliation, save the mapping. It loads automatically next time the same files come back."
          />
        </TabsContent>
        <TabsContent value="templates">
          <SavedList
            kind="template"
            items={data.templates}
            describe={describeMapping}
            onSave={saveTemplate}
            onDelete={deleteTemplate}
            onChange={set('templates')}
            emptyTitle="No General templates yet"
            emptyText={'In General Reconciliation, click "Save as template" on the Map & rules step to reuse your file names, keys and rules.'}
          />
        </TabsContent>
        <TabsContent value="recipes">
          <SavedList
            kind="recipe"
            items={data.recipes}
            describe={describeRecipe}
            onSave={saveRecipe}
            onDelete={deleteRecipe}
            onChange={set('recipes')}
            emptyTitle="No tool recipes yet"
            emptyText="PDF → Excel, Merge Files and Data Cleaner can save their options as a recipe for the next statement."
          />
        </TabsContent>
      </Tabs>
    </Card>
  )
}
