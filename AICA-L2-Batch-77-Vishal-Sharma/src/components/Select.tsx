import * as RadixSelect from '@radix-ui/react-select'

export interface SelectOption {
  value: string
  label: string
}

/** A themed, accessible replacement for the native <select> — same data
 * shape, but a proper styled popover with hover/selected states instead of
 * the browser's plain OS dropdown. */
export function Select({
  value,
  onValueChange,
  options,
  placeholder,
  className = '',
}: {
  value: string
  onValueChange: (value: string) => void
  options: SelectOption[]
  placeholder: string
  className?: string
}) {
  return (
    <RadixSelect.Root value={value || undefined} onValueChange={onValueChange}>
      <RadixSelect.Trigger
        className={`w-full inline-flex items-center justify-between gap-2 rounded-md border border-line bg-paper px-3 py-2 text-sm text-ink hover:border-bark/50 focus:outline-none focus:border-bark focus:ring-2 focus:ring-bark/15 data-[placeholder]:text-ink-soft transition-colors ${className}`}
      >
        <RadixSelect.Value placeholder={placeholder} />
        <RadixSelect.Icon>
          <ChevronIcon />
        </RadixSelect.Icon>
      </RadixSelect.Trigger>
      <RadixSelect.Portal>
        <RadixSelect.Content
          position="popper"
          sideOffset={4}
          className="z-50 max-h-72 overflow-hidden rounded-md border border-line bg-paper-raised shadow-lg"
        >
          <RadixSelect.ScrollUpButton className="flex items-center justify-center py-1 text-ink-soft">
            <ChevronIcon direction="up" />
          </RadixSelect.ScrollUpButton>
          <RadixSelect.Viewport className="p-1 max-h-64 overflow-y-auto">
            {options.map((opt) => (
              <RadixSelect.Item
                key={opt.value}
                value={opt.value}
                className="relative flex items-center rounded-sm px-3 py-2 text-sm text-ink cursor-pointer select-none outline-none data-[highlighted]:bg-gold-bg data-[highlighted]:text-gold-ink data-[state=checked]:font-semibold"
              >
                <RadixSelect.ItemText>{opt.label}</RadixSelect.ItemText>
              </RadixSelect.Item>
            ))}
          </RadixSelect.Viewport>
          <RadixSelect.ScrollDownButton className="flex items-center justify-center py-1 text-ink-soft">
            <ChevronIcon direction="down" />
          </RadixSelect.ScrollDownButton>
        </RadixSelect.Content>
      </RadixSelect.Portal>
    </RadixSelect.Root>
  )
}

function ChevronIcon({ direction = 'down' }: { direction?: 'up' | 'down' }) {
  return (
    <svg
      width="12"
      height="12"
      viewBox="0 0 12 12"
      fill="none"
      className="text-ink-soft shrink-0"
      style={{ transform: direction === 'up' ? 'rotate(180deg)' : undefined }}
    >
      <path d="M2.5 4.5L6 8L9.5 4.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}
