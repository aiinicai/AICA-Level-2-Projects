import type { BaseEntity, ListQuery, ListResult } from "@/types/common";

/**
 * Generic data-access contract implemented by every entity service.
 *
 * Stage 1 ships mock implementations only. A later stage adds a REST
 * implementation backed by the Google Apps Script web API — the UI consumes
 * this interface and therefore does not change.
 */
export interface EntityService<T extends BaseEntity, TCreate = Partial<T>, TUpdate = Partial<T>> {
  list(query?: ListQuery): Promise<ListResult<T>>;
  getById(id: string): Promise<T | null>;
  create(payload: TCreate): Promise<T>;
  update(id: string, payload: TUpdate): Promise<T>;
  remove(id: string): Promise<void>;
}

export type ServiceMode = "mock" | "rest";
