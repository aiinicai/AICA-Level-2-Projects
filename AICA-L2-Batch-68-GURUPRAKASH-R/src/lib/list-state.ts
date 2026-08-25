import { useEffect, useState } from "react";

/**
 * Module-level cache so list filters survive navigation to a detail page and
 * back within the session. Deliberately not persisted to storage.
 */
const cache = new Map<string, unknown>();

export function useCachedState<T>(key: string, initial: T) {
  const [value, setValue] = useState<T>((cache.get(key) as T) ?? initial);
  useEffect(() => {
    cache.set(key, value);
  }, [key, value]);
  return [value, setValue] as const;
}
