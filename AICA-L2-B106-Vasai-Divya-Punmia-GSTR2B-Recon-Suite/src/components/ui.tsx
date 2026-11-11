import { useEffect, useState, type ReactNode } from 'react';
import { AlertTriangle, CheckCircle2, Download, Info, Search, X, XCircle } from 'lucide-react';
import { useDevice } from '../device';

export const cx = (...c: (string | false | null | undefined)[]) => c.filter(Boolean).join(' ');

/* --------------------------------- Layout ---------------------------------- */

export function Card({ title, right, children, className, pad = true }: { title?: ReactNode; right?: ReactNode; children: ReactNode; className?: string; pad?: boolean }) {
  return (
    <section className={cx('bg-white border border-slate-200 rounded-lg shadow-sm overflow-hidden', className)}>
      {(title || right) && (
        <div className="flex flex-wrap items-center justify-between gap-2 px-3 py-2 border-b border-slate-200 bg-slate-50">
          <h3 className="text-xs font-semibold text-slate-700">{title}</h3>
          {right}
        </div>
      )}
      <div className={pad ? 'p-3' : ''}>{children}</div>
    </section>
  );
}

export function PageHead({ title, sub, right }: { title: string; sub?: ReactNode; right?: ReactNode }) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-2 mb-3">
      <div className="min-w-0">
        <h2 className="text-base sm:text-lg font-bold text-slate-800">{title}</h2>
        {sub && <p className="text-xs text-slate-500 mt-0.5 max-w-3xl">{sub}</p>}
      </div>
      {right && <div className="flex flex-wrap gap-2 shrink-0">{right}</div>}
    </div>
  );
}

const TONES = {
  teal: 'border-t-teal-600',
  green: 'border-t-emerald-600',
  amber: 'border-t-amber-500',
  orange: 'border-t-orange-500',
  red: 'border-t-red-600',
  violet: 'border-t-violet-600',
  sky: 'border-t-sky-600',
  slate: 'border-t-slate-500',
} as const;

export function Stat({ label, value, sub, tone = 'slate', onClick, active }: { label: string; value: ReactNode; sub?: ReactNode; tone?: keyof typeof TONES; onClick?: () => void; active?: boolean }) {
  const C = onClick ? 'button' : 'div';
  return (
    <C
      onClick={onClick}
      className={cx(
        'text-left bg-white border border-slate-200 border-t-[3px] rounded-lg p-3 shadow-sm min-w-0',
        TONES[tone],
        onClick && 'hover:border-slate-300 cursor-pointer',
        active && 'ring-2 ring-teal-500'
      )}
    >
      <p className="text-[0.65rem] uppercase tracking-wide font-semibold text-slate-500 truncate">{label}</p>
      <p className="text-xl font-bold text-slate-800 nums mt-0.5 truncate">{value}</p>
      {sub && <p className="text-[0.7rem] text-slate-500 mt-0.5 truncate">{sub}</p>}
    </C>
  );
}

export function Grid({ children, cols = 4 }: { children: ReactNode; cols?: 2 | 3 | 4 | 5 | 6 }) {
  const c = { 2: 'sm:grid-cols-2', 3: 'sm:grid-cols-3', 4: 'sm:grid-cols-2 lg:grid-cols-4', 5: 'sm:grid-cols-3 lg:grid-cols-5', 6: 'sm:grid-cols-3 xl:grid-cols-6' }[cols];
  return <div className={cx('grid grid-cols-2 gap-2 sm:gap-3', c)}>{children}</div>;
}

/* --------------------------------- Controls -------------------------------- */

type BtnKind = 'primary' | 'secondary' | 'danger' | 'ghost' | 'dark';
const BTN: Record<BtnKind, string> = {
  primary: 'bg-teal-600 hover:bg-teal-700 text-white border-teal-700',
  secondary: 'bg-white hover:bg-slate-50 text-slate-700 border-slate-300',
  danger: 'bg-red-600 hover:bg-red-700 text-white border-red-700',
  ghost: 'bg-transparent hover:bg-slate-100 text-slate-600 border-transparent',
  dark: 'bg-slate-800 hover:bg-slate-700 text-white border-slate-900',
};

