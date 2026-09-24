import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  DEFAULT_SETTINGS,
  SEED_ALERTS,
  SEED_CONNECTIONS,
  SEED_DASHBOARDS,
  SEED_MEMBERS,
  SEED_NOTIFICATIONS,
  SEED_REPORTS,
  SEED_SCHEDULES,
  uid,
} from "./data/seed";
import type {
  AlertRule,
  AppNotification,
  Connection,
  Dashboard,
  Member,
  Report,
  ScheduledReport,
  Widget,
  WorkspaceSettings,
} from "./types";

const KEY = "thedash.workspace.v1";

interface WorkspaceState {
  dashboards: Dashboard[];
  connections: Connection[];
  notifications: AppNotification[];
  alerts: AlertRule[];
  schedules: ScheduledReport[];
  reports: Report[];
  members: Member[];
  settings: WorkspaceSettings;
  onboardingDone: boolean;
}

const initialState = (): WorkspaceState => ({
  dashboards: SEED_DASHBOARDS,
  connections: SEED_CONNECTIONS,
  notifications: SEED_NOTIFICATIONS,
  alerts: SEED_ALERTS,
  schedules: SEED_SCHEDULES,
  reports: SEED_REPORTS,
  members: SEED_MEMBERS,
  settings: DEFAULT_SETTINGS,
  onboardingDone: false,
});

interface StoreApi extends WorkspaceState {
  hydrated: boolean;
  /* dashboards */
  createDashboard: (name: string, from?: Dashboard) => Dashboard;
  updateDashboard: (id: string, patch: Partial<Dashboard>) => void;
  deleteDashboard: (id: string) => void;
  duplicateDashboard: (id: string) => Dashboard | undefined;
  addWidget: (dashboardId: string, widget: Widget) => void;
  updateWidget: (dashboardId: string, widgetId: string, patch: Partial<Widget>) => void;
  removeWidget: (dashboardId: string, widgetId: string) => void;
  moveWidget: (dashboardId: string, from: number, to: number) => void;
  /* connections */
  addConnection: (c: Connection) => void;
  updateConnection: (id: string, patch: Partial<Connection>) => void;
  removeConnection: (id: string) => void;
  /* misc */
  notify: (n: Omit<AppNotification, "id" | "at" | "read">) => void;
  markAllRead: () => void;
  markRead: (id: string) => void;
  upsertAlert: (a: AlertRule) => void;
  removeAlert: (id: string) => void;
  upsertSchedule: (s: ScheduledReport) => void;
  removeSchedule: (id: string) => void;
  upsertReport: (r: Report) => void;
  removeReport: (id: string) => void;
  upsertMember: (m: Member) => void;
  removeMember: (id: string) => void;
  updateSettings: (patch: Partial<WorkspaceSettings>) => void;
  completeOnboarding: () => void;
  resetWorkspace: () => void;
}

