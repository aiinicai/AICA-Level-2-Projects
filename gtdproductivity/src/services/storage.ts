/**
 * Local-First Database Storage Engine for GTDProductivity
 * Stores unified items, tags, and audit records with JSON export/import & snapshots.
 */

import { Item, Tag, ProjectType, CanonicalStatus } from '../types/gtd';

const STORAGE_KEY_ITEMS = 'gtd_productivity_items_v1';
const STORAGE_KEY_TAGS = 'gtd_productivity_tags_v1';
const STORAGE_KEY_SETTINGS = 'gtd_productivity_settings_v1';

// Initial sample seed data for first-time onboarding
const INITIAL_TAGS: Tag[] = [
  { id: 'tag-computer', name: '@computer', parentId: null, rank: 1, isContext: true, isEnergyContext: false, isTimeContext: false, isPersonContext: false, createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
  { id: 'tag-calls', name: '@calls', parentId: null, rank: 2, isContext: true, isEnergyContext: false, isTimeContext: false, isPersonContext: false, createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
  { id: 'tag-errands', name: '@errands', parentId: null, rank: 3, isContext: true, isEnergyContext: false, isTimeContext: false, isPersonContext: false, createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
  { id: 'tag-home', name: '@home', parentId: null, rank: 4, isContext: true, isEnergyContext: false, isTimeContext: false, isPersonContext: false, createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
  { id: 'tag-agenda', name: '@agenda', parentId: null, rank: 5, isContext: true, isEnergyContext: false, isTimeContext: false, isPersonContext: true, createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
];

const INITIAL_ITEMS: Item[] = [
  // Inbox open loops ready for Clarify flow
  {
    id: 'inbox-1',
    type: 'action',
    title: 'Schedule dentist annual checkup and cleaning',
    notes: 'Dr. Miller’s office: 555-0192. Preferred morning slot.',
    parentId: null,
    projectId: null,
    rank: 1,
    status: 'inbox',
    context: '@phone',
    flagged: false,
    deferDate: null,
    dueDate: null,
    estimatedMinutes: 5,
    energyLevel: 'low',
    completedAt: null,
    droppedAt: null,
    createdAt: new Date(Date.now() - 3600000 * 2).toISOString(),
    updatedAt: new Date(Date.now() - 3600000 * 2).toISOString(),
    deletedAt: null,
  },
  {
    id: 'inbox-2',
    type: 'action',
    title: 'Renovate guest bedroom home office space',
    notes: 'Need new desk, paint walls, soundproofing. Multi-step outcome.',
    parentId: null,
    projectId: null,
    rank: 2,
    status: 'inbox',
    context: '@home',
    flagged: false,
    deferDate: null,
    dueDate: null,
    estimatedMinutes: null,
    energyLevel: null,
    completedAt: null,
    droppedAt: null,
    createdAt: new Date(Date.now() - 3600000 * 5).toISOString(),
    updatedAt: new Date(Date.now() - 3600000 * 5).toISOString(),
    deletedAt: null,
  },
  {
    id: 'inbox-3',
    type: 'action',
    title: 'Reply to Alex regarding Q3 quarterly marketing slides',
    notes: 'Quick confirmation of metrics. Takes ~90 seconds.',
    parentId: null,
    projectId: null,
    rank: 3,
    status: 'inbox',
    context: '@office',
    flagged: true,
    deferDate: null,
    dueDate: null,
    estimatedMinutes: 2,
    energyLevel: 'low',
    completedAt: null,
    droppedAt: null,
    createdAt: new Date(Date.now() - 3600000 * 8).toISOString(),
    updatedAt: new Date(Date.now() - 3600000 * 8).toISOString(),
    deletedAt: null,
  },
  {
    id: 'inbox-4',
    type: 'action',
    title: 'Someday: Learn conversational Italian for Tuscany trip',
    notes: 'Explore Pimsleur or Duolingo. Not actionable this quarter.',
    parentId: null,
    projectId: null,
    rank: 4,
    status: 'inbox',
    context: '@computer',
    flagged: false,
    deferDate: null,
    dueDate: null,
    estimatedMinutes: null,
    energyLevel: null,
    completedAt: null,
    droppedAt: null,
    createdAt: new Date(Date.now() - 3600000 * 12).toISOString(),
    updatedAt: new Date(Date.now() - 3600000 * 12).toISOString(),
    deletedAt: null,
  },

  // Sample Clarified Project 1: Sequential
  {
    id: 'proj-1',
    type: 'project',
    title: 'Publish Product Launch Case Study',
    notes: 'Showcase enterprise customer rollout and reliability benchmarks.',
    parentId: null,
    projectId: null,
    rank: 1,
    status: 'active',
    projectType: 'sequential',
    flagged: false,
    deferDate: null,
    dueDate: null,
    estimatedMinutes: null,
    energyLevel: null,
    completedAt: null,
    droppedAt: null,
    reviewIntervalDays: 7,
    lastReviewedAt: new Date().toISOString(),
    nextReviewAt: new Date(Date.now() + 86400000 * 7).toISOString(),
    createdAt: new Date(Date.now() - 86400000 * 4).toISOString(),
    updatedAt: new Date().toISOString(),
    deletedAt: null,
  },
  // Actions under Project 1 (Sequential: only first action is Available)
  {
    id: 'act-1-1',
    type: 'action',
    title: 'Draft case study outline and metrics summary',
    notes: 'Focus on 40% latency reduction metric.',
    parentId: 'proj-1',
    projectId: 'proj-1',
    rank: 1,
    status: 'active',
    context: '@office',
    flagged: true,
    deferDate: null,
    dueDate: new Date(Date.now() + 3600000 * 6).toISOString(), // Due in 6 hours (due soon!)
    estimatedMinutes: 45,
    energyLevel: 'high',
    completedAt: null,
    droppedAt: null,
    createdAt: new Date(Date.now() - 86400000 * 4).toISOString(),
    updatedAt: new Date().toISOString(),
    deletedAt: null,
  },
  {
    id: 'act-1-2',
    type: 'action',
    title: 'Interview customer lead engineer on quotes',
    notes: 'Blocked until outline is ready.',
    parentId: 'proj-1',
    projectId: 'proj-1',
    rank: 2,
    status: 'active',
    context: '@phone',
    flagged: false,
    deferDate: null,
    dueDate: null,
    estimatedMinutes: 30,
    energyLevel: 'medium',
    completedAt: null,
    droppedAt: null,
    createdAt: new Date(Date.now() - 86400000 * 4).toISOString(),
    updatedAt: new Date().toISOString(),
    deletedAt: null,
  },

  // Sample Clarified Project 2: Parallel
  {
    id: 'proj-2',
    type: 'project',
    title: 'Home Spring Maintenance',
    notes: 'Parallel tasks that can be done independently as weather permits.',
    parentId: null,
    projectId: null,
    rank: 2,
    status: 'active',
    projectType: 'parallel',
    flagged: false,
    deferDate: null,
    dueDate: null,
    estimatedMinutes: null,
    energyLevel: null,
    completedAt: null,
    droppedAt: null,
    reviewIntervalDays: 7,
    lastReviewedAt: new Date().toISOString(),
    nextReviewAt: new Date(Date.now() + 86400000 * 7).toISOString(),
    createdAt: new Date(Date.now() - 86400000 * 6).toISOString(),
    updatedAt: new Date().toISOString(),
    deletedAt: null,
  },
  {
    id: 'act-2-1',
    type: 'action',
    title: 'Inspect HVAC filters and replace if dusty',
    notes: 'Filter size 20x25x1',
    parentId: 'proj-2',
    projectId: 'proj-2',
    rank: 1,
    status: 'active',
    context: '@home',
    flagged: false,
    deferDate: null,
    dueDate: new Date(Date.now() + 3600000 * 18).toISOString(), // Due in 18 hours (due soon!)
    estimatedMinutes: 15,
    energyLevel: 'low',
    completedAt: null,
    droppedAt: null,
    createdAt: new Date(Date.now() - 86400000 * 6).toISOString(),
    updatedAt: new Date().toISOString(),
    deletedAt: null,
  },
  {
    id: 'act-2-2',
    type: 'action',
    title: 'Clean exterior patio gutters and downspout',
    notes: 'Requires ladder and garden hose.',
    parentId: 'proj-2',
    projectId: 'proj-2',
    rank: 2,
    status: 'active',
    context: '@home',
    flagged: false,
    deferDate: null,
    dueDate: new Date(Date.now() + 86400000 * 4).toISOString(), // Upcoming in 4 days
    estimatedMinutes: 45,
    energyLevel: 'medium',
    completedAt: null,
    droppedAt: null,
    createdAt: new Date(Date.now() - 86400000 * 6).toISOString(),
    updatedAt: new Date().toISOString(),
    deletedAt: null,
  },

  // Delegated / Waiting For items
  {
    id: 'act-wf-1',
    type: 'action',
    title: 'Waiting for Marcus: Signed NDA countersignature',
    notes: 'Sent via email on Monday morning. Needed before client kickoff.',
    parentId: null,
    projectId: null,
    rank: 5,
    status: 'on_hold',
    context: '@office',
    waitingForPerson: 'Marcus Vance',
    waitingSince: new Date(Date.now() - 86400000 * 3).toISOString(),
    flagged: false,
    deferDate: null,
    dueDate: null,
    estimatedMinutes: null,
    energyLevel: null,
    completedAt: null,
    droppedAt: null,
    createdAt: new Date(Date.now() - 86400000 * 3).toISOString(),
    updatedAt: new Date().toISOString(),
    deletedAt: null,
  },
  {
    id: 'act-wf-2',
    type: 'action',
    title: 'Waiting for IT Support: Replacement USB-C monitor cable',
    notes: 'Submitted ticket #8291 to IT desk. Follow up if not ready by Friday.',
    parentId: null,
    projectId: null,
    rank: 6,
    status: 'on_hold',
    context: '@office',
    waitingForPerson: 'Sarah Chen (IT)',
    waitingSince: new Date(Date.now() - 86400000 * 5).toISOString(),
    flagged: true,
    deferDate: null,
    dueDate: null,
    estimatedMinutes: null,
    energyLevel: null,
    completedAt: null,
    droppedAt: null,
    createdAt: new Date(Date.now() - 86400000 * 5).toISOString(),
    updatedAt: new Date().toISOString(),
    deletedAt: null,
  },

  // Someday / Maybe items (Incubated ideas)
  {
    id: 'sm-1',
    type: 'action',
    title: 'Learn conversational Italian for summer Tuscany trip',
    notes: 'Look into audio immersion courses or Pimsleur 30-min lessons. Revisit in Spring.',
    parentId: null,
    projectId: null,
    rank: 1,
    status: 'on_hold',
    context: '@home',
    flagged: false,
    deferDate: null,
    dueDate: null,
    estimatedMinutes: null,
    energyLevel: null,
    completedAt: null,
    droppedAt: null,
    createdAt: new Date(Date.now() - 86400000 * 14).toISOString(),
    updatedAt: new Date().toISOString(),
    deletedAt: null,
  },
  {
    id: 'sm-2',
    type: 'action',
    title: 'Explore Rust and WebAssembly audio DSP synthesizer',
    notes: 'Read the Rust Audio Guide and experiment with wasm-bindgen low-latency loops.',
    parentId: null,
    projectId: null,
    rank: 2,
    status: 'on_hold',
    context: '@computer',
    flagged: false,
    deferDate: null,
    dueDate: null,
    estimatedMinutes: null,
    energyLevel: null,
    completedAt: null,
    droppedAt: null,
    createdAt: new Date(Date.now() - 86400000 * 21).toISOString(),
    updatedAt: new Date().toISOString(),
    deletedAt: null,
  },
  {
    id: 'sm-3',
    type: 'action',
    title: 'Build custom ergonomic workbench for garage workshop',
    notes: 'Measure garage footprint, draft 2x4 frame blueprint, research locking heavy-duty casters.',
    parentId: null,
    projectId: null,
    rank: 3,
    status: 'on_hold',
    context: '@home',
    flagged: false,
    deferDate: null,
    dueDate: null,
    estimatedMinutes: null,
    energyLevel: null,
    completedAt: null,
    droppedAt: null,
    createdAt: new Date(Date.now() - 86400000 * 30).toISOString(),
    updatedAt: new Date().toISOString(),
    deletedAt: null,
  },
];

const STORAGE_KEY_DAILY_REVIEW = 'gtd_daily_review_meta';
const STORAGE_KEY_DAILY_CHECKLIST = 'gtd_daily_review_checklist';

export const storage = {
  getItems(): Item[] {
    try {
      const data = localStorage.getItem(STORAGE_KEY_ITEMS);
      if (!data) {
        localStorage.setItem(STORAGE_KEY_ITEMS, JSON.stringify(INITIAL_ITEMS));
        return INITIAL_ITEMS;
      }
      let parsed: Item[] = JSON.parse(data);

      // Migration enrichment: ensure sample items have due dates
      const hasAnyDueDate = parsed.some(i => i.dueDate);
      if (!hasAnyDueDate) {
        parsed = parsed.map(i => {
          if (i.id === 'act-1-1') {
            return { ...i, dueDate: new Date(Date.now() + 3600000 * 6).toISOString() };
          }
          if (i.id === 'act-2-1') {
            return { ...i, dueDate: new Date(Date.now() + 3600000 * 18).toISOString() };
          }
          if (i.id === 'act-2-2') {
            return { ...i, dueDate: new Date(Date.now() + 86400000 * 4).toISOString() };
          }
          return i;
        });
      }

      // Migration enrichment: ensure items have contexts if not present
      const hasAnyContext = parsed.some(i => i.context);
      if (!hasAnyContext) {
        parsed = parsed.map(i => {
          if (i.id === 'act-1-1') return { ...i, context: '@office' };
          if (i.id === 'act-1-2') return { ...i, context: '@phone' };
          if (i.id === 'act-2-1') return { ...i, context: '@home' };
          if (i.id === 'act-2-2') return { ...i, context: '@home' };
          if (i.id === 'act-wf-1') return { ...i, context: '@office' };
          if (i.id === 'inbox-1') return { ...i, context: '@phone' };
          if (i.id === 'inbox-2') return { ...i, context: '@home' };
          if (i.id === 'inbox-3') return { ...i, context: '@office' };
          if (i.id === 'inbox-4') return { ...i, context: '@computer' };
          return i;
        });
      }

      // Migration enrichment: ensure sample Someday/Maybe items exist
      const hasSomedayMaybe = parsed.some(i => i.status === 'on_hold' && !i.waitingForPerson);
      if (!hasSomedayMaybe) {
        const somedaySeeds = INITIAL_ITEMS.filter(i => i.id.startsWith('sm-'));
        parsed = [...parsed, ...somedaySeeds];
      }

      // Migration enrichment: ensure sample Waiting For items exist
      const hasWaitingFor = parsed.some(i => i.waitingForPerson && i.status !== 'dropped');
      if (!hasWaitingFor) {
        const waitingSeeds = INITIAL_ITEMS.filter(i => i.id.startsWith('act-wf-'));
        parsed = [...parsed, ...waitingSeeds];
      }

      localStorage.setItem(STORAGE_KEY_ITEMS, JSON.stringify(parsed));
      return parsed;
    } catch {
      return INITIAL_ITEMS;
    }
  },

  saveItems(items: Item[]): void {
    try {
      localStorage.setItem(STORAGE_KEY_ITEMS, JSON.stringify(items));
    } catch (e) {
      console.error('Failed to save items to local storage', e);
    }
  },

  getTags(): Tag[] {
    try {
      const data = localStorage.getItem(STORAGE_KEY_TAGS);
      if (!data) {
        localStorage.setItem(STORAGE_KEY_TAGS, JSON.stringify(INITIAL_TAGS));
        return INITIAL_TAGS;
      }
      return JSON.parse(data);
    } catch {
      return INITIAL_TAGS;
    }
  },

  saveTags(tags: Tag[]): void {
    try {
      localStorage.setItem(STORAGE_KEY_TAGS, JSON.stringify(tags));
    } catch (e) {
      console.error('Failed to save tags to local storage', e);
    }
  },

  getLastDailyReview(): string | null {
    try {
      return localStorage.getItem(STORAGE_KEY_DAILY_REVIEW);
    } catch {
      return null;
    }
  },

  saveLastDailyReview(isoDate: string): void {
    try {
      localStorage.setItem(STORAGE_KEY_DAILY_REVIEW, isoDate);
    } catch (e) {
      console.error('Failed to save daily review date', e);
    }
  },

  getDailyChecklist(): Record<string, boolean> {
    try {
      const data = localStorage.getItem(STORAGE_KEY_DAILY_CHECKLIST);
      return data ? JSON.parse(data) : {};
    } catch {
      return {};
    }
  },

  saveDailyChecklist(checklist: Record<string, boolean>): void {
    try {
      localStorage.setItem(STORAGE_KEY_DAILY_CHECKLIST, JSON.stringify(checklist));
    } catch (e) {
      console.error('Failed to save daily checklist', e);
    }
  },

  resetToDefault(): { items: Item[]; tags: Tag[] } {
    localStorage.setItem(STORAGE_KEY_ITEMS, JSON.stringify(INITIAL_ITEMS));
    localStorage.setItem(STORAGE_KEY_TAGS, JSON.stringify(INITIAL_TAGS));
    return { items: INITIAL_ITEMS, tags: INITIAL_TAGS };
  },

  exportJSON(): string {
    const backup = {
      version: '1.0',
      exportedAt: new Date().toISOString(),
      items: this.getItems(),
      tags: this.getTags(),
    };
    return JSON.stringify(backup, null, 2);
  },

  importJSON(jsonString: string): boolean {
    try {
      const parsed = JSON.parse(jsonString);
      if (Array.isArray(parsed.items) && Array.isArray(parsed.tags)) {
        this.saveItems(parsed.items);
        this.saveTags(parsed.tags);
        return true;
      }
      return false;
    } catch {
      return false;
    }
  },
};
