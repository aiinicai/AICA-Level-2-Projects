/** A small branded spinner, used in place of bare "Loading…" text
 * throughout the app so a fetch-in-progress reads as considered rather
 * than an unstyled placeholder. */
export function Loading({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="flex items-center gap-2.5 text-ink-soft py-2">
      <svg className="animate-spin h-4 w-4 text-bark" viewBox="0 0 24 24" fill="none">
        <circle className="opacity-20" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
        <path d="M22 12a10 10 0 0 0-10-10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
      </svg>
      <span className="text-sm">{label}</span>
    </div>
  )
}
