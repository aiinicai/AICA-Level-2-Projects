import { useRef, useState } from 'react'
import { BookMarked, ChevronDown, Save } from 'lucide-react'
import type { RecipeTool, ToolRecipe } from '@shared/contracts'
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
import { listRecipes, newId, saveRecipe } from '@/lib/db'
import { formatDate } from '@shared/format'
import { errorMessage, useAsync } from '@/lib/useAsync'
import { buildRecipe } from '../recipes'

/**
 * "Recipe ▾" picker and "Save settings as recipe". `current()` returns the options to store;
 * `onApply` receives a stored recipe's options (validate them before use).
 */
export function RecipeBar({
  tool,
  current,
  onApply,
  canSave
}: {
  tool: RecipeTool
  current: () => unknown
  onApply: (options: unknown, recipe: ToolRecipe) => void
  canSave: boolean
}): React.JSX.Element {
  const toast = useToast()
  const recipes = useAsync(() => listRecipes(tool), [tool])
  const [open, setOpen] = useState(false)
  const [name, setName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  // Enter in the name field and a click (or a repeated Enter) must not save the recipe twice.
  const inFlight = useRef(false)
  const save = async (): Promise<void> => {
    if (inFlight.current) return
    inFlight.current = true
    setSaving(true)
    setError(null)
    try {
      const recipe = buildRecipe(tool, name, current(), recipes.data ?? [], newId)
      await saveRecipe(recipe)
      await recipes.reload()
      setOpen(false)
      toast.success('Recipe saved', `"${recipe.name}" is listed under Workspace → Mappings & Templates.`)
    } catch (e) {
      setError(errorMessage(e))
    } finally {
      inFlight.current = false
      setSaving(false)
    }
  }

  const list = recipes.data ?? []
  return (
    <div className="mb-4 flex items-center gap-2">
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="secondary" size="sm" className="flex-1 justify-between" data-action="recipe-picker">
            <span className="inline-flex items-center gap-1.5">
              <BookMarked size={14} /> Recipe
            </span>
            <ChevronDown size={14} className="text-muted" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-[300px]">
          <DropdownMenuLabel>Apply saved settings</DropdownMenuLabel>
          {list.length === 0 && <div className="px-2.5 py-2 text-[12.5px] text-muted">No recipes yet. Set the options, then save them as a recipe.</div>}
          {list.map((r) => (
            <DropdownMenuItem key={r.id} hint={formatDate(new Date(r.updatedAt))} onSelect={() => onApply(r.options, r)}>
              {r.name}
            </DropdownMenuItem>
          ))}
          <DropdownMenuSeparator />
          <DropdownMenuItem
            icon={<Save size={14} />}
            disabled={!canSave}
            onSelect={() => {
              setName('')
              setError(null)
              setOpen(true)
            }}
          >
            Save settings as recipe…
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
      <Button
        variant="ghost"
        size="sm"
        disabled={!canSave}
        onClick={() => {
          setName('')
          setError(null)
          setOpen(true)
        }}
        data-action="save-recipe"
      >
        <Save size={14} /> Save as recipe
      </Button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent width={440}>
          <DialogHeader>
            <DialogTitle>Save settings as recipe</DialogTitle>
            <DialogDescription>Next month pick this recipe, drop the new file and download. A recipe with the same name is replaced.</DialogDescription>
          </DialogHeader>
          <DialogBody>
            <Field label="Recipe name" htmlFor="recipe-name" error={error}>
              <Input
                id="recipe-name"
                value={name}
                autoFocus
                placeholder="e.g. Al Safa bank statement"
                onChange={(e) => setName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key !== 'Enter' || e.repeat) return
                  e.preventDefault()
                  void save()
                }}
              />
            </Field>
          </DialogBody>
          <DialogFooter>
            <Button variant="secondary" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button onClick={() => void save()} loading={saving} disabled={!name.trim()}>
              Save recipe
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
