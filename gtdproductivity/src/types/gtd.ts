/**
 * GTDProductivity Core Data Model Types
 * Embodying David Allen's Getting Things Done & OmniFocus-inspired architecture.
 */

export type ItemType = 'folder' | 'project' | 'action';

export type ProjectType = 'sequential' | 'parallel' | 'single_action';

export type CanonicalStatus = 'inbox' | 'active' | 'on_hold' | 'completed' | 'dropped';

export type DynamicAvailability = 
  | 'available' 
  | 'blocked' 
  | 'deferred' 
  | 'due_soon' 
  | 'overdue' 
  | 'completed' 
  | 'dropped';

export type EnergyLevel = 'low' | 'medium' | 'high' | null;

export type TimeRequirement = number | null; // estimated minutes

export type HorizonLevel = 
  | 0 // Runway (Current Actions)
  | 1 // Horizon 1 (Current Projects - 1+ steps)
  | 2 // Horizon 2 (Areas of Focus & Accountability)
  | 3 // Horizon 3 (1-2 Year Goals & Objectives)
  | 4 // Horizon 4 (3-5 Year Vision)
  | 5; // Horizon 5 (Purpose & Principles)

export interface RepeatRule {
  id: string;
  itemId: string;
  frequency: 'daily' | 'weekly' | 'monthly' | 'yearly';
  interval: number; // e.g. every 2 weeks
  repeatFrom: 'scheduled_date' | 'completion_date';
  daysOfWeek?: number[]; // 0=Sun, 1=Mon, ..., 6=Sat
  endType: 'never' | 'after_occurrences' | 'on_date';
  endOccurrences?: number;
  endDate?: string | null;
  createdAt: string;
}

export interface Tag {
  id: string;
  name: string;
  parentId: string | null;
  color?: string | null;
  icon?: string | null;
  rank: number;
  isContext: boolean; // e.g. @calls, @computer, @office
  isEnergyContext: boolean; // high, medium, low
  isTimeContext: boolean; // 5min, 15min, 30min
  isPersonContext: boolean; // e.g. Agenda with Boss
  createdAt: string;
  updatedAt: string;
}

export interface ItemTag {
  itemId: string;
  tagId: string;
}

export interface ItemAttachment {
  id: string;
  itemId: string;
  attachmentType: 'link' | 'note' | 'file_ref';
  title: string;
  uriOrPath?: string | null;
  textContent?: string | null;
  createdAt: string;
}

export interface HorizonNote {
  id: string;
  horizonLevel: HorizonLevel;
  title: string;
  description: string;
  areaId?: string | null; // linked folder / area of focus
  linkedProjectIds: string[];
  createdAt: string;
  updatedAt: string;
}

export interface NaturalPlanningModel {
  purpose: string;
  principles: string[];
  outcomeVision: string;
  brainstormNotes: string;
  organizingStructure: string;
}

export interface Item {
  id: string;
  type: ItemType;
  title: string;
  notes: string;
  
  // Hierarchy
  parentId: string | null; // Parent folder, parent project, or parent action
  projectId: string | null; // Direct enclosing project for fast O(1) project queries
  rank: number; // Lexicographical or integer ordering within sibling list

  // State
  status: CanonicalStatus;
  flagged: boolean;
  
  // GTD Action Specifics
  waitingForPerson?: string | null; // If delegated / Waiting For
  waitingSince?: string | null; // ISO Date when handed off
  context?: string | null; // Primary GTD context (e.g. '@home', '@office', '@phone', '@computer', '@errands')
  
  // OmniFocus Dates
  deferDate: string | null; // ISO Date "Available From" (soft start)
  dueDate: string | null; // ISO Date "Hard Landscape" deadline
  estimatedMinutes: number | null; // Time available criterion
  energyLevel: EnergyLevel; // Energy available criterion
  completedAt: string | null; // ISO Date
  droppedAt: string | null; // ISO Date
  
  // Project-Specific Fields
  projectType?: ProjectType | null; // sequential, parallel, or single-action list
  reviewIntervalDays?: number | null; // default 7 days
  lastReviewedAt?: string | null; // ISO Date
  nextReviewAt?: string | null; // ISO Date
  npmPlan?: NaturalPlanningModel | null; // Natural Planning Model template
  
  // Audit / Local-First metadata
  createdAt: string;
  updatedAt: string;
  deletedAt: string | null; // Soft-delete for 30-day trash safety
}

export interface PerspectiveFilterRule {
  itemTypes?: ItemType[];
  canonicalStatuses?: CanonicalStatus[];
  availability?: DynamicAvailability[];
  flaggedOnly?: boolean;
  waitingForOnly?: boolean;
  tagIds?: string[];
  excludeTagIds?: string[];
  projectIds?: string[];
  dueBeforeDays?: number; // e.g. due within 2 days
  searchQuery?: string;
}

export interface Perspective {
  id: string;
  name: string;
  icon: string;
  isBuiltin: boolean;
  filter: PerspectiveFilterRule;
  groupBy: 'none' | 'project' | 'tag' | 'context' | 'due_date' | 'flagged';
  sortBy: 'rank' | 'due_date' | 'defer_date' | 'title' | 'estimated_minutes';
  sortOrder: 'asc' | 'desc';
  rank: number;
}

export interface ReviewRecord {
  id: string;
  projectId?: string | null;
  completedAt: string;
  reviewType: 'weekly_review_full' | 'single_project' | 'daily_glance';
  notes?: string;
  itemsProcessedCount: number;
}