const StoreContext = createContext<StoreApi | null>(null);

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<WorkspaceState>(initialState);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(KEY);
      if (raw) {
        const parsed = JSON.parse(raw) as Partial<WorkspaceState>;
        setState((prev) => ({ ...prev, ...parsed, settings: { ...prev.settings, ...parsed.settings } }));
      }
    } catch {
      /* corrupted storage — fall back to seed */
    }
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    try {
      localStorage.setItem(KEY, JSON.stringify(state));
    } catch {
      /* quota — non fatal */
    }
  }, [state, hydrated]);

  const patchDashboard = useCallback((id: string, fn: (d: Dashboard) => Dashboard) => {
    setState((s) => ({
      ...s,
      dashboards: s.dashboards.map((d) => (d.id === id ? { ...fn(d), updatedAt: new Date().toISOString() } : d)),
    }));
  }, []);

  const api = useMemo<StoreApi>(
    () => ({
      ...state,
      hydrated,
      createDashboard(name, from) {
        const created: Dashboard = from
          ? { ...structuredClone(from), id: uid(), name, updatedAt: new Date().toISOString(), favourite: false }
          : {
              id: uid(),
              name,
              description: "",
              tabs: ["Overview"],
              widgets: [],
              filters: [
                { id: "date", label: "Date range", field: "invoice_date", type: "date-range", value: "last_12m" },
              ],
              visibility: "private",
              updatedAt: new Date().toISOString(),
            };
        setState((s) => ({ ...s, dashboards: [created, ...s.dashboards] }));
        return created;
      },
      updateDashboard(id, patch) {
        patchDashboard(id, (d) => ({ ...d, ...patch }));
      },
      deleteDashboard(id) {
        setState((s) => ({ ...s, dashboards: s.dashboards.filter((d) => d.id !== id) }));
      },
      duplicateDashboard(id) {
        const source = state.dashboards.find((d) => d.id === id);
        if (!source) return undefined;
        const copy: Dashboard = {
          ...structuredClone(source),
          id: uid(),
          name: `${source.name} (copy)`,
          favourite: false,
          updatedAt: new Date().toISOString(),
        };
        setState((s) => ({ ...s, dashboards: [copy, ...s.dashboards] }));
        return copy;
      },
      addWidget(dashboardId, widget) {
        patchDashboard(dashboardId, (d) => ({ ...d, widgets: [...d.widgets, widget] }));
      },
      updateWidget(dashboardId, widgetId, patch) {
        patchDashboard(dashboardId, (d) => ({
          ...d,
          widgets: d.widgets.map((w) => (w.id === widgetId ? { ...w, ...patch } : w)),
        }));
      },
      removeWidget(dashboardId, widgetId) {
        patchDashboard(dashboardId, (d) => ({ ...d, widgets: d.widgets.filter((w) => w.id !== widgetId) }));
      },
      moveWidget(dashboardId, from, to) {
        patchDashboard(dashboardId, (d) => {
          const widgets = [...d.widgets];
          const [moved] = widgets.splice(from, 1);
          widgets.splice(to, 0, moved);
          return { ...d, widgets };
        });
      },
      addConnection(c) {
        setState((s) => ({ ...s, connections: [c, ...s.connections] }));
      },
      updateConnection(id, patch) {
        setState((s) => ({ ...s, connections: s.connections.map((c) => (c.id === id ? { ...c, ...patch } : c)) }));
      },
      removeConnection(id) {
        setState((s) => ({ ...s, connections: s.connections.filter((c) => c.id !== id) }));
      },
      notify(n) {
        setState((s) => ({
          ...s,
          notifications: [{ ...n, id: uid(), at: new Date().toISOString(), read: false }, ...s.notifications].slice(0, 50),
        }));
      },
      markAllRead() {
        setState((s) => ({ ...s, notifications: s.notifications.map((x) => ({ ...x, read: true })) }));
      },
      markRead(id) {
        setState((s) => ({
          ...s,
          notifications: s.notifications.map((x) => (x.id === id ? { ...x, read: true } : x)),
        }));
      },
      upsertAlert(a) {
        setState((s) => ({
          ...s,
          alerts: s.alerts.some((x) => x.id === a.id) ? s.alerts.map((x) => (x.id === a.id ? a : x)) : [a, ...s.alerts],
        }));
      },
      removeAlert(id) {
        setState((s) => ({ ...s, alerts: s.alerts.filter((a) => a.id !== id) }));
      },
      upsertSchedule(sch) {
        setState((s) => ({
          ...s,
          schedules: s.schedules.some((x) => x.id === sch.id)
            ? s.schedules.map((x) => (x.id === sch.id ? sch : x))
            : [sch, ...s.schedules],
        }));
      },
      removeSchedule(id) {
        setState((s) => ({ ...s, schedules: s.schedules.filter((x) => x.id !== id) }));
      },
      upsertReport(r) {
        setState((s) => ({
          ...s,
          reports: s.reports.some((x) => x.id === r.id) ? s.reports.map((x) => (x.id === r.id ? r : x)) : [r, ...s.reports],
        }));
      },
      removeReport(id) {
        setState((s) => ({ ...s, reports: s.reports.filter((x) => x.id !== id) }));
      },
      upsertMember(m) {
        setState((s) => ({
          ...s,
          members: s.members.some((x) => x.id === m.id) ? s.members.map((x) => (x.id === m.id ? m : x)) : [...s.members, m],
        }));
      },
      removeMember(id) {
        setState((s) => ({ ...s, members: s.members.filter((m) => m.id !== id) }));
      },
      updateSettings(patch) {
        setState((s) => ({ ...s, settings: { ...s.settings, ...patch } }));
      },
      completeOnboarding() {
        setState((s) => ({ ...s, onboardingDone: true }));
      },
      resetWorkspace() {
        setState(initialState());
      },
    }),
    [state, hydrated, patchDashboard],
  );

  return <StoreContext.Provider value={api}>{children}</StoreContext.Provider>;
}

export function useWorkspace() {
  const ctx = useContext(StoreContext);
  if (!ctx) throw new Error("useWorkspace must be used inside WorkspaceProvider");
  return ctx;
}

export function useFormatOpts() {
  const { settings } = useWorkspace();
  return {
    currency: settings.currency,
    numberSystem: settings.numberSystem,
    compact: settings.compactNumbers,
  };
}
