import * as DropdownMenu from '@radix-ui/react-dropdown-menu'
import type { TaskStatus } from '../types/database'
import { StatusBadge } from './Badges'

const NON_TERMINAL_STATUSES: TaskStatus[] = ['Open', 'In Process', 'Pending at Client', 'Pending at Department', 'Hold']

/** The status badge, but interactive — lets a task's assignee (or Admin)
 * change status from anywhere it's used (task list, task detail) without
 * having to open the task first. Closing still gets a confirmation, since
 * it locks the record. */
export function StatusMenu({
  status,
  onChange,
}: {
  status: TaskStatus
  onChange: (next: TaskStatus) => void
}) {
  const handleSelect = (next: TaskStatus) => {
    if (next === status) return
    if (next === 'Closed') {
      if (confirm('Close this task? It cannot be reversed except by an Admin.')) onChange(next)
      return
    }
    onChange(next)
  }

  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>
        <button className="cursor-pointer rounded-full focus:outline-none focus-visible:ring-2 focus-visible:ring-bark/40">
          <StatusBadge status={status} />
        </button>
      </DropdownMenu.Trigger>
      <DropdownMenu.Portal>
        <DropdownMenu.Content
          align="end"
          sideOffset={4}
          collisionPadding={8}
          className="z-50 min-w-44 overflow-hidden rounded-md border border-line bg-paper-raised shadow-lg p-1"
        >
          {NON_TERMINAL_STATUSES.map((s) => (
            <DropdownMenu.Item
              key={s}
              onSelect={() => handleSelect(s)}
              className={`flex items-center justify-between rounded-sm px-3 py-2 text-sm cursor-pointer select-none outline-none data-[highlighted]:bg-gold-bg data-[highlighted]:text-gold-ink ${
                s === status ? 'font-semibold text-ink' : 'text-ink'
              }`}
            >
              {s}
              {s === status && <CheckIcon />}
            </DropdownMenu.Item>
          ))}
          <DropdownMenu.Separator className="my-1 h-px bg-line" />
          <DropdownMenu.Item
            onSelect={() => handleSelect('Closed')}
            className="flex items-center justify-between rounded-sm px-3 py-2 text-sm cursor-pointer select-none outline-none text-moss data-[highlighted]:bg-moss-bg"
          >
            Closed
          </DropdownMenu.Item>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  )
}

function CheckIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
      <path d="M2 6.5L4.5 9L10 3" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}
