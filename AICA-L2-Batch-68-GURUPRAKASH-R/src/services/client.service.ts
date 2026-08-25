import type { Actor } from "@/types/activity";
import type {
  ClientContact,
  ClientFormValues,
  ClientLocation,
  ClientRecord,
} from "@/types/client";
import { formatId, type ClientId } from "@/types/common";
import { ACTIVE_ENGAGEMENT_STATUSES, type EngagementStatus } from "@/types/engagement";
import { appendActivity } from "./activity.service";
import { delay } from "./mock.utils";
import { sequences, store } from "./store";

export interface ClientEngagementStats {
  totalEngagements: number;
  activeEngagements: number;
  latestEngagementStatus: EngagementStatus | null;
}

export type ClientListItem = ClientRecord & ClientEngagementStats;

export interface ClientListQuery {
  search?: string;
  industry?: string;
  entityType?: string;
  status?: string;
  activeOnly?: "all" | "active" | "inactive";
  sortBy?: "clientCode" | "legalName" | "status" | "updatedAt";
  sortDir?: "asc" | "desc";
  page?: number;
  pageSize?: number;
}

export interface ClientListResult {
  items: ClientListItem[];
  total: number;
  page: number;
  pageSize: number;
}

export interface ClientService {
  list(query?: ClientListQuery): Promise<ClientListResult>;
  getById(id: string): Promise<ClientListItem | null>;
  create(values: ClientFormValues, actor: Actor): Promise<ClientRecord>;
  update(id: string, values: ClientFormValues, actor: Actor): Promise<ClientRecord>;
  deactivate(id: string, reason: string, actor: Actor): Promise<ClientRecord>;
  reactivate(id: string, reason: string, actor: Actor): Promise<ClientRecord>;
  archive(id: string, reason: string, actor: Actor): Promise<ClientRecord>;
  addContact(id: string, contact: Omit<ClientContact, "id">, actor: Actor): Promise<ClientRecord>;
  addLocation(
    id: string,
    location: Omit<ClientLocation, "id">,
    actor: Actor,
  ): Promise<ClientRecord>;
  /** Statuses that prevent archiving, exposed so the UI can explain the block. */
  blockingEngagements(id: string): { reference: string; status: EngagementStatus }[];
}

function stats(clientId: string): ClientEngagementStats {
  const linked = store.engagements.filter((engagement) => engagement.clientId === clientId);
  const latest = [...linked].sort((a, b) => b.updatedAt.localeCompare(a.updatedAt))[0];
  return {
    totalEngagements: linked.length,
    activeEngagements: linked.filter((engagement) =>
      ACTIVE_ENGAGEMENT_STATUSES.includes(engagement.status),
    ).length,
    latestEngagementStatus: latest?.status ?? null,
  };
}

const decorate = (client: ClientRecord): ClientListItem => ({ ...client, ...stats(client.id) });

function find(id: string): ClientRecord {
  const client = store.clients.find((row) => row.id === id);
  if (!client) throw new Error(`Client ${id} was not found.`);
  return client;
}

function touch(client: ClientRecord, actor: Actor) {
  client.updatedAt = new Date().toISOString();
  client.updatedBy = actor.user;
}

function log(
  client: ClientRecord,
  actor: Actor,
  action: string,
  remarks: string,
  previousStatus: string | null = null,
  newStatus: string | null = null,
) {
  appendActivity({
    user: actor.user,
    role: actor.role,
    clientId: client.id,
    clientName: client.legalName,
    engagementId: null,
    engagementRef: null,
    module: "Clients",
    recordReference: client.clientCode,
    action,
    previousStatus,
    newStatus,
    remarks,
  });
}

