import { listDatasets } from "../query/engine";
import { runQuery } from "../query/engine";
import type { DataQuery, DataResult, Dataset, Field, IntegrationProvider, SyncResult } from "../types";
import { integrationById } from "./catalog";

/**
 * Adapter registry.
 *
 * Production adapters must run server-side: credentials are stored as secrets
 * and never reach the browser. The demo adapter below answers from the local
 * demo dataset so the product is fully explorable before any real credentials
 * exist. Anything it returns is labelled "Demo data" in the UI.
 */

class DemoAdapter implements IntegrationProvider {
  id: string;
  name: string;
  private allowed: string[];

  constructor(providerId: string, datasets: string[]) {
    const def = integrationById(providerId);
    this.id = providerId;
    this.name = def?.name ?? providerId;
    this.allowed = datasets.length ? datasets : (def?.datasets.map((d) => d.id) ?? []);
  }

  async connect() {
    await delay(400);
  }

  async disconnect() {
    await delay(200);
  }

  async testConnection() {
    await delay(700);
    return { ok: true, message: "Connection successful — demo adapter responded in 0.7s" };
  }

  async getDatasets(): Promise<Dataset[]> {
    return listDatasets().filter((d) => this.allowed.includes(d.id));
  }

  async getSchema(dataset: string): Promise<Field[]> {
    return listDatasets().find((d) => d.id === dataset)?.fields ?? [];
  }

  async fetchData(dataset: string, query: DataQuery): Promise<DataResult> {
    return runQuery({ ...query, dataset });
  }

  async sync(): Promise<SyncResult> {
    await delay(900);
    const datasets = await this.getDatasets();
    return {
      records: datasets.reduce((sum, d) => sum + d.recordCount, 0),
      at: new Date().toISOString(),
      ok: true,
    };
  }
}

function delay(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

export function getAdapter(providerId: string, datasets: string[] = []): IntegrationProvider {
  const def = integrationById(providerId);
  if (def?.mode === "production") {
    throw new Error(
      `Adapter for ${def.name} must be called through a server function — credentials never leave the server.`,
    );
  }
  return new DemoAdapter(providerId, datasets);
}

export const isDemoAdapter = (providerId: string) => integrationById(providerId)?.mode !== "production";
