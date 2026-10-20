import { Select as SelectPrimitive } from 'radix-ui'
import { Check, ChevronDown } from 'lucide-react'
import { cn } from '@/lib/cn'

export interface SelectOption {
  value: string
  label: React.ReactNode
  disabled?: boolean
}

export interface SelectProps {
  value?: string
  defaultValue?: string
  onValueChange?: (value: string) => void
  options: SelectOption[]
  placeholder?: string
  disabled?: boolean
  id?: string
  className?: string
  size?: 'sm' | 'md'
  'aria-label'?: string
  'aria-invalid'?: boolean
}

/** A styled single-choice dropdown. (Radix does not allow an empty-string value; use a sentinel such as "__none".) */
export function Select({
  value,
  defaultValue,
  onValueChange,
  options,
  placeholder = 'Choose…',
  disabled,
  id,
  className,
  size = 'md',
  ...aria
}: SelectProps): React.JSX.Element {
  return (
    <SelectPrimitive.Root value={value} defaultValue={defaultValue} onValueChange={onValueChange} disabled={disabled}>
      <SelectPrimitive.Trigger
        id={id}
        aria-label={aria['aria-label']}
        aria-invalid={aria['aria-invalid']}
        className={cn(
          'flex w-full items-center justify-between gap-2 rounded-lg border border-[#D5DCE5] bg-white px-3 text-left text-ink outline-none transition-colors hover:border-[#C2CBD7] focus-visible:border-primary focus-visible:ring-2 focus-visible:ring-primary/15 disabled:cursor-not-allowed disabled:bg-[#F4F6F9] disabled:text-muted aria-invalid:border-unmatched data-[placeholder]:text-[#9AA4B2]',
          size === 'sm' ? 'h-8 text-[12.5px]' : 'h-9 text-[13.5px]',
          className
        )}
      >
        <span className="truncate">
          <SelectPrimitive.Value placeholder={placeholder} />
        </span>
        <SelectPrimitive.Icon>
          <ChevronDown size={15} className="text-muted" />
        </SelectPrimitive.Icon>
      </SelectPrimitive.Trigger>
      <SelectPrimitive.Portal>
        <SelectPrimitive.Content
          position="popper"
          sideOffset={4}
          className="z-50 max-h-[min(var(--radix-select-content-available-height),340px)] min-w-[var(--radix-select-trigger-width)] overflow-hidden rounded-lg border border-line bg-white shadow-lg"
        >
          <SelectPrimitive.Viewport className="p-1">
            {options.map((o) => (
              <SelectPrimitive.Item
                key={o.value}
                value={o.value}
                disabled={o.disabled}
                className="relative flex cursor-default items-center rounded-md py-1.5 pr-3 pl-7 text-[13px] text-ink outline-none select-none data-[disabled]:opacity-40 data-[highlighted]:bg-[#EEF4FD] data-[highlighted]:text-primary"
              >
                <SelectPrimitive.ItemIndicator className="absolute left-2 inline-flex">
                  <Check size={14} />
                </SelectPrimitive.ItemIndicator>
                <SelectPrimitive.ItemText>{o.label}</SelectPrimitive.ItemText>
              </SelectPrimitive.Item>
            ))}
          </SelectPrimitive.Viewport>
        </SelectPrimitive.Content>
      </SelectPrimitive.Portal>
    </SelectPrimitive.Root>
  )
}
