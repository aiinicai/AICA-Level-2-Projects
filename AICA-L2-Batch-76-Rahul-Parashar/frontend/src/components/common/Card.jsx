export default function Card({ title, subtitle, action, children, className = '' }) {
  return (
    <div className={`bg-paper rounded-lg border border-line p-4 sm:p-5 ${className}`}>
      {(title || action) && (
        <div className="flex items-start justify-between mb-3">
          <div>
            {title && <h3 className="font-heading text-sm font-semibold text-ink">{title}</h3>}
            {subtitle && <p className="text-xs text-slate font-body mt-0.5">{subtitle}</p>}
          </div>
          {action}
        </div>
      )}
      {children}
    </div>
  );
}
