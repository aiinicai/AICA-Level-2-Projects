import { useState } from 'react'
import { Check, ChevronsUpDown } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { cn } from '@/lib/utils'

/*
  Kept out of common.tsx on purpose: cmdk is heavy, and the login page has no
  business downloading it.
*/

export interface ComboOption {
  value: string
  label: string
  hint?: string
  group?: string
}

/**
 * Searchable single-select. Used for client, assignee and master-task pickers,
 * any of which can run to hundreds of rows where a plain <Select> is unusable.
 */
export function Combobox({
  options,
  value,
  onChange,
  placeholder = 'Select…',
  searchPlaceholder = 'Search…',
  emptyText = 'No match found.',
  allowClear = false,
  clearLabel = 'None',
  disabled = false,
  className,
}: {
  options: ComboOption[]
  value: string | null
  onChange: (value: string | null) => void
  placeholder?: string
  searchPlaceholder?: string
  emptyText?: string
  allowClear?: boolean
  clearLabel?: string
  disabled?: boolean
  className?: string
}) {
  const [open, setOpen] = useState(false)
  const selected = options.find((o) => o.value === value)

  const groups = options.reduce<Record<string, ComboOption[]>>((acc, option) => {
    const key = option.group ?? ''
    ;(acc[key] ??= []).push(option)
    return acc
  }, {})

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          type="button"
          variant="outline"
          role="combobox"
          aria-expanded={open}
          disabled={disabled}
          className={cn(
            'w-full justify-between font-normal',
            !selected && 'text-muted-foreground',
            className,
          )}
        >
          <span className="truncate">{selected?.label ?? placeholder}</span>
          <ChevronsUpDown className="ml-2 size-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-(--radix-popover-trigger-width) p-0" align="start">
        <Command>
          <CommandInput placeholder={searchPlaceholder} />
          <CommandList>
            <CommandEmpty>{emptyText}</CommandEmpty>
            {allowClear ? (
              <CommandGroup>
                <CommandItem
                  value="__clear__"
                  onSelect={() => {
                    onChange(null)
                    setOpen(false)
                  }}
                >
                  <Check className={cn('mr-2 size-4', value ? 'opacity-0' : 'opacity-100')} />
                  <span className="text-muted-foreground">{clearLabel}</span>
                </CommandItem>
              </CommandGroup>
            ) : null}
            {Object.entries(groups).map(([group, items]) => (
              <CommandGroup key={group || 'ungrouped'} heading={group || undefined}>
                {items.map((option) => (
                  <CommandItem
                    key={option.value}
                    value={`${option.label} ${option.hint ?? ''}`}
                    onSelect={() => {
                      onChange(option.value)
                      setOpen(false)
                    }}
                  >
                    <Check
                      className={cn(
                        'mr-2 size-4 shrink-0',
                        value === option.value ? 'opacity-100' : 'opacity-0',
                      )}
                    />
                    <span className="truncate">{option.label}</span>
                    {option.hint ? (
                      <span className="text-muted-foreground ml-auto pl-2 text-xs whitespace-nowrap">
                        {option.hint}
                      </span>
                    ) : null}
                  </CommandItem>
                ))}
              </CommandGroup>
            ))}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  )
}

/**
 * Combobox that also accepts a value that is not in the list — used for the
 * task-master category, where the 9 seeded categories are offered but a firm
 * can invent its own (say "FEMA") without a schema change.
 */
export function CreatableCombobox({
  options,
  value,
  onChange,
  placeholder = 'Select or type…',
  createLabel = 'Use',
  className,
}: {
  options: string[]
  value: string
  onChange: (value: string) => void
  placeholder?: string
  createLabel?: string
  className?: string
}) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const trimmed = query.trim()
  const isNew = trimmed.length > 0 && !options.some((o) => o.toLowerCase() === trimmed.toLowerCase())

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          type="button"
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className={cn(
            'w-full justify-between font-normal',
            !value && 'text-muted-foreground',
            className,
          )}
        >
          <span className="truncate">{value || placeholder}</span>
          <ChevronsUpDown className="ml-2 size-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-(--radix-popover-trigger-width) p-0" align="start">
        <Command>
          <CommandInput
            placeholder="Search or type a new one…"
            value={query}
            onValueChange={setQuery}
          />
          <CommandList>
            {!isNew ? <CommandEmpty>No match found.</CommandEmpty> : null}
            {isNew ? (
              <CommandGroup>
                <CommandItem
                  value={`__create__${trimmed}`}
                  onSelect={() => {
                    onChange(trimmed)
                    setQuery('')
                    setOpen(false)
                  }}
                >
                  <Check className="mr-2 size-4 opacity-0" />
                  {createLabel} “{trimmed}”
                </CommandItem>
              </CommandGroup>
            ) : null}
            <CommandGroup heading="Existing categories">
              {options.map((option) => (
                <CommandItem
                  key={option}
                  value={option}
                  onSelect={() => {
                    onChange(option)
                    setQuery('')
                    setOpen(false)
                  }}
                >
                  <Check
                    className={cn('mr-2 size-4', value === option ? 'opacity-100' : 'opacity-0')}
                  />
                  {option}
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  )
}
