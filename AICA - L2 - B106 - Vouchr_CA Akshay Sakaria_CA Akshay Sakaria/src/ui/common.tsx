import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from 'react';
import type { ExpenseStatus } from '../data/types';
import { useT, useTr } from '../i18n';
import { RuleError } from '../data/store';
import { Icon } from './Icon';
import { EmptyArt } from './Art';

export function StatusBadge({ status }: { status: ExpenseStatus }) {
  const t = useT();
  const tone = { submitted: 'info', approved: 'ok', rejected: 'danger', posted: 'brand', draft: '' }[status];
  return <span className={`badge ${tone}`}>{t(`status_${status}`)}</span>;
}

const BILL_STATUS = { paid: ['Paid', 'ok'], partial: ['Partially paid', 'info'], overdue: ['Overdue', 'danger'], open: ['Unpaid', 'warn'] } as const;

export function BillStatusBadge({ status }: { status: keyof typeof BILL_STATUS }) {
  const tr = useTr();
  const [label, tone] = BILL_STATUS[status];
  return <span className={`badge ${tone}`}>{tr(label)}</span>;
}

export function Initials({ name }: { name: string }) {
  const i = name.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]).join('').toUpperCase();
  return <div className="avatar">{i || '?'}</div>;
}

export function Logo({ name, url, size = 34 }: { name: string; url?: string; size?: number }) {
  if (url) return <img src={url} alt="" style={{ width: size, height: size }} />;
  return <div className="logo-fallback" style={{ width: size, height: size }}>{name.slice(0, 1)}</div>;
}

export function PageHead({ title, sub, children }: { title: string; sub?: string; children?: ReactNode }) {
  return (
    <div className="row between wrap" style={{ marginBottom: 16 }}>
      <div>
        <h1>{title}</h1>
        {sub && <div className="muted small" style={{ marginTop: 2 }}>{sub}</div>}
      </div>
      {children && <div className="row wrap">{children}</div>}
    </div>
  );
}

export function Empty({ children, art = 'doc' }: { children: ReactNode; art?: 'doc' | 'tray' | 'done' | 'search' }) {
  return <div className="empty"><EmptyArt kind={art} /><div>{children}</div></div>;
}

export function Drawer({ title, onClose, children, footer }: { title: ReactNode; onClose: () => void; children: ReactNode; footer?: ReactNode }) {
  const tr = useTr();
  const ref = useRef<HTMLDivElement>(null);
  // WCAG 2.1.2 / 2.4.3: Esc closes, Tab stays inside, focus returns to the opener
  useEffect(() => {
    const opener = document.activeElement as HTMLElement | null;
    const el = ref.current;
    el?.querySelector<HTMLElement>('input, select, textarea, button:not([aria-label])')?.focus({ preventScroll: true });
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { e.preventDefault(); onClose(); return; }
      if (e.key !== 'Tab' || !el) return;
      const f = [...el.querySelectorAll<HTMLElement>('a[href], button:not([disabled]), input:not([disabled]), select, textarea, [tabindex]:not([tabindex="-1"])')];
      if (!f.length) return;
      if (e.shiftKey && document.activeElement === f[0]) { e.preventDefault(); f[f.length - 1].focus(); }
      else if (!e.shiftKey && document.activeElement === f[f.length - 1]) { e.preventDefault(); f[0].focus(); }
    };
    document.addEventListener('keydown', onKey);
    return () => { document.removeEventListener('keydown', onKey); opener?.focus?.({ preventScroll: true }); };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  return (
    <div className="overlay" onClick={onClose}>
      <div className="drawer" ref={ref} onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true" aria-labelledby="drawer-title">
        <div className="drawer-head">
          <button className="icon-btn" onClick={onClose} aria-label={tr('Close')}><Icon name="x" /></button>
          <div className="grow"><h2 className="ellipsis" id="drawer-title">{title}</h2></div>
        </div>
        <div className="drawer-body">{children}</div>
        {footer && <div className="drawer-foot">{footer}</div>}
      </div>
    </div>
  );
}

// ---------- Toasts ----------
type Toast = { msg: string; err?: boolean } | null;
const ToastCtx = createContext<(msg: string, err?: boolean) => void>(() => {});

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toast, setToast] = useState<Toast>(null);
  const show = useCallback((msg: string, err?: boolean) => {
    setToast({ msg, err });
    window.setTimeout(() => setToast(null), err ? 4200 : 2400);
  }, []);
  return (
    <ToastCtx.Provider value={show}>
      {children}
      {toast && <div className={`toast ${toast.err ? 'err' : ''}`} role={toast.err ? 'alert' : 'status'}>{toast.msg}</div>}
    </ToastCtx.Provider>
  );
}

