import { DropdownMenu as MenuPrimitive } from 'radix-ui'
import { Check } from 'lucide-react'
import { cn } from '@/lib/cn'

export const DropdownMenu = MenuPrimitive.Root
export const DropdownMenuTrigger = MenuPrimitive.Trigger
export const DropdownMenuGroup = MenuPrimitive.Group

export function DropdownMenuContent({
  className,
  sideOffset = 6,
  align = 'end',
  ...props
}: React.ComponentProps<typeof MenuPrimitive.Content>): React.JSX.Element {
  return (
    <MenuPrimitive.Portal>
      <MenuPrimitive.Content
        sideOffset={sideOffset}
        align={align}
        collisionPadding={8}
        className={cn(
          'z-50 max-h-[var(--radix-dropdown-menu-content-available-height)] min-w-[200px] overflow-y-auto rounded-lg border border-line bg-white p-1 shadow-lg data-[state=open]:animate-[fade-in_100ms_ease-out]',
          className
        )}
        {...props}
      />
    </MenuPrimitive.Portal>
  )
}

export interface DropdownMenuItemProps extends React.ComponentProps<typeof MenuPrimitive.Item> {
  icon?: React.ReactNode
  tone?: 'default' | 'danger'
  /** Small text on the right, e.g. a date or shortcut. */
  hint?: React.ReactNode
}

export function DropdownMenuItem({ className, icon, tone = 'default', hint, children, ...props }: DropdownMenuItemProps): React.JSX.Element {
  return (
    <MenuPrimitive.Item
      className={cn(
        'flex cursor-default items-center gap-2 rounded-md px-2.5 py-1.5 text-[13px] outline-none select-none data-[disabled]:opacity-40',
        tone === 'danger' ? 'text-unmatched data-[highlighted]:bg-[#FDECEC]' : 'text-ink data-[highlighted]:bg-[#EEF4FD] data-[highlighted]:text-primary',
        className
      )}
      {...props}
    >
      {icon && <span className="inline-flex w-4 justify-center opacity-80">{icon}</span>}
      <span className="flex-1">{children}</span>
      {hint && <span className="text-[11.5px] text-muted">{hint}</span>}
    </MenuPrimitive.Item>
  )
}

export function DropdownMenuCheckboxItem({
  className,
  children,
  ...props
}: React.ComponentProps<typeof MenuPrimitive.CheckboxItem>): React.JSX.Element {
  return (
    <MenuPrimitive.CheckboxItem
      className={cn(
        'relative flex cursor-default items-center rounded-md py-1.5 pr-2.5 pl-8 text-[13px] text-ink outline-none select-none data-[disabled]:opacity-40 data-[highlighted]:bg-[#EEF4FD]',
        className
      )}
      {...props}
    >
      <MenuPrimitive.ItemIndicator className="absolute left-2.5 inline-flex">
        <Check size={14} />
      </MenuPrimitive.ItemIndicator>
      {children}
    </MenuPrimitive.CheckboxItem>
  )
}

export function DropdownMenuLabel({ className, ...props }: React.ComponentProps<typeof MenuPrimitive.Label>): React.JSX.Element {
  return <MenuPrimitive.Label className={cn('px-2.5 pt-2 pb-1 text-[11px] font-bold tracking-[1px] text-muted uppercase', className)} {...props} />
}

export function DropdownMenuSeparator({ className, ...props }: React.ComponentProps<typeof MenuPrimitive.Separator>): React.JSX.Element {
  return <MenuPrimitive.Separator className={cn('my-1 h-px bg-line', className)} {...props} />
}