export function Btn({ kind = 'secondary', icon, children, className, small, ...rest }: React.ButtonHTMLAttributes<HTMLButtonElement> & { kind?: BtnKind; icon?: ReactNode; small?: boolean }) {
  return (
    <button
      type="button"
      {...rest}
      className={cx(
        'inline-flex items-center justify-center gap-1.5 rounded-md border font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer',
        small ? 'text-[0.7rem] px-2 py-1' : 'text-xs px-3 py-2',
        BTN[kind],
        className
      )}
    >
      {icon}
      {children}
    </button>
  );
}

export function ExportBtn({ onClick, label = 'Excel' }: { onClick: () => void; label?: string }) {
  return (
    <Btn icon={<Download className="w-3.5 h-3.5" />} onClick={onClick} title="Download this view as an Excel file">
      {label}
    </Btn>
  );
}

export function Pills<T extends string>({ value, onChange, options }: { value: T; onChange: (v: T) => void; options: { id: T; label: ReactNode; count?: number }[] }) {
  return (
    <div className="flex gap-1.5 overflow-x-auto scrollbar-none -mx-1 px-1 pb-1">
      {options.map((o) => (
        <button
          key={o.id}
          type="button"
          onClick={() => onChange(o.id)}
          className={cx(
            'shrink-0 px-2.5 py-1.5 rounded-md border text-[0.72rem] font-medium whitespace-nowrap cursor-pointer',
            value === o.id ? 'bg-teal-600 text-white border-teal-600' : 'bg-white text-slate-600 border-slate-300 hover:border-teal-400'
          )}
        >
          {o.label}
          {o.count !== undefined && <span className={cx('ml-1.5 nums', value === o.id ? 'text-teal-100' : 'text-slate-400')}>{o.count}</span>}
        </button>
      ))}
    </div>
  );
}

export function SearchBox({ value, onChange, placeholder = 'Search GSTIN, name or invoice no.' }: { value: string; onChange: (v: string) => void; placeholder?: string }) {
  return (
    <label className="relative block w-full sm:w-72">
      <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full pl-8 pr-7 py-2 text-xs border border-slate-300 rounded-md bg-white focus:outline-none focus:ring-2 focus:ring-teal-500"
      />
      {value && (
        <button type="button" onClick={() => onChange('')} className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600" aria-label="Clear search">
          <X className="w-3.5 h-3.5" />
        </button>
      )}
    </label>
  );
}

export function Field({ label, children, hint }: { label: string; children: ReactNode; hint?: string }) {
  return (
    <label className="block">
      <span className="block text-[0.7rem] font-semibold text-slate-600 mb-1">{label}</span>
      {children}
      {hint && <span className="block text-[0.65rem] text-slate-400 mt-0.5">{hint}</span>}
    </label>
  );
}

export const inputCls = 'w-full px-2.5 py-2 text-sm sm:text-xs border border-slate-300 rounded-md bg-white focus:outline-none focus:ring-2 focus:ring-teal-500 disabled:bg-slate-100';

/* --------------------------------- Badges ---------------------------------- */

const BADGE = {
  green: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  teal: 'bg-teal-50 text-teal-700 border-teal-200',
  amber: 'bg-amber-50 text-amber-800 border-amber-200',
  orange: 'bg-orange-50 text-orange-700 border-orange-200',
  red: 'bg-red-50 text-red-700 border-red-200',
  violet: 'bg-violet-50 text-violet-700 border-violet-200',
  sky: 'bg-sky-50 text-sky-700 border-sky-200',
  slate: 'bg-slate-100 text-slate-600 border-slate-200',
} as const;
export type BadgeTone = keyof typeof BADGE;

export function Badge({ tone = 'slate', children, title }: { tone?: BadgeTone; children: ReactNode; title?: string }) {
  return (
    <span title={title} className={cx('inline-flex items-center px-1.5 py-0.5 rounded border text-[0.65rem] font-semibold whitespace-nowrap', BADGE[tone])}>
      {children}
    </span>
  );
}

export function Notice({ tone = 'info', children }: { tone?: 'info' | 'warn' | 'danger' | 'ok'; children: ReactNode }) {
  const s = {
    info: ['bg-sky-50 border-sky-200 text-sky-900', <Info key="i" className="w-4 h-4 text-sky-600 shrink-0 mt-0.5" />],
    warn: ['bg-amber-50 border-amber-200 text-amber-900', <AlertTriangle key="i" className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />],
    danger: ['bg-red-50 border-red-200 text-red-900', <XCircle key="i" className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />],
    ok: ['bg-emerald-50 border-emerald-200 text-emerald-900', <CheckCircle2 key="i" className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />],
  }[tone];
  return <div className={cx('flex gap-2 border rounded-lg p-3 text-xs leading-relaxed', s[0] as string)}>{s[1]}<div className="min-w-0">{children}</div></div>;
}

