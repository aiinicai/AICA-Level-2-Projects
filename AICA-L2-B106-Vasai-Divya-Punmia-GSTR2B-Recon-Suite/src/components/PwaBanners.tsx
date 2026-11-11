import { useState } from 'react';
import { MonitorDown, RefreshCcw, Share, ShieldAlert, SquarePlus, X } from 'lucide-react';
import { useInstallPrompt } from '../pwa';
import { Btn, cx } from './ui';

const KEY = 'gsr-install-banner-dismissed';
const DAYS = 14;

const dismissedRecently = () => {
  try {
    return Date.now() - Number(localStorage.getItem(KEY) || 0) < DAYS * 864e5;
  } catch {
    return false;
  }
};

/**
 * Bottom banners: "Install app" when the browser offers it, iPhone / iPad instructions
 * (Safari has no install prompt), a note when a phone opens the plain-http network link
 * (installing needs https), and "Updated — reload" after a new version arrives.
 */
export function PwaBanners({ phone }: { phone: boolean }) {
  const p = useInstallPrompt();
  const [hidden, setHidden] = useState(dismissedRecently);
  const dismiss = () => {
    setHidden(true);
    try {
      localStorage.setItem(KEY, String(Date.now()));
    } catch {
      /* private mode */
    }
  };

  let body: React.ReactNode = null;
  if (p.updateReady) {
    body = (
      <>
        <RefreshCcw className="w-5 h-5 text-teal-300 shrink-0" />
        <span className="flex-1">A new version of the app is ready.</span>
        <Btn small kind="primary" onClick={() => location.reload()}>
          Reload
        </Btn>
      </>
    );
  } else if (!hidden && !p.standalone) {
    if (p.canInstall) {
      body = (
        <>
          <MonitorDown className="w-5 h-5 text-teal-300 shrink-0" />
          <span className="flex-1">
            <b>Install GSTR-2B Recon</b> — open it from your {phone ? 'home screen' : 'desktop / Start menu'} in its own window.
          </span>
          <Btn small kind="primary" onClick={() => p.install().then((ok) => ok || dismiss())}>
            Install
          </Btn>
        </>
      );
    } else if (p.ios && p.secure) {
      body = (
        <>
          <SquarePlus className="w-5 h-5 text-teal-300 shrink-0" />
          <span className="flex-1">
            Install on this {/iphone|ipod/i.test(navigator.userAgent) ? 'iPhone' : 'iPad'}: tap{' '}
            <Share className="w-4 h-4 inline -mt-0.5" /> <b>Share</b>, then <b>Add to Home Screen</b>.
          </span>
        </>
      );
    } else if ((p.ios || p.android) && !p.secure) {
      body = (
        <>
          <ShieldAlert className="w-5 h-5 text-amber-300 shrink-0" />
          <span className="flex-1">
            To install on this {p.ios ? 'iPhone / iPad' : 'phone'}, open the <b>https://</b> link shown in the server window. Over http you can only add a shortcut (browser menu →{' '}
            <b>Add to Home screen</b>).{' '}
            <a className="underline text-teal-300" href="./install">
              How to set up
            </a>
          </span>
        </>
      );
    }
  }
  if (!body) return null;
  return (
    <div className={cx('no-print fixed z-40 inset-x-2 sm:inset-x-auto sm:right-4 sm:max-w-md fade-in', phone ? 'bottom-[calc(4rem+env(safe-area-inset-bottom))]' : 'bottom-4')}>
      <div className="flex items-center gap-3 bg-slate-900 text-white text-xs rounded-xl shadow-2xl px-3 py-2.5 border border-slate-700">
        {body}
        {!p.updateReady && (
          <button type="button" onClick={dismiss} className="p-1 text-slate-400 hover:text-white shrink-0" aria-label="Dismiss">
            <X className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  );
}
