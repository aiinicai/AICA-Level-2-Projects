const AVATAR_COLORS = ['bg-bark', 'bg-moss', 'bg-rust', 'bg-gold-ink', 'bg-slate', 'bg-amber']

function hashToIndex(id: string, mod: number) {
  let hash = 0
  for (let i = 0; i < id.length; i++) {
    hash = (hash << 5) - hash + id.charCodeAt(i)
    hash |= 0
  }
  return Math.abs(hash) % mod
}

function initials(name: string) {
  const parts = name.trim().split(/\s+/).filter(Boolean)
  if (parts.length === 0) return '?'
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
}

export function PersonChip({ id, name }: { id: string; name: string }) {
  const color = AVATAR_COLORS[hashToIndex(id, AVATAR_COLORS.length)]
  return (
    <span className="flex w-full min-w-0 items-center gap-1.5">
      <span
        className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full ${color} text-[9px] font-semibold text-white`}
      >
        {initials(name)}
      </span>
      <span className="min-w-0 flex-1 truncate text-ink-soft">{name}</span>
    </span>
  )
}
