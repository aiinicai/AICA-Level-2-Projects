import type { BaseEntity, ListQuery, ListResult } from "@/types/common";
import type { EntityService } from "./service.types";

/** Simulates network latency so loading states behave realistically in Stage 1. */
export function delay<T>(value: T, ms = 250): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), ms));
}

export function paginate<T>(items: T[], query: ListQuery = {}): ListResult<T> {
  const page = query.page ?? 1;
  const pageSize = query.pageSize ?? 25;
  const start = (page - 1) * pageSize;
  return { items: items.slice(start, start + pageSize), total: items.length, page, pageSize };
}

/**
 * Builds an in-memory service for an entity. Mock modules pass their seed rows
 * (empty in Stage 1) and get a fully working EntityService implementation.
 */
export function createMockService<T extends BaseEntity>(
  entityName: string,
  seed: T[] = [],
): EntityService<T> {
  let rows = [...seed];

  return {
    async list(query) {
      const term = query?.search?.trim().toLowerCase();
      const filtered = term
        ? rows.filter((row) => JSON.stringify(row).toLowerCase().includes(term))
        : rows;
      return delay(paginate(filtered, query));
    },
    async getById(id) {
      return delay(rows.find((row) => row.id === id) ?? null);
    },
    async create(payload) {
      throw new Error(`${entityName}: create() is implemented in a later stage. ${String(!!payload)}`);
    },
    async update(id, payload) {
      throw new Error(
        `${entityName}: update() is implemented in a later stage. (${id}, ${String(!!payload)})`,
      );
    },
    async remove(id) {
      rows = rows.filter((row) => row.id !== id);
      await delay(null);
    },
  };
}