export function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="text-center py-10 px-4">
      <p className="font-semibold text-slate-600 text-sm">{title}</p>
      {children && <p className="text-xs text-slate-400 mt-1 max-w-md mx-auto">{children}</p>}
    </div>
  );
}

/* --------------------------------- Table ----------------------------------- */

export interface Col<T> {
  h: ReactNode;
  cell: (r: T, i: number) => ReactNode;
  num?: boolean;
  wrap?: boolean;
  foot?: ReactNode;
  /** Phone card view: 'head' = top line of the card, 'actions' = buttons row. Default: first column is the head, untitled columns are actions. */
  card?: 'head' | 'actions';
}

const PAGE = 300;
const CARD_PAGE = 60;

/**
 * Table that scrolls inside its card and renders large registers in pages.
 * On phones it shows each row as a card (label : value) instead of a wide table.
 */
export function DataTable<T>({ cols, rows, empty = 'No records.', maxH = '65vh', rowClass, onRowDoubleClick }: { cols: Col<T>[]; rows: T[]; empty?: ReactNode; maxH?: string; rowClass?: (r: T) => string | undefined; onRowDoubleClick?: (r: T) => void }) {
  const cards = useDevice().type === 'phone';
  const page = cards ? CARD_PAGE : PAGE;
  const [limit, setLimit] = useState(page);
  useEffect(() => setLimit(page), [rows, page]);
  const hasFoot = cols.some((c) => c.foot !== undefined);

  if (cards) {
    const role = (c: Col<T>, i: number) => c.card ?? (i === 0 ? 'head' : c.h === '' || c.h === 'Actions' ? 'actions' : 'field');
    const head = cols.filter((c, i) => role(c, i) === 'head');
    const fields = cols.filter((c, i) => role(c, i) === 'field');
    const actions = cols.filter((c, i) => role(c, i) === 'actions');
    return (
      <div>
        <div className="card-list bg-slate-50">
          {rows.slice(0, limit).map((r, ri) => (
            <div key={ri} className={cx('card-row', rowClass?.(r))} onDoubleClick={onRowDoubleClick ? () => onRowDoubleClick(r) : undefined}>
              <div className="card-head">
                {head.map((c, i) => (
                  <span key={i}>{c.cell(r, ri)}</span>
                ))}
              </div>
              <dl>
                {fields.map((c, i) => (
                  <div key={i} className="contents">
                    <dt>{c.h}</dt>
                    <dd className={c.num ? 'num' : undefined}>{c.cell(r, ri)}</dd>
                  </div>
                ))}
              </dl>
              {actions.length > 0 && (
                <div className="card-actions">
                  {actions.map((c, i) => (
                    <span key={i}>{c.cell(r, ri)}</span>
                  ))}
                </div>
              )}
            </div>
          ))}
          {rows.length === 0 && <p className="text-center text-slate-400 text-sm py-8">{empty}</p>}
          {hasFoot && rows.length > 0 && (
            <div className="card-row card-total">
              <dl>
                {cols
                  .filter((c) => c.foot !== undefined && c.foot !== 'Total')
                  .map((c, i) => (
                    <div key={i} className="contents">
                      <dt>Total {c.h}</dt>
                      <dd className={c.num ? 'num' : undefined}>{c.foot}</dd>
                    </div>
                  ))}
              </dl>
            </div>
          )}
        </div>
        {rows.length > limit && (
          <div className="flex flex-col items-center gap-2 px-3 py-3 text-[0.75rem] text-slate-500">
            <span>
              Showing {limit.toLocaleString('en-IN')} of {rows.length.toLocaleString('en-IN')} (Excel export includes all)
            </span>
            <Btn onClick={() => setLimit((l) => l + CARD_PAGE * 2)}>Show more</Btn>
          </div>
        )}
      </div>
    );
  }

  return (
    <div>
      <div className="tbl-wrap" style={{ maxHeight: maxH }}>
        <table className="tbl">
          <thead>
            <tr>
              {cols.map((c, i) => (
                <th key={i} className={c.num ? 'num' : undefined}>
                  {c.h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.slice(0, limit).map((r, ri) => (
              <tr key={ri} className={rowClass?.(r)} onDoubleClick={onRowDoubleClick ? () => onRowDoubleClick(r) : undefined}>
                {cols.map((c, ci) => (
                  <td key={ci} className={cx(c.num && 'num', c.wrap && 'wrap')}>
                    {c.cell(r, ri)}
                  </td>
                ))}
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={cols.length} className="text-center text-slate-400 py-8 whitespace-normal">
                  {empty}
                </td>
              </tr>
            )}
          </tbody>
          {hasFoot && rows.length > 0 && (
            <tfoot>
              <tr>
                {cols.map((c, i) => (
                  <td key={i} className={c.num ? 'num' : undefined}>
                    {c.foot}
                  </td>
                ))}
              </tr>
            </tfoot>
          )}
        </table>
      </div>
      {rows.length > limit && (
        <div className="flex items-center justify-between gap-2 px-3 py-2 border-t border-slate-100 text-[0.7rem] text-slate-500">
          <span>
            Showing {limit.toLocaleString('en-IN')} of {rows.length.toLocaleString('en-IN')} rows (Excel export includes all)
          </span>
          <Btn small onClick={() => setLimit((l) => l + page * 3)}>
            Show more
          </Btn>
        </div>
      )}
    </div>
  );
}

/* --------------------------------- Modal ----------------------------------- */

export function Modal({ title, onClose, children, footer, wide }: { title: ReactNode; onClose: () => void; children: ReactNode; footer?: ReactNode; wide?: boolean }) {
  useEffect(() => {
    const k = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', k);
    return () => window.removeEventListener('keydown', k);
  }, [onClose]);
  return (
    <div className="fixed inset-0 z-50 bg-slate-900/50 flex items-end sm:items-center justify-center sm:p-4" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className={cx('bg-white w-full rounded-t-2xl sm:rounded-xl shadow-2xl flex flex-col max-h-[92vh] fade-in', wide ? 'sm:max-w-5xl' : 'sm:max-w-lg')}>
        <div className="flex items-center justify-between gap-3 px-4 py-3 border-b border-slate-200">
          <h2 className="font-bold text-slate-800 text-sm">{title}</h2>
          <button type="button" onClick={onClose} className="p-1 rounded hover:bg-slate-100 text-slate-500" aria-label="Close">
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="overflow-y-auto p-4">{children}</div>
        {footer && (
          <div className="flex flex-wrap justify-end gap-2 px-4 pt-3 border-t border-slate-200 bg-slate-50 sm:rounded-b-xl" style={{ paddingBottom: 'max(0.75rem, env(safe-area-inset-bottom))' }}>
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}

/* --------------------------------- Toasts ---------------------------------- */

export type Toast = { id: number; msg: string; kind: 'ok' | 'error' };

export function Toasts({ items }: { items: Toast[] }) {
  return (
    <div className="fixed z-[60] bottom-20 lg:bottom-4 right-3 left-3 sm:left-auto flex flex-col gap-2 items-end pointer-events-none">
      {items.map((t) => (
        <div
          key={t.id}
          className={cx(
            'pointer-events-auto max-w-sm w-full sm:w-auto px-3 py-2 rounded-lg shadow-lg text-xs font-medium fade-in flex items-start gap-2',
            t.kind === 'ok' ? 'bg-slate-800 text-white' : 'bg-red-600 text-white'
          )}
        >
          {t.kind === 'ok' ? <CheckCircle2 className="w-4 h-4 shrink-0" /> : <XCircle className="w-4 h-4 shrink-0" />}
          <span>{t.msg}</span>
        </div>
      ))}
    </div>
  );
}

export function Busy({ text }: { text: string }) {
  return (
    <div className="fixed inset-0 z-[70] bg-slate-900/40 flex items-center justify-center">
      <div className="bg-white rounded-xl shadow-xl px-6 py-5 flex items-center gap-3 text-sm font-medium text-slate-700">
        <span className="w-5 h-5 border-2 border-teal-600 border-t-transparent rounded-full animate-spin" />
        {text}
      </div>
    </div>
  );
}