export const clientService: ClientService = {
  async list(query = {}) {
    const term = query.search?.trim().toLowerCase();
    let rows = store.clients.map(decorate);

    if (term) {
      rows = rows.filter((row) =>
        [row.clientCode, row.legalName, row.tradeName]
          .join(" ")
          .toLowerCase()
          .includes(term),
      );
    }
    if (query.industry && query.industry !== "all") {
      rows = rows.filter((row) => row.industry === query.industry);
    }
    if (query.entityType && query.entityType !== "all") {
      rows = rows.filter((row) => row.entityType === query.entityType);
    }
    if (query.status && query.status !== "all") {
      rows = rows.filter((row) => row.status === query.status);
    }
    if (query.activeOnly === "active") rows = rows.filter((row) => row.isActive);
    if (query.activeOnly === "inactive") rows = rows.filter((row) => !row.isActive);

    const sortBy = query.sortBy ?? "clientCode";
    const dir = query.sortDir === "desc" ? -1 : 1;
    rows.sort((a, b) => String(a[sortBy]).localeCompare(String(b[sortBy])) * dir);

    const total = rows.length;
    const page = query.page ?? 1;
    const pageSize = query.pageSize ?? 10;
    const start = (page - 1) * pageSize;
    return delay({ items: rows.slice(start, start + pageSize), total, page, pageSize });
  },

  async getById(id) {
    const client = store.clients.find((row) => row.id === id);
    return delay(client ? decorate(client) : null);
  },

  async create(values, actor) {
    const code = formatId("client", sequences.nextClient()) as ClientId;
    const timestamp = new Date().toISOString();
    const client: ClientRecord = {
      ...values,
      id: code,
      clientCode: code,
      // New clients always start Active; status changes use the dedicated actions.
      status: "Active",
      contacts: [],
      locations: [],
      createdAt: timestamp,
      createdBy: actor.user,
      updatedAt: timestamp,
      updatedBy: actor.user,
      isActive: true,
    };
    store.clients.push(client);
    log(client, actor, "Client created", values.remarks || "New client record created.", null, client.status);
    return delay(client);
  },


  async update(id, values, actor) {
    const client = find(id);
    // Status, isActive, clientCode and id are immutable through ordinary update.
    const { status: _status, ...editable } = values;
    void _status;
    Object.assign(client, editable, {
      id: client.id,
      clientCode: client.clientCode,
      status: client.status,
      isActive: client.isActive,
    });
    touch(client, actor);
    log(client, actor, "Client updated", "Client master details amended.", client.status, client.status);
    return delay(client);
  },

  async deactivate(id, reason, actor) {
    const client = find(id);
    if (client.status !== "Active") {
      throw new Error(
        `Only an Active client can be deactivated. ${client.clientCode} is currently ${client.status}.`,
      );
    }
    const previous = client.status;
    client.status = "Inactive";
    client.isActive = false;
    touch(client, actor);
    log(client, actor, "Client deactivated", reason, previous, "Inactive");
    return delay(client);
  },

  async reactivate(id, reason, actor) {
    const client = find(id);
    if (client.status !== "Inactive") {
      throw new Error(
        client.status === "Archived"
          ? `${client.clientCode} is archived. Archived clients cannot be reactivated.`
          : `Only an Inactive client can be reactivated. ${client.clientCode} is currently ${client.status}.`,
      );
    }
    const previous = client.status;
    client.status = "Active";
    client.isActive = true;
    touch(client, actor);
    log(client, actor, "Client reactivated", reason, previous, "Active");
    return delay(client);
  },

  async archive(id, reason, actor) {
    const client = find(id);
    if (client.status === "Archived") {
      throw new Error(`${client.clientCode} is already archived.`);
    }
    const blocking = clientService.blockingEngagements(id);
    if (blocking.length > 0) {
      throw new Error(
        `This client cannot be archived: ${blocking.length} engagement(s) are still live (${blocking
          .map((item) => `${item.reference} – ${item.status}`)
          .join(", ")}).`,
      );
    }
    const previous = client.status;
    client.status = "Archived";
    client.isActive = false;
    touch(client, actor);
    log(client, actor, "Client archived", reason, previous, "Archived");
    return delay(client);
  },


  async addContact(id, contact, actor) {
    const client = find(id);
    client.contacts.push({ ...contact, id: `CNT-${Date.now().toString().slice(-6)}` });
    touch(client, actor);
    log(client, actor, "Client updated", `Secondary contact added: ${contact.name}.`);
    return delay(client);
  },

  async addLocation(id, location, actor) {
    const client = find(id);
    client.locations.push({ ...location, id: `LOC-${Date.now().toString().slice(-6)}` });
    touch(client, actor);
    log(client, actor, "Client updated", `Location added: ${location.locationName}.`);
    return delay(client);
  },

  blockingEngagements(id) {
    return store.engagements
      .filter(
        (engagement) =>
          engagement.clientId === id && ACTIVE_ENGAGEMENT_STATUSES.includes(engagement.status),
      )
      .map((engagement) => ({ reference: engagement.reference, status: engagement.status }));
  },
};
