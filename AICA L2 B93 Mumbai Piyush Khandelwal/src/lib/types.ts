export type Aggregation = "sum" | "avg" | "min" | "max" | "count";

export type FilterOperator =
  | "eq"
  | "neq"
  | "gt"
  | "gte"
  | "lt"
  | "lte"
  | "contains"
  | "in"
  | "between";

export interface Filter {
  field: string;
  op: FilterOperator;
  value: unknown;
}

export type DateGrain = "day" | "week" | "month" | "quarter" | "year";

export interface Measure {
  field: string;
  aggregation: Aggregation;
  alias?: string;
}

export interface Sort {
  field: string;
  dir: "asc" | "desc";
}

/** Provider-agnostic query. Widgets consume results, never raw provider data. */
export interface DataQuery {
  sourceId: string;
  dataset: string;
  dimensions?: string[];
  measures?: Measure[];
  filters?: Filter[];
  groupBy?: string[];
  dateField?: string;
  grain?: DateGrain;
  sort?: Sort[];
  limit?: number;
}

export type FieldType = "string" | "number" | "currency" | "percent" | "date" | "boolean";

export interface Field {
  name: string;
  label: string;
  type: FieldType;
  role: "dimension" | "measure";
}

export interface Dataset {
  id: string;
  name: string;
  description: string;
  fields: Field[];
  recordCount: number;
}

export interface DataResult {
  columns: Field[];
  rows: Record<string, string | number | null>[];
  truncated?: boolean;
  generatedAt: string;
}

export interface SyncResult {
  records: number;
  at: string;
  ok: boolean;
  message?: string;
}

/** Every provider (Tally, Zoho, Razorpay, custom REST…) implements this. */
export interface IntegrationProvider {
  id: string;
  name: string;
  connect(credentials: Record<string, string>): Promise<void>;
  disconnect(): Promise<void>;
  testConnection(): Promise<{ ok: boolean; message: string }>;
  getDatasets(): Promise<Dataset[]>;
  getSchema(dataset: string): Promise<Field[]>;
  fetchData(dataset: string, query: DataQuery): Promise<DataResult>;
  sync(): Promise<SyncResult>;
}

export type WidgetType =
  | "kpi"
  | "line"
  | "bar"
  | "area"
  | "pie"
  | "table"
  | "gauge"
  | "progress"
  | "text";

export interface WidgetOptions {
  /* visualisation */
  stacked?: boolean;
  horizontal?: boolean;
  donut?: boolean;
  showLegend?: boolean;
  showGrid?: boolean;
  showLabels?: boolean;
  colorIndex?: number;
  /* formatting */
  format?: "currency" | "number" | "percent" | "compact";
  decimals?: number;
  /* kpi / gauge / progress */
  comparison?: number;
  target?: number;
  sparkline?: boolean;
  /* text */
  body?: string;
  /* behaviour */
  drilldown?: boolean;
}

export interface WidgetLayout {
  /** column start is implicit; w in 12-col units, h in 80px row units */
  w: number;
  h: number;
}

export interface Widget {
  id: string;
  type: WidgetType;
  title: string;
  subtitle?: string;
  tab?: string;
  query?: DataQuery;
  options: WidgetOptions;
  layout: WidgetLayout;
}

export interface DashboardFilterDef {
  id: string;
  label: string;
  field: string;
  type: "date-range" | "select";
  options?: string[];
  value?: string;
}

export interface Dashboard {
  id: string;
  name: string;
  description?: string;
  tabs: string[];
  widgets: Widget[];
  filters: DashboardFilterDef[];
  visibility: "private" | "workspace" | "link";
  updatedAt: string;
  favourite?: boolean;
}

export type ConnectionStatus = "connected" | "error" | "syncing" | "disconnected";

export interface Connection {
  id: string;
  providerId: string;
  name: string;
  status: ConnectionStatus;
  datasets: string[];
  frequency: "manual" | "hourly" | "6h" | "daily";
  lastSync?: string;
  nextSync?: string;
  records: number;
  error?: string;
}

export interface AppNotification {
  id: string;
  title: string;
  body: string;
  category: "sync" | "report" | "alert" | "system";
  level: "info" | "success" | "warning" | "error";
  at: string;
  read: boolean;
}

export interface AlertRule {
  id: string;
  name: string;
  metric: string;
  condition: "drops_below" | "rises_above" | "decreases_by" | "increases_by";
  value: number;
  unit: "amount" | "percent";
  comparison: "previous_month" | "previous_quarter" | "absolute";
  channels: string[];
  enabled: boolean;
}

export interface ScheduledReport {
  id: string;
  reportName: string;
  cadence: "daily" | "weekly" | "monthly" | "quarterly";
  time: string;
  recipients: string[];
  format: "pdf" | "csv" | "excel";
  enabled: boolean;
  nextRun: string;
}

export interface ReportSection {
  id: string;
  kind: "summary" | "kpis" | "chart" | "table" | "commentary";
  title: string;
  body?: string;
  widgetIds?: string[];
}

export interface Report {
  id: string;
  name: string;
  period: string;
  sections: ReportSection[];
  updatedAt: string;
}

export type Role = "owner" | "admin" | "editor" | "viewer";

export interface Member {
  id: string;
  name: string;
  email: string;
  role: Role;
  status: "active" | "invited";
  lastActive?: string;
}

export interface WorkspaceSettings {
  workspaceName: string;
  currency: "INR" | "USD" | "EUR" | "GBP" | "AED";
  numberSystem: "indian" | "international";
  dateFormat: "DD/MM/YYYY" | "MM/DD/YYYY" | "YYYY-MM-DD";
  timezone: string;
  compactNumbers: boolean;
  theme: "light" | "dark" | "system";
}
