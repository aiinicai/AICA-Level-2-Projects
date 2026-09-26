import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { Settings, getSettings } from '../api';
import { useAuth } from './AuthContext';

interface SettingsContextValue {
  settings: Settings | null;
  loading: boolean;
  /** Re-read after the Settings page saves, so the change lands everywhere at once. */
  refresh: () => Promise<void>;
}

const SettingsContext = createContext<SettingsContextValue | null>(null);

/**
 * The firm's settings, loaded once per session.
 *
 * They are read in three places that must not disagree — the invoice form's
 * defaults, the letterhead on a generated PDF, and the Settings page itself —
 * so they live here rather than being fetched separately by each.
 */
export const SettingsProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user } = useAuth();
  const [settings, setSettings] = useState<Settings | null>(null);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    // The endpoint needs a session, so there is nothing to fetch until someone
    // has signed in.
    if (!user) {
      setSettings(null);
      return;
    }
    setLoading(true);
    try {
      const res = await getSettings();
      setSettings(res.data);
    } catch {
      // A failure here must not take a screen down: every consumer falls back
      // to a sensible default when settings are null.
      setSettings(null);
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return (
    <SettingsContext.Provider value={{ settings, loading, refresh }}>{children}</SettingsContext.Provider>
  );
};

export const useSettings = (): SettingsContextValue => {
  const ctx = useContext(SettingsContext);
  if (!ctx) throw new Error('useSettings must be used inside SettingsProvider');
  return ctx;
};
