// Phone notifications (Web Push). Works once the backend is live and the VAPID public key is set (VITE_VAPID_PUBLIC_KEY);
// the matching private key stays on the server (alerts-dispatch). iPhone: only after "Add to Home Screen" (iOS 16.4+).
import { supabase } from './backend';

const KEY = import.meta.env.VITE_VAPID_PUBLIC_KEY as string | undefined;

export type PushState = 'unsupported' | 'not_configured' | 'blocked' | 'off' | 'on';

export async function pushState(): Promise<PushState> {
  if (!('serviceWorker' in navigator) || !('PushManager' in window) || !('Notification' in window)) return 'unsupported';
  if (!supabase || !KEY) return 'not_configured';
  if (Notification.permission === 'denied') return 'blocked';
  const reg = await navigator.serviceWorker.getRegistration();
  return (await reg?.pushManager.getSubscription()) ? 'on' : 'off';
}

const keyBytes = (b64: string) => Uint8Array.from(atob((b64 + '==='.slice((b64.length + 3) % 4)).replace(/-/g, '+').replace(/_/g, '/')), (c) => c.charCodeAt(0));

export async function enablePush(): Promise<PushState> {
  if ((await pushState()) === 'unsupported' || !supabase || !KEY) return pushState();
  if ((await Notification.requestPermission()) !== 'granted') return 'blocked';
  const reg = await navigator.serviceWorker.ready;
  const sub = (await reg.pushManager.getSubscription()) ?? (await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: keyBytes(KEY) }));
  const j = sub.toJSON() as { endpoint: string; keys: { p256dh: string; auth: string } };
  const { error } = await supabase.from('push_subscriptions').upsert({ endpoint: j.endpoint, p256dh: j.keys.p256dh, auth: j.keys.auth }, { onConflict: 'endpoint' });
  if (error) { await sub.unsubscribe(); throw new Error(error.message); }
  return 'on';
}

export async function disablePush(): Promise<PushState> {
  const sub = await (await navigator.serviceWorker.getRegistration())?.pushManager.getSubscription();
  if (sub) { await supabase?.from('push_subscriptions').delete().eq('endpoint', sub.endpoint); await sub.unsubscribe(); }
  return pushState();
}

/** E-mail alerts on/off for the signed-in person (live mode). */
export async function setEmailAlerts(on: boolean) {
  if (!supabase) throw new Error('Available when the backend is connected');
  const { data } = await supabase.auth.getUser();
  const { error } = await supabase.from('profiles').update({ email_alerts: on }).eq('id', data.user?.id ?? '');
  if (error) throw new Error(error.message);
}
