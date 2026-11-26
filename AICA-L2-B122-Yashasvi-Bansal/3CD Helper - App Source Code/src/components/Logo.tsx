export function LogoMark({ className = "h-8 w-8" }: { className?: string }) {
  return (
    <svg viewBox="0 0 64 64" className={className} aria-hidden="true">
      <rect width="64" height="64" rx="14" fill="#0b1f44" />
      <path d="M18 16h20l8 8v24a2 2 0 0 1-2 2H18a2 2 0 0 1-2-2V18a2 2 0 0 1 2-2z" fill="#fff" />
      <path d="M38 16v8h8" fill="#d9e3f5" />
      <rect x="21" y="29" width="18" height="3" rx="1.5" fill="#365aae" />
      <rect x="21" y="35" width="13" height="3" rx="1.5" fill="#365aae" />
      <circle cx="44" cy="44" r="9" fill="#f2c14e" />
      <path d="M40 44l3 3 5-6" stroke="#0b1f44" strokeWidth="2.6" fill="none" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function Logo({ dark = false }: { dark?: boolean }) {
  return (
    <div className="flex items-center gap-2.5">
      <LogoMark />
      <div className="leading-tight">
        <div className={`text-base font-extrabold tracking-tight ${dark ? "text-white" : "text-navy-950"}`}>3CD Helper</div>
        <div className={`text-[10px] font-medium uppercase tracking-widest ${dark ? "text-navy-200" : "text-slate-500"}`}>Tax Audit Assistant</div>
      </div>
    </div>
  );
}
