import { useSyncExternalStore } from "react";

type State = { active: boolean; startedAt: number };

let state: State = { active: false, startedAt: 0 };
const subscribers = new Set<() => void>();

function emit() {
  subscribers.forEach((fn) => fn());
}

export function setRecordingActive(active: boolean) {
  state = active ? { active: true, startedAt: Date.now() } : { active: false, startedAt: 0 };
  emit();
}

function subscribe(fn: () => void) {
  subscribers.add(fn);
  return () => subscribers.delete(fn);
}

const server: State = { active: false, startedAt: 0 };

export function useRecordingState() {
  return useSyncExternalStore(
    subscribe,
    () => state,
    () => server,
  );
}
