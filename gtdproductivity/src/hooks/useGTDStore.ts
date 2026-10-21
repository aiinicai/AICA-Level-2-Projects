import { useState, useEffect, useCallback, useMemo } from 'react';
import { Item, Tag, ProjectType, CanonicalStatus, DynamicAvailability } from '../types/gtd';
import { storage } from '../services/storage';

export function useGTDStore() {
  const [items, setItems] = useState<Item[]>(() => storage.getItems());
  const [tags, setTags] = useState<Tag[]>(() => storage.getTags());

  // Save changes to storage whenever items or tags change
  useEffect(() => {
    storage.saveItems(items);
  }, [items]);

  useEffect(() => {
    storage.saveTags(tags);
  }, [tags]);

  // Active items (excluding soft-deleted)
  const activeItems = useMemo(() => {
    return items.filter(item => !item.deletedAt);
  }, [items]);

  // Unprocessed Inbox Items
  const inboxItems = useMemo(() => {
    return activeItems
      .filter(item => item.status === 'inbox')
      .sort((a, b) => a.rank - b.rank);
  }, [activeItems]);

  // Projects (Folder/Project container items)
  const projects = useMemo(() => {
    return activeItems
      .filter(item => item.type === 'project' && item.status !== 'dropped')
      .sort((a, b) => a.rank - b.rank);
  }, [activeItems]);

  // Next Actions Availability Logic (OmniFocus / GTD)
  const nextActions = useMemo(() => {
    const now = new Date().toISOString();

    // Group actions by project
    const projectMap = new Map<string, Item>();
    projects.forEach(p => projectMap.set(p.id, p));

    // Standalone actions without a project
    const standaloneActions = activeItems.filter(
      item => item.type === 'action' && 
              item.status === 'active' && 
              !item.projectId && 
              !item.waitingForPerson &&
              (!item.deferDate || item.deferDate <= now)
    );

    // Actions within projects, filtered by projectType
    const projectActions: Item[] = [];

    projects.forEach(project => {
      if (project.status !== 'active') return; // Project on hold or completed

      const children = activeItems
        .filter(item => item.projectId === project.id && item.status === 'active' && !item.completedAt)
        .sort((a, b) => a.rank - b.rank);

      if (project.projectType === 'sequential') {
        // Sequential: Only the very first non-deferred incomplete action is available
        const firstAvailable = children.find(child => !child.deferDate || child.deferDate <= now);
        if (firstAvailable) {
          projectActions.push(firstAvailable);
        }
      } else {
        // Parallel or Single-Action List: All non-deferred actions are available
        children.forEach(child => {
          if (!child.deferDate || child.deferDate <= now) {
            projectActions.push(child);
          }
        });
      }
    });

    return [...standaloneActions, ...projectActions].sort((a, b) => {
      // Flagged first, then rank
      if (a.flagged !== b.flagged) return a.flagged ? -1 : 1;
      return a.rank - b.rank;
    });
  }, [activeItems, projects]);

  // Waiting For Items
  const waitingForItems = useMemo(() => {
    return activeItems.filter(
      item => (item.waitingForPerson || item.title.toLowerCase().startsWith('waiting for')) && 
              !item.completedAt && 
              item.status !== 'dropped'
    );
  }, [activeItems]);

  // Someday / Maybe Items (Incubated items parked on hold, excluding active delegations)
  const somedayMaybeItems = useMemo(() => {
    return activeItems.filter(
      item => item.status === 'on_hold' && 
              !item.waitingForPerson && 
              !item.title.toLowerCase().startsWith('waiting for') &&
              !item.completedAt
    );
  }, [activeItems]);

  // 1. Frictionless Quick Capture
  const captureItem = useCallback((title: string, notes: string = '', dueDate?: string | null, context?: string | null) => {
    if (!title.trim()) return;

    // Detect @context from title if present (e.g. "Buy groceries @errands")
    const contextMatch = title.match(/@([a-zA-Z0-9_-]+)/);
    const detectedContext = contextMatch ? `@${contextMatch[1].toLowerCase()}` : null;

    const newItem: Item = {
      id: `item-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`,
      type: 'action',
      title: title.trim(),
      notes: notes.trim(),
      parentId: null,
      projectId: null,
      rank: items.length + 1,
      status: 'inbox',
      context: context || detectedContext || null,
      flagged: false,
      deferDate: null,
      dueDate: dueDate ? new Date(dueDate).toISOString() : null,
      estimatedMinutes: null,
      energyLevel: null,
      completedAt: null,
      droppedAt: null,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      deletedAt: null,
    };

    setItems(prev => [newItem, ...prev]);
    return newItem;
  }, [items.length]);

  // 2. Clarify Operations (David Allen Decision Tree)

  // 2a. Non-Actionable: Trash
  const clarifyTrash = useCallback((id: string) => {
    setItems(prev => prev.map(item => 
      item.id === id ? { ...item, deletedAt: new Date().toISOString(), status: 'dropped' } : item
    ));
  }, []);

  // 2b. Non-Actionable: Someday / Maybe
  const clarifySomedayMaybe = useCallback((id: string, notes?: string) => {
    setItems(prev => prev.map(item => 
      item.id === id ? { 
        ...item, 
        status: 'on_hold', 
        notes: notes !== undefined ? notes : item.notes,
        updatedAt: new Date().toISOString() 
      } : item
    ));
  }, []);

  // 2c. Non-Actionable: Reference
  const clarifyReference = useCallback((id: string, title?: string, notes?: string) => {
    setItems(prev => prev.map(item => 
      item.id === id ? { 
        ...item, 
        title: title || item.title,
        notes: notes !== undefined ? notes : item.notes,
        status: 'on_hold',
        updatedAt: new Date().toISOString() 
      } : item
    ));
  }, []);

  // 2d. Actionable: 2-Minute Rule (Do It Now)
  const clarifyDoNow = useCallback((id: string) => {
    setItems(prev => prev.map(item => 
      item.id === id ? { 
        ...item, 
        status: 'completed', 
        completedAt: new Date().toISOString(),
        updatedAt: new Date().toISOString() 
      } : item
    ));
  }, []);

  // 2e. Actionable: Delegate / Waiting For
  const clarifyWaitingFor = useCallback((id: string, person: string, notes?: string) => {
    setItems(prev => prev.map(item => 
      item.id === id ? { 
        ...item, 
        status: 'on_hold', 
        waitingForPerson: person.trim(),
        waitingSince: new Date().toISOString(),
        notes: notes !== undefined ? notes : item.notes,
        updatedAt: new Date().toISOString() 
      } : item
    ));
  }, []);

  // 2f. Actionable: Multi-Step Outcome -> Create Project + First Next Action
  const clarifyConvertToProject = useCallback((
    id: string, 
    projectTitle: string, 
    projectType: ProjectType, 
    firstActionTitle: string,
    notes?: string
  ) => {
    const now = new Date().toISOString();
    const actionId = `act-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`;

    setItems(prev => {
      // 1. Convert current inbox item to Project
      const updated = prev.map(item => {
        if (item.id === id) {
          return {
            ...item,
            type: 'project' as const,
            title: projectTitle.trim(),
            status: 'active' as CanonicalStatus,
            projectType,
            notes: notes !== undefined ? notes : item.notes,
            reviewIntervalDays: 7,
            lastReviewedAt: now,
            nextReviewAt: new Date(Date.now() + 86400000 * 7).toISOString(),
            updatedAt: now,
          };
        }
        return item;
      });

      // 2. Add the first next physical action child
      const firstAction: Item = {
        id: actionId,
        type: 'action',
        title: firstActionTitle.trim() || 'Define project scope and next milestone',
        notes: '',
        parentId: id,
        projectId: id,
        rank: 1,
        status: 'active',
        flagged: false,
        deferDate: null,
        dueDate: null,
        estimatedMinutes: null,
        energyLevel: null,
        completedAt: null,
        droppedAt: null,
        createdAt: now,
        updatedAt: now,
        deletedAt: null,
      };

      return [firstAction, ...updated];
    });
  }, []);

  // 2g. Actionable: Single Action -> Convert to Next Action with Project & Details
  const clarifyToNextAction = useCallback((
    id: string,
    title: string,
    projectId: string | null,
    notes?: string,
    deferDate?: string | null,
    dueDate?: string | null,
    estimatedMinutes?: number | null,
    energyLevel?: 'low' | 'medium' | 'high' | null,
    context?: string | null
  ) => {
    setItems(prev => prev.map(item => {
      if (item.id === id) {
        return {
          ...item,
          type: 'action',
          title: title.trim(),
          projectId: projectId || null,
          parentId: projectId || null,
          status: 'active',
          notes: notes !== undefined ? notes : item.notes,
          deferDate: deferDate || null,
          dueDate: dueDate || null,
          estimatedMinutes: estimatedMinutes || null,
          energyLevel: energyLevel || null,
          context: context !== undefined ? context : (item.context || null),
          updatedAt: new Date().toISOString(),
        };
      }
      return item;
    }));
  }, []);

  // Generic Item Updates
  const toggleComplete = useCallback((id: string) => {
    setItems(prev => prev.map(item => {
      if (item.id === id) {
        const isDone = Boolean(item.completedAt);
        return {
          ...item,
          status: isDone ? 'active' : 'completed',
          completedAt: isDone ? null : new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        };
      }
      return item;
    }));
  }, []);

  const toggleFlag = useCallback((id: string) => {
    setItems(prev => prev.map(item => {
      if (item.id === id) {
        return {
          ...item,
          flagged: !item.flagged,
          updatedAt: new Date().toISOString(),
        };
      }
      return item;
    }));
  }, []);

  const updateDueDate = useCallback((id: string, dueDate: string | null) => {
    setItems(prev => prev.map(item => {
      if (item.id === id) {
        return {
          ...item,
          dueDate: dueDate ? new Date(dueDate).toISOString() : null,
          updatedAt: new Date().toISOString(),
        };
      }
      return item;
    }));
  }, []);

  const updateContext = useCallback((id: string, context: string | null) => {
    setItems(prev => prev.map(item => {
      if (item.id === id) {
        return {
          ...item,
          context: context ? context.trim() : null,
          updatedAt: new Date().toISOString(),
        };
      }
      return item;
    }));
  }, []);

  const createProject = useCallback((title: string, projectType: ProjectType = 'sequential', notes: string = '') => {
    const now = new Date().toISOString();
    const newProj: Item = {
      id: `proj-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`,
      type: 'project',
      title: title.trim(),
      notes: notes.trim(),
      parentId: null,
      projectId: null,
      rank: 1,
      status: 'active',
      projectType,
      flagged: false,
      deferDate: null,
      dueDate: null,
      estimatedMinutes: null,
      energyLevel: null,
      completedAt: null,
      droppedAt: null,
      reviewIntervalDays: 7,
      lastReviewedAt: now,
      nextReviewAt: new Date(Date.now() + 86400000 * 7).toISOString(),
      createdAt: now,
      updatedAt: now,
      deletedAt: null,
    };

    setItems(prev => [newProj, ...prev]);
    return newProj;
  }, []);

  const addActionToProject = useCallback((projectId: string, title: string, context?: string | null) => {
    const now = new Date().toISOString();
    const siblingCount = activeItems.filter(i => i.projectId === projectId).length;
    const newAction: Item = {
      id: `act-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`,
      type: 'action',
      title: title.trim(),
      notes: '',
      parentId: projectId,
      projectId: projectId,
      rank: siblingCount + 1,
      status: 'active',
      context: context || null,
      flagged: false,
      deferDate: null,
      dueDate: null,
      estimatedMinutes: null,
      energyLevel: null,
      completedAt: null,
      droppedAt: null,
      createdAt: now,
      updatedAt: now,
      deletedAt: null,
    };

    setItems(prev => [...prev, newAction]);
    return newAction;
  }, [activeItems]);

  // Someday / Maybe activation: promote to active Next Action
  const activateSomedayMaybe = useCallback((id: string, context?: string | null) => {
    setItems(prev => prev.map(item => {
      if (item.id === id) {
        return {
          ...item,
          status: 'active' as CanonicalStatus,
          context: context !== undefined ? context : item.context,
          updatedAt: new Date().toISOString(),
        };
      }
      return item;
    }));
  }, []);

  // Waiting For resolution: either mark completed or switch to active next action
  const resolveWaitingFor = useCallback((id: string, resolution: 'complete' | 'next_action') => {
    setItems(prev => prev.map(item => {
      if (item.id === id) {
        if (resolution === 'complete') {
          return {
            ...item,
            status: 'completed' as CanonicalStatus,
            completedAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
          };
        } else {
          return {
            ...item,
            status: 'active' as CanonicalStatus,
            waitingForPerson: null,
            waitingSince: null,
            updatedAt: new Date().toISOString(),
          };
        }
      }
      return item;
    }));
  }, []);

  // Log a follow-up on a delegated item
  const logWaitingForFollowUp = useCallback((id: string, followUpNote?: string) => {
    const todayStr = new Date().toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
    setItems(prev => prev.map(item => {
      if (item.id === id) {
        const entry = followUpNote 
          ? `\n[Followed up ${todayStr}: ${followUpNote}]` 
          : `\n[Followed up ${todayStr}]`;
        return {
          ...item,
          notes: (item.notes || '') + entry,
          updatedAt: new Date().toISOString(),
        };
      }
      return item;
    }));
  }, []);

  // Directly capture a new Waiting For item
  const addWaitingForItem = useCallback((title: string, person: string, notes: string = '', context?: string | null) => {
    const now = new Date().toISOString();
    const newItem: Item = {
      id: `wf-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`,
      type: 'action',
      title: title.trim(),
      notes: notes.trim(),
      parentId: null,
      projectId: null,
      rank: 1,
      status: 'on_hold',
      waitingForPerson: person.trim(),
      waitingSince: now,
      context: context || null,
      flagged: false,
      deferDate: null,
      dueDate: null,
      estimatedMinutes: null,
      energyLevel: null,
      completedAt: null,
      droppedAt: null,
      createdAt: now,
      updatedAt: now,
      deletedAt: null,
    };
    setItems(prev => [newItem, ...prev]);
    return newItem;
  }, []);

  // Directly capture a new Someday/Maybe item
  const addSomedayMaybeItem = useCallback((title: string, notes: string = '', context?: string | null) => {
    const now = new Date().toISOString();
    const newItem: Item = {
      id: `sm-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`,
      type: 'action',
      title: title.trim(),
      notes: notes.trim(),
      parentId: null,
      projectId: null,
      rank: 1,
      status: 'on_hold',
      waitingForPerson: null,
      waitingSince: null,
      context: context || null,
      flagged: false,
      deferDate: null,
      dueDate: null,
      estimatedMinutes: null,
      energyLevel: null,
      completedAt: null,
      droppedAt: null,
      createdAt: now,
      updatedAt: now,
      deletedAt: null,
    };
    setItems(prev => [newItem, ...prev]);
    return newItem;
  }, []);

  // Daily review recording
  const [lastDailyReview, setLastDailyReviewState] = useState<string | null>(() => storage.getLastDailyReview());

  const completeDailyReview = useCallback(() => {
    const now = new Date().toISOString();
    storage.saveLastDailyReview(now);
    setLastDailyReviewState(now);
  }, []);

  const resetAllData = useCallback(() => {
    const { items: newItems, tags: newTags } = storage.resetToDefault();
    setItems(newItems);
    setTags(newTags);
    setLastDailyReviewState(null);
  }, []);

  return {
    items: activeItems,
    tags,
    inboxItems,
    projects,
    nextActions,
    waitingForItems,
    somedayMaybeItems,
    lastDailyReview,
    completeDailyReview,
    activateSomedayMaybe,
    resolveWaitingFor,
    logWaitingForFollowUp,
    addWaitingForItem,
    addSomedayMaybeItem,
    captureItem,
    clarifyTrash,
    clarifySomedayMaybe,
    clarifyReference,
    clarifyDoNow,
    clarifyWaitingFor,
    clarifyConvertToProject,
    clarifyToNextAction,
    toggleComplete,
    toggleFlag,
    updateDueDate,
    updateContext,
    createProject,
    addActionToProject,
    resetAllData,
  };
}
