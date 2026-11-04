// Vouchr illustration set — one geometry (rounded 1.6px strokes, 4px radii), currentColor + brand
// accent, light from top-left. Product-relevant only: bills, ledgers, trays. No stock imagery.

/** A paper bill with GST lines and a verified tick — staff hero. */
export function ReceiptArt() {
  return (
    <svg className="receipt" viewBox="0 0 112 136" aria-hidden="true">
      <defs>
        <linearGradient id="rcpt" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#ffffff" />
          <stop offset="1" stopColor="#eef2f7" />
        </linearGradient>
      </defs>
      <path d="M8 6h96v118l-8-6-8 6-8-6-8 6-8-6-8 6-8-6-8 6-8-6-8 6-8-6z" fill="url(#rcpt)" />
      <rect x="18" y="18" width="46" height="7" rx="3.5" fill="#0f2a44" opacity=".85" />
      <rect x="18" y="31" width="30" height="5" rx="2.5" fill="#94a3b8" />
      {[48, 60, 72].map((y) => (
        <g key={y}>
          <rect x="18" y={y} width="40" height="5" rx="2.5" fill="#cbd5e1" />
          <rect x="72" y={y} width="22" height="5" rx="2.5" fill="#cbd5e1" />
        </g>
      ))}
      <path d="M18 86h76" stroke="#94a3b8" strokeDasharray="3 3" />
      <rect x="18" y="94" width="26" height="7" rx="3.5" fill="#0f2a44" opacity=".85" />
      <rect x="62" y="93" width="32" height="9" rx="4.5" fill="#0f2a44" />
      <circle cx="88" cy="24" r="11" fill="#0e9f6e" />
      <path d="M83 24l3.5 3.5L93 21" fill="none" stroke="#fff" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

const S = { fill: 'none', stroke: 'currentColor', strokeWidth: 1.6, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const };

/** Empty-state illustrations. */
export function EmptyArt({ kind = 'doc' }: { kind?: 'doc' | 'tray' | 'done' | 'search' }) {
  return (
    <svg className="empty-art" viewBox="0 0 96 72" aria-hidden="true">
      <ellipse cx="48" cy="64" rx="34" ry="4" fill="currentColor" opacity=".08" />
      {kind === 'tray' && (
        <g {...S}>
          <path d="M18 38l8-20h44l8 20v16a4 4 0 0 1-4 4H22a4 4 0 0 1-4-4z" />
          <path d="M18 38h17l4 7h18l4-7h17" />
          <path d="M40 10v14M34 18l6 6 6-6" opacity=".7" />
        </g>
      )}
      {kind === 'done' && (
        <g {...S}>
          <circle cx="48" cy="32" r="22" />
          <path d="M38 32l7 7 13-14" strokeWidth="2.2" />
          <path d="M20 12l3 3M76 12l-3 3M48 4v4" opacity=".6" />
        </g>
      )}
      {kind === 'search' && (
        <g {...S}>
          <rect x="22" y="10" width="38" height="46" rx="5" />
          <path d="M30 22h20M30 30h14M30 38h18" opacity=".7" />
          <circle cx="62" cy="44" r="10" />
          <path d="M69 51l7 7" strokeWidth="2.2" />
        </g>
      )}
      {kind === 'doc' && (
        <g {...S}>
          <path d="M28 8h28l12 12v34a4 4 0 0 1-4 4H28a4 4 0 0 1-4-4V12a4 4 0 0 1 4-4z" />
          <path d="M56 8v12h12" />
          <path d="M32 30h24M32 38h24M32 46h14" opacity=".7" />
        </g>
      )}
    </svg>
  );
}
