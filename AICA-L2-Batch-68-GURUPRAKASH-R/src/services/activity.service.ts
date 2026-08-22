import type { ActivityInput, ActivityRecord } from "@/types/activity";
import { delay } from "./mock.utils";
import { store } from "./store";

/**
 * Append-only activity trail. There is deliberately no update or delete:
 * activity records are immutable once written.
 */
export interface ActivityService {
  list(): Promise<ActivityRecord[]>;
  getByClientId(clientId: string): Promise<ActivityRecord[]>;
  getByEngagementId(engagementId: string): Promise<ActivityRecord[]>;
  append(input: ActivityInput): Promise<ActivityRecord>;
}

let counter = store.activity.length;

const byNewestFirst = (a: ActivityRecord, b: ActivityRecord) =>
  b.timestamp.localeCompare(a.timestamp);

/** Synchronous writer used internally by the client and engagement services. */
export function appendActivity(input: ActivityInput): ActivityRecord {
  counter += 1;
  const record: ActivityRecord = {
    ...input,
    id: `ACT-LOG-${String(counter).padStart(4, "0")}`,
    timestamp: new Date().toISOString(),
  };
  store.activity.push(record);
  return record;
}

export const activityService: ActivityService = {
  async list() {
    return delay([...store.activity].sort(byNewestFirst));
  },
  async getByClientId(clientId) {
    return delay(
      store.activity.filter((entry) => entry.clientId === clientId).sort(byNewestFirst),
    );
  },
  async getByEngagementId(engagementId) {
    return delay(
      store.activity.filter((entry) => entry.engagementId === engagementId).sort(byNewestFirst),
    );
  },
  async append(input) {
    return delay(appendActivity(input));
  },
};
