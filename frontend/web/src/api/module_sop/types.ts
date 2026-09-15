/** SOP 模块共享类型（与后端 app/modules/sop/schemas 对应） */

export interface SopSpuInfo {
  spu_code: string;
  spu_name: string;
  product_line: string;
  brand: string;
  category: string;
  lifecycle_stage: string;
}

export interface SopSpuListResponse {
  items: SopSpuInfo[];
  total: number;
}

export interface SopDimensionOptions {
  regions: string[];
  channels: string[];
}

export interface SopSourceStatus {
  domain: string;
  label: string;
  source_objects: string[];
  phase_scope: "phase_one_core" | "phase_one_extension" | "connection_only" | string;
  contract_status: string;
  ingestion_status: string;
  latest_snapshot_at: string | null;
  max_business_date: string | null;
  record_count: number;
  note: string;
}

export interface SopDataStatus {
  overall_status: "ready" | "partial" | "not_started" | string;
  source_connection_configured: boolean;
  sources: SopSourceStatus[];
  open_quality_issues: number;
}

export interface SopMonthlyActual {
  period: string;
  outbound_qty: number;
  activation_qty: number;
}

export interface SopForecastPoint {
  forecast_month: string;
  region: string;
  channel: string;
  forecast_type: string;
  forecast_qty: number;
  version: string;
  source_table: string;
  snapshot_at: string;
}

export interface SopRuleFinding {
  code: string;
  severity: string;
  message: string;
}

export interface SopForecastCheck {
  forecast_month: string;
  region: string;
  channel: string;
  forecast_qty: number;
  evaluable: boolean;
  score: number | null;
  level: string;
  rule_version: string;
  baseline_qty: number | null;
  deviation_ratio: number | null;
  findings: SopRuleFinding[];
}

export interface SopTrendPoint {
  period: string;
  type: "actual" | "forecast";
  outbound_qty: number | null;
  activation_qty: number | null;
  ai_forecast_outbound: number | null;
  ai_forecast_activation: number | null;
  submit_forecast: number | null;
  event: string;
}

export interface SopChannelDifference {
  channel: string;
  month: string;
  aiQty: number;
  submitQty: number;
  diffQty: number;
  deviationRatio: number;
  dimension: string;
  reason: string;
}

export interface SopChannelMatrix {
  months: string[];
  channels: string[];
  submitMatrix: Record<string, number[]>;
  aiBaselineMatrix: Record<string, number[]>;
  deviationMatrix: Record<string, number[]>;
  diffList: SopChannelDifference[];
}

export interface SopProvenance {
  domain: string;
  source_system: string;
  source_table: string;
  batch_id: string;
  snapshot_at: string;
}

export interface SopMonthlyEventInfo {
  event_month: string;
  event: string;
}

export interface SopFirstPhaseReport {
  report_version: string;
  spu: SopSpuInfo;
  as_of_date: string;
  filters: { region: string; channel: string };
  completeness_status: "complete" | "partial" | "not_ready";
  missing_domains: string[];
  warnings: string[];
  monthly_actuals: SopMonthlyActual[];
  events: SopMonthlyEventInfo[];
  forecasts: SopForecastPoint[];
  forecast_checks: SopForecastCheck[];
  provenance: SopProvenance[];
}

export interface SopImportMeta {
  source_system: string;
  source_table: string;
  batch_id: string;
  snapshot_at: string;
}

export interface SopImportResponse {
  domain: string;
  batch_id: string;
  accepted: number;
  rejected: number;
  status: "completed" | "partial" | "failed";
  quality_issue_ids: number[];
}

export interface SopReportSnapshotSummary {
  id: number;
  spu_code: string;
  as_of_date: string;
  report_version: string;
  completeness_status: string;
  generated_at: string;
  record_count: number;
}

export interface SopReportSnapshotDetail {
  id: number;
  spu_code: string;
  as_of_date: string;
  report_version: string;
  completeness_status: string;
  generated_at: string;
  payload: Record<string, any>;
}

export interface SopSnapshotGenerateResponse {
  status: string;
  as_of_date?: string;
  report_version?: string;
  generated_count?: number;
}

export interface SopDocumentInfo {
  filename: string;
  file_type: string;
  chunk_count: number;
}

export interface SopDocumentChunk {
  chunk_id: string;
  chunk_idx: number;
  text_preview: string;
  file_type: string;
  page_number: number;
  chunk_level: number;
}

export interface SopSessionInfo {
  session_id: string;
  title: string;
  updated_at: string;
  message_count: number;
}

export interface SopMessageInfo {
  type: string;
  content: string;
  timestamp: string;
  rag_trace?: Record<string, any> | null;
}