export const useToast = () => useContext(ToastCtx);

// ---------- Confirm sheet ----------
// Replaces the browser's window.confirm, whose OK / Cancel buttons are always in the browser's language (usually English).
// Usage: const confirm = useConfirm(); if (await confirm(tr('Delete this draft?'), { danger: true })) …
// With `input`, it asks for a short text (e.g. the reason for cancelling) — useAskText() — instead of window.prompt.
type ConfirmReq = { message: string; ok?: string; danger?: boolean; input?: { label: string; min: number }; resolve: (yes: boolean, text?: string) => void };
const ConfirmCtx = createContext<(message: string, opts?: { ok?: string; danger?: boolean }) => Promise<boolean>>(async () => false);
const AskTextCtx = createContext<(message: string, opts: { label: string; ok?: string; danger?: boolean; min?: number }) => Promise<string | null>>(async () => null);

export function ConfirmProvider({ children }: { children: ReactNode }) {
  const [req, setReq] = useState<ConfirmReq | null>(null);
  const ask = useCallback((message: string, opts: { ok?: string; danger?: boolean } = {}) =>
    new Promise<boolean>((resolve) => setReq({ message, ...opts, resolve })), []);
  const askText = useCallback((message: string, opts: { label: string; ok?: string; danger?: boolean; min?: number }) =>
    new Promise<string | null>((resolve) => setReq({ message, ok: opts.ok, danger: opts.danger, input: { label: opts.label, min: opts.min ?? 3 }, resolve: (yes, text) => resolve(yes ? (text ?? '').trim() : null) })), []);
  const done = (yes: boolean, text?: string) => { req?.resolve(yes, text); setReq(null); };
  return (
    <ConfirmCtx.Provider value={ask}>
      <AskTextCtx.Provider value={askText}>
        {children}
        {req && <ConfirmSheet req={req} onDone={done} />}
      </AskTextCtx.Provider>
    </ConfirmCtx.Provider>
  );
}

function ConfirmSheet({ req, onDone }: { req: ConfirmReq; onDone: (yes: boolean, text?: string) => void }) {
  const tr = useTr();
  const ref = useRef<HTMLDivElement>(null);
  const [text, setText] = useState('');
  useEffect(() => {
    const opener = document.activeElement as HTMLElement | null;
    const first = req.input ? 'textarea' : '[data-cancel]'; // safe default: Cancel (or the text box)
    ref.current?.querySelector<HTMLElement>(first)?.focus({ preventScroll: true });
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { e.preventDefault(); onDone(false); }
      if (e.key === 'Tab' && ref.current) {
        const f = [...ref.current.querySelectorAll<HTMLElement>('textarea, button:not([disabled])')];
        if (e.shiftKey && document.activeElement === f[0]) { e.preventDefault(); f[f.length - 1].focus(); }
        else if (!e.shiftKey && document.activeElement === f[f.length - 1]) { e.preventDefault(); f[0].focus(); }
      }
    };
    document.addEventListener('keydown', onKey);
    return () => { document.removeEventListener('keydown', onKey); opener?.focus?.({ preventScroll: true }); };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  return (
    <div className="overlay confirm-overlay" onClick={() => onDone(false)}>
      <div className="confirm-sheet card pad stack" ref={ref} role="alertdialog" aria-modal="true" aria-describedby="confirm-msg" onClick={(e) => e.stopPropagation()}>
        <p id="confirm-msg" style={{ margin: 0 }}>{req.message}</p>
        {req.input && (
          <div className="field"><label htmlFor="confirm-text">{req.input.label}</label>
            <textarea id="confirm-text" className="input sm" rows={2} maxLength={250} value={text} onChange={(e) => setText(e.target.value)} /></div>
        )}
        <div className="row" style={{ justifyContent: 'flex-end' }}>
          <button className="btn" data-cancel onClick={() => onDone(false)}>{tr('Cancel')}</button>
          <button className={`btn ${req.danger ? 'danger' : 'primary'}`} disabled={!!req.input && text.trim().length < req.input.min} onClick={() => onDone(true, text)}>{req.ok ?? tr('Yes, continue')}</button>
        </div>
      </div>
    </div>
  );
}

export const useConfirm = () => useContext(ConfirmCtx);
export const useAskText = () => useContext(AskTextCtx);

/** Runs an action; a RuleError becomes a translated error toast, anything else is re-thrown. Returns true on success. */
export function useAttempt() {
  const toast = useToast();
  const tr = useTr();
  return (fn: () => void, ok?: string): boolean => {
    try {
      fn();
      if (ok) toast(tr(ok));
      return true;
    } catch (err) {
      if (err instanceof RuleError) { toast(tr(err.message, err.vars), true); return false; }
      throw err;
    }
  };
}
